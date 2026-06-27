# Feature Specification: WeChat Draft Publish-Ready Facade

**Workspace**: `wechat-draft-publish-ready-facade`
**Created**: 2026-06-27
**Status**: Draft
**Input**: Roadmap current feature: provide one agent-facing facade that composes article-document tools, asset preflight, Hermes artifact persistence, publish-ready validation, and WeChat draft creation.

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | Facade spans source validation/build -> optional artifact upsert -> publish artifact validation -> draft creation -> status result. |
| `external-side-effects` | ✅ | Creates WeChat drafts and may write Hermes workflow artifacts / workflow runs. |
| `artifact-handoff` | ✅ | Consumes `article_document`, `wechat_api_article`, and Hermes workflow artifact IDs. |
| `user-visible-output` | ✅ | Returns draft job/media ID, validation summary, artifact IDs, and actionable failures. |
| `prior-closure-failure` | ✅ | Original pain was 7-20 manual calls and repeated recovery loops for "send to draft". |
| `bugfix-loop-breaker` | ✅ | Must prove the facade reduces manual orchestration without hiding unsafe steps or losing diagnostics. |

**结论**: This feature requires full SDD verification and acceptance. It must compose the already-completed contract hardening, article-document tools, and asset-preflight features; it must not recreate writing generation, real image compression, note skill migration, or draft lifecycle CRUD.

---

## User Scenarios & Testing

### User Story 1 - Create Draft From Existing Publish-Ready Artifact (Priority: P1)

作为 agent，我希望给出已存在的 `publish_ready` `wechat_api_article` artifact ID 后，一次调用完成 validate + create draft，以便不用手动调用 validate 和 create_draft。

**Why this priority**: This is the lowest-risk facade slice because it uses the existing draft workflow and does not need to build or upsert artifacts.

**Acceptance Scenarios**:

1. **US1-1 existing artifact success**
   **Given** agent provides account and an existing `publish_ready` artifact ID
   **When** calling the facade
   **Then** it validates the artifact, calls draft creation, and returns job ID, status, media ID if saved, artifact summary, and phase trace.

2. **US1-2 existing artifact invalid**
   **Given** validation fails
   **When** calling the facade
   **Then** it does not call draft creation and returns validation errors with `next_action=fix_publish_ready_artifact`.

**Edge Cases**:

- **US1-3** Duplicate/idempotent calls must use or expose an idempotency key, not create multiple drafts unexpectedly.
- **US1-4** If draft creation returns `needs_operator_action`, facade must preserve retryability and current phase from lower-level workflow.

### User Story 2 - Create Draft From Article Document Payload (Priority: P1)

作为 agent，我希望给出 canonical `article_document` object 或 JSON string 后，一次调用完成 validate/render/build/upsert/validate/create draft，以便不用手动拼 Hermes artifact 和 HTML。

**Why this priority**: Article document tooling now exists; the facade should compose it into the common "article doc to draft" path.

**Acceptance Scenarios**:

1. **US2-1 article document success**
   **Given** document already has `cover.thumb_media_id` and body images have `wechat_url`
   **When** calling the facade with run/artifact metadata
   **Then** it builds a `publish_ready` payload, upserts it to Hermes, validates it, creates a draft, and returns the publish artifact ID and draft job result.

2. **US2-2 missing body image URL**
   **Given** document references an image asset without `wechat_url`
   **When** calling the facade
   **Then** it stops before artifact upsert/draft creation and returns `next_action=upload_body_images` or equivalent.

3. **US2-3 missing cover thumb**
   **Given** document lacks `cover.thumb_media_id`
   **When** calling the facade
   **Then** it stops before artifact upsert/draft creation and returns `next_action=upload_cover_image`.

**Edge Cases**:

- **US2-4** Facade must not upload/transform images implicitly. It may preflight assets only if image sources are explicitly provided by input.
- **US2-5** `content_text` for persisted publish-ready artifact must be inline HTML, not `content_ref`.

### User Story 3 - Optional Asset Preflight Gate (Priority: P2)

作为 agent，我希望 facade can optionally preflight declared assets before building/publishing, so invalid assets are caught before render/build/draft creation.

**Why this priority**: Asset preflight exists and should be used by the facade when source metadata is present, without introducing automatic compression.

**Acceptance Scenarios**:

1. **US3-1 preflight declared assets**
   **Given** input includes body/cover image sources and `preflight_assets=true`
   **When** calling the facade
   **Then** it runs preflight and returns diagnostics if any asset is invalid.

2. **US3-2 no implicit compression**
   **Given** an asset is oversized
   **When** facade preflight fails
   **Then** it returns transform recommendation and does not compress or upload automatically.

**Edge Cases**:

- **US3-3** If only prepared `wechat_url` / `thumb_media_id` are provided, preflight is not required.
- **US3-4** Preflight failures must not create drafts or write publish-ready artifacts.

### User Story 4 - Phase Trace And Recovery Contract (Priority: P1)

作为 agent，我希望 facade 返回清晰的 phase trace、intermediate artifacts、next action 和 retryability，以便失败后从正确阶段恢复。

**Why this priority**: Facade hides orchestration complexity; it must not hide where and why the workflow stopped.

**Acceptance Scenarios**:

1. **US4-1 phase trace on success**
   **Given** facade succeeds
   **When** response is returned
   **Then** it includes phases such as `input_validation`, `asset_preflight`, `artifact_build`, `artifact_upsert`, `publish_validation`, `draft_create`.

2. **US4-2 phase trace on failure**
   **Given** a phase fails
   **When** response is returned
   **Then** it includes `current_phase`, completed phases, generated artifact IDs if any, `next_action`, and `retryable`.

**Edge Cases**:

- **US4-3** If draft was already created but ledger update failed, facade must preserve the draft result and mark ledger issue separately, matching lower-level workflow semantics.

---

## Requirements

### Functional Requirements

- **FR-001**: MCP must expose a facade tool for creating a draft from an existing publish-ready artifact ID.
- **FR-002**: MCP must expose or include a facade mode for creating a draft from `article_document` object/JSON string by building a publish-ready artifact payload first.
- **FR-003**: Facade must validate publish-ready artifacts before draft creation and skip draft creation on validation failure.
- **FR-004**: Facade must create or upsert the required Hermes workflow run/artifact when operating from article-document input, or clearly fail with a structured action if Hermes write support is unavailable.
- **FR-005**: Facade must preserve idempotency controls for draft creation and must expose the idempotency key used.
- **FR-006**: Facade must return phase trace, intermediate artifact IDs/payload summaries, validation summary, draft job result, and remediation fields.
- **FR-007**: Facade must optionally run asset preflight for explicitly supplied asset sources, without performing real compression or implicit upload.
- **FR-008**: Facade must reuse existing article-document render/build, asset preflight, publish validation, and draft creation paths instead of duplicating their logic.
- **FR-009**: Facade errors must use existing remediation envelope and must not leak raw SQL, raw filesystem paths, tokens, or adapter secrets.

### Non-Functional Requirements

- **NFR-001**: Tests must not perform real WeChat draft writes; use mocked adapter/workflow/Hermes clients.
- **NFR-002**: Existing low-level tools must remain available and backward-compatible.
- **NFR-003**: Facade must not introduce content generation, title generation, rewriting, style review, or note skill migration.
- **NFR-004**: The article-document path must be deterministic for the same input and idempotency key.
- **NFR-005**: No real image compression or cover channel switch in this feature.

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 可恢复性 | Every stopped phase has next action | Facade hides multiple tools; recovery must stay visible | phase trace tests | 是 |
| 一致性 | Reuse existing lower-level modules | Avoid duplicate render/upload/draft semantics | tests assert helper/service composition | 是 |
| 安全性 | No sensitive leakage | Facade aggregates many errors | sanitization/error tests | 是 |
| 幂等性 | Repeated calls do not create unintended duplicate drafts | Draft creation is external side effect | idempotency tests | 是 |
| 可演进性 | Later ops CRUD/versioning can consume facade outputs | Roadmap depends on this as stable surface | typed output contract | 是 |

### Key Entities

- **PublishReadyFacadeInput**: account, mode/source, artifact IDs/run metadata, idempotency key, preflight flags.
- **PhaseTrace**: ordered phase statuses, current phase, completed phases, generated IDs, stopped reason.
- **FacadeDraftResult**: draft job result plus publish artifact summary and recovery metadata.
- **PublishReadyArtifactUpsertPayload**: payload generated by article-document builder and persisted through Hermes when supported.

---

## Out of Scope

- 不生成、改写、润色、审核文章内容。
- 不迁移 note skill，不处理 Library/Memory ingestion。
- 不实现真实图片压缩，不改变 cover/body image constraints。
- 不实现 draft list/update/delete/schedule/group-send。
- 不做运营 UI。
- 不替代低层 tools；低层 tools 必须继续可单独调用。
- 不实现 generic Hermes artifact versioning/diff，除非 plan 判断 facade cannot work without a minimal Hermes upsert client wrapper.

---

## Unclear Questions

- Existing `HermesDbClient` currently lacks workflow artifact upsert. Plan must decide whether to extend it for `upsert_workflow_artifact`, or limit MVP facade to existing artifact mode plus "build payload only" for article-document mode.
- Should facade be one tool with `source_type` modes, or two tools: `wechat_prepare_publish_ready_artifact` and `wechat_create_draft_facade`? Initial preference: one agent-facing facade for existing artifact mode, and a separate internal/service method for preparation if needed.
- Should facade auto-ensure workflow run? Initial preference: yes inside article-document mode if Hermes write support is added; existing artifact mode should not mutate runs.

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项：无。Hermes write support is an implementation-scope decision for plan, not a spec blocker.
