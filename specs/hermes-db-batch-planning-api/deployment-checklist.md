# Deployment Checklist: hermes-db-batch-planning-api

**Feature**: `hermes-db-batch-planning-api`  
**Migration**: `0008_novel_planning_tables`  
**Date**: 2026-06-16

---

## 🔴 部署前必做

### 1. 构建并推送镜像

```bash
# 方式 1: 本地构建（仅用于测试）
cd packages/hermes-db
docker build -t ghcr.io/northseacoder/hermes-db-mcp:latest .

# 方式 2: Git tag 触发 CI 构建（推荐）
git tag hermes-db-v0.2.18
git push origin hermes-db-v0.2.18
# GitHub Actions 会自动构建并推送到 ghcr.io
```

**Version 建议**: `v0.2.18`（假设当前最新是 v0.2.17，根据实际调整）

---

### 2. 执行 Migration（生产环境）

```bash
# NAS 部署时执行
cd /path/to/mcps/deploy
docker compose -f services/hermes-db.yml pull
docker compose -f services/hermes-db.yml run --rm --entrypoint alembic hermes-db-mcp upgrade head
docker compose -f services/hermes-db.yml up -d hermes-db-mcp
```

**预期输出**:
```
INFO  [alembic.runtime.migration] Running upgrade 0007_novel_agent_books_chapters -> 0008_novel_planning_tables
```

**Migration 内容**:
- 新增 6 个表：novel_worldbuilding, novel_characters, novel_foreshadowing, novel_volume_outlines, novel_human_reviews, novel_context_change_log
- 扩展 2 个表：novel_books (+context_version), novel_chapters (+context_version, +residue)
- 创建 9 个索引（含复合索引 idx_novel_foreshadowing_book_status_payoff）

---

### 3. 验证部署（生产环境）

#### 3.1 健康检查

```bash
# 调用 MCP health tool
# 期望返回
{
  "schema_revision": "0008_novel_planning_tables",
  "capabilities": {
    "novel_agent_books_chapters": true
  }
}
```

#### 3.2 工具列表检查

```bash
# 调用 MCP tools/list
# 确认包含以下 4 个新工具：
- batch_create_book_planning
- get_chapter_input_pack
- update_context_version
- get_current_context_version
```

#### 3.3 Smoke Test（可选）

```bash
# 在 agents 仓库调用新 MCP tools
# 验证基本功能（需要 agents 仓库先同步 bookId→bookSlug 接口变更）
```

---

## 🟡 本地开发验证（可选）

### 1. 启动本地依赖

```bash
# 方式 1: Docker Compose（如果有本地 PG/Redis compose）
docker compose -f /path/to/postgres-redis-compose.yml up -d

# 方式 2: 手动启动 PostgreSQL 和 Redis
# macOS (Homebrew)
brew services start postgresql@14
brew services start redis

# 或使用容器
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:14
docker run -d --name redis -p 6379:6379 redis:7
```

### 2. 配置环境变量

```bash
cd packages/hermes-db
cp .env.example .env
# 编辑 .env，确保 PG_DSN 和 REDIS_URL 指向本地服务
```

### 3. 执行 Migration（本地）

```bash
cd packages/hermes-db
source .venv/bin/activate
alembic upgrade head
```

### 4. 运行集成测试

```bash
# 按照 tests/integration_test_guide.md 执行 8 步验证
cd packages/hermes-db
source .venv/bin/activate

# Step 1: 验证 Migration
alembic current
# 应显示: 0008_novel_planning_tables (head)

# Step 2-7: 手动执行集成测试
# 详见 tests/integration_test_guide.md
```

---

## 🟢 跨仓库协调（agents 仓库）

### 通知 agents 仓库团队

**接口变更**: `bookId: string` → `bookSlug: string`

**影响文件**:
- `agents/src/repositories/novel_repository_port.ts`
- `agents/src/repositories/hermes_db_novel_repository.ts`
- `agents/src/orchestrators/novel_agent_orchestrator.ts`
- 所有测试文件

**协调文档**: `specs/hermes-db-batch-planning-api/cross-repo-coordination.md`

**迁移步骤**:
1. agents 仓库搜索所有 `bookId` 引用
2. 批量替换为 `bookSlug`（TypeScript 接口用 camelCase）
3. 更新 MCP tool 调用参数（使用 snake_case `book_slug`）
4. 运行 agents 仓库测试
5. 两个仓库集成测试

---

## 📋 验证清单

### 生产部署验证

- [ ] Migration 执行成功（无错误输出）
- [ ] `health()` 返回 `schema_revision: "0008_novel_planning_tables"`
- [ ] `tools/list` 包含 4 个新 MCP tools
- [ ] 数据库中存在 8 个新表/扩展表
- [ ] 数据库中存在 9 个新索引
- [ ] 服务可正常启动（无 crash loop）

### 功能验证（可选，需 agents 仓库配合）

- [ ] `batch_create_book_planning` 可正常调用
- [ ] 事务回滚机制工作正常
- [ ] 幂等性检查生效
- [ ] `get_chapter_input_pack` 可正常返回数据
- [ ] 性能指标达标（<500ms batch write, <200ms join query）

### 跨仓库协调验证

- [ ] agents 仓库已收到接口变更通知
- [ ] agents 仓库已创建对应 issue/PR
- [ ] agents 仓库接口变更已完成
- [ ] 两个仓库集成测试通过

---

## 🔄 回滚步骤（如需回滚）

```bash
# 1. 回滚 Migration
docker compose -f services/hermes-db.yml run --rm --entrypoint alembic hermes-db-mcp downgrade 0007_novel_agent_books_chapters

# 2. 重启服务使用旧镜像
docker compose -f services/hermes-db.yml down
docker compose -f services/hermes-db.yml up -d

# 注意：回滚会删除 8 个表及其中的所有数据，务必先备份
```

---

## 📝 部署日志模板

```
部署时间: __________
执行人: __________
环境: 生产 / 测试
版本: hermes-db-v0.2.18

Migration 执行:
- [ ] 执行成功
- [ ] 执行时间: __________
- [ ] 错误信息: __________

健康检查:
- [ ] schema_revision 正确
- [ ] capabilities 正确
- [ ] tools/list 包含新工具

Smoke Test:
- [ ] 已执行
- [ ] 结果: 通过 / 失败
- [ ] 备注: __________

跨仓库协调:
- [ ] 已通知 agents 仓库
- [ ] agents 仓库 issue: __________
- [ ] 集成测试状态: __________
```

---

## 🎯 成功标准

1. ✅ Migration 执行成功，无错误
2. ✅ `health()` 返回正确的 schema_revision 和 capabilities
3. ✅ 4 个新 MCP tools 可被正常调用
4. ✅ 服务稳定运行（无 crash，日志无异常）
5. ✅ agents 仓库已知晓接口变更（可延后，但需记录）

**最低通过线**: 前 4 项必须全部通过，第 5 项可标记为延后。
