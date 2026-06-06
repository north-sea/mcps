# Feature Specification: Hermes DB WeChat Analytics Ingestion

**Workspace**: `hermes-db-wechat-analytics-ingestion`  
**Created**: 2026-06-05  
**Status**: Ready for Plan  
**Input**: agents 仓 `wechat-analytics-ingestion` 已完成 mock/adapter/CLI，实现需要 hermes-db MCP 提供真实存储与 tools contract。

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|:---:|---|
| `multi-stage-workflow` | ❌ | hermes-db 只提供存储、校验、查询和 MCP tool contract，不负责编排导入 workflow |
| `external-side-effects` | ✅ | 需要新增 PG schema migration、幂等写入工具、查询工具和 health capability |
| `artifact-handoff` | ✅ | 本 feature 交付的 analytics tools 被 agents 仓 `wechat-analytics-ingestion` adapter/CLI 消费 |
| `user-visible-output` | ❌ | 不交付 UI；只交付结构化 MCP 响应和数据库记录 |
| `prior-closure-failure` | ✅ | 当前 agents 侧只能 mock/dry-run，缺真实 metric 存储、article resolution 和 live smoke 能力 |

**结论**: 命中 `external-side-effects` + `artifact-handoff` + `prior-closure-failure`。plan 阶段必须明确 schema migration、MCP tool contract、幂等 upsert、article resolution、health capability、agents live smoke evidence gate，以及旧 mock-only 路径如何在真实 contract 可用后退役。

---

## Problem

`agents` 仓已经把微信文章数据手工导入路径收敛为：

`external file row -> normalizer/mapping -> NormalizedArticleMetricRecord -> MCP upsert -> metric snapshot`

但 `hermes-db` 当前只有 topic、workflow persistence、wechat publication ledger，没有 analytics metric 存储、导入幂等 upsert、查询 tool 或 `wechat_analytics_ingestion` capability。因此 agents 侧只能 mock/dry-run，无法做 live smoke。

本 feature 在 `hermes-db` 内补齐最小 P1 analytics ingestion contract，让手工 JSON/CSV/XLS 转换后的文章指标能可靠绑定到已发布文章并写入数据库。

---

## Goals

- 提供微信文章指标快照和渠道日明细的持久化模型。
- 提供 MCP tool：批量 upsert 文章指标快照，并返回结构化 import summary。
- 提供 MCP tool：按账号、文章、日期窗口查询指标快照。
- 在 `health.capabilities` 中暴露 `wechat_analytics_ingestion=true`。
- 支持 article resolution 所需的稳定引用查询，避免 agents 侧依赖标题匹配。
- 保证重复导入同一 article/stat_date/window/source 的数据是幂等更新，不产生重复快照。

---

## Non-Goals

- 不在 hermes-db 解析 Excel/CSV/JSON 文件；文件解析属于 agents normalizer。
- 不做微信后台自动采集、浏览器自动化、任务队列或 dashboard。
- 不计算 account-level baseline 或趋势洞察，只预留后续可扩展字段。
- 不用文章标题做唯一绑定键。
- 不要求 P2 人群画像阻塞 P1；可以实现表和可选写入，但 P1 live smoke 只依赖 snapshot + channel daily。

---

## User Stories

### US1: 导入单篇文章 D+1/D+3/D+7 指标

作为 agents CLI，我可以调用 `bulk_upsert_wechat_article_metric_snapshots` 写入某篇文章某个统计窗口的指标；重复调用同一输入时更新旧记录，不新增重复快照。

**Acceptance**:
- 输入包含 `account`、`source`、`records[]`。
- 每条 record 必须能解析到唯一 `article_id`，或者直接包含合法 `article_id`。
- 同一 `(article_id, stat_date, window_label, source)` 只保留一条 snapshot。
- 返回 `total_rows`、`created`、`updated`、`skipped`、`unmatched`、`errors`、`status`。

### US2: 写入阅读趋势渠道明细

作为 agents CLI，我可以随 snapshot 一起写入每日渠道数据，例如 `全部/推荐/聊天会话/公众号消息/公众号主页/其他`。

**Acceptance**:
- 同一 `(article_id, metric_date, channel, source)` 幂等 upsert。
- `全部` 渠道允许存储，但作为 total row，不要求服务端展开或求和。
- 渠道明细错误不应破坏已校验通过的 snapshot 写入，除非事务策略选择 all-or-nothing 并在 plan 中明确。

### US3: 查询已导入指标

作为 agents 或后续分析消费者，我可以按 `account`、`article_id`、`date_from/date_to`、`window_label` 查询快照。

**Acceptance**:
- `list_wechat_article_metric_snapshots` 返回 `{ items, total?, limit?, offset? }`。
- 默认不返回大块 raw json；`include_raw=true` 时返回 raw_json。
- 查询结果包含 `snapshot_id`、`article_id`、`account`、`stat_date`、`window_label`、`source`、核心 P1 字段、`updated_at`。

### US4: 文章稳定引用解析

作为 agents article resolver，我可以用 article id、published URL、canonical URL、external reference 或 external refs 查找唯一文章。

**Acceptance**:
- 0 个匹配返回明确 not found/empty 语义。
- 多个匹配返回 ambiguous/conflict 语义，不应任选一个。
- 标题只能作为诊断信息，不参与唯一匹配。

---

## Functional Requirements

### FR-001: Database Tables

新增或等价实现以下表：

1. `hermes.wechat_article_metric_snapshots`
   - `snapshot_id UUID PRIMARY KEY`
   - `article_id UUID NOT NULL REFERENCES hermes.wechat_articles(article_id) ON DELETE CASCADE`
   - `account TEXT NOT NULL`
   - `stat_date DATE NOT NULL`
   - `window_label TEXT NOT NULL`
   - `source TEXT NOT NULL`
   - P1 overview/conversion numeric fields:
     - `read_user_count`
     - `average_stay_seconds`
     - `completion_rate`
     - `new_follow_user_count`
     - `share_user_count`
     - `wow_user_count`
     - `like_user_count`
     - `favorite_user_count`
     - `reward_cents`
     - `comment_count`
     - `delivered_user_count`
     - `account_message_read_user_count`
     - `first_share_user_count`
     - `total_share_user_count`
     - `share_generated_read_user_count`
   - `missing_fields TEXT[]`
   - `raw_json JSONB`
   - `import_run_id UUID NULL`
   - `collected_at TIMESTAMPTZ`
   - `created_at TIMESTAMPTZ`
   - `updated_at TIMESTAMPTZ`
   - unique: `(article_id, stat_date, window_label, source)`

2. `hermes.wechat_article_channel_daily_metrics`
   - `metric_id UUID PRIMARY KEY`
   - `article_id UUID NOT NULL REFERENCES hermes.wechat_articles(article_id) ON DELETE CASCADE`
   - `account TEXT NOT NULL`
   - `metric_date DATE NOT NULL`
   - `channel TEXT NOT NULL`
   - `source TEXT NOT NULL`
   - `read_user_count`
   - `share_user_count`
   - `raw_json JSONB`
   - `import_run_id UUID NULL`
   - timestamps
   - unique: `(article_id, metric_date, channel, source)`

3. Optional P2: `hermes.wechat_article_audience_profiles`
   - `profile_id UUID PRIMARY KEY`
   - `article_id UUID NOT NULL REFERENCES hermes.wechat_articles(article_id) ON DELETE CASCADE`
   - `account TEXT NOT NULL`
   - `dimension TEXT NOT NULL` where values include `gender`, `age`, `region`
   - `bucket TEXT NOT NULL`
   - `ratio DOUBLE PRECISION NOT NULL`
   - `source TEXT NOT NULL`
   - `raw_json JSONB`
   - `import_run_id UUID NULL`
   - timestamps
   - unique: `(article_id, dimension, bucket, source)`

4. Optional observability: `hermes.analytics_import_runs`
   - `import_run_id UUID PRIMARY KEY`
   - `account TEXT NOT NULL`
   - `source TEXT NOT NULL`
   - `status TEXT NOT NULL`
   - `total_rows`, `created`, `updated`, `skipped`
   - `unmatched JSONB`, `errors JSONB`, `metadata JSONB`
   - timestamps

### FR-002: MCP Tool `bulk_upsert_wechat_article_metric_snapshots`

Input shape must be compatible with agents adapter:

```json
{
  "account": "qiaomu",
  "source": "manual_json",
  "dry_run": false,
  "records": [
    {
      "article_id": "uuid",
      "stat_date": "2026-04-13",
      "window_label": "D+1",
      "read_user_count": 2682,
      "average_stay_seconds": 68,
      "completion_rate": 0.369128,
      "missing_fields": [],
      "raw_json": {}
    }
  ],
  "channel_daily_metrics": [],
  "audience_profiles": [],
  "import_metadata": {}
}
```

Response shape:

```json
{
  "import_run_id": "uuid",
  "total_rows": 1,
  "created": 1,
  "updated": 0,
  "skipped": 0,
  "unmatched": [],
  "errors": [],
  "status": "completed"
}
```

Status values: `completed`, `completed_with_errors`, `failed`, `dry_run`.

### FR-003: MCP Tool `list_wechat_article_metric_snapshots`

Input:

```json
{
  "account": "qiaomu",
  "article_id": "uuid",
  "date_from": "2026-04-13",
  "date_to": "2026-04-20",
  "window_label": "D+1",
  "limit": 50,
  "offset": 0,
  "include_raw": false
}
```

Response:

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

### FR-004: Health Capability

`health` must include:

```json
{
  "capabilities": {
    "wechat_analytics_ingestion": true
  }
}
```

If migration/table readiness is missing, either omit the capability or set it to `false`; agents fail closed.

### FR-005: Article Resolution

Add either:

- a dedicated tool such as `resolve_wechat_article`, or
- enhanced `list_wechat_articles` filters that support stable refs.

Minimum filters:

- `article_id`
- `published_url`
- `canonical_url`
- `external_reference`
- external ref pair: `ref_type`, `ref_value`

Result must allow agents to distinguish `0`, `1`, and `>1` matches.

---

## Data Validation

- `account`, `source`, `stat_date`, `window_label`, `article_id` are required for persisted snapshots.
- `completion_rate` and audience `ratio` should be stored as `0..1`; reject values outside range unless plan explicitly chooses coercion.
- Count fields must be non-negative integers where present.
- Date strings must be valid ISO dates.
- `source` should allow at least:
  - `manual_json`
  - `manual_csv`
  - `manual_xls`
  - `wechat_api`
  - `browser_automation`
  - `manual_patch`

---

## Error Semantics

- Invalid input: return tool error payload with `error`, `message`, optional `field`, optional `details`.
- Unknown article id: row-level `unmatched`, not silent success.
- Ambiguous article resolution: row-level `errors` with code `ambiguous_article`.
- Schema missing: tool error `schema_drift`.
- Dry run: validate and summarize without writing tables.

---

## Observability

Each bulk import should provide enough summary for CLI display:

- requested row count
- created count
- updated count
- skipped count
- unmatched rows
- row-level errors
- import run id when persisted

If `analytics_import_runs` is implemented, store summary and `import_metadata`.

---

## Verification Requirements

- Migration SQL tests cover new tables, indexes, unique constraints, and downgrade.
- Schema health tests verify required analytics tables.
- Repo tests cover:
  - snapshot insert
  - snapshot update on duplicate key
  - channel metric upsert
  - dry run no-write
  - invalid date/rate/count rejection
- Tool tests cover agents adapter contract response shape.
- Health test covers `wechat_analytics_ingestion`.
- Live smoke after implementation:
  - create or reuse one `wechat_article`
  - import one D+1 snapshot and two channel rows
  - repeat same import and observe `updated=1`
  - query snapshot list and confirm no duplicate snapshot

---

## Dependencies

- Depends on existing `wechat_articles` ledger from migration `0003_wechat_publication_ledger`.
- Agents-side contract exists in `/Users/yqg/personal/AI/agents/specs/wechat-analytics-ingestion/` and adapter types under `packages/adapters/src/mcp/analytics-types.ts`.

---

## Open Questions For Plan

- Should bulk upsert be all-or-nothing per import, or should row-level partial success be allowed?
- Should `analytics_import_runs` be mandatory for MVP or implemented as follow-up?
- Should P2 audience profiles be fully persisted in MVP, or only accepted and skipped with summary?
- Should article resolution be a new dedicated tool or an extension to `list_wechat_articles`?

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项：无 specify 阶段阻塞；上方开放问题应在 plan 中决策并落到实现边界。
- Evidence basis：当前 repo 已有 `0003_wechat_publication_ledger`、`wechat_articles` repository/tools/tests 和 health capability 模式；本 feature 依赖该 article ledger，并新增 analytics schema 与 MCP contract。
