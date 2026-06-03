# Implementation Plan: hermes-db WeChat Publication Ledger

**Workspace**: `hermes-db-wechat-publication-ledger` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/hermes-db-wechat-publication-ledger/spec.md`

---

## Summary

Add a durable WeChat article ledger to `packages/hermes-db` by extending the current Alembic + repository + MCP tools pattern. The recommended design keeps article identity and idempotency in PostgreSQL, stores external publication references in a separate audit-friendly table, and exposes MCP tools for upsert, list, get, and reference repair without copying artifact bodies into article records.

This plan intentionally keeps publishing, URL intelligence, analytics scraping, and downstream workflow orchestration in the `agents` repository. `hermes-db` owns durable article records, referential integrity, bounded query contracts, health capability, and structured diagnostics.

---

## Architecture Overview

The feature fits the existing hermes-db layered architecture:

```text
wechat-agent / analytics ingestion / repair scripts
        |
        v
MCP tools: wechat_articles.py
        |
        v
contracts.py validators and structured errors
        |
        v
repositories/wechat_article_repo.py
        |
        v
PostgreSQL hermes.wechat_articles
PostgreSQL hermes.wechat_article_external_refs

health.py -> services/schema.py -> capability flags
```

Write flow:

1. `upsert_wechat_article` validates the run/artifact references, status-specific required fields, idempotency key, and URL/reference payload.
2. Repository upsert uses `(account, publication_idempotency_key)` as the logical publication identity and returns the existing article on retry.
3. Any supplied publication URL, canonical URL, WeChat platform identifiers, YouMind reference, or repair reference is written to `wechat_article_external_refs` without destroying previous refs.
4. `update_wechat_article_external_refs` appends or supersedes refs and optionally patches selected article summary fields.

Read flow:

1. `list_wechat_articles` returns bounded article summaries and references, never artifact content.
2. `get_wechat_article` returns one article with external refs and artifact ids, still not artifact bodies.
3. Consumers that need draft/final text must call existing `get_workflow_artifact_content` explicitly.

---

## Architecture Reference

| 参考模式 / 模板 | 来源 URL | 适配点 | 不适配点 | 当前阶段 |
|-----------------|----------|--------|----------|----------|
| Layered architecture | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | 当前代码已按 tools / contracts / services / repositories / migrations 分层，新增 ledger 应沿用 | 不引入 queue、event sourcing、CDC 或独立 ledger service | MVP |
| Registry + external reference table | UNVERIFIED | Article 主实体需要稳定 id，外部 URL/平台标识需要历史和 repair 能力 | 不做完整审计系统，不记录每个字段的事件流 | MVP |

跳过候选方案讨论：用户已明确采用本轮 DB/MCP 专家建议继续推进；当前代码现实下主方向只有一个，即沿用 hermes-db 单体分层和 PostgreSQL 强约束。细节权衡在 ADR 中记录。

---

## Producer-Consumer Matrix

| Producer | Artifact / Record | Consumer | Consumption Proof |
|---|---|---|---|
| `wechat-agent` publication stage | `wechat_articles` row | analytics ingestion, retrospective reports, repair scripts | `upsert_wechat_article` returns stable `article_id`; repeated calls with same `(account, publication_idempotency_key)` return same article |
| `workflow_artifacts` feature | `draft_artifact_id`, `published_artifact_id`, `publish_artifact_id` references | article ledger details, retrospective agent | DB FK verifies referenced artifacts exist; `get_wechat_article` returns ids without artifact body |
| `wechat-agent` / publisher output | `published_url`, `canonical_url`, publish target reference | analytics ingestion URL binding | `list_wechat_articles` can filter by account/status/date; external refs include URL/reference values |
| analytics ingestion / repair | WeChat platform identifiers and repaired URL refs | future metric snapshots and reconciliation | `update_wechat_article_external_refs` appends refs and can patch article URL/status |
| `health` schema inspector | `capabilities.wechat_publication_ledger` | downstream agents and release smoke tests | `/mcp` health reports capability true only when tables, constraints, and indexes are present |

**孤儿 artifact 处理**: No new ledger record is orphaned. Article rows are consumed by analytics and retrospective features; external refs are consumed by binding/repair. Artifact bodies remain in `workflow_artifacts` and are intentionally not duplicated here.

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 幂等性 | 同一发布事实重复 upsert 只得到一条 article | Unique `(account, publication_idempotency_key)`; repository returns existing row on retry | repository/tool repeated upsert tests |
| 可追溯性 | article links run, topic, draft/final/publish artifacts | Strong FKs to workflow run/artifacts where present; nullable fields for repair/import cases | FK success/failure tests and get detail tests |
| 兼容性 | Existing topic/workflow artifact tools continue working | Additive migration, additive tool module registration | full `packages/hermes-db` test suite |
| 可诊断性 | FK, conflict, schema drift, validation errors are structured | Tool layer maps PG exceptions to stable MCP error payloads | tool tests for not_found/conflict/schema_drift |
| 可演进性 | Analytics can bind by article id, URL, WeChat ids, and repair refs | External refs table with type/value/history instead of JSON-only storage | query/update refs contract tests |
| 查询性能 | List reads are bounded and index-backed | Index account/status/date, topic/date, run_id, published/canonical URL, ref type/value | SQL/migration tests and list tool tests |

---

## Capacity / Scale Notes

- **规模假设**: MVP supports hundreds to low thousands of articles per account per month.
- **读写特征**: Low write volume during publishing; read volume is mostly filtered analytics, repair, and retrospective lookup.
- **失败代价**: Duplicate articles pollute analytics; missing refs can be repaired; invalid artifact references should fail early.
- **Retention**: No deletion/retention behavior in MVP. Future cleanup must preserve analytics referential integrity.

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001: Article identity | Consumers need stable article id across retry, repair, and analytics | A. client article id; B. server UUID; C. natural URL key only | B: server-generated UUID | Caller must use idempotency key for retry identity | Local DB/MCP design judgment |
| ADR-002: Idempotency | Publishing may retry and URLs may be missing at first | A. unique URL; B. unique `(account, publication_idempotency_key)`; C. always insert | B | Client should pass stable key; server fallback must be documented | Local DB/MCP design judgment |
| ADR-003: Artifact references | Ledger must not point to impossible draft/final rows | A. weak text refs; B. strong FK with nullable fields; C. copy artifact content | B | Historical import without artifacts needs nullable/repair path | Existing workflow schema |
| ADR-004: URL normalization | WeChat URL rules can change and require source context | A. hermes-db full normalization; B. caller canonicalizes, DB lightly validates; C. raw URL only | B | Some duplicates may need later repair if caller is inconsistent | Local DB/MCP design judgment |
| ADR-005: External refs storage | refs need history, uniqueness, and repair | A. JSONB on article; B. separate refs table; C. overwrite columns only | B | More tables and repository code | Local DB/MCP design judgment |
| ADR-006: Status representation | Status set may evolve | A. PostgreSQL enum; B. TEXT + CHECK; C. free text | B | Migration needed to add status values | PostgreSQL migration pragmatism |

---

## Key Design Decisions

### Decision 1: Use server-generated `article_id` and explicit idempotency key

- **背景**: `article_id` is an internal durable identity. Retry and repair identity should be based on publication facts, not caller-generated article ids.
- **选项**:
  - A: Let clients provide `article_id`.
  - B: Generate `article_id` server-side and require or derive `publication_idempotency_key`.
  - C: Use `published_url` as primary key.
- **结论**: Choose B. `article_id UUID PRIMARY KEY` generated by repository/tool code; unique `(account, publication_idempotency_key)`.
- **影响**: Clients should send a stable `publication_idempotency_key`. If missing, tool derives one from the strongest available facts: canonical URL, external reference, publish artifact, then published artifact.
- **来源**: UNVERIFIED, based on local DB/MCP design requirements.

### Decision 2: Enforce strong DB references for known run/artifact ids

- **背景**: Ledger rows are only valuable if their run and artifact links resolve.
- **选项**:
  - A: Store all ids as weak text.
  - B: Use FKs to `wechat_workflow_runs(run_id)` and `workflow_artifacts(artifact_id)`, while allowing nullable optional fields.
  - C: Copy artifact text into `wechat_articles`.
- **结论**: Choose B.
- **影响**: DB prevents impossible references. MCP validation returns structured errors before or after FK violations. Nullable artifact fields keep repair/import paths open.
- **来源**: Existing `workflow_artifacts` acceptance and schema.

### Decision 3: Keep URL canonicalization mostly in callers

- **背景**: WeChat URL forms and platform references are source-specific and can change.
- **选项**:
  - A: hermes-db parses and canonicalizes all WeChat URLs.
  - B: callers pass `canonical_url` and platform ids; hermes-db lightly validates and indexes.
  - C: ignore canonical URL.
- **结论**: Choose B.
- **影响**: hermes-db trims and rejects empty/oversized URL fields, but does not implement deep WeChat URL semantics. Repair tools can add better refs later.
- **来源**: UNVERIFIED, based on separation of concerns.

### Decision 4: Store external references in a separate table

- **背景**: URL, WeChat ids, YouMind refs, and repair refs need history and sometimes uniqueness.
- **选项**:
  - A: Store all refs in article `metadata`.
  - B: Store current summary columns on article and historical refs in `wechat_article_external_refs`.
  - C: Only keep latest URL columns.
- **结论**: Choose B.
- **影响**: Queries can bind by stable refs; repair can supersede refs without destroying history.
- **来源**: UNVERIFIED, based on analytics binding needs.

### Decision 5: Use `TEXT + CHECK` for article status

- **背景**: Postgres enum is inconvenient to evolve during early product discovery.
- **选项**:
  - A: PostgreSQL enum.
  - B: `TEXT NOT NULL` plus CHECK constraint.
  - C: unrestricted text.
- **结论**: Choose B with statuses from the spec.
- **影响**: Adding status values still requires migration, but is simpler than enum alteration and prevents accidental unknown states.
- **来源**: UNVERIFIED, based on migration maintainability.

---

## Module Design

### Module: Alembic Migration

**职责**: Add article ledger tables, constraints, and indexes under `hermes` schema.

**改动概述**:

- Add `migrations/versions/0003_wechat_publication_ledger.py`.
- Set `down_revision = "0002_wechat_workflow_artifacts"`.
- Create `hermes.wechat_articles` and `hermes.wechat_article_external_refs`.
- Add indexes for account/status/date, topic/date, run, URL/ref lookups.

**关键接口 / 行为**:

```text
upgrade:
  create hermes.wechat_articles if not exists
  create hermes.wechat_article_external_refs if not exists
  add FK run_id -> wechat_workflow_runs(run_id)
  add nullable FK artifact ids -> workflow_artifacts(artifact_id)
  add unique account + publication_idempotency_key
  add ref uniqueness for active external refs
```

**注意事项**:

- Migration must not mutate `topics`, `wechat_workflow_runs`, or `workflow_artifacts` behavior.
- FKs should be strong for supplied references, but optional article columns stay nullable where spec allows repair/import.
- Downgrade must drop refs before articles.

### Module: Data Contracts and Validation

**职责**: Define article constants, status/ref allowed values, validation helpers, and structured errors.

**改动概述**:

- Extend `contracts.py` with publication ledger constants and validators.
- Add max limits for list queries and URL/ref text lengths.
- Add status-specific validation for published/missing-url cases.

**关键接口 / 行为**:

```text
validate_wechat_article_payload(...)
validate_wechat_article_query(...)
validate_wechat_article_ref_payload(...)
derive_publication_idempotency_key(...)
error("conflict", field="external_ref", details={...})
error("schema_drift", details={...})
```

**注意事项**:

- Tool layer should not leak raw asyncpg exception strings for FK or unique conflicts.
- Empty strings should be normalized to missing values before validation.

### Module: Article Repository

**职责**: Encapsulate all SQL for article upsert, list, detail, and refs update.

**改动概述**:

- Add `repositories/wechat_article_repo.py`.
- Provide methods for article upsert, article list, detail lookup, refs append/supersede, and optional article patch.

**关键接口 / 行为**:

```text
upsert_article(pool, payload) -> (row, created)
list_articles(pool, filters, limit, offset) -> list[row]
get_article(pool, article_id) -> row | None
list_article_refs(pool, article_id) -> list[row]
upsert_external_refs(pool, article_id, refs, patch) -> row
```

**注意事项**:

- `upsert_article` should use a transaction so article row and initial refs stay consistent.
- Same `(account, publication_idempotency_key)` is idempotent. Different article trying to claim an active unique ref should return `conflict`.
- For FK violations, map constraint names to `not_found` / `validation_error` fields.

### Module: MCP Article Tools

**职责**: Expose stable MCP tool contracts to downstream agents and analytics.

**改动概述**:

- Add `tools/wechat_articles.py`.
- Register it in `server.register_tools()`.
- Provide four tools:
  - `upsert_wechat_article`
  - `list_wechat_articles`
  - `get_wechat_article`
  - `update_wechat_article_external_refs`

**关键接口 / 行为**:

```text
upsert_wechat_article(
  account,
  run_id,
  publication_idempotency_key?,
  task_id?,
  topic_id?,
  draft_artifact_id?,
  published_artifact_id?,
  publish_artifact_id?,
  status,
  dry_run,
  title?,
  published_url?,
  canonical_url?,
  publish_target?,
  external_references?,
  metadata?
)

list_wechat_articles(
  account?,
  topic_id?,
  run_id?,
  status?,
  publish_target?,
  date_from?,
  date_to?,
  limit,
  offset
)

get_wechat_article(article_id)

update_wechat_article_external_refs(
  article_id,
  refs,
  patch?
)
```

**注意事项**:

- List/detail must not return artifact `content_text`.
- `get_wechat_article` returns refs and artifact ids only.
- Write tools should use idempotent/non-destructive annotations where accurate.

### Module: Health and Schema Inspection

**职责**: Report publication ledger availability without breaking existing health output.

**改动概述**:

- Extend `services/schema.py` with `inspect_wechat_publication_ledger_schema`.
- Extend `tools/health.py` capabilities with `wechat_publication_ledger`.
- Tests should cover both migrated and missing schema cases.

**关键接口 / 行为**:

```text
health().capabilities.wechat_publication_ledger == true
```

**注意事项**:

- Missing ledger schema should not crash health.
- Existing `workflow_artifacts` capability remains independently reported.

---

## Data Model

Detailed schema is in [data-model.md](data-model.md).

Core entities:

- `hermes.wechat_articles`: article ledger main table with stable `article_id`, idempotency key, account/run/topic/artifact references, status, URLs, publish target, and metadata.
- `hermes.wechat_article_external_refs`: append-oriented external reference table for URLs, WeChat platform ids, YouMind refs, and manual repair refs.

---

## Project Structure

```text
packages/hermes-db/
  migrations/versions/
    0003_wechat_publication_ledger.py
  src/hermes_db_mcp/
    contracts.py
    repositories/
      wechat_article_repo.py
    services/
      schema.py
    tools/
      health.py
      wechat_articles.py
    server.py
  tests/
    test_wechat_article_repo_sql.py
    test_wechat_article_tools.py
    test_wechat_article_integration.py
    test_wechat_article_schema_health.py
    test_migration_sql.py
    test_health.py
```

---

## Risks and Tradeoffs

- Strong FKs catch bad references early but make historical import impossible unless nullable fields and repair paths are preserved.
- Caller-side canonical URL keeps hermes-db simple but can create temporary duplicate refs if callers are inconsistent.
- `TEXT + CHECK` status is easier than enum but still needs migration when status vocabulary grows.
- Separate refs table adds repository complexity, but avoids lossy overwrites and gives analytics a reliable binding surface.
- Derived idempotency keys are fallback only. Downstream agents should pass explicit keys to avoid semantic drift.

---

## Evolution Path

- **MVP**: Two tables, four MCP tools, strong FKs for supplied run/artifact refs, explicit or derived idempotency key, caller-provided canonical refs.
- **成长期**: Add richer URL/ref normalization helpers once real analytics inputs reveal stable rules.
- **成熟期**: Consider event/audit table or retention policy only after publication/analytics volume justifies it.

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。未引入 queue、event sourcing、CDC、object store 或独立 ledger service。
- 是否引用了外部模式但没有适配检查：否。只沿用当前仓库分层和轻量 registry/ref-table 模式。
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。新增状态、FK、唯一约束、schema drift、conflict 都已记录。

---

## Verification Strategy

1. **Static checks**: `uv run ruff check .` under `packages/hermes-db`.
2. **Migration SQL tests**:
   - `0003_wechat_publication_ledger.py` has correct down revision.
   - Tables, FKs, CHECK constraints, unique constraints, and indexes are present.
3. **Repository tests**:
   - Repeated upsert with same `(account, publication_idempotency_key)` returns same article.
   - FK violations map to expected diagnostics.
   - External refs append/supersede without losing history.
4. **Tool contract tests**:
   - `upsert_wechat_article`, `list_wechat_articles`, `get_wechat_article`, `update_wechat_article_external_refs`.
   - List/detail omit artifact content.
   - Missing schema returns structured `schema_drift` or diagnostic error.
5. **Integration tests**:
   - Create workflow run/artifacts, upsert article with refs, list/get/update refs.
6. **Regression tests**:
   - Existing topic, inspiration, workflow run, workflow artifact, health, and transport tests pass.
7. **Release smoke**:
   - NAS `alembic upgrade head`.
   - `/mcp` health reports `wechat_publication_ledger=true`.
   - `tools/list` includes all four new article tools.

---

## Stage Readiness

- 是否需要 `data-model.md`: 需要。This feature adds two tables, status constraints, FKs, uniqueness rules, and query/index contracts.
- 下一步建议：`tasks`
- 阻塞项：无。Plan decisions are sufficient for task breakdown.

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | 必须 | 主实现计划 |
| data-model.md | 必须 | 新增 article/ref 实体、约束和 DDL |
| tasks.md | 后续阶段生成 | 由 `tasks` 阶段产出 |
| acceptance.md | 后续阶段生成 | 用于最终验收结论 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| Layered architecture | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | 仅作为分层参考 |
| Existing workflow schema | [../hermes-db-wechat-artifact-persistence/data-model.md](../hermes-db-wechat-artifact-persistence/data-model.md) | 本 feature 的上游依赖 |
| Existing workflow acceptance | [../hermes-db-wechat-artifact-persistence/acceptance.md](../hermes-db-wechat-artifact-persistence/acceptance.md) | 证明依赖已发布 |
| Article identity/idempotency/ref design | UNVERIFIED | 基于本地 DB/MCP 专家判断 |
