# Article Document Artifact Example

This document shows the canonical `article_document` artifact shape used before WeChat rendering.
Markdown is a legacy import/export format only; the publish path uses this structured document.

## Canonical `article_document`

For readability, `content_text` is shown below as parsed JSON. In `workflow_artifacts`, it is stored as a JSON string.

For new MCP flows, prefer the typed article-document tools:

- `wechat_import_article_markdown`
- `wechat_validate_article_document`
- `wechat_render_article_document`
- `wechat_build_publish_ready_artifact`
- `wechat_create_draft_facade`

These tools accept the article document object directly where appropriate and handle validation/rendering inside the MCP. Only stringify the document when persisting it to hermes `content_text`.

```json
{
  "artifact_id": "artifact_20260624_article_document_001",
  "run_id": "run_20260624_001",
  "account": "yueliang",
  "stage": "drafted",
  "type": "article_document",
  "name": "article-document.json",
  "content_hash": "sha256:...",
  "content_size_bytes": 4096,
  "content_text": {
    "schema_version": "article_document.tiptap.v1",
    "title": "结构化正文测试",
    "digest": "结构化摘要",
    "author": "月亮",
    "style_profile_id": "yueliang.default",
    "content_source_url": "https://example.com/source",
    "cover": {
      "thumb_media_id": "PERMANENT_THUMB_MEDIA_ID_ABC123"
    },
    "assets": {
      "hero": {
        "asset_ref": "hero",
        "wechat_url": "https://mmbiz.qpic.cn/mmbiz_png/example123/0?wx_fmt=png",
        "alt": "正文图",
        "ready": true
      }
    },
    "doc": {
      "type": "doc",
      "content": [
        {
          "type": "heading",
          "attrs": { "level": 2 },
          "content": [{ "type": "text", "text": "小标题" }]
        },
        {
          "type": "paragraph",
          "content": [
            { "type": "text", "text": "正文 " },
            { "type": "text", "text": "重点", "marks": [{ "type": "bold" }] }
          ]
        },
        {
          "type": "image",
          "attrs": { "asset_ref": "hero", "alt": "正文图" }
        },
        { "type": "horizontalRule" }
      ]
    },
    "source_markdown_artifact_id": "artifact_legacy_markdown_001"
  },
  "metadata": {
    "schema_version": "article_document.tiptap.v1",
    "style_profile_id": "yueliang.default",
    "source_markdown_artifact_id": "artifact_legacy_markdown_001"
  },
  "created_at": "2026-06-24T00:00:00Z",
  "updated_at": "2026-06-24T00:00:00Z"
}
```

Actual `upsert_workflow_artifact` calls should pass the document as a string:

```json
{
  "run_id": "run_20260624_001",
  "stage": "drafted",
  "type": "article_document",
  "name": "article-document.json",
  "content_hash": "sha256:...",
  "content_size_bytes": 4096,
  "content_text": "{\"schema_version\":\"article_document.tiptap.v1\",\"title\":\"结构化正文测试\",\"doc\":{\"type\":\"doc\",\"content\":[]}}",
  "metadata": {
    "schema_version": "article_document.tiptap.v1",
    "style_profile_id": "yueliang.default"
  }
}
```

## Rendering Handoff

The renderer validates the ProseMirror/Tiptap JSON against the local allowlist, fails closed on unresolved images, and emits a separate `wechat_api_article` artifact.

The generated artifact records:

- `metadata.source_article_document_artifact_id`
- `metadata.source_article_document_schema_version`
- `metadata.schema_version = "wechat_api_article.v1"`
- `metadata.style_profile_id`
- `metadata.wechat_asset_manifest.ready = true`

`wechat_create_draft` remains a downstream consumer of `wechat_api_article` only. Passing `article_document` directly to draft payload construction is a boundary error.

## Agent-Facing Draft Flow

### Happy Path

1. Call `wechat_list_accounts` and inspect `constraints.assets` before uploading images.
2. Call `wechat_preflight_asset` for each cover/body image before upload. This tool does not upload or compress; it reports whether the source already satisfies the current WeChat constraints and returns transform recommendations when it does not.
3. Upload or otherwise prepare image assets:
   - body images need `wechat_url`
   - cover image needs `thumb_media_id`
4. Call `wechat_import_article_markdown` if the source is Markdown, or pass an existing `article_document` object to the next step.
5. Call `wechat_validate_article_document` before rendering/building.
6. Call `wechat_render_article_document` for operator/agent preview.
7. Call `wechat_create_draft_facade` with `source_type="article_document"`, `run_id`, `publish_artifact_id`, and the prepared article document. The facade builds the publish-ready payload, upserts the workflow run/artifact, validates it, and creates the WeChat draft.

If a `publish_ready` / `wechat_api_article` artifact already exists, call `wechat_create_draft_facade` with `source_type="publish_ready_artifact"` and `artifact_id`. The facade validates the artifact before creating the draft and returns a phase trace for recovery.

### Manual Recovery Path

Use low-level tools when debugging, re-rendering, or recovering from a specific failed phase:

1. Call `wechat_build_publish_ready_artifact` to get a hermes `upsert_workflow_artifact` payload for `stage=publish_ready`, `type=wechat_api_article`.
2. Ensure the `workflow_run` exists before upserting workflow artifacts.
3. Upsert the returned publish-ready payload to hermes.
4. Call `wechat_validate_publish_artifact`.
5. Call `wechat_create_draft`.

The article-document tools are side-effect-free. They do not upload images, write hermes-db, or create WeChat drafts.
`wechat_preflight_asset` is also side-effect-free. It keeps current limits conservative: body images still target `media/uploadimg` under 1MB, and cover images still target `thumb` JPEG under 64KB. Real compression is not implemented in this MCP feature; use the recommendation to transform the asset externally, then preflight again.
`wechat_create_draft_facade` is side-effecting: in `article_document` mode it writes Hermes workflow records and creates a WeChat draft; in `publish_ready_artifact` mode it creates the WeChat draft after validation.

If `wechat_create_draft` reports `content_ref` is unsupported, re-upsert the publish-ready artifact with inline rendered HTML in `content_text`. `content_ref` dereferencing is intentionally not part of the draft creation path yet.
