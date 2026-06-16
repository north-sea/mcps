# Feature Specification: hermes-db-batch-planning-api

**Workspace**: `hermes-db-batch-planning-api`  
**Created**: 2026-06-16  
**Status**: Draft  
**Priority**: 高（阻塞 `novel-agent-book-planning` feature 的 implement 阶段）  
**Input**: 来自 agents 仓库的 `specs/novel-agent-book-planning/mcps-dependency.md`

> 本 feature 为 agents 仓库的 `novel-agent-book-planning` feature 提供跨仓库依赖支持。

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ❌ | 单一批量 API 实现，无多阶段协同 |
| `external-side-effects` | ✅ | 写入 PostgreSQL 数据库，影响 hermes-db 持久化状态 |
| `artifact-handoff` | ❌ | 无下游 feature 消费本 feature 的产物 |
| `user-visible-output` | ❌ | MCP tools，用户不直接可见（通过 agents 仓库间接使用） |
| `prior-closure-failure` | ❌ | 无历史失败记录 |
| `bugfix-loop-breaker` | ❌ | 不是 bugfix |

**结论**: 命中 1 个 trait (`external-side-effects`)，适用标准 SDD 流程，无需特殊强化。

---

## User Scenarios & Testing

### User Story 1 - 批量写入书籍规划数据（事务保证） (Priority: P0)

作为 **novel-agent orchestrator**，我希望能够一次性批量写入书籍规划数据（4 个表：novel_worldbuilding、novel_characters、novel_foreshadowing、novel_volume_outlines），并通过 PostgreSQL 事务保证原子性，以便避免部分写入失败导致的数据不一致。

**Why this priority**: 这是 novel-agent 全书大纲生成的核心依赖，任一表写入失败都必须回滚。

**Acceptance Scenarios**:

1. **[US1-1] 成功批量写入 4 个表**
   **Given** 提供完整的 `{bookSlug, outline, worldbuilding, characters[], foreshadowing[]}` 数据  
   **When** 调用 `batch_create_book_planning` MCP tool  
   **Then** 系统在 PostgreSQL 事务中原子写入 4 个表，返回 `{success: true}`

2. **[US1-2] 事务回滚机制**
   **Given** 提供的数据中第 3 个表（novel_characters）存在约束冲突  
   **When** 调用 `batch_create_book_planning` MCP tool  
   **Then** 系统回滚前 2 个表（novel_worldbuilding）的写入，返回 `{success: false, errors: ['constraint violation']}`

3. **[US1-3] 幂等性保证**
   **Given** 相同 `bookSlug` 的规划数据已存在  
   **When** 再次调用 `batch_create_book_planning` MCP tool  
   **Then** 系统拒绝写入，返回 `{success: false, errors: ['book planning already exists']}`

**Edge Cases**:

- **[US1-4]** characters 数组为空 → 允许（某些书可能初期没有角色档案）
- **[US1-5]** foreshadowing 数组超过 100 个 → 拒绝并提示"伏笔数量过多"
- **[US1-6]** PostgreSQL 连接失败 → 返回明确的数据库连接错误

---

### User Story 2 - 批量读取章纲输入包 (Priority: P0)

作为 **novel-agent orchestrator**，我希望能够一次性读取章纲生成所需的完整输入包（上 N 章摘要、相关角色、活跃伏笔、情感债），以便减少 HTTP 往返次数并提升性能。

**Why this priority**: 章纲生成是高频操作，每次生成需要 14 次 HTTP 调用会导致延迟过高（700ms+）。

**Acceptance Scenarios**:

1. **[US2-1] 成功读取完整输入包**
   **Given** 指定 `bookSlug`、`chapterNumber`、以及各项数量限制  
   **When** 调用 `get_chapter_input_pack` MCP tool  
   **Then** 系统返回包含 `{recentChapters, characters, foreshadowing, emotionalDebts, volumeGoal}` 的完整数据

2. **[US2-2] 处理第一章的冷启动**
   **Given** 请求 `chapterNumber = 1`，但没有历史章节  
   **When** 调用 `get_chapter_input_pack` MCP tool  
   **Then** 系统返回 `recentChapters = []`，但仍返回角色、伏笔和 volumeGoal

3. **[US2-3] 过滤活跃伏笔**
   **Given** 数据库中有 10 个伏笔，但只有 3 个 status = 'active' 且 payoffChapter >= 当前章节  
   **When** 调用 `get_chapter_input_pack` MCP tool，设置 `maxForeshadowing = 5`  
   **Then** 系统只返回 3 个活跃伏笔

**Edge Cases**:

- **[US2-4]** bookSlug 不存在 → 返回 `{error: 'book not found'}`
- **[US2-5]** 请求的 `recentChaptersCount` 超过实际已写章节数 → 返回所有已写章节
- **[US2-6]** volumeGoal 无法推断（单卷书且无 volume_outline） → 返回 `volumeGoal = null`

---

### User Story 3 - 上下文版本追踪 (Priority: P1)

作为 **novel-agent orchestrator**，我希望能够追踪大纲修改历史并更新版本号，以便在章纲生成时检测上下文不一致并注入警告。

**Why this priority**: 避免"用户修改全书大纲后，章纲生成仍基于旧大纲"的数据漂移问题。

**Acceptance Scenarios**:

1. **[US3-1] 更新上下文版本**
   **Given** 用户修改全书大纲（changed_scope = 'book_outline'）  
   **When** 调用 `update_context_version` MCP tool  
   **Then** 系统递增 `novel_books.context_version`，写入 `novel_context_change_log` 表，返回 `{newVersion: 2}`

2. **[US3-2] 读取当前版本**
   **Given** bookSlug 存在  
   **When** 调用 `get_current_context_version` MCP tool  
   **Then** 系统返回当前 `novel_books.context_version` 值

3. **[US3-3] 变更日志记录完整**
   **Given** 多次修改大纲  
   **When** 查询 `novel_context_change_log` 表  
   **Then** 每次修改都有记录（old_version、new_version、changed_scope、change_summary、changed_at）

**Edge Cases**:

- **[US3-4]** bookSlug 不存在 → 返回错误
- **[US3-5]** change_summary 为空 → 允许（可选字段）
- **[US3-6]** changed_scope 值非法 → 拒绝并提示合法值列表

---

## Requirements

### Functional Requirements

- **FR-001**: 系统必须提供 `batch_create_book_planning` MCP tool，接收 `{bookId, outline, worldbuilding, characters[], foreshadowing[]}` 数据
- **FR-002**: `batch_create_book_planning` 必须在 PostgreSQL 事务中原子写入 4 个表（books、worldbuilding、characters、foreshadowing）
- **FR-003**: 任一表写入失败，必须回滚所有已写入数据
- **FR-004**: 系统必须提供 `get_chapter_input_pack` MCP tool，一次调用返回完整章纲输入包
- **FR-005**: `get_chapter_input_pack` 必须在 PostgreSQL 层面优化 join，减少查询次数
- **FR-006**: `get_chapter_input_pack` 必须过滤活跃伏笔（status = 'active' 且 payoffChapter >= 当前章节）
- **FR-007**: 系统必须提供 `update_context_version` MCP tool，更新 books.context_version 并记录变更日志
- **FR-008**: 系统必须提供 `get_current_context_version` MCP tool，读取 books.context_version
- **FR-009**: 系统必须新增 `human_reviews` 表，记录规划阶段的人审状态和反馈
- **FR-010**: 系统必须新增 `context_change_log` 表，记录大纲修改历史
- **FR-011**: 系统必须扩展 books 表，新增 `context_version` 字段（INTEGER，默认值 1）
- **FR-012**: 系统必须扩展 chapters 表，新增 `context_version` 字段（INTEGER，记录生成时的大纲版本）

### Non-Functional Requirements

- **NFR-001**: `batch_create_book_planning` 调用延迟 <500ms（含 PostgreSQL 事务）
- **NFR-002**: `get_chapter_input_pack` 调用延迟 <200ms（含 join 查询）
- **NFR-003**: 所有 MCP tools 必须有明确的错误处理和错误码
- **NFR-004**: PostgreSQL 事务隔离级别为 READ COMMITTED
- **NFR-005**: 所有数据库写入操作必须有明确的约束检查（NOT NULL、REFERENCES、CHECK）
- **NFR-006**: 所有表使用 `novel_` 前缀，保持与现有 schema 命名一致
- **NFR-007**: 所有外键引用 `novel_books(book_slug)`，类型为 TEXT，级联删除策略为 ON DELETE CASCADE

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 原子性 | 4 个表写入全成功或全失败 | 避免部分写入导致的数据不一致 | 集成测试验证事务回滚 | 是 |
| 性能 | 批量读取延迟 <200ms | 章纲生成是高频操作，延迟过高影响用户体验 | 压测验证延迟分布 | 否（但需在 plan 中说明优化策略） |
| 可追溯性 | 所有大纲修改都有日志记录 | 便于调试上下文漂移问题 | 手动验证 context_change_log 表 | 是 |

### Key Entities

- **BatchBookPlanningData**: 批量写入的数据结构（bookSlug, outline, worldbuilding, characters[], foreshadowing[]）
- **ChapterInputPackParams**: 输入包请求参数（bookSlug, chapterNumber, recentChaptersCount, maxCharacters, maxForeshadowing, maxEmotionalDebts）
- **ChapterInputPack**: 输入包数据结构（recentChapters, characters, foreshadowing, emotionalDebts, volumeGoal）
- **HumanReview**: 人审记录（book_slug, stage, target_id, status, reviewer_notes, feedback, approved_at）
- **ContextChangeLog**: 变更日志（book_slug, old_version, new_version, changed_scope, change_summary, changed_at）

**注意**：所有实体引用书籍时使用 `bookSlug` (TEXT)，而非 `bookId` (UUID)，与现有 `novel_books` 主键一致。

---

## Out of Scope

- **章纲生成的 LLM 调用逻辑**：留给 agents 仓库的 novel-agent orchestrator
- **人审门禁的交互界面**：留给 agents 仓库或后续 UI feature
- **历史版本的 diff 和回滚**：当前只记录版本号，不支持版本对比
- **多书并发写入的冲突检测**：当前假设单书单线程规划

---

## API Specifications

### 1. batch_create_book_planning

**输入**（JSON）：
```json
{
  "bookSlug": "string",
  "outline": {
    "storyArc": "string",
    "mainCharacters": ["string"],
    "coreConflicts": ["string"],
    "estimatedChapters": 100,
    "styleProfileId": "uuid (optional)"
  },
  "worldbuilding": {
    "rules": "string",
    "history": "string",
    "magicSystem": "string (optional)"
  },
  "characters": [
    {
      "name": "string",
      "role": "string",
      "personality": "string",
      "secondaryInterpretation": "string",
      "behaviorProhibitions": ["string"]
    }
  ],
  "foreshadowing": [
    {
      "title": "string",
      "plantChapter": 1,
      "reminderChapter": 5,
      "payoffChapter": 10,
      "priority": "high | medium | low"
    }
  ]
}
```

**输出**（JSON）：
```json
{
  "success": true
}
```

**错误输出**：
```json
{
  "success": false,
  "errors": ["error message 1", "error message 2"]
}
```

**幂等性保证**：
- 检查 `novel_books(book_slug)` 是否存在
- 检查 `novel_worldbuilding`、`novel_characters`、`novel_foreshadowing` 是否已有该 book_slug 的记录
- 如果已存在规划数据，返回 `{"success": false, "errors": ["book planning already exists"]}`

---

### 2. get_chapter_input_pack

**输入**（JSON）：
```json
{
  "bookSlug": "string",
  "chapterNumber": 10,
  "recentChaptersCount": 3,
  "maxCharacters": 5,
  "maxForeshadowing": 3,
  "maxEmotionalDebts": 2
}
```

**输出**（JSON）：
```json
{
  "recentChapters": [
    {
      "chapterNumber": 9,
      "title": "string",
      "summary": "string",
      "contextVersion": 1
    }
  ],
  "characters": [
    {
      "name": "string",
      "role": "string",
      "personality": "string",
      "secondaryInterpretation": "string",
      "behaviorProhibitions": ["string"]
    }
  ],
  "foreshadowing": [
    {
      "title": "string",
      "plantChapter": 1,
      "reminderChapter": 5,
      "payoffChapter": 10,
      "priority": "high",
      "status": "active"
    }
  ],
  "emotionalDebts": [
    {
      "description": "string",
      "sourceChapter": 7,
      "involvedCharacters": ["string"]
    }
  ],
  "volumeGoal": "string (optional)"
}
```

**数据提取逻辑**：
- `emotionalDebts`：从最近 N 章的 `novel_chapters.residue.emotionalDebts` 聚合提取
- `volumeGoal`：从 `novel_volume_outlines` 根据 `chapterNumber` 推断当前卷，返回对应卷的 `goal` 字段

---

### 3. update_context_version

**输入**（JSON）：
```json
{
  "bookSlug": "string",
  "changedScope": "book_outline | volume_outline | characters | foreshadowing",
  "changeSummary": "string (optional)"
}
```

**输出**（JSON）：
```json
{
  "newVersion": 2
}
```

---

### 4. get_current_context_version

**输入**（JSON）：
```json
{
  "bookSlug": "string"
}
```

**输出**（JSON）：
```json
{
  "contextVersion": 2
}
```

---

## Database Schema Changes

### 新增表：novel_worldbuilding

```sql
CREATE TABLE novel_worldbuilding (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
  rules TEXT NOT NULL,
  history TEXT NOT NULL,
  magic_system TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(book_slug)
);

CREATE INDEX idx_novel_worldbuilding_book ON novel_worldbuilding(book_slug);
```

---

### 新增表：novel_characters

```sql
CREATE TABLE novel_characters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
  name TEXT NOT NULL,
  role TEXT NOT NULL,
  personality TEXT NOT NULL,
  secondary_interpretation TEXT,
  behavior_prohibitions TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(book_slug, name)
);

CREATE INDEX idx_novel_characters_book ON novel_characters(book_slug);
```

---

### 新增表：novel_foreshadowing

```sql
CREATE TABLE novel_foreshadowing (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
  title TEXT NOT NULL,
  plant_chapter INTEGER NOT NULL,
  reminder_chapter INTEGER,
  payoff_chapter INTEGER NOT NULL,
  priority VARCHAR(10) NOT NULL CHECK (priority IN ('high', 'medium', 'low')),
  status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'resolved')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(book_slug, title)
);

CREATE INDEX idx_novel_foreshadowing_book_status_payoff ON novel_foreshadowing(book_slug, status, payoff_chapter);
```

---

### 新增表：novel_volume_outlines

```sql
CREATE TABLE novel_volume_outlines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
  volume_number INTEGER NOT NULL,
  goal TEXT NOT NULL,
  start_chapter INTEGER NOT NULL,
  end_chapter INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(book_slug, volume_number)
);

CREATE INDEX idx_novel_volume_outlines_book ON novel_volume_outlines(book_slug);
```

---

### 新增表：novel_human_reviews

```sql
CREATE TABLE novel_human_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
  stage VARCHAR(50) NOT NULL CHECK (stage IN ('concept', 'outline', 'volume', 'chapter')),
  target_id UUID,  -- volume_id 或 chapter_id（可选）
  status VARCHAR(20) NOT NULL CHECK (status IN ('pending_review', 'approved', 'rejected')),
  reviewer_notes TEXT,
  feedback JSONB,  -- 结构化反馈（用于再生成）
  approved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_novel_human_reviews_book_stage ON novel_human_reviews(book_slug, stage);
```

---

### 新增表：novel_context_change_log

```sql
CREATE TABLE novel_context_change_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
  old_version INTEGER NOT NULL,
  new_version INTEGER NOT NULL,
  changed_scope VARCHAR(50) NOT NULL CHECK (changed_scope IN ('book_outline', 'volume_outline', 'characters', 'foreshadowing')),
  change_summary TEXT,
  changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_novel_context_change_log_book ON novel_context_change_log(book_slug, changed_at DESC);
```

---

### 字段扩展：novel_books 表

```sql
ALTER TABLE novel_books ADD COLUMN context_version INTEGER DEFAULT 1;
```

---

### 字段扩展：novel_chapters 表

```sql
ALTER TABLE novel_chapters ADD COLUMN context_version INTEGER;
ALTER TABLE novel_chapters ADD COLUMN residue JSONB;
```

**residue 字段说明**：
存储章节生成时产生的残留上下文，用于后续章节的情感债提取。结构参见决策 2。

---

## Cross-Repository Dependency

**依赖方**: agents 仓库 `novel-agent-book-planning` feature  
**接口契约**: agents 仓库的 `NovelRepositoryPort` 将扩展以下方法：

```typescript
export interface NovelRepositoryPort {
  // ... 现有方法
  
  batchCreateBookPlanning(data: BatchBookPlanningData): Promise<void>;
  getChapterInputPack(params: ChapterInputPackParams): Promise<ChapterInputPack>;
  updateContextVersion(bookSlug: string, changedScope: string): Promise<{ newVersion: number }>;
  getCurrentContextVersion(bookSlug: string): Promise<number>;
}
```

agents 仓库的 `HermesDbNovelRepository` 将实现这些方法，调用本 feature 提供的 MCP tools。

**重要变更**：所有接口方法使用 `bookSlug` (string) 作为书籍标识符，而非 `bookId` (UUID)，与 hermes-db 现有 schema 一致。

---

## Clarified Decisions

### 决策 1：事务边界 ✅

**结论**：所有 4 个表的写入必须在单个 PostgreSQL 事务中完成。

**理由**：
- 避免部分写入失败导致的数据不一致
- PostgreSQL 原生支持 ACID 事务
- MCP tool 内部封装事务逻辑，外部调用者无需关心

---

### 决策 2：情感债的数据来源 ✅

**结论**：扩展 `novel_chapters` 表，新增 `residue JSONB` 字段。

**理由**：
- 当前 hermes-db schema 中 `novel_chapters` 表没有 `residue` 字段
- 需要扩展此字段以支持情感债提取
- MVP 阶段从 `novel_chapters.residue` 提取，避免新增独立表

**residue 字段结构**：
```json
{
  "emotionalDebts": [
    {
      "description": "角色 A 对角色 B 的未了心结",
      "involvedCharacters": ["角色A", "角色B"]
    }
  ],
  "unsolvedTensions": ["未解决的冲突线索"],
  "lingeringMoods": ["本章残留的情绪基调"]
}
```

**数据流**：
1. 章节内容生成时，LLM 提取 `residue` 并写入 `novel_chapters.residue`
2. `get_chapter_input_pack` 从最近 N 章的 `residue.emotionalDebts` 聚合返回

---

### 决策 3：volumeGoal 的推断逻辑 ✅

**结论**：从 `novel_volume_outlines` 表读取当前卷的 goal 字段。

**理由**：
- 单卷书：volumeGoal 为 null 或等于 bookOutline
- 多卷书：根据 chapterNumber 推断当前卷，返回对应卷的 goal

---

### 决策 4：表命名策略 ✅

**结论**：所有新表使用 `novel_` 前缀，保持与现有 schema 一致。

**理由**：
- 现有表使用 `novel_books`、`novel_chapters` 命名
- 避免双轨并存（有前缀表和无前缀表混用）
- API 层（MCP tools）仍使用简写（books/chapters），内部映射到带前缀的表名

**表名映射**：
- `books` → `novel_books`
- `chapters` → `novel_chapters`
- `worldbuilding` → `novel_worldbuilding`
- `characters` → `novel_characters`
- `foreshadowing` → `novel_foreshadowing`
- `volume_outlines` → `novel_volume_outlines`
- `human_reviews` → `novel_human_reviews`
- `context_change_log` → `novel_context_change_log`

---

### 决策 5：主键和外键策略 ✅

**结论**：所有新表的 `book_id` 字段引用 `novel_books(book_slug)`，类型为 TEXT。

**理由**：
- 现有 `novel_books` 主键是 `book_slug` (TEXT)，不是 UUID
- 所有现有表（novel_chapters、novel_style_profiles）的外键都引用 `book_slug`
- 保持外键引用一致性

**外键约束统一格式**：
```sql
book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE
```

---

### 决策 6：幂等性实现策略 ✅

**结论**：`batch_create_book_planning` 的幂等性检查分两步：

1. **检查 book_slug 是否已存在于 novel_books**
2. **检查是否已有规划数据**（novel_worldbuilding、novel_characters、novel_foreshadowing 任一表有记录）

**理由**：
- 单纯检查 book_slug 存在不够充分（可能只有书籍元数据，但没有规划数据）
- 单纯检查规划表不够安全（可能 book_slug 被删除后重建，导致孤儿记录）

**实现逻辑**：
```python
# 伪代码
if await db.exists("SELECT 1 FROM novel_books WHERE book_slug = $1", book_slug):
    # 检查是否已有规划数据
    has_planning = await db.exists("""
        SELECT 1 FROM novel_worldbuilding WHERE book_slug = $1
        UNION ALL
        SELECT 1 FROM novel_characters WHERE book_slug = $1 LIMIT 1
        UNION ALL
        SELECT 1 FROM novel_foreshadowing WHERE book_slug = $1 LIMIT 1
    """, book_slug)
    
    if has_planning:
        return {"success": False, "errors": ["book planning already exists"]}
```

---

### 决策 7：规模与性能目标 ✅

**结论**：系统按以下规模设计：

| 维度 | 数量级 | 依据 |
|------|--------|------|
| 章纲生成 QPS | 0.1-0.5 QPS | 单书串行规划，非高频场景 |
| 并发书籍数 | 1-3 本 | MVP 阶段单用户，未来扩展到多用户 |
| 单书章节数 | 50-200 章 | 网文典型规模 |
| 单书角色数 | 10-50 个 | 主要角色 + 配角 |
| 单书伏笔数 | 20-100 个 | 短期伏笔 + 长线伏笔 |

**性能目标调整**：
- `batch_create_book_planning`：<500ms（不变）
- `get_chapter_input_pack`：<200ms（不变，但索引策略按低 QPS 优化）
- 不引入 Redis 缓存（规模不需要）

**索引策略**：
- 主键和外键自动索引
- `novel_foreshadowing(book_slug, status, payoff_chapter)` 复合索引（支持活跃伏笔过滤）
- `novel_chapters(book_slug, chapter_number)` 复合索引（支持最近章节查询）

---

## Architecture Risks & Mitigations

### 风险 1：PostgreSQL 事务超时 ⚠️ 中严重性

**风险描述**：
- 4 个表的批量写入可能耗时较长（特别是 foreshadowing 数组很大时）
- PostgreSQL 默认事务超时 30s，可能触发超时

**缓解方案**：
- 限制 foreshadowing 数组最大长度（100 个）
- 使用批量 INSERT 语句（单条语句插入多行）
- 监控事务耗时，超时前提前返回错误

---

### 风险 2：join 查询性能瓶颈 ⚠️ 低严重性

**风险描述**：
- `get_chapter_input_pack` 需要 join 5 个表（chapters、characters、foreshadowing、emotional_debts、volume_outlines）
- 数据量大时可能导致查询延迟

**缓解方案**：
- 在关键字段上建立索引（book_id、chapter_number、status）
- 使用 PostgreSQL EXPLAIN ANALYZE 分析查询计划
- 考虑引入 Redis 缓存（后续优化）

---

## Stage Readiness

- **当前阶段**: `clarify` ✅ 已完成
- **已澄清决策**：
  1. ✅ 事务边界（PostgreSQL 单一事务）
  2. ✅ 情感债数据来源（扩展 novel_chapters.residue JSONB）
  3. ✅ volumeGoal 推断逻辑（从 novel_volume_outlines 读取）
  4. ✅ 表命名策略（所有表使用 novel_ 前缀）
  5. ✅ 主键和外键策略（引用 novel_books(book_slug) TEXT）
  6. ✅ 幂等性实现（检查 book_slug + 检查规划数据存在性）
  7. ✅ 规模与性能目标（0.1-0.5 QPS，单书串行）
- **已补充完整定义**：
  - novel_worldbuilding 表结构
  - novel_characters 表结构
  - novel_foreshadowing 表结构
  - novel_volume_outlines 表结构
  - novel_human_reviews 表结构
  - novel_context_change_log 表结构
  - novel_chapters.residue JSONB 字段结构
- **下一步建议**: `plan`（设计技术方案、模块边界、事务实现策略）
- **阻塞项**：无
- **跨仓库影响**：agents 仓库的 `NovelRepositoryPort` 需要使用 `bookSlug` (string) 而非 `bookId` (UUID)
