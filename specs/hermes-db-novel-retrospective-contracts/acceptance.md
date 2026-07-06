# Acceptance: Hermes-DB Novel Retrospective Contracts

**Workspace**: `hermes-db-novel-retrospective-contracts`  
**Date**: 2026-07-07  
**Overall**: PASS WITH DEPLOYMENT GATE

## Evidence Table

| Requirement | Evidence | Verdict |
|---|---|---|
| FR-001 reports/alerts schema | `0009_novel_retrospective_contracts.py`; schema health tests | PASS |
| FR-002 correction constraints | migration + repo/tools/tests for create/get/list/update | PASS |
| FR-003 handoff packages | migration + repo/tools/tests for create/get/latest | PASS |
| FR-004 character states | migration + repo/tools/tests for upsert/get/list | PASS |
| FR-005 learning candidates | dedicated novel learning candidate table and tools | PASS |
| FR-006 agents adapter contract | 19 tool names match `agents/.../novel-retrospective-client.ts` | PASS |
| FR-007 health and tests | `health_novel_retrospective`, global health key, 27 focused tests pass | PASS |
| FR-008 no runtime generation | grep boundary check has no prompt/model/draft/polish/write matches | PASS |

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Migration, repository, tools, health, registration, tests exist. |
| Workflow closure | PASS WITH DEPLOYMENT GATE | Local contract is implemented; live DB migration and live adapter smoke are deferred. |
| User-visible outcome | PASS | Agents now have matching server-side MCP contract code to target after deployment. |

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| Old logic retirement | 不适用 | This adds missing contracts; no old runtime path removed. | Keep local JSON fallback in agents until live smoke. |
| Publish/live side effects | 已完成 | No live DB migration, no publish, no note deletion. | Apply migration only in deployment window. |
| Roadmap update | 已完成 | Note skill roadmap advances to `hermes-personal-ops-migration`. | Start specify/plan for personal ops migration. |
| Documentation | 已完成 | `plan.md`, `data-model.md`, `tasks.md`, `verify-evidence.md` updated. | Use acceptance as deployment gate record. |
| Architecture debt | 已完成 | Live deployment and agents `--use-hermes-db` smoke are explicit deferred gates. | Track in future deployment/ops work. |
| Knowledge capture | 已完成 | See table below. | Recorded locally only. |
| Commit state | 延后 | User did not request commit; dirty worktree includes broader roadmap changes. | No `git add` or `git commit`. |

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| pattern | Adapter-driven MCP contracts | When agents adapter already names stable tools, hermes-db should implement matching snake_case tools and verify with cross-repo grep/tests. | `verify-evidence.md` tool-name checks | agents/mcps MCP contract work | recorded-only | Reuse for future cross-repo contracts. |
| decision | Dedicated novel retrospective tables | WeChat retrospective tables are not reused because novel reports/constraints/handoff states have different query semantics. | `plan.md` ADR-001; migration `0009` | hermes-db novel contracts | recorded-only | Consider bridge only for self-evolution policies later. |
| follow-up | Deployment gate remains | Code is ready locally, but live migration and agents hermes-db smoke were not run. | `verify-evidence.md` deployment gate | NAS/hermes-db deployment | recorded-only | Schedule migration and smoke separately. |

## Completion Record

- **最终结论**: PASS WITH DEPLOYMENT GATE
- **Tests**:
  - `rtk uv run pytest tests/test_novel_retrospective_tools.py tests/test_novel_retrospective_schema_health.py tests/test_health.py` -> 16 passed
  - `rtk uv run pytest tests/test_novel_retrospective_tools.py tests/test_novel_retrospective_schema_health.py tests/test_novel_planning_tools.py tests/test_novel_schema_health.py tests/test_health.py` -> 27 passed
  - `rtk uv run ruff check ...` -> pass
- **延后**: live DB migration, live agents `--use-hermes-db` smoke, note skill deletion.
- **下一项**: `hermes-personal-ops-migration`，进入 specify/plan。
