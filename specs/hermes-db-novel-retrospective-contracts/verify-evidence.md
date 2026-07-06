# Verify Evidence: Hermes-DB Novel Retrospective Contracts

**Workspace**: `hermes-db-novel-retrospective-contracts`  
**Date**: 2026-07-07  
**Verdict**: PASS WITH DEPLOYMENT GATE

## Evidence Commands

| Check | Command / Evidence | Result |
|---|---|---|
| Focused retrospective + health tests | `rtk uv run pytest tests/test_novel_retrospective_tools.py tests/test_novel_retrospective_schema_health.py tests/test_health.py` | 16 passed |
| Focused novel regression set | `rtk uv run pytest tests/test_novel_retrospective_tools.py tests/test_novel_retrospective_schema_health.py tests/test_novel_planning_tools.py tests/test_novel_schema_health.py tests/test_health.py` | 27 passed |
| Lint | `rtk uv run ruff check src/hermes_db_mcp/repositories/novel_retrospective_repo.py src/hermes_db_mcp/tools/novel_retrospective.py src/hermes_db_mcp/services/schema.py tests/test_novel_retrospective_tools.py tests/test_novel_retrospective_schema_health.py tests/test_health.py` | pass |
| Server tool names | `rg "def (create_novel_retrospective_report|...|health_novel_retrospective)" tools/novel_retrospective.py` | 19 expected tool functions present |
| Agents adapter tool names | `rg "'create_novel_retrospective_report'|...|'health_novel_retrospective'" agents/.../novel-retrospective-client.ts` | 19 matching calls present |
| No writing runtime in MCP | `rg "prompt|model|draft|polish|write" tools/novel_retrospective.py repositories/novel_retrospective_repo.py` | no matches |

## Implementation Scope

| Area | Files | Verdict |
|---|---|---|
| Migration | `migrations/versions/0009_novel_retrospective_contracts.py` | PASS |
| Repository | `src/hermes_db_mcp/repositories/novel_retrospective_repo.py` | PASS |
| MCP tools | `src/hermes_db_mcp/tools/novel_retrospective.py`; `server.py` import | PASS |
| Schema health | `src/hermes_db_mcp/services/schema.py`; `tools/health.py` | PASS |
| Tests | `tests/test_novel_retrospective_tools.py`; `tests/test_novel_retrospective_schema_health.py`; `tests/test_health.py` | PASS |

## Requirement Evidence

| Requirement | Evidence | Verdict |
|---|---|---|
| FR-001 Reports and alerts schema | migration adds `novel_retrospective_reports` and `novel_retrospective_alerts`; schema inspector covers columns/checks/indexes | PASS |
| FR-002 Correction constraints | migration, repo, and tools cover create/get/list/update status | PASS |
| FR-003 Handoff packages | migration, repo, and tools cover create/get/latest | PASS |
| FR-004 Character states | migration, repo, and tools cover upsert/get/list with unique key | PASS |
| FR-005 Novel learning candidates | dedicated `novel_learning_candidates` table and create/list tools | PASS |
| FR-006 MCP tools match agents adapter | 19 server functions match 19 adapter `callTool` names | PASS |
| FR-007 Health/schema/tests | `novel_retrospective_contracts` capability and `health_novel_retrospective`; 27 focused tests pass | PASS |
| FR-008 Preserve runtime boundary | no prompt/model/draft/polish/write matches in new MCP tool/repo files | PASS |

## Deployment Gate

| Gate | Status | Notes |
|---|---|---|
| Local code/test readiness | PASS | Focused tests and lint pass. |
| Live DB migration applied | DEFERRED | No live NAS/production DB migration was run in this session. |
| Live agents `--use-hermes-db` smoke | DEFERRED | Requires migrated DB and selected environment. |
| Note skill deletion | NOT ALLOWED | Still deferred to `note-thin-shell-and-archive`. |

## Architecture Drift

- No generation runtime moved into MCP.
- No Library/Wiki or Memory route changed.
- New MCP scope is durable CRUD/query/health only.
