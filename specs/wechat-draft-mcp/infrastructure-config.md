# Infrastructure Configuration: WeChat Draft MCP

**Feature**: `wechat-draft-mcp` | **Date**: 2026-06-21  
**Status**: Configuration Design (未部署)  
**Purpose**: 固化 T001a、T001d 配置设计，作为 Phase 1-3 实现和 T001b dry-run 的输入

---

## 配置来源说明

本文档提取自 `plan.md`、`data-model.md` 和 `spec.md`。当前 **ECS adapter 未部署**，以下配置为实现前的设计固化。

---

## 1. 微信 API Credential 配置（T001a）

### 1.1 AppID/AppSecret 存储位置

| 项目 | 设计决策 |
|---|---|
| **存储位置** | Ali ECS adapter 端（环境变量或 secret manager） |
| **NAS 端存储** | ❌ 不存储 AppSecret/AccessToken |
| **NAS 端引用** | `EcsWechatAdapterConfig.auth_ref`（adapter auth token）<br>`ApiCredentialConfig.adapter_account_ref`（账号映射） |
| **Redaction** | 日志/响应不输出 AppSecret/AccessToken 值 |

### 1.2 目标账号：`yueliang`

| Field | Value |
|---|---|
| `account_id` | `yueliang` |
| `adapter_account_ref` | `yueliang`（adapter 端逻辑账号） |
| `appid_hint` | 可选 redacted AppID suffix（如 `...abc123`） |
| `secret_source_hint` | ECS 环境变量/KMS/Secrets Manager（不输出实际 secret） |

### 1.3 微信 IP 白名单配置

| 项目 | 设计 |
|---|---|
| **白名单 IP** | Ali ECS 公网 IP/EIP（`EcsWechatAdapterConfig.egress_public_ip`） |
| **配置位置** | 微信公众号后台手动配置 |
| **验证方式** | T001b AccessToken dry-run（需等待 T012b adapter 实现） |
| **禁用 IP** | ❌ NAS 家宽 IP（不稳定）<br>❌ Tailscale `100.x` 地址（私有网络） |

### 1.4 ApiCredentialConfig 示例

```yaml
account_id: yueliang
credential_location: ecs_adapter
adapter_account_ref: yueliang
appid_hint: "wx...abc123"  # redacted
secret_source_hint: "ECS_ENV_VAR or Ali_KMS_Secret"
ip_whitelist_note: "ECS egress IP: <REDACTED>, configured in WeChat console"
```

---

## 2. ECS Adapter 运行配置（T001d）

### 2.1 Runtime Path

| 项目 | 设计路径 |
|---|---|
| **Package 位置** | `packages/wechat-draft-adapter/` |
| **入口** | `src/server.ts` |
| **构建产物** | `dist/server.js` |
| **当前状态** | ❌ 未创建（Phase 1 T005 后实现） |

### 2.2 Adapter Endpoints

| Endpoint | Method | Capability | Notes |
|---|---|---|---|
| `/health` | GET | Health check | 返回 adapter 状态和 capability 列表 |
| `/accounts/:account/check-credentials` | POST | `check_credentials` | AccessToken dry-run（不输出 token） |
| `/accounts/:account/drafts` | POST | `draft_add` | 创建草稿，返回 `media_id` |
| `/drafts/batchget` | POST | `draft_batchget` | 可选，批量查询草稿 |

**禁用 Endpoints**：
- ❌ 图片上传（`/media/uploadimg`）
- ❌ 素材上传（`/material/add_material`）
- ❌ 发布/群发/更新/删除相关端点

### 2.3 Adapter Auth

| 项目 | 设计 |
|---|---|
| **Auth 机制** | Token-based authentication |
| **NAS 端引用** | `EcsWechatAdapterConfig.auth_ref`（环境变量/secret ref） |
| **Adapter 端验证** | 每个请求需携带 auth header |
| **Token 存储** | NAS 端不存储 raw token，只存储 ref |

### 2.4 AccessToken 缓存

| 项目 | 设计 |
|---|---|
| **缓存位置** | ECS adapter 端（内存或 Redis） |
| **过期时间** | 7200 秒（微信官方 TTL） |
| **安全边界** | 提前 300 秒刷新（避免边界竞态） |
| **刷新策略** | Token 失效时一次重试，rate limit/permission error 不盲重试 |
| **日志脱敏** | ✅ 日志不输出 token 值 |

### 2.5 EcsWechatAdapterConfig 示例

```yaml
adapter_id: ali-wechat-egress
base_url: "http://100.x.x.x:3000"  # Tailscale private endpoint
auth_ref: "env:WECHAT_ADAPTER_AUTH_TOKEN"
allowed_accounts:
  - yueliang
egress_public_ip: "<REDACTED_ECS_PUBLIC_IP>"
network_path: tailscale  # or wireguard / ssh_tunnel
timeout_ms: 10000
capabilities:
  - check_credentials
  - draft_add
  - draft_batchget
metadata:
  deployment_note: "Ali ECS, systemd service wechat-adapter"
  host_alias: "ali"
```

---

## 3. NAS 到 ECS 私有网络通道（T001d）

### 3.1 网络路径选项

| 选项 | 优先级 | Notes |
|---|---|---|
| **Tailscale** | 推荐 | 零配置 mesh VPN，`100.x.x.x` 地址 |
| **WireGuard** | 备选 | 需手动配置 VPN tunnel |
| **SSH Tunnel** | 备选 | `ssh -L` 转发，依赖 SSH session |
| **Private VPC** | 备选 | 需 Ali 内网 VPC 配置 |

### 3.2 访问方式

| 从 | 到 | 协议 | URL 格式 |
|---|---|---|---|
| NAS MCP | ECS Adapter | HTTP over private network | `http://100.x.x.x:3000` (Tailscale) |
| ECS Adapter | WeChat API | HTTPS from public IP | `https://api.weixin.qq.com` |

### 3.3 连接验证

**Phase 0 验证**（T001d）：
- ✅ 确认 Tailscale/WireGuard/SSH tunnel 配置存在
- ✅ 记录 adapter private endpoint URL

**Phase 3 验证**（T001b，blocked by T012b）：
- ⏳ NAS 调用 `GET /health` 成功
- ⏳ NAS 调用 `POST /accounts/yueliang/check-credentials` 返回 AccessToken metadata（不输出 token）

---

## 4. Process Manager 与运维（T001d）

### 4.1 Adapter Runtime

| 项目 | 设计 |
|---|---|
| **进程管理** | systemd (推荐) 或 PM2 |
| **Service 名称** | `wechat-adapter.service` |
| **启动命令** | `node dist/server.js` 或 `npm start` |
| **工作目录** | `/path/to/packages/wechat-draft-adapter` |
| **环境变量** | `WECHAT_APPID_YUELIANG`, `WECHAT_APPSECRET_YUELIANG`, `ADAPTER_AUTH_TOKEN`, `PORT` |
| **日志** | `/var/log/wechat-adapter/` 或 systemd journal |

### 4.2 Health Check

| 项目 | 设计 |
|---|---|
| **Endpoint** | `GET /health` |
| **响应格式** | `{"status": "ok", "capabilities": ["check_credentials", "draft_add"]}` |
| **监控** | NAS 端定期 health check，失败时告警 |

### 4.3 重启与恢复

| 场景 | 操作 |
|---|---|
| Adapter 无响应 | `systemctl restart wechat-adapter` |
| Token 缓存失效 | Adapter 自动刷新，无需人工干预 |
| ECS 公网 IP 变更 | 更新微信 IP 白名单，重启 adapter |

---

## 5. 配置差异：NAS vs ECS

| 项目 | NAS 端 | ECS 端 |
|---|---|---|---|
| **AppID/AppSecret** | ❌ 不存储 | ✅ 存储（环境变量/secret manager） |
| **AccessToken** | ❌ 不缓存 | ✅ 缓存（7200s TTL） |
| **Adapter Auth** | ✅ 存储 ref（`auth_ref`） | ✅ 验证 auth header |
| **微信 API 调用** | ❌ 不直连 | ✅ 从 ECS 公网 IP 出口 |
| **Hermes-db 访问** | ✅ 读 artifact、写 ledger | ❌ 无 hermes-db 访问 |
| **出口 IP** | NAS 家宽（不稳定） | ECS 公网 IP（微信白名单） |

---

## 6. 待确认项（需现场核实）

| 项目 | 状态 | 阻塞任务 |
|---|---|---|
| Ali ECS 公网 IP/EIP 实际值 | 待确认 | T001a |
| Tailscale/WireGuard/SSH tunnel 具体配置 | 待确认 | T001d |
| ECS AppSecret/Auth Token 实际存储位置 | 待确认 | T001a |
| 微信 IP 白名单是否已配置 | 待确认 | T001b |
| ECS adapter systemd service 名称 | 待设计 | T012b |
| Adapter 默认监听端口 | 待设计 | T012b |

---

## 7. Next Steps

| 阶段 | 任务 | 产物 |
|---|---|---|
| **Phase 0** | T001a/T001d（本文档已完成） | ✅ `infrastructure-config.md` |
| **Phase 1** | T005/T006（MCP 骨架与 tool contract） | `packages/wechat-draft/` |
| **Phase 3** | T011/T012/T012a/T012b（Adapter 实现） | `packages/wechat-draft-adapter/` |
| **Phase 3** | T001b（AccessToken dry-run） | ⏳ Blocked by T012b |

---

## 8. 参考文档

- [spec.md](spec.md) — P1 需求和安全边界
- [plan.md](plan.md) — ADR-003（凭证和出口模型）
- [data-model.md](data-model.md) — `EcsWechatAdapterConfig` / `ApiCredentialConfig`
- [official-api-research.md](official-api-research.md) — AccessToken / draft/add API
- [tasks.md](tasks.md) — Phase 0-5 任务定义
