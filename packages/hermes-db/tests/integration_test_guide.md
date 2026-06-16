# Integration Test Guide: hermes-db-batch-planning-api

## T017: 端到端集成测试

本文件记录手动集成测试的步骤和验证点。

---

## 前置条件

1. PostgreSQL 数据库运行中
2. 已执行 migration：`alembic upgrade head`
3. 已配置 `.env` 文件（PG_DSN, REDIS_URL）
4. MCP server 可启动

---

## 测试步骤

### Step 1: 执行 Migration

```bash
cd packages/hermes-db
source .venv/bin/activate
alembic upgrade head
```

**验证点**：
- [ ] 无错误输出
- [ ] 检查 8 个表是否创建：
  ```sql
  \dt hermes.novel_*
  ```
  应显示：
  - novel_books（扩展 context_version）
  - novel_chapters（扩展 context_version, residue）
  - novel_worldbuilding
  - novel_characters
  - novel_foreshadowing
  - novel_volume_outlines
  - novel_human_reviews
  - novel_context_change_log

- [ ] 检查索引是否创建：
  ```sql
  \di hermes.idx_novel_*
  ```

---

### Step 2: 准备测试数据

创建测试书籍：

```sql
INSERT INTO hermes.novel_books (book_slug, title, author, total_chapters, context_version)
VALUES ('integration-test-book', 'Integration Test Novel', 'Test Author', 100, 1);
```

**验证点**：
- [ ] 插入成功
- [ ] context_version 默认值为 1

---

### Step 3: 测试 batch_create_book_planning

使用 MCP client 调用（或手动 Python 脚本）：

```python
import asyncio
import asyncpg
from hermes_db_mcp.repositories import novel_planning_repo

async def test():
    pool = await asyncpg.create_pool(dsn="postgresql://...")
    
    await novel_planning_repo.batch_create_book_planning(
        pool,
        book_slug="integration-test-book",
        outline={"storyArc": "Test arc", "mainCharacters": ["Alice"], "coreConflicts": ["Test conflict"], "estimatedChapters": 100},
        worldbuilding={"rules": "Test rules", "history": "Test history", "magicSystem": "Test magic"},
        characters=[
            {"name": "Alice", "role": "protagonist", "personality": "brave", "secondaryInterpretation": "complex", "behaviorProhibitions": ["lie", "cheat"]},
            {"name": "Bob", "role": "antagonist", "personality": "cunning", "secondaryInterpretation": None, "behaviorProhibitions": []},
        ],
        foreshadowing=[
            {"title": "Mystery Box", "plantChapter": 1, "reminderChapter": 5, "payoffChapter": 10, "priority": "high"},
            {"title": "Dark Secret", "plantChapter": 2, "reminderChapter": None, "payoffChapter": 15, "priority": "medium"},
        ],
    )
    
    await pool.close()

asyncio.run(test())
```

**验证点**：
- [ ] 无异常抛出
- [ ] 4 个表有数据：
  ```sql
  SELECT COUNT(*) FROM hermes.novel_worldbuilding WHERE book_slug = 'integration-test-book';  -- 应为 1
  SELECT COUNT(*) FROM hermes.novel_characters WHERE book_slug = 'integration-test-book';      -- 应为 2
  SELECT COUNT(*) FROM hermes.novel_foreshadowing WHERE book_slug = 'integration-test-book';   -- 应为 2
  ```

---

### Step 4: 测试幂等性

重复执行 Step 3 的代码。

**验证点**：
- [ ] 抛出 ValueError，包含 "planning_already_exists"

---

### Step 5: 准备章节数据（测试 get_chapter_input_pack）

```sql
-- 插入测试章节
INSERT INTO hermes.novel_chapters (chapter_id, book_slug, chapter_number, title, content, word_count, context_version, residue)
VALUES 
  ('ch_001', 'integration-test-book', 1, 'Chapter 1', 'Content 1', 3000, 1, '{"emotionalDebts": [{"description": "Alice feels guilty", "involvedCharacters": ["Alice"]}]}'),
  ('ch_002', 'integration-test-book', 2, 'Chapter 2', 'Content 2', 3000, 1, '{"emotionalDebts": [{"description": "Bob seeks revenge", "involvedCharacters": ["Bob"]}]}');

-- 插入章节分析
INSERT INTO hermes.novel_chapter_analyses (chapter_id, summary, plot_points, characters, conflicts, hooks)
VALUES 
  ('ch_001', 'Summary 1', '[]', '[]', '[]', '[]'),
  ('ch_002', 'Summary 2', '[]', '[]', '[]', '[]');

-- 插入卷大纲
INSERT INTO hermes.novel_volume_outlines (book_slug, volume_number, goal, start_chapter, end_chapter)
VALUES ('integration-test-book', 1, 'Volume 1 Goal: Introduce characters', 1, 50);
```

---

### Step 6: 测试 get_chapter_input_pack

```python
async def test_get_input_pack():
    pool = await asyncpg.create_pool(dsn="postgresql://...")
    
    result = await novel_planning_repo.get_chapter_input_pack(
        pool,
        book_slug="integration-test-book",
        chapter_number=3,
        recent_chapters_count=2,
        max_characters=5,
        max_foreshadowing=3,
        max_emotional_debts=2,
    )
    
    print("Result:", result)
    await pool.close()

asyncio.run(test_get_input_pack())
```

**验证点**：
- [ ] `recentChapters` 包含 2 个章节（chapter 1, 2）
- [ ] `characters` 包含 2 个角色（Alice, Bob）
- [ ] `foreshadowing` 包含 2 个伏笔（Mystery Box, Dark Secret）
- [ ] `emotionalDebts` 包含最多 2 个情感债
- [ ] `volumeGoal` = "Volume 1 Goal: Introduce characters"

---

### Step 7: 测试 update_context_version

```python
async def test_update_version():
    pool = await asyncpg.create_pool(dsn="postgresql://...")
    
    new_version = await novel_planning_repo.update_context_version(
        pool,
        book_slug="integration-test-book",
        changed_scope="book_outline",
        change_summary="Updated story arc to be more dramatic",
    )
    
    print("New version:", new_version)  # 应为 2
    
    current_version = await novel_planning_repo.get_current_context_version(
        pool,
        book_slug="integration-test-book",
    )
    
    print("Current version:", current_version)  # 应为 2
    await pool.close()

asyncio.run(test_update_version())
```

**验证点**：
- [ ] new_version = 2
- [ ] current_version = 2
- [ ] novel_context_change_log 表有 1 条记录

---

### Step 8: 性能验证（T016）

```sql
-- 测试 batch_create_book_planning 延迟
\timing on
-- 执行 batch_create_book_planning（通过 Python 脚本计时）

-- 测试 get_chapter_input_pack 查询性能
EXPLAIN ANALYZE
SELECT chapter_number, title, summary, context_version, residue
FROM hermes.novel_chapter_analyses
JOIN hermes.novel_chapters USING (chapter_id)
WHERE book_slug = 'integration-test-book' AND chapter_number < 3
ORDER BY chapter_number DESC
LIMIT 2;
```

**验证点**：
- [ ] batch_create_book_planning <500ms
- [ ] get_chapter_input_pack <200ms
- [ ] EXPLAIN ANALYZE 显示使用了索引 `idx_novel_chapters_book_number`
- [ ] foreshadowing 查询使用了索引 `idx_novel_foreshadowing_book_status_payoff`

---

## 清理测试数据

```sql
DELETE FROM hermes.novel_books WHERE book_slug = 'integration-test-book';
-- CASCADE 会自动删除相关的所有表数据
```

---

## 集成测试结论

- [ ] 所有步骤验证通过
- [ ] 性能指标达标
- [ ] 事务原子性验证通过
- [ ] 幂等性验证通过
- [ ] 完整流程无阻塞

**测试日期**: _______________  
**测试人**: _______________  
**结论**: ☐ PASS  ☐ FAIL

**备注**:
