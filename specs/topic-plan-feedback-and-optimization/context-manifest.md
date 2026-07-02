# Context Manifest: Topic Plan Feedback And Optimization

**Workspace**: `topic-plan-feedback-and-optimization`
**Created**: 2026-07-02
**Status**: active

> 本文件用于记录 SDD 各阶段必须读取的高信号上下文。它不是待修改源文件清单，也不替代实现阶段按需阅读代码。

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/topic-plan-feedback-and-optimization/spec.md` | Defines feedback/report requirements, P1/P2 boundary, event precedence, and health gate scope. | implement | yes |
| `specs/topic-plan-feedback-and-optimization/plan.md` | Defines module boundaries, ADRs, idempotency behavior, report aggregation strategy, and verification path. | implement | yes |
| `specs/topic-plan-feedback-and-optimization/data-model.md` | Defines feedback event table, indexes, DTOs, metric rules, and config snapshot path. | implement | yes |
| `specs/topic-plan-feedback-and-optimization/tasks.md` | Defines execution slices, dependencies, and verification commands. | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/topic-plan-feedback-and-optimization/spec.md` | Verify implementation covers US1-US4, FR-001..FR-012, and P2 optional boundary. | verify | yes |
| `specs/topic-plan-feedback-and-optimization/plan.md` | Check architecture drift, ADRs, quality attributes, and P1 health gate assumptions. | verify | yes |
| `specs/topic-plan-feedback-and-optimization/data-model.md` | Check migration/repo/tool/report outputs match documented schema, DTO, and metric rules. | verify | yes |
| `specs/topic-plan-feedback-and-optimization/tasks.md` | Check every task has evidence, defer note, or explicit blocker before closeout. | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `packages/hermes-db/src/hermes_db_mcp/repositories/topic_plan_repo.py` | Existing TopicPlan repository style and source/config metadata source for feedback report. | plan / implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/topic_plans.py` | Existing MCP tool validation, serialization, annotations, and structured error style. | plan / implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/services/schema.py` | Existing schema inspection pattern used by health capabilities. | plan / implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/health.py` | Existing health capability default map and schema merge point. | plan / implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/wechat_retrospective.py` | Existing report-style tool surface and DTO/error patterns for analytical MCP outputs. | implement / verify | no |
| `packages/hermes-db/src/hermes_db_mcp/repositories/wechat_retrospective_repo.py` | Existing aggregation/report SQL style for retrospective metrics and suggestions. | implement / verify | no |
| `packages/hermes-db/migrations/versions/0010_topic_plan_contracts.py` | Alembic predecessor and current `topic_plans` schema contract. | implement / verify | yes |
| `packages/hermes-db/tests/test_migration_sql.py` | Migration text assertion style and revision guard. | implement / verify | yes |
| `packages/hermes-db/tests/test_topic_plan_repo_sql.py` | Existing fake pool/connection SQL assertion style for TopicPlan repo. | implement / verify | yes |
| `packages/hermes-db/tests/test_topic_plan_tools.py` | Existing TopicPlan tool monkeypatch and envelope assertion style. | implement / verify | yes |
| `packages/hermes-db/tests/test_topic_plan_schema_health.py` | Existing schema health fixture style for TopicPlan capability. | implement / verify | yes |

---

## Rules

- 每条 entry 必须有 `Reason`；缺少 reason 的 manifest 不得通过 verify。
- `Required = yes` 的本地文件不存在时，当前阶段必须回退到 `plan` 或 `tasks` 更新 manifest。
- 不要把即将修改的源文件列为固定 context；源文件由 implement / verify 按需检查。
- 不复制长文档；只记录路径、来源、用途和短摘要。
- 不引入 `.trellis/`、Trellis CLI、hook、task.py 或自动 context injection。
