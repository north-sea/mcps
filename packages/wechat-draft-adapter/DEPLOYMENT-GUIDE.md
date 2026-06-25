# 🚀 ECS Adapter 部署指南

## 📋 部署步骤

### Step 1: 在 ECS 上创建配置文件

```bash
# SSH 到 ECS
ssh ali

# 创建目录
sudo mkdir -p /opt/wechat-adapter
cd /opt/wechat-adapter

# 创建 .env 文件
sudo nano .env
```

**复制以下内容到 .env**（填入你的微信凭据）:

```bash
# Adapter Server Configuration
PORT=3000

# Authentication Token (已生成)
ADAPTER_AUTH_TOKEN=<generate-a-random-token>

# Allowed Accounts
ALLOWED_ACCOUNTS=weiyuchengchun,yueliang,xiaban

# WeChat Credentials - 请填入你的实际值
WECHAT_APPID_WEIYUCHENGCHUN=wx________________
WECHAT_APPSECRET_WEIYUCHENGCHUN=________________________________
WECHAT_APPID_YUELIANG=wx________________
WECHAT_APPSECRET_YUELIANG=________________________________
WECHAT_APPID_XIABAN=wx________________
WECHAT_APPSECRET_XIABAN=________________________________
```

**保存并设置权限**:
```bash
sudo chmod 600 /opt/wechat-adapter/.env
```

---

### Step 2: 执行自动部署脚本

**在本机执行**:

```bash
cd /Users/yqg/personal/AI/mcps/packages/wechat-draft-adapter
./deploy-to-ecs.sh
```

脚本会自动：
1. ✅ 构建 adapter
2. ✅ 复制文件到 ECS
3. ✅ 安装依赖
4. ✅ 创建 systemd 服务
5. ✅ 启动服务
6. ✅ 健康检查

---

### Step 3: 配置微信 IP 白名单

**获取 ECS 公网 IP**:
```bash
ssh ali 'curl -s ifconfig.me'
```

**配置微信后台**:
1. 登录 [微信公众号后台](https://mp.weixin.qq.com/)
2. **设置与开发** → **基本配置**
3. **IP 白名单** → **修改**
4. 添加上面获取的 ECS 公网 IP
5. 保存

---

### Step 4: 验证 Token

```bash
ssh ali 'curl -X POST http://localhost:3000/accounts/xiaban/check-credentials -H "Authorization: Bearer $ADAPTER_AUTH_TOKEN"'
```

**预期输出（成功）**:
```json
{
  "success": true,
  "account": "weiyuchengchun",
  "token_valid": true,
  "expires_in": 7199
}
```

**如果失败**:
- `errcode: 40164` → IP 白名单未配置
- `errcode: 40001` → AppSecret 错误
- `success: false, error: "token_error"` → 检查环境变量

---

### Step 5: 配置本机 MCP 客户端

**添加环境变量** (`~/.zshrc`):
```bash
# WeChat Adapter Auth Token
export WECHAT_ADAPTER_AUTH_TOKEN="ILs9Ma/zRNqRT/YMwabt79qG4wAFjT98uYBLOM0HGxw="
```

**重新加载**:
```bash
source ~/.zshrc
```

**配置 Claude Code** (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "wechat-draft": {
      "command": "node",
      "args": ["/Users/yqg/personal/AI/mcps/packages/wechat-draft/dist/index.js"],
      "env": {
        "WECHAT_ADAPTER_BASE_URL": "http://<ECS-TAILSCALE-IP>:3000",
        "WECHAT_ADAPTER_AUTH_TOKEN": "env:WECHAT_ADAPTER_AUTH_TOKEN",
        "WECHAT_DRAFT_RUNTIME_PATH": "/Users/yqg/.wechat-draft"
      }
    }
  }
}
```

**如果你有 Tailscale**:
- 替换 `<ECS-TAILSCALE-IP>` 为 ECS 的 Tailscale IP（通常是 `100.x.x.x`）
- 如果没有，可以用 SSH tunnel: `ssh -L 3000:localhost:3000 ali`，然后用 `http://localhost:3000`

---

### Step 6: 测试完整流程

**在 Claude Code 中测试**:

```javascript
// 1. 列出账号
wechat_list_accounts()

// 2. 检查 adapter 连通性（通过 check-credentials）
// 这会触发 NAS -> ECS -> WeChat 的完整链路
```

---

## ⚠️ 故障排查

### Adapter 未启动

```bash
# 查看日志
ssh ali 'sudo journalctl -u wechat-adapter -n 50'

# 重启服务
ssh ali 'sudo systemctl restart wechat-adapter'

# 查看状态
ssh ali 'sudo systemctl status wechat-adapter'
```

### 本机无法连接 adapter

```bash
# 测试连通性（如果用 Tailscale）
ping 100.x.x.x
curl http://100.x.x.x:3000/health

# 如果没有 Tailscale，用 SSH tunnel
ssh -L 3000:localhost:3000 ali
# 然后在本机访问 http://localhost:3000/health
```

### Token 验证失败

```bash
# 在 ECS 上手动测试
ssh ali
source /opt/wechat-adapter/.env
curl -X POST http://localhost:3000/accounts/xiaban/check-credentials \
  -H "Authorization: Bearer $ADAPTER_AUTH_TOKEN"
```

---

## 📊 部署验证清单

- [ ] ECS adapter 服务运行中（`systemctl status wechat-adapter`）
- [ ] Health check 通过（`curl http://localhost:3000/health`）
- [ ] Token dry-run 成功（返回 `token_valid: true`）
- [ ] ECS 公网 IP 已加入微信白名单
- [ ] 本机环境变量已配置（`echo $WECHAT_ADAPTER_AUTH_TOKEN`）
- [ ] Claude Code MCP 配置已更新
- [ ] 本机可连接 adapter（Tailscale 或 SSH tunnel）

---

## 🎉 完成后

部署完成后，你就可以：

1. ✅ 在 Claude Code 中调用 `wechat_list_accounts`
2. ✅ 使用 `wechat_validate_publish_artifact` 验证 artifact
3. ✅ 使用 `wechat_create_draft` 创建草稿（需要 publish-ready artifact）
4. ✅ 使用 `wechat_get_draft_status` 查询状态

**下一步**: 参考 `docs/wechat-ready-artifact-example.md` 准备一个测试 artifact，然后执行完整的 live smoke 测试（T021）。
