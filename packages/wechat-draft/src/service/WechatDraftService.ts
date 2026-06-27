import { ConfigLoader } from '../config/index.js';
import { HermesDbClient, ArtifactValidator } from '../hermes/index.js';
import { SQLiteJobStore, type DraftJobStore } from '../store/index.js';
import { DraftWorkflow } from '../workflow/index.js';
import { AssetSourceLoader } from '../wechat/AssetSourceLoader.js';
import { WechatAdapterClient, type AdapterUploadAssetResponse } from '../wechat/WechatAdapterClient.js';
import { mapOperationalErrorToResult } from './errorMapping.js';
import { HealthMonitor, type HealthSnapshot } from './HealthMonitor.js';
import {
  type CreateDraftInput,
  type CreateDraftOutput,
  type GetDraftStatusInput,
  type GetDraftStatusOutput,
  type ListAccountsInput,
  type ListAccountsOutput,
  type Result,
  type UploadAssetInput,
  type UploadAssetOutput,
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

  async uploadAsset(input: UploadAssetInput): Promise<Result<UploadAssetOutput>> {
    const resolved = this.resolveAccountAdapter(input.account, 'asset_upload');
    if (!resolved.success) {
      return resolved;
    }

    try {
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
