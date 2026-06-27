import { ConfigLoader } from '../config/index.js';
import { createHash } from 'node:crypto';
import { HermesDbClient, ArtifactValidator } from '../hermes/index.js';
import type { WorkflowArtifact } from '../hermes/index.js';
import {
  ArticleDocumentToWechatArtifactBuilder,
  ArticleDocumentValidator,
  MarkdownArticleExporter,
  MarkdownArticleImporter,
  type ArticleDocumentEnvelope,
  type ArticleDocumentValidationIssue,
  type ArticleDocumentValidationResult,
  WechatArticleDocumentRenderer,
  getWechatStyleProfile,
} from '../render/index.js';
import { SQLiteJobStore, type DraftJobStore } from '../store/index.js';
import { DraftWorkflow } from '../workflow/index.js';
import { AssetSourceLoader } from '../wechat/AssetSourceLoader.js';
import { WechatAdapterClient, type AdapterUploadAssetResponse } from '../wechat/WechatAdapterClient.js';
import { articleDocumentError } from './articleDocumentErrors.js';
import { mapOperationalErrorToResult } from './errorMapping.js';
import { HealthMonitor, type HealthSnapshot } from './HealthMonitor.js';
import {
  type BuildPublishReadyArtifactInput,
  type BuildPublishReadyArtifactOutput,
  type CreateDraftFacadeInput,
  type CreateDraftFacadeOutput,
  type CreateDraftInput,
  type CreateDraftOutput,
  type FacadePhase,
  type GetDraftStatusInput,
  type GetDraftStatusOutput,
  type ImportArticleMarkdownInput,
  type ImportArticleMarkdownOutput,
  type ListDraftsInput,
  type ListDraftsOutput,
  type AssetPreflightInput,
  type AssetPreflightOutput,
  type ListAccountsInput,
  type ListAccountsOutput,
  type RenderArticleDocumentInputTool,
  type RenderArticleDocumentOutputTool,
  type Result,
  type UploadAssetInput,
  type UploadAssetOutput,
  type ValidateArticleDocumentInput,
  type ValidateArticleDocumentOutput,
  type ValidateArtifactInput,
  type ValidateArtifactOutput,
  ErrorCode,
  createErrorResult,
  createSuccessResult,
} from '../schemas/index.js';
import type { AccountConfig, EcsWechatAdapterConfig, ServiceConfig } from '../config/types.js';

export interface WechatDraftServiceDependencies {
  configLoader: ConfigLoader;
  config: ServiceConfig;
  hermesDbClient: HermesDbClient;
  artifactValidator: ArtifactValidator;
  jobStore: DraftJobStore;
  draftWorkflow: DraftWorkflow;
  assetSourceLoader: AssetSourceLoader;
  adapterClientFactory?: WechatAdapterClientFactory;
  healthMonitor?: HealthMonitor;
}

export interface WechatAssetUploadClient {
  batchGetDrafts?(
    account: string,
    request: { offset: number; count: number; no_content: 0 | 1 }
  ): Promise<{
    success: boolean;
    total_count?: number;
    item_count?: number;
    item?: Array<{
      media_id: string;
      content?: {
        news_item?: Array<{
          title?: string;
          author?: string;
          digest?: string;
          content?: string;
          content_source_url?: string;
          thumb_media_id?: string;
        }>;
      };
      update_time?: number;
    }>;
  }>;

  uploadAsset(
    account: string,
    request: {
      usage: 'body_image' | 'cover_image';
      bytes: Uint8Array;
      filename: string;
      mimeType: string;
    }
  ): Promise<AdapterUploadAssetResponse>;
}

export type WechatAdapterClientFactory = (
  adapterConfig: EcsWechatAdapterConfig
) => WechatAssetUploadClient;

interface ResolvedAccountAdapter {
  accountConfig: AccountConfig;
  adapterConfig: EcsWechatAdapterConfig;
}

export interface LocalHealthSnapshot {
  status: 'ok' | 'degraded';
  version: string;
  checks: {
    config_loaded: boolean;
    runtime_writable: boolean;
  };
}

export class WechatDraftService {
  private readonly configLoader: ConfigLoader;
  private readonly config: ServiceConfig;
  private readonly hermesDbClient: HermesDbClient;
  private readonly artifactValidator: ArtifactValidator;
  private readonly jobStore: DraftJobStore;
  private readonly draftWorkflow: DraftWorkflow;
  private readonly assetSourceLoader: AssetSourceLoader;
  private readonly adapterClientFactory: WechatAdapterClientFactory;
  private readonly healthMonitor: HealthMonitor;

  constructor(dependencies: WechatDraftServiceDependencies) {
    this.configLoader = dependencies.configLoader;
    this.config = dependencies.config;
    this.hermesDbClient = dependencies.hermesDbClient;
    this.artifactValidator = dependencies.artifactValidator;
    this.jobStore = dependencies.jobStore;
    this.draftWorkflow = dependencies.draftWorkflow;
    this.assetSourceLoader = dependencies.assetSourceLoader;
    this.adapterClientFactory =
      dependencies.adapterClientFactory || ((adapterConfig) => new WechatAdapterClient(adapterConfig));
    this.healthMonitor =
      dependencies.healthMonitor ||
      new HealthMonitor({
        runtimePath: dependencies.config.runtime_path || process.env.WECHAT_DRAFT_RUNTIME_PATH || '.',
        configLoaded: true,
        sqliteCheck: () => ({ ok: true }),
        initialExternalChecks: {
          adapter: { ok: null },
          hermesDb: { ok: null },
        },
      });
  }

  static async create(): Promise<WechatDraftService> {
    const configLoader = new ConfigLoader();
    const config = configLoader.load();
    const jobStore = new SQLiteJobStore({ runtimePath: config.runtime_path });

    await jobStore.initialize();
    const hermesDbClient = new HermesDbClient(
      config.hermes_db.base_url,
      config.hermes_db.timeout_ms,
      config.hermes_db.auth_token
    );

    return new WechatDraftService({
      configLoader,
      config,
      hermesDbClient,
      artifactValidator: new ArtifactValidator(),
      jobStore,
      draftWorkflow: new DraftWorkflow(),
      assetSourceLoader: new AssetSourceLoader(),
      adapterClientFactory: (adapterConfig) => new WechatAdapterClient(adapterConfig),
      healthMonitor: new HealthMonitor({
        runtimePath: jobStore.getRuntimePath(),
        configLoaded: true,
        probeIntervalMs: parseHealthProbeInterval(),
        sqliteCheck: () => jobStore.checkHealth(),
        adapterProbe: async () => checkAdapter(config.wechat_adapter),
        hermesDbProbe: async () => {
          const result = await hermesDbClient.health();
          return {
            ok: result.ok,
            error: result.error,
          };
        },
      }),
    });
  }

  async getHealthSnapshot(): Promise<HealthSnapshot> {
    return this.healthMonitor.getSnapshot();
  }

  startHealthMonitor(): void {
    this.healthMonitor.start();
  }

  stopHealthMonitor(): void {
    this.healthMonitor.stop();
  }

  listAccounts(input?: ListAccountsInput): Result<ListAccountsOutput> {
    try {
      const accounts = this.configLoader.getAllAccounts(input?.include_disabled ?? false);
      return createSuccessResult({
        accounts: accounts.map((account) => {
          return {
            account_id: account.account_id,
            display_name: account.display_name,
            enabled: account.enabled,
            capabilities: this.config.wechat_adapter.capabilities,
            constraints: this.assetSourceLoader.getConstraints(),
          };
        }),
      });
    } catch (error) {
      return this.internalError(error);
    }
  }

  async validatePublishArtifact(
    input: ValidateArtifactInput
  ): Promise<Result<ValidateArtifactOutput>> {
    const resolved = this.resolveAccountAdapter(input.account);
    if (!resolved.success) {
      return resolved;
    }

    try {
      const artifact = await this.hermesDbClient.getArtifact(input.artifact_id);
      if (!artifact) {
        return createErrorResult(
          ErrorCode.ARTIFACT_NOT_FOUND,
          `Artifact "${input.artifact_id}" not found in hermes-db`
        );
      }

      const validationResult = this.artifactValidator.validate(artifact);
      return createSuccessResult({
        valid: validationResult.valid,
        artifact_id: input.artifact_id,
        account: input.account,
        validation_errors: [
          ...validationResult.errors,
          ...validationResult.warnings,
        ],
        artifact_summary: {
          title: (artifact.metadata as any)?.title,
          stage: artifact.stage,
          type: artifact.type,
          publish_ready: (artifact.metadata as any)?.publish_ready,
          wechat_asset_ready: (artifact.metadata as any)?.wechat_asset_manifest?.ready,
        },
      });
    } catch (error) {
      return this.internalError(error);
    }
  }

  async createDraft(input: CreateDraftInput): Promise<Result<CreateDraftOutput>> {
    const resolved = this.resolveAccountAdapter(input.account);
    if (!resolved.success) {
      return resolved;
    }

    try {
      const finalIdempotencyKey =
        input.idempotency_key ||
        SQLiteJobStore.generateIdempotencyKey(input.account, input.artifact_id);
      const job = await this.draftWorkflow.execute({
        account: input.account,
        artifactId: input.artifact_id,
        idempotencyKey: finalIdempotencyKey,
        hermesDbClient: this.hermesDbClient,
        adapterConfig: resolved.data.adapterConfig,
        jobStore: this.jobStore,
      });

      return createSuccessResult({
        job_id: job.job_id,
        status: job.status,
        account: job.account,
        artifact_id: job.artifact_id,
        title: job.title,
        media_id: job.media_id,
        error: job.error,
        created_at: job.created_at,
      });
    } catch (error) {
      return this.internalError(error);
    }
  }

  async createDraftFacade(
    input: CreateDraftFacadeInput
  ): Promise<Result<CreateDraftFacadeOutput>> {
    const phaseTrace: FacadePhase[] = [];
    const idempotencyKey =
      input.idempotency_key ||
      SQLiteJobStore.generateIdempotencyKey(
        input.account,
        input.source_type === 'publish_ready_artifact' ? input.artifact_id : input.publish_artifact_id
      );
    let publishArtifactId =
      input.source_type === 'publish_ready_artifact' ? input.artifact_id : input.publish_artifact_id;
    let upsertOutcome: Record<string, unknown> | undefined;

    const fail = <T>(
      phase: FacadePhase['phase'],
      result: Result<T>,
      fallbackNextAction: string,
      fallbackMessage: string
    ): Result<CreateDraftFacadeOutput> => {
      setPhase(phaseTrace, phase, 'failed', publishArtifactId, result.success ? fallbackMessage : result.error.message);
      const error = result.success
        ? {
            code: ErrorCode.INTERNAL_ERROR,
            message: fallbackMessage,
            next_action: fallbackNextAction,
            retryable: false,
            current_phase: phase,
          }
        : result.error;
      return createErrorResult(error.code as typeof ErrorCode[keyof typeof ErrorCode], error.message, {
        ...(error.details ?? {}),
        phase_trace: phaseTrace,
        publish_artifact_id: publishArtifactId,
        upsert_outcome: upsertOutcome,
      }, {
        next_action: error.next_action || fallbackNextAction,
        remediation_hint: error.remediation_hint,
        retryable: error.retryable ?? false,
        current_phase: error.current_phase || phase,
      });
    };

    setPhase(phaseTrace, 'input_validation', 'succeeded');

    if (input.source_type === 'article_document') {
      setPhase(phaseTrace, 'asset_preflight', 'skipped', undefined, 'Prepared WeChat asset IDs/URLs are required; implicit upload/compression is out of scope.');

      setPhase(phaseTrace, 'artifact_build', 'running');
      const built = this.buildPublishReadyArtifact({
        article: input.article,
        artifact_id: input.publish_artifact_id,
        run_id: input.run_id,
        account: input.account,
        task_id: input.task_id,
        topic_id: input.topic_id,
        source_artifact_id: input.source_artifact_id,
        style_profile_id: input.style_profile_id,
      });
      if (!built.success) {
        return fail('artifact_build', built, 'fix_article_document', 'Failed to build publish-ready artifact');
      }
      setPhase(phaseTrace, 'artifact_build', 'succeeded', publishArtifactId);

      setPhase(phaseTrace, 'workflow_run_upsert', 'running');
      try {
        const runUpsert = await this.hermesDbClient.upsertWorkflowRun({
          run_id: input.run_id,
          phase: 'draft',
          status: 'running',
          account: input.account,
          task_id: input.task_id,
          topic_id: input.topic_id,
          current_stage: 'publish_ready_facade',
          metadata: {
            source: 'wechat_create_draft_facade',
            source_type: input.source_type,
          },
        });
        if (runUpsert.error) {
          return this.facadeHermesError('workflow_run_upsert', runUpsert, phaseTrace, publishArtifactId, upsertOutcome);
        }
        setPhase(phaseTrace, 'workflow_run_upsert', 'succeeded');
      } catch (error) {
        return this.facadeCaughtError('workflow_run_upsert', error, phaseTrace, publishArtifactId, upsertOutcome);
      }

      setPhase(phaseTrace, 'artifact_upsert', 'running', publishArtifactId);
      try {
        const artifactUpsert = await this.hermesDbClient.upsertWorkflowArtifact(built.data.upsert_payload);
        upsertOutcome = artifactUpsert;
        if (artifactUpsert.error) {
          return this.facadeHermesError('artifact_upsert', artifactUpsert, phaseTrace, publishArtifactId, upsertOutcome);
        }
        setPhase(phaseTrace, 'artifact_upsert', 'succeeded', publishArtifactId);
      } catch (error) {
        return this.facadeCaughtError('artifact_upsert', error, phaseTrace, publishArtifactId, upsertOutcome);
      }
    } else {
      setPhase(phaseTrace, 'asset_preflight', 'skipped');
      setPhase(phaseTrace, 'artifact_build', 'skipped', publishArtifactId);
      setPhase(phaseTrace, 'workflow_run_upsert', 'skipped');
      setPhase(phaseTrace, 'artifact_upsert', 'skipped', publishArtifactId);
    }

    setPhase(phaseTrace, 'publish_validation', 'running', publishArtifactId);
    const validation = await this.validatePublishArtifact({
      account: input.account,
      artifact_id: publishArtifactId,
    });
    if (!validation.success) {
      return fail('publish_validation', validation, 'fix_publish_ready_artifact', 'Publish-ready artifact validation failed');
    }
    if (!validation.data.valid) {
      setPhase(phaseTrace, 'publish_validation', 'failed', publishArtifactId, 'Publish-ready artifact validation failed');
      return createErrorResult(ErrorCode.ARTIFACT_VALIDATION_FAILED, 'Publish-ready artifact validation failed', {
        validation_summary: validation.data,
        phase_trace: phaseTrace,
        publish_artifact_id: publishArtifactId,
        upsert_outcome: upsertOutcome,
      }, {
        next_action: 'fix_publish_ready_artifact',
        remediation_hint: 'Fix validation_errors and retry the facade with the same publish artifact id or a new version.',
        retryable: false,
        current_phase: 'publish_validation',
      });
    }
    setPhase(phaseTrace, 'publish_validation', 'succeeded', publishArtifactId);

    setPhase(phaseTrace, 'draft_create', 'running', publishArtifactId);
    const draft = await this.createDraft({
      account: input.account,
      artifact_id: publishArtifactId,
      idempotency_key: idempotencyKey,
    });
    if (!draft.success) {
      return fail('draft_create', draft, 'inspect_draft_create_error', 'Draft creation failed');
    }
    if (draft.data.status !== 'saved') {
      setPhase(phaseTrace, 'draft_create', 'failed', publishArtifactId, draft.data.error?.message || `Draft status ${draft.data.status}`);
      return createErrorResult(draft.data.error?.code as typeof ErrorCode[keyof typeof ErrorCode] || ErrorCode.WECHAT_API_ERROR, draft.data.error?.message || `Draft status ${draft.data.status}`, {
        draft: draft.data,
        validation_summary: validation.data,
        phase_trace: phaseTrace,
        publish_artifact_id: publishArtifactId,
        upsert_outcome: upsertOutcome,
      }, {
        next_action: draft.data.error?.next_action || 'inspect_draft_status',
        remediation_hint: draft.data.error?.remediation_hint,
        retryable: draft.data.error?.retryable ?? false,
        current_phase: draft.data.error?.current_phase || 'draft_create',
      });
    }
    setPhase(phaseTrace, 'draft_create', 'succeeded', publishArtifactId);

    return createSuccessResult({
      account: input.account,
      source_type: input.source_type,
      idempotency_key: idempotencyKey,
      publish_artifact_id: publishArtifactId,
      current_phase: 'draft_create',
      completed_phases: completedPhases(phaseTrace),
      phase_trace: phaseTrace,
      validation_summary: validation.data,
      upsert_outcome: upsertOutcome,
      draft: draft.data,
    });
  }

  async getDraftStatus(input: GetDraftStatusInput): Promise<Result<GetDraftStatusOutput>> {
    if (!input.job_id && !input.artifact_id) {
      return createErrorResult(
        ErrorCode.INVALID_INPUT,
        'Either job_id or artifact_id must be provided'
      );
    }

    try {
      const job = input.job_id
        ? await this.jobStore.getJobById(input.job_id)
        : await this.jobStore.getJobByArtifactId(input.artifact_id as string);

      if (!job) {
        return createSuccessResult({ found: false });
      }

      return createSuccessResult({
        found: true,
        job_id: job.job_id,
        status: job.status,
        account: job.account,
        artifact_id: job.artifact_id,
        title: job.title,
        media_id: job.media_id,
        error: job.error,
        created_at: job.created_at,
        updated_at: job.updated_at,
      });
    } catch (error) {
      return this.internalError(error);
    }
  }

  async listDrafts(input: ListDraftsInput): Promise<Result<ListDraftsOutput>> {
    const resolved = this.resolveAccountAdapter(input.account, 'draft_batchget');
    if (!resolved.success) {
      return resolved;
    }

    try {
      const adapterClient = this.adapterClientFactory(resolved.data.adapterConfig);
      if (!adapterClient.batchGetDrafts) {
        return createErrorResult(
          ErrorCode.ADAPTER_CAPABILITY_MISSING,
          'WeChat adapter client does not implement draft_batchget',
          { capability: 'draft_batchget' },
          {
            next_action: 'upgrade_wechat_draft_adapter_client',
            remediation_hint: 'Deploy an adapter client build that supports draft batchget before calling wechat_list_drafts.',
            retryable: false,
            current_phase: 'draft_list',
          }
        );
      }
      const response = await adapterClient.batchGetDrafts(input.account, {
        offset: input.offset,
        count: input.count,
        no_content: input.include_content ? 0 : 1,
      });

      return createSuccessResult({
        account: input.account,
        total_count: response.total_count,
        item_count: response.item_count,
        offset: input.offset,
        count: input.count,
        include_content: input.include_content,
        items: (response.item || []).map((item) => {
          const article = item.content?.news_item?.[0] || {};
          const content = input.include_content ? article.content : undefined;
          return {
            media_id: item.media_id,
            update_time: item.update_time,
            title: article.title,
            author: article.author,
            digest: article.digest,
            thumb_media_id: article.thumb_media_id,
            content_source_url: article.content_source_url,
            content_preview: content ? toPreviewText(content) : undefined,
            content,
          };
        }),
      });
    } catch (error) {
      return this.mapOperationalError(error);
    }
  }

  async preflightAsset(input: AssetPreflightInput): Promise<Result<AssetPreflightOutput>> {
    try {
      const preflight = await this.assetSourceLoader.preflight(input);
      return createSuccessResult(preflight);
    } catch (error) {
      return this.internalError(error);
    }
  }

  importArticleMarkdown(
    input: ImportArticleMarkdownInput
  ): Result<ImportArticleMarkdownOutput> {
    try {
      const importer = new MarkdownArticleImporter();
      const validator = new ArticleDocumentValidator();
      const article = importer.import(input);
      const validation = validator.validate(article);

      return createSuccessResult({
        article,
        content_text: input.return_content_text ? JSON.stringify(article) : undefined,
        validation: {
          valid: validation.valid,
          errors: validation.errors,
        },
      });
    } catch (error) {
      return articleDocumentError(error, 'article_import');
    }
  }

  validateArticleDocument(
    input: ValidateArticleDocumentInput
  ): Result<ValidateArticleDocumentOutput> {
    const normalized = normalizeArticleDocumentInput(input.article);
    if (!normalized.success) {
      return normalized;
    }

    const validator = new ArticleDocumentValidator();
    const validation = validator.validate(normalized.data);
    return createSuccessResult({
      valid: validation.valid,
      schema_version: normalized.data.schema_version,
      errors: validation.errors,
      article: input.return_normalized ? normalized.data : undefined,
    });
  }

  renderArticleDocument(
    input: RenderArticleDocumentInputTool
  ): Result<RenderArticleDocumentOutputTool> {
    const normalized = normalizeArticleDocumentInput(input.article);
    if (!normalized.success) {
      return normalized;
    }

    try {
      const article = normalized.data;
      const outputFormat = input.output_format ?? 'html';
      if (outputFormat === 'markdown') {
        const exported = new MarkdownArticleExporter().exportMarkdown(article);
        return createSuccessResult({
          output_format: 'markdown',
          markdown: exported.markdown,
          content_hash: hashContent(exported.markdown),
          content_size_bytes: Buffer.byteLength(exported.markdown, 'utf8'),
          preview_text: toPreviewText(exported.markdown),
          consumed_body_images: [],
          warnings: exported.warnings,
        });
      }

      const styleProfileId = input.style_profile_id || article.style_profile_id || 'yueliang.default';
      const renderer = new WechatArticleDocumentRenderer(getWechatStyleProfile(styleProfileId));
      const rendered = renderer.render({
        article: {
          ...article,
          style_profile_id: styleProfileId,
        },
        include_cover_image: input.include_cover_image ?? false,
      });

      return createSuccessResult({
        output_format: 'html',
        html: rendered.html,
        content_hash: hashContent(rendered.html),
        content_size_bytes: Buffer.byteLength(rendered.html, 'utf8'),
        preview_text: toPreviewText(rendered.html),
        consumed_body_images: rendered.consumed_body_images,
        warnings: [],
      });
    } catch (error) {
      return articleDocumentError(error, 'article_render');
    }
  }

  buildPublishReadyArtifact(
    input: BuildPublishReadyArtifactInput
  ): Result<BuildPublishReadyArtifactOutput> {
    const normalized = normalizeArticleDocumentInput(input.article);
    if (!normalized.success) {
      return normalized;
    }

    try {
      const article = normalized.data;
      const sourceArtifactId = input.source_artifact_id || `${input.artifact_id}:article_document`;
      const source: WorkflowArtifact = {
        artifact_id: sourceArtifactId,
        run_id: input.run_id,
        task_id: input.task_id,
        topic_id: input.topic_id,
        account: input.account,
        stage: 'draft',
        type: 'article_document',
        name: `${article.title} - Article Document`,
        content_hash: hashContent(JSON.stringify(article)),
        content_size_bytes: Buffer.byteLength(JSON.stringify(article), 'utf8'),
        content_preview: article.title,
        content_text: JSON.stringify(article),
        metadata: {
          title: article.title,
          style_profile_id: article.style_profile_id,
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      const built = new ArticleDocumentToWechatArtifactBuilder().build({
        source,
        article,
        style_profile_id: input.style_profile_id,
      });

      return createSuccessResult({
        upsert_payload: {
          artifact_id: input.artifact_id,
          run_id: built.run_id,
          task_id: built.task_id,
          topic_id: built.topic_id,
          account: built.account,
          stage: 'publish_ready',
          type: 'wechat_api_article',
          name: built.name,
          content_hash: built.content_hash,
          content_size_bytes: built.content_size_bytes,
          content_preview: built.content_preview,
          content_text: built.content_text as string,
          metadata: built.metadata,
        },
      });
    } catch (error) {
      return articleDocumentError(error, 'article_build');
    }
  }

  async uploadAsset(input: UploadAssetInput): Promise<Result<UploadAssetOutput>> {
    const resolved = this.resolveAccountAdapter(input.account, 'asset_upload');
    if (!resolved.success) {
      return resolved;
    }

    try {
      if (input.preflight) {
        const preflight = await this.assetSourceLoader.preflight(input);
        if (!preflight.valid) {
          return createErrorResult(
            ErrorCode.INVALID_INPUT,
            'Asset preflight failed',
            { preflight },
            {
              next_action: nextActionFromPreflight(preflight),
              remediation_hint: 'Fix the asset source or transform it according to preflight recommendations, then retry upload.',
              retryable: false,
              current_phase: 'asset_preflight',
            }
          );
        }
      }

      const loadedAsset = await this.assetSourceLoader.load({
        usage: input.usage,
        source_type: input.source_type,
        source: input.source,
        filename: input.filename,
        mime_type: input.mime_type,
      });
      const adapterClient = this.adapterClientFactory(resolved.data.adapterConfig);
      const uploadResponse = await adapterClient.uploadAsset(input.account, {
        usage: input.usage,
        bytes: loadedAsset.bytes,
        filename: loadedAsset.filename,
        mimeType: loadedAsset.mimeType,
      });

      return createSuccessResult({
        account: input.account,
        usage: input.usage,
        source_type: input.source_type,
        filename: loadedAsset.filename,
        mime_type: loadedAsset.mimeType,
        size_bytes: loadedAsset.sizeBytes,
        wechat_url: uploadResponse.wechat_url,
        thumb_media_id: uploadResponse.thumb_media_id,
        created_at: new Date().toISOString(),
      });
    } catch (error) {
      return this.mapOperationalError(error);
    }
  }

  private resolveAccountAdapter(
    account: string,
    requiredCapability?: string
  ): Result<ResolvedAccountAdapter> {
    const accountConfig = this.configLoader.getAccount(account);
    if (!accountConfig) {
      return createErrorResult(
        ErrorCode.ACCOUNT_NOT_FOUND,
        `Account "${account}" not found`
      );
    }

    if (!accountConfig.enabled) {
      return createErrorResult(
        ErrorCode.ACCOUNT_DISABLED,
        `Account "${account}" is disabled`
      );
    }

    const adapterConfig = this.config.wechat_adapter;
    if (requiredCapability && !adapterConfig.capabilities.includes(requiredCapability)) {
      return createErrorResult(
        ErrorCode.ADAPTER_CAPABILITY_MISSING,
        `WeChat adapter does not support ${requiredCapability} capability`
      );
    }

    return createSuccessResult({ accountConfig, adapterConfig });
  }

  private mapOperationalError<T>(error: unknown): Result<T> {
    return mapOperationalErrorToResult<T>(error) || this.internalError(error);
  }

  private facadeHermesError(
    phase: FacadePhase['phase'],
    result: Record<string, unknown>,
    phaseTrace: FacadePhase[],
    publishArtifactId: string,
    upsertOutcome: Record<string, unknown> | undefined
  ): Result<CreateDraftFacadeOutput> {
    const message = typeof result.message === 'string' ? result.message : `Hermes ${phase} failed`;
    setPhase(phaseTrace, phase, 'failed', publishArtifactId, message);
    return createErrorResult(ErrorCode.HERMES_DB_UPSERT_FAILED, message, {
      hermes_error: result,
      phase_trace: phaseTrace,
      publish_artifact_id: publishArtifactId,
      upsert_outcome: upsertOutcome,
    }, {
      next_action: typeof result.next_action === 'string' ? result.next_action : 'inspect_hermes_upsert_error',
      remediation_hint: typeof result.remediation_hint === 'string' ? result.remediation_hint : undefined,
      retryable: typeof result.retryable === 'boolean' ? result.retryable : false,
      current_phase: phase,
    });
  }

  private facadeCaughtError(
    phase: FacadePhase['phase'],
    error: unknown,
    phaseTrace: FacadePhase[],
    publishArtifactId: string,
    upsertOutcome: Record<string, unknown> | undefined
  ): Result<CreateDraftFacadeOutput> {
    const message = error instanceof Error ? error.message : `Hermes ${phase} failed`;
    setPhase(phaseTrace, phase, 'failed', publishArtifactId, message);
    return createErrorResult(ErrorCode.HERMES_DB_UPSERT_FAILED, message, {
      phase_trace: phaseTrace,
      publish_artifact_id: publishArtifactId,
      upsert_outcome: upsertOutcome,
    }, {
      next_action: 'check_hermes_db_connectivity',
      retryable: true,
      current_phase: phase,
    });
  }

  private internalError<T>(error: unknown): Result<T> {
    return createErrorResult(
      ErrorCode.INTERNAL_ERROR,
      error instanceof Error ? error.message : 'Unknown error'
    );
  }
}

function parseHealthProbeInterval(): number {
  const rawValue = process.env.HEALTH_PROBE_INTERVAL_MS;
  if (!rawValue) {
    return 30_000;
  }

  const value = Number.parseInt(rawValue, 10);
  return Number.isInteger(value) && value > 0 ? value : 30_000;
}

async function checkAdapter(adapterConfig: EcsWechatAdapterConfig): Promise<{ ok: boolean; error?: string }> {
  try {
    const client = new WechatAdapterClient(adapterConfig);
    await client.checkHealth();
    return { ok: true };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : 'Unknown adapter health error',
    };
  }
}

function normalizeArticleDocumentInput(
  value: unknown
): Result<ArticleDocumentEnvelope> {
  try {
    const parsed = typeof value === 'string' ? JSON.parse(value) : value;
    const validator = new ArticleDocumentValidator();
    const validation: ArticleDocumentValidationResult = validator.validate(parsed);
    if (!validation.valid) {
      const details = {
        errors: validation.errors.map((error: ArticleDocumentValidationIssue) => ({
          field: error.field,
          issue: error.issue,
        })),
      };
      return createErrorResult(
        ErrorCode.INVALID_INPUT,
        'Invalid article_document',
        details,
        {
          next_action: 'fix_article_document',
          remediation_hint: 'Fix the article_document validation errors and retry.',
          retryable: false,
          current_phase: 'article_validation',
        }
      );
    }

    return createSuccessResult(parsed as ArticleDocumentEnvelope);
  } catch (error) {
    return articleDocumentError(error, 'article_validation');
  }
}

function hashContent(value: string): string {
  return createHash('sha256').update(value).digest('hex');
}

function toPreviewText(value: string): string {
  return value.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim().slice(0, 240);
}

function nextActionFromPreflight(preflight: AssetPreflightOutput): string {
  const firstRecommendation = preflight.recommendations[0];
  if (!firstRecommendation) {
    return 'inspect_asset_preflight';
  }

  switch (firstRecommendation.action) {
    case 'compress':
      return 'compress_or_resize_asset';
    case 'convert_format':
      return 'convert_asset_format';
    case 'use_accepted_path_or_remote_url':
      return 'use_accepted_path_or_remote_url';
    case 'replace_asset':
      return 'replace_asset';
    case 'none':
    default:
      return 'inspect_asset_preflight';
  }
}

function setPhase(
  trace: FacadePhase[],
  phase: FacadePhase['phase'],
  status: FacadePhase['status'],
  artifactId?: string,
  message?: string
): void {
  const existing = trace.find((entry) => entry.phase === phase);
  const next = {
    phase,
    status,
    artifact_id: artifactId,
    message,
  };

  if (existing) {
    Object.assign(existing, next);
    return;
  }

  trace.push(next);
}

function completedPhases(trace: FacadePhase[]): string[] {
  return trace.filter((entry) => entry.status === 'succeeded').map((entry) => entry.phase);
}
