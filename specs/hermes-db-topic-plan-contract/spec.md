# Feature Specification: Hermes DB Topic Plan Contract

**Workspace**: `hermes-db-topic-plan-contract`  
**Created**: 2026-06-30  
**Status**: Draft  
**Input**: 用户描述: "将账号绑定选题规划中阻塞的 hermes-db 侧 topic_plans 契约详细写成 SDD spec；生产方不再限定为独立部署的 hotspot-agent，可由 Hermes cron + skill/subagent、Codex/Claude Code 或轻量 CLI 调用。"

> 注意：本文件按 SDD spec 格式新增，但未同步修改 `specs/.active`。检查时发现 mcps 工作树已有未提交的 `specs/.active` 修改，当前 active feature 为 `wechat-content-runtime-contracts`，为避免覆盖用户现有上下文，本次只新增独立 spec 文件。

---

## Discovery Findings

- mcps 当前分支为 `main`，近期 hermes-db 相关提交已包含 topic candidate 基础能力：`aee7062 feat: add topic candidate MCP contract`、`1e4b951 test: cover topic candidate health capability`、`853d1ed feat: add topic candidate track config sync`、`0a28672 fix: decode topic track json payloads`。
- 当前已有 `topic_candidates`、`topic_candidate_accounts`、`topic_candidate_tracks` 的 schema health 检查和 MCP tools；candidate 状态机已支持 `new -> shortlisted`。
- 当前未发现 `topic_plans` 表、`topic_plans` health capability、`upsert_topic_plan/list_topic_plans/get_topic_plan/update_topic_plan_status` MCP tools。
- agents 仓库的 `account-bound-topic-planning` 已完成 dry-run 与 batch planning；生产 `--write`、`plans list` 和端到端验收被 hermes-db `topic_plans` 契约阻塞。
- 运行边界已调整：选题规划不要求作为独立部署的 `hotspot-agent` 长期存在。hermes-db 契约应面向任意 `topic-planning runtime`，包括 Hermes cron 加载 skill/subagent、Codex/Claude Code 手动触发、或轻量 CLI job。

---

## Feature Traits *(LM 自动检测，用户可 override)*

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | `topic-planning runtime` 生成 `TopicPlan`，hermes-db 持久化，后续写作 agent 消费 plan。 |
| `external-side-effects` | ✅ | 新增 PostgreSQL 表、MCP 写工具，并在 write 模式中更新 candidate 状态。 |
| `artifact-handoff` | ✅ | `topic_plans` 中的 outline/writing/image brief 是跨 agent handoff artifact。 |
| `user-visible-output` | ✅ | `plans list` 和后续写作链路会向用户/运营者展示可写作 plan。 |
| `prior-closure-failure` | ✅ | agents 侧 dry-run 已完成，但生产 write 因 hermes-db capability 缺失无法闭环。 |
| `bugfix-loop-breaker` | ❌ | 这是新增契约能力，不是现有 bugfix 或 regression 修复。 |

**结论**: 下游 plan/tasks/verify/closeout 需要启用 Producer-Consumer Matrix、Evidence Gate、Workflow Replay 和三维 Verdict；不启用 bugfix-loop-breaker 专项。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 持久化账号绑定选题规划 (Priority: P1)

作为 `topic-planning runtime`，我希望把 dry-run 已校验通过的 `TopicPlan` 写入 hermes-db 的正式表，而不是塞进 candidate raw payload 或临时 artifact，以便后续写作 agent 能稳定读取同一份选题规划。

**Why this priority**: 规划运行层的 write 主链路被该契约直接阻塞；没有持久化表就无法进入真实生产。

**Acceptance Scenarios**:

1. **[US1-1] planned plan 可幂等 upsert**  
   **Given** 一个存在的 `topic_candidates` 记录，状态为 `new` 或 `shortlisted`  
   **When** 调用 `upsert_topic_plan` 写入 `status=planned`、3-5 个 `topic_angles`、`recommended_angle_index`、`outline_pack`、`writing_brief`、`image_brief`、`evidence` 和 `llm_metadata`  
   **Then** hermes-db 创建或更新同一 candidate 的 `topic_plans` 记录，返回 `plan_id`、`candidate_id`、`status=planned`、`upserted=created|updated`、`created_at`、`updated_at`

2. **[US1-2] planned 写入可同步 shortlist candidate**  
   **Given** `upsert_topic_plan` 输入包含 `mark_candidate_shortlisted=true` 且 plan 状态为 `planned`  
   **When** upsert 成功  
   **Then** hermes-db 在同一事务中把 candidate 状态推进为 `shortlisted`，返回 `candidate_status=shortlisted`

3. **[US1-3] rejected plan 可记录但默认不 reject candidate**  
   **Given** AI shortlist 判定候选不适合写作  
   **When** 调用 `upsert_topic_plan` 写入 `status=rejected`、空 `topic_angles`、空 handoff 包和 `rejection_reason`  
   **Then** hermes-db 保存 rejected plan，但不自动把 candidate 状态改为 `rejected`

**Edge Cases**:

- **[US1-4] handoff 包缺失**: `status=planned` 时缺少 `outline_pack`、`writing_brief` 或 `image_brief` 必须返回 validation error，不得写入半成品。
- **[US1-5] 推荐角度越界**: `recommended_angle_index` 必须是整数，且落在 `topic_angles` 范围内。
- **[US1-6] candidate 不存在**: 必须返回结构化 not-found/validation 错误，不得创建孤儿 plan。
- **[US1-7] 并发 upsert**: 同一 `candidate_id` 并发写入只能留下一个 active plan；结果必须可重试、幂等。

### User Story 2 - 读取可消费的 TopicPlan (Priority: P1)

作为后续写作 agent 或人工运营者，我希望能按 account、track、status 查询可写作 plan，并读取完整 handoff 包，以便进入正文生成或人工审阅。

**Why this priority**: 本机 Codex/Claude Code、NAS Hermes 运行层和后续写作链路都依赖 `list_topic_plans/get_topic_plan` 消费同一份落库 plan。

**Acceptance Scenarios**:

1. **[US2-1] 按账号列出 planned plans**  
   **Given** `after-work` 下存在多个 `topic_plans`  
   **When** 调用 `list_topic_plans(account_id="after-work", status="planned", limit=20)`  
   **Then** 返回按 `created_at desc` 排序的 items、`total`、`limit`、`offset`

2. **[US2-2] 按 track/status 过滤**  
   **Given** 同一账号下存在多个 track 和多个 plan status  
   **When** 调用 `list_topic_plans(account_id, track_id, status)`  
   **Then** 只返回匹配过滤条件的 plan，且每个 planned item 包含完整 `topic_angles`、`outline_pack`、`writing_brief`、`image_brief`

3. **[US2-3] 获取单个 plan**  
   **Given** 已知 `plan_id`  
   **When** 调用 `get_topic_plan(plan_id)`  
   **Then** 返回完整 `TopicPlan` DTO；不存在时返回结构化 not-found 错误

**Edge Cases**:

- **[US2-4] pagination**: `limit` 必须有安全上限，非法 `limit/offset` 返回 validation error。
- **[US2-5] schema drift**: DB 中 planned plan 若缺必需 handoff 字段，tool 必须 fail closed 或返回明确 schema error，不能静默裁剪字段。

### User Story 3 - 更新 plan 生命周期 (Priority: P2)

作为写作链路，我希望在 plan 被消费后标记状态并关联正式 topic，以便避免重复写作并保留 lineage。

**Why this priority**: `TopicPlan` 是 candidate 和正式 topic 之间的新 handoff 节点，需要可追溯生命周期。

**Acceptance Scenarios**:

1. **[US3-1] planned 转 consumed**  
   **Given** 一个 `status=planned` 的 plan  
   **When** 调用 `update_topic_plan_status(plan_id, status="consumed", topic_id=<topic_id>)`  
   **Then** plan 状态变为 `consumed`，写入 `topic_id` 和 `consumed_at`

2. **[US3-2] planned/rejected 可 archived**  
   **Given** 一个不再使用的 plan  
   **When** 调用 `update_topic_plan_status(plan_id, status="archived")`  
   **Then** plan 状态变为 `archived`，保留历史内容和关联 candidate

**Edge Cases**:

- **[US3-3] 非法状态转换**: 只允许 `planned -> consumed|archived`、`rejected -> archived`、`consumed -> archived`。
- **[US3-4] consumed 缺 topic_id**: 第一版应要求 `consumed` 必须提供 `topic_id`，否则返回 validation error。

### User Story 4 - 扩展 candidate raw 读取以支持 planning context (Priority: P1)

作为 `topic-planning runtime`，我希望 hermes-db 能按 candidate id 返回完整候选内容和可选 raw payload，以便 planning prompt 能包含 matched keywords、source evidence 和上游原始字段。

**Why this priority**: PlanningContextBuilder 需要 `get_topic_candidate(include_raw=true)`，当前 contract 必须在 hermes-db 侧提供；该 builder 可以位于 Hermes skill/subagent、Codex/Claude Code 辅助脚本或轻量 CLI 中。

**Acceptance Scenarios**:

1. **[US4-1] 单条 candidate 读取**  
   **Given** 已知 `candidate_id`  
   **When** 调用 `get_topic_candidate(candidate_id, include_raw=false)`  
   **Then** 返回 candidate 基础字段，不包含 raw payload 或只包含空 raw payload

2. **[US4-2] raw payload 可选返回**  
   **Given** candidate 存在 `raw_payload`  
   **When** 调用 `get_topic_candidate(candidate_id, include_raw=true)`  
   **Then** 返回 `raw_payload`，包括 matchedKeywords 等 planning 可用证据

**Edge Cases**:

- **[US4-3] missing candidate**: 不存在的 candidate 返回 not-found，不返回空对象。
- **[US4-4] raw JSON 解码**: JSON/JSONB 字段必须返回对象，不返回字符串化 JSON。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: hermes-db 必须新增正式存储实体 `hermes.topic_plans`，不得复用 `topic_candidates.raw_payload` 或 workflow artifact 作为 plan 主存储。
- **FR-002**: `topic_plans` 必须通过 `candidate_id` 唯一关联 `topic_candidates`；MVP 默认一个 candidate 一个 active plan。
- **FR-003**: `topic_plans.status` 必须支持 `planned`、`rejected`、`consumed`、`archived`。
- **FR-004**: planned plan 必须持久化 `recommended_angle_index`、3-5 个 `topic_angles`、`outline_pack`、`writing_brief`、`image_brief`、`evidence`、`llm_metadata`。
- **FR-005**: rejected plan 必须允许 `topic_angles=[]`、handoff 包为空，并必须保存 `rejection_reason`。
- **FR-006**: `upsert_topic_plan` 必须是幂等写工具，按 `candidate_id` 创建或更新 plan，并返回 `upserted=created|updated`。
- **FR-007**: `upsert_topic_plan` 必须支持 `mark_candidate_shortlisted=true`；仅当 plan `status=planned` 时，才能在同一事务中把 candidate 推进为 `shortlisted`。
- **FR-008**: `upsert_topic_plan` 不得在 `status=rejected` 时自动 reject candidate；确定性 reject 仍应由既有 `reject_topic_candidate` 工具处理。
- **FR-009**: hermes-db 必须新增 `list_topic_plans`，支持 `account_id`、`track_id`、`status`、`limit`、`offset` 过滤。
- **FR-010**: hermes-db 必须新增 `get_topic_plan(plan_id)`，返回完整 `TopicPlan` DTO。
- **FR-011**: hermes-db 必须新增 `update_topic_plan_status(plan_id, status, topic_id?)`，支持 plan 生命周期推进并返回 `previous_status`、`status`、`topic_id`。
- **FR-012**: hermes-db 必须新增或补齐 `get_topic_candidate(candidate_id, include_raw)`，支持 `include_raw=true` 返回 `raw_payload`。
- **FR-013**: `health` capability 必须新增 `topic_plans`，只有表、约束、索引和 MCP contract 所需字段完整时才返回 `true`。
- **FR-014**: 所有新增 MCP tools 必须遵循现有 envelope/error 风格，返回结构化 validation/not-found/schema 错误，不抛出未包装异常。
- **FR-015**: schema migration 必须纳入 hermes-db 现有迁移体系，并有可重复执行的 migration SQL 测试。

### MCP Tool Contract

```text
upsert_topic_plan(input) -> TopicPlanUpsertResult
list_topic_plans(filters) -> ListTopicPlansResult
get_topic_plan(plan_id) -> TopicPlan
update_topic_plan_status(plan_id, status, topic_id?) -> TopicPlanStatusResult
get_topic_candidate(candidate_id, include_raw?) -> TopicCandidateWithRaw
health() -> capabilities.topic_plans
```

### DTO Requirements

```ts
type TopicPlanStatus = "planned" | "rejected" | "consumed" | "archived";

interface UpsertTopicPlanInput {
  candidate_id: string;
  account_id: string;
  track_id: string;
  source: string;
  status: "planned" | "rejected";
  recommended_angle_index?: number | null;
  topic_angles: TopicAngle[];
  outline_pack?: OutlinePack | null;
  writing_brief?: WritingBrief | null;
  image_brief?: ImageBrief | null;
  rejection_reason?: string | null;
  evidence: Record<string, unknown>;
  llm_metadata: Record<string, unknown>;
  mark_candidate_shortlisted?: boolean;
}

interface TopicPlanUpsertResult {
  plan_id: string;
  candidate_id: string;
  status: "planned" | "rejected";
  candidate_status?: "new" | "shortlisted" | "adopted" | "rejected" | "expired";
  created_at: string;
  updated_at: string;
  upserted: "created" | "updated";
  warnings?: string[];
}

interface ListTopicPlansInput {
  account_id?: string;
  track_id?: string;
  status?: TopicPlanStatus;
  limit?: number;
  offset?: number;
}

interface TopicPlanStatusResult {
  plan_id: string;
  previous_status: TopicPlanStatus;
  status: TopicPlanStatus;
  topic_id?: string | null;
}
```

### Non-Functional Requirements

- **NFR-001**: 原子性。`upsert_topic_plan` 与 candidate `shortlisted` 更新必须在同一 DB transaction 中完成，避免 plan 写入成功但 candidate 状态未更新。
- **NFR-002**: 幂等性。同一 `candidate_id` 重复 upsert 不得生成重复 active plan。
- **NFR-003**: 可恢复。validation/schema/LLM 输出错误不应产生任何 DB side effect。
- **NFR-004**: 可观测。`health.capabilities.topic_plans` 必须能被 agents 用作 write gate。
- **NFR-005**: 兼容性。不得破坏现有 `topic_candidates` upsert/list/adopt/reject/shortlist/expire 和 track sync tools。
- **NFR-006**: 查询性能。`list_topic_plans` 应有 account/status/created、account/track/status/created 的索引支撑。
- **NFR-007**: 数据可追溯。plan 必须保留 `candidate_id`、`source`、`topic_id`、`evidence`、`llm_metadata` 和 timestamps。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 一致性 | planned 写入和 candidate shortlist 原子提交 | agents write path 不应出现半成功 | repository transaction 测试 | 是 |
| 幂等性 | 同一 candidate 多次 upsert 只有一个 plan | batch retry 和 CLI retry 会重复调用 | unique constraint + upsert 测试 | 是 |
| 可用性 | capability 缺失时 agents fail closed | 避免运行时才发现生产契约未部署 | health schema 测试 | 是 |
| 可演进性 | DTO 字段清晰，JSONB 承载 outline/brief | 后续写作 agent 会消费这些包 | schema + tool contract tests | 是 |
| 性能 | account/status 查询可控 | 运营列表和 agent 批处理需要低延迟 | EXPLAIN 或 repo SQL 断言 | 否 |

### Key Entities

- **TopicPlan**: candidate 面向某个公众号账号生成的选题规划。关键字段：`plan_id`、`candidate_id`、`account_id`、`track_id`、`status`、`topic_angles`、handoff 包、`evidence`、`llm_metadata`、`topic_id`、timestamps。
- **TopicAngle**: 账号绑定选题角度，至少包含 `title`、`angle`、`column_name`、`audience_fit`、`why_now`、`risk_notes`、`rationale`。
- **OutlinePack**: 给写作 agent 的推荐角度大纲，包含 hook、thesis、sections、examples、call_to_action、avoid。
- **WritingBrief**: 写作约束，包含 account_id、style_tags、target_audience、word_count_range、tone、source_constraints。
- **ImageBrief**: 配图约束，包含 visual_style、cover_prompt、inline_prompts、aspect ratios、avoid。
- **TopicCandidateWithRaw**: planning context 的 candidate 读取 DTO，支持 include_raw 可选返回原始 payload。

---

## Runtime Boundary

本 feature 只定义 hermes-db 的持久化与 MCP tool contract，不规定选题规划运行时必须是独立 agent。推荐运行形态：

```text
Hermes cron
  -> load wechat-topic-planning skill
  -> optional delegate_task for account-bound planning
  -> call hermes-db MCP get/list topic_candidates
  -> generate validated TopicPlan JSON
  -> call upsert_topic_plan(mark_candidate_shortlisted=true)
  -> topic_plans becomes the shared source for Codex / Claude Code / Hermes / future writers
```

运行层约束：

- Hermes cron 负责定时、投递和 profile/workdir 绑定；hermes-db 不感知 cron。
- Skill/subagent 负责账号上下文组装、LLM planning、schema validation 和成本控制。
- hermes-db 只通过 MCP tools 暴露 candidate/plan 读写，不接受运行层直连数据库。
- 本机 Codex/Claude Code 与 NAS Hermes 必须消费同一份 `topic_plans`，不能复制一份本地状态。
- 若保留 `hotspot-agent`，它应降级为可选薄 CLI/job，而不是必须独立部署的长期 agent。

## Producer-Consumer Matrix

| Producer | Artifact / State | Consumer | Contract |
|----------|------------------|----------|----------|
| Hermes cron + topic-planning skill/subagent / Codex / Claude Code / optional CLI | `upsert_topic_plan` input | hermes-db MCP | validated `TopicPlan` fields |
| hermes-db repository | `hermes.topic_plans` row | `list_topic_plans/get_topic_plan` | complete handoff package |
| hermes-db repository | candidate `status=shortlisted` | existing candidate workflows | existing candidate state machine |
| writing agent / operator | `update_topic_plan_status(consumed)` | hermes-db MCP | topic lineage via `topic_id` |
| health tool | `capabilities.topic_plans=true` | agents write gate | fail closed before production write |

---

## Out of Scope

- 不在 hermes-db 内执行 LLM planning、打分、改写标题或生成正文。
- 不在本 feature 中生成文章正文、图片、草稿箱内容或发布。
- 不新增 candidate status `planned`；规划成功继续复用现有 `shortlisted`。
- 不自动 reject AI 未入选候选；除非调用既有 deterministic reject 工具。
- 不实现多 plan 版本管理；MVP 使用 `candidate_id` unique。
- 不要求选题规划必须由独立部署的 `hotspot-agent` 实现；运行层可以是 Hermes cron + skill/subagent、Codex/Claude Code 手动触发，或轻量 CLI job。
- 不改动 agents 侧既有 prompt、parser 或 dry-run 行为；如后续收缩 `hotspot-agent` 边界，应在 agents/Hermes 运行层 feature 中处理。

---

## Unclear Questions

- 已解决：`plan_id` 使用 DB 生成 UUID；upsert 以 `candidate_id` 幂等。
- 已解决：MVP 不增加 soft delete，只使用 `archived` 生命周期状态。
- 已解决：新增单条 `get_topic_candidate(include_raw)` tool，默认仍隐藏 raw payload。
- 已解决：`topic_id` 使用 `UUID REFERENCES hermes.topics(id) ON DELETE SET NULL`。

---

## Stage Readiness

- 下一步建议：进入 `closeout` 或提交评审；`plan`、`tasks`、实现、verify evidence 和 acceptance 已完成。
- 阻塞项：无。
