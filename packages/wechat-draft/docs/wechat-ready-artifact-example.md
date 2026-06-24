# WeChat-Ready Artifact Example

This document provides a complete example of a `workflow_artifacts` entry that passes WeChat-ready validation.

## Valid WeChat-Ready Artifact

```json
{
  "artifact_id": "artifact_20260621_example_001",
  "run_id": "run_20260621_001",
  "task_id": "task_draft_001",
  "topic_id": "550e8400-e29b-41d4-a716-446655440000",
  "account": "yueliang",
  "stage": "publish_ready",
  "type": "wechat_api_article",
  "name": "article.wechat-api-ready.json",
  "content_hash": "sha256:abc123...",
  "content_size_bytes": 15420,
  "content_preview": "这是一篇关于 AI 技术的文章...",
  "content_text": "<p>这是正文内容，包含微信图片 <img src=\"https://mmbiz.qpic.cn/mmbiz_png/example123/0?wx_fmt=png\" /></p>",
  "content_ref": null,
  "metadata": {
    "publish_ready": true,
    "title": "AI 技术发展趋势分析",
    "digest": "本文深入分析 2026 年 AI 技术的最新发展趋势",
    "author": "月亮",
    "content_source_url": "https://example.com/articles/ai-trends-2026",
    "cover": {
      "thumb_media_id": "PERMANENT_THUMB_MEDIA_ID_ABC123"
    },
    "style_profile_id": "yueliang.default",
    "style_version": "2026-06-21",
    "schema_version": "wechat_api_article.v1",
    "source_article_document_artifact_id": "artifact_20260624_article_document_001",
    "source_article_document_schema_version": "article_document.tiptap.v1",
    "wechat_asset_manifest": {
      "ready": true,
      "body_images": [
        {
          "wechat_url": "https://mmbiz.qpic.cn/mmbiz_png/example123/0?wx_fmt=png",
          "position_hint": "paragraph-2"
        },
        {
          "wechat_url": "https://mmbiz.qpic.cn/mmbiz_jpg/example456/0?wx_fmt=jpeg",
          "position_hint": "paragraph-5"
        }
      ],
      "cover_thumb_media_id": "PERMANENT_THUMB_MEDIA_ID_ABC123",
      "asset_warnings": []
    },
    "source_markdown_artifact_id": "artifact_20260621_markdown_001",
    "parent_artifact_id": "artifact_20260624_article_document_001",
    "format": "wechat_api_article"
  },
  "created_at": "2026-06-21T10:00:00Z",
  "updated_at": "2026-06-21T10:05:00Z"
}
```

## Validation Rules

### Required Fields

| Field | Value | Validation |
|---|---|---|
| `stage` | `publish_ready` | Must be exactly `publish_ready` |
| `type` | `wechat_api_article` | Must be exactly `wechat_api_article` |
| `metadata.publish_ready` | `true` | Must be `true` |
| `metadata.title` | Non-empty string | Required |
| `metadata.wechat_asset_manifest.ready` | `true` | Must be `true` |
| `metadata.cover.thumb_media_id` | Non-empty string | Permanent WeChat material ID |
| `content_text` or `content_ref` | Non-null | At least one must be provided |

### WeChat Image URL Format

All body images must use WeChat-hosted URLs:
- ✅ Valid: `https://mmbiz.qpic.cn/mmbiz_png/...`
- ✅ Valid: `https://mmbiz.qpic.cn/mmbiz_jpg/...`
- ❌ Invalid: `https://example.com/image.png`
- ❌ Invalid: `file:///local/path/image.png`
- ❌ Invalid: `http://unsecure-url.com/image.png`

### Cover Material

Cover `thumb_media_id` must be a permanent WeChat material ID obtained via:
- WeChat API: `POST /cgi-bin/material/add_material?type=thumb`
- Or manually uploaded via WeChat backend

### Asset Manifest Structure

```json
{
  "ready": true,
  "body_images": [
    {
      "wechat_url": "https://mmbiz.qpic.cn/...",
      "position_hint": "optional-block-id"
    }
  ],
  "cover_thumb_media_id": "PERMANENT_THUMB_MEDIA_ID",
  "asset_warnings": []
}
```

## Invalid Examples

### Example 1: Wrong Stage

```json
{
  "stage": "draft",  // ❌ Should be "publish_ready"
  "type": "wechat_api_article",
  "metadata": {
    "publish_ready": true,
    ...
  }
}
```

**Validation Error**:
```json
{
  "field": "stage",
  "issue": "Expected 'publish_ready', got 'draft'",
  "severity": "error"
}
```

### Example 2: Non-WeChat Image URL

```json
{
  "stage": "publish_ready",
  "type": "wechat_api_article",
  "metadata": {
    "wechat_asset_manifest": {
      "ready": true,
      "body_images": [
        {
          "wechat_url": "https://example.com/image.png"  // ❌ Not WeChat URL
        }
      ]
    }
  }
}
```

**Validation Error**:
```json
{
  "field": "metadata.wechat_asset_manifest.body_images",
  "issue": "Invalid WeChat image URL: https://example.com/image.png",
  "severity": "error"
}
```

### Example 3: Missing Cover thumb_media_id

```json
{
  "stage": "publish_ready",
  "type": "wechat_api_article",
  "metadata": {
    "publish_ready": true,
    "cover": {},  // ❌ Missing thumb_media_id
    "wechat_asset_manifest": {
      "ready": true
    }
  }
}
```

**Validation Error**:
```json
{
  "field": "metadata.cover.thumb_media_id",
  "issue": "Cover thumb_media_id is missing",
  "severity": "error"
}
```

## Asset Preparation Workflow

The WeChat-ready artifact contract assumes upstream asset preparation:

```text
1. Writing Agent / Style Skill
   - Generate canonical article_document JSON
   - Optionally import legacy Markdown into article_document

2. Asset Preparation Flow (Separate from Draft MCP)
   - Upload body images via WeChat API: POST /cgi-bin/media/uploadimg
   - Upload cover image via WeChat API: POST /cgi-bin/material/add_material?type=thumb
   - Resolve article_document image asset_ref values to WeChat URLs
   - Render final HTML with WeChat image URLs

3. Save to hermes-db
   - stage: publish_ready
   - type: wechat_api_article
   - metadata.wechat_asset_manifest.ready: true
   - metadata.source_article_document_artifact_id: source canonical artifact

4. WeChat Draft MCP
   - Validate artifact via wechat_validate_publish_artifact
   - Create draft via wechat_create_draft
```

## MVP Scope

- ✅ MCP validates artifact is WeChat-ready
- ✅ MCP rejects non-WeChat image URLs
- ✅ MCP rejects missing cover thumb_media_id
- ✅ MCP rejects `article_document` as a direct draft input
- ❌ MCP does NOT upload images
- ❌ MCP does NOT normalize assets
- ❌ MCP does NOT render `article_document`

Image upload, asset normalization, and canonical `article_document` rendering are handled by upstream workflows.
