# Tasks: Hermes DB Topic Plan Contract

**Workspace**: `hermes-db-topic-plan-contract` | **Date**: 2026-07-01  
**Input**: [spec.md](spec.md) + [plan.md](plan.md) + [data-model.md](data-model.md)

---

## 执行原则

- 按可验证 slice 推进：migration/schema -> repository -> MCP tools -> health -> regression evidence。
- 横向 schema/repo 任务必须服务于后续 MCP contract，不做脱离消费者的表设计。
- 所有新增 contract 必须有测试钉住字段、状态和错误行为。
- 不改 agents 仓；agents 只作为后续 smoke consumer。

---

## Phase 1: Schema And Health Foundation

**目标**: 建立 `topic_plans` 的持久化底座和健康门禁。

- [x] T001 [US1/US2] 新增 `topic_plans` migration
  - scope: `packages/hermes-db/migrations/versions/0010_topic_plan_contracts.py`
  - slice: 数据库能创建 `hermes.topic_plans`，包含 FK、唯一约束、状态/shape check、listing indexes
  - blocked_by: none
  - maps_to: FR-001..FR-005, FR-015, ADR-001, ADR-002, 查询性能
  - verify: migration 文件包含 required table/constraints/indexes/down_revision；`tests/test_migration_sql.py` 有断言

- [x] T002 [US1/US2] 增加 migration SQL 测试
  - scope: `packages/hermes-db/tests/test_migration_sql.py`
  - slice: revision、down_revision、table、constraint、index 名称被文本测试锁住
  - blocked_by: T001
  - maps_to: FR-015, migration ordering risk
  - verify: `rtk uv run pytest tests/test_migration_sql.py`

- [x] T003 [US2] 增加 topic plan schema inspector
  - scope: `packages/hermes-db/src/hermes_db_mcp/services/schema.py`, `packages/hermes-db/tests/test_topic_plan_schema_health.py`
  - slice: 完整 schema 返回 `{"topic_plans": true}`，缺字段/约束/索引返回 false
  - blocked_by: T001
  - maps_to: FR-013, 可观测
  - verify: `rtk uv run pytest tests/test_topic_plan_schema_health.py`

- [x] T004 [US2] 接入 health capability
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/health.py`, `packages/hermes-db/tests/test_health.py`
  - slice: `/health` capability 增加 `topic_plans`，agents 可用作 write gate
  - blocked_by: T003
  - maps_to: FR-013, ADR-005
  - verify: `rtk uv run pytest tests/test_health.py`

---

## Phase 2: Repository Contract

**目标**: 让 Python repo 层完整覆盖 plan lifecycle 和 candidate raw context。

- [x] T005 [US1] 实现 `topic_plan_repo.upsert_topic_plan`
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/topic_plan_repo.py`, `packages/hermes-db/tests/test_topic_plan_repo_sql.py`
  - slice: planned/rejected payload 可创建；重复 candidate upsert 返回 updated 且不重复建 plan
  - blocked_by: T001
  - maps_to: FR-001..FR-008, NFR-001..NFR-003, ADR-001..ADR-004
  - verify: repo SQL tests cover created/updated, planned shape, rejected shape, invalid status no write

- [x] T006 [US1] 实现 plan upsert 与 candidate shortlist 同事务
  - scope: `topic_plan_repo.py`, `tests/test_topic_plan_repo_sql.py`
  - slice: `mark_candidate_shortlisted=true` 且 `status=planned` 时，在同一 transaction 更新 candidate `shortlisted`
  - blocked_by: T005
  - maps_to: FR-007, FR-008, NFR-001, ADR-004
  - verify: fake connection/transaction 测试证明 SQL 顺序和 rejected 不触发 candidate update

- [x] T007 [US2/US3] 实现 list/get/status repository 方法
  - scope: `topic_plan_repo.py`, `tests/test_topic_plan_repo_sql.py`
  - slice: 支持 account/track/status pagination；按 plan_id get；状态更新返回 `previous_status`、`status`、`topic_id`
  - blocked_by: T005
  - maps_to: FR-009..FR-011, NFR-006, NFR-007
  - verify: repo SQL tests cover filters, not found, status transitions, consumed topic_id/consumed_at

- [x] T008 [US4] 扩展 candidate raw read
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/topic_candidate_repo.py`, `packages/hermes-db/tests/test_topic_candidate_repo_sql.py`
  - slice: `get_candidate(..., include_raw=false)` 默认不返回 raw；`include_raw=true` 返回 `raw_payload`
  - blocked_by: none
  - maps_to: FR-012, 兼容性
  - verify: existing topic candidate repo/tool tests pass plus include_raw regression

---

## Phase 3: MCP Tool Surface

**目标**: 对 agents 暴露稳定、可验证的 TopicPlan MCP tools。

- [x] T009 [US1] 实现 `upsert_topic_plan` MCP tool
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/topic_plans.py`, `packages/hermes-db/tests/test_topic_plan_tools.py`
  - slice: planned/rejected payload validation、error envelope、repository call contract 完整
  - blocked_by: T005, T006
  - maps_to: FR-006..FR-008, FR-014
  - verify: tool tests cover success, validation error, rejected no auto candidate reject, shortlist guard

- [x] T010 [US2/US3] 实现 list/get/update TopicPlan tools
  - scope: `tools/topic_plans.py`, `tests/test_topic_plan_tools.py`
  - slice: tools 返回可消费 DTO，not-found/invalid-status 使用现有 error 风格
  - blocked_by: T007
  - maps_to: FR-009..FR-011, FR-014
  - verify: tool tests cover filters, get, lifecycle update, not-found

- [x] T011 [US4] 暴露或补齐 `get_topic_candidate(include_raw)`
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/topic_candidates.py`, `tests/test_topic_candidate_tools.py`
  - slice: MCP caller 可选择读取 raw payload，默认响应保持兼容
  - blocked_by: T008
  - maps_to: FR-012, NFR-005
  - verify: tool tests assert raw absent by default and present when requested

- [x] T012 [US1/US2] 注册 topic plan tool module
  - scope: `packages/hermes-db/src/hermes_db_mcp/server.py`
  - slice: hermes-db 启动时加载 `tools/topic_plans.py`
  - blocked_by: T009, T010
  - maps_to: MCP Tool Contract
  - verify: existing import/register tests or focused import smoke passes

---

## Phase 4: Verification And Closeout Prep

**目标**: 汇总 fresh evidence，证明新 contract 可交付且不破坏旧 topic candidate flows。

- [x] T013 [Verify] 运行 focused hermes-db test suite
  - scope: `packages/hermes-db/tests/`
  - slice: migration、schema health、repo、tools、candidate compatibility 全部通过
  - blocked_by: T002, T004, T009, T010, T011, T012
  - maps_to: Evidence Gate, Workflow Replay
  - verify: run focused pytest command from plan and record exact results

- [x] T014 [Verify] 生成 verify evidence
  - scope: `specs/hermes-db-topic-plan-contract/verify-evidence.md`
  - slice: Evidence table 覆盖 schema/repo/tools/health/compatibility/remaining risk
  - blocked_by: T013
  - maps_to: 三维 Verdict input
  - verify: evidence includes commands, outcomes, PASS/PARTIAL/FAIL verdicts, and blockers

- [x] T015 [Closeout Prep] 更新 SDD 状态与 acceptance 输入
  - scope: `tasks.md`, `verify-evidence.md`, future `acceptance.md`
  - slice: 所有任务状态、阻塞项、延后项、退役结论、提交结论可追踪
  - blocked_by: T014
  - maps_to: Closeout Checklist, Knowledge Capture
  - verify: no unchecked task lacks either completion evidence or explicit blocker

---

## 依赖与顺序

关键路径：

1. T001 -> T002/T003 -> T004
2. T001 -> T005 -> T006/T007 -> T009/T010 -> T012
3. T008 -> T011
4. T013 -> T014 -> T015

可并行：

- T002 and T003 after T001.
- T008 can run before topic plan repo is complete.
- T009 and T010 can be implemented in parallel once their repo methods exist.

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|-------------|----------|
| US1 持久化账号绑定选题规划 | T001, T005, T006, T009 |
| US2 读取可消费 TopicPlan | T003, T004, T007, T010 |
| US3 更新 plan 生命周期 | T007, T010 |
| US4 candidate raw planning context | T008, T011 |
| FR-001..FR-005 schema/entity/status/payload | T001, T002, T005 |
| FR-006..FR-008 upsert and candidate status semantics | T005, T006, T009 |
| FR-009..FR-011 list/get/update tools | T007, T010 |
| FR-012 get candidate include_raw | T008, T011 |
| FR-013 health capability | T003, T004 |
| FR-014 envelope/error style | T009, T010, T011 |
| FR-015 migration tests | T001, T002 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|----------------------|----------|----------|
| ADR-001 first-class storage | T001, T005 | T002, T013 |
| ADR-002 one plan per candidate | T001, T005 | T005, T013 |
| ADR-003 constrained lifecycle | T001, T007, T010 | T002, T010 |
| ADR-004 transaction for shortlist | T006, T009 | T006, T013 |
| ADR-005 schema-based health | T003, T004 | T004, T013 |
| 原子性 / 幂等性 / 兼容性 | T005, T006, T008, T011 | T013 |

---

## Context Manifest

已生成 [context-manifest.md](context-manifest.md)。原因：本 feature 命中 `multi-stage-workflow`、`artifact-handoff`、`database-schema` 和 `external-consumer-contract`，实现/验证需要跨 SDD 文档、migration、repo、tool、health 和测试恢复上下文。

---

## Stage Readiness

- 推荐下一步：提交评审 / release preflight
- 阻塞项：无。15/15 tasks 已完成，verify evidence 和 acceptance 已生成。
