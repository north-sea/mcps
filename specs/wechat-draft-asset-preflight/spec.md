# Feature Specification: WeChat Draft Asset Preflight

**Workspace**: `wechat-draft-asset-preflight`
**Created**: 2026-06-27
**Status**: Draft
**Input**: Roadmap next feature after `wechat-article-document-tools`: add asset probing, clearer local path diagnostics, and explicit preflight/compression support for WeChat cover/body images.

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | Asset flow spans source probing -> validation -> optional transform recommendation/compression -> upload -> article document/render/build. |
| `external-side-effects` | ✅ | If compression is implemented it writes transformed files or buffers; upload remains a separate existing side-effecting tool. |
| `artifact-handoff` | ✅ | Output asset metadata feeds article document assets and cover fields. |
| `user-visible-output` | ✅ | Agents/operators see diagnostics, transformed asset stats, and next actions. |
| `prior-closure-failure` | ✅ | Original draft run failed on opaque image size/path constraints and manual compression retries. |
| `bugfix-loop-breaker` | ✅ | Must prevent repeated trial-and-error upload failures by proving constraints and diagnostics before upload. |

**结论**: 本 feature 启用 workflow、external-side-effects、artifact handoff、user-visible output 和 bugfix-loop-breaker 强化规则。Plan 必须区分 pure preflight/probe、optional local transform、and existing upload tool；不得把 publish-ready facade 或 draft creation 混入。

---

## User Scenarios & Testing

### User Story 1 - Probe Asset Before Upload (Priority: P1)

作为 agent，我希望在上传前探测本地或远程图片的 MIME、大小、尺寸、是否符合账号 constraints，以便不用通过上传失败才知道问题。

**Why this priority**: 当前 constraints 已可发现，但 agent 仍需要自己下载/读文件/算大小，且容器路径不可达错误不够直观。

**Acceptance Scenarios**:

1. **US1-1 probe local image**
   **Given** agent 提供 `local_path`、usage=`body_image` 或 `cover_image`
   **When** 调用 asset preflight/probe tool
   **Then** 返回 MIME、byte size、文件可读性、matched constraint、pass/fail、next action。

2. **US1-2 probe remote image**
   **Given** agent 提供 `remote_url`
   **When** 调用 probe tool
   **Then** tool fetches headers/content as needed, returns status, content type, byte size if available, and whether it can be uploaded as-is.

**Edge Cases**:

- **US1-3** local path outside `ASSET_ROOT` must return `next_action=use_accepted_path_or_remote_url` and include accepted prefixes, not raw `realpath ENOENT`.
- **US1-4** remote URL fetch failure must be retryable when network/status suggests transient failure, non-retryable for invalid URL/protocol.
- **US1-5** unknown MIME or missing extension should return a recoverable diagnostic, not infer unsafe defaults.

### User Story 2 - Recommend Or Perform Explicit Compression (Priority: P1)

作为 agent，我希望知道图片能否压到 WeChat 限制内，并在明确请求时获得压缩后的可上传资产，以便避免反复手动压图。

**Why this priority**: 封面 64KB 和正文 1MB 是最常见失败点；但自动静默压缩会改变用户素材质量，必须显式。

**Acceptance Scenarios**:

1. **US2-1 dry-run transform plan**
   **Given** image exceeds usage constraints
   **When** agent calls preflight with dry-run/plan mode
   **Then** returns transform recommendations such as resize, quality, output format, estimated target, and quality caveats.

2. **US2-2 explicit compression output**
   **Given** agent opts into compression
   **When** compression succeeds
   **Then** returns transformed asset location or bytes reference, output MIME, size, dimensions, and upload-ready source metadata.

**Edge Cases**:

- **US2-3** If target cannot be reached without severe quality loss, return `needs_operator_action`, not a misleading "success".
- **US2-4** Do not silently convert cover to unsupported MIME; cover remains JPEG/thumb unless a later live-verified channel change is implemented.
- **US2-5** Compression output must be deterministic enough for tests and must not overwrite user source files.

### User Story 3 - Upload With Preflight Guard (Priority: P2)

作为 agent，我希望 upload tool can optionally run preflight first and return the same diagnostics when it refuses an asset, so I can recover without separate guesswork.

**Why this priority**: Existing `wechat_upload_asset` already validates size/MIME. The next improvement is making its failure details and optional preflight path match the new preflight tool.

**Acceptance Scenarios**:

1. **US3-1 upload returns preflight summary on rejection**
   **Given** `wechat_upload_asset` rejects size/MIME/source
   **When** response is returned
   **Then** details include a preflight-style summary: usage, source_type, bytes, limit, MIME, accepted prefixes/protocols, and next action.

2. **US3-2 optional preflight flag**
   **Given** agent passes `preflight=true` or equivalent
   **When** upload is attempted
   **Then** tool probes and reports validation result before adapter upload; adapter is not called if preflight fails.

**Edge Cases**:

- **US3-3** Existing upload behavior without the flag must remain backward-compatible.
- **US3-4** Upload still does not auto-compress unless explicit transform input is provided.

### User Story 4 - Preserve Official WeChat Constraints (Priority: P2)

作为维护者，我希望 feature 不把未验证的运营推测写成确定能力，以免后续创建草稿失败。

**Why this priority**: 复盘中“正文图 10MB”“封面直接切 image 通道”并不都能直接采纳。

**Acceptance Scenarios**:

1. **US4-1 constraints remain conservative**
   **Given** preflight reports constraints
   **When** usage=`body_image`
   **Then** body image limit remains aligned to uploadimg 1MB unless official/live evidence changes.

2. **US4-2 cover channel remains explicit**
   **Given** usage=`cover_image`
   **When** preflight reports constraints
   **Then** cover remains `thumb`/64KB JPEG; alternate image channel is marked experimental/deferred unless live smoke proves it.

**Edge Cases**:

- **US4-3** Any future alternate channel must be introduced as a separate feature or explicit experimental flag with evidence.

---

## Requirements

### Functional Requirements

- **FR-001**: MCP 必须提供 asset probe/preflight 能力，返回 source readability/fetch status、MIME、byte size、dimensions where available、constraint match、validation result。
- **FR-002**: local path diagnostics must expose accepted path prefixes and distinguish path outside root, missing file, unreadable file, and unsupported source type.
- **FR-003**: remote URL diagnostics must distinguish invalid URL/protocol, fetch failure, HTTP status failure, missing content type/length, and unsupported MIME/size.
- **FR-004**: MCP must support dry-run transform recommendation for oversized or unsupported assets.
- **FR-005**: If compression/transform is implemented in this feature, it must be explicit, non-destructive, and return transformed asset metadata suitable for `wechat_upload_asset`.
- **FR-006**: `wechat_upload_asset` failures must include preflight-style diagnostics and remain backward-compatible.
- **FR-007**: Constraints must remain aligned with current official WeChat API behavior: body `uploadimg` under 1MB; cover `thumb` 64KB JPEG unless separately verified.
- **FR-008**: All errors must use the existing remediation envelope and avoid leaking sensitive absolute paths beyond accepted prefixes.

### Non-Functional Requirements

- **NFR-001**: No real WeChat upload is required for preflight tests.
- **NFR-002**: Transform tests must use small deterministic fixtures and avoid large binary churn in git.
- **NFR-003**: Preflight must not overwrite source files.
- **NFR-004**: Network-dependent remote tests must use local test servers or mocks.
- **NFR-005**: Do not introduce heavyweight image dependencies without plan-stage justification.

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 可恢复性 | every failed asset path has a next action | Agent should recover without upload trial-and-error | preflight and upload tests | 是 |
| 安全性 | no sensitive full path/token/header leakage | Local path and remote fetch errors may contain private data | sanitized details tests | 是 |
| 一致性 | preflight and upload guards use same constraints | Prevent drift between advice and enforcement | shared helper tests | 是 |
| 成本 | no unnecessary network/download work | Remote probing can be expensive | plan defines fetch strategy | 是 |
| 可演进性 | future facade can reuse preflight output | Publish-ready facade depends on this | typed output contract | 是 |

### Key Entities

- **AssetPreflightInput**: usage, source_type, source, optional filename/MIME, mode/dry-run flags.
- **AssetPreflightResult**: source diagnostics, detected metadata, constraints, pass/fail, recommendations, transformed asset reference if requested.
- **TransformRecommendation**: resize/format/quality plan and caveats.
- **TransformedAsset**: non-destructive local artifact or buffer reference suitable for upload.

---

## Out of Scope

- 不创建草稿、不写 hermes-db、不构造 article document。
- 不放宽正文图到 5MB/10MB；正文仍按 `media/uploadimg` 1MB。
- 不直接把封面切到永久 `image` 通道；该假设需要 live evidence 后另做 feature。
- 不做批量队列、运营 UI、草稿 CRUD、定时发布。
- 不自动静默压缩用户素材；压缩必须显式请求。
- 不引入通用媒体资产管理系统。

---

## Unclear Questions

- 是否在本 feature 实现真实压缩，还是只实现 probe + transform recommendation。初始倾向：plan 阶段评估现有依赖后决定；若无合适依赖，先做 recommendation，不引入重依赖。
- transformed asset 返回本地路径还是 bytes/base64 reference。初始倾向：返回 runtime-managed local path under accepted asset root or temp transform root, not inline base64.
- 是否新增独立 `wechat_preflight_asset` tool，还是扩展 `wechat_upload_asset(preflight=true)`。初始倾向：两者都需要：独立 preflight for dry-run，upload 复用其 diagnostics。

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项：无。压缩实现深度可在 plan 阶段通过依赖和 YAGNI 判断确定。
