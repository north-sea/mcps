# Acceptance: WeChat Canonical Article Artifact

**Feature**: `wechat-canonical-article-artifact`  
**Date**: 2026-06-24  
**Verdict**: PASS with noted follow-up

## Scope Verified

- `article_document.tiptap.v1` envelope, schema version, assets, cover and metadata types are implemented.
- ProseMirror allowlist validation rejects unsupported nodes/marks, invalid schema versions and unresolved image assets.
- Canonical renderer outputs WeChat-safe HTML from structured JSON, not Markdown text.
- Renderer fails closed on missing assets and non-WeChat image URLs.
- `ArticleDocumentToWechatArtifactBuilder` creates `publish_ready` `wechat_api_article` artifacts compatible with `ArtifactValidator` and `DraftPayloadBuilder`.
- `DraftPayloadBuilder` still rejects direct `article_document` input.
- Legacy Markdown importer/exporter exists only for compatibility and marks exports as non-canonical.
- WeChat adapter exposes `draft_batchget` and live smoke verified a real draft.

## Evidence

### Local Build And Tests

```bash
rtk pnpm --filter @mcps/wechat-draft build
rtk pnpm --filter @mcps/wechat-draft-adapter build
rtk node packages/wechat-draft/test-article-document-renderer.mjs
rtk node packages/wechat-draft/test-markdown-wechat-renderer.mjs
```

Results:

- `@mcps/wechat-draft` build: PASS
- `@mcps/wechat-draft-adapter` build: PASS
- Canonical article test: `40/40 tests passed`
- Existing Markdown renderer regression: `17/17 tests passed`

### Live Smoke

Account: `yueliang`

Inputs:

- Generated local JPEG: `/private/tmp/wechat-canonical-smoke-cover.jpg`
- Body image upload returned WeChat URL:
  `http://mmbiz.qpic.cn/sz_mmbiz_jpg/tea949YTyuswTbf2ibDkVTR5UeZS4C0ORR5p8TmuibbVenlHkEQMEaSWvE7RhGnyxW7H2lQUgVISqRIm5zk3obIosoM9ktO6W5UoQJo0PYv3s/0?from=appmsg`
- Cover upload returned `thumb_media_id`:
  `Qot4VGi0raBIXbuQaXFJMjT14Y87Pvi4m4gThoYvP27puJroGsnltWtwGc6Uv2tk`
- Draft creation returned `media_id`:
  `Qot4VGi0raBIXbuQaXFJMj7Ydgz3Om6ZAYf9SEgFtR5YJFG53WLDjh2cLots6CWh`

Batchget verification:

```json
{
  "status": 200,
  "success": true,
  "found": true,
  "title": "Canonical smoke 2026-06-24T14:30:10.038Z",
  "hasCanonicalText": true,
  "noMarkdownResidue": true,
  "hasWechatImage": true,
  "contentLength": 1870,
  "total_count": 8,
  "item_count": 8
}
```

Hermes workflow run:

- `run_id`: `wechat-canonical-smoke-2026-06-24T14-30-10-038Z`
- `status`: `completed`

## Deviations

- The command environment did not expose `HERMES_DB_AUTH_TOKEN`, so local `wechat_validate_publish_artifact` / `wechat_create_draft` could not read hermes-db and failed with HTTP 401.
- The ready `wechat_api_article` artifact was written through the hermes-db MCP tool, but actual draft creation used direct adapter fallback after `DraftPayloadBuilder` payload generation.
- Source `article_document` artifact upsert hit a hermes-db argument parsing issue where JSON `content_text` was interpreted as an object. The ready artifact still records `source_article_document_artifact_id` and schema metadata.

## Residual Risks

- A future full MCP-path smoke should run in an environment where `HERMES_DB_AUTH_TOKEN` is available to the `wechat-draft` server process.
- Adapter deployment was updated during verification to expose `/accounts/:account/drafts/batchget`; this should be included in commit/deploy notes.
- The initial 1x1 JPEG upload returned a WeChat `-1 system error`; the verified path uses a 200x200 JPEG.

## Completion State

- T001-T012: complete
- T013: complete with this evidence
- T014: complete via `packages/wechat-draft/docs/canonical-article-artifact.md`
- T015: complete via this acceptance and commit plan
