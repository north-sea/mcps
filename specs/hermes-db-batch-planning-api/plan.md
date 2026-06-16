# Implementation Plan: hermes-db-batch-planning-api

**Workspace**: `hermes-db-batch-planning-api` | **Date**: 2026-06-16 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/hermes-db-batch-planning-api/spec.md`

---

## Summary

为 agents 仓库的 novel-agent 提供 4 个批量 MCP tools：批量写入书籍规划数据（事务保证）、批量读取章纲输入包、上下文版本追踪。遵循现有 hermes-db 架构模式（FastMCP + asyncpg + 原生 SQL），在单个 PostgreSQL 事务中完成 4 表原子写入，通过 join 优化减少章纲生成的 HTTP 往返次数。

---

## Architecture Overview

本次改动在现有 hermes-db 项目中新增 4 个 MCP tools 和对应的 repository 方法，扩展 novel domain 的数据访问能力。

```text
┌─────────────────────────────────────────────────────────────┐
│ agents 仓库 (novel-agent orchestrator)                       │
│  └─ NovelRepositoryPort 接口                                 │
└────────────────┬────────────────────────────────────────────┘
                 │ MCP protocol (JSON-RPC 2.0)
┌────────────────▼────────────────────────────────────────────┐
│ hermes-db MCP Server                                         │
│  ├─ tools/novel_planning.py (NEW)                           │
│  │   ├─ batch_create_book_planning                          │
│  │   ├─ get_chapter_input_pack                              │
│  │   ├─ update_context_version                              │
│  │   └─ get_current_context_version                         │
│  └─ repositories/novel_planning_repo.py (NEW)               │
│      └─ [数据访问方法]                                       │
└────────────────┬────────────────────────────────────────────┘
                 │ asyncpg
┌────────────────▼────────────────────────────────────────────┐
│ PostgreSQL (hermes schema)                                   │
│  ├─ novel_books (扩展 context_version)                      │
│  ├─ novel_chapters (扩展 context_version, residue)          │
│  ├─ novel_worldbuilding (NEW)                               │
│  ├─ novel_characters (NEW)                                  │
│  ├─ novel_foreshadowing (NEW)                               │
│  ├─ novel_volume_outlines (NEW)                             │
│  ├─ novel_human_reviews (NEW)                               │
│  └─ novel_context_change_log (NEW)                          │
└─────────────────────────────────────────────────────────────┘
```

**数据流**：
1. **批量写入流**：MCP tool → 参数校验 → repository → asyncpg transaction → 4 表写入（原子）
2. **批量读取流**：MCP tool → 参数校验 → repository → join 查询（5 表）→ 结果聚合

---

## Capacity / Scale Notes

- **规模假设**: 0.1-0.5 QPS，单书串行规划，1-3 本书并发，50-200 章/书
- **读写特征**: 写少读多（规划一次，章纲生成多次引用）
- **失败代价**: 
  - **部分写入失败** → 数据不一致 → 章纲生成错误 → **必须事务保证**
  - **join 查询慢** → 章纲生成延迟高 → 用户体验下降 → **需要索引优化**
  - **幂等性缺失** → 重复写入 → 数据冲突 → **需要双重检查**

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001: 跳过候选方案讨论 | 需求简单，现有架构已有明确模式 | A: 讨论多个方案 / B: 直接遵循现有模式 | B: 遵循现有 FastMCP + asyncpg 模式 | 无架构探索空间 | 项目现状 |
| ADR-002: 事务管理方式 | 4 表写入必须原子 | A: 手动 begin/commit / B: context manager | B: async with conn.transaction() | 需要 asyncpg 0.30+ | [asyncpg docs](https://magicstack.github.io/asyncpg/current/usage.html) |
| ADR-003: 批量写入方式 | 需要插入多个 characters/foreshadowing | A: loop inside transaction / B: executemany() | A: loop + ON CONFLICT（参考现有 batch_upsert_chapters） | 可能比 executemany 慢，但逻辑清晰 | repositories/novel_repo.py:71 |
| ADR-004: 幂等性检查方式 | 避免重复写入 | A: 只检查 book_slug / B: 双重检查（book + 规划表） | B: 检查 book_slug 存在 + 规划表有记录 | 多一次查询开销（~10ms） | spec.md 决策 6 |
| ADR-005: residue 字段实现 | emotionalDebts 数据源 | A: 扩展 novel_chapters / B: 新建 emotional_debts 表 | A: 扩展 novel_chapters.residue JSONB | 无独立查询能力 | spec.md 决策 2 |

---

## Key Design Decisions

### Decision 1: 错误处理和错误码设计

- **背景**: MCP tools 需要明确的错误返回格式，便于 agents 仓库识别失败原因并决策重试或降级
- **选项**:
  - A: 复用现有 ERROR_CODES，扩展 novel_planning 专属错误码
  - B: 创建独立的错误码体系
- **结论**: A（扩展现有 ERROR_CODES）
- **影响**: 在 contracts.py 中新增以下错误码：
  - `planning_already_exists`: 幂等性检查失败
  - `book_not_found`: bookSlug 不存在
  - `foreshadowing_limit_exceeded`: 伏笔数量超过 100
  - `transaction_failed`: 事务回滚（含原因）
- **来源**: contracts.py:271-297（现有错误码约定）

---

### Decision 2: 事务隔离级别

- **背景**: PostgreSQL 默认隔离级别 READ COMMITTED，需要确认是否需要更高隔离级别
- **选项**:
  - A: READ COMMITTED（默认）
  - B: REPEATABLE READ（防止幻读）
  - C: SERIALIZABLE（完全隔离）
- **结论**: A（READ COMMITTED）
- **影响**: 
  - 不设置 isolation 参数，使用 asyncpg 默认行为
  - 单书串行规划场景无并发冲突风险
  - 如果未来需要多书并发，再升级到 REPEATABLE READ
- **来源**: [PostgreSQL Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)

---

### Decision 3: join 查询优化策略

- **背景**: get_chapter_input_pack 需要 join 5 个表，可能成为性能瓶颈
- **选项**:
  - A: 单个 join 查询 + 后处理聚合
  - B: 多个独立查询 + Python 侧聚合
  - C: 引入 Redis 缓存
- **结论**: A（单个 join 查询）
- **影响**: 
  - SQL 逻辑复杂，但减少网络往返（14 次 → 1 次）
  - 依赖索引优化（novel_foreshadowing 需要复合索引）
  - 0.1-0.5 QPS 场景下不引入缓存（避免过度设计）
- **来源**: repositories/topic_repo.py 现有 join 模式参考

---

## Module Design

### Module: tools/novel_planning.py (NEW)

**职责**: 定义 4 个 MCP tools，处理参数校验、调用 repository 层、错误转换

**改动概述**: 新增文件，遵循现有 tools/novel_chapters.py 的模式

**关键接口 / 行为**:

```python
# 1. batch_create_book_planning
@mcp.tool()
async def batch_create_book_planning(
    bookSlug: str,
    outline: dict,
    worldbuilding: dict,
    characters: list[dict],
    foreshadowing: list[dict],
    ctx: AppContext
) -> dict:
    """
    步骤：
    1. 校验 bookSlug 非空
    2. 校验 foreshadowing 数组长度 <= 100
    3. 调用 repo.batch_create_book_planning()
    4. 返回 {success: true} 或 ToolError
    """

# 2. get_chapter_input_pack
@mcp.tool()
async def get_chapter_input_pack(
    bookSlug: str,
    chapterNumber: int,
    recentChaptersCount: int = 3,
    maxCharacters: int = 5,
    maxForeshadowing: int = 3,
    maxEmotionalDebts: int = 2,
    ctx: AppContext
) -> dict:
    """
    步骤：
    1. 校验 chapterNumber > 0
    2. 调用 repo.get_chapter_input_pack()
    3. 返回完整输入包或 ToolError
    """

# 3. update_context_version
# 4. get_current_context_version
# （略，参考 tools/topics.py 的简单 CRUD 模式）
```

**注意事项**:
- 复用 contracts.py 的 error() 函数和 ToolError 类型
- 参数校验失败立即返回，不调用 repository
- 数据库错误统一捕获为 database_error 错误码

---

### Module: repositories/novel_planning_repo.py (NEW)

**职责**: 封装 PostgreSQL 数据访问逻辑，包括事务管理、join 查询、幂等性检查

**改动概述**: 新增文件，参考 repositories/novel_repo.py 的模式

**关键接口 / 行为**:

```python
async def batch_create_book_planning(
    pool: asyncpg.Pool,
    book_slug: str,
    outline: dict,
    worldbuilding: dict,
    characters: list[dict],
    foreshadowing: list[dict]
) -> None:
    """
    步骤：
    1. acquire connection
    2. 开启事务 (async with conn.transaction())
    3. 幂等性检查：
       - SELECT FROM novel_books WHERE book_slug = $1
       - SELECT FROM novel_worldbuilding WHERE book_slug = $1 LIMIT 1
       - 任一存在则 raise ValueError("planning_already_exists")
    4. INSERT novel_worldbuilding (单条)
    5. loop: INSERT novel_characters ... ON CONFLICT DO NOTHING
    6. loop: INSERT novel_foreshadowing ... ON CONFLICT DO NOTHING
    7. 事务自动提交或回滚
    """

async def get_chapter_input_pack(
    pool: asyncpg.Pool,
    book_slug: str,
    chapter_number: int,
    recent_chapters_count: int,
    max_characters: int,
    max_foreshadowing: int,
    max_emotional_debts: int
) -> dict:
    """
    步骤：
    1. acquire connection (无需事务，只读查询)
    2. 单个 join 查询：
       - recent chapters (ORDER BY chapter_number DESC LIMIT N)
       - characters (LIMIT max_characters)
       - foreshadowing (WHERE status='active' AND payoff_chapter >= chapter_number LIMIT N)
       - volume_outlines (推断当前卷)
    3. 从 recent chapters 的 residue.emotionalDebts 聚合（Python 侧）
    4. 返回 ChapterInputPack 字典
    """
```

**注意事项**:
- 事务内异常自动回滚，无需手动 rollback
- join 查询依赖索引（见 Migration 章节）
- residue JSONB 字段需要 json.loads 反序列化（asyncpg 自动处理）

---

### Module: migrations/versions/TXXX_novel_planning_tables.py (NEW)

**职责**: 创建 8 个新表和扩展 2 个现有表字段

**改动概述**: 新增 Alembic migration 文件

**关键行为**:

```python
def upgrade():
    # 1. 扩展现有表
    op.add_column('novel_books', sa.Column('context_version', sa.Integer, server_default='1'))
    op.add_column('novel_chapters', sa.Column('context_version', sa.Integer, nullable=True))
    op.add_column('novel_chapters', sa.Column('residue', sa.dialects.postgresql.JSONB, nullable=True))
    
    # 2. 创建 6 个新表（见 spec.md Database Schema Changes）
    op.create_table('novel_worldbuilding', ...)
    op.create_table('novel_characters', ...)
    op.create_table('novel_foreshadowing', ...)
    op.create_table('novel_volume_outlines', ...)
    op.create_table('novel_human_reviews', ...)
    op.create_table('novel_context_change_log', ...)
    
    # 3. 创建索引
    op.create_index('idx_novel_foreshadowing_book_status_payoff', 
                    'novel_foreshadowing', 
                    ['book_slug', 'status', 'payoff_chapter'])
    op.create_index('idx_novel_chapters_book_number', 
                    'novel_chapters', 
                    ['book_slug', 'chapter_number'])

def downgrade():
    # 逆向操作：删除表和索引，移除字段
```

**注意事项**:
- 遵循现有 migration 命名约定（见 0007_novel_agent_books_chapters.py）
- 所有外键 ON DELETE CASCADE
- CHECK 约束用于枚举值校验

---

## Data Model

核心变化详见 spec.md Database Schema Changes 章节。关键点：

1. **主键策略**: 所有新表使用 UUID 主键，外键引用 novel_books(book_slug) TEXT
2. **唯一约束**: 
   - novel_worldbuilding(book_slug) UNIQUE
   - novel_characters(book_slug, name) UNIQUE
   - novel_foreshadowing(book_slug, title) UNIQUE
3. **JSONB 字段**:
   - novel_chapters.residue（存储 emotionalDebts、unsolvedTensions、lingeringMoods）
   - novel_human_reviews.feedback（结构化反馈）
4. **时间戳**: 所有表包含 created_at / updated_at（除 novel_context_change_log 只有 changed_at）

不单独创建 data-model.md，因为 spec.md 已包含完整表定义。

---

## Project Structure

```text
packages/hermes-db/
├── migrations/versions/
│   └── TXXX_novel_planning_tables.py        (NEW)
├── src/hermes_db_mcp/
│   ├── tools/
│   │   └── novel_planning.py                (NEW, ~200 行)
│   ├── repositories/
│   │   └── novel_planning_repo.py           (NEW, ~300 行)
│   ├── contracts.py                         (扩展错误码，+4 个)
│   └── server.py                            (注册 4 个新 tools)
└── tests/
    ├── test_novel_planning_tools.py         (NEW)
    └── test_novel_planning_repo.py          (NEW)
```

---

## Risks and Tradeoffs

### 风险 1: 事务超时（低严重性）

- **风险**: 4 个表的批量写入可能耗时较长，特别是 foreshadowing 数组很大时
- **缓解**: 
  - 限制 foreshadowing 数组最大长度 100
  - 使用 loop inside transaction（参考现有 batch_upsert_chapters）
  - 监控事务耗时，记录 >1s 的慢事务

### 风险 2: join 查询性能（低严重性）

- **风险**: get_chapter_input_pack 的 5 表 join 可能导致查询延迟
- **缓解**: 
  - 建立复合索引（book_slug, status, payoff_chapter）
  - 使用 EXPLAIN ANALYZE 验证查询计划
  - 规模 0.1-0.5 QPS 下暂不引入缓存

### 风险 3: residue 字段结构漂移（中严重性）

- **风险**: novel_chapters.residue 是自由 JSONB，可能出现结构不一致
- **缓解**: 
  - 在 agents 仓库的章节生成逻辑中明确 residue 结构
  - 考虑在 repository 层添加 JSONB schema 校验（未来优化）
  - 当前 MVP 阶段容忍结构漂移

### 权衡说明

| 权衡点 | 选择 | 代价 |
|--------|------|------|
| 事务 vs 批量API | 单事务 4 表写入 | 可能超时（已缓解） |
| join vs 多次查询 | 单个 join | SQL 复杂度高，但减少网络往返 |
| residue JSONB vs 独立表 | JSONB | 无独立查询能力，结构可能漂移 |
| 缓存 vs 无缓存 | 无缓存（MVP） | 未来高频场景需要引入 Redis |

---

## Evolution Path

- **MVP**（当前阶段）: 
  - 无缓存，单个 join 查询
  - residue JSONB 自由结构
  - 单书串行规划假设
  
- **成长期**（触发信号：QPS > 1，多书并发 > 5）: 
  - 引入 Redis 缓存 get_chapter_input_pack 结果（TTL 10min）
  - 考虑将 emotional_debts 提取为独立表
  - 升级事务隔离级别到 REPEATABLE READ

- **成熟期**（触发信号：QPS > 10，数据量 > 10万章）: 
  - 考虑读写分离（主从复制）
  - 考虑分表策略（按 book_slug 分片）
  - 引入查询缓存预热机制

---

## Anti-Pattern Check

- ✅ 是否把成熟期架构套到了 MVP：否（未引入缓存、分片、消息队列）
- ✅ 是否引用了外部模式但没有适配检查：否（遵循现有项目模式）
- ✅ 是否新增未记录的状态、依赖、缓存、队列或失败模式：否（所有决策已记录）

---

## Verification Strategy

### 1. 单元测试（pytest + pytest-asyncio）

**test_novel_planning_repo.py**:
- `test_batch_create_book_planning_success`: 验证 4 表原子写入
- `test_batch_create_book_planning_idempotent`: 验证幂等性（重复调用返回错误）
- `test_batch_create_book_planning_rollback`: 验证事务回滚（模拟约束冲突）
- `test_get_chapter_input_pack_success`: 验证完整输入包返回
- `test_get_chapter_input_pack_first_chapter`: 验证冷启动场景（recentChapters = []）
- `test_get_chapter_input_pack_filter_foreshadowing`: 验证活跃伏笔过滤

**test_novel_planning_tools.py**:
- `test_batch_create_book_planning_tool_validation`: 验证参数校验（foreshadowing > 100 拒绝）
- `test_get_chapter_input_pack_tool_error_handling`: 验证 bookSlug 不存在返回错误

### 2. 集成测试

**手动验证步骤**:
1. 执行 migration（alembic upgrade head）
2. 调用 batch_create_book_planning，检查 4 个表是否有数据
3. 调用 get_chapter_input_pack，检查返回数据是否完整
4. 使用 EXPLAIN ANALYZE 验证 join 查询性能 <200ms
5. 模拟事务回滚（删除 novel_worldbuilding UNIQUE 约束后重试）

### 3. 性能验证

- 批量写入延迟 <500ms（通过 pytest-benchmark 或手动计时）
- join 查询延迟 <200ms（通过 EXPLAIN ANALYZE）
- 慢查询日志监控（PostgreSQL log_min_duration_statement = 200）

---

## Stage Readiness

- **是否需要 data-model.md**: 不需要（spec.md 已包含完整表定义）
- **下一步建议**: `tasks`（拆解可执行任务）
- **阻塞项**: 无

---

## Design Artifacts

本次计划涉及的产物：

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | ✅ 必须 | 本文件 |
| data-model.md | ❌ 不需要 | spec.md 已包含完整表定义 |
| tasks.md | 后续阶段生成 | 由 `tasks` 阶段产出 |
| acceptance.md | 后续阶段生成 | 用于最终验收结论 |

---

## Notes

### 待观察点

1. **事务耗时分布**: 关注 foreshadowing 数组大小与事务耗时的关系
2. **join 查询计划**: 验证索引是否被正确使用（通过 EXPLAIN ANALYZE）
3. **residue 字段使用率**: 观察是否所有章节都有 residue 数据，缺失率是否影响 emotionalDebts 提取

### 已知约束

- 依赖 asyncpg 0.30+（async with transaction() 语法）
- 依赖 PostgreSQL 12+（JSONB 和 gen_random_uuid()）
- agents 仓库需要同步修改 NovelRepositoryPort 接口（bookId → bookSlug）

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| asyncpg 事务管理 | https://magicstack.github.io/asyncpg/current/usage.html | 官方文档 |
| PostgreSQL JSONB | https://www.postgresql.org/docs/current/datatype-json.html | 官方文档 |
| MCP tool 定义 | https://modelcontextprotocol.io/docs/concepts/tools | 官方文档 |
| 现有架构模式 | repositories/novel_repo.py:71-108 | batch_upsert_chapters 参考 |
| 错误码约定 | contracts.py:271-297 | ERROR_CODES 字典 |

