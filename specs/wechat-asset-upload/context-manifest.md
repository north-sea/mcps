# Context Manifest: WeChat Asset Upload Tool

**Workspace**: `wechat-asset-upload`
**Created**: 2026-06-22
**Status**: active
**Last Updated**: 2026-06-22

> 本文件用于记录 SDD 各阶段必须读取的高信号上下文。它不是待修改源文件清单，也不替代实现阶段按需阅读代码。

---

## Implementation Progress

**Phase 1: Contract And Source Loading Foundation**
- ✅ T001: MCP tool schema 和结果类型已完成
  - 新增 `AssetUsageSchema`、`AssetSourceTypeSchema`、`UploadAssetInputSchema`、`UploadAssetOutputSchema`
  - 新增 5 个素材上传专用错误码：`ASSET_SOURCE_INVALID`、`ASSET_FILE_NOT_READABLE`、`ASSET_REMOTE_URL_FETCH_FAILED`、`ASSET_SIZE_EXCEEDED`、`ASSET_FORMAT_UNSUPPORTED`
  - TypeScript 编译通过
- ✅ T002: AssetSourceLoader 已完成
  - 支持 local_path（Node.js fs.readFile）和 remote_url（Node.js fetch）
  - body_image: jpg/jpeg/png, 最大 1MB
  - cover_image: jpg/jpeg only, 最大 64KB（微信 thumb 素材要求）
  - 15/15 单元测试通过（本地文件、远程 URL、大小限制、格式限制、错误处理）
- ✅ T003: WechatAdapterClient 扩展已完成
  - 新增 `AdapterUploadAssetResponse` 类型
  - 新增 `uploadAsset` 方法，使用 Node.js 原生 `FormData` 和 `Blob` 构建 multipart 请求
  - 修改 `fetch` 方法支持 `customBody`，避免强制设置 `Content-Type: application/json`
  - 向 `/accounts/:account/assets` 发送 multipart/form-data
  - 404 正确映射为 `adapter_endpoint_not_found`
  - 3/3 单元测试通过

**Phase 2: Body Image Upload Slice**
- ✅ T004: ECS adapter 正文图片上传路径已完成
  - 安装 `multer` 用于解析 multipart/form-data
  - 新增 `UploadImageResponse`、`AddMaterialResponse`、`UploadAssetUsage` 类型
  - 在 `WeChatApiClient` 中新增 `uploadBodyImage` 方法，调用 `/cgi-bin/media/uploadimg`
  - 在 `WeChatApiClient` 中新增 `uploadCoverImage` 方法，调用 `/cgi-bin/material/add_material?type=thumb`
  - 在 `server.ts` 中新增 `POST /accounts/:account/assets` 路由，使用 multer 解析 multipart
  - 根据 `usage` 字段路由到 `uploadBodyImage` 或 `uploadCoverImage`
  - `/health` 返回 `asset_upload` capability
  - TypeScript 编译通过
- ✅ T005: MCP server 注册正文图片闭环已完成
  - 在 `server.ts` 中注册 `wechat_upload_asset` tool
  - 复用 account 和 adapter 校验逻辑
  - 检查 adapter capability 包含 `asset_upload`
  - 调用 `AssetSourceLoader.load` 物化本地/远程图片
  - 调用 `WechatAdapterClient.uploadAsset` 上传到 adapter
  - 返回 `wechat_url`（body_image）或 `thumb_media_id`（cover_image）
  - 错误映射：AssetSourceError 正确映射到对应错误码
  - 默认 adapter capabilities 增加 `asset_upload`
  - TypeScript 编译通过

**Phase 4: Error Mapping, Contract Guard, And Verification**
- ✅ T008: 增加上传专用错误映射和敏感信息保护已完成
- ✅ T009: 确认 wechat_create_draft 不出现隐式上传路径已完成
- ✅ T010: 运行本地构建和测试已完成（18/18 单元测试通过）
- ✅ T011: 更新使用说明和微信素材约束已完成

**Phase 5: Acceptance And Closeout Prep**
- ✅ T012: 记录验证证据和剩余风险已完成
  - 创建 `acceptance.md`
  - 三维 Verdict：Component ✅ PASS, Workflow ✅ PASS (with limitations), User-visible ⚠️ PENDING (live smoke)
  - 6 个 residual risks 已记录（high: 2, medium: 2, low: 2）
  - FR/NFR 100% 覆盖
  - 提供首次使用建议

**Implementation Complete**: 所有 12 个任务（T001-T012）已完成！

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-asset-upload/spec.md` | 固定需求边界：不新增 MCP、单 tool、支持本地路径和远程 URL、不扫描文章、不支持 base64。 | implement | yes |
| `specs/wechat-asset-upload/plan.md` | 固定方案和 ADR：MCP 物化图片字节、ECS adapter 调微信 API、统一 `/assets` endpoint、cover 使用 `type=thumb`。 | implement | yes |
| `specs/wechat-asset-upload/tasks.md` | 固定任务顺序、切片边界和验证点。 | implement | yes |
| `packages/wechat-draft/src/server.ts` | 现有 MCP tool 注册模式、账号校验和 draft tool 边界。 | implement | yes |
| `packages/wechat-draft/src/wechat/WechatAdapterClient.ts` | 现有 NAS/MCP 到 ECS adapter 的 HTTP client、错误映射和 fetch helper。 | implement | yes |
| `packages/wechat-draft-adapter/src/server.ts` | 现有 ECS adapter route、authMiddleware、validateAccount 和 draft endpoint 模式。 | implement | yes |
| `packages/wechat-draft-adapter/src/wechat/WeChatApiClient.ts` | 现有微信 API client、TokenManager 复用和 token retry 行为。 | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-asset-upload/spec.md` | 验证 US/FR/NFR 是否满足，尤其是“不新增 MCP”和“不扫描文章”。 | verify | yes |
| `specs/wechat-asset-upload/plan.md` | 检查实现是否偏离 ADR、质量属性和 Producer-Consumer Matrix。 | verify | yes |
| `specs/wechat-asset-upload/tasks.md` | 检查每个任务的完成范围和 fresh evidence。 | verify | yes |
| `packages/wechat-draft/src/workflow/DraftWorkflow.ts` | 验证 `wechat_create_draft` 未被改成隐式上传素材。 | verify | yes |
| `packages/wechat-draft/src/wechat/DraftPayloadBuilder.ts` | 验证草稿创建仍只消费 WeChat-ready artifact。 | verify | yes |
| `packages/wechat-draft/src/hermes/ArtifactValidator.ts` | 验证上传结果与现有 `wechat_asset_manifest` 校验契约兼容。 | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| https://developers.weixin.qq.com/doc/service/guide/product/asset.html | 微信服务号素材管理入口，确认 `uploadimg` 与 `add_material` 均属于素材管理能力。 | plan / implement / verify | yes |
| https://developers.weixin.qq.com/doc/service/api/material/permanent/api_uploadimage.html | 官方正文图片上传接口：`POST /cgi-bin/media/uploadimg`，formdata `media`，返回 `url`，jpg/png 且 1MB 以下。 | plan / implement / verify | yes |
| https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial.html | 官方永久素材接口：`POST /cgi-bin/material/add_material`，`type=thumb` 返回 `media_id`；thumb JPG 且 64KB。 | plan / implement / verify | yes |

---

## Rules

- `Required = yes` 的本地文件不存在时，当前阶段必须回退到 `plan` 或 `tasks` 更新 manifest。
- 不把所有待修改源文件当成固定 context；这里只列实现和验证必须先理解的高信号文件。
- 不复制长文档；只记录路径、来源、用途和短摘要。
- 不引入 `.trellis/`、Trellis CLI、hook、task.py 或自动 context injection。
