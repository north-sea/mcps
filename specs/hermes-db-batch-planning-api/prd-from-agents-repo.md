# mcps 仓库依赖：hermes-db-batch-planning-api

**状态**: 待启动  
**优先级**: 高（阻塞 `novel-agent-book-planning` 的 implement 阶段）  
**mcps 仓库路径**: `/Users/yqg/personal/AI/mcps`

---

## Feature Scope（mcps 仓库需实现）

### 1. batch_create_book_planning API

**功能**：批量写入书籍规划数据（4 个表），PostgreSQL 事务保证原子性。

**输入**：
```typescript
{
  bookId: string;
  outline: {
    storyArc: string;
    mainCharacters: string[];
    coreConflicts: string[];
    estimatedChapters: number;
    styleProfileId?: string;
  };
  worldbuilding: {
    rules: string;
    history: string;
    magicSystem?: string;
  };
  characters: Array<{
    name: string;
    role: string;
    personality: string;
    secondaryInterpretation: string;
    behaviorProhibitions: string[];
  }>;
  foreshadowing: Array<{
    title: string;
    plantChapter: number;
    reminderChapter: number;
    payoffChapter: number;
    priority: 'high' | 'medium' | 'low';
  }>;
}
```

**输出**：
```typescript
{
  success: boolean;
  errors?: string[];
}
```

**实现要点**：
- 使用 PostgreSQL 事务包裹 4 个表的写入（books、worldbuilding、characters、foreshadowing）
- 任一表写入失败，全部回滚
- MCP tool 名称：`batch_create_book_planning`

---

### 2. get_chapter_input_pack API

**功能**：批量读取章纲生成所需的输入包（上 N 章 + 角色 + 伏笔 + 情感债），减少 HTTP 往返。

**输入**：
```typescript
{
  bookId: string;
  chapterNumber: number;
  recentChaptersCount: number;    // 上 N 章（建议 3）
  maxCharacters: number;          // 最多角色数（建议 5）
  maxForeshadowing: number;       // 最多伏笔数（建议 3）
  maxEmotionalDebts: number;      // 最多情感债（建议 2）
}
```

**输出**：
```typescript
{
  recentChapters: Array<{
    chapterNumber: number;
    title: string;
    summary: string;
    contextVersion: number;
  }>;
  characters: Array<{
    name: string;
    role: string;
    personality: string;
    secondaryInterpretation: string;
    behaviorProhibitions: string[];
  }>;
  foreshadowing: Array<{
    title: string;
    plantChapter: number;
    reminderChapter: number;
    payoffChapter: number;
    priority: string;
    status: 'active' | 'paid_off';
  }>;
  emotionalDebts: Array<{
    description: string;
    sourceChapter: number;
    involvedCharacters: string[];
  }>;
  volumeGoal: string;  // 当前卷的目标
}
```

**实现要点**：
- 在 PostgreSQL 层面做 join 优化，一次查询返回所有数据
- 过滤逻辑：
  - recentChapters：最近 N 章（按 chapterNumber DESC）
  - characters：本章相关角色（根据 volumeOutline 推断，MVP 可返回全部角色）
  - foreshadowing：status = 'active' 且 payoffChapter >= 当前章节
  - emotionalDebts：未解决的情感线索（MVP 可从 chapters 表的 residue 字段提取）
- MCP tool 名称：`get_chapter_input_pack`

---

### 3. human_reviews 表

**Schema**：
```sql
CREATE TABLE human_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_id UUID NOT NULL REFERENCES books(id),
  stage VARCHAR(50) NOT NULL,  -- 'concept' | 'outline' | 'volume' | 'chapter'
  target_id UUID,  -- volume_id 或 chapter_id（可选，用于标识具体审核对象）
  status VARCHAR(20) NOT NULL,  -- 'pending_review' | 'approved' | 'rejected'
  reviewer_notes TEXT,
  feedback JSONB,  -- 结构化反馈（用于再生成）
  approved_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_human_reviews_book_stage ON human_reviews(book_id, stage);
```

**用途**：记录每个阶段的人审状态和反馈。

---

### 4. context_change_log 表 + 版本追踪字段

**新增表**：
```sql
CREATE TABLE context_change_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_id UUID NOT NULL REFERENCES books(id),
  old_version INTEGER NOT NULL,
  new_version INTEGER NOT NULL,
  changed_scope VARCHAR(50) NOT NULL,  -- 'book_outline' | 'volume_outline' | 'characters' | 'foreshadowing'
  change_summary TEXT,
  changed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_context_change_log_book ON context_change_log(book_id, changed_at DESC);
```

**字段扩展**：
```sql
-- books 表
ALTER TABLE books ADD COLUMN context_version INTEGER DEFAULT 1;

-- chapters 表（如果需要记录生成时的大纲版本）
ALTER TABLE chapters ADD COLUMN context_version INTEGER;
```

---

### 5. update_context_version API

**功能**：用户修改大纲时调用，更新版本号并记录变更日志。

**输入**：
```typescript
{
  bookId: string;
  changedScope: 'book_outline' | 'volume_outline' | 'characters' | 'foreshadowing';
  changeSummary?: string;
}
```

**输出**：
```typescript
{
  newVersion: number;
}
```

**实现要点**：
- 读取当前 `books.context_version`
- 更新为 `context_version + 1`
- 写入 `context_change_log` 表
- MCP tool 名称：`update_context_version`

---

## 接口契约（agents 仓库期望）

agents 仓库的 `NovelRepositoryPort` 将扩展以下方法：

```typescript
// src/domain/novel-repository-port.ts
export interface NovelRepositoryPort {
  // ... 现有方法
  
  batchCreateBookPlanning(data: BatchBookPlanningData): Promise<void>;
  getChapterInputPack(params: ChapterInputPackParams): Promise<ChapterInputPack>;
  updateContextVersion(bookId: string, changedScope: string): Promise<{ newVersion: number }>;
  getCurrentContextVersion(bookId: string): Promise<number>;
}
```

agents 仓库的 `HermesDbNovelRepository` 将实现这些方法，调用 mcps 仓库提供的 MCP tools。

---

## 启动方式

在 mcps 仓库中执行：

```bash
cd /Users/yqg/personal/AI/mcps
/sdd specify hermes-db-batch-planning-api
```

提供以上 Scope 作为需求输入。

---

## 验收标准

mcps feature 完成后，agents 仓库应能：
1. 调用 `batch_create_book_planning` 成功写入 4 个表
2. 调用 `get_chapter_input_pack` 成功获取完整输入包
3. 调用 `update_context_version` 成功更新版本号并记录日志
4. 集成测试验证事务回滚机制（模拟第 3 个表写入失败，验证前 2 个表未写入）

---

## 时间估算

- mcps feature SDD 流程：specify (0.5h) + clarify (0.5h) + plan (1h) + implement (3-4h) + verify (1h) = **6-7 小时**
- agents feature 解除阻塞后：tasks (1h) + implement (4-5h) + verify (2h) = **7-8 小时**

**总计**：13-15 小时（约 2 个工作日）
