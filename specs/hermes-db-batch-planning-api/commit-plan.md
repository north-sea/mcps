# Commit Plan: hermes-db-batch-planning-api

**Workspace**: `hermes-db-batch-planning-api`
**Date**: 2026-06-16
**Status**: Awaiting User Confirmation

> Commit plan 是提交前的用户确认 gate。未获得用户明确确认前，不得执行 `git add` 或 `git commit`。

---

## Summary

当前 feature 有 11 个相关文件待提交：
- 4 个修改文件（M）：README.md, contracts.py, server.py, specs/.active
- 7 个新增文件（??）：migration, repository, tools, tests, specs 文档

建议拆分为 5 个 batch：
1. Database Schema (migration)
2. Core Implementation (repository + tools)
3. Tests
4. Documentation (README + specs)
5. Workspace State (specs/.active)

**无无关 dirty files，无待用户决策文件。**

---

## Included Files

| File | Reason | Evidence |
|---|---|---|
| `packages/hermes-db/migrations/versions/0008_novel_planning_tables.py` | 本 feature 的 database schema（6 新表 + 2 字段扩展 + 9 索引） | T001-T003 (tasks.md) |
| `packages/hermes-db/src/hermes_db_mcp/repositories/novel_planning_repo.py` | 本 feature 的 repository 层（5 个数据访问方法） | T004-T006 (tasks.md) |
| `packages/hermes-db/src/hermes_db_mcp/tools/novel_planning.py` | 本 feature 的 MCP tools 层（4 个 MCP tools） | T007-T009 (tasks.md) |
| `packages/hermes-db/src/hermes_db_mcp/contracts.py` | 新增 4 个错误码（book_not_found, planning_already_exists, foreshadowing_limit_exceeded, transaction_failed） | T010 (tasks.md) |
| `packages/hermes-db/src/hermes_db_mcp/server.py` | 注册 novel_planning tools | T011 (tasks.md) |
| `packages/hermes-db/tests/test_novel_planning_repo.py` | Repository 层单元测试（7 个测试用例） | T012-T014 (tasks.md) |
| `packages/hermes-db/tests/test_novel_planning_tools.py` | MCP tools 层单元测试（7 个测试用例） | T015 (tasks.md) |
| `packages/hermes-db/tests/integration_test_guide.md` | 集成测试指南（8 步手动验证流程） | T017 (tasks.md) |
| `packages/hermes-db/README.md` | 新增 4 个 MCP tools 的工具列表描述 | T019 (tasks.md) |
| `specs/hermes-db-batch-planning-api/` | 完整 spec 文档（spec.md, plan.md, tasks.md, context-manifest.md, acceptance.md, cross-repo-coordination.md, commit-plan.md） | SDD 全流程产物 |
| `specs/.active` | 更新当前 active feature 为 hermes-db-batch-planning-api | SDD workspace 约定 |

**所有 11 个文件都直接属于本 feature，无模糊归属。**

---

## Excluded Files

无。所有 dirty files 均属于本 feature。

---

## Needs User Decision

无。所有文件归属明确。

---

## Risks

| Risk | Impact | Handling |
|---|---|---|
| Migration 未执行 | 提交后仍需手动执行 `alembic upgrade head` | 已在集成测试指南和 acceptance.md 中标注为延后项 |
| specs/.active 变更 | 覆盖前一个 feature (hermes-db-agent-self-evolution-foundation) 的 active 状态 | 符合 SDD 约定，新 feature 应更新 .active |
| 跨仓库接口不兼容 | agents 仓库未同步 bookId→bookSlug 变更会导致调用失败 | 已记录在 cross-repo-coordination.md，标注为延后项 |

---

## Commit Batches

| Batch | Files | Commit Message | Rationale |
|---|---|---|---|
| 1 | `migrations/versions/0008_novel_planning_tables.py` | `feat(hermes-db): add novel planning tables migration`<br><br>新增 6 个规划表 (worldbuilding, characters, foreshadowing, volume_outlines, human_reviews, context_change_log)，扩展 books 和 chapters 表支持上下文版本追踪，创建 9 个性能优化索引。<br><br>Refs: hermes-db-batch-planning-api T001-T003 | Database schema 独立，后续实现依赖它 |
| 2 | `src/hermes_db_mcp/repositories/novel_planning_repo.py`<br>`src/hermes_db_mcp/tools/novel_planning.py`<br>`src/hermes_db_mcp/contracts.py`<br>`src/hermes_db_mcp/server.py` | `feat(hermes-db): implement batch planning API`<br><br>实现 4 个 MCP tools：<br>- batch_create_book_planning（4 表事务性写入）<br>- get_chapter_input_pack（批量读取章纲输入）<br>- update_context_version（版本追踪）<br>- get_current_context_version（版本读取）<br><br>新增 4 个错误码：book_not_found, planning_already_exists, foreshadowing_limit_exceeded, transaction_failed。<br><br>Refs: hermes-db-batch-planning-api T004-T011 | 核心实现文件，功能内聚 |
| 3 | `tests/test_novel_planning_repo.py`<br>`tests/test_novel_planning_tools.py` | `test(hermes-db): add novel planning tests`<br><br>新增 14 个单元测试覆盖：<br>- 事务原子性和回滚<br>- 双重幂等性检查<br>- 完整输入包读取<br>- 冷启动处理<br>- 参数校验和错误码转换<br><br>测试通过率：14/14 (100%)<br><br>Refs: hermes-db-batch-planning-api T012-T015 | 测试独立批次，方便后续测试维护 |
| 4 | `packages/hermes-db/README.md`<br>`packages/hermes-db/tests/integration_test_guide.md`<br>`specs/hermes-db-batch-planning-api/` | `docs(hermes-db): add batch planning API documentation`<br><br>- 更新 README 工具列表（+4 个 MCP tools）<br>- 新增集成测试指南（8 步手动验证流程）<br>- 新增完整 SDD 文档（spec, plan, tasks, acceptance, cross-repo-coordination）<br><br>Refs: hermes-db-batch-planning-api T017-T019 | 文档独立批次，包含 spec、测试指南和验收记录 |
| 5 | `specs/.active` | `chore: update active feature to hermes-db-batch-planning-api`<br><br>更新当前活跃 feature 为 hermes-db-batch-planning-api。 | Workspace 状态独立，不影响功能代码 |

---

## Execution Rules

- 未获得用户明确确认前，不得执行 `git add` 或 `git commit`。
- 只允许 add `Included Files` 中属于已确认 batch 的文件。
- 不得使用 `git add -A`、`git add .` 或等价宽泛命令。
- 每个 batch 单独提交；任一 batch 失败时停止后续 batch。
- 不自动执行 `git push`。push 必须由用户另行明确要求。
- 如果没有相关 diff，记录 `no related diff`，不得生成空 commit。

---

## User Confirmation

等待用户确认：

- **确认提交**: 按上述 5 个 batches 执行本地提交。
- **修改计划**: 根据用户要求调整 included/excluded/batches。
- **暂不提交**: closeout 记录 not submitted 和剩余 dirty files。
