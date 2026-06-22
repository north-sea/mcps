# Feature Specification: WeChat Asset Upload Tool

**Workspace**: `wechat-asset-upload`  
**Created**: 2026-06-22  
**Status**: Completed  
**Completed**: 2026-06-22  
**Input**: 用户希望素材上传功能直接放进现有微信 MCP：ECS 上的 `wechat-draft-adapter` 需要支持微信素材上传，现有 `wechat-draft` MCP 新增一个 tool，不新增 MCP；不需要扫描文章。

> 写入本文件后，应同步更新 `specs/.active` 指向当前 workspace。

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | 素材上传结果会被后续 publish-ready artifact 或 `wechat_create_draft` 草稿创建流程消费。 |
| `external-side-effects` | ✅ | 调用微信官方素材接口，会在公众号素材/图文图片系统产生真实外部副作用。 |
| `artifact-handoff` | ✅ | `wechat_upload_asset` 产出的 `wechat_url` 或 `thumb_media_id` 是后续正文组装、manifest 和草稿创建的输入。 |
| `user-visible-output` | ✅ | 上传后的封面素材和正文图片最终会出现在公众号后台草稿与文章内容中。 |
| `prior-closure-failure` | ✅ | 现有 `wechat-draft-mcp` 明确把素材上传留给上游，导致端到端草稿链路缺少官方 API 素材准备能力。 |
| `bugfix-loop-breaker` | ❌ | 本次是新增能力，不是复杂回归修复。 |

**结论**: 下游 plan 需要覆盖 Producer-Consumer Matrix；verify 需要 Evidence Gate；closeout 需要记录三维 Verdict 和 acceptance.md。

---

## User Scenarios & Testing

### User Story 1 - 通过现有 MCP 上传微信素材 (P1)

作为 Codex / Claude Code / Hermes 调用方，我希望直接通过现有 `wechat-draft` MCP 上传公众号素材，以便拿到后续草稿创建所需的微信素材引用。

**Why this priority**: 当前草稿 MCP 已经能消费 `wechat_asset_manifest`，但缺少从图片到微信素材引用的官方 API 前置能力。

**Acceptance Scenarios**:

1. **[US1-1] 单 tool 暴露上传能力**  
   **Given** `wechat-draft` MCP 已配置可用账号和 ECS adapter  
   **When** 调用 `wechat_upload_asset`，传入 `account`、`usage` 和本地文件路径或远程图片 URL  
   **Then** MCP 必须通过 ECS adapter 调用微信官方素材接口，并返回结构化上传结果。

2. **[US1-2] 正文图片上传**  
   **Given** `usage=body_image` 且图片格式、大小和账号配置合法  
   **When** 调用 `wechat_upload_asset`  
   **Then** 返回可用于正文 `<img src="...">` 的微信图片 URL，并标记 `usage=body_image`。

3. **[US1-3] 封面图片上传**  
   **Given** `usage=cover_image` 且图片格式、大小和账号配置合法  
   **When** 调用 `wechat_upload_asset`  
   **Then** 返回可用于草稿封面的永久素材 `thumb_media_id`，并标记 `usage=cover_image`。

**Edge Cases**:

- **[US1-4]** 账号不存在、禁用、ECS adapter 不可达、token 获取失败、微信 IP 白名单不匹配、权限不足或限流时，返回结构化错误和人工处理建议，不泄露 token、AppSecret 或完整 HTTP trace。
- **[US1-5]** 图片输入缺失、本地文件不可读、远程 URL 不可访问、格式不支持、体积超过微信限制、mime type 不可信或 adapter 无法读取图片时，MCP 必须拒绝上传或返回明确的 validation error。
- **[US1-6]** `usage` 不是 `body_image` 或 `cover_image` 时必须拒绝，不做隐式推断。

### User Story 2 - 保持现有草稿 MCP 边界 (P1)

作为维护者，我希望素材上传并入现有微信 MCP 和 ECS adapter，而不是新增一个 MCP，以便调用方仍使用同一个微信草稿能力入口。

**Why this priority**: 用户明确要求不新增 MCP；现有 adapter 已经是 AppSecret、AccessToken 和微信固定出口 IP 边界。

**Acceptance Scenarios**:

1. **[US2-1] 不新增 MCP 服务**  
   **Given** 当前仓库已有 `packages/wechat-draft` 和 `packages/wechat-draft-adapter`  
   **When** 实现素材上传功能  
   **Then** 只应扩展现有 MCP server 和 ECS adapter，不创建新的 MCP package。

2. **[US2-2] 微信 API 出口仍在 ECS adapter**  
   **Given** NAS 侧 MCP 不直接持有 AppSecret  
   **When** 调用 `wechat_upload_asset`  
   **Then** 所有微信官方素材 API 调用必须由 ECS adapter 发起。

**Edge Cases**:

- **[US2-3]** 如果 adapter 版本过旧或缺少素材上传 capability，MCP 应返回 `adapter_capability_missing` 类错误，而不是直接调用微信 API。
- **[US2-4]** 现有 `wechat_create_draft` 不应自动扫描正文、自动上传图片或隐式修改内容。

### User Story 3 - 不扫描文章，只上传调用方指定图片 (P2)

作为调用方，我希望本次 MVP 只处理明确传入的单个图片素材，以便上游流程自行决定图片位置、正文替换和 manifest 生成策略。

**Why this priority**: 用户明确说不需要扫描文章；这能降低副作用范围，避免草稿创建阶段隐式改写文章。

**Acceptance Scenarios**:

1. **[US3-1] 不解析正文内容**  
   **Given** 调用方只传图片输入和 `usage`  
   **When** 调用 `wechat_upload_asset`  
   **Then** MCP 不读取、扫描、解析或重写 Markdown/HTML 正文。

2. **[US3-2] 上传结果可被上游组装为 manifest**  
   **Given** 上传成功  
   **When** MCP 返回结果  
   **Then** 结果必须包含足够字段，使调用方能把正文图片 URL 或封面 `thumb_media_id` 写入 `wechat_asset_manifest`。

**Edge Cases**:

- **[US3-3]** 本次不做批量图片上传、正文 URL 替换、Markdown 渲染、图片压缩、图片去重、素材库查询或素材复用。
- **[US3-4]** 上传成功但后续 artifact 组装失败时，MCP 不负责回滚微信素材。

---

## Requirements

### Functional Requirements

- **FR-001**: 系统必须在现有 `wechat-draft` MCP 中新增 `wechat_upload_asset` tool，不新增独立 MCP。
- **FR-002**: `wechat_upload_asset` 必须支持 `usage=body_image` 和 `usage=cover_image`。
- **FR-003**: `usage=body_image` 成功时必须返回微信正文图片 URL。
- **FR-004**: `usage=cover_image` 成功时必须返回微信封面永久素材 `thumb_media_id`。
- **FR-005**: `wechat_upload_asset` 必须通过现有账号配置解析 account、adapter 和 adapter auth token。
- **FR-006**: `wechat_upload_asset` 必须调用 ECS `wechat-draft-adapter`，不得从 NAS MCP 直接调用微信官方素材 API。
- **FR-007**: ECS `wechat-draft-adapter` 必须新增素材上传能力，并复用现有 AccessToken 获取、缓存和刷新机制。
- **FR-008**: ECS adapter 必须按 `usage` 路由到对应微信官方素材接口；正文图片与封面永久素材的返回语义必须不同。
- **FR-009**: MCP 和 adapter 返回值必须包含 `account`、`usage`、上传状态、微信素材引用、时间和错误摘要。
- **FR-010**: MCP 必须在 adapter 不支持素材上传 capability 时返回结构化错误。
- **FR-011**: MCP 不得自动扫描文章、替换正文图片、生成完整 publish-ready artifact 或隐式调用 `wechat_create_draft`。
- **FR-012**: 系统必须避免在日志、错误和 MCP 输出中暴露 AppSecret、AccessToken、adapter auth token、完整图片内容和完整 HTTP trace。
- **FR-013**: `wechat_upload_asset` 必须支持本地文件路径和远程图片 URL 两种输入来源。
- **FR-014**: `wechat_upload_asset` MVP 不支持 base64 作为图片输入来源。

### Non-Functional Requirements

- **NFR-001**: 安全边界保持保守：微信 API 凭据和固定出口能力只在 ECS adapter 内部。
- **NFR-002**: 返回内容必须短小可操作，适合 agent 继续把结果写入 artifact metadata。
- **NFR-003**: 上传错误必须能区分调用方输入错误、adapter 配置错误、token 错误、微信 API 错误和网络错误。
- **NFR-004**: 该能力不得改变现有 `wechat_create_draft` 的 publish-ready artifact 契约。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 安全性 | token 和 AppSecret 不出 ECS adapter | 微信凭据泄露影响公众号安全 | 测试和日志审查确认不返回敏感值 | 是 |
| 可用性 | 单个 tool 覆盖正文图和封面图 | 降低 agent 调用复杂度 | MCP tools 列表和 schema 显示 `usage` 枚举 | 是 |
| 可诊断性 | 错误能定位到输入、adapter、token、微信 API | 素材上传失败常需要人工处理 | 单测覆盖错误映射；文档列出常见处理建议 | 是 |
| 契约稳定性 | 草稿创建继续只消费 ready artifact | 避免发布阶段隐式改写内容 | `wechat_create_draft` 无自动上传路径 | 是 |

### Key Entities

- **UploadAssetRequest**: MCP tool 输入。关键属性包括 `account`、`usage`、`source_type=local_path|remote_url`、图片来源、可选 `filename` 和 `mime_type`。
- **AssetUsage**: 图片用途枚举。仅允许 `body_image` 和 `cover_image`。
- **UploadedWechatAsset**: 上传结果。正文图片包含 `wechat_url`；封面图包含 `thumb_media_id`。
- **EcsWechatAdapterAssetEndpoint**: ECS adapter 上的私有 HTTP endpoint，负责认证、账号校验、AccessToken、微信素材 API 调用和错误映射。

---

## Out of Scope

- 新增独立 MCP package 或服务。
- 扫描 Markdown/HTML 正文、批量替换图片 URL、生成完整 `publish_ready` artifact。
- 把素材上传隐式并入 `wechat_create_draft`。
- 素材库管理、素材去重、复用查询、过期清理。
- 图片压缩、裁剪、水印、OCR、格式转换。
- 自动发布、群发、删除草稿、更新草稿。

---

## Unclear Questions

- adapter endpoint 设计采用一个 `/accounts/:account/assets` 统一 endpoint，还是内部拆成正文图片和封面素材 endpoint。该问题不影响用户层 tool 形态，可在 plan 阶段决定。

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项：无。adapter endpoint 形态、远程 URL 下载责任边界和传输方式可在 plan 阶段决策。
