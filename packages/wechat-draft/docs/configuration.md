# WeChat Draft MCP - Configuration Guide

**Feature**: `wechat-draft-mcp`  
**Date**: 2026-06-21  
**Scope**: T019 - 客户端配置示例

---

## 配置架构

```
┌─────────────────────────────────────────────────────────────┐
│ NAS / 本机 MCP Client (Hermes / Codex / Claude Code)      │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ wechat-draft MCP                                    │   │
│ │ - stdio 方式启动                                     │   │
│ │ - 读取环境变量配置                                   │   │
│ │ - 调用 hermes-db MCP (可选)                         │   │
│ └──────────────────┬──────────────────────────────────┘   │
│                    │ HTTP (Tailscale/WireGuard)            │
└────────────────────┼────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Ali ECS (公网固定 IP)                                        │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ wechat-draft-adapter (Docker / systemd)            │   │
│ │ - 持有 AppID/AppSecret                              │   │
│ │ - 缓存 AccessToken                                  │   │
│ │ - 唯一微信 API 出口                                  │   │
│ └──────────────────┬──────────────────────────────────┘   │
│                    │ HTTPS                                  │
└────────────────────┼────────────────────────────────────────┘
                     │
                     ▼
              微信公众号 API
         (IP 白名单: ECS 公网 IP)
```

---

## 环境变量

### NAS / 本机 MCP 侧

```bash
# Adapter 访问配置
export WECHAT_ADAPTER_BASE_URL="http://100.x.x.x:3000"  # Tailscale IP
export WECHAT_ADAPTER_AUTH_TOKEN="<生成的随机 token>"

# Runtime 路径（可选，默认 ~/.wechat-draft/）
export WECHAT_DRAFT_RUNTIME_PATH="/Users/yqg/.wechat-draft"

# Hermes-db 访问（如果需要 ledger 更新）
export HERMES_DB_BASE_URL="http://localhost:8787"

# ECS 出口 IP（用于日志/诊断，非必需）
export WECHAT_ECS_EGRESS_IP="<ECS 公网 IP>"
```

### Ali ECS Adapter 侧

```bash
# 监听端口
export PORT=3000

# Adapter 认证 token（与 NAS 侧一致）
export ADAPTER_AUTH_TOKEN="<生成的随机 token>"

# 允许的账号（逗号分隔）
export ALLOWED_ACCOUNTS="weiyuchengchun,yueliang,xiaban"

# 微信 AppID/AppSecret
export WECHAT_APPID_YUELIANG="wx..."
export WECHAT_APPSECRET_YUELIANG="<secret>"
export WECHAT_APPID_XIABAN="wx..."
export WECHAT_APPSECRET_XIABAN="<secret>"
```

---

## 配置示例

### 1. Claude Code (本机)

**位置**: `~/.claude/settings.json`

```json
{
  "mcpServers": {
    "wechat-draft": {
      "command": "node",
      "args": ["/Users/yqg/personal/AI/mcps/packages/wechat-draft/dist/index.js"],
      "env": {
        "WECHAT_ADAPTER_BASE_URL": "http://100.64.0.2:3000",
        "WECHAT_ADAPTER_AUTH_TOKEN": "env:WECHAT_ADAPTER_AUTH_TOKEN",
        "WECHAT_DRAFT_RUNTIME_PATH": "/Users/yqg/.wechat-draft",
        "HERMES_DB_BASE_URL": "http://localhost:8787"
      }
    },
    "hermes-db": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/yqg/personal/AI/mcps/packages/hermes-db",
        "run",
        "hermes-db-mcp"
      ],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@localhost:5432/hermes"
      }
    }
  }
}
```

**环境变量** (`~/.zshrc` 或 `~/.bashrc`):
```bash
export WECHAT_ADAPTER_AUTH_TOKEN="your-random-token-here"
```

---

### 2. Codex (本机)

**位置**: `~/.codex/mcp.json`

```json
{
  "mcpServers": {
    "wechat-draft": {
      "command": "node",
      "args": ["/Users/yqg/personal/AI/mcps/packages/wechat-draft/dist/index.js"],
      "env": {
        "WECHAT_ADAPTER_BASE_URL": "http://100.64.0.2:3000",
        "WECHAT_ADAPTER_AUTH_TOKEN": "env:WECHAT_ADAPTER_AUTH_TOKEN",
        "WECHAT_DRAFT_RUNTIME_PATH": "/Users/yqg/.wechat-draft"
      }
    }
  }
}
```

---

### 3. Hermes (NAS)

**位置**: `~/hermes/config/mcp-servers.yaml`

```yaml
servers:
  wechat-draft:
    command: node
    args:
      - /path/to/mcps/packages/wechat-draft/dist/index.js
    env:
      WECHAT_ADAPTER_BASE_URL: "http://100.64.0.2:3000"
      WECHAT_ADAPTER_AUTH_TOKEN: "env:WECHAT_ADAPTER_AUTH_TOKEN"
      WECHAT_DRAFT_RUNTIME_PATH: "/var/hermes/.wechat-draft"
      HERMES_DB_BASE_URL: "http://localhost:8787"
```

---

## 安全注意事项

### ✅ 必须做

1. **生成强随机 ADAPTER_AUTH_TOKEN**:
   ```bash
   openssl rand -base64 32
   ```

2. **环境变量存储 token**（不要硬编码）:
   ```bash
   # ~/.zshrc 或 ~/.bashrc
   export WECHAT_ADAPTER_AUTH_TOKEN="<生成的 token>"
   ```

3. **配置文件引用环境变量**:
   ```json
   "WECHAT_ADAPTER_AUTH_TOKEN": "env:WECHAT_ADAPTER_AUTH_TOKEN"
   ```

4. **ECS adapter 只监听内网**（Tailscale/WireGuard）:
   - 不要绑定 `0.0.0.0:3000`
   - 使用 Tailscale IP 或 SSH tunnel

### ❌ 禁止做

- ❌ 不要把 AppSecret 存在 NAS 侧
- ❌ 不要把 ADAPTER_AUTH_TOKEN 提交到 git
- ❌ 不要让 adapter 监听公网 IP（除非有防火墙）
- ❌ 不要在 MCP 配置文件中硬编码 token

---

## 验证配置

### 测试 MCP 工具可用

```bash
# Claude Code
# 打开 Claude Code，输入：
# /mcp list

# 应该看到 wechat-draft 和 4 个工具：
# - wechat_list_accounts
# - wechat_validate_publish_artifact
# - wechat_create_draft
# - wechat_get_draft_status
```

### 测试 Adapter 连通性

```bash
# 从 NAS/本机测试
curl http://100.64.0.2:3000/health

# 预期输出：
# {"status":"ok","capabilities":["check_credentials","draft_add","draft_batchget","asset_upload"]}
```

---

## Troubleshooting

| 问题 | 排查 | 解决 |
|---|---|---|
| MCP 工具找不到 | 检查 `mcpServers` 配置路径 | 确认 `dist/index.js` 路径正确 |
| Adapter unreachable | `curl http://<adapter>/health` | 检查 Tailscale/WireGuard 状态 |
| Adapter auth failed | 检查 `WECHAT_ADAPTER_AUTH_TOKEN` | 确认 NAS 和 ECS 两侧 token 一致 |
| Runtime path 权限 | `ls -la ~/.wechat-draft/` | `mkdir -p ~/.wechat-draft/jobs/` |

---

## 下一步

配置完成后，参考 `DEPLOYMENT.md` 部署 ECS adapter，然后参考 `docs/error-handling.md` 了解错误处理和运维建议。
