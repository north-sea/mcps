# WeChat Draft MCP Server

WeChat Draft MCP Server 提供微信公众号草稿管理能力，通过 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 暴露给 AI agent。

当前推荐部署方式是 Docker 化 Streamable HTTP MCP 服务，供本机 agent 和 NAS agent 统一通过 `POST /mcp` 调用。部署和客户端配置见 [HTTP Docker Service](docs/http-docker-service.md)。

正式部署与 `hermes-db` 一致：推送 `wechat-draft-vX.Y.Z` tag 后由 GitHub Actions 构建 GHCR 镜像，NAS self-hosted runner 拉取精确版本并重启服务。

## 功能

- **账号管理**: 列出可用的微信公众号账号
- **素材上传**: 上传图片素材（正文图片和封面图片）到微信素材库
- **Artifact 验证**: 验证 hermes-db artifact 是否满足微信发布要求
- **草稿创建**: 从 hermes-db publish-ready artifact 创建微信草稿
- **状态查询**: 查询草稿任务状态

---

## 工具列表

### `wechat_list_accounts`

列出可用的微信公众号账号。

**输入**:
- `include_disabled` (可选, boolean): 是否包含禁用账号，默认 false

**输出**:
```json
{
  "accounts": [
    {
      "account_id": "xiaban",
      "display_name": "下班不躺平",
      "enabled": true,
      "capabilities": ["check_credentials", "draft_add", "draft_batchget", "asset_upload"]
    }
  ]
}
```

---

### `wechat_upload_asset`

上传图片素材到微信素材库。支持本地文件路径和远程图片 URL。

**输入**:
- `account` (必需, string): 微信账号 ID
- `usage` (必需, enum): 素材用途
  - `body_image`: 正文图片，返回可用于 `<img src="...">` 的微信 CDN URL
  - `cover_image`: 封面图片，返回可用于草稿封面的永久素材 `thumb_media_id`
- `source_type` (必需, enum): 图片来源类型
  - `local_path`: 本地文件路径（MCP 运行环境可读）
  - `remote_url`: 远程图片 URL（http/https）
- `source` (必需, string): 图片来源（文件路径或 URL）
- `filename` (可选, string): 原始文件名（用于 MIME 推断）
- `mime_type` (可选, string): 显式指定 MIME 类型

**输出**:
```json
{
  "account": "xiaban",
  "usage": "body_image",
  "source_type": "local_path",
  "filename": "cover.jpg",
  "mime_type": "image/jpeg",
  "size_bytes": 102400,
  "wechat_url": "https://mmbiz.qpic.cn/...",
  "created_at": "2026-06-22T12:34:56.789Z"
}
```

**素材约束**:

| 用途 | 格式 | 最大大小 | 返回字段 | 说明 |
|------|------|----------|----------|------|
| `body_image` | JPG, JPEG, PNG | 1MB | `wechat_url` | 微信 CDN 图片 URL，可直接用于正文 `<img src="...">` |
| `cover_image` | JPG, JPEG | 64KB | `thumb_media_id` | 永久缩略图素材 ID，用于草稿封面 |

**注意事项**:
- 封面图片使用微信永久 thumb 素材，要求严格（JPG 且 64KB 以内），需要提前准备合规图片
- 不支持 base64 编码图片（MVP 范围外）
- 远程 URL 仅支持 http/https 协议
- 上传成功后，素材立即可用于草稿创建，但不会自动写入 artifact metadata

**示例**:

```javascript
// 上传本地正文图片
await mcpClient.callTool('wechat_upload_asset', {
  account: 'weiyuchengchun',
  usage: 'body_image',
  source_type: 'local_path',
  source: '/path/to/image.jpg'
});
// 返回: { wechat_url: "https://mmbiz.qpic.cn/..." }

// 上传远程封面图片
await mcpClient.callTool('wechat_upload_asset', {
  account: 'xiaban',
  usage: 'cover_image',
  source_type: 'remote_url',
  source: 'https://example.com/cover.jpg'
});
// 返回: { thumb_media_id: "abc123..." }
```

---

### `wechat_validate_publish_artifact`

验证 hermes-db artifact 是否满足微信发布要求。

**输入**:
- `account` (必需, string): 微信账号 ID
- `artifact_id` (必需, string): hermes-db artifact ID

**输出**:
```json
{
  "valid": true,
  "artifact_id": "art_123",
  "account": "weiyuchengchun",
  "validation_errors": [],
  "artifact_summary": {
    "title": "文章标题",
    "stage": "publish",
    "type": "wechat-article",
    "publish_ready": true,
    "wechat_asset_ready": true
  }
}
```

---

### `wechat_create_draft`

从 hermes-db publish-ready artifact 创建微信草稿。

**输入**:
- `account` (必需, string): 微信账号 ID
- `artifact_id` (必需, string): hermes-db artifact ID
- `idempotency_key` (可选, string): 幂等键，默认为 `account+artifact_id` 的哈希

**输出**:
```json
{
  "job_id": "job_xxx",
  "status": "saved",
  "account": "weiyuchengchun",
  "artifact_id": "art_123",
  "title": "文章标题",
  "media_id": "draft_media_id_xxx",
  "created_at": "2026-06-22T12:34:56.789Z"
}
```

**注意事项**:
- 草稿创建**不会**自动上传素材
- Artifact 必须包含符合微信要求的 `wechat_asset_manifest`
- 正文图片 URL 必须是微信 CDN URL（`https://mmbiz.qpic.cn/...`）
- 封面必须提供有效的 `thumb_media_id`

---

### `wechat_get_draft_status`

查询草稿任务状态。

**输入**:
- `job_id` (可选, string): 任务 ID
- `artifact_id` (可选, string): Artifact ID

至少提供 `job_id` 或 `artifact_id` 之一。

**输出**:
```json
{
  "found": true,
  "job_id": "job_xxx",
  "status": "saved",
  "account": "weiyuchengchun",
  "artifact_id": "art_123",
  "title": "文章标题",
  "media_id": "draft_media_id_xxx",
  "created_at": "2026-06-22T12:00:00.000Z",
  "updated_at": "2026-06-22T12:00:05.123Z"
}
```

---

## 工作流程

典型的素材上传 + 草稿创建流程：

1. **准备素材**: 上传封面和正文图片
   ```javascript
   // 上传封面
   const coverResult = await mcpClient.callTool('wechat_upload_asset', {
    account: 'xiaban',
     usage: 'cover_image',
     source_type: 'local_path',
     source: '/path/to/cover.jpg'
   });
   // 获得 thumb_media_id

   // 上传正文图片
   const bodyImageResult = await mcpClient.callTool('wechat_upload_asset', {
    account: 'xiaban',
     usage: 'body_image',
     source_type: 'local_path',
     source: '/path/to/body-image.jpg'
   });
   // 获得 wechat_url
   ```

2. **组装 artifact**: 将上传结果写入 artifact metadata
   ```javascript
   artifact.metadata.wechat_asset_manifest = {
     ready: true,
     cover_thumb_media_id: coverResult.thumb_media_id,
     body_images: [bodyImageResult.wechat_url]
   };
   artifact.content_text = `<img src="${bodyImageResult.wechat_url}">...`;
   ```

3. **验证 artifact**: 确认符合微信要求
   ```javascript
   const validation = await mcpClient.callTool('wechat_validate_publish_artifact', {
     account: 'weiyuchengchun',
     artifact_id: 'art_123'
   });
   ```

4. **创建草稿**: 从 artifact 创建微信草稿
   ```javascript
   const draftResult = await mcpClient.callTool('wechat_create_draft', {
     account: 'weiyuchengchun',
     artifact_id: 'art_123'
   });
   ```

---

## 错误处理

### 素材上传错误

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| `asset_source_invalid` | 源类型无效或协议不支持 | 检查 `source_type` 和 URL 协议 |
| `asset_file_not_readable` | 本地文件不可读 | 检查文件路径和权限 |
| `asset_remote_url_fetch_failed` | 远程 URL 下载失败 | 检查 URL 可访问性和网络 |
| `asset_size_exceeded` | 文件超过大小限制 | body_image 最大 1MB，cover_image 最大 64KB |
| `asset_format_unsupported` | 格式不支持 | body_image 支持 jpg/png，cover_image 只支持 jpg |
| `adapter_capability_missing` | Adapter 不支持素材上传 | 升级 ECS adapter 到支持 `asset_upload` 的版本 |
| `wechat_api_error` | 微信 API 错误 | 检查 errcode（40005: 格式错误, 40009: 大小错误） |

### 草稿创建错误

| 错误码 | 说明 | 处理建议 |
|--------|------|----------|
| `account_not_found` | 账号不存在 | 检查账号配置 |
| `account_disabled` | 账号已禁用 | 启用账号 |
| `artifact_not_found` | Artifact 不存在 | 检查 artifact_id |
| `artifact_not_publish_ready` | Artifact 未标记为 publish_ready | 完成 artifact 准备流程 |
| `artifact_wechat_assets_not_ready` | 微信素材未准备好 | 上传素材并更新 wechat_asset_manifest |

---

## 安装与配置

### 1. 安装依赖

```bash
pnpm install
```

### 2. 构建

```bash
pnpm build
```

### 3. 配置

MCP server 需要以下配置（通过环境变量或 config 文件）：

- `WECHAT_ADAPTER_BASE_URL`: ECS adapter 地址（例如 `http://localhost:3000`）
- `WECHAT_ADAPTER_AUTH_TOKEN`: Adapter 认证 token
- `HERMES_DB_BASE_URL`: hermes-db 地址
- `HERMES_DB_AUTH_TOKEN`: hermes-db 认证 token（可选）

使用外部 `accounts.yaml` 时，账号清单来自文件；运行时 endpoint 仍可通过
`WECHAT_ADAPTER_BASE_URL` / `WECHAT_ADAPTER_AUTH_REF` / `HERMES_DB_BASE_URL`
覆盖 YAML 设置。

### 4. 运行

```bash
pnpm start
# 或
node ./dist/index.js
```

Docker HTTP 服务使用：

```bash
pnpm --filter @mcps/wechat-draft docker:build
cd packages/wechat-draft
cp .env.nas.example .env
docker compose --env-file .env -f docker-compose.example.yml up -d
```

---

## 依赖服务

- **ECS WeChat Adapter**: 私有 HTTP 服务，运行在阿里云 ECS，负责调用微信官方 API
- **hermes-db**: 存储 artifact 的数据库服务

---

## 参考资料

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [微信公众号素材管理](https://developers.weixin.qq.com/doc/service/guide/product/asset.html)
- [微信正文图片上传接口](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_uploadimage.html)
- [微信永久素材接口](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial.html)
