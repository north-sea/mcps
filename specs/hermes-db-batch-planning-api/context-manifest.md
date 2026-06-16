# Context Manifest: hermes-db-batch-planning-api

**Workspace**: `hermes-db-batch-planning-api`
**Created**: 2026-06-16
**Status**: active

> 本文件用于记录 SDD 各阶段必须读取的高信号上下文。它不是待修改源文件清单，也不替代实现阶段按需阅读代码。

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/hermes-db-batch-planning-api/spec.md` | 理解需求边界、用户场景、验收标准、数据库 schema 定义 | implement | yes |
| `specs/hermes-db-batch-planning-api/plan.md` | 遵守架构决策（ADR-002/003/004）、模块设计、错误码约定 | implement | yes |
| `specs/hermes-db-batch-planning-api/tasks.md` | 任务边界、验证点、依赖顺序 | implement | yes |
| `packages/hermes-db/src/hermes_db_mcp/repositories/novel_repo.py:71-108` | 参考现有 batch_upsert_chapters 的事务管理模式（loop inside transaction） | implement | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/novel_chapters.py:18-84` | 参考现有 MCP tool 的参数校验和错误处理模式 | implement | yes |
| `packages/hermes-db/src/hermes_db_mcp/contracts.py:271-297` | 复用 ERROR_CODES 字典和 error() 函数 | implement | yes |
| `packages/hermes-db/migrations/versions/0007_novel_agent_books_chapters.py` | 参考现有 migration 的命名约定和表结构定义 | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/hermes-db-batch-planning-api/spec.md` | 验证 P0 需求（US1/US2/US3）和验收场景是否实现 | verify | yes |
| `specs/hermes-db-batch-planning-api/plan.md` | 检查架构漂移（是否违反 ADR-002/003/004）、风险缓解是否落地 | verify | yes |
| `specs/hermes-db-batch-planning-api/tasks.md` | 检查 19 个任务是否完成、覆盖检查表是否全部命中 | verify | yes |
| NFR-001/002 性能指标 | 验证 batch_create_book_planning <500ms, get_chapter_input_pack <200ms | verify | yes |
| `tests/test_novel_planning_repo.py` | 验证单元测试覆盖（事务、幂等性、join 查询、边界条件） | verify | yes |
| `tests/test_novel_planning_tools.py` | 验证 MCP tool 层参数校验和错误码返回 | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| https://magicstack.github.io/asyncpg/current/usage.html | asyncpg 事务管理语法（async with connection.transaction()） | plan / implement | yes |
| https://www.postgresql.org/docs/current/datatype-json.html | PostgreSQL JSONB 字段的插入和查询方式 | plan / implement | yes |
| https://modelcontextprotocol.io/docs/concepts/tools | MCP tool 定义规范（名称、描述、input schema） | plan / implement | yes |
| https://www.postgresql.org/docs/current/transaction-iso.html | PostgreSQL 事务隔离级别（READ COMMITTED 默认行为） | plan | yes |
| `packages/hermes-db/src/hermes_db_mcp/repositories/topic_repo.py:284-336` | 参考现有 batch_update_fields 的 WHERE id = ANY($idx) 模式 | implement | yes |

---

## Rules

- 每条 entry 必须有 `Reason`；缺少 reason 的 manifest 不得通过 verify。
- `Required = yes` 的本地文件不存在时，当前阶段必须回退到 `plan` 或 `tasks` 更新 manifest。
- 不要把即将修改的源文件列为固定 context；源文件由 implement / verify 按需检查。
- 不复制长文档；只记录路径、来源、用途和短摘要。
- 不引入 `.trellis/`、Trellis CLI、hook、task.py 或自动 context injection。
