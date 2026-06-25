# Canonical Article Artifact

`article_document` is the canonical body format for the new WeChat article pipeline. Markdown is only a legacy import and human-readable export format.

## Boundary

- Producers save structured `article_document.tiptap.v1` JSON.
- The renderer validates the ProseMirror/Tiptap JSON allowlist and creates a separate `wechat_api_article`.
- `wechat_create_draft` and `DraftPayloadBuilder` only consume `stage="publish_ready", type="wechat_api_article"`.
- Passing `article_document` directly to draft creation is invalid input.

## Local Modules

- `ArticleDocumentTypes.ts`: envelope, schema versions, asset metadata.
- `ArticleDocumentValidator.ts`: ProseMirror schema validation and image `asset_ref` checks.
- `WechatArticleDocumentRenderer.ts`: WeChat-safe HTML rendering with inline style profiles.
- `ArticleDocumentToWechatArtifactBuilder.ts`: `article_document` plus prepared assets to `wechat_api_article`.
- `MarkdownArticleImporter.ts`: legacy Markdown to canonical JSON.
- `MarkdownArticleExporter.ts`: non-canonical Markdown/HTML previews.

## Live Smoke

Use:

```bash
pnpm --filter @mcps/wechat-draft build
node packages/wechat-draft/scripts/live-canonical-smoke.mjs
```

The script uploads one body image and one cover image, creates a draft, then calls adapter `drafts/batchget` to verify:

- the draft `media_id` is present in batchget results;
- body content includes `article_document.tiptap.v1`;
- no Markdown markers remain;
- body image URLs use `mmbiz.qpic.cn`.

For multi-account production checks, set `WECHAT_CANONICAL_SMOKE_ACCOUNT=xiaban`; the default style profile becomes `xiaban.default` unless `WECHAT_CANONICAL_SMOKE_STYLE_PROFILE` is set explicitly.

The live smoke now requires both `WECHAT_ADAPTER_AUTH_TOKEN` and `HERMES_DB_AUTH_TOKEN`. Missing hermes-db auth is a blocker, because direct adapter fallback is not accepted as full MCP path evidence.
