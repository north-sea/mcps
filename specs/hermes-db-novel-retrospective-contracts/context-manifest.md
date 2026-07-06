# Context Manifest: Hermes-DB Novel Retrospective Contracts

**Workspace**: `hermes-db-novel-retrospective-contracts`  
**Date**: 2026-07-07

## Implement Context

| Path | Reason |
|---|---|
| `specs/hermes-db-novel-retrospective-contracts/spec.md` | Requirements and non-goals. |
| `specs/hermes-db-novel-retrospective-contracts/plan.md` | Architecture decisions, module boundaries, verification path. |
| `specs/hermes-db-novel-retrospective-contracts/data-model.md` | Table and tool contract details. |
| `specs/hermes-db-novel-retrospective-contracts/tasks.md` | Execution order and verification gates. |
| `specs/novel-runtime-contracts/contract-gap-register.md` | Upstream gap evidence. |
| `agents/packages/adapters/src/mcp/novel-retrospective-client.ts` | Consumer tool names and list unwrapping behavior. |
| `agents/packages/adapters/src/mcp/novel-retrospective-types.ts` | Payload and response shapes. |
| `mcps/packages/hermes-db/migrations/versions/0008_novel_planning_tables.py` | Latest novel migration style and revision chain. |
| `mcps/packages/hermes-db/src/hermes_db_mcp/repositories/novel_planning_repo.py` | Existing asyncpg repository pattern. |
| `mcps/packages/hermes-db/src/hermes_db_mcp/tools/novel_planning.py` | Existing FastMCP tool validation/error pattern. |
| `mcps/packages/hermes-db/src/hermes_db_mcp/services/schema.py` | Health schema inspector pattern. |
| `mcps/packages/hermes-db/src/hermes_db_mcp/tools/health.py` | Global health capability wiring. |

## Check Context

| Path / Command | Reason |
|---|---|
| `rtk uv run pytest tests/test_novel_retrospective_*.py tests/test_health.py` | Focused hermes-db verification target after implementation. |
| `rtk rg "create_novel_retrospective_report|health_novel_retrospective" mcps/packages/hermes-db/src/hermes_db_mcp` | Confirms server-side tool names exist. |
| `rtk rg "prompt|model|draft|polish|write" mcps/packages/hermes-db/src/hermes_db_mcp/tools/novel_retrospective.py` | Boundary check: no writing runtime in MCP. |
| `rtk rg "novel_retrospective_contracts" mcps/packages/hermes-db/src/hermes_db_mcp` | Confirms health/schema wiring. |
| `agents/packages/adapters/src/mcp/novel-retrospective-client.ts` | Cross-repo consumer contract check. |

## Research Context

| Source | Reason |
|---|---|
| Existing hermes-db migration/repository/tool tests | Prefer local patterns over new dependencies. |
| `mcps/specs/novel-runtime-contracts/acceptance.md` | Records why this feature exists and what must remain deferred. |
