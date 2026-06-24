# Data Model: WeChat Canonical Article Artifact

**Workspace**: `wechat-canonical-article-artifact`  
**Date**: 2026-06-24  
**Plan**: [plan.md](plan.md)

---

## Storage Strategy

MVP reuses `hermes.workflow_artifacts`.

No new hermes-db migration is required for the first implementation unless tests prove that `content_text`, `content_ref`, metadata size, or listing behavior is insufficient.

---

## Entity: `article_document` Artifact

| Field | Value / Type | Notes |
|---|---|---|
| `type` | `article_document` | Canonical article source |
| `stage` | `draft` / `transformed-draft` / `article_document` | Exact stage naming may align with upstream workflow |
| `name` | `article-document` | Stable artifact name |
| `content_text` | JSON string | Tiptap/ProseMirror JSON document envelope |
| `content_ref` | nullable string | Existing fallback for oversized content |
| `parent_artifact_id` | nullable artifact id | Link to source Markdown or previous version |
| `metadata.schema_version` | `article_document.tiptap.v1` | Required |
| `metadata.format` | `article_document` | Required |
| `metadata.style_profile_id` | string | Example: `yueliang.default` |
| `metadata.style_version` | string? | Optional but recommended |
| `metadata.source_markdown_artifact_id` | string? | Legacy provenance |
| `metadata.allowed_extensions` | string[] | Renderer validation reference |

### `content_text` Envelope

```json
{
  "schema_version": "article_document.tiptap.v1",
  "title": "到了四个月，还能继续奶睡抱睡吗？",
  "digest": "你刚把他放下来。",
  "author": "月亮睡了我不睡",
  "style_profile_id": "yueliang.default",
  "doc": {
    "type": "doc",
    "content": [
      {
        "type": "paragraph",
        "content": [{ "type": "text", "text": "你刚把他放下来。" }]
      },
      {
        "type": "heading",
        "attrs": { "level": 2 },
        "content": [{ "type": "text", "text": "先把坏习惯这顶帽子摘掉" }]
      },
      {
        "type": "paragraph",
        "content": [
          { "type": "text", "text": "它是", "marks": [] },
          { "type": "text", "text": "最本能的入睡方式", "marks": [{ "type": "bold" }] }
        ]
      },
      {
        "type": "image",
        "attrs": {
          "asset_ref": "asset-body-1",
          "alt": "奶睡和抱睡"
        }
      },
      {
        "type": "horizontalRule"
      }
    ]
  },
  "assets": [
    {
      "asset_ref": "asset-body-1",
      "source_url": "https://example.com/source.webp",
      "usage": "body_image"
    }
  ]
}
```

---

## Entity: `wechat_api_article` Artifact

This remains the existing publish-ready contract consumed by `wechat-draft`.

| Field | Value / Type | Notes |
|---|---|---|
| `type` | `wechat_api_article` | Existing draft MCP input |
| `stage` | `publish_ready` | Required by `ArtifactValidator` |
| `content_text` | HTML string | Final WeChat-safe HTML |
| `metadata.publish_ready` | `true` | Required |
| `metadata.title` | string | Required |
| `metadata.cover.thumb_media_id` | string | Required |
| `metadata.wechat_asset_manifest.ready` | `true` | Required |
| `metadata.wechat_asset_manifest.body_images[].wechat_url` | `https://mmbiz.qpic.cn/...` | Required for body images |
| `metadata.source_article_document_artifact_id` | string | Link back to canonical artifact |
| `metadata.style_profile_id` | string | Same profile used by renderer |
| `metadata.style_version` | string | Renderer/style traceability |

---

## Relationship Model

```text
source_markdown artifact
        |
        | parent_artifact_id / source_markdown_artifact_id
        v
article_document artifact
        |
        | source_article_document_artifact_id
        v
wechat_api_article artifact
        |
        | draft_artifact_id / published_artifact_id in ledger
        v
wechat_articles(status=drafted, metadata.media_id)
```

---

## Validation Rules

### `article_document`

- `metadata.schema_version` must be `article_document.tiptap.v1`.
- `content_text` must parse as JSON.
- Envelope must contain `doc.type="doc"`.
- All nodes and marks must be in the MVP allowlist.
- Image nodes must contain an `asset_ref` or a previously prepared `wechat_url`.
- Title must be present either in envelope or metadata.
- Unknown nodes fail closed before rendering.

### `wechat_api_article`

Use existing `ArtifactValidator` rules:

- `stage === "publish_ready"`
- `type === "wechat_api_article"`
- `metadata.publish_ready === true`
- `metadata.title` exists
- cover `thumb_media_id` exists
- body image URLs are `https://mmbiz.qpic.cn/...`
- `content_text` or `content_ref` exists

---

## Query Behavior

- `list_workflow_artifacts` must continue to omit `content_text`.
- `get_workflow_artifact_content` returns the full JSON envelope or HTML content by artifact id.
- Agent/UI reading should fetch by artifact id rather than broad full-text list scans.

---

## Compatibility

- Markdown import may create both `source_markdown` and `article_document`.
- Markdown export is generated from `article_document` and marked non-canonical.
- Old `wechat_api_article` artifacts remain valid and do not require backfill.
