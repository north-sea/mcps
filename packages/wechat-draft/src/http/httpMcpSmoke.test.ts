import test from 'node:test';
import assert from 'node:assert/strict';
import type { Server } from 'node:http';
import type { AddressInfo } from 'node:net';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { ConfigLoader } from '../config/index.js';
import type { AccountConfig, EcsWechatAdapterConfig, ServiceConfig } from '../config/types.js';
import type { WorkflowArtifact, HermesDbClient } from '../hermes/index.js';
import { createLogger } from '../logging/index.js';
import { HealthMonitor } from '../service/HealthMonitor.js';
import { WechatDraftService } from '../service/WechatDraftService.js';
import { SQLiteJobStore } from '../store/SQLiteJobStore.js';
import { DraftWorkflow } from '../workflow/DraftWorkflow.js';
import { AssetSourceLoader } from '../wechat/AssetSourceLoader.js';
import { createHttpApp } from './app.js';

test('HTTP MCP smoke calls list accounts and create draft through Streamable HTTP', async () => {
  const context = await createSmokeContext();
  const server = await listen(context.service);
  const address = server.address() as AddressInfo;
  const client = new Client({ name: 'wechat-draft-http-smoke', version: '0.0.0' });
  const transport = new StreamableHTTPClientTransport(
    new URL(`http://127.0.0.1:${address.port}/mcp`),
    {
      requestInit: {
        headers: {
          Authorization: 'Bearer smoke-token',
          'X-Request-Id': 'smoke-request-1',
        },
      },
    }
  );

  try {
    await client.connect(transport);

    const accounts = await client.callTool({
      name: 'wechat_list_accounts',
      arguments: {},
    });
    assert.deepEqual(parseToolData<{ accounts: Array<{ account_id: string }> }>(accounts).accounts, [
      { account_id: 'xiaban', display_name: '下班不躺平', enabled: true, capabilities: ['check_credentials', 'draft_add', 'asset_upload'] },
    ]);

    const firstDraft = await client.callTool({
      name: 'wechat_create_draft',
      arguments: {
        account: 'xiaban',
        artifact_id: 'artifact_1',
        idempotency_key: 'idem_http_smoke',
      },
    });
    const secondDraft = await client.callTool({
      name: 'wechat_create_draft',
      arguments: {
        account: 'xiaban',
        artifact_id: 'artifact_1',
        idempotency_key: 'idem_http_smoke',
      },
    });

    const firstData = parseToolData<{ status: string; media_id?: string; job_id: string }>(firstDraft);
    const secondData = parseToolData<{ status: string; media_id?: string; job_id: string }>(secondDraft);

    assert.equal(firstData.status, 'saved');
    assert.equal(firstData.media_id, 'draft_media_http_smoke');
    assert.equal(secondData.job_id, firstData.job_id);
    const storedJob = await context.store.getJobById(firstData.job_id);
    assert.equal(storedJob?.media_id, 'draft_media_http_smoke');
    assert.equal(storedJob?.status, 'saved');
    assert.equal(context.calls.createDraft, 1);
    assert.equal(context.calls.getArtifact, 1);
  } finally {
    await client.close();
    await closeServer(server);
    context.store.close();
    await context.cleanup();
  }
});

async function listen(service: WechatDraftService): Promise<Server> {
  const app = createHttpApp({
    service,
    authToken: 'smoke-token',
    logger: createLogger({ level: 'silent' }),
  });

  return new Promise((resolve, reject) => {
    const server = app.listen(0, '127.0.0.1', () => resolve(server));
    server.once('error', reject);
  });
}

async function closeServer(server: Server): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

async function createSmokeContext(): Promise<{
  service: WechatDraftService;
  store: SQLiteJobStore;
  cleanup: () => Promise<void>;
  calls: { getArtifact: number; createDraft: number };
}> {
  const dir = await mkdtemp(join(tmpdir(), 'wechat-draft-http-smoke-'));
  const store = new SQLiteJobStore({ databasePath: join(dir, 'jobs.db') });
  await store.initialize();

  const calls = {
    getArtifact: 0,
    createDraft: 0,
  };
  const hermesDbClient = {
    async getArtifact() {
      calls.getArtifact += 1;
      return makeArtifact();
    },
    async upsertArticleLedger() {
      return undefined;
    },
  } as unknown as HermesDbClient;
  const configLoader = createConfigLoader();
  const workflow = new DraftWorkflow({
    adapterClientFactory: () => ({
      async checkHealth() {
        return undefined;
      },
      async createDraft() {
        calls.createDraft += 1;
        return {
          success: true,
          media_id: 'draft_media_http_smoke',
        };
      },
    }),
  });

  return {
    service: new WechatDraftService({
      configLoader,
      config: createServiceConfig(),
      hermesDbClient,
      artifactValidator: {} as never,
      jobStore: store,
      draftWorkflow: workflow,
      assetSourceLoader: new AssetSourceLoader({ assetRoot: dir }),
      healthMonitor: new HealthMonitor({
        runtimePath: dir,
        sqliteCheck: () => store.checkHealth(),
        initialExternalChecks: {
          adapter: { ok: true },
          hermesDb: { ok: true },
        },
      }),
    }),
    store,
    cleanup: () => rm(dir, { recursive: true, force: true }),
    calls,
  };
}

function parseToolData<T>(result: unknown): T {
  assert.ok(result && typeof result === 'object' && 'content' in result, 'Expected MCP content result');
  const content = (result as { content: unknown[] }).content;
  const text = content.find(isTextContent)?.text;
  assert.ok(text, 'Expected text tool result');
  const parsed = JSON.parse(text) as { success: boolean; data?: T; error?: unknown };
  assert.equal(parsed.success, true);
  assert.ok(parsed.data, 'Expected success data');
  return parsed.data;
}

function isTextContent(item: unknown): item is { type: 'text'; text: string } {
  return Boolean(
    item &&
      typeof item === 'object' &&
      (item as { type?: unknown }).type === 'text' &&
      typeof (item as { text?: unknown }).text === 'string'
  );
}

function createConfigLoader(): ConfigLoader {
  const account = createAccountConfig();

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
    accounts: [createAccountConfig()],
    wechat_adapter: createAdapterConfig(),
    credentials: [],
    hermes_db: {
      base_url: 'http://127.0.0.1:8765',
      timeout_ms: 1000,
    },
  };
}

function createAccountConfig(): AccountConfig {
  return {
    account_id: 'xiaban',
    display_name: '下班不躺平',
    enabled: true,
    adapter_account_ref: 'xiaban',
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

function makeArtifact(): WorkflowArtifact {
  return {
    artifact_id: 'artifact_1',
    run_id: 'run_1',
    account: 'xiaban',
    stage: 'publish_ready',
    type: 'wechat_api_article',
    name: 'HTTP Smoke Article',
    content_hash: 'hash_1',
    content_size_bytes: 32,
    content_text: '<p>Hello WeChat</p>',
    metadata: {
      publish_ready: true,
      title: 'HTTP Smoke Article',
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
