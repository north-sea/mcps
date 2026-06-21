# Hermes-db Integration

**HermesDbClient** 通过 HTTP 调用 hermes-db MCP server，实现 workflow artifact 读取和 wechat_articles ledger 写入。

---

## 架构设计

```
wechat-draft MCP (NAS)
    ↓ HTTP Client (fetch)
hermes-db MCP HTTP API (nas.local:8765/mcp)
    ↓ PostgreSQL
hermes database
```

**优势**：
- ✅ 松耦合：不需要数据库凭据
- ✅ 复用现有能力：hermes-db MCP 已有完整的 artifact/ledger 工具
- ✅ 类型安全：直接使用 hermes-db MCP 的工具定义

---

## 配置

### 环境变量

```bash
# Hermes-db MCP HTTP endpoint
HERMES_DB_BASE_URL=http://nas.local:8765

# Optional: 超时时间（毫秒）
HERMES_DB_TIMEOUT_MS=10000

# Optional: Bearer token（如果 hermes-db 需要认证）
HERMES_DB_AUTH_TOKEN=your_token_here
```

### 配置加载

`ConfigLoader` 自动从环境变量加载配置：

```typescript
hermes_db: {
  base_url: process.env.HERMES_DB_BASE_URL || 'http://nas.local:8765',
  timeout_ms: parseInt(process.env.HERMES_DB_TIMEOUT_MS || '10000', 10),
  auth_token: process.env.HERMES_DB_AUTH_TOKEN,
}
```

---

## 使用的 hermes-db MCP 工具

### 1. `mcp__hermes-db__get_workflow_artifact_content`

**用途**: 读取 publish-ready artifact

**参数**:
```json
{
  "artifact_id": "article_20260621_001"
}
```

**返回**:
```json
{
  "artifact": {
    "artifact_id": "article_20260621_001",
    "run_id": "run_123",
    "account": "weiyuchengchun",
    "stage": "publish_ready",
    "type": "wechat_api_article",
    "content_text": "<p>正文内容...</p>",
    "metadata": {
      "title": "文章标题",
      "publish_ready": true,
      "wechat_asset_manifest": {
        "ready": true,
        "cover_thumb_media_id": "xxx",
        "body_wechat_image_urls": ["https://mmbiz.qpic.cn/..."]
      }
    },
    "created_at": "2026-06-21T10:00:00Z"
  }
}
```

### 2. `mcp__hermes-db__upsert_wechat_article`

**用途**: 写入草稿状态到 wechat_articles ledger

**参数**:
```json
{
  "publication_idempotency_key": "weiyuchengchun_20260621_001",
  "account": "weiyuchengchun",
  "run_id": "run_123",
  "status": "drafted",
  "draft_artifact_id": "article_20260621_001",
  "title": "文章标题",
  "metadata": {
    "wechat_media_id": "xxx_media_id_from_wechat",
    "draft_created_at": "2026-06-21T15:00:00Z"
  }
}
```

**返回**: 成功或错误信息

### 3. `mcp__hermes-db__health`

**用途**: 健康检查

**参数**: `{}`

**返回**:
```json
{
  "status": "ok"
}
```

---

## HTTP 调用实现

### 请求格式

```http
POST http://nas.local:8765/mcp/tools/call
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN_HERE (optional)

{
  "name": "mcp__hermes-db__get_workflow_artifact_content",
  "arguments": {
    "artifact_id": "article_20260621_001"
  }
}
```

### 响应格式

**成功**:
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"artifact\": {...}}"
    }
  ]
}
```

**错误**:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Artifact not found"
  }
}
```

---

## HermesDbClient 实现

### 核心方法

```typescript
class HermesDbClient {
  // 调用 hermes-db MCP 工具（私有方法）
  private async callTool<T>(toolName: string, args: Record<string, any>): Promise<T>

  // 读取 artifact
  async getArtifact(artifactId: string): Promise<WorkflowArtifact | null>

  // 写入 ledger
  async upsertArticleLedger(update: ArticleLedgerUpdate): Promise<void>

  // 健康检查
  async health(): Promise<{ ok: boolean; error?: string }>
}
```

### 错误处理

1. **超时**: 10 秒后自动取消请求（可配置）
2. **Artifact 未找到**: 返回 `null` 而非抛出错误
3. **Ledger 写入失败**: 记录警告但重新抛出错误，由调用方决定是否继续
4. **网络错误**: 抛出描述性错误信息

---

## 使用示例

### 在 DraftWorkflow 中使用

```typescript
// 读取 artifact
const artifact = await hermesDbClient.getArtifact(ctx.artifactId);
if (!artifact) {
  return createFailedJob(ctx, 'artifact_not_found', 'Artifact not found in hermes-db');
}

// 写入 ledger（成功后）
try {
  await hermesDbClient.upsertArticleLedger({
    publication_idempotency_key: ctx.idempotencyKey,
    account: ctx.account,
    run_id: artifact.run_id,
    status: 'drafted',
    draft_artifact_id: ctx.artifactId,
    title: job.title || 'Untitled',
    metadata: {
      wechat_media_id: mediaId,
      draft_created_at: job.created_at,
    },
  });
} catch (error) {
  // Ledger 更新失败不阻塞草稿创建
  console.warn('[DraftWorkflow] Ledger update failed, draft still created:', error);
}
```

---

## 故障排查

### 1. 连接失败

**症状**: `Failed to get artifact: HTTP 500` 或超时

**检查**:
```bash
# 检查 hermes-db 是否运行
curl http://nas.local:8765/health

# 检查 MCP endpoint
curl -X POST http://nas.local:8765/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name":"mcp__hermes-db__health","arguments":{}}'
```

### 2. 认证失败

**症状**: `HTTP 401: Unauthorized`

**解决**: 设置 `HERMES_DB_AUTH_TOKEN` 环境变量

### 3. Artifact 未找到

**症状**: `getArtifact` 返回 `null`

**检查**: artifact_id 是否存在，stage 是否为 `publish_ready`

### 4. Ledger 写入失败

**症状**: 草稿创建成功但控制台有警告

**影响**: 不影响草稿创建，但 hermes-db 中没有记录

**检查**: hermes-db 日志、数据库连接、字段校验

---

## 与旧实现的对比

### Phase 1 (骨架实现)

```typescript
async getArtifact(artifactId: string) {
  // TODO: 调用 hermes-db MCP
  return null;
}

async upsertArticleLedger(update: ArticleLedgerUpdate) {
  throw new Error('Not yet implemented');
}
```

### Phase 2 (HTTP 集成)

```typescript
async getArtifact(artifactId: string) {
  const result = await this.callTool<{ artifact: WorkflowArtifact | null }>(
    'mcp__hermes-db__get_workflow_artifact_content',
    { artifact_id: artifactId }
  );
  return result?.artifact || null;
}

async upsertArticleLedger(update: ArticleLedgerUpdate) {
  await this.callTool('mcp__hermes-db__upsert_wechat_article', {
    publication_idempotency_key: update.publication_idempotency_key,
    account: update.account,
    run_id: update.run_id,
    status: update.status,
    draft_artifact_id: update.draft_artifact_id,
    title: update.title,
    metadata: update.metadata,
  });
}
```

---

## 测试

### 健康检查

```bash
# 在 wechat-draft MCP 启动后
export HERMES_DB_BASE_URL=http://nas.local:8765
export HERMES_DB_AUTH_TOKEN=your_token

# 通过 MCP 工具调用
wechat_get_draft_status(job_id="test")  # 内部会初始化 HermesDbClient
```

### 端到端测试

```bash
# 1. 创建 publish-ready artifact（通过 hermes-db）
# 2. 调用 wechat_create_draft
# 3. 检查 hermes-db 中的 wechat_articles 记录
```

---

## 未来优化

1. **连接池**: 复用 HTTP 连接（当前每次 `fetch` 新建连接）
2. **重试机制**: 网络临时故障时自动重试
3. **批量操作**: 支持批量读取 artifact 或批量写入 ledger
4. **缓存**: 短期缓存 artifact（减少重复查询）
5. **Metrics**: 导出请求延迟、成功率等监控指标
