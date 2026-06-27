import test from 'node:test';
import assert from 'node:assert/strict';

import { ConfigLoader } from '../config/index.js';
import type { EcsWechatAdapterConfig, ServiceConfig } from '../config/types.js';
import type { HermesDbClient } from '../hermes/index.js';
import { ARTICLE_DOCUMENT_SCHEMA_VERSION, type ArticleDocumentEnvelope } from '../render/index.js';
import { ErrorCode } from '../schemas/index.js';
import type { DraftJobStore } from '../store/index.js';
import type { DraftWorkflow } from '../workflow/index.js';
import { AssetSourceLoader } from '../wechat/AssetSourceLoader.js';
import { WechatDraftService } from './WechatDraftService.js';

test('WechatDraftService.importArticleMarkdown converts markdown to article_document', () => {
  const service = createArticleDocumentService();

  const result = service.importArticleMarkdown({
    markdown: '# Imported Title\n\nHello **world**.\n\n![Chart](chart.png)',
    body_images: [
      {
        asset_ref: 'img_1',
        wechat_url: 'https://mmbiz.qpic.cn/chart.png',
        ready: true,
      },
    ],
    return_content_text: true,
  });

  assert.equal(result.success, true);
  assert.equal(result.success ? result.data.article.schema_version : undefined, ARTICLE_DOCUMENT_SCHEMA_VERSION);
  assert.equal(result.success ? result.data.article.title : undefined, 'Imported Title');
  assert.equal(result.success ? result.data.article.assets?.img_1?.alt : undefined, 'Chart');
  assert.equal(result.success ? JSON.parse(result.data.content_text as string).title : undefined, 'Imported Title');
});

test('WechatDraftService.importArticleMarkdown returns remediation for missing image assets', () => {
  const service = createArticleDocumentService();

  const result = service.importArticleMarkdown({
    markdown: '# Imported Title\n\n![Chart](chart.png)',
    return_content_text: false,
  });

  assert.equal(result.success, false);
  assert.equal(result.success ? undefined : result.error.code, ErrorCode.INVALID_INPUT);
  assert.equal(result.success ? undefined : result.error.next_action, 'prepare_body_image_assets');
  assert.equal(result.success ? undefined : result.error.current_phase, 'article_import');
});

test('WechatDraftService.validateArticleDocument accepts objects and rejects invalid JSON', () => {
  const service = createArticleDocumentService();
  const article = makeArticleDocument();

  const valid = service.validateArticleDocument({
    article: JSON.stringify(article),
    return_normalized: true,
  });
  const invalid = service.validateArticleDocument({
    article: '{not json',
    return_normalized: false,
  });

  assert.equal(valid.success, true);
  assert.equal(valid.success ? valid.data.valid : undefined, true);
  assert.equal(valid.success ? valid.data.article?.title : undefined, article.title);
  assert.equal(invalid.success, false);
  assert.equal(invalid.success ? undefined : invalid.error.next_action, 'fix_article_document_json');
});

test('WechatDraftService.renderArticleDocument returns HTML and consumed image refs', () => {
  const service = createArticleDocumentService();

  const result = service.renderArticleDocument({
    article: makeArticleDocument(),
    output_format: 'html',
    include_cover_image: false,
  });

  assert.equal(result.success, true);
  assert.match(result.success ? result.data.html as string : '', /Hello/);
  assert.match(result.success ? result.data.html as string : '', /https:\/\/mmbiz\.qpic\.cn\/body\.png/);
  assert.deepEqual(result.success ? result.data.consumed_body_images : [], [
    { asset_ref: 'img_1', wechat_url: 'https://mmbiz.qpic.cn/body.png' },
  ]);
  assert.equal(result.success ? result.data.output_format : undefined, 'html');
  assert.equal(result.success ? result.data.content_hash.length : undefined, 64);
});

test('WechatDraftService.renderArticleDocument returns remediation for missing body image URL', () => {
  const service = createArticleDocumentService();
  const article = makeArticleDocument();
  article.assets = {
    img_1: {
      asset_ref: 'img_1',
      ready: true,
    },
  };

  const result = service.renderArticleDocument({
    article,
    output_format: 'html',
    include_cover_image: false,
  });

  assert.equal(result.success, false);
  assert.equal(result.success ? undefined : result.error.next_action, 'upload_body_images');
  assert.equal(result.success ? undefined : result.error.current_phase, 'article_render');
});

test('WechatDraftService.buildPublishReadyArtifact returns hermes upsert payload', () => {
  const service = createArticleDocumentService();

  const result = service.buildPublishReadyArtifact({
    article: makeArticleDocument(),
    artifact_id: 'artifact_publish_ready_1',
    run_id: 'run_1',
    account: 'xiaban',
  });

  assert.equal(result.success, true);
  const payload = result.success ? result.data.upsert_payload : undefined;
  assert.equal(payload?.artifact_id, 'artifact_publish_ready_1');
  assert.equal(payload?.stage, 'publish_ready');
  assert.equal(payload?.type, 'wechat_api_article');
  assert.match(payload?.content_text ?? '', /Hello/);
  assert.equal((payload?.metadata.cover as { thumb_media_id?: string } | undefined)?.thumb_media_id, 'thumb_media_1');
  assert.equal(payload?.content_hash.length, 64);
});

test('WechatDraftService.buildPublishReadyArtifact returns remediation for missing cover thumb', () => {
  const service = createArticleDocumentService();
  const article = makeArticleDocument();
  article.cover = undefined;

  const result = service.buildPublishReadyArtifact({
    article,
    artifact_id: 'artifact_publish_ready_1',
    run_id: 'run_1',
    account: 'xiaban',
  });

  assert.equal(result.success, false);
  assert.equal(result.success ? undefined : result.error.next_action, 'upload_cover_image');
  assert.equal(result.success ? undefined : result.error.current_phase, 'article_build');
});

function makeArticleDocument(): ArticleDocumentEnvelope {
  return {
    schema_version: ARTICLE_DOCUMENT_SCHEMA_VERSION,
    title: 'Article Tool Test',
    digest: 'Short digest',
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
          content: [{ type: 'text', text: 'Hello article document.' }],
        },
        {
          type: 'image',
          attrs: { asset_ref: 'img_1', alt: 'Body image' },
        },
      ],
    },
  };
}

function createArticleDocumentService(): WechatDraftService {
  return new WechatDraftService({
    configLoader: createConfigLoader(),
    config: createServiceConfig(),
    hermesDbClient: {} as HermesDbClient,
    artifactValidator: {} as never,
    jobStore: {} as DraftJobStore,
    draftWorkflow: {} as DraftWorkflow,
    assetSourceLoader: new AssetSourceLoader(),
  });
}

function createConfigLoader(): ConfigLoader {
  return {
    getAccount: () => undefined,
    getWechatAdapter: () => createAdapterConfig(),
    getAllAccounts: () => [],
    getEnabledAccounts: () => [],
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
