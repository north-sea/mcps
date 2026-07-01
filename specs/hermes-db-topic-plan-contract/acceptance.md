# Acceptance Record: Hermes DB Topic Plan Contract

**Workspace**: `hermes-db-topic-plan-contract` | **Date**: 2026-07-01 | **Spec**: [spec.md](spec.md)

---

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| FR-001..FR-005: first-class `topic_plans` schema and plan payload shape | Added `hermes.topic_plans` migration with candidate/topic FKs, unique candidate plan, lifecycle status check, planned/rejected shape checks, and indexes. | `packages/hermes-db/migrations/versions/0010_topic_plan_contracts.py`; `tests/test_migration_sql.py` | PASS |
| FR-006..FR-008: idempotent plan upsert and candidate shortlist semantics | `topic_plan_repo.upsert_topic_plan` uses `ON CONFLICT(candidate_id)` and updates candidate `shortlisted` only for `status=planned` in the same transaction. | `tests/test_topic_plan_repo_sql.py` | PASS |
| FR-009..FR-011: list/get/update TopicPlan MCP contract | Added repository and MCP tool support for `list_topic_plans`, `get_topic_plan`, and `update_topic_plan_status`. | `packages/hermes-db/src/hermes_db_mcp/tools/topic_plans.py`; `tests/test_topic_plan_tools.py` | PASS |
| FR-012: candidate raw context for planning | Extended candidate read path with `include_raw`, defaulting to hidden raw payload. | `topic_candidate_repo.py`; `tools/topic_candidates.py`; candidate tests | PASS |
| FR-013: health capability | Added `inspect_topic_plan_schema` and `health.capabilities.topic_plans`. | `services/schema.py`; `tools/health.py`; schema/health tests | PASS |
| FR-014: structured MCP validation/error behavior | Tool tests cover invalid status, invalid planned payload, not found, and invalid shortlist guard. | `tests/test_topic_plan_tools.py` | PASS |
| FR-015: migration test coverage | Migration text assertions cover revision, down revision, schema objects, and downgrade drop. | `tests/test_migration_sql.py` | PASS |
| Regression compatibility | Full hermes-db test suite passed. | `rtk uv run pytest` -> 383 passed, 23 skipped | PASS |

---

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | New schema, repo, MCP tools, health capability, and candidate raw read are implemented and locally tested. |
| Workflow closure | PASS | Producer-consumer chain is closed inside hermes-db: migration -> health -> repo -> tools -> tests. |
| User-visible outcome | PASS | Agents can use `upsert_topic_plan`, `list_topic_plans`, `get_topic_plan`, `update_topic_plan_status`, and `get_topic_candidate(include_raw)`. |

**Overall**: PASS

---

## Workflow Replay

- **输入摘要**: `spec.md` requested a durable TopicPlan contract for WeChat topic planning.
- **实现摘要**: Added migration `0010_topic_plan_contracts`, `topic_plan_repo.py`, `tools/topic_plans.py`, schema health support, candidate `include_raw` read, server registration, and focused tests.
- **验证摘要**: Focused suite passed 47/47; full hermes-db suite passed 383/383 with 23 skipped integration tests.
- **用户可见结果断言**: hermes-db now has an MCP-facing topic plan lifecycle contract ready for downstream agents smoke after deployment.

---

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | 已完成 | No old topic candidate behavior removed; raw payload remains hidden by default. | 无 |
| 发布、提交、CI 或 follow-through | 未提交 | Local tests passed; git commit not requested yet. | User can choose commit/release after review. |
| 文档、阶段说明、模板或验收记录更新 | 已完成 | `plan.md`, `data-model.md`, `tasks.md`, `context-manifest.md`, `verify-evidence.md`, and this `acceptance.md` were created/updated. | 无 |
| ADR、架构债或演进触发信号 | 已完成 | Plan records one-plan-per-candidate MVP and future versioning as evolution path. | Add plan versioning only after downstream need appears. |
| Knowledge Capture | 已完成 | This acceptance records decision, evidence, and follow-up boundaries. | Optional external memory sync if desired later. |

---

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| decision | TopicPlan is first-class hermes-db storage | `topic_plans` is a durable MCP contract table, not embedded in `topic_candidates.raw_payload` or workflow artifacts. | `plan.md`, migration, repo/tool tests | hermes-db topic planning | recorded-only | Downstream agents smoke after deployment |
| learning | Candidate raw payload remains opt-in | `get_topic_candidate(include_raw=true)` exposes planning context while default reads continue hiding raw payload. | candidate repo/tool tests | topic candidate compatibility | recorded-only | Keep default hidden behavior in downstream callers |

---

## Commit Result

| Field | Value |
|---|---|
| Status | not_submitted |
| Commit Hashes | 无 |
| Commit Messages | 无 |
| Included Files | 无 |
| Excluded / Remaining Files | `.pnpm-store/` remains unrelated local noise; paused roadmap work is in `stash@{0}`. |
| Reason | 本次未请求提交；已完成本地实现与验证。 |

---

## Completion Record

- **最终结论**: PASS
- **完成依据**: `verify-evidence.md`; focused suite 47 passed; full hermes-db suite 383 passed, 23 skipped.
- **阻塞项**: 无。
- **延后项**: live Postgres migration/preflight and agents-side smoke after deployment.
- **退役结论**: 不退役旧 candidate flows；仅新增 opt-in raw read 和 TopicPlan contract。
- **提交结论**: not_submitted。
- **后续动作**: Review diff, decide whether to commit/release; later restore paused roadmap stash when returning to note skill roadmap.
