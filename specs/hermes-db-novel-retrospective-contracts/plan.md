# Implementation Plan: Hermes-DB Novel Retrospective Contracts

**Workspace**: `hermes-db-novel-retrospective-contracts` | **Date**: 2026-07-07 | **Spec**: [spec.md](spec.md)

## Summary

只有一个合理方向：复用 hermes-db 现有 migration/repository/tool/health/test 结构，新增 novel retrospective durable state。原因是 agents 侧已经存在 `NovelRetrospectiveToolsClient` 和真实 MCP transport，工具名和 payload 已经稳定；当前缺口只在 mcps server-side contracts。

本 feature 不做 prompt、模型、写作、复盘生成逻辑。它只让 agents 已完成的 retrospective/handoff runtime 能把结构化结果持久化到 hermes-db。

## Current Evidence

| Source | Evidence | Interpretation |
|---|---|---|
| `agents/packages/adapters/src/mcp/novel-retrospective-client.ts` | calls `create_novel_retrospective_report`, `list_novel_retrospective_reports`, `create_novel_handoff_package`, etc. | Server must expose matching snake_case MCP tool names. |
| `agents/packages/adapters/src/mcp/novel-retrospective-types.ts` | defines input and response shapes | Use this as contract source unless implementation exposes a deliberate compatibility correction. |
| `mcps/packages/hermes-db/migrations/versions/0008_novel_planning_tables.py` | current latest novel migration after `0007_novel_agent_books` | Add `0009_novel_retrospective_contracts.py` with `down_revision="0008_novel_planning"`. |
| `mcps/packages/hermes-db/src/hermes_db_mcp/tools/novel_planning.py` | tool validation/error style | Follow current tool style: validate required fields, return `error(...)`, delegate to repository. |
| `mcps/packages/hermes-db/src/hermes_db_mcp/tools/health.py` and `services/schema.py` | health capabilities assembled from schema inspectors | Add `novel_retrospective_contracts` capability. |

## Architecture Decisions

### ADR-001: Use Dedicated Novel Retrospective Tables

- **Decision**: create dedicated hermes tables for reports, alerts, correction constraints, handoff packages, character states, and novel learning candidates.
- **Why**: Existing WeChat retrospective tables are account/article oriented; overloading them would blur domain semantics and make agents adapter mapping fragile.
- **Cost**: More tables and tests, but simpler contract ownership.

### ADR-002: Match Agents Adapter Tool Names

- **Decision**: MCP tools use exact names called by `HermesNovelRetrospectiveTools`.
- **Why**: The agents adapter is already implemented and tested locally; changing names would require cross-repo churn.
- **Cost**: Server-side naming is driven by consumer contract.

### ADR-003: Store JSON Payloads As JSONB, Keep Query Keys Relational

- **Decision**: keep query/filter keys relational (`book_slug`, `chapter`, `status`, IDs), while nested diagnosis/progress/character details stay JSONB.
- **Why**: Current use cases need reliable list/get/latest/status filters, not analytics over every nested field.
- **Cost**: Future analytics may add generated columns or indexes if needed.

### ADR-004: MCP Health Proves Schema Availability Only

- **Decision**: `health_novel_retrospective` and global `health` report schema readiness, not runtime generation quality.
- **Why**: Generation quality is agents-owned.
- **Cost**: A green health does not imply retrospective report quality, only contract availability.

## Module Design

| Module | Change | YAGNI Stop | Notes |
|---|---|---|---|
| migration | add `0009_novel_retrospective_contracts.py` | DB native | Use `CREATE TABLE IF NOT EXISTS`, check constraints, indexes, FK to `novel_books`. |
| repository | add `repositories/novel_retrospective_repo.py` | existing pattern | Async functions per tool group; no ORM abstraction. |
| tools | add `tools/novel_retrospective.py` | existing FastMCP pattern | Validate payloads and call repo; return dicts matching agents adapter. |
| health/schema | extend `services/schema.py` and `tools/health.py` | existing pattern | Add one capability key and focused schema inspector. |
| tests | add repository/tool/schema tests | existing pytest style | Mock tool tests plus DB-backed tests where existing fixtures support it. |

## Data Flow

1. agents runtime creates a retrospective report payload.
2. agents MCP transport calls `create_novel_retrospective_report`.
3. hermes-db tool validates scalar fields/enums and delegates to repository.
4. repository inserts rows in `hermes.novel_retrospective_reports`; related alerts/constraints/handoff/state/candidates use FK IDs and `book_slug`.
5. list/get/update tools return snake_case response dicts with ISO-ish timestamp strings, matching agents adapter expectations.
6. health tools expose `novel_retrospective_contracts=true` when tables/constraints/indexes exist.

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| agents retrospective runtime | report + alerts | hermes-db tools | tool tests call create/list/get/update using fixture payloads |
| human review / agents approval | correction constraints | chapter input pack / future agents workflow | list by `book_slug` and `status` returns approved constraints |
| agents handoff builder | handoff package | next writing session | `get_latest_novel_handoff_package(book_slug)` returns newest snapshot |
| agents character tracker | character state | next retrospective/handoff/session | upsert/get/list character state tools preserve latest state |
| agents retrospective learning | learning candidate | future self-evolution bridge | create/list by source report preserves candidate fields |

## Verification Strategy

| Layer | Verification |
|---|---|
| migration/schema | schema inspector returns `novel_retrospective_contracts=true`; downgrade removes tables/indexes. |
| repository | create/get/list/update/upsert/latest functions over fixture data. |
| tools | parameter validation, error handling, and response shape tests. |
| health | global health includes capability key; focused `health_novel_retrospective` returns status. |
| no-runtime-boundary | grep/review verifies no prompt/model/writing-generation code added to MCP. |

## Deferred Work

- Hook agents `--use-hermes-db` CLI to a live hermes-db instance after server contracts are available.
- Promote novel learning candidates into shared self-evolution policy flow if the schema proves compatible.
- Add Library/Wiki routes for novel platform rules and source samples.
