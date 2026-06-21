# Quick Start Guide

本指南帮助你快速配置和测试 wechat-draft MCP。

---

## 1. 配置环境变量

### 创建 .env 文件

```bash
cd /Users/yqg/personal/AI/mcps/packages/wechat-draft
cp .env.example .env
```

### 编辑 .env 文件

```bash
# 必需配置
HERMES_DB_BASE_URL=http://nas.local:8765
HERMES_DB_AUTH_TOKEN=your_actual_hermes_token

WECHAT_ADAPTER_BASE_URL=http://100.117.14.128:3000
WECHAT_ADAPTER_AUTH_TOKEN=your_actual_adapter_token

# 可选配置
WECHAT_DRAFT_RUNTIME_PATH=/tmp/wechat-draft
```

**如何获取 tokens**:
- `HERMES_DB_AUTH_TOKEN`: hermes-db MCP 的认证 token
- `WECHAT_ADAPTER_AUTH_TOKEN`: ECS adapter 的认证 token（在 ECS `.env` 中配置的 `ADAPTER_AUTH_TOKEN`）

---

## 2. 测试 HermesDbClient

### 基础测试

```bash
cd /Users/yqg/personal/AI/mcps/packages/wechat-draft

# 设置 token
export HERMES_DB_AUTH_TOKEN='your_token'

# 运行测试
node test-hermes-client.mjs
```

**预期输出**:
```
Testing HermesDbClient...
Base URL: http://nas.local:8765

1. Health check:
✅ Result: {
  "ok": true
}

2. Get artifact (non-existent):
✅ Result: null (as expected)

Tests complete.
```

### 测试真实 artifact

如果你有真实的 artifact_id：

```bash
TEST_ARTIFACT_ID='your_artifact_id' node test-hermes-client.mjs
```

---

## 3. 配置 MCP 客户端

### Claude Code

编辑 `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "wechat-draft": {
      "command": "node",
      "args": ["/Users/yqg/personal/AI/mcps/packages/wechat-draft/dist/index.js"]
    }
  }
}
```

**注意**: `.env` 文件会被自动加载，不需要在配置中重复设置环境变量。

### Codex

编辑 `~/.codex/mcp.json`:

```json
{
  "mcpServers": {
    "wechat-draft": {
      "command": "node",
      "args": ["/Users/yqg/personal/AI/mcps/packages/wechat-draft/dist/index.js"]
    }
  }
}
```

---

## 4. 验证 MCP 工具

在 Claude Code 或 Codex 中：

```javascript
// 1. 列出账号
wechat_list_accounts()

// 2. 检查 hermes-db 连接（内部会调用 health check）
wechat_validate_publish_artifact(artifact_id="test")

// 3. 创建草稿（需要真实 publish-ready artifact）
wechat_create_draft(
  account="weiyuchengchun",
  artifact_id="your_artifact_id"
)
```

---

## 5. 端到端测试流程

### 前置条件

1. **准备 publish-ready artifact**（通过上游 writing agent 或 hermes-db）:
   - `stage = "publish_ready"`
   - `type = "wechat_api_article"`
   - `metadata.publish_ready = true`
   - `metadata.wechat_asset_manifest.ready = true`
   - 封面有 `thumb_media_id`
   - 正文图片都是微信 URL（`https://mmbiz.qpic.cn/...`）

2. **ECS adapter 正常运行**:
   ```bash
   curl http://100.117.14.128:3000/health
   # 应返回: {"status":"ok",...}
   ```

3. **hermes-db MCP 正常运行**:
   ```bash
   curl http://nas.local:8765/health -H "Authorization: Bearer YOUR_TOKEN"
   # 应返回: {"status":"ok"}
   ```

### 执行流程

```javascript
// Step 1: 验证 artifact
const validation = wechat_validate_publish_artifact(
  artifact_id="article_20260621_001"
);
// 预期: success=true, 无错误

// Step 2: 创建草稿
const result = wechat_create_draft(
  account="weiyuchengchun",
  artifact_id="article_20260621_001"
);
// 预期: success=true, 返回 job_id 和 media_id

// Step 3: 查询状态
const status = wechat_get_draft_status(
  job_id=result.data.job_id
);
// 预期: status="saved", 包含 media_id

// Step 4: 在微信公众号后台查看草稿
// 登录 https://mp.weixin.qq.com -> 素材管理 -> 草稿箱
// 搜索标题或通过 media_id 定位
```

---

## 6. 故障排查

### HermesDbClient 连接失败

**症状**: `Failed to get artifact: HTTP 401` 或超时

**检查**:
```bash
# 1. 检查 hermes-db 是否运行
curl http://nas.local:8765/health

# 2. 检查 token 是否正确
curl http://nas.local:8765/health \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. 检查 .env 文件
cat .env | grep HERMES_DB
```

### Adapter 连接失败

**症状**: `Adapter unreachable` 或 `needs_operator_action`

**检查**:
```bash
# 1. 检查 adapter 是否运行
ssh ali 'docker ps | grep wechat-adapter'

# 2. 检查 Tailscale 连通性
ping 100.117.14.128

# 3. 测试 adapter health
curl http://100.117.14.128:3000/health
```

### Artifact 验证失败

**症状**: `invalid_artifact` 或 `asset_validation` 错误

**检查**:
- artifact stage 是否为 `publish_ready`
- wechat_asset_manifest.ready 是否为 `true`
- 封面是否有 `thumb_media_id`
- 正文图片 URL 是否都是 `https://mmbiz.qpic.cn/...`

---

## 7. 日志和调试

### MCP 日志

MCP stdout/stderr 会输出到 Claude Code 或 Codex 的日志中。

### Job Store 日志

```bash
# 查看 JSONL 审计日志
ls /tmp/wechat-draft/jobs/
cat /tmp/wechat-draft/jobs/2026-06-21.jsonl | jq
```

### Adapter 日志

```bash
ssh ali 'docker logs -f wechat-adapter'
```

---

## 8. 安全检查清单

- [ ] `.env` 文件存在且包含正确的 tokens
- [ ] `.env` 已添加到 `.gitignore`
- [ ] 不要在代码、日志、截图中泄露 tokens
- [ ] ECS adapter 只能通过 Tailscale 访问（不开放公网）
- [ ] hermes-db 认证已启用
- [ ] 定期轮换 tokens

---

## 9. 常见问题

**Q: .env 文件会自动加载吗？**  
A: 是的，`src/index.ts` 顶部有 `import 'dotenv/config'`，会自动加载同目录下的 `.env`。

**Q: 可以不用 .env 文件吗？**  
A: 可以，直接在 shell 中 `export` 环境变量，或在 MCP 配置中设置 `env` 字段。

**Q: 测试脚本需要 .env 吗？**  
A: 测试脚本 **不会** 自动加载 `.env`，需要手动 `export` 环境变量。

**Q: hermes-db token 在哪里查看？**  
A: 取决于 hermes-db MCP 的配置，通常在 hermes-db 的环境变量或配置文件中。

---

## 10. 下一步

完成配置和测试后，你可以：

1. **集成到 writing workflow**: 让 writing agent 输出 publish-ready artifact
2. **素材准备流程**: 实现图片上传到微信素材库的流程（Phase 2）
3. **批量操作**: 一次创建多篇草稿
4. **监控告警**: 添加 Prometheus metrics 或日志采集

---

**需要帮助？** 查看完整文档：
- [Hermes-db Integration](./hermes-db-integration.md)
- [Configuration Guide](./configuration.md)
- [Runbook](./runbook.md)
- [Error Handling](./error-handling.md)
