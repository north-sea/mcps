# Feature Specification: Topic Plan Feedback And Optimization

**Workspace**: `topic-plan-feedback-and-optimization`  
**Created**: 2026-07-01  
**Reviewed**: 2026-07-02  
**Status**: Accepted (P1 Conditional)  
**Input**: 用户描述: "后续需要根据每个公众号选题的采纳率来优化选题相关配置；现在入库字段只够粗粒度分析，需要补充反馈事件和配置版本字段。"

> 注意：本 spec 作为独立后续 feature 新增，暂不修改 `specs/.active`。当前 `specs/.active` 已有既有未提交修改，为避免覆盖上下文，本次只新增 feature 目录和 spec。

---

## Discovery Findings

- `hermes.topic_candidates` 已记录 `account_id`、`track_id`、`source`、`hot_score`、`fit_score`、`novelty_score`、`status`、`topic_id`、`rejection_reason`、`adopted_at`，可用于候选池和上游 source 粗粒度转化分析。
- `hermes.topic_candidate_tracks` 已记录 `keywords`、`negative_keywords`、`scoring_profile`，但没有配置版本号或快照 hash。
- `hermes.topic_plans` 已记录 `status=planned|rejected|consumed|archived`、`topic_id`、`consumed_at`、`evidence`、`llm_metadata`，可分析 planned -> consumed，但不能区分人工采纳、写作链路自动消费、延期、主观否决或发布后表现。
- 当前 `topic_plans` 通过 `candidate_id` unique 绑定一个 active plan；适合保留为 handoff 主表，不适合把所有人工反馈历史塞进 plan row。
- 现有字段可支持 dashboard 粗看：按 account/track/source 统计 candidate -> plan -> consumed；但不够支撑“根据采纳率优化关键词、negative keywords、scoring profile、prompt/runtime”的闭环。

---

## Feature Traits *(LM 自动检测，用户可 override)*

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | candidate 入池、plan 生成、人工/写作采纳、发布表现、配置优化是跨阶段闭环。 |
| `external-side-effects` | ✅ | 新增 DB 表/MCP 写工具，记录人工反馈和配置快照。 |
| `artifact-handoff` | ✅ | feedback 和 optimization report 会被 Hermes、Codex、后续配置调优流程消费。 |
| `user-visible-output` | ✅ | 用户会查看采纳率、拒绝原因和配置优化建议。 |
| `prior-closure-failure` | ✅ | 现有 `topic_plans` 已能落库，但无法准确表达采纳率优化所需的反馈语义。 |
| `bugfix-loop-breaker` | ❌ | 这是分析闭环能力增强，不是 regression 修复。 |

**结论**: 下游 plan/tasks/verify 需要启用 Producer-Consumer Matrix、Evidence Gate、Workflow Replay 和配置演进审查；不启用 bugfix-loop-breaker 专项。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 记录人工采纳与不采纳反馈 (Priority: P1)

作为公众号运营者，我希望能对一个 `topic_plan` 明确记录“采纳、拒绝、延期、归档、已写、已发布”等事件及原因，以便后续统计真实采纳率，而不是只用 `consumed` 状态猜测。

**Why this priority**: 没有反馈事件，就无法区分“计划生成了但没人想写”和“已经进入写作链路”，优化会误判。

**Acceptance Scenarios**:

1. **[US1-1] 记录人工采纳**  
   **Given** 一个 `status=planned` 的 topic plan  
   **When** 调用 `record_topic_plan_feedback(plan_id, event_type="accepted", dedupe_key="ui-click-123", reason_tags=["worth-writing"], decided_by="user")`  
   **Then** hermes-db 创建一条反馈事件，返回 `event_id`、`plan_id`、`event_type=accepted`、`created_at`、`event_at`

2. **[US1-2] 记录人工拒绝并保留原因**  
   **Given** 一个 `status=planned` 的 topic plan  
   **When** 调用 `record_topic_plan_feedback(plan_id, event_type="rejected", reason_tags=["off-brand", "too-generic"], note="像模板题")`  
   **Then** 反馈事件保存 reason tags 和 note，但不自动删除或覆盖原 plan 内容

3. **[US1-3] 记录写作/发布生命周期事件**  
   **Given** 一个已被写作链路消费的 topic plan  
   **When** 调用 `record_topic_plan_feedback(plan_id, event_type="written"|"published", topic_id=<topic_id>, metadata={...})`  
   **Then** 事件可用于后续采纳率和发布表现分析

**Edge Cases**:

- **[US1-4] 无效 plan**: 不存在的 `plan_id` 必须返回 structured not-found。
- **[US1-5] 非法事件类型**: 不支持的 `event_type` 必须 validation error，不写入。
- **[US1-6] 重复事件**: 同一 `plan_id` 可有多条事件；写入必须支持 `dedupe_key`，并以 `(plan_id, event_type, dedupe_key)` 作为 MVP 幂等唯一范围，避免按钮重复点击或 agent 重试导致 report 膨胀。
- **[US1-7] 补录历史事件**: 反馈事件必须支持 `event_at` 表示事件实际发生时间；未传时默认等于写入时间。
- **[US1-8] 发布事件 lineage**: `published` 事件必须至少携带 `topic_id`、`publication_id` 或 `publication_idempotency_key` 之一，否则 validation error。

### User Story 2 - 保存规划配置版本和快照 (Priority: P1)

作为后续优化流程，我希望每次 `topic_plan` 能关联当时使用的账号配置、track 配置、scoring profile、runtime/prompt 版本，以便判断哪套配置带来的采纳率更高。

**Why this priority**: 没有配置版本或快照，采纳率只能按当前配置回看历史，会把旧配置效果错误归因到新配置上。

**Acceptance Scenarios**:

1. **[US2-1] plan 可携带配置快照 metadata**  
   **Given** planning runtime 生成 `UpsertTopicPlanInput`  
   **When** 写入 `llm_metadata.config_snapshot`  
   **Then** 记录 `runtime_name`、`runtime_version`、`planner_version`、`account_config_hash`、`track_config_hash`、`scoring_profile_hash`

2. **[US2-2] track config 可被版本化引用**  
   **Given** `topic_candidate_tracks.scoring_profile`、`keywords` 或 `negative_keywords` 改动  
   **When** 后续 plan 写入  
   **Then** plan/feedback report 能区分改动前后的配置效果

3. **[US2-3] 缺少版本信息可被识别**  
   **Given** 旧 plan 没有配置版本字段  
   **When** 生成采纳率 report  
   **Then** 旧数据归入 `unknown_config`，不和新版配置混算

**Edge Cases**:

- **[US2-4] hash 不稳定**: JSON hash 必须基于 canonical serialization，字段顺序不应改变 hash。
- **[US2-5] 配置过大**: report 默认只返回 hash 和摘要，不返回完整大 JSON。

### User Story 3 - 生成采纳率与优化分析报告 (Priority: P1)

作为内容系统维护者，我希望按 account、track、source、runtime_version、config hash 查询采纳率、拒绝原因分布和 consumed/published 转化，以便调整关键词、negative keywords、scoring profile 和 planning runtime。

**Why this priority**: 这是“根据采纳率优化配置”的直接输出。

**Acceptance Scenarios**:

1. **[US3-1] 按账号/track 汇总采纳率**  
   **Given** 多个 account/track 下有 topic plans 和 feedback events  
   **When** 调用 `get_topic_plan_feedback_report(account_id, track_id, window_days=30)`  
   **Then** 返回 `planned_count`、`accepted_count`、`rejected_count`、`deferred_count`、`consumed_count`、`published_count`、`acceptance_rate`、`consume_rate`

2. **[US3-2] 拒绝原因分布**  
   **Given** 多条 rejected feedback 带 `reason_tags`  
   **When** 生成 report  
   **Then** 返回 reason tag 计数和 top reasons，例如 `too-generic`、`off-brand`、`low-timeliness`、`weak-source`

3. **[US3-3] 配置版本维度对比**  
   **Given** 不同 `track_config_hash` 或 `runtime_version` 下有足够样本  
   **When** 生成 report  
   **Then** 返回按配置分组的采纳率和样本数，并标记样本不足的组

**Edge Cases**:

- **[US3-4] 样本不足**: 分母低于阈值时 report 必须返回 `sample_warning`，不输出强优化结论。
- **[US3-5] 事件冲突**: 同一 plan 同时有 accepted 和 rejected 时，report 必须使用固定 precedence，避免不同调用方各自按“最新事件”解释。
- **[US3-6] 时间窗口**: report 默认按 `event_at` 过滤；`created_at` 仅用于审计/补录查询，避免早期实验污染当前效果判断。

### User Story 4 - 给配置调优提供可执行建议 (Priority: P2)

作为 Hermes/Codex 配置调优流程，我希望能根据 report 生成保守的配置建议草案，而不是自动修改生产配置，以便人工确认后再调整。

**Why this priority**: 配置优化是目标，但自动改关键词和 scoring profile 风险较高，MVP 应先给建议不自动写配置。

**Scope note**: 本 feature 的 P1 交付只保证 report 提供足够证据；P2 的 optimization summary 作为可选 tool 输出，不阻塞 feedback/report MVP 上线，也不阻塞 `health.capabilities.topic_plan_feedback=true`。

**Acceptance Scenarios**:

1. **[US4-1] 输出优化建议草案**  
   **Given** 某 track 的 `too-generic` 拒绝原因占比高  
   **When** 生成 optimization summary  
   **Then** 返回建议，例如新增 negative keywords、提高 fit threshold、调整 source 权重，但不自动修改 track config

2. **[US4-2] 建议包含证据引用**  
   **Given** report 中有样本 plan 和 feedback  
   **When** 输出建议  
   **Then** 每条建议包含 sample plan ids 或 reason tag 依据

**Edge Cases**:

- **[US4-3] 无足够样本**: 返回“继续采集反馈”，不生成强建议。
- **[US4-4] 隐私与日志**: report 不应泄露 secret、完整 prompt 或未经裁剪的 raw payload。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: hermes-db 必须新增反馈事件实体，建议为 `hermes.topic_plan_feedback_events`，通过 `plan_id` 关联 `topic_plans`。
- **FR-002**: 反馈事件必须支持 `event_type`：`accepted`、`rejected`、`deferred`、`archived`、`written`、`published`、`score_adjusted`。
- **FR-003**: 反馈事件必须支持 `reason_tags` JSONB array、`note`、`decided_by`、`topic_id`、`metadata`、`event_at`、`created_at`。
- **FR-003A**: 反馈事件必须支持 `dedupe_key`，并以 `(plan_id, event_type, dedupe_key)` 作为 MVP 幂等唯一范围；未提供 `dedupe_key` 的写入仍允许，但必须在 report precedence 中按 plan 去重，不能放大采纳率。
- **FR-003B**: 反馈事件必须支持 `event_at` 表示事件实际发生时间；未提供时默认等于 `created_at`。
- **FR-003C**: `published` 事件必须至少携带 `topic_id`、`publication_id` 或 `publication_idempotency_key` 之一，三者可通过显式字段或 `metadata` 提供。
- **FR-004**: 必须新增 MCP tool `record_topic_plan_feedback`，用于写入反馈事件。
- **FR-005**: 必须新增 MCP tool `list_topic_plan_feedback`，支持按 `plan_id`、`account_id`、`track_id`、`event_type`、`event_at` 时间窗口查询；可选支持 `created_at` 审计窗口。
- **FR-006**: 必须新增 MCP tool `get_topic_plan_feedback_report`，返回采纳率、消费率、发布率、拒绝原因分布、按 source/runtime/config 分组的统计。
- **FR-007**: report 必须定义固定事件 precedence：`published > written > accepted > deferred > rejected > archived`；同一 precedence 下按 `event_at DESC, created_at DESC` 选最新，同时保留原始事件列表。
- **FR-008**: report 必须支持样本不足标记，例如 `sample_warning=true` 和 `min_sample_size`。
- **FR-009**: planning runtime 必须在 `llm_metadata.config_snapshot` 中记录稳定配置标识：`runtime_name`、`runtime_version`、`planner_version`、`account_config_hash`、`track_config_hash`、`scoring_profile_hash`；report 默认从该路径读取，缺失时归入 `unknown_config`。
- **FR-010**: 配置 hash 必须使用 canonical JSON 序列化，避免字段顺序导致 hash 漂移。
- **FR-011**: report 不得读取或返回完整 secret、Authorization header、API key、完整 raw prompt 或未裁剪 raw payload。
- **FR-012**: health capability 必须新增 `topic_plan_feedback`；P1 表、索引和三个 P1 MCP tool contract 完整时返回 true，P2 `get_topic_plan_optimization_summary` 不参与 health gate。

### MCP Tool Contract

```text
record_topic_plan_feedback(input) -> TopicPlanFeedbackEvent
list_topic_plan_feedback(filters) -> ListTopicPlanFeedbackResult
get_topic_plan_feedback_report(filters) -> TopicPlanFeedbackReport
get_topic_plan_optimization_summary(filters) -> TopicPlanOptimizationSummary  # P2 optional
health() -> capabilities.topic_plan_feedback
```

### DTO Requirements

```ts
type TopicPlanFeedbackEventType =
  | "accepted"
  | "rejected"
  | "deferred"
  | "archived"
  | "written"
  | "published"
  | "score_adjusted";

interface RecordTopicPlanFeedbackInput {
  plan_id: string;
  event_type: TopicPlanFeedbackEventType;
  dedupe_key?: string | null;
  reason_tags?: string[];
  note?: string | null;
  decided_by?: string | null;
  topic_id?: string | null;
  metadata?: Record<string, unknown>;
  event_at?: string | null;
}

interface TopicPlanFeedbackEvent {
  event_id: string;
  plan_id: string;
  account_id: string;
  track_id?: string | null;
  event_type: TopicPlanFeedbackEventType;
  dedupe_key?: string | null;
  reason_tags: string[];
  note?: string | null;
  decided_by?: string | null;
  topic_id?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  event_at: string;
}

interface TopicPlanFeedbackReport {
  account_id?: string;
  track_id?: string;
  window_days: number;
  planned_count: number;
  accepted_count: number;
  rejected_count: number;
  deferred_count: number;
  consumed_count: number;
  published_count: number;
  acceptance_rate: number | null;
  consume_rate: number | null;
  publish_rate: number | null;
  reason_tag_counts: Record<string, number>;
  by_source: FeedbackMetricGroup[];
  by_runtime_version: FeedbackMetricGroup[];
  by_track_config_hash: FeedbackMetricGroup[];
  sample_warning?: boolean;
  min_sample_size: number;
}

interface TopicPlanOptimizationSummary {
  account_id?: string;
  track_id?: string;
  sample_warning?: boolean;
  suggestions: Array<{
    type: "negative_keyword" | "fit_threshold" | "source_weight" | "runtime_prompt";
    summary: string;
    evidence_plan_ids: string[];
    reason_tags: string[];
  }>;
}
```

### Non-Functional Requirements

- **NFR-001**: 反馈写入必须幂等友好；客户端重试不得因为重复 accepted 事件导致 report 夸大采纳率；有 `dedupe_key` 时写入层去重，无 `dedupe_key` 时 report 层按 precedence 去重。
- **NFR-002**: report 查询必须能按 account/time window 低延迟返回，至少需要 `(account_id, track_id, created_at)` 和 `(plan_id, created_at)` 索引。
- **NFR-003**: 反馈事件是 append-only 审计记录；不得通过更新 plan row 丢失历史反馈。
- **NFR-004**: 采纳率 report 必须保留分母定义，避免把 `planned_count`、`candidate_count`、`feedback_count` 混用。
- **NFR-005**: 所有 tool 错误必须遵循 hermes-db 现有 structured error 风格。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 可归因 | 每个反馈可关联 plan/account/track/source/runtime/config | 支撑配置优化而非凭感觉调参 | report 分组测试 | 是 |
| 一致性 | report 事件 precedence 明确 | 避免重复事件或冲突事件污染采纳率 | precedence 单测 | 是 |
| 可审计 | 反馈 append-only | 人工判断会变化，需要保留历史 | schema + repo 测试 | 是 |
| 安全 | 不泄露 secret/raw prompt | report 可能给多个 agent 消费 | 敏感字段过滤测试 | 是 |
| 可演进 | 配置 hash 和 metadata 可扩展 | 后续支持 A/B 配置和自动建议 | DTO 和 migration 测试 | 否 |

### Key Entities

- **TopicPlanFeedbackEvent**: 围绕一个 topic plan 的人工或系统反馈事件，包含事件类型、原因标签、note、decided_by、topic_id、metadata 和时间。
- **PlanningConfigSnapshot**: 写入 `llm_metadata.config_snapshot` 的配置版本摘要，包含 runtime/prompt/account/track/scoring profile 的 hash 或版本。
- **FeedbackReport**: 按账号、track、source、runtime、配置 hash 聚合的采纳率和拒绝原因报告。
- **OptimizationSuggestion**: 基于 report 的保守配置建议草案，不自动修改生产配置。

---

## Producer-Consumer Matrix

| Producer | Artifact / State | Consumer | Contract |
|---|---|---|---|
| Human operator / Hermes / Codex | feedback event | hermes-db MCP | `record_topic_plan_feedback` |
| Writing agent | `written` / `published` event | feedback report | plan/topic lineage |
| Topic planning runtime | config hashes in `llm_metadata` | feedback report | stable runtime/config attribution |
| hermes-db report tool | acceptance and reason metrics | Hermes/Codex optimization workflow | sample-aware summary |
| Human operator | approved config change | track config sync feature | out-of-scope for this feature |

---

## Out of Scope

- 不自动修改 `topic_candidate_tracks.keywords`、`negative_keywords` 或 `scoring_profile`；MVP 只生成建议。
- 不替代 `topic_plans.status` 生命周期；feedback events 是补充审计和分析层。
- 不实现发布后详细阅读/点赞/分享等公众号 analytics ingestion；可在 report 中消费已有 analytics，但不是本 feature 的主范围。
- 不要求旧 plan 补齐历史 feedback；旧数据可归入 `unknown_feedback` 或 `unknown_config`。
- 不改变 `topic_plans.candidate_id` unique MVP 约束。

---

## Unclear Questions

- `accepted` 是否应自动把 plan 状态保持为 `planned`，还是新增 `accepted` plan status？已采纳：不新增 plan status，用 feedback event 表达。
- `published` 事件是否应强制要求 `topic_id` 或 publication ledger id？已采纳：`published` 必须至少携带 `topic_id`、`publication_id` 或 `publication_idempotency_key` 之一。
- feedback event 是否需要幂等键 `dedupe_key`？已采纳：加入 `dedupe_key`，MVP 唯一范围为 `(plan_id, event_type, dedupe_key)`。
- report 的时间窗口默认使用 `event_at`，缺失时 fallback 到 `created_at`。
- report 的默认 `min_sample_size` 已采纳：MVP 默认 5，并允许参数覆盖。

---

## Stage Readiness

- 下一步建议：等待用户确认 commit plan；如暂不提交，则记录 not_submitted 并保留当前 dirty files。
- 阻塞项：无。P1 feedback/report contract 已验收；P2 summary 已明确延期。
