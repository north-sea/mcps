# Acceptance Record: hermes-db-batch-planning-api

**Workspace**: `hermes-db-batch-planning-api` | **Date**: 2026-06-16 | **Spec**: [spec.md](spec.md)

> 本 feature 命中 `external-side-effects` trait，使用完整 acceptance 模板。

---

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| US1-1: 批量写入 4 表 | Mock transaction 验证 + 3 次 execute 调用（worldbuilding + 1 character + 1 foreshadowing） | `test_novel_planning_repo.py::test_success_batch_create` PASSED | PASS |
| US1-2: 事务回滚 | `async with conn.transaction()` 自动回滚机制 + MockTransaction 协议验证 | `novel_planning_repo.py:88-127` + mock 测试 | PASS |
| US1-3: 幂等性 | 双重检查逻辑（book exists + planning tables empty）+ ValueError("planning_already_exists") | `test_novel_planning_repo.py::test_idempotent_planning_already_exists` PASSED | PASS |
| US1-4: 空数组边界 | 代码逻辑允许 `characters=[]`，for 循环自然跳过 | `novel_planning_repo.py:114-119` 代码审查 | PASS |
| US1-5: 伏笔数量限制 | `if len(foreshadowing) > 100:` 校验 + error("foreshadowing_limit_exceeded") | `test_novel_planning_tools.py::test_foreshadowing_limit_exceeded` PASSED | PASS |
| US1-6: 连接失败 | `except Exception as e:` 捕获并返回 error("database_error") | `novel_planning.py:106-107` 代码审查 | PASS |
| US2-1: 读取完整输入包 | 返回包含 recentChapters/characters/foreshadowing/emotionalDebts/volumeGoal 的完整结构 | `test_novel_planning_repo.py::test_success_get_input_pack` PASSED | PASS |
| US2-2: 冷启动 | chapter_number = 1 时 WHERE chapter_number < 1 返回空列表，仍返回其他字段 | `test_novel_planning_repo.py::test_cold_start_first_chapter` PASSED | PASS |
| US2-3: 伏笔过滤 | SQL: `WHERE status = 'active' AND payoff_chapter >= $4` | `novel_planning_repo.py:186-192` + mock fetch 验证 | PASS |
| US2-4: book_not_found | book_exists = None 时 raise ValueError("book_not_found") | `test_novel_planning_tools.py::test_book_not_found_error` PASSED | PASS |
| US2-5: 超出已写章节 | SQL LIMIT 自动限制返回数量，不抛错 | `novel_planning_repo.py:161` 代码审查 | PASS |
| US2-6: volumeGoal = null | COALESCE 返回 null 时赋值为 None | `novel_planning_repo.py:208` 代码审查 | PASS |
| US3-1: 更新版本 | UPDATE context_version + 1 + INSERT change_log | `test_novel_planning_repo.py::test_update_context_version` PASSED | PASS |
| US3-2: 读取版本 | SELECT context_version FROM novel_books WHERE book_slug = $1 | `test_novel_planning_repo.py::test_get_current_context_version` PASSED | PASS |
| US3-3: 变更日志 | INSERT INTO novel_context_change_log (book_slug, old_version, new_version, changed_scope, change_summary, changed_at) | Migration `0008_novel_planning_tables.py` + repo 逻辑 `novel_planning_repo.py:269-276` | PASS |

**Evidence 质量**: 15/15 requirements 都有可定位的测试或代码路径，无 PARTIAL 或 FAIL。

---

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | 4 个 MCP tools 已实现，Repository 层事务管理、幂等性、join 查询逻辑正确，14/14 单元测试通过 |
| Workflow closure | PASS | MCP tools → Repository → PostgreSQL 链路完整，错误码转换正确，参数校验完整 |
| User-visible outcome | CONDITIONAL PASS | MCP tools 功能完整，但未执行端到端集成测试（T017）和跨仓库协调（T018） |

**Overall**: ✅ **CONDITIONAL PASS**

**三维不一致说明**:

User-visible outcome 判为 CONDITIONAL PASS 的原因：
- MCP tools 本身不是用户直接可见（通过 agents 仓库的 novel-agent 间接调用）
- 单元测试覆盖充分（14/14），但缺少端到端集成测试验证实际 PostgreSQL 行为和性能指标
- 跨仓库接口变更（bookId→bookSlug）需外部协调完成后才能真正验证联调

本 feature 实现层面已完成且质量合格，允许进入 closeout 并标记为 CONDITIONAL PASS，待集成测试和跨仓库协调完成后可升级为 PASS。

---

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | ✅ 不适用 | 新功能，无旧逻辑需退役 | 无 |
| 发布、提交、CI 或 follow-through | ✅ 延后 | Migration 需执行 `alembic upgrade head`，已记录在 `tests/integration_test_guide.md` | 用户或 CI 在部署前执行 migration |
| 文档、阶段说明、模板或验收记录更新 | ✅ 已完成 | README.md 已更新工具列表（+4 个 MCP tools） | 无 |
| ADR、架构债或演进触发信号 | ✅ 已完成 | 5 个 ADR 已记录在 `plan.md`，可选优化（Redis 缓存、读写分离）已记录在 Phase 6 | 当 QPS > 1 时考虑缓存，QPS > 10 时考虑读写分离 |
| Knowledge Capture | ✅ 已完成 | 4 条可复用知识已识别并记录在本文档 Knowledge Capture 段 | 无 |

**无阻塞项。延后项（migration 执行、集成测试、跨仓库协调）不影响代码交付质量。**

---

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| pattern | asyncpg 事务管理 - loop inside transaction | 批量写入时应将循环放在事务内（loop inside transaction），而不是为每个元素开启独立事务，以保证原子性并减少事务开销。 | ADR-003 (`plan.md`), `novel_planning_repo.py:114-125` | 所有 hermes-db asyncpg 批量写入场景 | recorded-only | 无 |
| pattern | 双重幂等性检查模式 | 批量写入前应检查 (1) 父实体存在，(2) 子表无记录，双重检查保证幂等性且错误信息明确（book_not_found vs planning_already_exists）。 | ADR-004 (`plan.md`), `novel_planning_repo.py:92-102` | 所有需要幂等性保证的批量写入 MCP tools | recorded-only | 无 |
| convention | MCP tool 错误码设计 - ValueError 转换模式 | Repository 层抛出带语义前缀的 ValueError（如 "book_not_found: <slug>"），Tool 层通过字符串匹配（`if "book_not_found" in str(e)`）转换为明确错误码和 details。 | Decision 1 (`plan.md`), `novel_planning.py:98-108` | 所有 hermes-db MCP tools | recorded-only | 无 |
| gotcha | MockTransaction 异步上下文管理器协议 | Mock asyncpg transaction 时必须创建独立类实现 `__aenter__` 和 `__aexit__`，直接返回 AsyncMock 会导致 "coroutine object does not support the asynchronous context manager protocol" 错误。 | Error fix in `test_novel_planning_repo.py:27-31` | 所有测试 asyncpg 事务的单元测试 | recorded-only | 无 |

---

## Commit Result

| Field | Value |
|---|---|
| Status | ✅ committed |
| Commit Hashes | a4cf8f2, fd3c8f8, 7ddb7bc, 8df2370, d725cec |
| Commit Messages | Batch 1: feat(hermes-db): add novel planning tables migration<br>Batch 2: feat(hermes-db): implement batch planning API<br>Batch 3: test(hermes-db): add novel planning tests<br>Batch 4: docs(hermes-db): add batch planning API documentation<br>Batch 5: chore: update active feature to hermes-db-batch-planning-api |
| Included Files | 18 个文件（1 migration + 4 实现文件 + 2 测试文件 + 1 集成测试指南 + 9 SDD 文档 + 1 README + 1 .active） |
| Excluded / Remaining Files | 无 |
| Reason | 已按 5 个 batch 顺序提交完成 |

---

## Completion Record

- **最终结论**: ✅ CONDITIONAL PASS
- **完成依据**: 15/15 P0/P1 requirements 已验证（Evidence Table），14/14 单元测试通过，所有 ADR 已遵守，无 architecture drift
- **阻塞项**: 无
- **延后项**: 
  1. T017 端到端集成测试（需手动执行 `tests/integration_test_guide.md`）
  2. T018 跨仓库协调（需通知 agents 仓库 bookId→bookSlug 接口变更）
  3. **⚠️ Migration 执行（部署前必须运行 `alembic upgrade head`）**
- **退役结论**: 不适用（新功能）
- **提交结论**: ✅ committed（5 个 batches，commit hash: a4cf8f2, fd3c8f8, 7ddb7bc, 8df2370, d725cec）
- **后续动作**: 部署前执行 migration → 集成测试 → 跨仓库协调
