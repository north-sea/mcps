# Implementation Plan: Topic Plan Feedback And Optimization

**Workspace**: `topic-plan-feedback-and-optimization` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/topic-plan-feedback-and-optimization/spec.md`

> 临时 feature：本计划不修改 `specs/.active`，当前 active 仍由既有工作流持有。

---

## Summary

Extend the existing hermes-db topic planning contract with append-only feedback events, stable planning config attribution, and sample-aware feedback reports. The recommended implementation stays inside the current hermes-db MCP service: Alembic migration, repository functions, MCP tools, schema health, and focused repo/tool/report tests.

只有一个合理实现方向：复用现有 `topic_plans`、`topic_candidates`、`wechat_retrospective` 的 repo/tool/schema-health 模式。独立分析服务、队列或 agents-side shadow storage 会增加一致性和部署成本，不符合当前 MVP。

---

## Architecture Overview

```text
Human / Hermes / Codex / writing agents
  record feedback, written, published events
        |
        v
hermes-db MCP tools
  record_topic_plan_feedback
  list_topic_plan_feedback
  get_topic_plan_feedback_report
  get_topic_plan_optimization_summary (P2 optional)
        |
        v
repository layer
  topic_plan_feedback_repo.py
  topic_plan_repo.py config snapshot read path
        |
        v
Postgres hermes schema
  topic_plans
  topic_plan_feedback_events
  topic_candidates / topic_candidate_tracks
```

Write path remains synchronous and database-backed. Report path uses SQL aggregation over `topic_plans` plus feedback events; it does not mutate track config.

---

## Architecture Reference

| 参考模式 / 模板 | 来源 URL | 适配点 | 不适配点 | 当前阶段 |
|---|---|---|---|---|
| 单体 + 分层 | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | 当前 hermes-db 已是 MCP tool -> repo -> Postgres 分层，新增能力可沿用 | 不需要拆微服务或 BFF | MVP |
| 事件溯源思想 | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | feedback events append-only，适合审计人工判断变化 | 不引入完整 event bus、投影服务或异步一致性模型 | MVP |

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| Human / Hermes / Codex | `TopicPlanFeedbackEvent` | `list_topic_plan_feedback`, report SQL | Tool tests can read written event; repo tests verify event row shape |
| Writing agent | `written` event with `topic_id` | feedback report | Report fixture counts `consumed_count` without double-counting accepted |
| Publishing flow / human repair | `published` event with publication lineage | feedback report and optimization summary | Validation test rejects missing lineage; report test counts published once |
| Planning runtime | `llm_metadata.config_snapshot` | report grouping | Report fixture separates `track_config_hash` and `unknown_config` |
| Report tool | `TopicPlanFeedbackReport` | Hermes/Codex tuning workflow | Tool test returns reason distribution, sample warning, grouped metrics |
| Report tool | `TopicPlanOptimizationSummary` (P2 optional) | Human-approved config sync follow-up | Summary includes evidence plan ids and never writes config |

**孤儿 artifact 处理**: `OptimizationSummary` 是 P2 optional。若 implementation 暂不做该 tool，必须在 tasks 中明确切为后续，不能留下无入口 DTO。

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|---|---|---|---|
| 可归因 | 每条反馈可追溯到 plan/account/track/source/config | feedback row 冗余 `account_id`、`track_id`；`source` 和 config 从 plan row / config snapshot 聚合 | repo/report fixtures |
| 幂等 | 客户端重试不放大采纳率 | `dedupe_key` 可选；有 key 时 unique，无 key 时 report 按 precedence 去重 | duplicate event tests |
| 一致性 | 冲突事件有确定 precedence | report 统一使用 `published > written > accepted > deferred > rejected > archived` | precedence unit tests |
| 可审计 | 人工判断历史 append-only | 不更新旧 feedback row 表达状态变化 | migration/repo tests |
| 安全 | report 不泄露 secret、完整 prompt 或 raw payload | report DTO 只返回 hash、摘要和裁剪证据 | sensitive filtering tests |
| 性能 | account/time window report 可低延迟 | indexes on `(account_id, track_id, event_at)` and `(plan_id, event_at)` | migration/schema tests |

---

## Capacity / Scale Notes

- **规模假设**: 单人/小团队公众号运营，topic plan 和 feedback 为日级到千级数据量，不需要离线数仓。
- **读写特征**: feedback 写少读多；report 是按账号、track、时间窗口的聚合读。
- **一致性**: feedback 写入和查询需要读到已提交事件；report 可接受数据库事务级一致性，不需要异步投影。
- **失败代价**: 重复写会污染采纳率；漏写会降低样本量；错误泄露 prompt/secret 风险高于延迟风险。

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|---|---|---|---|---|---|
| ADR-001: feedback 独立表 | `topic_plans` 是 handoff 主表，不适合塞历史反馈 | A: `topic_plan_feedback_events`; B: update plan row; C: metadata array | 选择 A | 新增 migration/repo/tool | Local code: `topic_plans` unique candidate model |
| ADR-002: 同步 MCP 写入 | MVP 不需要异步事件总线 | A: direct DB insert; B: queue/event bus | 选择 A | 高并发扩展有限 | Existing hermes-db MCP repo pattern |
| ADR-003: `dedupe_key` 可选但推荐 | 既要支持 UI/agent 重试，也要允许人工补录 | A: required key; B: optional key + report precedence; C: no key | 选择 B | 无 key 的重复事件只能 report 去重 | Spec accepted clarification |
| ADR-004: report 默认按 `event_at` 窗口 | 补录历史事件不能按写入时间误算 | A: `event_at`; B: `created_at` only | 选择 A | 需要额外字段和索引 | Spec accepted clarification |
| ADR-005: config snapshot 放 `llm_metadata.config_snapshot` | 现有 `topic_plans` 已有 JSON metadata | A: metadata path; B: new columns; C: snapshot table | MVP 选择 A | JSONB 查询需谨慎，未来可升列 | Existing `topic_plans.llm_metadata` |
| ADR-006: P2 summary 不自动写配置 | 自动调参风险高 | A: summary only; B: write track config | 选择 A | 仍需人工操作闭环 | Spec out of scope |

---

## Module Design

### Module: Migration `0011_topic_plan_feedback`

**YAGNI stop**: Layer 3, Postgres constraints/indexes are enough.

**职责**: Add `hermes.topic_plan_feedback_events` and, if useful, schema-health checks for feedback capability.

**改动概述**:

- Add Alembic migration after `0010_topic_plans`.
- Create feedback event table with FK to `hermes.topic_plans(plan_id)`.
- Add idempotency unique index for non-null `dedupe_key`.
- Add report indexes for plan/account/track/time filters.

**关键接口 / 行为**:

```text
topic_plan_feedback_events(
  event_id uuid primary key default gen_random_uuid(),
  plan_id uuid not null references hermes.topic_plans(plan_id) on delete cascade,
  account_id text not null,
  track_id text,
  event_type text not null,
  dedupe_key text,
  reason_tags jsonb not null default '[]',
  note text,
  decided_by text,
  topic_id uuid references hermes.topics(id) on delete set null,
  metadata jsonb not null default '{}',
  event_at timestamptz not null default now(),
  created_at timestamptz not null default now()
)
```

**注意事项**:

- `dedupe_key` unique 应使用 partial unique index：`WHERE dedupe_key IS NOT NULL`。
- `published` lineage 需要 check 可能较难跨 JSONB 完整表达；MVP 可在 tool validation 中强制。

### Module: Repository `topic_plan_feedback_repo.py`

**YAGNI stop**: Layer 5, plain asyncpg repository functions match existing code.

**职责**: Own feedback insert/list/report SQL and row serialization inputs.

**改动概述**:

- `record_topic_plan_feedback(pool, ...)` fetches plan context, validates existence, inserts event.
- `list_topic_plan_feedback(pool, filters...)` supports plan/account/track/type/time pagination.
- `get_topic_plan_feedback_report(pool, filters...)` aggregates per plan using precedence.

**关键接口 / 行为**:

```text
record:
  fetch plan by plan_id to derive account_id, track_id, source/config
  validate event_type and published lineage
  INSERT ... ON CONFLICT (plan_id, event_type, dedupe_key)
    WHERE dedupe_key IS NOT NULL DO NOTHING
  if conflict happened, fetch and return the existing event
  return event row

report:
  select plans in window/account/track
  left join events in event_at window
  choose effective event per plan by precedence, event_at DESC, created_at DESC
  group by source/runtime_version/track_config_hash
  return counts, rates, reason tags, sample_warning
```

**注意事项**:

- `planned_count` 分母应来自 matching `topic_plans`，不是 feedback event count。
- `consumed_count` 可兼容 `topic_plans.status='consumed'` 和 `written`/`published` feedback，但必须在 report 中说明口径。
- Do not return raw `llm_metadata`, prompt, Authorization, API keys, or raw payload.

### Module: MCP Tools `topic_plan_feedback.py`

**YAGNI stop**: Layer 5, FastMCP functions and dict DTOs match current service style.

**职责**: Expose feedback record/list/report tools to agents.

**改动概述**:

- Add `packages/hermes-db/src/hermes_db_mcp/tools/topic_plan_feedback.py`.
- Register it in `server.register_tools()`.
- Use existing `contracts.error(...)`, pagination helpers, and timestamp serialization style.

**关键接口 / 行为**:

```text
record_topic_plan_feedback(plan_id, event_type, ctx,
                           dedupe_key?, reason_tags?, note?, decided_by?,
                           topic_id?, metadata?, event_at?)

list_topic_plan_feedback(ctx, plan_id?, account_id?, track_id?,
                         event_type?, created_from?, created_to?,
                         event_from?, event_to?, limit?, offset?)

get_topic_plan_feedback_report(ctx, account_id?, track_id?,
                               window_days=30, min_sample_size=5,
                               group_by?)
```

**注意事项**:

- Tool validation should run before repository writes.
- Because MCP annotations are static while `dedupe_key` is optional, set `record_topic_plan_feedback` `idempotentHint=False`; document that supplying `dedupe_key` makes client retries idempotency-safe.
- P2 `get_topic_plan_optimization_summary` may live in the same module only if implemented in this feature.

### Module: Config Snapshot Handling

**YAGNI stop**: Layer 5, reuse existing `llm_metadata` JSONB path before adding columns.

**职责**: Define and consume `llm_metadata.config_snapshot`.

**改动概述**:

- Do not migrate existing rows.
- Report reads `llm_metadata -> 'config_snapshot'`.
- Missing snapshot maps to `unknown_config`.
- Add a small canonical JSON hash helper only if planning runtime code in this repo writes the snapshot; otherwise record the expected contract in tests/spec.

**关键接口 / 行为**:

```json
{
  "config_snapshot": {
    "runtime_name": "wechat-topic-planner",
    "runtime_version": "2026-07-01",
    "planner_version": "v1",
    "account_config_hash": "sha256:...",
    "track_config_hash": "sha256:...",
    "scoring_profile_hash": "sha256:..."
  }
}
```

**注意事项**:

- Hash must be based on canonical JSON serialization.
- Report returns hashes and light summaries only, not full config JSON.

### Module: Schema Health

**YAGNI stop**: Layer 3, database metadata inspection follows existing health checks.

**职责**: Add `health().capabilities.topic_plan_feedback`.

**改动概述**:

- Extend `services/schema.py` with `inspect_topic_plan_feedback_schema(pool)`.
- Extend `tools/health.py` default capability map and schema merge.
- Add schema-health tests for missing table, missing constraint, missing index.

### Module: Tests

**YAGNI stop**: Layer 4, reuse existing pytest and fake-pool SQL assertion style.

**职责**: Pin migration text, repository SQL behavior, tool validation, report semantics, and health gating.

**改动概述**:

- Add migration SQL assertions to `test_migration_sql.py`.
- Add `test_topic_plan_feedback_repo_sql.py`.
- Add `test_topic_plan_feedback_tools.py`.
- Add `test_topic_plan_feedback_schema_health.py`.
- Add report fixtures for duplicate events, conflict precedence, unknown config, sample warning, and sensitive field filtering.

---

## Data Model

Detailed storage and DTO design is in [data-model.md](data-model.md).

---

## Project Structure

```text
packages/hermes-db/migrations/versions/0011_topic_plan_feedback.py
packages/hermes-db/src/hermes_db_mcp/repositories/topic_plan_feedback_repo.py
packages/hermes-db/src/hermes_db_mcp/tools/topic_plan_feedback.py
packages/hermes-db/src/hermes_db_mcp/services/schema.py
packages/hermes-db/src/hermes_db_mcp/tools/health.py
packages/hermes-db/src/hermes_db_mcp/server.py
packages/hermes-db/tests/test_topic_plan_feedback_repo_sql.py
packages/hermes-db/tests/test_topic_plan_feedback_tools.py
packages/hermes-db/tests/test_topic_plan_feedback_schema_health.py
packages/hermes-db/tests/test_migration_sql.py
```

---

## Risks and Tradeoffs

- Optional `dedupe_key` preserves manual flexibility but cannot prevent all duplicate writes at insert time.
- JSONB config snapshot avoids schema churn now, but heavy report filtering by config may later need generated columns or dedicated snapshot table.
- Report SQL can become complex; keep MVP groupings fixed before adding dynamic dimensions.
- P2 optimization summary should not be half-implemented. Either implement with evidence-only output or defer cleanly.

---

## Evolution Path

- **MVP**: Append-only feedback table, config snapshot path, three P1 MCP tools, health flag, report with fixed groupings.
- **成长期**: Promote hot config snapshot fields to generated columns or indexed columns when report volume grows.
- **成熟期**: Add approved config-change workflow and A/B config versions; consider async materialized report if query latency becomes a problem.

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否，未引入 event bus、数仓、独立服务或自动调参。
- 是否引用了外部模式但没有适配检查：否，事件溯源只借用 append-only 审计思想。
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否；新增表、tool、health capability 和 report 口径已记录。

---

## Verification Strategy

- Migration text tests verify table, constraints, indexes, rollback.
- Schema-health tests verify `topic_plan_feedback` capability only turns true when required schema exists.
- Tool tests verify validation: invalid plan, invalid event type, duplicate `dedupe_key`, missing published lineage, pagination.
- Repository SQL tests verify insert idempotency, list filters, event time filters, and no raw payload leakage.
- Report tests verify precedence, counts/rates, `unknown_config`, `sample_warning`, reason tag distribution, and sensitive metadata filtering.
- Existing `topic_plan` tests should continue passing to prove feedback events did not alter plan lifecycle.

---

## Stage Readiness

- 是否需要 `data-model.md`：需要。该 feature 新增实体、约束、索引、DTO 和 report 口径，单靠 plan.md 不够清晰。
- 下一步建议：等待用户确认 [commit-plan.md](commit-plan.md)，或选择暂不提交。
- 阻塞项：无。P1 implementation, focused verification and acceptance record complete.

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|---|---|---|
| plan.md | 必须 | 当前文件 |
| data-model.md | 需要 | 反馈事件表、DTO、report 口径 |
| tasks.md | 后续阶段生成 | 由 `tasks` 阶段产出 |
| acceptance.md | 后续阶段生成 | 用于最终验收结论 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|---|---|---|
| 分层单体 / 事件溯源参考 | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | 作为模式参考，不替代本仓库现实 |
| hermes-db MCP module shape | UNVERIFIED | Local code: `packages/hermes-db/src/hermes_db_mcp/` |
| accepted spec clarifications | UNVERIFIED | Local spec: `specs/topic-plan-feedback-and-optimization/spec.md` |
