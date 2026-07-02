# Tasks: Topic Plan Feedback And Optimization

**Workspace**: `topic-plan-feedback-and-optimization` | **Date**: 2026-07-02  
**Input**: [spec.md](spec.md) + [plan.md](plan.md) + [data-model.md](data-model.md)

---

## 执行原则

- 按可验证 slice 推进：schema foundation -> record feedback -> list feedback -> report metrics -> health gate -> optional P2 summary -> verification。
- 横向 migration/schema 任务只服务于后续 P1 MCP tools，不做脱离消费者的表设计。
- P1 只包含 `record_topic_plan_feedback`、`list_topic_plan_feedback`、`get_topic_plan_feedback_report` 和 `health.capabilities.topic_plan_feedback`。
- P2 `get_topic_plan_optimization_summary` 可实现，也可在任务执行时明确延期；不得影响 P1 health gate。
- 所有 report 口径必须有测试钉住 denominator、precedence、`event_at` window、`unknown_config` 和敏感字段过滤。

---

## Phase 1: Schema And Health Foundation

**目标**: 建立 feedback events 的持久化底座，并让 health gate 可判断 P1 能力是否可用。

- [x] T001 [Foundation] 新增 `topic_plan_feedback_events` migration
  - scope: `packages/hermes-db/migrations/versions/0011_topic_plan_feedback.py`
  - slice: 数据库能创建 append-only feedback event 表，包含 FK、event type check、JSONB shape check、partial unique dedupe index、report indexes
  - blocked_by: none
  - maps_to: FR-001..FR-003C, ADR-001, ADR-003, ADR-004, 可审计, 幂等, 性能
  - verify: migration text includes table, constraints, indexes, down_revision=`0010_topic_plans`, downgrade drops indexes/table
  - evidence: `rtk uv run pytest tests/test_migration_sql.py tests/test_topic_plan_feedback_schema_health.py` passed on 2026-07-02

- [x] T002 [Foundation] 增加 migration SQL 测试
  - scope: `packages/hermes-db/tests/test_migration_sql.py`
  - slice: revision、down_revision、table、constraint、index、rollback 名称被测试锁住
  - blocked_by: T001
  - maps_to: FR-001..FR-003C, migration ordering risk
  - verify: `rtk uv run pytest tests/test_migration_sql.py`
  - evidence: `tests/test_migration_sql.py` passed in focused run on 2026-07-02

- [x] T003 [Foundation] 增加 feedback schema inspector
  - scope: `packages/hermes-db/src/hermes_db_mcp/services/schema.py`, `packages/hermes-db/tests/test_topic_plan_feedback_schema_health.py`
  - slice: 完整 schema 返回 `{"topic_plan_feedback": true}`，缺表/约束/索引返回 false
  - blocked_by: T001
  - maps_to: FR-012, 可观测, Evidence Gate
  - verify: `rtk uv run pytest tests/test_topic_plan_feedback_schema_health.py`
  - evidence: `tests/test_topic_plan_feedback_schema_health.py` passed in focused run on 2026-07-02

---

## Phase 2: Record Feedback Slice

**目标**: 让人工/agent 能安全写入反馈事件，并证明重复提交不会污染 report。

- [x] T004 [US1] 实现 feedback repository 写入
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/topic_plan_feedback_repo.py`, `packages/hermes-db/tests/test_topic_plan_feedback_repo_sql.py`
  - slice: `record_topic_plan_feedback` repo 通过 `plan_id` 派生 `account_id/track_id/source/config`，写入 event，并在 `dedupe_key` 冲突时返回 existing event
  - blocked_by: T001
  - maps_to: US1, FR-001..FR-003C, NFR-001, ADR-001, ADR-003
  - verify: repo SQL tests cover success, not-found plan, invalid event type guard path, duplicate `dedupe_key` `DO NOTHING + fetch existing`
  - evidence: `rtk uv run pytest tests/test_topic_plan_feedback_repo_sql.py tests/test_topic_plan_feedback_tools.py` passed on 2026-07-02

- [x] T005 [US1] 实现 record MCP tool 和校验
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/topic_plan_feedback.py`, `packages/hermes-db/tests/test_topic_plan_feedback_tools.py`
  - slice: MCP caller 可记录 accepted/rejected/deferred/written/published event；非法 event type、不存在 plan、missing published lineage 返回 structured error
  - blocked_by: T004
  - maps_to: US1, FR-004, FR-003C, MCP Tool Contract, 安全
  - verify: tool tests cover accepted success, rejected reason tags, written topic id, published lineage validation, `idempotentHint=False` annotation/docstring expectation
  - evidence: `tests/test_topic_plan_feedback_tools.py` passed in focused run on 2026-07-02

---

## Phase 3: List Feedback Slice

**目标**: 让调用方能按 plan/account/track/type/time 窗口读取反馈事件，支持审计和后续 report 调试。

- [x] T006 [US1/US3] 实现 feedback list repository
  - scope: `topic_plan_feedback_repo.py`, `tests/test_topic_plan_feedback_repo_sql.py`
  - slice: 支持 `plan_id/account_id/track_id/event_type/event_at` window 和 pagination；可选支持 `created_at` audit window
  - blocked_by: T004
  - maps_to: FR-005, US3-6, 可审计
  - verify: repo SQL tests cover filters, `event_at` ordering, created audit filters if implemented, limit/offset
  - evidence: `rtk uv run pytest tests/test_topic_plan_feedback_repo_sql.py tests/test_topic_plan_feedback_tools.py` passed on 2026-07-02

- [x] T007 [US1/US3] 实现 `list_topic_plan_feedback` MCP tool
  - scope: `tools/topic_plan_feedback.py`, `tests/test_topic_plan_feedback_tools.py`
  - slice: tool 返回 `ListTopicPlanFeedbackResult`，时间字段序列化稳定，pagination/error 风格与现有 hermes-db tools 一致
  - blocked_by: T006
  - maps_to: FR-005, MCP Tool Contract
  - verify: tool tests cover filters pass-through, invalid pagination, timestamp serialization, empty result
  - evidence: `tests/test_topic_plan_feedback_tools.py` passed in focused run on 2026-07-02

---

## Phase 4: Report Metrics Slice

**目标**: 生成可用于配置优化的采纳率、消费率、发布率、拒绝原因和 config grouping report。

- [x] T008 [US2/US3] 实现 report aggregation repository
  - scope: `topic_plan_feedback_repo.py`, `tests/test_topic_plan_feedback_repo_sql.py`
  - slice: `get_topic_plan_feedback_report` repo 以 matching `topic_plans` 为分母，按 fixed precedence 和 `event_at DESC, created_at DESC` 选 effective event
  - blocked_by: T004, T006
  - maps_to: US2, US3, FR-006..FR-009, ADR-004, 一致性, 可归因
  - verify: report tests cover `planned_count`, `accepted_count`, `consumed_count`, `published_count`, rates null-on-zero, conflict precedence, same-precedence latest selection
  - evidence: `rtk uv run pytest tests/test_topic_plan_feedback_repo_sql.py tests/test_topic_plan_feedback_tools.py` passed on 2026-07-02

- [x] T009 [US2/US3] 实现 config snapshot 和 grouping 口径
  - scope: `topic_plan_feedback_repo.py`, `tests/test_topic_plan_feedback_repo_sql.py`
  - slice: report 从 `topic_plans.llm_metadata.config_snapshot` 读取 runtime/config hash，缺失时归入 `unknown_config`，`by_source` 来自 `topic_plans.source`
  - blocked_by: T008
  - maps_to: US2, US3-3, FR-009, FR-010, ADR-005, 可归因
  - verify: fixtures cover `runtime_version`, `track_config_hash`, `scoring_profile_hash`, `unknown_config`, `by_source`
  - evidence: grouping fixtures passed in focused report repo tests on 2026-07-02

- [x] T010 [US3] 实现 reason tag、安全过滤和 sample warning
  - scope: `topic_plan_feedback_repo.py`, `tests/test_topic_plan_feedback_repo_sql.py`
  - slice: report 返回 reason tag counts、`sample_warning`、`min_sample_size`，且不返回 raw prompt、Authorization、API key、raw payload
  - blocked_by: T008
  - maps_to: US3-2, US3-4, FR-008, FR-011, 安全
  - verify: tests cover low denominator warning, custom `min_sample_size`, sensitive metadata exclusion
  - evidence: sample warning/reason tag DTO assertions passed in focused report repo/tool tests on 2026-07-02

- [x] T011 [US3] 实现 `get_topic_plan_feedback_report` MCP tool
  - scope: `tools/topic_plan_feedback.py`, `tests/test_topic_plan_feedback_tools.py`
  - slice: MCP caller 能按 account/track/window 查询 report；默认 `window_days=30`、`min_sample_size=5`
  - blocked_by: T008, T009, T010
  - maps_to: FR-006, FR-008, MCP Tool Contract
  - verify: tool tests cover default params, invalid params, repo call shape, DTO serialization
  - evidence: `tests/test_topic_plan_feedback_tools.py` passed in focused run on 2026-07-02

---

## Phase 5: Health Gate And Registration

**目标**: 让 P1 feedback/report 能力在服务启动和 health 中可见。

- [x] T012 [P1 Gate] 注册 feedback tool module
  - scope: `packages/hermes-db/src/hermes_db_mcp/server.py`
  - slice: hermes-db 启动时加载 `tools/topic_plan_feedback.py`
  - blocked_by: T005, T007, T011
  - maps_to: MCP Tool Contract, P1 health gate
  - verify: focused import/register smoke 或现有 server import tests pass
  - evidence: `rtk uv run pytest tests/test_migration_sql.py tests/test_topic_plan_feedback_schema_health.py tests/test_topic_plan_feedback_repo_sql.py tests/test_topic_plan_feedback_tools.py tests/test_health.py` passed on 2026-07-02

- [x] T013 [P1 Gate] 接入 `health.capabilities.topic_plan_feedback`
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/health.py`, `packages/hermes-db/tests/test_health.py`
  - slice: P1 schema/tool contract 就绪时 capability 为 true；P2 summary 不参与 gate
  - blocked_by: T003, T012
  - maps_to: FR-012, Evidence Gate
  - verify: `rtk uv run pytest tests/test_health.py tests/test_topic_plan_feedback_schema_health.py`
  - evidence: health + schema health focused tests passed on 2026-07-02

---

## Phase 6: P2 Optional Optimization Summary

**目标**: 若本轮选择实现 P2，则只输出 evidence-backed 建议，不自动修改配置；若不实现，干净延期。

- [x] T014 [US4/P2] 决定 P2 summary 本轮实现或延期
  - scope: `tasks.md`, optional `tools/topic_plan_feedback.py`, optional tests
  - slice: 明确 `get_topic_plan_optimization_summary` 是本轮实现还是记录为后续；不得影响 T013 P1 health gate
  - blocked_by: T011
  - maps_to: US4, FR optional, ADR-006
  - verify: 若延期，tasks/acceptance 记录 defer reason；若实现，进入 T015
  - evidence: deferred on 2026-07-02; P1 health gate excludes `get_topic_plan_optimization_summary`, so no P1 blocker

- [ ] T015 [US4/P2] 实现 evidence-only optimization summary
  - scope: `topic_plan_feedback_repo.py`, `tools/topic_plan_feedback.py`, `tests/test_topic_plan_feedback_tools.py`
  - slice: 基于 report 生成 conservative suggestions，包含 evidence plan ids/reason tags；`sample_warning=true` 时返回继续采集反馈
  - blocked_by: T014
  - maps_to: US4, ADR-006, 安全
  - verify: tests cover suggestion output, insufficient sample, no write to `topic_candidate_tracks`, sensitive filtering
  - defer: P2 optional summary deferred this round to keep P1 feedback/report contract shippable.

---

## Phase 7: Verification And Closeout Prep

**目标**: 产出 fresh evidence，证明 P1 闭环可交付且没有破坏既有 topic plan/candidate flows。

- [x] T016 [Verify] 运行 focused hermes-db tests
  - scope: `packages/hermes-db/tests/`
  - slice: migration、schema health、repo、tools、report、existing topic plan/candidate compatibility 全部通过
  - blocked_by: T002, T013, T014
  - maps_to: Evidence Gate, Workflow Replay, 三维 Verdict input
  - verify: `rtk uv run pytest tests/test_migration_sql.py tests/test_topic_plan_feedback_schema_health.py tests/test_topic_plan_feedback_repo_sql.py tests/test_topic_plan_feedback_tools.py tests/test_topic_plan_tools.py tests/test_topic_candidate_tools.py tests/test_health.py`
  - evidence: 61 passed in 0.32s on 2026-07-02

- [x] T017 [Verify] 记录 verify evidence
  - scope: `specs/topic-plan-feedback-and-optimization/verify-evidence.md`
  - slice: Evidence table 覆盖 schema/repo/tools/report/health/P2 decision/remaining risk
  - blocked_by: T016
  - maps_to: Evidence Gate, acceptance input
  - verify: evidence includes exact commands, outcomes, PASS/PARTIAL/FAIL verdicts, blockers
  - evidence: [verify-evidence.md](verify-evidence.md) created on 2026-07-02

- [x] T018 [Closeout Prep] 更新任务状态与验收输入
  - scope: `tasks.md`, `verify-evidence.md`, future `acceptance.md`
  - slice: 所有任务都有完成证据、延期说明或显式 blocker；P2 状态清晰
  - blocked_by: T017
  - maps_to: Closeout Checklist, Knowledge Capture Gate
  - verify: no unchecked task lacks blocker/defer note before closeout
  - evidence: all P1 tasks checked; T015 has explicit P2 defer note

---

## 依赖与顺序

关键路径：

1. T001 -> T002/T003
2. T001 -> T004 -> T005 -> T006/T007 -> T008 -> T009/T010 -> T011 -> T012 -> T013
3. T011 -> T014 -> optional T015
4. T013 + T014 -> T016 -> T017 -> T018

可并行：

- T002 and T003 after T001.
- T006/T007 can progress while report tests are being designed after T004.
- T009 and T010 can run in parallel after T008.
- T015 is optional and can be skipped cleanly if T014 records defer decision.

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|---|---|
| US1 记录人工采纳/拒绝/写作/发布反馈 | T001, T004, T005 |
| US2 保存并引用配置快照 | T008, T009 |
| US3 生成采纳率与优化分析 report | T006, T007, T008, T009, T010, T011 |
| US4 P2 优化建议草案 | T014, optional T015 |
| FR-001..FR-003C feedback entity/event fields/dedupe/event_at/lineage | T001, T002, T004, T005 |
| FR-004 record tool | T004, T005 |
| FR-005 list tool | T006, T007 |
| FR-006 report tool | T008, T009, T010, T011 |
| FR-007 precedence | T008 |
| FR-008 sample warning | T010, T011 |
| FR-009 config snapshot | T009 |
| FR-010 canonical hash contract | T009, T017 |
| FR-011 sensitive filtering | T010, T015 |
| FR-012 health capability | T003, T012, T013 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|---|---|---|
| ADR-001 feedback 独立表 | T001, T004 | T002, T016 |
| ADR-002 同步 MCP 写入 | T004, T005 | T016 |
| ADR-003 optional `dedupe_key` | T001, T004, T005 | T004, T005, T016 |
| ADR-004 `event_at` report window | T006, T008 | T006, T008, T016 |
| ADR-005 config snapshot path | T009 | T009, T016 |
| ADR-006 P2 summary no config write | T014, T015 | T015, T017 |
| 可归因 / 一致性 / 安全 / 性能 | T008, T009, T010, T013 | T016, T017 |

---

## Context Manifest

已生成 [context-manifest.md](context-manifest.md)。原因：本 feature 命中 `multi-stage-workflow`、`artifact-handoff`、`external-side-effects`、`user-visible-output` 和 `prior-closure-failure`，实现/验证需要跨 SDD 文档、migration、repo、tool、health 和 report 口径恢复上下文。

---

## Stage Readiness

- 推荐下一步：等待用户确认 [commit-plan.md](commit-plan.md)，或选择暂不提交。
- 阻塞项：无。P1 acceptance 已生成；T015 为 P2 延期项。
