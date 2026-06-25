# Error Handling & Operator Actions

**Feature**: `wechat-draft-mcp`  
**Date**: 2026-06-21  
**Scope**: T018 - 失败处理和人工处理建议

---

## 最终状态分类

| 状态 | 含义 | 是否需要人工介入 |
|---|---|---|
| `saved` | 草稿创建成功并保存到微信草稿箱 | ❌ 否 |
| `failed` | 创建失败（技术错误、未知错误） | ✅ 是（排查日志） |
| `invalid_artifact` | Artifact 不符合微信 API 要求 | ✅ 是（修复 artifact） |
| `needs_operator_action` | 需要运维介入（网络/权限/配置问题） | ✅ 是（按建议操作） |

---

## 错误分类与处理建议

### ✅ `saved` - 成功

**含义**: 草稿已成功创建并保存到微信草稿箱。

**Job 字段**:
- `status: "saved"`
- `media_id: "<wechat_media_id>"`
- `title: "<article_title>"`

**下一步**:
1. 用户在微信公众号后台草稿箱找到草稿
2. 人工校验内容、排版、图片
3. 手动发布或定时发布

---

### ❌ `invalid_artifact` - Artifact 不符合要求

**触发场景**:

| ErrorCode | 触发条件 | 处理建议 |
|---|---|---|
| `artifact_not_found` | `hermes.workflow_artifacts` 中找不到 artifact | 检查 artifact_id 是否正确 |
| `artifact_validation_failed` | stage/type/publish_ready/wechat_asset_manifest 不符合要求 | 修复 artifact：确保 `stage=publish_ready`, `type=wechat_api_article`, `publish_ready=true`, `wechat_asset_manifest.ready=true` |
| `wechat_asset_invalid` | 封面 `thumb_media_id` 无效或正文图片不是微信 URL | 重新上传封面素材或正文图片到微信素材库 |

**错误示例**:
```json
{
  "status": "invalid_artifact",
  "error": {
    "code": "artifact_validation_failed",
    "message": "metadata.wechat_asset_manifest.ready: wechat_asset_manifest.ready is false"
  }
}
```

**处理建议**:
1. 读取 `error.message` 中的具体字段
2. 修复上游写文 agent 或素材准备流程
3. 重新生成 artifact 后再次调用 `wechat_create_draft`

---

### ⚠️ `needs_operator_action` - 需要运维介入

**触发场景**:

| ErrorCode | 触发条件 | 处理建议 |
|---|---|---|
| `adapter_unreachable` | NAS 无法连接到 ECS adapter | 检查 Tailscale/WireGuard/SSH tunnel 状态；检查 ECS adapter 是否运行 |
| `adapter_auth_failed` | Adapter 认证失败 (401) | 检查 `WECHAT_ADAPTER_AUTH_TOKEN` 环境变量是否正确 |
| `wechat_token_invalid` | 微信 AccessToken 无效/过期 | 检查 ECS adapter 的 AppSecret 是否正确；检查 token 获取日志 |
| `wechat_rate_limit` | 微信 API 频控 (errcode 45009) | 等待一段时间后重试；避免短时间内大量调用 |
| `wechat_permission_denied` | 公众号权限不足 (errcode 48001) | 检查公众号是否有草稿管理权限；检查是否为服务号 |

**错误示例**:
```json
{
  "status": "needs_operator_action",
  "error": {
    "code": "adapter_unreachable",
    "message": "Adapter unreachable. Check Tailscale/WireGuard/SSH tunnel."
  }
}
```

**处理建议**:
1. **adapter_unreachable**: 
   ```bash
   # 检查 Tailscale 状态
   tailscale status
   
   # 检查 ECS adapter 健康
   curl http://<adapter_base_url>/health
   ```

2. **adapter_auth_failed**:
   - 检查 NAS MCP 配置中的 `auth_ref`
   - 检查环境变量 `WECHAT_ADAPTER_AUTH_TOKEN`

3. **wechat_token_invalid**:
   ```bash
   # 在 ECS 上检查 AppSecret
   echo $WECHAT_APPSECRET_XIABAN
   
   # 检查 IP 白名单（微信公众号后台 -> 设置与开发 -> 基本配置 -> IP白名单）
   ```

4. **wechat_rate_limit**:
   - 等待 1 小时后重试
   - 检查是否有其他进程频繁调用微信 API

5. **wechat_permission_denied**:
   - 登录微信公众号后台检查权限
   - 确认账号类型（服务号 vs 订阅号）

---

### 🔴 `failed` - 技术错误

**触发场景**:

| ErrorCode | 触发条件 | 处理建议 |
|---|---|---|
| `internal_error` | 未分类的内部错误 | 查看 job error message 和 MCP 日志 |
| `wechat_api_error` | 微信 API 返回未分类错误码 | 查看 error message 中的 errcode/errmsg，参考微信官方文档 |
| `hermes_db_unreachable` | 无法连接 hermes-db | 检查 hermes-db MCP 状态 |
| `hermes_db_upsert_failed` | Ledger 更新失败 | 草稿已创建，但 `wechat_articles` 未更新；需要手动补录 |

**错误示例**:
```json
{
  "status": "failed",
  "error": {
    "code": "wechat_api_error",
    "message": "WeChat API error [40001]: invalid credential"
  }
}
```

**处理建议**:
1. **internal_error**: 查看 MCP 日志，联系开发者
2. **wechat_api_error**: 参考 [微信官方错误码文档](https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Global_Return_Code.html)
3. **hermes_db_upsert_failed**: 
   - 检查 `media_id` 是否在错误消息中
   - 草稿已创建，可以手动补录到 `wechat_articles` 或忽略

---

## 重试策略

| 状态 | 是否可重试 | 重试前需要做什么 |
|---|---|---|
| `saved` | ❌ 已成功，无需重试 | - |
| `invalid_artifact` | ✅ 可重试 | 修复 artifact 后重新生成 |
| `needs_operator_action` | ✅ 可重试 | 按建议修复网络/配置/权限后重试 |
| `failed` | ⚠️ 视情况 | 排查错误原因后重试 |

**Idempotency 保护**:
- 相同 `account` + `artifact_id` 的成功 job 会被拒绝重复创建
- 如果上次失败，可以直接重试（不会创建重复草稿）

---

## 日志与诊断

### Job Store 查询

```bash
# 按 job_id 查询
wechat_get_draft_status --job_id job_1234567890_abc

# 按 artifact_id 查询（返回最新 job）
wechat_get_draft_status --artifact_id artifact_xyz

# 查看最近 7 天的 job 文件
ls -lh ~/.wechat-draft/jobs/
```

### Adapter 健康检查

```bash
# Health check
curl http://<adapter_base_url>/health

# Check credentials (dry-run token)
curl -X POST http://<adapter_base_url>/accounts/xiaban/check-credentials \
  -H "Authorization: Bearer <ADAPTER_AUTH_TOKEN>"
```

### 微信 API 官方文档

- [全局返回码](https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Global_Return_Code.html)
- [草稿箱管理](https://developers.weixin.qq.com/doc/offiaccount/Draft_Box/Add_draft.html)
- [AccessToken](https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html)

---

## 监控指标

建议监控：

1. **成功率**: `saved` jobs / total jobs
2. **错误分布**: 各 error_code 的占比
3. **Adapter 可用性**: health check 成功率
4. **Token 刷新频率**: 避免过于频繁

---

## Runbook 摘要

| 问题 | 快速排查 | 解决方案 |
|---|---|---|
| Adapter 不可达 | `tailscale status` | 重启 Tailscale 或 adapter |
| Token 无效 | 检查 ECS `$WECHAT_APPSECRET_*` | 更新环境变量并重启 adapter |
| IP 白名单 | 微信后台查看 IP 白名单 | 添加 ECS 公网 IP |
| 素材无效 | 检查 artifact `wechat_asset_manifest` | 重新上传封面/正文图片到微信 |
| Ledger 更新失败 | 检查 hermes-db MCP 可用性 | 手动补录或忽略（草稿已创建）|

---

## 参考

- **Error Codes**: `packages/wechat-draft/src/schemas/result-types.ts`
- **Workflow States**: `packages/wechat-draft/src/workflow/DraftWorkflow.ts`
- **Job Store**: `packages/wechat-draft/src/store/JobStore.ts`
- **API Risk Control**: `docs/api-risk-control.md`
