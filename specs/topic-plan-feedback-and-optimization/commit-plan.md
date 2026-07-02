# Commit Plan: Topic Plan Feedback And Optimization

**Workspace**: `topic-plan-feedback-and-optimization`
**Date**: 2026-07-02
**Status**: Confirmed For Submission And Deployment

> Commit plan 是提交前的用户确认 gate。未获得用户明确确认前，不得执行 `git add` 或 `git commit`。

---

## Summary

当前 feature 有相关 diff，建议 1 个 commit 提交 P1 feedback/report contract 与 SDD completion records。工作树中还存在多组无关 dirty/untracked 文件，必须排除。

---

## Included Files

| File | Reason | Evidence |
|---|---|---|
| `packages/hermes-db/migrations/versions/0011_topic_plan_feedback.py` | P1 feedback event schema migration | T001, FR-001..FR-003C |
| `packages/hermes-db/src/hermes_db_mcp/repositories/topic_plan_feedback_repo.py` | P1 record/list/report repository | T004, T006, T008-T010 |
| `packages/hermes-db/src/hermes_db_mcp/tools/topic_plan_feedback.py` | P1 MCP tools for record/list/report | T005, T007, T011 |
| `packages/hermes-db/pyproject.toml` | bump hermes-db package version for service tag deploy | Release follow-through |
| `packages/hermes-db/src/hermes_db_mcp/config.py` | bump runtime health version for release | Release follow-through |
| `deploy/mcp-services.json` | include `topic_plan_feedback` in NAS deploy smoke capabilities | Release follow-through |
| `packages/hermes-db/src/hermes_db_mcp/services/schema.py` | schema health inspector for feedback capability | T003 |
| `packages/hermes-db/src/hermes_db_mcp/tools/health.py` | `health.capabilities.topic_plan_feedback` wiring | T013 |
| `packages/hermes-db/src/hermes_db_mcp/server.py` | register feedback MCP tool module | T012 |
| `packages/hermes-db/tests/test_migration_sql.py` | migration text assertions | T002 |
| `packages/hermes-db/tests/test_topic_plan_feedback_schema_health.py` | feedback schema health tests | T003 |
| `packages/hermes-db/tests/test_topic_plan_feedback_repo_sql.py` | record/list/report repo tests | T004, T006, T008-T010 |
| `packages/hermes-db/tests/test_topic_plan_feedback_tools.py` | record/list/report tool tests | T005, T007, T011 |
| `packages/hermes-db/tests/test_health.py` | health capability test update | T013 |
| `specs/topic-plan-feedback-and-optimization/spec.md` | final SDD spec state and closeout status | Completion record |
| `specs/topic-plan-feedback-and-optimization/plan.md` | implementation plan and ADRs | Completion record |
| `specs/topic-plan-feedback-and-optimization/data-model.md` | schema/DTO/report metric model | Completion record |
| `specs/topic-plan-feedback-and-optimization/tasks.md` | task status and evidence | Completion record |
| `specs/topic-plan-feedback-and-optimization/context-manifest.md` | implement/check context | Completion record |
| `specs/topic-plan-feedback-and-optimization/verify-evidence.md` | focused verification package | T017 |
| `specs/topic-plan-feedback-and-optimization/acceptance.md` | closeout acceptance record | Closeout |
| `specs/topic-plan-feedback-and-optimization/commit-plan.md` | commit confirmation plan | Closeout |

---

## Excluded Files

| File | Reason |
|---|---|
| `specs/.active` | Existing unrelated active-feature state; this feature intentionally did not switch active. |
| `specs/wechat-draft-http-service/tasks.md` | Unrelated dirty file from prior work. |
| `.pnpm-store/` | Runtime/package cache, not feature source. |
| `DEPLOYMENT_SUMMARY.md` | Unrelated untracked deployment doc. |
| `NAS_DEPLOYMENT_GUIDE.md` | Unrelated untracked deployment doc. |
| `scripts/nmem-nas-domain-sync.sh` | Unrelated untracked script. |
| `scripts/nmem-space-map.example.json` | Unrelated untracked example config. |
| `specs/agents-capability-reconciliation/` | Unrelated feature directory. |
| `specs/agents-wechat-content-runtime-fixes/` | Unrelated feature directory. |
| `specs/knowledge-memory-architecture/` | Unrelated feature directory. |
| `specs/note-skill-inventory-matrix/` | Unrelated feature directory. |
| `specs/note-skill-migration-roadmap/` | Unrelated feature directory. |
| `specs/wechat-content-runtime-contracts/` | Unrelated feature directory. |
| `specs/wechat-draft-http-service/acceptance.md` | Unrelated feature artifact. |
| `specs/wechat-topic-draft-trial/` | Unrelated feature directory. |

---

## Needs User Decision

| File | Why Uncertain | Question |
|---|---|---|
| none | All included files are scoped to this feature; unrelated files are excluded. | 无 |

---

## Risks

| Risk | Impact | Handling |
|---|---|---|
| untracked unrelated files | Accidental broad add would commit unrelated work | Use explicit `git add <included files only>`; never `git add -A`. |
| P2 deferred task | Commit contains P1 only and leaves `T015` unchecked with defer note | Acceptance records CONDITIONAL PASS and follow-up. |
| local focused tests only | Full repo/CI not run | Commit message should mention focused test scope; CI can run after commit. |

---

## Commit Batches

| Batch | Files | Commit Message | Rationale |
|---|---|---|---|
| 1 | All Included Files | `feat(hermes-db): add topic plan feedback reporting` | Single cohesive feature: schema, tools, tests, SDD records. |

---

## Execution Rules

- 未获得用户明确确认前，不得执行 `git add` 或 `git commit`。
- 只允许 add `Included Files` 中属于已确认 batch 的文件。
- 不得使用 `git add -A`、`git add .` 或等价宽泛命令。
- 每个 batch 单独提交；任一 batch 失败时停止后续 batch。
- 不自动执行 `git push`。push 必须由用户另行明确要求。

---

## User Confirmation

等待用户确认：

- `确认提交`: 按上述 batch 执行本地提交。
- `修改计划`: 根据用户要求调整 included/excluded/batches。
- `暂不提交`: closeout 记录 not submitted 和剩余 dirty files。
