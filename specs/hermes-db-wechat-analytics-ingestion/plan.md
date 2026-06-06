# Implementation Plan: Hermes DB WeChat Analytics Ingestion

**Workspace**: `hermes-db-wechat-analytics-ingestion` | **Date**: 2026-06-06 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/hermes-db-wechat-analytics-ingestion/spec.md`

---

## Summary

Add durable WeChat analytics ingestion to `packages/hermes-db` by extending the existing Alembic + contracts + repository + MCP tools + health capability pattern. The recommended design stores article metric snapshots, channel daily rows, and import run summaries in PostgreSQL, resolves every metric row to an existing `wechat_articles.article_id`, and exposes bounded MCP contracts for bulk upsert and snapshot query.

This plan keeps file parsing, Excel/CSV/JSON normalization, browser automation, dashboarding, and trend interpretation in the `agents` repository. `hermes-db` owns persistence, idempotency, validation, article binding semantics, structured diagnostics, and schema readiness signals.

---

## Architecture Overview

The feature fits the current hermes-db layered architecture:

```text
agents wechat analytics CLI / adapter
        |
        v
MCP tools: wechat_analytics.py
        |
        v
contracts.py validators and structured errors
        |
        v
repositories/wechat_analytics_repo.py
repositories/wechat_article_repo.py for article resolution
        |
        v
PostgreSQL hermes.analytics_import_runs
PostgreSQL hermes.wechat_article_metric_snapshots
PostgreSQL hermes.wechat_article_channel_daily_metrics

health.py -> services/schema.py -> capabilities.wechat_analytics_ingestion
```

Write flow:

1. `bulk_upsert_wechat_article_metric_snapshots` validates top-level `account`, `source`, `dry_run`, `records`, optional `channel_daily_metrics`, optional `audience_profiles`, and `import_metadata`.
2. Each input row must provide `article_id` or stable article reference fields. Tool logic resolves references to exactly one existing article; zero matches become `unmatched`, multiple matches become row-level `ambiguous_article` errors.
3. The repository writes one `analytics_import_runs` row for non-dry-run imports, then upserts metric snapshots by `(article_id, stat_date, window_label, source)` and channel rows by `(article_id, metric_date, channel, source)`.
4. The response returns `import_run_id`, counts, unmatched rows, row-level errors, and a final status: `completed`, `completed_with_errors`, `failed`, or `dry_run`.

Read flow:

1. `list_wechat_article_metric_snapshots` validates bounded filters.
2. Repository joins `wechat_article_metric_snapshots` to `wechat_articles` for account filtering and article metadata.
3. Results omit `raw_json` by default; callers opt in with `include_raw=true`.

---

## Architecture Reference

| 参考模式 / 模板 | 来源 URL | 适配点 | 不适配点 | 当前阶段 |
|-----------------|----------|--------|----------|----------|
| Layered architecture | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | 当前 hermes-db 已按 tools / contracts / repositories / services / migrations 分层，analytics ingestion 应沿用 | 不引入独立 analytics service、queue、CDC、event sourcing 或 OLAP store | MVP |
| Registry + metric snapshot tables | UNVERIFIED | 已有 `wechat_articles` 作为 article registry，metric snapshots 需要稳定绑定和幂等覆盖 | 不做完整指标仓库、宽表建模平台或实时聚合层 | MVP |

跳过候选方案讨论：当前代码现实下只有一个合理方向，即沿用 hermes-db 单体分层和 PostgreSQL 强约束做增量能力。主要权衡不在架构方向，而在 import transaction 语义、article resolution 入口、MVP 表范围和 health gate；这些在 ADR 中记录。

---

## Producer-Consumer Matrix

| Producer | Artifact / Record | Consumer | Consumption Proof |
|---|---|---|---|
| agents `wechat-analytics-ingestion` normalizer | `NormalizedArticleMetricRecord` payload | `bulk_upsert_wechat_article_metric_snapshots` | MCP response returns created/updated counts and row-level errors using the agents adapter shape |
| hermes-db publication ledger | `wechat_articles.article_id` and external refs | analytics row resolver | Direct `article_id` import succeeds; stable URL/ref resolution returns 0/1/>1 semantics without title matching |
| hermes-db analytics ingestion | `wechat_article_metric_snapshots` rows | agents CLI and future retrospective analysis | `list_wechat_article_metric_snapshots` returns bounded rows for account/article/date/window filters |
| hermes-db analytics ingestion | `wechat_article_channel_daily_metrics` rows | future channel analysis and audit | Repository/tool tests prove channel rows are idempotently upserted with same `(article_id, metric_date, channel, source)` |
| hermes-db analytics ingestion | `analytics_import_runs` summary | agents CLI, release smoke, operations diagnostics | Import response includes persisted `import_run_id`; DB row records counts, unmatched rows, errors, and metadata |
| hermes-db health inspector | `capabilities.wechat_analytics_ingestion` | downstream agents startup/live smoke gate | `/mcp` health reports true only when required analytics tables, constraints, and indexes are present |

**孤儿 artifact 处理**: No orphan artifact is introduced. `audience_profiles` is a P2 payload area and should not produce a persisted artifact in MVP unless the table is implemented; skipped P2 rows must be reported in the import summary rather than silently accepted.

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 幂等性 | Re-importing the same article/date/window/source updates exactly one snapshot | Unique snapshot and channel keys; repository returns created/updated counts | repo tests repeat identical import and assert updated count / no duplicate |
| 一致性 | Metrics only bind to existing articles | FK to `wechat_articles`; resolver rejects not found and ambiguous refs | tool tests for unknown article and ambiguous reference |
| 可诊断性 | CLI can show import summary without parsing logs | Persist `analytics_import_runs`; response carries unmatched/errors/status | tool tests assert response shape and persisted summary |
| 兼容性 | Existing topic/workflow/article tools keep working | Additive migration and separate tool module registration | targeted analytics tests plus existing wechat article tests |
| 可演进性 | P1 supports snapshots/channel rows; P2 audience can be added later | Keep raw_json/import_metadata and optional audience handling separated | data-model review and future migration path |
| 查询性能 | Common account/article/date/window queries are index-backed and bounded | indexes on article/date/window/source and channel date/source; limit/offset validation | migration SQL tests and query SQL inspection |

---

## Capacity / Scale Notes

- **规模假设**: MVP supports manual or semi-manual imports for hundreds to low thousands of articles per account per month.
- **读写特征**: Batch writes from CLI; reads are filtered by account/article/date/window. This is not a real-time analytics pipeline.
- **失败代价**: Duplicate snapshots distort retrospective analysis; wrong article binding is worse than row-level rejection; missing channel rows are diagnosable and repairable.
- **Retention**: No cleanup policy in MVP. Future retention must preserve import run audit and article FK integrity.

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001: Snapshot identity | Re-import must be idempotent | A. always insert; B. unique article/date/window/source; C. unique title/date | B | Caller must supply consistent `source` and `window_label` | Local DB/MCP design judgment |
| ADR-002: Import transaction semantics | Spec leaves partial vs all-or-nothing open | A. all-or-nothing; B. per-row partial success with persisted summary; C. dry-run only | B | More bookkeeping; mixed success requires clear CLI display | Local DB/MCP design judgment |
| ADR-003: Import run persistence | CLI/live smoke need durable evidence | A. optional table; B. mandatory MVP table; C. response only | B | Extra migration/repo work | Spec observability requirement |
| ADR-004: Audience profiles | P2 should not block P1 live smoke | A. fully persist MVP; B. reject payload; C. accept and skip with summary | C for MVP | Consumers cannot query P2 yet | Spec P1/P2 split |
| ADR-005: Article resolution entry | Agents need stable refs, not title matching | A. new `resolve_wechat_article`; B. extend `list_wechat_articles`; C. resolve inside bulk only | C for MVP, A as follow-up if reused | Resolution behavior initially scoped to ingestion | Existing article tools and MVP scope |
| ADR-006: Raw source payloads | Debugging imports needs source row context | A. no raw JSON; B. snapshot/channel raw_json opt-in read; C. store files | B | More storage, must avoid returning raw by default | Spec query requirement |

---

## Key Design Decisions

### Decision 1: Use partial success with persisted import summary

- **背景**: Manual analytics files may contain a mix of valid rows, unknown article refs, and malformed optional channel rows. A single bad row should not force operators to throw away all good rows.
- **选项**:
  - A: One transaction for the entire import and fail everything on first error.
  - B: Validate rows, upsert valid records in a transaction, record invalid/unmatched rows in `analytics_import_runs`, and return `completed_with_errors`.
  - C: Only support `dry_run` until all rows are clean.
- **结论**: Choose B. Snapshot and channel writes for accepted rows should be atomic inside one import transaction; rejected rows are excluded before writes and captured in summary.
- **影响**: Implementation must clearly separate rejected rows from write failures. If DB write fails after validation, status is `failed` and no partial DB writes should remain.
- **来源**: UNVERIFIED, based on local DB/MCP design requirements.

### Decision 2: Make `analytics_import_runs` mandatory in MVP

- **背景**: The feature exists to unblock live smoke and operator-visible CLI feedback. A response-only summary disappears after the command exits.
- **选项**:
  - A: Implement summary only in MCP response.
  - B: Persist import run summary in `hermes.analytics_import_runs`.
  - C: Defer observability to agents logs.
- **结论**: Choose B.
- **影响**: Every non-dry-run call gets a stable `import_run_id`. `dry_run` may return a generated non-persisted id or `null`; plan prefers generated id plus `status="dry_run"` in response, with no DB write.
- **来源**: Spec observability and live smoke requirements.

### Decision 3: Resolve articles inside the bulk tool for MVP

- **背景**: The immediate consumer is the agents analytics adapter. A general resolver tool is useful, but not required to unblock P1 ingestion.
- **选项**:
  - A: Add dedicated `resolve_wechat_article`.
  - B: Extend `list_wechat_articles` filters for URL/ref lookup.
  - C: Implement shared repository resolver and call it from bulk import only.
- **结论**: Choose C for MVP. Keep resolver repository/helper reusable so a dedicated tool can be added later without changing semantics.
- **影响**: Bulk import must accept direct `article_id` and stable reference fields. Title remains diagnostic only.
- **来源**: Existing `wechat_article_repo.py` and spec FR-005.

### Decision 4: Persist P1 snapshots and channel rows; skip P2 audience payloads with summary

- **背景**: Spec says P2 audience profile storage must not block P1 live smoke.
- **选项**:
  - A: Implement audience profile table and tool behavior now.
  - B: Reject any request containing audience profiles.
  - C: Accept payload shape, validate minimally, skip persistence, and report skipped P2 count/reason.
- **结论**: Choose C for MVP. Do not create `wechat_article_audience_profiles` until there is a consumer and query contract.
- **影响**: `data-model.md` marks audience profiles as future table, not MVP migration. Tool response must not silently claim P2 rows were imported.
- **来源**: Spec Non-Goals and FR-001 P2 note.

### Decision 5: Add health capability only when all required MVP structures exist

- **背景**: Downstream agents fail closed based on health capability.
- **选项**:
  - A: Set capability true after migration revision only.
  - B: Inspect required columns, constraints, and indexes.
  - C: Always register tools and rely on runtime errors.
- **结论**: Choose B, matching existing `inspect_wechat_publication_ledger_schema`.
- **影响**: `health.capabilities.wechat_analytics_ingestion` stays false if migration is missing or partial.
- **来源**: Existing `services/schema.py` health inspection pattern.

---

## Module Design

### Module: Alembic Migration

**职责**: Add analytics ingestion tables, constraints, and indexes under `hermes` schema.

**改动概述**:

- Add `migrations/versions/0004_wechat_analytics_ingestion.py`.
- Set `down_revision = "0003_wechat_publication_ledger"`.
- Create `hermes.analytics_import_runs`.
- Create `hermes.wechat_article_metric_snapshots`.
- Create `hermes.wechat_article_channel_daily_metrics`.
- Do not create `wechat_article_audience_profiles` in MVP.

**关键接口 / 行为**:

```text
upgrade:
  create analytics_import_runs
  create wechat_article_metric_snapshots with FK article_id -> wechat_articles(article_id)
  create unique snapshot key article_id + stat_date + window_label + source
  create wechat_article_channel_daily_metrics with FK article_id -> wechat_articles(article_id)
  create unique channel key article_id + metric_date + channel + source
  add account/date/source indexes for bounded reads and smoke checks

downgrade:
  drop channel metrics
  drop snapshots
  drop import runs
```

**注意事项**:

- Migration must be additive and must not alter `wechat_articles` semantics.
- Numeric fields should use `INTEGER` for counts/cents, `DOUBLE PRECISION` for rates/seconds unless implementation chooses `NUMERIC` for precision and records why.
- Check constraints should reject negative counts and out-of-range `completion_rate`.

### Module: Data Contracts and Validation

**职责**: Define analytics constants, payload validation, row normalization boundaries, and structured errors.

**改动概述**:

- Extend `contracts.py` with analytics source values, status values, query limits, count/rate/date validators, and bulk payload validation.
- Keep file parsing out of hermes-db; tool accepts already-normalized dicts.

**关键接口 / 行为**:

```text
validate_wechat_analytics_bulk_payload(...)
validate_wechat_metric_record(...)
validate_wechat_channel_metric(...)
validate_wechat_metric_query(...)
error("ambiguous_article", details={...})
error("schema_drift", details={...})
```

**注意事项**:

- Empty strings normalize to missing values before validation.
- `completion_rate` must be `0..1`.
- Count fields must be non-negative integers where present.
- Unknown `source` returns a structured validation error unless implementation deliberately keeps source open-ended and documents it in tests.

### Module: Analytics Repository

**职责**: Encapsulate SQL for import runs, article resolution, metric upsert, channel upsert, and snapshot list queries.

**改动概述**:

- Add `repositories/wechat_analytics_repo.py`.
- Reuse or extend `wechat_article_repo.py` only for article lookup semantics; do not duplicate article table SQL in tools.

**关键接口 / 行为**:

```text
resolve_article(pool, account, article_id?, published_url?, canonical_url?, external_reference?, ref_type?, ref_value?)
create_import_run(conn, summary)
update_import_run(conn, import_run_id, summary)
upsert_metric_snapshots(conn, rows) -> {created, updated}
upsert_channel_daily_metrics(conn, rows) -> {created, updated}
list_metric_snapshots(pool, filters, include_raw, limit, offset)
```

**注意事项**:

- `resolve_article` returns `not_found`, one row, or `ambiguous`; it never picks a title match.
- Upsert SQL should use `RETURNING (xmax = 0) AS created` only if tests confirm asyncpg/Postgres behavior remains reliable for this use case; otherwise count created/updated through a CTE.
- Repository methods should accept typed Python values after validation; parsing belongs in tool/contracts.

### Module: MCP Analytics Tools

**职责**: Expose the agents-facing analytics ingestion and query contract.

**改动概述**:

- Add `tools/wechat_analytics.py`.
- Register it in `server.register_tools()`.
- Implement:
  - `bulk_upsert_wechat_article_metric_snapshots`
  - `list_wechat_article_metric_snapshots`

**关键接口 / 行为**:

```text
bulk_upsert:
  validate payload
  if dry_run: resolve/validate only, return status dry_run, no writes
  collect unmatched and row errors
  write valid rows + import run in one transaction
  return summary with import_run_id and counts

list_snapshots:
  validate filters
  query bounded rows
  omit raw_json unless include_raw
```

**注意事项**:

- Tool annotations should mark bulk upsert as non-destructive, idempotent, open-world.
- `schema_drift` should map UndefinedTable/UndefinedColumn failures consistently with existing tool modules.
- Raw source payloads can be large; default list response must exclude `raw_json`.

### Module: Schema Health

**职责**: Report analytics capability only when database structures satisfy the MVP contract.

**改动概述**:

- Add `inspect_wechat_analytics_ingestion_schema(pool)` in `services/schema.py`.
- Add default `wechat_analytics_ingestion: False` in `tools/health.py`.
- Merge inspector output with existing capability dict.

**关键接口 / 行为**:

```text
required tables:
  analytics_import_runs
  wechat_article_metric_snapshots
  wechat_article_channel_daily_metrics

required constraints/indexes:
  snapshot unique key
  channel unique key
  article FKs
  key date/source/account indexes
```

**注意事项**:

- Capability must stay false for partial migrations.
- Existing health behavior for topic/workflow/publication ledger must remain unchanged.

### Module: Tests and Documentation

**职责**: Prove migration, contracts, repository behavior, MCP response shape, and live-smoke readiness.

**改动概述**:

- Add analytics-focused tests alongside existing wechat article tests.
- Update README/deployment docs if the project documents schema revision and capabilities by version.

**关键接口 / 行为**:

```text
test_wechat_analytics_contracts.py
test_wechat_analytics_repo_sql.py
test_wechat_analytics_tools.py
test_wechat_analytics_schema_health.py
test_wechat_analytics_integration.py
```

**注意事项**:

- Real DB integration should skip cleanly when `DATABASE_URL` is absent, matching existing pattern.
- Live smoke evidence belongs in `acceptance.md` after implementation/deploy, not in plan.

---

## Data Model

Detailed table design is in [data-model.md](data-model.md).

MVP tables:

- `hermes.analytics_import_runs`
- `hermes.wechat_article_metric_snapshots`
- `hermes.wechat_article_channel_daily_metrics`

Future/P2 table:

- `hermes.wechat_article_audience_profiles`

---

## Project Structure

```text
packages/hermes-db/
  migrations/versions/
    0004_wechat_analytics_ingestion.py
  src/hermes_db_mcp/
    contracts.py
    server.py
    repositories/
      wechat_analytics_repo.py
      wechat_article_repo.py
    services/
      schema.py
    tools/
      health.py
      wechat_analytics.py
  tests/
    test_migration_sql.py
    test_wechat_analytics_contracts.py
    test_wechat_analytics_repo_sql.py
    test_wechat_analytics_tools.py
    test_wechat_analytics_schema_health.py
    test_wechat_analytics_integration.py
docs/
  hermes-db-deployment.md
specs/hermes-db-wechat-analytics-ingestion/
  spec.md
  plan.md
  data-model.md
  tasks.md
  acceptance.md
```

---

## Risks and Tradeoffs

- Partial success is operationally useful but requires precise summary semantics; tests must pin created/updated/skipped/unmatched/errors.
- Article resolution inside bulk import keeps MVP small but may duplicate future consumer needs; keep resolver reusable for a later dedicated tool.
- Storing `raw_json` helps debug imports but can bloat rows; list APIs must omit raw payloads by default.
- `source` values may evolve as ingestion moves from manual files to API/browser collection; validation should be strict enough for diagnostics without forcing frequent migrations.
- Health capability that checks indexes is more robust but can be brittle if index names drift; tests should lock names intentionally.

---

## Evolution Path

- **MVP**: Manual JSON/CSV/XLS normalized by agents, bulk upsert snapshots/channel rows, persisted import summary, bounded query, health capability.
- **成长期**: Add dedicated `resolve_wechat_article`, persist/query audience profiles, add account-level rollups if retrospective consumers need them.
- **成熟期**: If import volume grows materially, evaluate separate analytics store, async ingestion queue, or partitioning by account/date. Do not add these before volume requires them.

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。No queue, CDC, OLAP warehouse, event sourcing, or dashboard system.
- 是否引用了外部模式但没有适配检查：否。Layered architecture is used because it matches current code structure.
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。New import statuses and failure semantics are recorded in spec/plan; no cache or queue is introduced.

---

## Verification Strategy

- Migration SQL tests cover creation, indexes, constraints, FK relationships, and downgrade for `0004_wechat_analytics_ingestion`.
- Contract tests cover valid payloads, invalid dates, invalid rates, negative counts, source validation, bounded query validation, and P2 audience skip semantics.
- Repository tests cover snapshot insert/update counts, channel insert/update counts, import run creation/update, article resolver 0/1/>1 semantics, and list query SQL.
- Tool tests cover agents adapter response shape, dry-run no-write, unknown article unmatched, ambiguous article row error, schema drift mapping, raw_json omitted by default, and include_raw behavior.
- Health tests cover `wechat_analytics_ingestion=false` before required structures and `true` after all required structures are present.
- Integration smoke after implementation:
  - create or reuse one `wechat_article`
  - import one D+1 snapshot and two channel rows
  - repeat same import and observe `updated=1`
  - query snapshot list and confirm exactly one snapshot
  - verify `health.capabilities.wechat_analytics_ingestion == true`

---

## Stage Readiness

- 是否需要 `data-model.md`：需要，原因是本 feature 新增持久化实体、FK、唯一约束、状态和索引。
- 下一步建议：`tasks`
- 阻塞项：无 plan 阶段阻塞；tasks 阶段应把 ADR 决策拆成 migration/contracts/repository/tools/health/tests/docs/evidence 任务。

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | 必须 | 主实现计划 |
| data-model.md | 必须 | 展开 analytics tables、关系、约束和迁移策略 |
| tasks.md | 后续阶段生成 | 由 `tasks` 阶段产出 |
| acceptance.md | 后续阶段生成 | 记录本地测试、NAS migration、MCP live smoke 和 agents live smoke 证据 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| Layered architecture reference | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | 仅作为分层模式参考；实际以当前 hermes-db 代码结构为准 |
| Existing publication ledger pattern | UNVERIFIED | Local source: `packages/hermes-db/src/hermes_db_mcp/tools/wechat_articles.py`, `repositories/wechat_article_repo.py`, `services/schema.py` |
| Analytics import semantics | UNVERIFIED | Local product/contract judgment from `spec.md` and agents adapter dependency |
