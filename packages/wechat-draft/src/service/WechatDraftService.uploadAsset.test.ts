import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { ConfigLoader } from '../config/index.js';
import type { AccountConfig, EcsWechatAdapterConfig, ServiceConfig } from '../config/types.js';
import type { HermesDbClient } from '../hermes/index.js';
import { ErrorCode } from '../schemas/index.js';
import type { DraftJobStore } from '../store/index.js';
import type { DraftWorkflow } from '../workflow/index.js';
import { AssetSourceLoader } from '../wechat/AssetSourceLoader.js';
import { AdapterAuthError } from '../wechat/WechatAdapterClient.js';
import { WechatDraftService } from './WechatDraftService.js';

test('WechatDraftService.listAccounts returns account constraints', async () => {
  const { service, cleanup } = await createUploadService();

  try {
    const result = service.listAccounts();

    assert.equal(result.success, true);
    const account = result.success ? result.data.accounts[0] : undefined;
    assert.equal(account?.account_id, 'xiaban');
    assert.equal(account?.constraints?.assets.body_image.max_bytes, 1024 * 1024);
    assert.deepEqual(account?.constraints?.assets.body_image.source_types, ['local_path', 'remote_url']);
    assert.equal(account?.constraints?.assets.cover_image.max_bytes, 64 * 1024);
    assert.equal(account?.constraints?.assets.cover_image.media_type, 'thumb');
    assert.equal(account?.constraints?.assets.local_path.enabled, true);
  } finally {
    await cleanup();
  }
});

test('WechatDraftService.uploadAsset returns body image URLs and cover thumb media ids', async () => {
  const { service, writeAsset, cleanup, adapterCalls } = await createUploadService();

  try {
    await writeAsset('body.png', Buffer.from([1, 2, 3]));
    await writeAsset('cover.jpg', Buffer.from([1, 2, 3]));

    const bodyResult = await service.uploadAsset({
      account: 'xiaban',
      usage: 'body_image',
      source_type: 'local_path',
      source: 'body.png',
    });
    const coverResult = await service.uploadAsset({
      account: 'xiaban',
      usage: 'cover_image',
      source_type: 'local_path',
      source: 'cover.jpg',
    });

    assert.equal(bodyResult.success, true);
    assert.equal(bodyResult.success ? bodyResult.data.wechat_url : undefined, 'https://mmbiz.qpic.cn/body.png');
    assert.equal(coverResult.success, true);
    assert.equal(coverResult.success ? coverResult.data.thumb_media_id : undefined, 'thumb_media_1');
    assert.deepEqual(adapterCalls.map((call) => call.usage), ['body_image', 'cover_image']);
  } finally {
    await cleanup();
  }
});

test('WechatDraftService.uploadAsset maps adapter auth failures', async () => {
  const { service, writeAsset, cleanup } = await createUploadService({
    uploadAsset: async () => {
      throw new AdapterAuthError('Adapter authentication failed');
    },
  });

  try {
    await writeAsset('body.png', Buffer.from([1, 2, 3]));

    const result = await service.uploadAsset({
      account: 'xiaban',
      usage: 'body_image',
      source_type: 'local_path',
      source: 'body.png',
    });

    assert.equal(result.success, false);
    assert.equal(result.success ? undefined : result.error.code, ErrorCode.ADAPTER_AUTH_FAILED);
  } finally {
    await cleanup();
  }
});

test('WechatDraftService.uploadAsset returns asset_size_exceeded before adapter upload', async () => {
  const { service, writeAsset, cleanup, adapterCalls } = await createUploadService();

  try {
    await writeAsset('large.jpg', Buffer.alloc(64 * 1024 + 1));

    const result = await service.uploadAsset({
      account: 'xiaban',
      usage: 'cover_image',
      source_type: 'local_path',
      source: 'large.jpg',
    });

    assert.equal(result.success, false);
    assert.equal(result.success ? undefined : result.error.code, ErrorCode.ASSET_SIZE_EXCEEDED);
    assert.equal(adapterCalls.length, 0);
  } finally {
    await cleanup();
  }
});

test('WechatDraftService.preflightAsset returns diagnostics without adapter upload', async () => {
  const { service, writeAsset, cleanup, adapterCalls } = await createUploadService();

  try {
    await writeAsset('large.jpg', Buffer.alloc(64 * 1024 + 1));

    const result = await service.preflightAsset({
      usage: 'cover_image',
      source_type: 'local_path',
      source: 'large.jpg',
    });

    assert.equal(result.success, true);
    assert.equal(result.success ? result.data.valid : undefined, false);
    assert.equal(result.success ? result.data.recommendations[0]?.action : undefined, 'compress');
    assert.equal(adapterCalls.length, 0);
  } finally {
    await cleanup();
  }
});

test('WechatDraftService.uploadAsset preflight gate skips adapter on invalid asset', async () => {
  const { service, writeAsset, cleanup, adapterCalls } = await createUploadService();

  try {
    await writeAsset('large.jpg', Buffer.alloc(64 * 1024 + 1));

    const result = await service.uploadAsset({
      account: 'xiaban',
      usage: 'cover_image',
      source_type: 'local_path',
      source: 'large.jpg',
      preflight: true,
    });

    assert.equal(result.success, false);
    assert.equal(result.success ? undefined : result.error.code, ErrorCode.INVALID_INPUT);
    assert.equal(result.success ? undefined : result.error.next_action, 'compress_or_resize_asset');
    assert.equal(
      result.success ? undefined : (result.error.details?.preflight as { valid?: boolean }).valid,
      false
    );
    assert.equal(adapterCalls.length, 0);
  } finally {
    await cleanup();
  }
});

test('WechatDraftService.uploadAsset preflight gate allows valid upload', async () => {
  const { service, writeAsset, cleanup, adapterCalls } = await createUploadService();

  try {
    await writeAsset('body.png', Buffer.from([1, 2, 3]));

    const result = await service.uploadAsset({
      account: 'xiaban',
      usage: 'body_image',
      source_type: 'local_path',
      source: 'body.png',
      preflight: true,
    });

    assert.equal(result.success, true);
    assert.equal(result.success ? result.data.wechat_url : undefined, 'https://mmbiz.qpic.cn/body.png');
    assert.equal(adapterCalls.length, 1);
  } finally {
    await cleanup();
  }
});

async function createUploadService(overrides: {
  uploadAsset?: UploadAssetFn;
} = {}): Promise<{
  service: WechatDraftService;
  writeAsset: (filename: string, content: Buffer) => Promise<void>;
  adapterCalls: Array<{ usage: 'body_image' | 'cover_image'; filename: string }>;
  cleanup: () => Promise<void>;
}> {
  const assetRoot = await mkdtemp(join(tmpdir(), 'wechat-draft-upload-service-'));
  const adapterCalls: Array<{ usage: 'body_image' | 'cover_image'; filename: string }> = [];
  const uploadAsset: UploadAssetFn =
    overrides.uploadAsset ||
    (async (_account, request) => {
      adapterCalls.push({ usage: request.usage, filename: request.filename });
      return request.usage === 'body_image'
        ? { success: true, wechat_url: 'https://mmbiz.qpic.cn/body.png' }
        : { success: true, thumb_media_id: 'thumb_media_1' };
    });

  return {
    service: new WechatDraftService({
      configLoader: createConfigLoader(),
      config: createServiceConfig(),
      hermesDbClient: {} as HermesDbClient,
      artifactValidator: {} as never,
      jobStore: {} as DraftJobStore,
      draftWorkflow: {} as DraftWorkflow,
      assetSourceLoader: new AssetSourceLoader({ assetRoot }),
      adapterClientFactory: () => ({ uploadAsset }),
    }),
    writeAsset: (filename, content) => writeFile(join(assetRoot, filename), content),
    adapterCalls,
    cleanup: () => rm(assetRoot, { recursive: true, force: true }),
  };
}

type UploadAssetFn = (
  account: string,
  request: {
    usage: 'body_image' | 'cover_image';
    bytes: Uint8Array;
    filename: string;
    mimeType: string;
  }
) => Promise<{ success: boolean; wechat_url?: string; thumb_media_id?: string }>;

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
    accounts: [],
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
