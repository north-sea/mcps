# WeChat Draft Adapter

ECS-side HTTP adapter for WeChat Official Account API. Provides private endpoints for NAS-side MCP with AccessToken management, fixed egress IP, and credential isolation.

## 架构

```
NAS/MCP (wechat-draft)
    ↓ (Tailscale/WireGuard)
ECS Adapter (wechat-draft-adapter)
    ↓ (Fixed Egress IP)
WeChat Official API
```

**职责边界**:
- NAS/MCP: 账号配置、artifact 验证、job 管理、本地文件读取
- ECS Adapter: AppSecret 持有、AccessToken 管理、微信 API 调用、固定出口 IP
- WeChat API: 草稿创建、素材上传、token 刷新

---

## Endpoints

### `GET /health`

Health check，返回 capabilities 和 allowed accounts。

**认证**: 不需要

**响应**:
```json
{
  "status": "ok",
  "capabilities": ["check_credentials", "draft_add", "draft_batchget", "asset_upload"],
  "allowed_accounts": ["weiyuchengchun", "yueliang", "xiaban"]
}
```

---

### `POST /accounts/:account/check-credentials`

AccessToken dry-run，验证账号凭据有效性。

**认证**: Bearer token

**响应**:
```json
{
  "success": true,
  "account": "weiyuchengchun",
  "token_valid": true,
  "expires_in": 3600
}
```

---

### `POST /accounts/:account/drafts`

创建微信草稿。

**认证**: Bearer token

**请求体** (application/json):
```json
{
  "articles": [
    {
      "title": "文章标题",
      "author": "作者",
      "digest": "摘要",
      "content": "<p>正文HTML</p>",
      "content_source_url": "https://example.com",
      "thumb_media_id": "cover_media_id",
      "need_open_comment": 1,
      "only_fans_can_comment": 0
    }
  ]
}
```

**响应**:
```json
{
  "success": true,
  "account": "weiyuchengchun",
  "media_id": "draft_media_id_xxx"
}
```

---

### `POST /accounts/:account/assets`

上传图片素材到微信素材库。

**认证**: Bearer token

**请求体** (multipart/form-data):
- `usage` (string): `body_image` 或 `cover_image`
- `media` (file): 图片文件
- `filename` (string, 可选): 原始文件名
- `mime_type` (string, 可选): MIME 类型

**响应** (usage=body_image):
```json
{
  "success": true,
  "account": "weiyuchengchun",
  "usage": "body_image",
  "wechat_url": "https://mmbiz.qpic.cn/..."
}
```

**响应** (usage=cover_image):
```json
{
  "success": true,
  "account": "weiyuchengchun",
  "usage": "cover_image",
  "thumb_media_id": "media_id_xxx"
}
```

**微信素材接口映射**:
| usage | 微信 API | 返回字段 | 约束 |
|-------|----------|----------|------|
| `body_image` | `/cgi-bin/media/uploadimg` | `url` | jpg/png, 1MB 以下 |
| `cover_image` | `/cgi-bin/material/add_material?type=thumb` | `media_id` | jpg, 64KB 以下 |

---

## 配置

### 环境变量

**必需**:
- `ADAPTER_AUTH_TOKEN`: Adapter HTTP 认证 token（NAS MCP 使用）
- `ALLOWED_ACCOUNTS`: 允许的账号列表，逗号分隔（例如 `weiyuchengchun,yueliang,xiaban`）
- `WECHAT_APPID_<ACCOUNT>`: 各账号的 AppID（例如 `WECHAT_APPID_WEIYUCHENGCHUN`）
- `WECHAT_APPSECRET_<ACCOUNT>`: 各账号的 AppSecret（例如 `WECHAT_APPSECRET_WEIYUCHENGCHUN`）

**可选**:
- `PORT`: HTTP 端口，默认 3000

### 示例配置

```bash
# Adapter 认证
export ADAPTER_AUTH_TOKEN="your-secure-token"

# 允许的账号
export ALLOWED_ACCOUNTS="weiyuchengchun,yueliang,xiaban"

# 账号凭据
export WECHAT_APPID_WEIYUCHENGCHUN="wx1234567890abcdef"
export WECHAT_APPSECRET_WEIYUCHENGCHUN="abcdef1234567890abcdef1234567890"
export WECHAT_APPID_XIABAN="wxabcdef1234567890"
export WECHAT_APPSECRET_XIABAN="abcdef1234567890abcdef1234567890"

# 端口（可选）
export PORT=3000
```

---

## 部署

### 1. 安装依赖

```bash
pnpm install
```

### 2. 构建

```bash
pnpm build
```

### 3. 配置环境变量

创建 `.env` 文件或通过 systemd 配置环境变量。

### 4. 运行

```bash
pnpm start
# 或
node ./dist/index.js
```

### 5. 配置 systemd (生产环境)

```ini
[Unit]
Description=WeChat Draft Adapter
After=network.target

[Service]
Type=simple
User=wechat-adapter
WorkingDirectory=/opt/wechat-draft-adapter
Environment="NODE_ENV=production"
EnvironmentFile=/etc/wechat-adapter/.env
ExecStart=/usr/bin/node /opt/wechat-draft-adapter/dist/index.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 安全性

### 1. 凭据隔离

- AppSecret 只存在 ECS adapter，NAS/MCP 无法访问
- AccessToken 由 adapter 管理，MCP 只获得 adapter auth token
- 微信 API 响应不包含 token 或 secret

### 2. 网络隔离

- Adapter HTTP 端点为私有（Tailscale/WireGuard/SSH tunnel）
- 只允许配置的账号调用
- Bearer token 认证所有私有端点

### 3. IP 白名单

- ECS 固定出口 IP 配置在微信公众平台 IP 白名单
- 所有微信 API 调用从 ECS 发起

---

## AccessToken 管理

### Token 生命周期

1. **首次获取**: 调用 `/cgi-bin/token` 获取 access_token（有效期 7200 秒）
2. **缓存**: 保存在内存，记录过期时间
3. **自动刷新**: 过期前 5 分钟自动刷新
4. **错误重试**: 遇到 token 错误（40001, 40014, 42001）时清除缓存并重试一次

### Token 错误码

| errcode | 说明 | 处理 |
|---------|------|------|
| 40001 | invalid credential | 清除 token 并重新获取 |
| 40014 | invalid access_token | 清除 token 并重新获取 |
| 42001 | access_token expired | 清除 token 并重新获取 |

---

## 错误处理

### Adapter 错误

| 错误类型 | HTTP Status | 说明 |
|----------|-------------|------|
| `unauthorized` | 401 | Bearer token 无效 |
| `account_not_allowed` | 403 | 账号不在允许列表 |
| `account_not_found` | 404 | 账号凭据未配置 |
| `token_error` | 400 | 微信 AccessToken 错误 |
| `wechat_api_error` | 400 | 微信 API 错误 |
| `internal_error` | 500 | Adapter 内部错误 |

### 微信素材错误

| errcode | 说明 | 建议 |
|---------|------|------|
| 40005 | invalid file type | 检查图片格式（body_image: jpg/png, cover_image: jpg only） |
| 40007 | invalid media_id | media_id 无效或已过期 |
| 40009 | invalid image file size | 检查文件大小（body_image: <1MB, cover_image: <64KB） |

---

## 监控

### Health Check

```bash
curl http://localhost:3000/health
```

### 日志

Adapter 会输出以下日志：
- 启动信息（端口、允许的账号）
- AccessToken 获取和刷新
- API 调用错误和重试

生产环境建议通过 systemd journal 或日志文件收集：
```bash
journalctl -u wechat-adapter -f
```

---

## 依赖

- **Node.js**: >= 20 (使用原生 `fetch`, `FormData`, `Blob`)
- **express**: HTTP 服务框架
- **multer**: Multipart/form-data 解析
- **zod**: Schema 验证

---

## 参考资料

- [微信公众号素材管理](https://developers.weixin.qq.com/doc/service/guide/product/asset.html)
- [微信正文图片上传](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_uploadimage.html)
- [微信永久素材上传](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial.html)
- [微信 AccessToken](https://developers.weixin.qq.com/doc/service/api/access_token.html)
- [微信草稿接口](https://developers.weixin.qq.com/doc/service/api/draft.html)
