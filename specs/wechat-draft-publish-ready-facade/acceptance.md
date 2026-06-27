# Acceptance Record: WeChat Draft Publish-Ready Facade

**Workspace**: `wechat-draft-publish-ready-facade` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| FR-001 existing publish-ready artifact facade | `wechat_create_draft_facade` supports `source_type="publish_ready_artifact"` and validates before draft creation. | `WechatDraftService.createDraftFacade creates a draft from an existing publish_ready artifact`; `createMcpServer.ts` | PASS |
| FR-002 article_document facade mode | `source_type="article_document"` builds publish-ready payload, upserts Hermes run/artifact, validates, then creates draft. | `WechatDraftService.createDraftFacade builds, upserts, validates, and creates from article_document` | PASS |
| FR-003 validation gate before draft | Invalid publish-ready validation returns `artifact_validation_failed` and does not call draft workflow. | `WechatDraftService.createDraftFacade stops before draft creation when publish_ready validation fails` | PASS |
| FR-004 Hermes workflow writes | `HermesDbClient` wraps `upsert_workflow_run` / `upsert_workflow_artifact`; facade surfaces Hermes conflict remediation. | `HermesDbClient.ts`; `WechatDraftService.createDraftFacade preserves Hermes remediation on artifact upsert conflict` | PASS |
| FR-005 idempotency key exposure | Facade forwards explicit idempotency key and returns the final key used. | `WechatDraftService.createDraftFacade creates a draft from an existing publish_ready artifact` | PASS |
| FR-006 phase trace and remediation | Success returns phase trace; validation/build/Hermes/draft failures preserve `current_phase`, `next_action`, `retryable`, and details. | `WechatDraftService.facade.test.ts`; `verify-evidence.md` Diffusion Check | PASS |
| FR-007 asset preflight boundary | Article mode stops before Hermes writes when prepared cover/body assets are missing; no implicit compression/upload added. | `WechatDraftService.createDraftFacade returns article_document remediation before Hermes writes`; `rg` diffusion check | PASS |
| FR-008 reuse existing paths | Facade composes `buildPublishReadyArtifact`, `validatePublishArtifact`, and `createDraft`; no renderer/workflow duplication. | `WechatDraftService.ts`; `verify-evidence.md` Diffusion Check | PASS |
| FR-009 structured errors | Hermes conflict, article build failure, validation failure, and non-saved draft preserve remediation envelope without raw SQL/path/secret exposure. | Facade service tests; existing `errorMapping` / workflow tests still pass | PASS |
| NFR-001 no live WeChat writes in tests | Verification uses fakes/mocks and HTTP MCP smoke discovery only. | `pnpm --filter @mcps/wechat-draft test` 64/64 PASS | PASS |
| NFR-002 low-level compatibility | Existing low-level tools remain registered; HTTP MCP smoke still exercises `wechat_create_draft`. | `HTTP MCP smoke calls list accounts and create draft through Streamable HTTP` | PASS |
| NFR-003 no upstream generation/migration | No content generation, note migration, draft CRUD, scheduling, or version diff implementation added. | `verify-evidence.md` Diffusion Check | PASS |

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Schema, Hermes client wrappers, service facade, MCP registration, and tests are present. |
| Workflow closure | PASS | Existing artifact path and article-document path both close through validate/create draft with phase trace. |
| User-visible outcome | PASS | Agents can discover one facade tool and receive idempotency key, phase trace, validation summary, draft result, and remediation fields. |

**Overall**: PASS

## Workflow Replay

- **输入摘要**: fixture `article_document` with prepared `cover.thumb_media_id` and body image `wechat_url`.
- **最终 payload 摘要**: facade returned `publish_artifact_id`, `upsert_outcome`, `validation_summary.valid=true`, and `draft.status=saved`.
- **用户可见结果断言**: MCP exposes `wechat_create_draft_facade`; service response contains phase trace and draft job result.
- **Replay 类型**: fixture。真实 WeChat draft write intentionally skipped by NFR-001.

## Bugfix Closure

| Field | Value |
|---|---|
| Root Cause / Hypothesis | Prior chain forced agents to manually compose build/upsert/validate/create-draft phases; recovery context was split across tools. |
| Fix Mechanism | Added a facade tool and service method that composes existing deterministic helpers and wraps each side-effect boundary in `phase_trace`. |
| Prevention Mechanism | Facade tests cover happy paths, validation stop, build stop, Hermes conflict, and non-saved draft remediation. |
| Failed Attempts Summary | Rejected “build payload only” because it preserved manual Hermes upsert; rejected implicit compression/upload because it belongs to asset-preflight or later image pipeline work. |
| Regression Guard | `pnpm --filter @mcps/wechat-draft build`; `pnpm --filter @mcps/wechat-draft test` 64/64 PASS; `git diff --check` PASS. |
| Diffusion Check | `rg` for compression/CRUD/scheduling/versioning keywords only matched boundary docs/specs, not implementation. |
| Remaining Risk | No live WeChat draft creation in this feature; runtime verification remains a release/deployment follow-up. |

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | 不适用 | Low-level tools intentionally remain available as manual recovery/debug path. | 无 |
| 发布、提交、CI 或 follow-through | 延后 | Local build/test/check pass; no commit/CI/deploy requested or executed. | 用户确认后再提交/部署 |
| 文档、阶段说明、模板或验收记录更新 | 已完成 | `docs/article-document-artifact-example.md` now recommends facade happy path and low-level recovery path. | 无 |
| ADR、架构债或演进触发信号 | 已完成 | ADR boundary retained: no image compression, no draft CRUD, no generic artifact versioning inside facade. | Hermes versioning remains next conditional feature |
| Knowledge Capture | 已完成 | Decision/pattern/follow-up recorded below. | 无 |

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| pattern | Facade Over Low-Level Tools | Agent-facing MCPs should expose one happy-path facade while keeping low-level tools for recovery. The facade should return a phase trace around each side-effect boundary. | `plan.md` ADR-001/003; `WechatDraftService.facade.test.ts` | WeChat draft MCP orchestration tools | recorded-only | 无 |
| decision | No Implicit Compression | Publish-ready facade does not compress or upload images implicitly. Prepared `wechat_url` / `thumb_media_id` remain required until a separate image pipeline feature owns that behavior. | `spec.md` NFR-005; `verify-evidence.md` Diffusion Check | WeChat article-document to draft path | recorded-only | 无 |
| follow-up | Live Draft Smoke | Local tests prove component/workflow contracts but not real WeChat draft creation. A release smoke can validate adapter/Hermes integration after deployment. | `acceptance.md` Workflow Replay | Deployment/release verification | follow-up | Run live smoke only with explicit account/operator approval |

## Commit Result

| Field | Value |
|---|---|
| Status | not_submitted |
| Commit Hashes | 无 |
| Commit Messages | 无 |
| Included Files | 无 |
| Excluded / Remaining Files | 工作树含多个本 roadmap 历史 feature 和当前 feature 文件；未获用户提交确认。 |
| Reason | SDD closeout 不自动 `git add` / `git commit`。 |

## Completion Record

- **最终结论**: PASS
- **完成依据**: Evidence Table 全部 PASS；Workflow Replay fixture PASS；build/test/diff-check PASS。
- **阻塞项**: 无。
- **延后项**: live WeChat draft smoke、提交、部署。
- **退役结论**: 不退役低层工具；它们作为调试和手动恢复路径保留。
- **提交结论**: not_submitted。
- **后续动作**: 更新 roadmap，推荐进入 `hermes-artifact-versioning-and-diff` 的 specify/plan 判断。
