# Article Document Artifact Example

This document shows the canonical `article_document` artifact shape used before WeChat rendering.
Markdown is a legacy import/export format only; the publish path uses this structured document.

## Canonical `article_document`

For readability, `content_text` is shown below as parsed JSON. In `workflow_artifacts`, it is stored as a JSON string.

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

## Rendering Handoff

The renderer validates the ProseMirror/Tiptap JSON against the local allowlist, fails closed on unresolved images, and emits a separate `wechat_api_article` artifact.

The generated artifact records:

- `metadata.source_article_document_artifact_id`
- `metadata.source_article_document_schema_version`
- `metadata.schema_version = "wechat_api_article.v1"`
- `metadata.style_profile_id`
- `metadata.wechat_asset_manifest.ready = true`

`wechat_create_draft` remains a downstream consumer of `wechat_api_article` only. Passing `article_document` directly to draft payload construction is a boundary error.
