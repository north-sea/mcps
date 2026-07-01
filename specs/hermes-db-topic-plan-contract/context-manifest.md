# Context Manifest: Hermes DB Topic Plan Contract

**Workspace**: `hermes-db-topic-plan-contract`
**Created**: 2026-07-01
**Status**: active

> 本文件用于记录 SDD 各阶段必须读取的高信号上下文。它不是待修改源文件清单，也不替代实现阶段按需阅读代码。

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/hermes-db-topic-plan-contract/spec.md` | Defines TopicPlan requirements, MCP tool contract, DTO fields, and out-of-scope boundaries. | implement | yes |
| `specs/hermes-db-topic-plan-contract/plan.md` | Defines module boundaries, ADRs, transaction semantics, and verification strategy. | implement | yes |
| `specs/hermes-db-topic-plan-contract/data-model.md` | Defines table columns, constraints, indexes, lifecycle states, and payload rules. | implement | yes |
| `specs/hermes-db-topic-plan-contract/tasks.md` | Defines execution slices, dependencies, and local verification commands. | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/hermes-db-topic-plan-contract/spec.md` | Verify implementation covers user stories, FR/NFR, Producer-Consumer Matrix, and runtime boundary. | verify | yes |
| `specs/hermes-db-topic-plan-contract/plan.md` | Check architecture drift, ADRs, quality attributes, and risk mitigations. | verify | yes |
| `specs/hermes-db-topic-plan-contract/data-model.md` | Check migration/repo/tool outputs match documented table and DTO rules. | verify | yes |
| `specs/hermes-db-topic-plan-contract/tasks.md` | Check every task has evidence or an explicit blocker before closeout. | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `packages/hermes-db/src/hermes_db_mcp/repositories/topic_candidate_repo.py` | Existing repository style for topic candidate upsert/list/status/raw payload behavior. | plan / implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/topic_candidates.py` | Existing MCP tool envelope and validation style for candidate lifecycle. | plan / implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/services/schema.py` | Existing schema inspection pattern used by health capabilities. | plan / implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/health.py` | Existing health capability merge point. | plan / implement / verify | yes |
| `packages/hermes-db/migrations/versions/0009_topic_candidate_contracts.py` | Current Alembic migration immediately before topic plan contract. | plan / implement / verify | yes |
| `packages/hermes-db/tests/test_migration_sql.py` | Existing migration text assertion style and revision id guard. | plan / implement / verify | yes |
| `packages/hermes-db/tests/test_topic_candidate_repo_sql.py` | Existing fake pool/connection SQL assertion style for topic candidate repo. | plan / implement / verify | yes |
| `packages/hermes-db/tests/test_topic_candidate_tools.py` | Existing tool monkeypatch and envelope assertion style. | plan / implement / verify | yes |
| `packages/hermes-db/tests/test_topic_candidate_schema_health.py` | Existing schema health fixture style for topic candidate capability. | plan / implement / verify | yes |

---

## Rules

- 每条 entry 必须有 `Reason`；缺少 reason 的 manifest 不得通过 verify。
- `Required = yes` 的本地文件不存在时，当前阶段必须回退到 `plan` 或 `tasks` 更新 manifest。
- 不要把即将修改的源文件列为固定 context；源文件由 implement / verify 按需检查。
- 不复制长文档；只记录路径、来源、用途和短摘要。
- 不引入 `.trellis/`、Trellis CLI、hook、task.py 或自动 context injection。
