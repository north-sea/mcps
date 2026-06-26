import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import type { EcsWechatAdapterConfig } from '../config/types.js';
import type { WorkflowArtifact, HermesDbClient } from '../hermes/HermesDbClient.js';
import { SQLiteJobStore } from '../store/SQLiteJobStore.js';
import { DraftWorkflow } from './DraftWorkflow.js';

test('DraftWorkflow creates a draft once and returns existing job for duplicate idempotency key', async () => {
  const { store, cleanup } = await createStore();
  const calls = {
    getArtifact: 0,
    checkHealth: 0,
    createDraft: 0,
    upsertLedger: 0,
  };
  const hermesDbClient = {
    async getArtifact() {
      calls.getArtifact += 1;
      return makeArtifact();
    },
    async upsertArticleLedger() {
      calls.upsertLedger += 1;
    },
  } as unknown as HermesDbClient;
  const workflow = new DraftWorkflow({
    adapterClientFactory: () => ({
      async checkHealth() {
        calls.checkHealth += 1;
      },
      async createDraft() {
        calls.createDraft += 1;
        return {
          success: true,
          media_id: 'draft_media_1',
        };
      },
    }),
  });
  const context = {
    account: 'xiaban',
    artifactId: 'artifact_1',
    idempotencyKey: 'idem_workflow_1',
    hermesDbClient,
    adapterConfig: makeAdapterConfig(),
    jobStore: store,
  };

  try {
    const first = await workflow.execute(context);
    const second = await workflow.execute(context);

    assert.equal(first.status, 'saved');
    assert.equal(first.media_id, 'draft_media_1');
    assert.equal(second.job_id, first.job_id);
    assert.equal(second.status, 'saved');
    assert.deepEqual(calls, {
      getArtifact: 1,
      checkHealth: 1,
      createDraft: 1,
      upsertLedger: 1,
    });
  } finally {
    store.close();
    await cleanup();
  }
});

async function createStore(): Promise<{
  store: SQLiteJobStore;
  cleanup: () => Promise<void>;
}> {
  const dir = await mkdtemp(join(tmpdir(), 'wechat-draft-workflow-test-'));
  const store = new SQLiteJobStore({ databasePath: join(dir, 'jobs.db') });
  await store.initialize();

  return {
    store,
    cleanup: () => rm(dir, { recursive: true, force: true }),
  };
}

function makeArtifact(): WorkflowArtifact {
  return {
    artifact_id: 'artifact_1',
    run_id: 'run_1',
    account: 'xiaban',
    stage: 'publish_ready',
    type: 'wechat_api_article',
    name: 'Test Article',
    content_hash: 'hash_1',
    content_size_bytes: 32,
    content_text: '<p>Hello WeChat</p>',
    metadata: {
      publish_ready: true,
      title: 'Test Article',
      cover: {
        thumb_media_id: 'thumb_1',
      },
      wechat_asset_manifest: {
        ready: true,
      },
    },
    created_at: '2026-01-01T00:00:00.000Z',
    updated_at: '2026-01-01T00:00:00.000Z',
  };
}

function makeAdapterConfig(): EcsWechatAdapterConfig {
  return {
    adapter_id: 'test-adapter',
    base_url: 'http://127.0.0.1:3000',
    auth_ref: 'env:WECHAT_ADAPTER_AUTH_TOKEN',
    allowed_accounts: ['xiaban'],
    egress_public_ip: '<REDACTED>',
    network_path: 'tailscale',
    timeout_ms: 1000,
    capabilities: ['check_credentials', 'draft_add', 'asset_upload'],
  };
}
