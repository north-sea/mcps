# Acceptance Record: Hermes Artifact Versioning And Diff

**Workspace**: `hermes-artifact-versioning-and-diff` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| FR-001 create new workflow artifact version | Added `create_workflow_artifact_version`; derives defaults from parent and writes through immutable `upsert_artifact`. | `workflow_artifacts.py`; `test_create_workflow_artifact_version_derives_parent_fields` | PASS |
| FR-002 preserve immutable rows and set parent | Version tool sets `parent_artifact_id` and does not mutate parent row. | `create_workflow_artifact_version`; tool test asserts parent link | PASS |
| FR-003 idempotent same logical tuple/hash | Version creation reuses existing `upsert_artifact` idempotency behavior. | Existing upsert tests plus version tool implementation | PASS |
| FR-004 list/latest versions | Added `list_workflow_artifact_versions` and `get_latest_workflow_artifact_version`. | Tool tests and repo SQL tests | PASS |
| FR-005 diff two workflow artifacts | Added `diff_workflow_artifacts`. | Inline diff and content_ref fallback tests | PASS |
| FR-006 bounded diff output | `max_preview_lines` capped at 200; preview only, no full content dump. | `diff_workflow_artifacts`; bounded inline diff test | PASS |
| FR-007 backward-compatible upsert | Existing upsert success/idempotency/missing-run tests pass. | `test_workflow_tools.py`; targeted pytest 19/19 | PASS |
| FR-008 remediation envelope | Conflict now points to `create_workflow_artifact_version`; missing parent and selector errors include next action. | Tool tests | PASS |
| FR-009 no raw SQL/secrets/unbounded content | Tool errors use structured envelopes; diff omits full content and does not dereference refs. | `verify-evidence.md` Architecture Drift Check | PASS |

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Repo helpers and MCP tools are implemented with tests. |
| Workflow closure | PASS | Conflict recovery can now proceed through explicit version creation, then list/latest/diff inspection. |
| User-visible outcome | PASS | Agents get version, lineage, latest, and bounded diff outputs without using `force_update`. |

**Overall**: PASS

## Workflow Replay

- **输入摘要**: parent artifact `artifact-parent`, revised inline content with new `content_hash`.
- **最终 payload 摘要**: version tool returns child artifact with `parent_artifact_id`, `version=2`, `created=true`, `lineage_root_artifact_id`; diff tool returns field/content changes and bounded preview.
- **用户可见结果断言**: Agent can recover from `artifact_id_conflict` by calling a named version tool instead of inventing unrelated IDs.
- **Replay 类型**: fixture. Live DB integration skipped by existing test fixture in this environment.

## Bugfix Closure

| Field | Value |
|---|---|
| Root Cause / Hypothesis | Upsert had implicit version fields but no explicit agent-facing lifecycle tools, so conflict recovery pushed ID invention to callers. |
| Fix Mechanism | Added explicit create/list/latest/diff tools while preserving immutable upsert behavior. |
| Prevention Mechanism | Tests pin conflict remediation, version creation, list/latest, diff, and existing upsert compatibility. |
| Failed Attempts Summary | Rejected `force_update`; it would mutate audit history and conflict with existing idempotency semantics. |
| Regression Guard | Targeted pytest 19/19; workflow contract/schema/migration pytest 14 passed, 1 skipped; `git diff --check` PASS. |
| Diffusion Check | No WeChat facade changes, no migration, no in-place overwrite path. |
| Remaining Risk | Recursive parent-chain lineage across logical tuple changes is deferred. |

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | 不适用 | `upsert_workflow_artifact` remains backward-compatible. | 无 |
| 发布、提交、CI 或 follow-through | 延后 | Local tests/checks pass; no commit/deploy requested. | 用户确认后提交/部署 |
| 文档、阶段说明、模板或验收记录更新 | 已完成 | spec/plan/tasks/evidence/acceptance written. | 无 |
| ADR、架构债或演进触发信号 | 已完成 | ADRs record immutable rows, logical tuple family, bounded text diff, no `force_update`. | Recursive lineage if future usage needs it |
| Knowledge Capture | 已完成 | Recorded below. | 无 |

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| decision | Immutable Artifact Versions | Revised artifact content should create explicit child versions, not mutate existing rows. This keeps audit and idempotency semantics coherent. | `plan.md` ADR-001; tests | Hermes workflow artifacts | recorded-only | 无 |
| pattern | Bounded Artifact Diff | Generic MCP diff tools should return field/metadata summaries and bounded previews, not full content dumps. | `diff_workflow_artifacts`; tests | Hermes artifact inspection tools | recorded-only | 无 |
| follow-up | Recursive Lineage | Current version family is `run_id/stage/name`; recursive parent-chain lineage is deferred until a concrete cross-tuple use case appears. | `verify-evidence.md` Remaining Risk | Hermes artifact lifecycle | follow-up | Revisit if parent chains cross logical tuples |

## Commit Result

| Field | Value |
|---|---|
| Status | not_submitted |
| Commit Hashes | 无 |
| Commit Messages | 无 |
| Included Files | 无 |
| Excluded / Remaining Files | Working tree contains this feature plus prior roadmap feature diffs; no commit confirmation. |
| Reason | SDD closeout does not auto-submit commits. |

## Completion Record

- **最终结论**: PASS
- **完成依据**: Evidence Table 全部 PASS；targeted pytest 与 diff check PASS。
- **阻塞项**: 无。
- **延后项**: live DB integration、commit/deploy、recursive parent-chain lineage。
- **退役结论**: 不退役现有 upsert；它仍是基础写入工具。
- **提交结论**: not_submitted。
- **后续动作**: roadmap 可切到 `wechat-draft-ops-crud`，但该 feature 涉及更高风险外部副作用，应先 specify/clarify destructive annotations and operator confirmation。
