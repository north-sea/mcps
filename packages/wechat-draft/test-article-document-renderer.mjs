/**
 * Manual tests for canonical article_document rendering.
 */

import {
  ARTICLE_DOCUMENT_SCHEMA_VERSION,
  ArticleDocumentToWechatArtifactBuilder,
  ArticleDocumentValidator,
  MarkdownArticleExporter,
  MarkdownArticleImporter,
  WechatArticleDocumentRenderer,
  getWechatStyleProfile,
} from './dist/render/index.js';
import { ArtifactValidator } from './dist/hermes/index.js';
import { DraftPayloadBuilder } from './dist/wechat/index.js';

let testCount = 0;
let passCount = 0;

function assert(condition, message) {
  testCount++;
  if (!condition) {
    console.error(`FAIL: ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  }
  passCount++;
  console.log(`PASS: ${message}`);
}

function assertThrows(fn, message, expectedText) {
  testCount++;
  try {
    fn();
  } catch (error) {
    const actual = error instanceof Error ? error.message : String(error);
    if (expectedText && !actual.includes(expectedText)) {
      console.error(`FAIL: ${message}: expected "${expectedText}", got "${actual}"`);
      throw error;
    }
    passCount++;
    console.log(`PASS: ${message}`);
    return;
  }
  throw new Error(`Assertion failed: ${message}`);
}

function fixture(overrides = {}) {
  return {
    schema_version: ARTICLE_DOCUMENT_SCHEMA_VERSION,
    title: '结构化正文测试',
    digest: '结构化摘要',
    author: 'mcps',
    style_profile_id: 'yueliang.default',
    content_source_url: 'https://example.com/source',
    cover: {
      thumb_media_id: 'mock-thumb-media-id',
    },
    assets: {
      hero: {
        asset_ref: 'hero',
        wechat_url: 'https://mmbiz.qpic.cn/mock-body1',
        alt: '正文图',
        ready: true,
      },
    },
    doc: {
      type: 'doc',
      content: [
        {
          type: 'heading',
          attrs: { level: 2 },
          content: [{ type: 'text', text: '小标题' }],
        },
        {
          type: 'paragraph',
          content: [
            { type: 'text', text: '正文 ' },
            { type: 'text', text: '重点', marks: [{ type: 'bold' }] },
            {
              type: 'text',
              text: ' 链接',
              marks: [{ type: 'link', attrs: { href: 'https://example.com' } }],
            },
          ],
        },
        {
          type: 'image',
          attrs: { asset_ref: 'hero', alt: '正文图' },
        },
        { type: 'horizontalRule' },
      ],
    },
    ...overrides,
  };
}

const validator = new ArticleDocumentValidator();

{
  const result = validator.validate(fixture());
  assert(result.valid, 'valid article_document passes validator');
}

{
  const result = validator.validate(fixture({ schema_version: 'article_document.unknown' }));
  assert(!result.valid, 'invalid schema_version fails validator');
  assert(result.errors.some((error) => error.field === 'schema_version'), 'schema_version error is structured');
}

{
  const article = fixture({
    doc: {
      type: 'doc',
      content: [{ type: 'unsupportedBlock' }],
    },
  });
  const result = validator.validate(article);
  assert(!result.valid, 'unknown node fails validator');
  assert(result.errors.some((error) => error.field === 'doc'), 'unknown node is reported on doc');
}

{
  const article = fixture({
    doc: {
      type: 'doc',
      content: [
        {
          type: 'paragraph',
          content: [{ type: 'text', text: 'bad mark', marks: [{ type: 'underline' }] }],
        },
      ],
    },
  });
  const result = validator.validate(article);
  assert(!result.valid, 'unknown mark fails validator');
}

{
  const article = fixture({
    doc: {
      type: 'doc',
      content: [{ type: 'image', attrs: { alt: 'missing ref' } }],
    },
  });
  const result = validator.validate(article);
  assert(!result.valid, 'missing image asset_ref fails validator');
  assert(
    result.errors.some((error) => error.field.includes('asset_ref')),
    'missing image asset_ref is diagnosed'
  );
}

{
  const html = new WechatArticleDocumentRenderer(getWechatStyleProfile('yueliang.default')).render({
    article: fixture(),
  }).html;
  assert(html.includes('小标题'), 'renderer keeps heading text');
  assert(html.includes('font-size: 22px'), 'renderer applies profile heading style');
  assert(html.includes('<strong'), 'renderer applies bold mark');
  assert(html.includes('https://mmbiz.qpic.cn/mock-body1'), 'renderer uses uploaded WeChat image URL');
  assert(!html.includes('##'), 'renderer does not leave Markdown heading syntax');
  assert(!html.includes('**'), 'renderer does not leave Markdown bold syntax');
  assert(!html.includes('![]('), 'renderer does not leave Markdown image syntax');
}

{
  const profile = getWechatStyleProfile('xiaban.default');
  assert(profile.account_id === 'xiaban', 'xiaban.default style profile resolves to xiaban account');
  const html = new WechatArticleDocumentRenderer(profile).render({
    article: fixture({ style_profile_id: 'xiaban.default' }),
  }).html;
  assert(html.includes('#207C58'), 'xiaban.default applies production-safe accent color');
}

assertThrows(
  () => getWechatStyleProfile('xiaban.missing'),
  'unknown style profile fails closed',
  'Unknown WeChat style profile'
);

assertThrows(
  () =>
    new WechatArticleDocumentRenderer(getWechatStyleProfile('yueliang.default')).render({
      article: fixture({
        assets: {
          hero: {
            asset_ref: 'hero',
            wechat_url: 'https://example.com/not-wechat.png',
            ready: true,
          },
        },
      }),
    }),
  'renderer rejects non-WeChat image URL',
  'WeChat image URL'
);

const sourceArtifact = {
  artifact_id: 'artifact-article-doc-1',
  run_id: 'run-1',
  account: 'yueliang',
  stage: 'drafted',
  type: 'article_document',
  name: 'article document',
  content_hash: 'mock-content-hash',
  content_size_bytes: 10,
  content_text: JSON.stringify(fixture()),
  metadata: { style_profile_id: 'yueliang.default' },
  created_at: '2026-06-24T00:00:00.000Z',
  updated_at: '2026-06-24T00:00:00.000Z',
};

{
  const artifact = new ArticleDocumentToWechatArtifactBuilder().build({ source: sourceArtifact });
  const validation = new ArtifactValidator().validate(artifact);
  assert(validation.valid, 'generated wechat_api_article passes existing ArtifactValidator');
  assert(artifact.stage === 'publish_ready', 'generated artifact is publish_ready');
  assert(artifact.type === 'wechat_api_article', 'generated artifact type is wechat_api_article');
  assert(
    artifact.metadata.source_article_document_artifact_id === sourceArtifact.artifact_id,
    'generated artifact links source article_document'
  );

  const payload = new DraftPayloadBuilder().buildPayload(artifact);
  assert(payload.success, 'generated artifact can build draft payload');
  assert(payload.payload?.articles[0].thumb_media_id === 'mock-thumb-media-id', 'payload has cover thumb_media_id');
}

{
  const xiabanArtifact = new ArticleDocumentToWechatArtifactBuilder().build({
    source: {
      ...sourceArtifact,
      account: 'xiaban',
      metadata: { style_profile_id: 'xiaban.default' },
      content_text: JSON.stringify(fixture({ style_profile_id: 'xiaban.default' })),
    },
  });
  assert(
    xiabanArtifact.metadata.style_profile_id === 'xiaban.default',
    'builder preserves xiaban.default style profile'
  );
  assert(xiabanArtifact.account === 'xiaban', 'builder preserves xiaban account');
}

{
  const httpArtifact = new ArticleDocumentToWechatArtifactBuilder().build({
    source: {
      ...sourceArtifact,
      content_text: JSON.stringify(
        fixture({
          assets: {
            hero: {
              asset_ref: 'hero',
              wechat_url: 'http://mmbiz.qpic.cn/mock-body1',
              alt: '正文图',
              ready: true,
            },
          },
        })
      ),
    },
  });
  const validation = new ArtifactValidator().validate(httpArtifact);
  assert(validation.valid, 'ArtifactValidator accepts http mmbiz.qpic.cn image URLs returned by uploadimg');
}

{
  const payload = new DraftPayloadBuilder().buildPayload(sourceArtifact);
  assert(!payload.success, 'draft payload builder rejects article_document directly');
  assert(
    payload.errors?.some((error) => error.field === 'type'),
    'direct article_document rejection reports type field'
  );
}

{
  const article = new MarkdownArticleImporter().import({
    markdown: `---
source: legacy
---
# 导入标题

## 小标题

正文 **重点**

![图片里的 **强调** 文本](https://example.com/image.png)

---`,
    author: 'legacy-agent',
    style_profile_id: 'yueliang.default',
    cover: { thumb_media_id: 'mock-thumb-media-id' },
    body_images: [
      {
        asset_ref: 'legacy-image-1',
        wechat_url: 'https://mmbiz.qpic.cn/legacy-body1',
        ready: true,
      },
    ],
    source_markdown_artifact_id: 'artifact-legacy-markdown-1',
  });
  const result = validator.validate(article);
  assert(result.valid, 'Markdown importer creates valid article_document');
  assert(article.title === '导入标题', 'Markdown importer derives H1 title');
  assert(article.doc.type === 'doc', 'Markdown importer creates ProseMirror doc');
  const docJson = JSON.stringify(article.doc);
  assert(!docJson.includes('## 小标题'), 'Markdown importer removes heading marker from structure');
  assert(!docJson.includes('**重点**'), 'Markdown importer removes bold marker from text structure');
  assert(!docJson.includes('!['), 'Markdown importer removes image syntax from structure');
  assert(
    article.assets['legacy-image-1'].alt === '图片里的 强调 文本',
    'Markdown importer strips inline Markdown from image alt'
  );
}

assertThrows(
  () =>
    new MarkdownArticleImporter().import({
      markdown: `# 缺图

![缺图](https://example.com/image.png)`,
      cover: { thumb_media_id: 'mock-thumb-media-id' },
    }),
  'Markdown importer fails closed when image asset is missing',
  'Missing prepared image asset'
);

{
  const article = fixture();
  const exporter = new MarkdownArticleExporter();
  const markdown = exporter.exportMarkdown(article);
  assert(markdown.non_canonical, 'Markdown exporter marks output as non-canonical');
  assert(
    markdown.markdown.includes('non-canonical preview'),
    'Markdown exporter includes non-canonical warning comment'
  );
  assert(markdown.markdown.includes('## 小标题'), 'Markdown exporter includes heading');
  assert(markdown.markdown.includes('**重点**'), 'Markdown exporter includes bold mark');
  assert(markdown.markdown.includes('![正文图](https://mmbiz.qpic.cn/mock-body1)'), 'Markdown exporter includes image alt');

  const html = exporter.exportHtmlPreview(article);
  assert(html.non_canonical, 'HTML preview exporter marks output as non-canonical');
  assert(html.html.includes('non-canonical preview'), 'HTML preview includes non-canonical warning comment');
  assert(html.html.includes('https://mmbiz.qpic.cn/mock-body1'), 'HTML preview renders WeChat image URL');
}

console.log(`\n${passCount}/${testCount} tests passed`);
