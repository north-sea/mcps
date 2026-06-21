# Data Model: WeChat Draft MCP

**Workspace**: `wechat-draft-mcp` | **Date**: 2026-06-21

MVP does not own article content storage. Article content is stored in `hermes.workflow_artifacts` by the writing agent / style skill. This MCP consumes a rendered WeChat-ready artifact, validates its WeChat asset references, and writes draft results back to local job summaries plus `hermes.wechat_articles`.

## External Hermes Models Used

### `hermes.workflow_artifacts`

**Purpose**: Stores the article artifact prepared by upstream agents.

Relevant fields:

| Field | Type | Notes |
|---|---|---|
| `artifact_id` | string | Primary input to `wechat_create_draft`. |
| `run_id` | string | Required to later upsert `wechat_articles`. |
| `task_id` | string | Optional trace field. |
| `topic_id` | uuid | Optional topic link. |
| `account` | string | Target WeChat account; must match MCP input. |
| `stage` | string | Recommended MVP value: `publish_ready`. |
| `type` | string | Recommended MVP value: `wechat_api_article`. |
| `name` | string | Logical artifact name, e.g. `article.wechat-api-ready.json`. |
| `content_hash` | string | Used for idempotency and traceability. |
| `content_size_bytes` | number | Used to bound responses and API payloads. |
| `content_preview` | string | Compact display snippet. |
| `content_text` | string | Inline rendered body HTML if small enough. |
| `content_ref` | string | External content reference if body is too large. |
| `metadata` | object | Must include title, style details, cover `thumb_media_id`, and WeChat asset manifest. |

Expected metadata:

```json
{
  "publish_ready": true,
  "title": "文章标题",
  "digest": "可选摘要",
  "author": "可选作者",
  "content_source_url": "https://optional.example.com",
  "cover": {
    "thumb_media_id": "PERMANENT_THUMB_MEDIA_ID"
  },
  "style_profile_id": "yueliang.default",
  "style_version": "2026-06-21",
  "wechat_asset_manifest": {
    "ready": true,
    "body_images": [
      {
        "wechat_url": "https://mmbiz.qpic.cn/...",
        "position_hint": "optional-block-id"
      }
    ],
    "cover_thumb_media_id": "PERMANENT_THUMB_MEDIA_ID",
    "asset_warnings": []
  },
  "source_markdown_artifact_id": "optional-source-artifact",
  "format": "wechat_api_article"
}
```

**微信素材 ready 契约**：

- `cover.thumb_media_id` 必须存在，且表示微信永久素材 MediaID。
- `wechat_asset_manifest.ready` 必须为 `true`。
- `body_images[*].wechat_url` 必须是微信图文图片 URL。
- `wechat_create_draft` 不接受非微信图片 URL、本地路径或临时图片 URL；这些输入必须在调用前转换为微信素材 ready 引用。
- `draft/add` payload 只使用已验证的微信 URL / `thumb_media_id`。

### `hermes.wechat_articles`

**Purpose**: Stores WeChat-side article ledger, not full article body.

MCP writes this only after successfully creating a WeChat draft.

| Field | Value in draft phase |
|---|---|
| `account` | Target account, e.g. `yueliang`. |
| `run_id` | From `workflow_artifacts.run_id`. |
| `status` | `drafted`. |
| `draft_artifact_id` | The publish-ready artifact consumed by MCP. |
| `title` | From artifact metadata. |
| `publication_idempotency_key` | Stable key derived from account + artifact id/hash. |
| `metadata` | Draft job id, WeChat `media_id`, style metadata, asset manifest summary, API request id/error context. |
| `published_url` | Must remain empty until human publish confirmation. |

Ledger metadata requirements:

```json
{
  "draft_job_id": "job_...",
  "draft_locator": {
    "media_id": "MEDIA_ID",
    "source": "wechat_draft_add"
  },
  "wechat_media_id": "MEDIA_ID",
  "style_profile_id": "yueliang.default",
  "style_version": "2026-06-21",
  "wechat_asset_manifest": {
    "ready": true,
    "body_image_count": 0,
    "has_cover_thumb_media_id": true
  },
  "diagnostic_ref": "runtime/wechat-draft/artifacts/<job_id>/artifact-validation.json"
}
```

The metadata must be compact. It may contain references to local diagnostics, but not full article HTML, AppSecret, AccessToken, full HTTP payloads, or long traces.

## MCP-Owned Entities

### AccountConfig

| Field | Type | Constraint | Notes |
|---|---|---|---|
| `account_id` | string | required, unique | Example: `yueliang`. |
| `display_name` | string | required | Human-readable account name. |
| `enabled` | boolean | required | Disabled accounts cannot be used. |
| `adapter_account_ref` | string | required | Account id expected by the Ali ECS adapter; usually same as `account_id`. |
| `adapter_id` | string | required | Links to `EcsWechatAdapterConfig`. |
| `metadata` | object | optional | Non-secret operator notes such as ECS IP whitelist owner. |

### ApiCredentialConfig

| Field | Type | Notes |
|---|---|---|
| `account_id` | string | Links to account. |
| `credential_location` | enum | `ecs_adapter`; NAS-side MCP must not store raw AppSecret in MVP. |
| `adapter_account_ref` | string | Adapter-side logical account. |
| `appid_hint` | string | Optional redacted AppID suffix or operator label returned by adapter. |
| `secret_source_hint` | string | Optional ECS secret/env source label; never raw secret. |
| `ip_whitelist_note` | string | Operator note for WeChat console config; should reference ECS public IP/EIP. |

### EcsWechatAdapterConfig

| Field | Type | Notes |
|---|---|---|
| `adapter_id` | string | Stable logical id, e.g. `ali-wechat-egress`. |
| `base_url` | string | Private endpoint reachable from NAS, e.g. Tailscale/WireGuard/SSH tunnel URL. |
| `auth_ref` | string | Secret/env reference for adapter auth token or equivalent credential. |
| `allowed_accounts` | string[] | Accounts the MCP may request through this adapter. |
| `egress_public_ip` | string | Ali ECS public IP/EIP configured in WeChat IP whitelist. |
| `network_path` | enum | `tailscale`, `wireguard`, `ssh_tunnel`, `private_vpc`, `other`. |
| `timeout_ms` | number | Short timeout for health/check/create calls. |
| `capabilities` | string[] | MVP allowlist: `check_credentials`, `draft_add`, optional `draft_batchget`. |
| `metadata` | object | Non-secret deployment notes such as host alias `ali` or systemd unit name. |

### AccessTokenState

| Field | Type | Notes |
|---|---|---|
| `account_id` | string | Links to account. |
| `owner` | enum | `ecs_adapter`; token is not stored by NAS MCP in MVP. |
| `token_hash` | string | Hash only, never token value. |
| `expires_at` | datetime | Token expiry with safety margin. |
| `last_refresh_at` | datetime | Last attempted refresh. |
| `last_error_code` | string | WeChat errcode or local error. |
| `last_error_message` | string | Redacted diagnostic. |

### AdapterHealthState

| Field | Type | Notes |
|---|---|---|
| `adapter_id` | string | Links to `EcsWechatAdapterConfig`. |
| `reachable` | boolean | Whether NAS-side MCP can reach adapter health endpoint. |
| `egress_public_ip` | string | Adapter-reported or operator-configured ECS public IP/EIP. |
| `version` | string | Adapter version or build id. |
| `capabilities` | string[] | Adapter-reported allowlist. |
| `last_checked_at` | datetime | Last health/check time. |
| `last_error` | string | Redacted transport/auth/config error. |

### PublishReadyArtifact

**Description**: Normalized view after MCP loads `workflow_artifacts`.

| Field | Type | Constraint | Notes |
|---|---|---|---|
| `artifact_id` | string | required | Source artifact id. |
| `run_id` | string | required | Required for ledger update. |
| `account` | string | required | Must match enabled account. |
| `stage` | string | required | MVP expected: `publish_ready`. |
| `type` | string | required | MVP expected: `wechat_api_article`. |
| `title` | string | required | From artifact metadata. Missing title is invalid in MVP. |
| `body_html` | string | required | From `content_text` or fetched `content_ref`; rendered HTML already using WeChat body image URLs. |
| `digest` | string | optional | Summary/abstract. |
| `author` | string | optional | Written if provided. |
| `content_source_url` | string | optional | Read-original URL. |
| `cover_thumb_media_id` | string | required | 永久素材 MediaID；缺失时 `wechat_create_draft` 拒绝。 |
| `style_profile_id` | string | required | Produced upstream; MCP records but does not render. |
| `style_version` | string | required | Produced upstream. |
| `wechat_asset_manifest` | object | required | 微信素材 ready 清单；正文图片必须已有 `wechat_url`，封面必须匹配 `cover_thumb_media_id`。 |
| `content_hash` | string | required | From artifact. |
| `content_size_bytes` | number | required | From artifact. |

### WechatAssetManifest

**Description**: `wechat_create_draft` 接受的唯一图片素材契约。

| Field | Type | Notes |
|---|---|---|
| `ready` | boolean | Must be true for create-draft. |
| `body_images` | object[] | Each image has `wechat_url` and optional `position_hint`; no external/source URL is accepted by create-draft. |
| `cover_thumb_media_id` | string | Permanent thumb/image media id used by draft API. |
| `asset_warnings` | string[] | Non-blocking compatibility notes. |

### ArtifactValidationResult

| Field | Type | Notes |
|---|---|---|
| `valid` | boolean | Whether artifact can be written. |
| `artifact_id` | string | Source artifact. |
| `account` | string | Target account. |
| `title` | string | Parsed title if available. |
| `errors` | object[] | Missing/invalid fields. |
| `warnings` | string[] | Non-blocking compatibility notes. |

### WechatApiError

| Field | Type | Notes |
|---|---|---|
| `errcode` | number | WeChat error code when present. |
| `errmsg` | string | Redacted WeChat error text. |
| `category` | enum | `credential`, `token`, `ip_whitelist`, `permission`, `rate_limit`, `asset_validation`, `payload`, `server`, `unknown`. |
| `retryable` | boolean | Whether automatic one-shot retry is allowed. |
| `next_action` | string | Operator-facing action. |

### AdapterError

| Field | Type | Notes |
|---|---|---|
| `category` | enum | `unreachable`, `auth`, `account_not_configured`, `capability_missing`, `timeout`, `bad_response`, `internal`. |
| `message` | string | Redacted diagnostic. |
| `retryable` | boolean | Whether retry is useful without operator action. |
| `next_action` | string | Operator-facing action, e.g. check Tailscale, adapter systemd unit, auth token, or allowlist. |

### DraftJob

| Field | Type | Notes |
|---|---|---|
| `job_id` | string | Server-generated. |
| `account_id` | string | Target account. |
| `artifact_id` | string | Publish-ready artifact. |
| `run_id` | string | From artifact. |
| `title` | string | Compact summary; not full body. |
| `status` | enum | See transitions below. |
| `wechat_media_id` | string | Present after successful `draft/add`. |
| `draft_locator` | object | At minimum `{ media_id, source }`. |
| `article_id` | string | Present after successful ledger upsert. |
| `error_type` | string | Validation/credential/token/asset_validation/wechat_api/ledger/lock/internal. |
| `manual_action` | object | Needed action and reason. |
| `idempotency_key` | string | Stable key from caller or derived from account + artifact id + content hash. |
| `diagnostic_ref` | string | Redacted artifact directory or file path. |
| `created_at` | datetime | Job creation time. |
| `updated_at` | datetime | Latest update time. |

```text
queued -> artifact_validation -> adapter_check -> payload_build -> draft_add -> ledger_update -> saved
                         -> invalid_artifact
                                          -> needs_operator_action
                                          -> failed
```

Terminal statuses: `saved`, `failed`, `invalid_artifact`, `needs_operator_action`.

### ArticleLedgerUpdate

| Field | Type | Notes |
|---|---|---|
| `account` | string | Target account. |
| `run_id` | string | From artifact. |
| `status` | string | `drafted` after successful draft save. |
| `draft_artifact_id` | string | Publish-ready artifact id. |
| `title` | string | Article title. |
| `publication_idempotency_key` | string | Stable key. |
| `metadata` | object | `draft_job_id`, `wechat_media_id`, `draft_locator`, `style_profile_id`, `style_version`, `wechat_asset_manifest`. |

### ManualActionRequest

| Field | Type | Notes |
|---|---|---|
| `reason` | enum | `missing_secret`, `invalid_secret`, `ip_whitelist`, `permission_denied`, `asset_not_ready`, `rate_limit`, `wechat_api_error`, `ledger_repair`. |
| `message` | string | Short actionable instruction. |
| `diagnostic_ref` | string | Optional redacted diagnostic path. |
| `retry_allowed` | boolean | Whether caller may retry after manual action. |

## Relationships

```text
workflow_artifacts 1:N DraftJob
workflow_artifacts 1:N wechat_articles via draft_artifact_id
AccountConfig 1:N DraftJob
AccountConfig 1:1 ApiCredentialConfig
AccountConfig N:1 EcsWechatAdapterConfig
EcsWechatAdapterConfig 0:1 AdapterHealthState
EcsWechatAdapterConfig 1:N AccessTokenState
DraftJob 0:1 WechatApiError
DraftJob 0:1 AdapterError
DraftJob 0:1 ManualActionRequest
DraftJob 0:1 ArticleLedgerUpdate
```

## MCP Runtime Storage

```text
packages/wechat-draft/config/accounts.example.yaml

runtime/wechat-draft/jobs/YYYY-MM-DD.jsonl
runtime/wechat-draft/artifacts/<job_id>/
  artifact-validation.json
  adapter-summary.json
  wechat-api-summary.json

packages/wechat-draft-adapter/config/accounts.example.yaml
runtime/wechat-draft-adapter/token-cache/<account_id>.json
runtime/wechat-draft-adapter/logs/YYYY-MM-DD.jsonl
```

Runtime paths must be configurable and excluded from git.

Runtime storage rules:

- JSONL is the MVP operational log, not the long-term system of record.
- Each line must be one complete `DraftJob` summary or status transition event with `job_id`, `idempotency_key`, `account_id`, `artifact_id`, `status`, `timestamp`, and compact error/locator fields.
- NAS-side MCP must not store AccessToken in MVP. Adapter token cache may store AccessToken only under a configurable ECS runtime path with restrictive permissions; tool outputs must never return token values.
- `wechat_get_draft_status(job_id)` reads from JSONL; successful jobs must also be discoverable through `wechat_articles.metadata.draft_job_id`.
- Repeated `wechat_create_draft` calls with the same idempotency key must return the existing terminal job when possible; they must not create a second draft silently.
- Keep JSONL files by date and rotate daily. Default retention: 30 days for JSONL summaries, 7 days for API summaries, unless the operator config overrides it.
- Diagnostic artifacts must be redacted before writing by default. Full article body, AppSecret, AccessToken, adapter auth token, full HTTP request/response bodies, and account secrets are forbidden.
- Runtime cleanup must never delete `hermes.wechat_articles` rows. DB ledger correction is a separate manual repair workflow.

## Migration Notes

- MCP database migration: none for MVP if existing hermes-db `workflow_artifacts` and `wechat_articles` are available.
- No new `wechat_articles.status` value is needed. Use artifact `stage` for content-production readiness and `wechat_articles.status` for WeChat-side result.
- Human publish confirmation later updates the existing article ledger to `published` and supplies `published_url` or external refs.
- If JSONL retention, cross-host status lookup, or operational analytics become core requirements, add a later feature for a first-class `draft_jobs` table instead of expanding this MVP migration scope.
