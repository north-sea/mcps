# Implementation Plan: WeChat Asset Upload Tool

**Workspace**: `wechat-asset-upload` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/wechat-asset-upload/spec.md`

---

## Summary

在现有 `wechat-draft` MCP 中新增一个 `wechat_upload_asset` tool，并扩展 ECS 上的 `wechat-draft-adapter` 来调用微信官方素材接口。MCP 负责读取本地文件或下载远程图片并转成受控 multipart payload；ECS adapter 仍是唯一微信 API 出口，按 `usage=body_image|cover_image` 分别调用正文图片上传和永久封面素材上传。

本阶段只有一个合理方向：不新增 MCP，不让 ECS adapter 读取用户本地路径，也不让 adapter 主动抓任意远程 URL，避免本地路径不可达和 ECS SSRF 风险。

---

## Architecture Overview

```text
Agent / User
  |
  | MCP tool: wechat_upload_asset(account, usage, source_type, source)
  v
packages/wechat-draft
  - validate account / adapter capability
  - local_path: read file from MCP runtime
  - remote_url: fetch URL with size/type guard
  - send multipart or binary upload request to ECS adapter
  |
  v
packages/wechat-draft-adapter on Ali ECS
  - authMiddleware + validateAccount
  - TokenManager.getToken(account)
  - usage=body_image -> POST /cgi-bin/media/uploadimg
  - usage=cover_image -> POST /cgi-bin/material/add_material?type=thumb
  |
  v
WeChat Official API
  - body_image returns url
  - cover_image returns media_id
```

现有边界保持不变：NAS / 本机 MCP 不持有 AppSecret，不直接调用微信官方 API；ECS adapter 复用现有 AccessToken 缓存、刷新和错误映射。

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| `wechat_upload_asset` with `usage=body_image` | `wechat_url` | 上游 artifact 组装流程 / 手工写入 `content_text` 与 `wechat_asset_manifest.body_images` | `wechat_validate_publish_artifact` 接受正文中 `https://mmbiz.qpic.cn/...` 图片 URL |
| `wechat_upload_asset` with `usage=cover_image` | `thumb_media_id` | 上游 artifact 组装流程 / `DraftPayloadBuilder` | `DraftPayloadBuilder` 从 `metadata.cover.thumb_media_id` 或 `wechat_asset_manifest.cover_thumb_media_id` 构建 draft payload |
| ECS adapter upload endpoint | `adapter_upload_asset_response` | MCP tool response formatter | MCP 返回 `success=true` 且包含 `usage`、`account`、`wechat_url` 或 `thumb_media_id` |

**孤儿 artifact 处理**: 上传结果本身不写入 hermes-db；它是调用方继续组装 publish-ready artifact 的中间结果。没有自动 consumer 是有意边界，本 feature 不做文章扫描或 artifact 写回。

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 安全性 | AppSecret / AccessToken 只存在 ECS adapter | MCP 只调用 adapter；adapter 响应不包含 token 或 secret | 单测检查响应 shape；错误路径不泄露敏感值 |
| SSRF 控制 | ECS adapter 不主动抓取任意远程 URL | 远程 URL 由 MCP 下载并做 allow/limit guard，再上传字节 | adapter API 只接收文件内容，不接收 `remote_url` |
| 可用性 | 一个 MCP tool 覆盖正文图和封面图 | `usage` 枚举驱动不同返回字段 | tool schema 和 tests 覆盖两个 usage |
| 契约稳定性 | `wechat_create_draft` 不自动上传素材 | 上传 tool 与草稿 tool 分离 | 代码检查和单测确认 draft workflow 无 upload 分支 |
| 可诊断性 | 错误能定位输入、adapter、token、微信 API | 增加 upload-specific error mapping | 测试覆盖本地文件不可读、远程 URL 失败、微信 40005/40009 等 |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001: 单 MCP tool | 用户要求不拆两个 tools | A. 两个 tools；B. 一个 tool + usage | B: `wechat_upload_asset` + `usage` | tool schema 稍复杂，但 agent 调用入口更少 | 用户确认 |
| ADR-002: MCP 下载远程 URL | 本地路径 ECS 不可读，adapter 抓远程 URL 有 SSRF 风险 | A. MCP 统一取字节；B. adapter 读取路径/URL | A | MCP 需要实现 fetch/read 和大小限制 | UNVERIFIED |
| ADR-003: Adapter 统一 endpoint | MCP 对外一个 tool，adapter 可保持同构 | A. `/assets` + usage；B. 两个 public endpoints | A: `POST /accounts/:account/assets` | handler 内部分支，但 endpoint 更稳定 | UNVERIFIED |
| ADR-004: 封面用永久 thumb 素材 | 草稿 `thumb_media_id` 需要素材 id | A. `type=image`；B. `type=thumb` | B: `add_material?type=thumb` | thumb 有 64KB/JPG 限制，调用方需准备合规封面 | 微信官方文档 |

---

## Key Design Decisions

### Decision 1: 图片输入由 MCP 统一物化为文件字节

- **背景**: MVP 支持 `local_path` 和 `remote_url`。本地路径只在 MCP 运行环境可读；远程 URL 如果交给 ECS adapter 拉取，会扩大 ECS 出口服务的 SSRF 面。
- **选项**:
  - A: MCP 读取本地路径、下载远程 URL，然后把文件字节传给 adapter。
  - B: MCP 把路径或 URL 透传给 adapter。
- **结论**: 选择 A。
- **影响**: MCP 侧新增文件读取、URL fetch、大小限制、mime/扩展名初筛；adapter 只处理上传字节和微信 API。
- **来源**: 安全边界推断；微信官方素材接口要求 `media` formdata。

### Decision 2: Adapter 对外统一 `/accounts/:account/assets`

- **背景**: MCP 对外只有一个 `wechat_upload_asset` tool，adapter 最好保持同一语义入口。
- **选项**:
  - A: 一个 endpoint，body/form field 包含 `usage`。
  - B: 两个 endpoint：`/body-images` 和 `/cover-images`。
- **结论**: 选择 A，对外统一 endpoint，内部两个 private helper。
- **影响**: capability 命名为 `asset_upload`；handler 内按 `usage` 调用 `uploadBodyImage` 或 `uploadCoverImage`。
- **来源**: 当前代码已有 `/accounts/:account/drafts` 聚合 draft 语义，沿用同类风格。

### Decision 3: 不引入新依赖，优先使用 Node 20 原生能力

- **背景**: 两个 package 当前依赖很少；Node 20 有 `fetch`、`Blob`、`FormData`，标准库有 `fs`。
- **选项**:
  - A: 使用原生 `fetch` / `FormData` / `Blob` / `fs`.
  - B: 引入 `form-data`、`mime-types`、下载库。
- **结论**: 选择 A。
- **影响**: MIME 判断先做最小白名单，必要时由微信 API 返回最终格式错误；不增加供应链复杂度。
- **来源**: 现有 `package.json` 已依赖最小化；Node 20 devDependency 已存在于 adapter。

### Decision 4: 不创建 upload job store

- **背景**: 素材上传是即时请求，结果只有 URL/media_id；spec 未要求持久记录。
- **选项**:
  - A: 直接返回上传结果。
  - B: 复用/扩展 `JobStore` 记录每次上传。
- **结论**: 选择 A。
- **影响**: 简化实现；后续如果需要素材库管理或审计，再作为独立 feature 增加持久化。
- **来源**: spec Out of Scope 排除了素材库管理。

---

## Module Design

### Module: `packages/wechat-draft/src/schemas/tool-schemas.ts`

**职责**: 定义 MCP tool 输入输出契约。

**YAGNI 停止层级**: 第 5 层，schema 直接表达，不新增抽象 schema builder。

**改动概述**:

- 新增 `UploadAssetInputSchema`。
- 新增 `UploadAssetOutputSchema`。
- 新增 `AssetUsageSchema = z.enum(['body_image', 'cover_image'])`。
- 新增 `AssetSourceTypeSchema = z.enum(['local_path', 'remote_url'])`。

**关键接口 / 行为**:

```text
wechat_upload_asset({
  account: string,
  usage: 'body_image' | 'cover_image',
  source_type: 'local_path' | 'remote_url',
  source: string,
  filename?: string,
  mime_type?: string
})

returns {
  account,
  usage,
  source_type,
  filename?,
  mime_type?,
  size_bytes?,
  wechat_url?,       // body_image
  thumb_media_id?,   // cover_image
  created_at
}
```

**注意事项**:

- `wechat_url` 和 `thumb_media_id` 至少且只能按 usage 返回对应核心字段。
- 不接受 base64。

### Module: `packages/wechat-draft/src/server.ts`

**职责**: 注册 `wechat_upload_asset` MCP tool，做账号和 adapter capability 校验。

**YAGNI 停止层级**: 第 6 层，直接增加 tool handler，复用现有 account/adapter 校验模式。

**改动概述**:

- 在现有 tools 后新增 `wechat_upload_asset`。
- 复用 `ConfigLoader.getAccount` / `getAdapter`。
- 检查 adapter capabilities 包含 `asset_upload`。
- 调用新增 `WechatAdapterClient.uploadAsset(...)`。

**关键接口 / 行为**:

```text
validate account enabled
resolve adapter
if !adapter.capabilities.includes('asset_upload') -> ADAPTER_CAPABILITY_MISSING
materialize image source
adapterClient.uploadAsset(account, usage, file)
return createSuccessResult(upload result)
```

**注意事项**:

- 不改 `wechat_create_draft`。
- 错误响应保持现有 `createErrorResult` 风格。

### Module: `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` *(new)*

**职责**: 把 `local_path` 或 `remote_url` 转成受控上传对象。

**YAGNI 停止层级**: 第 4 层，使用 Node 原生 `fs` 和 `fetch`，不引入下载库。

**改动概述**:

- `local_path`: 使用 `fs.readFile` 读取文件；从 filename 或显式参数推断最小 mime。
- `remote_url`: 只允许 `http:` / `https:`；fetch 后检查 status、content-length、content-type；读取 ArrayBuffer。
- 对不同 usage 应用大小与格式 guard。

**关键接口 / 行为**:

```text
loadAssetSource(input) -> {
  bytes: Uint8Array,
  filename: string,
  mimeType: string,
  sizeBytes: number
}
```

**注意事项**:

- `body_image`: jpg/jpeg/png，最大 1MB。
- `cover_image`: JPG，最大 64KB，因为计划使用 `type=thumb`。
- 远程 URL 不跟随无限重定向；实现阶段使用 fetch 默认行为并加总大小限制，必要时后续收紧。

### Module: `packages/wechat-draft/src/wechat/WechatAdapterClient.ts`

**职责**: NAS/MCP 侧 HTTP client，调用 ECS adapter。

**YAGNI 停止层级**: 第 6 层，扩展现有 client，不新增 transport 层。

**改动概述**:

- 新增 response type `AdapterUploadAssetResponse`。
- 新增 error `AdapterCapabilityMissingError` 或用现有 `AdapterEndpointNotFoundError` 映射为 capability missing。
- 新增 `uploadAsset(account, request)`，向 `/accounts/:account/assets` 发送 multipart/form-data。

**关键接口 / 行为**:

```text
POST {baseUrl}/accounts/{account}/assets
Authorization: Bearer ...
multipart:
  usage=body_image|cover_image
  media=@file
  filename?
  mime_type?
```

**注意事项**:

- 该方法不能把图片内容写入错误 details。
- fetch helper 当前默认 JSON；multipart 需要允许 caller 自定义 headers/body，避免强行设置 `Content-Type: application/json`。

### Module: `packages/wechat-draft/src/config/loader.ts`

**职责**: 暴露 adapter capability。

**YAGNI 停止层级**: 第 5 层，直接更新默认 capabilities。

**改动概述**:

- 默认 `capabilities` 增加 `asset_upload`。

**注意事项**:

- 旧 adapter 未部署时，本地配置可能先声明 capability 但远端 404。MCP 仍要把 404 映射成 adapter 版本不匹配。

### Module: `packages/wechat-draft-adapter/src/server.ts`

**职责**: ECS 私有 HTTP API，接收 MCP 上传的图片字节，调用微信官方素材接口。

**YAGNI 停止层级**: 第 4 层，使用 Express + Node 原生 Web APIs；如 Express 无法直接处理 multipart，再引入最小 multipart 依赖需在实现阶段记录理由。

**改动概述**:

- `/health` capabilities 增加 `asset_upload`。
- 新增 `POST /accounts/:account/assets`。
- 复用 `authMiddleware` 和 `validateAccount`。
- 解析 multipart fields: `usage` 和 `media`。
- 调用 `apiClient.uploadBodyImage` 或 `apiClient.uploadCoverImage`。

**关键接口 / 行为**:

```text
if usage === 'body_image':
  POST https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=...
  formdata media=@file
  return { success, account, usage, url }

if usage === 'cover_image':
  POST https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=...&type=thumb
  formdata media=@file
  return { success, account, usage, media_id }
```

**注意事项**:

- adapter 不接受 `source_type` 或远程 URL。
- adapter 只处理已经由 MCP 物化后的文件。
- 请求体大小限制需要覆盖封面 64KB 和正文 1MB，建议 adapter route-level limit 先设 2MB。

### Module: `packages/wechat-draft-adapter/src/wechat/WeChatApiClient.ts`

**职责**: 封装微信官方 API 调用。

**YAGNI 停止层级**: 第 6 层，沿用现有 class 和 token retry 逻辑。

**改动概述**:

- 新增常量：
  - `WECHAT_UPLOAD_IMAGE_API = https://api.weixin.qq.com/cgi-bin/media/uploadimg`
  - `WECHAT_ADD_MATERIAL_API = https://api.weixin.qq.com/cgi-bin/material/add_material`
- 新增 `uploadBodyImage(account, file)`。
- 新增 `uploadCoverImage(account, file)`。
- token error 时沿用清 token 后重试一次。

**注意事项**:

- 官方 uploadImage 返回字段是 `url`。
- 官方 addMaterial 返回字段是 `media_id`，图片素材还可能返回 `url`；对 `cover_image` 只把 `media_id` 作为核心结果返回。
- 微信素材错误继续走 `WeChatApiError`，补充 `isAssetError` 覆盖 40005、40009。

### Module: `packages/wechat-draft-adapter/src/types/wechat.ts`

**职责**: 定义微信 API response 类型。

**YAGNI 停止层级**: 第 5 层，直接增加必要接口。

**改动概述**:

- `UploadImageResponse { url: string }`
- `AddMaterialResponse { media_id: string; url?: string }`
- `UploadAssetUsage = 'body_image' | 'cover_image'`

---

## Data Model

不需要单独 `data-model.md`。本 feature 不新增数据库表、不新增持久状态、不修改 hermes-db schema；只新增 transient request/response schema。

---

## Project Structure

```text
packages/wechat-draft/
  src/server.ts                         # register wechat_upload_asset
  src/schemas/tool-schemas.ts           # input/output schema
  src/schemas/result-types.ts           # add error code if needed
  src/wechat/AssetSourceLoader.ts       # local_path / remote_url -> bytes
  src/wechat/WechatAdapterClient.ts     # uploadAsset client method
  src/config/loader.ts                  # asset_upload capability

packages/wechat-draft-adapter/
  src/server.ts                         # POST /accounts/:account/assets
  src/wechat/WeChatApiClient.ts         # uploadBodyImage / uploadCoverImage
  src/types/wechat.ts                   # upload response types
```

---

## Risks and Tradeoffs

- **Multipart parsing may require a dependency**: Express does not parse multipart by default. Plan 首选原生 Web API，但如果实现阶段发现 Node/Express 组合处理 multipart 过于脆弱，应引入 `multer` 或 `busboy` 并在实现说明中记录理由。
- **封面 thumb 限制严格**: 微信永久 `thumb` 素材要求 JPG 且 64KB，很多封面图会失败。本 feature 不做压缩转换，只返回明确错误。
- **远程 URL 下载风险**: MCP 下载远程 URL 仍需大小和协议限制。MVP 不做域名 allowlist，但禁止非 HTTP(S)。
- **上传结果不持久化**: 这符合当前范围，但用户需要自行把返回值写入 artifact metadata。
- **能力声明与部署版本可能错位**: MCP 本地 config 可能声明 `asset_upload`，但 ECS adapter 尚未部署新 endpoint。需要把 adapter 404 映射为版本不匹配。

---

## Evolution Path

- **MVP**: 单图上传；支持 local path 和 remote URL；返回 `wechat_url` 或 `thumb_media_id`；不持久化。
- **成长期**: 批量上传、图片压缩/裁剪、素材上传结果写回 artifact metadata。
- **成熟期**: 素材库管理、去重、复用、审计和过期清理。

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。素材库、去重、批量处理、图片处理均排除。
- 是否引用了外部模式但没有适配检查：否。本计划只使用现有 MCP + ECS adapter 边界。
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。新增 transient upload request/response；无持久状态。

---

## Verification Strategy

1. **Schema tests**:
   - 接受 `usage=body_image|cover_image`。
   - 接受 `source_type=local_path|remote_url`。
   - 拒绝 base64、未知 usage、未知 source_type。

2. **MCP unit tests**:
   - 本地文件不可读返回 validation error。
   - 远程 URL 404 / 非图片 content-type / 超限返回 validation error。
   - adapter 缺少 capability 或 endpoint 404 返回 adapter capability/version mismatch。
   - 成功 body image 返回 `wechat_url`。
   - 成功 cover image 返回 `thumb_media_id`。

3. **Adapter unit tests**:
   - `/health` 返回 `asset_upload` capability。
   - `/accounts/:account/assets` 复用 auth/account middleware。
   - `usage=body_image` 调用 uploadimg path。
   - `usage=cover_image` 调用 add_material path with `type=thumb`。
   - token error 仍重试一次。
   - 微信 40005 / 40009 映射为素材 validation error。

4. **Build checks**:
   - `pnpm --filter @mcps/wechat-draft build`
   - `pnpm --filter @mcps/wechat-draft-adapter build`

5. **Optional live smoke**:
   - 用小于 1MB 的 jpg/png 调 `wechat_upload_asset usage=body_image`，确认返回 `mmbiz.qpic.cn` URL。
   - 用小于 64KB 的 JPG 调 `wechat_upload_asset usage=cover_image`，确认返回 `thumb_media_id`。
   - live smoke 需要真实公众号账号、ECS adapter、微信 IP 白名单和人工确认，不作为本地单测前置。

---

## Stage Readiness

- 是否需要 `data-model.md`：不需要。没有持久实体、状态关系或 DB schema 变化。
- 下一步建议：`tasks`
- 阻塞项：无。multipart 依赖选择可在实现阶段以最小可行原则处理并记录。

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | 必须 | 当前文件 |
| data-model.md | 不需要 | 仅 transient schema，无持久模型 |
| tasks.md | 后续阶段生成 | 拆分实现任务 |
| acceptance.md | 后续阶段生成 | traits 命中，closeout 时需要 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| 正文图片接口 | https://developers.weixin.qq.com/doc/service/api/material/permanent/api_uploadimage.html | `POST /cgi-bin/media/uploadimg`，返回 `url`；jpg/png，1MB 以下 |
| 永久素材接口 | https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial.html | `POST /cgi-bin/material/add_material`；`type=thumb` 用于缩略图，返回 `media_id` |
| 素材管理入口 | https://developers.weixin.qq.com/doc/service/guide/product/asset.html | 列出 uploadimg 与 add_material 能力 |
