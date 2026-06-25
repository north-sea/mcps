# API Risk Control & Redaction Policy

**Feature**: `wechat-draft-mcp`  
**Date**: 2026-06-21  
**Scope**: T013a - API 风控、频控和脱敏策略

---

## 重试策略

### ✅ 可重试错误（仅一次）

**Token 相关错误**（ECS adapter 内自动重试）:

| WeChat errcode | 描述 | 处理方式 |
|---|---|---|
| 40001 | invalid credential | 清除缓存 token，刷新后重试一次 |
| 40014 | invalid access_token | 清除缓存 token，刷新后重试一次 |
| 42001 | access_token expired | 清除缓存 token，刷新后重试一次 |

**实现位置**: `packages/wechat-draft-adapter/src/wechat/WeChatApiClient.ts:20-30`

```typescript
async createDraft(account: string, request: DraftAddRequest): Promise<DraftAddResponse> {
  try {
    return await this.callDraftAdd(account, request);
  } catch (error) {
    // Retry once on token error
    if (error instanceof WeChatApiError && error.isTokenError()) {
      this.tokenManager.clearToken(account);
      return await this.callDraftAdd(account, request);
    }
    throw error;
  }
}
```

### ❌ 不可重试错误（直接返回）

**Rate limit 错误**:

| WeChat errcode | 描述 | 处理方式 |
|---|---|---|
| 45009 | API freq out of limit | 不重试，返回 `needs_operator_action`，建议等待或联系微信 |

**Permission 错误**:

| WeChat errcode | 描述 | 处理方式 |
|---|---|---|
| 48001 | api unauthorized | 不重试，返回 `needs_operator_action`，检查公众号权限 |

**IP 白名单错误**:

| WeChat errcode | 描述 | 处理方式 |
|---|---|---|
| 40164 | invalid ip | 不重试，返回 `needs_operator_action`，检查 ECS 公网 IP 白名单配置 |

**Asset 错误**:

| WeChat errcode | 描述 | 处理方式 |
|---|---|---|
| 40007 | invalid media_id | 不重试，返回 `invalid_artifact`，检查封面 `thumb_media_id` |
| 40008 | invalid message type | 不重试，返回 `invalid_artifact`，检查 payload 格式 |

**Adapter 层错误**:

| 错误类型 | 描述 | 处理方式 |
|---|---|---|
| adapter_unreachable | 网络不可达 | 不重试，返回 `needs_operator_action`，检查 Tailscale/WireGuard/SSH 通道 |
| adapter_auth_failed | 认证失败 | 不重试，返回 `needs_operator_action`，检查 ADAPTER_AUTH_TOKEN |
| adapter_timeout | 超时 | 不重试，返回 `needs_operator_action`，检查网络延迟或增加超时 |

---

## 脱敏策略

### 🔒 必须脱敏字段

**ECS adapter**:

| 字段 | 脱敏方式 | 位置 |
|---|---|---|
| `access_token` | 不返回原文，只返回 metadata（有效性、剩余时间） | `TokenManager.getTokenMetadata()` |
| `appid` | 只在初始化日志显示，response 不返回 | `server.ts:222` |
| `appsecret` | 永不日志，永不返回 | 只从环境变量读取 |
| `ADAPTER_AUTH_TOKEN` | 永不日志，401 错误不返回 token 原文 | `server.ts:19` |

**NAS MCP**:

| 字段 | 脱敏方式 | 位置 |
|---|---|---|
| adapter auth token | 从 `env:` 解析后不日志，不返回 | `WechatAdapterClient.ts:150` |
| artifact `content_text` | 只返回 `content_preview`（前 200 字符） | MCP tool response |
| `media_id` | 可返回（用于定位草稿），但不返回完整正文 | CreateDraftOutput |

### ✅ 可返回字段

**安全返回**（用于诊断和定位）:

- `account` (account_id)
- `artifact_id`
- `title`
- `media_id` (草稿定位 ID)
- `job_id`
- `status`
- `errcode` / `errmsg` (WeChat 错误码)
- `expires_in` (token 剩余时间)
- `token_valid` (token 有效性 boolean)

**禁止返回**:

- `access_token` (原文)
- `appsecret` (原文)
- `ADAPTER_AUTH_TOKEN` (原文)
- 完整 `content_text`（草稿创建成功后不回传正文）

---

## 日志脱敏

**ECS adapter 启动日志**:

```
✅ Loaded credentials for account: xiaban
❌ Logging appid/appsecret in production
```

**当前实现**: `server.ts:222` 已脱敏 appid/secret，只记录 account 名称。

**MCP tool 返回值**:

- `wechat_create_draft` 成功返回：`job_id`, `status`, `account`, `artifact_id`, `title`, `media_id`
- 不返回：完整 `content_text`, `access_token`, adapter auth token

**错误日志**:

- Token 错误只记录 `errcode` / `errmsg`，不记录 token 原文
- Adapter 错误只记录 endpoint 和错误类型，不记录 auth header

---

## 频控策略

**微信 API 频控**（官方限制）:

- AccessToken: 2000 次/日，建议缓存复用（已实现：7200s TTL）
- draft/add: 无明确公开限制，遇到 45009 时停止

**Adapter 侧频控**（MVP 不实现，Phase 2 可选）:

- 单账号串行化（避免并发刷 token）
- 跨账号无限制

**NAS MCP 侧频控**（MVP 不实现，Phase 2 可选）:

- JobStore idempotency key 拒重
- 无全局 rate limit

---

## 验收条件

1. ✅ Token 错误只在 adapter 内重试一次（`WeChatApiClient.createDraft`）
2. ✅ Rate limit/permission/IP whitelist 错误不重试，直接返回 `needs_operator_action`
3. ✅ TokenManager 不返回 token 原文，只返回 metadata
4. ✅ Adapter 启动日志不泄露 appid/secret 原文
5. ✅ MCP tool 返回值不包含完整 `content_text`
6. ✅ 401/403 错误不返回 auth token 原文

---

## 待加固项（后续 Phase）

- [ ] Adapter response 完整 HTTP trace 脱敏（当前未实现 debug 模式）
- [ ] MCP tool 返回 `content_preview` 而非完整正文（T015 实现时加固）
- [ ] Adapter 侧单账号串行化锁（避免并发刷 token）
- [ ] JobStore retention policy（自动清理过期 job）

---

## 参考

- **Token 管理**: `packages/wechat-draft-adapter/src/wechat/TokenManager.ts`
- **API Client 重试**: `packages/wechat-draft-adapter/src/wechat/WeChatApiClient.ts`
- **Adapter 认证**: `packages/wechat-draft-adapter/src/server.ts`
- **错误分类**: `packages/wechat-draft/src/schemas/result-types.ts`
