import test from 'node:test';
import assert from 'node:assert/strict';

import { ConfigLoader } from '../config/index.js';
import type { AccountConfig, EcsWechatAdapterConfig, ServiceConfig } from '../config/types.js';
import type { HermesDbClient } from '../hermes/index.js';
import { ErrorCode } from '../schemas/index.js';
import type { DraftJobStore } from '../store/index.js';
import type { DraftWorkflow } from '../workflow/index.js';
import { AssetSourceLoader } from '../wechat/AssetSourceLoader.js';
import { WechatDraftService } from './WechatDraftService.js';

test('WechatDraftService.listDrafts returns bounded summaries by default', async () => {
  const { service, calls } = createListDraftsService();

  const result = await service.listDrafts({
    account: 'xiaban',
    offset: 0,
    count: 20,
    include_content: false,
  });

  assert.equal(result.success, true);
  const item = result.success ? result.data.items[0] : undefined;
  assert.equal(result.success ? result.data.total_count : undefined, 1);
  assert.equal(item?.media_id, 'draft_media_1');
  assert.equal(item?.title, 'Remote Draft');
  assert.equal(item?.thumb_media_id, 'thumb_1');
  assert.equal(item?.content, undefined);
  assert.equal(item?.content_preview, undefined);
  assert.deepEqual(calls[0], { account: 'xiaban', offset: 0, count: 20, no_content: 1 });
});

test('WechatDraftService.listDrafts includes content only when requested', async () => {
  const { service, calls } = createListDraftsService();

  const result = await service.listDrafts({
    account: 'xiaban',
    offset: 0,
    count: 1,
    include_content: true,
  });

  assert.equal(result.success, true);
  const item = result.success ? result.data.items[0] : undefined;
  assert.equal(item?.content, '<p>Hello <strong>draft</strong></p>');
  assert.equal(item?.content_preview, 'Hello draft');
  assert.deepEqual(calls[0], { account: 'xiaban', offset: 0, count: 1, no_content: 0 });
});

test('WechatDraftService.listDrafts returns capability remediation when adapter lacks batchget', async () => {
  const { service, calls } = createListDraftsService({
    capabilities: ['check_credentials', 'draft_add', 'asset_upload'],
  });

  const result = await service.listDrafts({
    account: 'xiaban',
    offset: 0,
    count: 20,
    include_content: false,
  });

  assert.equal(result.success, false);
  assert.equal(result.success ? undefined : result.error.code, ErrorCode.ADAPTER_CAPABILITY_MISSING);
  assert.equal(calls.length, 0);
});

function createListDraftsService(options: {
  capabilities?: string[];
} = {}): { service: WechatDraftService; calls: Array<Record<string, unknown>> } {
  const calls: Array<Record<string, unknown>> = [];
  const capabilities = options.capabilities || ['check_credentials', 'draft_add', 'draft_batchget', 'asset_upload'];

  return {
    service: new WechatDraftService({
      configLoader: createConfigLoader(capabilities),
      config: createServiceConfig(capabilities),
      hermesDbClient: {} as HermesDbClient,
      artifactValidator: {} as never,
      jobStore: {} as DraftJobStore,
      draftWorkflow: {} as DraftWorkflow,
      assetSourceLoader: new AssetSourceLoader(),
      adapterClientFactory: () => ({
        async batchGetDrafts(account, request) {
          calls.push({ account, ...request });
          return {
            success: true,
            total_count: 1,
            item_count: 1,
            item: [
              {
                media_id: 'draft_media_1',
                update_time: 1780000000,
                content: {
                  news_item: [
                    {
                      title: 'Remote Draft',
                      author: 'Tester',
                      digest: 'Digest',
                      content: '<p>Hello <strong>draft</strong></p>',
                      content_source_url: 'https://example.com/source',
                      thumb_media_id: 'thumb_1',
                    },
                  ],
                },
              },
            ],
          };
        },
        async uploadAsset() {
          throw new Error('uploadAsset should not be called');
        },
      }),
    }),
    calls,
  };
}

function createConfigLoader(capabilities: string[]): ConfigLoader {
  const account: AccountConfig = {
    account_id: 'xiaban',
    display_name: '下班不躺平',
    enabled: true,
    adapter_account_ref: 'xiaban',
  };

  return {
    getAccount: (accountId: string) => (accountId === account.account_id ? account : undefined),
    getWechatAdapter: () => createAdapterConfig(capabilities),
    getAllAccounts: () => [account],
    getEnabledAccounts: () => [account],
    load: () => createServiceConfig(capabilities),
  } as unknown as ConfigLoader;
}

function createServiceConfig(capabilities: string[]): ServiceConfig {
  return {
    accounts: [],
    wechat_adapter: createAdapterConfig(capabilities),
    credentials: [],
    hermes_db: {
      base_url: 'http://127.0.0.1:8765',
      timeout_ms: 1000,
    },
  };
}

function createAdapterConfig(capabilities: string[]): EcsWechatAdapterConfig {
  return {
    base_url: 'http://127.0.0.1:3000',
    auth_ref: 'env:WECHAT_ADAPTER_AUTH_TOKEN',
    egress_public_ip: '<REDACTED>',
    network_path: 'tailscale',
    timeout_ms: 1000,
    capabilities,
  };
}
