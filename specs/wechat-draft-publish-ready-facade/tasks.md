# Tasks: WeChat Draft Publish-Ready Facade

**Workspace**: `wechat-draft-publish-ready-facade` | **Date**: 2026-06-27
**Input**: `specs/wechat-draft-publish-ready-facade/spec.md` + `plan.md`
**Prerequisites**: spec.md, plan.md

---

## 执行原则

- Facade composes existing service methods; do not duplicate render/preflight/draft logic.
- Existing low-level tools remain available and backward-compatible.
- Article-document mode may write Hermes workflow run/artifact and create WeChat draft; phase trace must expose each side-effect boundary.
- No writing generation, real image compression, draft CRUD, scheduling, or generic artifact versioning.

---

## Phase 1: Baseline And Contract

**目标**: 固定当前 orchestration 缺口和 facade result contract。

- [x] T001 [Bugfix] 记录 before evidence 和 failed-attempt ledger
  - scope: `specs/wechat-draft-publish-ready-facade/verify-evidence.md`
  - slice: 证明当前 tools 已具备低层能力，但没有 one-call validate/build/upsert/create-draft facade。
  - blocked_by: none
  - maps_to: Bugfix Context / prior-closure-failure
  - verify: evidence includes current tool list, Hermes client wrapper gap, and no facade tool.

- [x] T002 [Foundation] 定义 facade schemas and phase trace types
  - scope: `tool-schemas.ts`
  - slice: `CreateDraftFacadeInput/Output` supports `publish_ready_artifact` and `article_document` modes, phase trace, idempotency key, validation summary, draft result, upsert outcome.
  - blocked_by: T001
  - maps_to: FR-001..FR-006 / ADR-001
  - verify: TypeScript build and tests compile against typed input/output.

---

## Phase 2: Hermes Client Write Wrappers

**目标**: 让 article-document mode 可以真正写入 publish-ready artifact，而不是把 upsert 再推回 agent。

- [x] T003 [Hermes] Add workflow run/artifact upsert wrappers
  - scope: `HermesDbClient.ts`, tests or service fakes
  - slice: client can call existing Hermes MCP `upsert_workflow_run` and `upsert_workflow_artifact`, preserving structured tool errors.
  - blocked_by: T002
  - maps_to: FR-004 / ADR-002
  - verify: mocked `fetch` or service fake asserts correct tool names/arguments and error passthrough.

---

## Phase 3: Existing Publish Artifact Facade Slice

**目标**: 已有 publish-ready artifact 一次调用完成 validate + create draft。

- [x] T004 [US1] Implement existing artifact mode
  - scope: `WechatDraftService.ts`, service tests
  - slice: input artifact ID -> validatePublishArtifact -> createDraft -> facade output with phase trace and idempotency key.
  - blocked_by: T002
  - maps_to: US1 / FR-001 / FR-003 / FR-005 / FR-006
  - verify: success test asserts validate before draft and response includes draft job/media; invalid validation skips draft.

- [x] T005 [US4] Preserve lower-level draft failure details
  - scope: `WechatDraftService.ts`, tests
  - slice: non-saved draft result preserves `current_phase`, `next_action`, `retryable`, and phase trace.
  - blocked_by: T004
  - maps_to: US4 / FR-006 / FR-009
  - verify: test with workflow returning `needs_operator_action`.

---

## Phase 4: Article Document Facade Slice

**目标**: article_document 一次调用完成 build/upsert/validate/create draft。

- [x] T006 [US2] Implement article document build/upsert path
  - scope: `WechatDraftService.ts`, `HermesDbClient.ts`, tests
  - slice: article document -> buildPublishReadyArtifact -> upsert workflow run -> upsert artifact -> validate -> create draft.
  - blocked_by: T003, T004
  - maps_to: US2 / FR-002 / FR-004 / FR-008
  - verify: test asserts upsert run/artifact called and draft uses publish artifact ID.

- [x] T007 [US2/US3] Stop before side effects on missing prepared assets
  - scope: `WechatDraftService.ts`, tests
  - slice: missing body `wechat_url` or cover `thumb_media_id` returns lower-level next_action and does not call Hermes upsert/draft.
  - blocked_by: T006
  - maps_to: US2 / US3 / FR-007 / FR-009
  - verify: tests assert no Hermes write/draft calls on build/preflight failure.

- [x] T008 [US4] Surface Hermes upsert conflicts/errors
  - scope: `WechatDraftService.ts`, tests
  - slice: Hermes `artifact_id_conflict` or missing run/upsert error is surfaced with current phase `artifact_upsert`, next action, and generated payload summary.
  - blocked_by: T006
  - maps_to: FR-004 / FR-006 / FR-009
  - verify: fake Hermes client returns structured error and facade preserves it.

---

## Phase 5: MCP Tool And Docs

**目标**: agent can discover and call the facade; docs recommend it as happy path.

- [x] T009 [MCP] Register `wechat_create_draft_facade`
  - scope: `createMcpServer.ts`, HTTP MCP smoke
  - slice: MCP tool is discoverable and described as side-effecting; existing low-level tools remain registered.
  - blocked_by: T004, T006
  - maps_to: FR-001 / NFR-002
  - verify: HTTP MCP smoke `listTools` includes facade and low-level tools.

- [x] T010 [Docs] Update agent-facing draft flow
  - scope: `docs/article-document-artifact-example.md`
  - slice: docs recommend facade for common path and low-level tools for debugging/manual recovery.
  - blocked_by: T009
  - maps_to: NFR-003 / roadmap boundary
  - verify: static review confirms no writing generation/image compression/draft CRUD instructions.

---

## Phase 6: Verification And Closeout

**目标**: fresh evidence and acceptance.

- [x] T011 [Bugfix] Diffusion check
  - scope: source/docs/specs
  - slice: facade does not duplicate renderer/preflight/draft logic, and errors use remediation envelope.
  - blocked_by: T010
  - maps_to: Bugfix Loop Breaker
  - verify: `rg` findings recorded in `verify-evidence.md`.

- [x] T012 [Verify] Run build/test/checks
  - scope: `packages/wechat-draft`, `verify-evidence.md`
  - slice: component/workflow contract evidence.
  - blocked_by: T011
  - maps_to: Verification Strategy
  - verify: record build, test, `git diff --check`.

- [x] T013 [Closeout Prep] Acceptance and roadmap update
  - scope: `acceptance.md`, roadmap
  - slice: closeout can judge PASS/PARTIAL/FAIL and next feature.
  - blocked_by: T012
  - maps_to: Acceptance Gate / Knowledge Capture
  - verify: acceptance inputs ready.

---

## 依赖与顺序

- 关键路径：T001 -> T002 -> T003/T004 -> T005/T006 -> T007/T008 -> T009 -> T010 -> T011 -> T012 -> T013。
- T003 and T004 can proceed after schemas stabilize.
- T006 requires Hermes wrappers and existing artifact mode helpers.
- T009 must wait until both facade modes are stable.

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|-------------|----------|
| US1 existing publish artifact facade | T004, T005, T009 |
| US2 article document facade | T006, T007, T008 |
| US3 optional asset preflight gate | T007 |
| US4 phase trace/recovery | T002, T005, T008 |
| Bugfix loop breaker | T001, T011, T012, T013 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|----------------------|----------|----------|
| ADR-001 one facade tool | T002, T009 | T012 |
| ADR-002 minimal Hermes wrappers | T003, T006, T008 | T012 |
| ADR-003 compose existing methods | T004, T006, T011 | T012 |
| ADR-004 no implicit upload/compression | T007, T010 | T011 |
| 可恢复性 | T005, T007, T008 | T012 |
| 幂等性 | T004, T005 | T012 |
| 安全性 | T008, T011 | T012 |

---

## Context Manifest

已生成 `context-manifest.md`。本 feature 命中多项 traits，并新增 WeChat draft/Hermes 写副作用 facade，必须保留实现和验证上下文。

---

## Stage Readiness

- 推荐下一步：`implement`
- 阻塞项：无。
- 原因：13 个任务覆盖 spec/plan 的 P1/P2 场景、ADR、质量属性和 bugfix-loop-breaker。
