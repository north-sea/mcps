# Implementation Plan: WeChat Draft MCP

**Workspace**: `wechat-draft-mcp` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

## Summary

Build `wechat-draft-mcp` as an independent TypeScript MCP service under `packages/wechat-draft`, plus a minimal Ali ECS WeChat API adapter. MVP uses WeChat official server APIs only. The NAS-side MCP consumes hermes-db publish-ready artifacts, validates that the artifact is already WeChat-asset-ready, calls the ECS adapter to create a WeChat draft from a stable ECS egress IP, and writes the resulting `media_id` to local job summaries plus `hermes.wechat_articles`.

No non-official write path is part of this feature.

## Architecture Overview

```text
Writing agent / style skill
  - generate Markdown
  - apply account style
  - provide rendered article HTML
  - provide WeChat-hosted body image URLs and cover thumb_media_id
  - preserve image position in body HTML / WeChat asset manifest
  - save publish-ready artifact to hermes-db
        |
        | artifact_id
        v
Hermes / Codex / Claude Code
        |
        | MCP tools
        v
packages/wechat-draft
  - tool contracts + schemas
  - account/adapter config
  - hermes-db artifact reader / ledger writer
  - artifact validator
  - ECS adapter client
  - draft workflow orchestrator
  - local job summary store
        |
        | private HTTP over Tailscale/WireGuard/SSH tunnel
        v
Ali ECS WeChat API adapter
  - AppID/AppSecret refs
  - AccessToken cache/refresh
  - WeChat API allowlist
  - redacted adapter logs
        |
        | HTTPS WeChat API from ECS public IP/EIP
        v
api.weixin.qq.com/cgi-bin/draft/add
        |
        | media_id
        v
hermes.wechat_articles(status=drafted, draft_artifact_id=artifact_id, metadata.media_id)
```

The MCP owns agent-facing tool contracts, artifact validation, idempotency, job summaries, and hermes-db ledger updates. The ECS adapter owns AppID/AppSecret resolution, AccessToken cache/refresh, fixed-public-IP WeChat API egress, and a small allowlist of official WeChat API calls. Upstream agents or a separate asset-prep workflow own content, image handling, cover material preparation, and style generation. `workflow_artifacts.stage` represents content-production readiness; `wechat_articles.status` represents WeChat-side result.
The MCP does not normalize or upload assets inside `wechat_create_draft`: the final artifact must already contain WeChat-hosted body image URLs and a permanent cover `thumb_media_id`.

## Architecture Reference

| Reference | Fit | Non-fit | Stage |
|---|---|---|---|
| Ali ECS WeChat API adapter | Gives WeChat a stable public egress IP and keeps AppSecret/token handling off the NAS. | Does not solve upstream image/style generation or hermes-db access. | MVP |
| Official WeChat API client | `draft/add`, `draft/batchget`, AccessToken and error-code mapping are stable adapter boundaries. | Should not be exposed as broad publish/update/delete surface. | MVP |
| Artifact handoff | `workflow_artifacts` already stores body/ref/hash/metadata and can preserve image positions. | MCP should not create content artifacts from raw Markdown or repair image assets. | MVP |
| Minimal MCP surface | Side-effecting `wechat_create_draft` plus read-only validation/status tools. | No publish tools, delete tools, editor preview tools, or alternate write adapters. | MVP |

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| Writing agent / style skill | `workflow_artifacts(type=wechat_api_article, stage=publish_ready)` | `wechat-draft-mcp` | `wechat_validate_publish_artifact` passes. |
| Hermes-db reader | `PublishReadyArtifact` | Draft workflow | Create-draft refuses invalid account/type/stage/metadata/assets. |
| ECS adapter | `AccessTokenState` | WeChat API call | Draft API call only runs with non-expired token from ECS egress. |
| ECS adapter client | `DraftAddResult(media_id)` | Draft workflow / ledger writer | Successful draft produces `media_id`. |
| Draft workflow | `DraftJob` | Caller / status tool | Returns job id, status, artifact id, account, title, media id. |
| Ledger writer | `ArticleLedgerUpdate` | `hermes.wechat_articles` | Successful draft produces `status=drafted` with `draft_artifact_id` and `metadata.media_id`. |

## Quality Attribute Targets

| Attribute | Target | Design impact | Verification |
|---|---|---|---|
| Safety | No publish/update/delete/mass-send behavior | No such tools or client methods in MVP | Tool list review + API client tests |
| Secret safety | No AppSecret/AccessToken leaks | AppSecret/token stay on ECS adapter; MCP stores only adapter refs; redacted logs | Redaction tests |
| Stable egress | WeChat sees Ali ECS public IP, not home NAS IP or Tailscale IP | Adapter-only live calls; runbook requires ECS IP whitelist evidence | Credential dry-run + live smoke |
| Reuse | Same MCP works for Hermes, Codex, Claude Code | Standard MCP server, artifact-id input | MCP discovery and two client examples |
| Artifact contract | Only WeChat-compatible payload reaches `draft/add` | Strict artifact validation; no upload/normalization in create-draft | Invalid artifact and non-WeChat asset fixture tests |
| Observability | Each side-effect job has compact summary | Local JSONL + article ledger metadata | `wechat_get_draft_status` + ledger row |

## Lightweight ADR

| Decision | Context | Options | Decision | Cost |
|---|---|---|---|---|
| ADR-001 independent service | Need shared draft-writing capability | Independent MCP / extend hermes-db / keep in agents | Independent TS MCP under `packages/wechat-draft` | New service to build |
| ADR-002 official API only | WeChat docs support draft management APIs | Official API / alternate write adapters | MVP uses official API only | Requires API credentials and WeChat-compatible assets |
| ADR-003 credential and egress model | NAS has unstable home egress; AppSecret and AccessToken are high-risk secrets | NAS direct API / ECS proxy / ECS adapter | Ali ECS adapter holds secrets, token cache, and official API egress | New small adapter deployment |
| ADR-004 style and asset boundary | Styles belong to content production; WeChat API refuses external image URLs in final payload | MCP renders content / MCP normalizes assets / upstream or separate asset-prep flow fully prepares WeChat assets | Upstream or a separate asset-prep flow provides rendered article + WeChat-ready assets; MCP only validates | Requires a clear asset-ready artifact contract |
| ADR-005 persistence | Article body and ledger already exist in hermes-db | MCP stores body / workflow_artifacts | Body stays in `workflow_artifacts`; MCP writes ledger only after draft success | MCP needs hermes-db access |

## Key Design Decisions

### Decision 1: Use WeChat Official API as the Only MVP Draft Path

The MCP calls the Ali ECS adapter. The adapter calls:

- `GET /cgi-bin/token` or configured equivalent token provider.
- `POST /cgi-bin/draft/add`.
- Optional read-only `POST /cgi-bin/draft/batchget` for locating recent drafts.

No alternate write adapter is built.

### Decision 2: Publish-ready Artifact Is WeChat API-ready

The MCP does not accept raw Markdown. It requires a hermes-db artifact with:

```text
stage = publish_ready
type = wechat_api_article
metadata.publish_ready = true
metadata.title
metadata.style_profile_id
metadata.style_version
metadata.wechat_asset_manifest.ready = true
metadata.wechat_asset_manifest.body_images[*].wechat_url
metadata.cover.thumb_media_id
```

**素材契约**：

- 微信 `draft/add` 最终 payload 不允许外部图片 URL；MCP 输入也必须已经是微信素材 ready。
- 正文图片：artifact/body HTML 中的图片必须是微信图文图片 URL（例如微信上传接口返回的 `mmbiz.qpic.cn` URL）。
- 封面图片：artifact metadata 必须提供永久素材 `thumb_media_id`。
- 如果 artifact 仍包含非微信图片 URL、本地路径或缺少 `thumb_media_id`，MCP 返回 `invalid_artifact` / `asset_validation`，不下载、不上传、不修复。

If this contract fails, the MCP returns `invalid_artifact` before calling WeChat APIs.

### Decision 3: Ali ECS Adapter Owns Secrets, Token Handling, and WeChat Egress

The adapter owns AppID/AppSecret resolution, AccessToken acquisition, cache, expiry margin, single refresh on token-related errors, redacted error reporting, and outbound HTTPS calls to WeChat. The NAS MCP stores only adapter endpoint/auth references and account mapping. WeChat IP whitelist is configured with the Ali ECS public IP/EIP, not the NAS home IP or Tailscale IP.

### Decision 4: Idempotency Is Required Before Side Effects

`wechat_create_draft(account, artifact_id, idempotency_key?)` derives a stable key from `account + artifact_id + content_hash` when absent. Repeated calls return the existing terminal job when possible and must not silently create duplicate drafts.

## Module Design

### Module: MCP Server

Tools:

```text
wechat_list_accounts()
wechat_check_api_credentials(account, dry_run?)
wechat_validate_publish_artifact(account, artifact_id)
wechat_create_draft(account, artifact_id, idempotency_key?)
wechat_get_draft_status(job_id)
```

`wechat_create_draft` is the only write-side tool in MVP.

Tool contract requirements:

- Register tools with explicit input and output schemas.
- Mark `wechat_create_draft` as side-effecting; keep list/check/validate/status tools read-only or diagnostic.
- Every tool response must include `ok`, `status`, `account`, `timestamp`, and a compact `next_action` when not successful.
- Error types must come from a closed enum: `config`, `credential`, `token`, `artifact_validation`, `asset_validation`, `wechat_api`, `rate_limit`, `ledger`, `lock`, `internal`.
- `wechat_create_draft` must accept an optional `idempotency_key`; if absent, derive one from `account + artifact_id + content_hash`.
- Responses must not include full article body, AppSecret, AccessToken, full HTTP payload, full HTML, or long logs.

### Module: Config Loader

- Load account configs.
- Validate enabled account and adapter refs.
- Keep AppID/AppSecret/AccessToken out of NAS-side source, config, and logs.
- Store adapter base URL, adapter auth ref, account id, and expected egress IP note.
- AppID/AppSecret refs live in the ECS adapter config, not the MCP config.

### Module: Adapter Client

```text
WechatAdapterClient
  health()
  checkCredentials(account, dryRun)
  addDraft(account, articlePayload, idempotencyKey)
  batchGetDrafts(account, offset, count, noContent)
```

Adapter client requirements:

- Use private network endpoint by default, e.g. Tailscale/WireGuard/SSH tunnel URL.
- Authenticate to the adapter using a token or mTLS-equivalent config reference.
- Map adapter transport errors separately from WeChat API errors.
- Never return AppSecret, AccessToken, full article body, full request payload, or full trace.

### Module: ECS WeChat API Adapter

Adapter endpoints:

```text
GET /health
POST /accounts/{account}/check-credentials
POST /accounts/{account}/drafts
POST /accounts/{account}/drafts/batchget
```

Adapter requirements:

- Resolve AppID/AppSecret from ECS env/secret manager.
- Acquire and cache AccessToken with safety margin.
- Serialize token refresh per account.
- Map token errors such as invalid credential, invalid appid, invalid secret, IP whitelist mismatch, frozen AppSecret, and token API disabled.
- Allowlist only credential check, `draft/add`, optional `draft/batchget`.
- Do not implement publish, mass-send, update, delete, schedule, or open proxy behavior.
- Restrict access to NAS/private network callers.

### Module: HermesDbClient

- Read `workflow_artifacts` by `artifact_id`.
- Resolve inline `content_text` or supported `content_ref`.
- Upsert `wechat_articles` after successful draft creation.
- Surface schema drift / missing references as structured errors.

### Module: Artifact Validator

- Validate target account matches artifact account/metadata.
- Validate `stage=publish_ready`, `type=wechat_api_article`, `publish_ready=true`.
- Validate required fields: title, body HTML/content, style profile/version, content hash.
- Validate API limits: title length, author length, digest length, content size/length where enforceable.
- Validate image contract: body image URLs must be WeChat-hosted and cover must provide `thumb_media_id`.
- Extract image URLs from artifact metadata or body HTML only for validation and diagnostics.
- Reject raw Markdown or missing required metadata.

### Module: Draft Workflow

- Validate account and artifact.
- Acquire idempotency lock.
- Build `draft/add` payload from the validated WeChat-ready artifact.
- Call ECS adapter `draft/add`.
- Persist `DraftJob` with returned `media_id`.
- Upsert `wechat_articles.status=drafted`.
- Write local job summary.

### Module: Job Store

- Persist compact JSONL summaries.
- Avoid storing full article content or secrets.
- Support `wechat_get_draft_status`.
- Enforce retention, rotation, and redaction rules from `data-model.md`.
- Store a stable `job_id` and idempotency key so repeated calls can return the previous terminal result instead of creating duplicate drafts.

## Data Model

Detailed model: [data-model.md](data-model.md).

MVP entities:

- `AccountConfig`
- `ApiCredentialConfig`
- `AccessTokenState`
- `EcsWechatAdapterConfig`
- `PublishReadyArtifact`
- `WechatAssetManifest`
- `ArtifactValidationResult`
- `DraftJob`
- `ArticleLedgerUpdate`
- `WechatApiError`

No new database migration is required if current hermes-db workflow/artifacts and article ledger tables are available.

## Project Structure

```text
packages/wechat-draft/
  package.json
  tsconfig.json
  src/
    index.ts
    server.ts
    config/
    hermes/
      HermesDbClient.ts
      ArtifactValidator.ts
    wechat/
      WechatAdapterClient.ts
      WeChatApiErrors.ts
      DraftPayloadBuilder.ts
    workflow/
      DraftWorkflow.ts
      AccountLock.ts
    store/
      JobStore.ts
    schemas/
  config/
    accounts.example.yaml
  tests/

packages/wechat-draft-adapter/
  package.json
  tsconfig.json
  src/
    index.ts
    server.ts
    config/
    auth/
    wechat/
      TokenManager.ts
      WeChatApiClient.ts
      WeChatApiErrors.ts
    schemas/
  config/
    accounts.example.yaml
  tests/
```

## Risks and Tradeoffs

- Official API path requires an ECS adapter deployment and private network path from NAS.
- WeChat API requires body images to be WeChat-hosted and cover to use permanent `thumb_media_id`; MCP rejects artifacts that are not already prepared this way.
- ECS IP whitelist, credential, adapter availability, or private tunnel issues can block all draft writes until operator action.
- MCP depends on hermes-db read/write access and private-network access to the ECS adapter; the adapter depends on outbound HTTPS to WeChat API.
- MCP cannot know final published URL after human publish; later confirmation updates article ledger.

## Operations Runbook Requirements

MVP implementation must ship a compact runbook before live smoke:

- Startup: stdio command, required environment variables, account config path, runtime path, hermes-db access path.
- ECS adapter deployment: service command, systemd/process manager, private listen address, adapter auth, runtime path, log path, and restart policy.
- Credential setup: AppID/AppSecret secret refs on ECS, token cache path on ECS, ECS public IP/EIP whitelist requirement, AppSecret freeze/unfreeze operator note.
- Health checks: MCP startup, adapter `/health`, `wechat_list_accounts`, `wechat_check_api_credentials`, adapter token dry-run, hermes-db schema/ledger check.
- Runtime files: JSONL log rotation, diagnostic artifact directory, permissions, `.gitignore`, and cleanup policy.
- Failure handling: operator SOP for adapter unreachable/private tunnel down, invalid credential, ECS IP whitelist mismatch, frozen AppSecret, rate limit, WeChat API 5xx, hermes-db unavailable, and ledger upsert failure.
- Redaction: logs/traces must not expose AppSecret, AccessToken, full request body, full article content, or personal account data by default.
- Configuration parity: examples must cover local Codex, Claude Code, NAS/Hermes, and ECS adapter usage without committing secrets.

## Evolution Path

- **MVP**: one account, NAS MCP + Ali ECS adapter, rendered WeChat-ready artifact input, draft-only API save, article ledger update.
- **Growth**: multi-account support, richer draft locator/status, notification hooks, and optional direct artifact content-ref fetchers.
- **Mature**: token provider integration and richer upstream integrations that produce WeChat-ready artifacts before `wechat_create_draft`.

## Verification Strategy

1. Unit tests for schemas, artifact validation, adapter client, adapter token manager, WeChat API error mapping, draft payload builder, hermes-db client mapping, and job store.
2. Contract tests for MCP tools and side-effect annotations.
3. HTTP mock tests for MCP -> adapter and adapter -> WeChat `token`, `draft/add`, and `draft/batchget`.
4. Credential dry-run smoke: NAS reaches adapter, adapter reaches WeChat from ECS, token acquisition or expected operator-action error, with secrets redacted.
5. Live guarded smoke: one WeChat-ready test artifact -> adapter calls `draft/add` -> `media_id` -> `wechat_articles.status=drafted`.
6. Operations dry run: verify MCP and adapter runtime path permissions, redacted diagnostic output, stale lock cleanup, adapter restart behavior, and log rotation.

## Stage Readiness

- Next recommended stage: `execute-plan`.
- Blocking items before full implementation:
  - Confirm WeChat-ready artifact `stage/type/metadata/wechat_asset_manifest` contract with writing agent or separate asset-prep workflow.
  - Confirm `yueliang` AppID/AppSecret on Ali ECS adapter and WeChat IP whitelist for ECS public IP/EIP.
  - Confirm NAS can reach ECS adapter through a private channel.
  - Decide hermes-db access path: hermes-db MCP tools vs direct DB client.
  - Write the operations runbook before the first live draft API call.
