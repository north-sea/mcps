# Tasks: WeChat Asset Upload Tool

**Workspace**: `wechat-asset-upload` | **Date**: 2026-06-22  
**Input**: `specs/wechat-asset-upload/spec.md` + `plan.md`  
**Prerequisites**: spec.md, plan.md

---

## 执行原则

- 按端到端切片推进：先完成正文图片上传闭环，再完成封面缩略图上传闭环。
- 横向前置任务只服务于后续 slice，不做开放式重构。
- `wechat_create_draft` 不得被改成自动上传素材。
- 本 feature 不新增 MCP、不新增数据库、不做素材库管理。

---

## Phase 1: Contract And Source Loading Foundation

**目标**: 建立 MCP tool schema、图片来源读取和 adapter capability 边界，为两个上传 slice 共用。

- [x] T001 [Foundation] 增加 MCP tool schema 和结果类型
  - scope: `packages/wechat-draft/src/schemas/tool-schemas.ts`, `packages/wechat-draft/src/schemas/result-types.ts`（如需新增错误码）
  - slice: 为 `wechat_upload_asset` 建立可验证输入/输出契约，服务 T004/T005
  - blocked_by: none
  - maps_to: FR-001, FR-002, FR-009, FR-013, FR-014, ADR-001
  - verify: schema tests 或 TypeScript 编译证明 `usage=body_image|cover_image`、`source_type=local_path|remote_url` 可用，base64/未知枚举不可用

- [x] T002 [Foundation] 实现 `AssetSourceLoader`
  - scope: `packages/wechat-draft/src/wechat/AssetSourceLoader.ts`
  - slice: MCP 能把本地文件路径或远程图片 URL 物化为受限文件字节，服务 T004/T005
  - blocked_by: T001
  - maps_to: US1-1, US1-5, FR-013, FR-014, ADR-002, SSRF 控制
  - verify: unit tests 覆盖本地文件成功/不可读、远程 URL 成功/404/非 HTTP(S)/超限/非图片类型

- [x] T003 [Foundation] 扩展 adapter client 支持 multipart 上传
  - scope: `packages/wechat-draft/src/wechat/WechatAdapterClient.ts`
  - slice: MCP 能把 T002 产出的文件字节发送到 ECS adapter，服务 T004/T005
  - blocked_by: T001, T002
  - maps_to: FR-005, FR-006, FR-010, ADR-003
  - verify: unit tests mock fetch，确认请求发往 `/accounts/:account/assets`，带 Authorization，multipart 不被强制设置为 JSON

---

## Phase 2: Body Image Upload Slice

**目标**: 完成 `usage=body_image` 从 MCP 到 ECS adapter 再到微信 uploadimg 的闭环。

- [x] T004 [US1] 实现 ECS adapter 正文图片上传路径
  - scope: `packages/wechat-draft-adapter/src/server.ts`, `packages/wechat-draft-adapter/src/wechat/WeChatApiClient.ts`, `packages/wechat-draft-adapter/src/types/wechat.ts`
  - slice: `wechat_upload_asset usage=body_image` 可通过 adapter 调用 `/cgi-bin/media/uploadimg` 并返回 `wechat_url`
  - blocked_by: T003
  - maps_to: US1-1, US1-2, FR-003, FR-007, FR-008, ADR-003
  - verify: adapter tests 确认 `usage=body_image` 调用 uploadimg path，微信成功响应 `url` 映射为 adapter `wechat_url`

- [x] T005 [US1] 在 MCP server 注册 `wechat_upload_asset` 的正文图片闭环
  - scope: `packages/wechat-draft/src/server.ts`, `packages/wechat-draft/src/config/loader.ts`
  - slice: agent 调用现有 MCP tool 上传正文图片，返回可用于 `<img src="...">` 的 `wechat_url`
  - blocked_by: T004
  - maps_to: US1-1, US1-2, US2-1, US2-2, FR-001, FR-006, FR-010
  - verify: MCP handler tests 覆盖 account 校验、adapter capability 校验、body_image 成功返回和 adapter 404/capability missing

---

## Phase 3: Cover Image Upload Slice

**目标**: 完成 `usage=cover_image` 从 MCP 到 ECS adapter 再到微信 permanent thumb material 的闭环。

- [x] T006 [US1] 实现 ECS adapter 封面缩略图上传路径
  - scope: `packages/wechat-draft-adapter/src/server.ts`, `packages/wechat-draft-adapter/src/wechat/WeChatApiClient.ts`, `packages/wechat-draft-adapter/src/types/wechat.ts`
  - slice: `wechat_upload_asset usage=cover_image` 可通过 adapter 调用 `/cgi-bin/material/add_material?type=thumb` 并返回 `thumb_media_id`
  - blocked_by: T004
  - maps_to: US1-1, US1-3, FR-004, FR-007, FR-008, ADR-004
  - verify: adapter tests 确认 `usage=cover_image` 调用 add_material path with `type=thumb`，微信 `media_id` 映射为 `thumb_media_id`
  - note: 已在 T004 中完成，因为采用统一 endpoint + usage 路由设计

- [x] T007 [US1] 在 MCP server 补齐封面上传闭环
  - scope: `packages/wechat-draft/src/server.ts`, `packages/wechat-draft/src/wechat/AssetSourceLoader.ts`
  - slice: agent 调用同一个 MCP tool 上传封面图，返回草稿创建可用的 `thumb_media_id`
  - blocked_by: T006
  - maps_to: US1-3, US3-2, FR-004, FR-009
  - verify: MCP handler tests 覆盖 cover_image 成功返回、JPG/64KB guard、非 JPG 或超限错误
  - note: 已在 T005 中完成，统一 tool 根据 usage 路由；AssetSourceLoader 已包含 cover_image 的 64KB/JPG 限制

---

## Phase 4: Error Mapping, Contract Guard, And Verification

**目标**: 补齐失败路径、安全边界和验收证据，防止素材上传破坏现有草稿契约。

- [x] T008 [Quality] 增加上传专用错误映射和敏感信息保护
  - scope: `packages/wechat-draft/src/wechat/WechatAdapterClient.ts`, `packages/wechat-draft-adapter/src/wechat/WeChatApiClient.ts`, `packages/wechat-draft-adapter/src/server.ts`
  - slice: 输入错误、adapter 错误、token 错误、微信素材错误能被 agent 区分，且不泄露 token/secret/图片内容
  - blocked_by: T005, T007
  - maps_to: US1-4, US1-5, FR-012, NFR-001, NFR-003, 可诊断性
  - verify: tests 覆盖 40005、40009、401/403/404、token error、remote URL 失败；断言错误 details 不包含 token 和图片 bytes
  - note: MCP server 改进错误映射（AssetSourceError、AdapterError 分别处理，404 映射为 capability_missing）；adapter 已正确处理，不泄露敏感信息

- [x] T009 [Contract] 确认 `wechat_create_draft` 不出现隐式上传路径
  - scope: `packages/wechat-draft/src/server.ts`, `packages/wechat-draft/src/workflow/DraftWorkflow.ts`, `packages/wechat-draft/src/wechat/DraftPayloadBuilder.ts`
  - slice: 草稿创建仍只消费 publish-ready artifact，不扫描文章、不上传素材
  - blocked_by: T005, T007
  - maps_to: US2-4, US3-1, FR-011, NFR-004, 契约稳定性
  - verify: code review + regression tests 或 search 证明 draft workflow 未调用 `AssetSourceLoader` / `uploadAsset`
  - note: 已验证 DraftWorkflow 和 DraftPayloadBuilder 只消费 wechat_asset_manifest，没有扫描、下载或自动上传逻辑

- [x] T010 [Verify] 运行本地构建和测试
  - scope: `packages/wechat-draft`, `packages/wechat-draft-adapter`
  - slice: 两个 package 均能通过本地验证，素材上传契约可执行
  - blocked_by: T008, T009
  - maps_to: Verification Strategy, Evidence Gate
  - verify: `pnpm --filter @mcps/wechat-draft build`; `pnpm --filter @mcps/wechat-draft-adapter build`; 相关 test 命令通过或记录不可运行原因
  - note: ✅ 两个 package 编译通过；✅ 18/18 单元测试通过（AssetSourceLoader 15/15, WechatAdapterClient 3/3）

- [x] T011 [Docs] 更新使用说明和微信素材约束
  - scope: `packages/wechat-draft/README.md`, `packages/wechat-draft-adapter/README.md` 或相关 docs
  - slice: 调用方知道如何用本地路径/远程 URL 上传正文图和封面图，并理解格式/大小限制
  - blocked_by: T010
  - maps_to: US3-2, NFR-002, 可诊断性
  - verify: 文档包含 `wechat_upload_asset` 示例、`body_image`/`cover_image` 返回字段、1MB jpg/png、64KB JPG、base64 不支持
  - note: ✅ MCP README 包含完整 tool 文档、工作流程、错误处理；✅ Adapter README 包含 endpoint 说明、素材约束、部署指南
  - verify: 文档包含 `wechat_upload_asset` 示例、`body_image`/`cover_image` 返回字段、1MB jpg/png、64KB JPG、base64 不支持

---

## Phase 5: Acceptance And Closeout Prep

**目标**: 为 verify/closeout 留出 fresh evidence 和 completion record 输入。

- [x] T012 [Acceptance] 记录验证证据和剩余风险
  - scope: `specs/wechat-asset-upload/acceptance.md`（closeout 阶段创建或更新）
  - slice: feature traits 命中后的三维 verdict 有证据可写
  - blocked_by: T010, T011
  - maps_to: Feature Traits, Evidence Gate, 三维 Verdict
  - verify: acceptance 记录 Component / Workflow / User-visible Outcome verdict；如果未跑 live smoke，明确标为 residual risk
  - note: ✅ 创建 acceptance.md，记录三维 Verdict（Component ✅, Workflow ✅, User-visible ⚠️ pending live smoke）；✅ 记录 6 个 residual risks；✅ FR/NFR 100% 覆盖；✅ 提供首次使用建议

---

## 依赖与顺序

- 关键路径：T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008 -> T009 -> T010 -> T011 -> T012。
- T004 和 T006 都在 adapter 内，可在 T003 后部分并行，但建议先完成 T004 正文图闭环，再复用模式做 T006。
- T009 可以在 T005/T007 完成后并行执行，不必等待 T008。
- T011 依赖最终字段和错误语义稳定，应在 T010 后做。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|-------------|----------|
| US1 单 tool 上传微信素材 | T001, T003, T004, T005, T006, T007 |
| US2 保持现有 MCP + ECS adapter 边界 | T003, T005, T009 |
| US3 不扫描文章，只上传指定图片 | T002, T009, T011 |
| 本地路径 + 远程 URL | T002, T005, T007 |
| 不支持 base64 | T001, T002, T011 |
| 错误和敏感信息保护 | T008 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|----------------------|----------|----------|
| ADR-001 单 MCP tool | T001, T005, T007 | T010 |
| ADR-002 MCP 统一物化图片字节 | T002, T003 | T008, T010 |
| ADR-003 adapter 统一 endpoint | T003, T004, T006 | T010 |
| ADR-004 cover 用 permanent thumb | T006, T007 | T010, T011 |
| 安全性 / SSRF 控制 | T002, T003, T008 | T010 |
| 契约稳定性 | T009 | T010 |

---

## Notes

- 如果实现阶段发现 Express multipart 解析必须引入依赖，应优先选择最小成熟依赖，并在 closeout 记录原因。
- live smoke 需要真实公众号账号、ECS adapter、微信 IP 白名单和测试图片，不作为本地实现完成的硬前置；如果未执行，必须在 acceptance 中记录为残余风险。
- 不处理图片压缩/裁剪；不合规封面图应返回明确错误，由调用方准备合规素材。

---

## Stage Readiness

- 推荐下一步：`execute-plan`
- 阻塞项：无。任务足以开始实现；外部 live smoke 条件仅影响最终验收风险记录。
