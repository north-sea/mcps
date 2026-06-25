# Operations Runbook

**Feature**: `wechat-draft-mcp`  
**Date**: 2026-06-21  
**Scope**: T019a - 运维 runbook

---

## 部署清单

### 前置条件

- [ ] Ali ECS 实例可用（公网固定 IP/EIP）
- [ ] Docker 或 systemd 运行环境
- [ ] Tailscale/WireGuard/SSH tunnel 已配置
- [ ] 微信公众号 AppID/AppSecret 已获取
- [ ] 生成 `ADAPTER_AUTH_TOKEN`（`openssl rand -base64 32`）

---

## 快速部署（ECS Adapter）

### 方式 1: Docker 部署（推荐）

#### 1. 构建镜像

```bash
# 在本地构建
cd /Users/yqg/personal/AI/mcps/packages/wechat-draft-adapter
docker build -t wechat-draft-adapter:latest .

# 推送到 ECS（如果跨机器）
docker save wechat-draft-adapter:latest | gzip | ssh ecs 'gunzip | docker load'
```

#### 2. 创建环境变量文件

```bash
# 在 ECS 上创建 /opt/wechat-adapter/.env
cat > /opt/wechat-adapter/.env <<EOF
PORT=3000
ADAPTER_AUTH_TOKEN=<生成的 token>
ALLOWED_ACCOUNTS=weiyuchengchun,yueliang,xiaban
WECHAT_APPID_YUELIANG=wx...
WECHAT_APPSECRET_YUELIANG=<secret>
WECHAT_APPID_XIABAN=wx...
WECHAT_APPSECRET_XIABAN=<secret>
EOF

chmod 600 /opt/wechat-adapter/.env
```

#### 3. 启动容器

```bash
docker run -d \
  --name wechat-adapter \
  --restart unless-stopped \
  --env-file /opt/wechat-adapter/.env \
  -p 127.0.0.1:3000:3000 \
  wechat-draft-adapter:latest
```

#### 4. 验证健康

```bash
curl http://localhost:3000/health
```

---

### 方式 2: systemd 部署

#### 1. 构建并复制

```bash
cd /Users/yqg/personal/AI/mcps/packages/wechat-draft-adapter
pnpm run build

# 复制到 ECS
rsync -avz --exclude node_modules . ecs:/opt/wechat-adapter/
ssh ecs 'cd /opt/wechat-adapter && npm install --production'
```

#### 2. 创建 systemd service

```bash
# 在 ECS 上创建 /etc/systemd/system/wechat-adapter.service
cat > /etc/systemd/system/wechat-adapter.service <<EOF
[Unit]
Description=WeChat Draft Adapter
After=network.target

[Service]
Type=simple
User=wechat-adapter
WorkingDirectory=/opt/wechat-adapter
EnvironmentFile=/opt/wechat-adapter/.env
ExecStart=/usr/bin/node /opt/wechat-adapter/dist/index.js
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF
```

#### 3. 启动服务

```bash
# 创建运行用户
useradd -r -s /bin/false wechat-adapter

# 启动服务
systemctl daemon-reload
systemctl enable wechat-adapter
systemctl start wechat-adapter

# 查看状态
systemctl status wechat-adapter
journalctl -u wechat-adapter -f
```

---

## 微信配置

### 1. 配置 IP 白名单

登录微信公众号后台：

1. **设置与开发** → **基本配置**
2. **IP 白名单** → **修改**
3. 添加 ECS 公网 IP/EIP
4. 保存

**验证 ECS 出口 IP**:
```bash
# 在 ECS 上执行
curl ifconfig.me
```

### 2. 获取 AppID/AppSecret

1. **设置与开发** → **基本配置**
2. **开发者ID(AppID)** - 复制
3. **开发者密码(AppSecret)** - 重置并复制（只显示一次）

---

## NAS/本机 MCP 配置

### 1. 配置环境变量

```bash
# ~/.zshrc 或 ~/.bashrc
export WECHAT_ADAPTER_AUTH_TOKEN="<与 ECS 一致的 token>"

# 重新加载
source ~/.zshrc
```

### 2. 配置 MCP server

参考 `docs/configuration.md` 配置 Claude Code / Codex / Hermes。

### 3. 测试连通性

```bash
# 通过 Tailscale/WireGuard IP 测试
curl http://100.64.0.2:3000/health
```

---

## 健康检查

### Adapter Health Check

```bash
# 基础健康检查
curl http://localhost:3000/health

# 预期输出
{
  "status": "ok",
  "capabilities": ["check_credentials", "draft_add", "draft_batchget", "asset_upload"],
  "allowed_accounts": ["weiyuchengchun", "yueliang", "xiaban"]
}
```

### Token Dry-run

```bash
curl -X POST http://localhost:3000/accounts/xiaban/check-credentials \
  -H "Authorization: Bearer $ADAPTER_AUTH_TOKEN"

# 预期输出（成功）
{
  "success": true,
  "account": "xiaban",
  "token_valid": true,
  "expires_in": 7199
}

# 预期输出（失败 - IP 白名单）
{
  "success": false,
  "error": "token_error",
  "errcode": 40164,
  "errmsg": "invalid ip"
}
```

### MCP 工具可用性

```bash
# Claude Code
# 在 Claude Code 中输入：
wechat_list_accounts

# 预期输出
{
  "success": true,
  "data": {
    "accounts": [
      {
        "account_id": "xiaban",
        "display_name": "下班不躺平",
        "enabled": true,
        "adapter_id": "ali-wechat-egress",
        "capabilities": ["check_credentials", "draft_add", "draft_batchget", "asset_upload"]
      }
    ]
  }
}
```

---

## 日志管理

### Docker 日志

```bash
# 查看实时日志
docker logs -f wechat-adapter

# 查看最近 100 行
docker logs --tail 100 wechat-adapter

# 配置日志轮转（/etc/docker/daemon.json）
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### systemd 日志

```bash
# 查看实时日志
journalctl -u wechat-adapter -f

# 查看最近 100 行
journalctl -u wechat-adapter -n 100

# 清理旧日志
journalctl --vacuum-time=7d
```

### MCP Job Store

```bash
# 查看 job 文件
ls -lh ~/.wechat-draft/jobs/

# 查看今天的 jobs
cat ~/.wechat-draft/jobs/$(date +%Y-%m-%d).jsonl | jq .

# 统计成功率
cat ~/.wechat-draft/jobs/*.jsonl | jq -r .status | sort | uniq -c
```

---

## 故障排查

### Adapter 启动失败

**症状**: 容器/服务无法启动

**排查**:
```bash
# Docker
docker logs wechat-adapter

# systemd
journalctl -u wechat-adapter -n 50

# 常见原因
- 环境变量缺失（ADAPTER_AUTH_TOKEN / WECHAT_APPID_* / WECHAT_APPSECRET_*）
- 端口冲突（3000 已被占用）
- 权限不足（文件/目录访问）
```

**解决**:
```bash
# 检查环境变量
docker exec wechat-adapter env | grep WECHAT

# 检查端口
netstat -tlnp | grep 3000

# 更换端口
docker run -p 127.0.0.1:3001:3000 ...
```

---

### Adapter unreachable

**症状**: NAS MCP 报错 `adapter_unreachable`

**排查**:
```bash
# 1. 检查 Tailscale 状态（NAS 侧）
tailscale status

# 2. Ping ECS
ping 100.64.0.2

# 3. 测试端口
nc -zv 100.64.0.2 3000

# 4. 检查 ECS adapter 是否运行
ssh ecs 'docker ps | grep wechat-adapter'
```

**解决**:
```bash
# 重启 Tailscale（NAS 侧）
sudo tailscale down && sudo tailscale up

# 重启 adapter（ECS 侧）
docker restart wechat-adapter
```

---

### Token 错误

**症状**: `wechat_token_invalid` 或 `errcode: 40164`

**排查**:
```bash
# 1. 检查 IP 白名单
ssh ecs 'curl ifconfig.me'  # 获取 ECS 公网 IP
# 对比微信后台 IP 白名单

# 2. 检查 AppSecret
ssh ecs 'docker exec wechat-adapter env | grep WECHAT_APPSECRET'

# 3. 手动获取 token
curl "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=wx...&secret=<secret>"
```

**解决**:
- **IP 白名单错误**: 在微信后台添加 ECS 公网 IP
- **AppSecret 错误**: 更新环境变量并重启 adapter
- **AppSecret 冻结**: 联系微信客服

---

### Rate Limit

**症状**: `errcode: 45009`

**排查**:
```bash
# 统计最近 1 小时调用次数
cat ~/.wechat-draft/jobs/$(date +%Y-%m-%d).jsonl | \
  jq -r 'select(.created_at >= "'$(date -u -v-1H +%Y-%m-%dT%H:%M:%S)'") | .job_id' | \
  wc -l
```

**解决**:
- 等待 1 小时后重试
- 减少调用频率
- 检查是否有其他进程频繁调用

---

## 定期维护

### 每周

- [ ] 检查 adapter 日志是否有异常
- [ ] 清理 job store 旧文件（保留 30 天）:
  ```bash
  find ~/.wechat-draft/jobs/ -name "*.jsonl" -mtime +30 -delete
  ```

### 每月

- [ ] 检查 Docker 镜像更新
- [ ] 检查微信 API 配额使用情况
- [ ] 备份重要 job 记录

### 每季度

- [ ] 轮转 `ADAPTER_AUTH_TOKEN`
- [ ] 审查 adapter 日志脱敏策略
- [ ] 检查 IP 白名单配置

---

## 升级流程

### Adapter 升级

```bash
# 1. 构建新镜像
docker build -t wechat-draft-adapter:v0.2.0 .

# 2. 备份当前环境变量
docker exec wechat-adapter env > /opt/wechat-adapter/.env.backup

# 3. 停止旧容器
docker stop wechat-adapter
docker rename wechat-adapter wechat-adapter-old

# 4. 启动新容器
docker run -d \
  --name wechat-adapter \
  --restart unless-stopped \
  --env-file /opt/wechat-adapter/.env \
  -p 127.0.0.1:3000:3000 \
  wechat-draft-adapter:v0.2.0

# 5. 验证健康
curl http://localhost:3000/health

# 6. 删除旧容器（确认无问题后）
docker rm wechat-adapter-old
```

### MCP 升级

```bash
# 1. 拉取最新代码
cd /Users/yqg/personal/AI/mcps
git pull

# 2. 重新构建
cd packages/wechat-draft
pnpm install
pnpm run build

# 3. 重启 MCP client（Claude Code / Codex）
# 无需手动操作，MCP client 自动检测变化
```

---

## 监控指标

建议监控（Phase 2 可选）:

- **Adapter 可用性**: health check 成功率
- **草稿成功率**: saved jobs / total jobs
- **错误分布**: error_code 占比
- **Token 刷新频率**: token 获取次数/天

---

## 应急联系

- **微信 API 问题**: [微信开放社区](https://developers.weixin.qq.com/community/)
- **Tailscale 问题**: [Tailscale Docs](https://tailscale.com/kb/)
- **项目问题**: GitHub Issues

---

## 参考文档

- **配置示例**: `docs/configuration.md`
- **错误处理**: `docs/error-handling.md`
- **API 风控**: `docs/api-risk-control.md`
- **部署指南**: `DEPLOYMENT.md`
