import test from 'node:test';
import assert from 'node:assert/strict';

import { ConfigLoader } from '../config/index.js';
import type { AccountConfig, EcsWechatAdapterConfig, ServiceConfig } from '../config/types.js';
import type { HermesDbClient, WorkflowArtifact } from '../hermes/index.js';
import { ARTICLE_DOCUMENT_SCHEMA_VERSION, type ArticleDocumentEnvelope } from '../render/index.js';
import { ErrorCode } from '../schemas/index.js';
import type { DraftJobStore } from '../store/index.js';
import type { DraftWorkflow } from '../workflow/index.js';
import { AssetSourceLoader } from '../wechat/AssetSourceLoader.js';
import { WechatDraftService } from './WechatDraftService.js';

test('WechatDraftService.createDraftFacade creates a draft from an existing publish_ready artifact', async () => {
  const { service, calls } = createFacadeService();

  const result = await service.createDraftFacade({
    source_type: 'publish_ready_artifact',
    account: 'xiaban',
    artifact_id: 'artifact_1',
    idempotency_key: 'idem_1',
  });

  assert.equal(result.success, true);
  assert.equal(result.success ? result.data.publish_artifact_id : undefined, 'artifact_1');
  assert.equal(result.success ? result.data.draft?.status : undefined, 'saved');
  assert.equal(result.success ? result.data.idempotency_key : undefined, 'idem_1');
  assert.deepEqual(
    result.success ? result.data.phase_trace.filter((phase) => phase.status === 'succeeded').map((phase) => phase.phase) : [],
    ['input_validation', 'publish_validation', 'draft_create']
  );
  assert.equal(calls.getArtifact, 1);
  assert.equal(calls.createDraft, 1);
  assert.equal(calls.upsertWorkflowRun, 0);
  assert.equal(calls.upsertWorkflowArtifact, 0);
});

test('WechatDraftService.createDraftFacade stops before draft creation when publish_ready validation fails', async () => {
  const { service, calls } = createFacadeService({
    validation: { valid: false, errors: [{ field: 'stage', issue: 'bad stage', severity: 'error' }], warnings: [] },
  });

  const result = await service.createDraftFacade({
    source_type: 'publish_ready_artifact',
    account: 'xiaban',
    artifact_id: 'artifact_1',
  });

  assert.equal(result.success, false);
  assert.equal(result.success ? undefined : result.error.code, ErrorCode.ARTIFACT_VALIDATION_FAILED);
  assert.equal(result.success ? undefined : result.error.current_phase, 'publish_validation');
  assert.equal(result.success ? undefined : result.error.next_action, 'fix_publish_ready_artifact');
  assert.equal(calls.createDraft, 0);
});

test('WechatDraftService.createDraftFacade preserves non-saved draft remediation details', async () => {
  const { service } = createFacadeService({
    draftJob: {
      job_id: 'job_operator_action',
      status: 'needs_operator_action',
      account: 'xiaban',
      artifact_id: 'artifact_1',
      title: 'Facade Article',
      created_at: '2026-01-01T00:00:00.000Z',
      error: {
        code: ErrorCode.WECHAT_API_ERROR,
        message: 'operator review required',
        next_action: 'open_operator_console',
        retryable: false,
        current_phase: 'draft_creating',
      },
    },
  });

  const result = await service.createDraftFacade({
    source_type: 'publish_ready_artifact',
    account: 'xiaban',
    artifact_id: 'artifact_1',
    idempotency_key: 'idem_operator_action',
  });

  assert.equal(result.success, false);
  assert.equal(result.success ? undefined : result.error.code, ErrorCode.WECHAT_API_ERROR);
  assert.equal(result.success ? undefined : result.error.current_phase, 'draft_creating');
  assert.equal(result.success ? undefined : result.error.next_action, 'open_operator_console');
  assert.equal(
    result.success ? undefined : (result.error.details?.draft as { status?: string }).status,
    'needs_operator_action'
  );
});

test('WechatDraftService.createDraftFacade builds, upserts, validates, and creates from article_document', async () => {
  const { service, calls } = createFacadeService();

  const result = await service.createDraftFacade({
    source_type: 'article_document',
    account: 'xiaban',
    run_id: 'run_1',
    publish_artifact_id: 'publish_ready_1',
    article: makeArticleDocument(),
    idempotency_key: 'idem_article',
  });

  assert.equal(result.success, true);
  assert.equal(result.success ? result.data.publish_artifact_id : undefined, 'publish_ready_1');
  assert.equal(result.success ? result.data.upsert_outcome?.artifact_id : undefined, 'publish_ready_1');
  assert.equal(result.success ? result.data.draft?.status : undefined, 'saved');
  assert.deepEqual(
    result.success ? result.data.phase_trace.map((phase) => [phase.phase, phase.status]) : [],
    [
      ['input_validation', 'succeeded'],
      ['asset_preflight', 'skipped'],
      ['artifact_build', 'succeeded'],
      ['workflow_run_upsert', 'succeeded'],
      ['artifact_upsert', 'succeeded'],
      ['publish_validation', 'succeeded'],
      ['draft_create', 'succeeded'],
    ]
  );
  assert.equal(calls.upsertWorkflowRun, 1);
  assert.equal(calls.upsertWorkflowArtifact, 1);
  assert.equal(calls.createDraft, 1);
});

test('WechatDraftService.createDraftFacade returns article_document remediation before Hermes writes', async () => {
  const { service, calls } = createFacadeService();
  const article = makeArticleDocument();
  article.cover = undefined;

  const result = await service.createDraftFacade({
    source_type: 'article_document',
    account: 'xiaban',
    run_id: 'run_1',
    publish_artifact_id: 'publish_ready_1',
    article,
  });

  assert.equal(result.success, false);
  assert.equal(result.success ? undefined : result.error.current_phase, 'article_build');
  assert.equal(result.success ? undefined : result.error.next_action, 'upload_cover_image');
  assert.equal(calls.upsertWorkflowRun, 0);
  assert.equal(calls.upsertWorkflowArtifact, 0);
  assert.equal(calls.createDraft, 0);
});

test('WechatDraftService.createDraftFacade preserves Hermes remediation on artifact upsert conflict', async () => {
  const { service, calls } = createFacadeService({
    artifactUpsert: {
      error: 'artifact_id_conflict',
      message: 'artifact id already exists with different content_hash',
      next_action: 'create_new_artifact_version_or_use_existing_artifact',
      retryable: false,
    },
  });

  const result = await service.createDraftFacade({
    source_type: 'article_document',
    account: 'xiaban',
    run_id: 'run_1',
    publish_artifact_id: 'publish_ready_1',
    article: makeArticleDocument(),
  });

  assert.equal(result.success, false);
  assert.equal(result.success ? undefined : result.error.code, ErrorCode.HERMES_DB_UPSERT_FAILED);
  assert.equal(result.success ? undefined : result.error.current_phase, 'artifact_upsert');
  assert.equal(
    result.success ? undefined : result.error.next_action,
    'create_new_artifact_version_or_use_existing_artifact'
  );
  assert.equal(calls.upsertWorkflowRun, 1);
  assert.equal(calls.upsertWorkflowArtifact, 1);
  assert.equal(calls.createDraft, 0);
});

function createFacadeService(overrides: {
  validation?: { valid: boolean; errors: Array<Record<string, unknown>>; warnings: Array<Record<string, unknown>> };
  artifactUpsert?: Record<string, unknown>;
  draftJob?: Record<string, unknown>;
} = {}): { service: WechatDraftService; calls: Record<string, number> } {
  const calls = {
    getArtifact: 0,
    upsertWorkflowRun: 0,
    upsertWorkflowArtifact: 0,
    createDraft: 0,
  };
  const hermesDbClient = {
    async getArtifact(artifactId: string) {
      calls.getArtifact += 1;
      return makePublishArtifact(artifactId);
    },
    async upsertWorkflowRun(input: Record<string, unknown>) {
      calls.upsertWorkflowRun += 1;
      return { created: true, run_id: input.run_id };
    },
    async upsertWorkflowArtifact(input: Record<string, unknown>) {
      calls.upsertWorkflowArtifact += 1;
      if (overrides.artifactUpsert) {
        return overrides.artifactUpsert;
      }
      return { created: true, artifact_id: input.artifact_id };
    },
    async upsertArticleLedger() {
      return undefined;
    },
  } as unknown as HermesDbClient;
  const artifactValidator = {
    validate() {
      return overrides.validation || { valid: true, errors: [], warnings: [] };
    },
  };
  const draftWorkflow = {
    async execute(input: { account: string; artifactId: string; idempotencyKey: string }) {
      calls.createDraft += 1;
      return overrides.draftJob || {
        job_id: `job_${input.idempotencyKey}`,
        status: 'saved',
        account: input.account,
        artifact_id: input.artifactId,
        title: 'Facade Article',
        media_id: 'draft_media_1',
        created_at: '2026-01-01T00:00:00.000Z',
      };
    },
  } as unknown as DraftWorkflow;

  return {
    service: new WechatDraftService({
      configLoader: createConfigLoader(),
      config: createServiceConfig(),
      hermesDbClient,
      artifactValidator: artifactValidator as never,
      jobStore: {} as DraftJobStore,
      draftWorkflow,
      assetSourceLoader: new AssetSourceLoader(),
    }),
    calls,
  };
}

function makeArticleDocument(): ArticleDocumentEnvelope {
  return {
    schema_version: ARTICLE_DOCUMENT_SCHEMA_VERSION,
    title: 'Facade Article',
    digest: 'Facade digest',
    author: 'Tester',
    style_profile_id: 'xiaban.default',
    cover: {
      thumb_media_id: 'thumb_media_1',
      alt: 'Cover',
    },
    assets: {
      img_1: {
        asset_ref: 'img_1',
        wechat_url: 'https://mmbiz.qpic.cn/body.png',
        alt: 'Body image',
        ready: true,
      },
    },
    doc: {
      type: 'doc',
      content: [
        {
          type: 'paragraph',
          content: [{ type: 'text', text: 'Hello facade.' }],
        },
        {
          type: 'image',
          attrs: { asset_ref: 'img_1', alt: 'Body image' },
        },
      ],
    },
  };
}

function makePublishArtifact(artifactId: string): WorkflowArtifact {
  return {
    artifact_id: artifactId,
    run_id: 'run_1',
    account: 'xiaban',
    stage: 'publish_ready',
    type: 'wechat_api_article',
    name: 'Facade Article',
    content_hash: 'hash_1',
    content_size_bytes: 32,
    content_text: '<p>Hello facade.</p>',
    metadata: {
      publish_ready: true,
      title: 'Facade Article',
      cover: {
        thumb_media_id: 'thumb_media_1',
      },
      wechat_asset_manifest: {
        ready: true,
      },
    },
    created_at: '2026-01-01T00:00:00.000Z',
    updated_at: '2026-01-01T00:00:00.000Z',
  };
}

function createConfigLoader(): ConfigLoader {
  const account: AccountConfig = {
    account_id: 'xiaban',
    display_name: '下班不躺平',
    enabled: true,
    adapter_account_ref: 'xiaban',
  };

  return {
    getAccount: (accountId: string) => (accountId === account.account_id ? account : undefined),
    getWechatAdapter: () => createAdapterConfig(),
    getAllAccounts: () => [account],
    getEnabledAccounts: () => [account],
    load: () => createServiceConfig(),
  } as unknown as ConfigLoader;
}

function createServiceConfig(): ServiceConfig {
  return {
    accounts: [createConfigLoader().getAllAccounts()[0]],
    wechat_adapter: createAdapterConfig(),
    credentials: [],
    hermes_db: {
      base_url: 'http://127.0.0.1:8765',
      timeout_ms: 1000,
    },
  };
}

function createAdapterConfig(): EcsWechatAdapterConfig {
  return {
    base_url: 'http://127.0.0.1:3000',
    auth_ref: 'env:WECHAT_ADAPTER_AUTH_TOKEN',
    egress_public_ip: '<REDACTED>',
    network_path: 'tailscale',
    timeout_ms: 1000,
    capabilities: ['check_credentials', 'draft_add', 'asset_upload'],
  };
}
