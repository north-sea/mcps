# Cross-Repository Coordination: agents 仓库接口变更

## T018: 通知 agents 仓库接口变更

本文件记录需要在 agents 仓库中同步的接口变更。

---

## 接口变更摘要

**变更类型**: 参数类型变更  
**影响范围**: `NovelRepositoryPort` 接口  
**变更原因**: hermes-db 使用 `book_slug` (TEXT) 作为主键，而非 `bookId` (UUID)

---

## 需要修改的接口

### 文件：`agents/src/repositories/novel_repository_port.ts`

**变更前**：

```typescript
export interface NovelRepositoryPort {
  // ... 现有方法
  
  batchCreateBookPlanning(data: BatchBookPlanningData): Promise<void>;
  getChapterInputPack(params: ChapterInputPackParams): Promise<ChapterInputPack>;
  updateContextVersion(bookId: string, changedScope: string): Promise<{ newVersion: number }>;
  getCurrentContextVersion(bookId: string): Promise<number>;
}

export interface BatchBookPlanningData {
  bookId: string;  // ❌ 需要改为 bookSlug
  outline: BookOutline;
  worldbuilding: Worldbuilding;
  characters: Character[];
  foreshadowing: Foreshadowing[];
}

export interface ChapterInputPackParams {
  bookId: string;  // ❌ 需要改为 bookSlug
  chapterNumber: number;
  recentChaptersCount?: number;
  maxCharacters?: number;
  maxForeshadowing?: number;
  maxEmotionalDebts?: number;
}
```

**变更后**：

```typescript
export interface NovelRepositoryPort {
  // ... 现有方法
  
  batchCreateBookPlanning(data: BatchBookPlanningData): Promise<void>;
  getChapterInputPack(params: ChapterInputPackParams): Promise<ChapterInputPack>;
  updateContextVersion(bookSlug: string, changedScope: string): Promise<{ newVersion: number }>;  // ✅ bookId → bookSlug
  getCurrentContextVersion(bookSlug: string): Promise<number>;  // ✅ bookId → bookSlug
}

export interface BatchBookPlanningData {
  bookSlug: string;  // ✅ bookId → bookSlug, 类型保持 string
  outline: BookOutline;
  worldbuilding: Worldbuilding;
  characters: Character[];
  foreshadowing: Foreshadowing[];
}

export interface ChapterInputPackParams {
  bookSlug: string;  // ✅ bookId → bookSlug, 类型保持 string
  chapterNumber: number;
  recentChaptersCount?: number;
  maxCharacters?: number;
  maxForeshadowing?: number;
  maxEmotionalDebts?: number;
}
```

---

## 需要修改的实现

### 文件：`agents/src/repositories/hermes_db_novel_repository.ts`

**变更位置**：所有调用 MCP tools 的地方

**示例**：

```typescript
// 变更前
async batchCreateBookPlanning(data: BatchBookPlanningData): Promise<void> {
  await this.mcpClient.call("batch_create_book_planning", {
    bookId: data.bookId,  // ❌
    outline: data.outline,
    worldbuilding: data.worldbuilding,
    characters: data.characters,
    foreshadowing: data.foreshadowing,
  });
}

// 变更后
async batchCreateBookPlanning(data: BatchBookPlanningData): Promise<void> {
  await this.mcpClient.call("batch_create_book_planning", {
    book_slug: data.bookSlug,  // ✅ 参数名改为 book_slug（snake_case）
    outline: data.outline,
    worldbuilding: data.worldbuilding,
    characters: data.characters,
    foreshadowing: data.foreshadowing,
  });
}
```

**注意**：MCP tool 参数使用 `snake_case`（`book_slug`），TypeScript 接口使用 `camelCase`（`bookSlug`）。

---

## 影响分析

### 受影响的 agents 仓库文件

1. `src/repositories/novel_repository_port.ts`（接口定义）
2. `src/repositories/hermes_db_novel_repository.ts`（实现）
3. `src/orchestrators/novel_agent_orchestrator.ts`（调用方，如果直接使用 bookId）
4. 所有测试文件（`*.test.ts`）

### 向后兼容性

❌ **不兼容变更**：agents 仓库必须同步更新，否则会出现参数不匹配错误。

---

## 迁移步骤

### Step 1: 在 agents 仓库中搜索所有 `bookId` 引用

```bash
cd agents
grep -r "bookId" src/repositories/
grep -r "bookId" src/orchestrators/
```

### Step 2: 批量替换

```bash
# 接口和类型定义
sed -i '' 's/bookId: string/bookSlug: string/g' src/repositories/novel_repository_port.ts

# MCP tool 调用（需要手动检查，因为参数名是 snake_case）
# 手动修改 hermes_db_novel_repository.ts
```

### Step 3: 更新测试

所有使用 `bookId` 的测试数据需要改为 `bookSlug`。

### Step 4: 验证

```bash
# 类型检查
npm run type-check

# 运行测试
npm test
```

---

## 协调时间线

1. **本 PR 合并前**：通知 agents 仓库团队（如果是跨团队）
2. **本 PR 合并后**：agents 仓库同步更新接口
3. **agents 仓库更新完成前**：agents 仓库的 novel-agent-book-planning feature 无法使用新的 MCP tools

---

## 联系人

- **hermes-db 负责人**: _______________
- **agents 仓库负责人**: _______________
- **协调日期**: _______________

---

## Checklist

- [ ] 已通知 agents 仓库团队
- [ ] agents 仓库已创建对应 issue/PR
- [ ] agents 仓库接口变更已完成
- [ ] agents 仓库测试通过
- [ ] 两个仓库的集成测试通过
