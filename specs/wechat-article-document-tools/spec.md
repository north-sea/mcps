# Feature Specification: WeChat Article Document Tools

**Workspace**: `wechat-article-document-tools`
**Created**: 2026-06-27
**Status**: Draft
**Input**: Roadmap next feature after `wechat-draft-agent-contract-hardening`: expose existing article document import/render/preview/build capabilities as MCP tools so agents do not hand-roll Tiptap JSON or WeChat HTML.

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | 工具承接 markdown/source article -> article_document -> rendered HTML/preview -> publish_ready `wechat_api_article` 的准备链路，但不创建草稿。 |
| `external-side-effects` | ❌ | 本 feature 只做纯转换、校验和 artifact payload 构造；不调用 WeChat API、不上传素材、不写 hermes-db。 |
| `artifact-handoff` | ✅ | 输入/输出均围绕 `article_document` 与 `wechat_api_article` artifact 形态，供 hermes-db 和 `wechat_create_draft` 后续消费。 |
| `user-visible-output` | ✅ | 返回 HTML preview、Markdown preview、validation errors、publish-ready artifact payload，直接影响 agent 和运营校对。 |
| `prior-closure-failure` | ✅ | 上一轮复盘中 `content_text` object/string、手搓 Tiptap、手写 HTML 渲染是明确失败点。 |
| `bugfix-loop-breaker` | ✅ | 目标是切断 agent 重复手写转换和绕过 `content_ref` 限制的失败循环，需要 before/after 证据和扩散检查。 |

**结论**: 本 feature 启用 workflow、artifact handoff、user-visible output 和 bugfix-loop-breaker 强化规则。下游 plan 必须证明复用现有 render modules，不重复实现写作生成、图片上传、草稿创建或 note skill migration。

---

## User Scenarios & Testing

### User Story 1 - Import Markdown To Article Document (Priority: P1)

作为 agent，我希望把已准备好的 markdown 与素材清单转换为 canonical `article_document`，以便不用手写 Tiptap/ProseMirror JSON。

**Why this priority**: 当前失败链路里 agent 需要手写 Python 拆 markdown、构造 Tiptap 节点；这既脆弱又不可发现。

**Acceptance Scenarios**:

1. **US1-1 import simple markdown**
   **Given** agent 提供 markdown、title/author/digest 和已准备好的 `body_images` 清单
   **When** 调用 article document import tool
   **Then** 返回 `schema_version=article_document.tiptap.v1` 的 document object、assets map、title 和 validation result。

2. **US1-2 missing prepared image is actionable**
   **Given** markdown 中包含图片引用但 `body_images` 数量不足
   **When** 调用 import tool
   **Then** 返回结构化错误，提示先准备/上传对应正文图，而不是抛出不可恢复的 generic exception。

**Edge Cases**:

- **US1-3** frontmatter 应被忽略或只作为后续显式字段输入的补充，不应产生不透明字段。
- **US1-4** import tool 不负责下载、压缩、上传图片，只接受已准备好的 asset metadata。

### User Story 2 - Validate And Preview Article Document (Priority: P1)

作为 agent 或运营，我希望在创建 publish-ready artifact 前校验并预览文章文档，以便及时发现无效节点、缺失 asset_ref 或样式渲染问题。

**Why this priority**: 当前 `wechat_validate_publish_artifact` 只验证下游 `wechat_api_article`，不能让 agent 在 article_document 阶段自检。

**Acceptance Scenarios**:

1. **US2-1 validate canonical document**
   **Given** agent 提供 `article_document` object 或 JSON string
   **When** 调用 validate tool
   **Then** 返回 `valid=true/false`、errors 数组、schema version 和可选 normalized document。

2. **US2-2 render HTML preview**
   **Given** document 中的图片 asset 已包含 `wechat_url`
   **When** 调用 render/preview tool
   **Then** 返回 WeChat-ready HTML、consumed image refs、warnings；不写入 hermes-db，不创建草稿。

**Edge Cases**:

- **US2-3** unsupported Tiptap node/mark 必须返回 field/path + issue，而不是泄露 renderer stack。
- **US2-4** 缺少图片 `wechat_url` 时应提示先调用 asset preparation/upload，不应生成不可发布 HTML。
- **US2-5** preview 可返回 Markdown/HTML，但必须标记非 canonical preview，source of truth 仍是 article_document。

### User Story 3 - Build Publish-Ready WeChat Artifact Payload (Priority: P1)

作为 agent，我希望从 canonical `article_document` 构造 `publish_ready` 的 `wechat_api_article` artifact payload，以便后续直接 upsert 到 hermes-db 并调用 `wechat_create_draft`。

**Why this priority**: 上一轮失败证明 agent 手写 HTML 和 artifact metadata 容易与 draft payload builder 契约错位。

**Acceptance Scenarios**:

1. **US3-1 build artifact payload**
   **Given** `article_document` 包含 cover `thumb_media_id` 和正文图片 `wechat_url`
   **When** 调用 build tool
   **Then** 返回可传给 hermes `upsert_workflow_artifact` 的 `stage=publish_ready`、`type=wechat_api_article`、`content_text=HTML`、`metadata.cover.thumb_media_id` 和 `wechat_asset_manifest`。

2. **US3-2 missing cover thumb is actionable**
   **Given** document 缺少 `cover.thumb_media_id`
   **When** 调用 build tool
   **Then** 返回 `next_action=upload_cover_image` 或等价恢复动作，说明 build draft artifact 前必须准备 cover thumb。

**Edge Cases**:

- **US3-3** build tool 不直接调用 hermes-db upsert；它只返回 payload，让 agent 明确选择 artifact id/version。
- **US3-4** 输出 hash/size 必须与 HTML content 一致，避免下游 upsert idempotency 误判。

### User Story 4 - Keep Tool Contracts Agent-Friendly (Priority: P2)

作为维护者，我希望这些新 tools 的输入输出都是 typed、discoverable、documented 的，以便后续 publish-ready facade 可以复用它们，而不是再次引入隐式约定。

**Why this priority**: 当前修复已经建立 `constraints` 和 remediation envelope，本 feature 应沿用而不是发明第二套结果格式。

**Acceptance Scenarios**:

1. **US4-1 tools are registered in MCP server**
   **Given** WeChat draft MCP 启动
   **When** agent lists tools
   **Then** 能看到 article document import/validate/render/build tools，描述中明确“不上传素材、不创建草稿”。

2. **US4-2 errors use existing remediation envelope**
   **Given** import/render/build 遇到可恢复输入错误
   **When** tool 返回失败
   **Then** 响应沿用 `code/message/details/next_action/remediation_hint/retryable/current_phase`。

**Edge Cases**:

- **US4-3** 不应新增与 `note-skill-migration-roadmap` 重叠的写作、改稿、选题、风格审稿工具。
- **US4-4** 不应把 Markdown 作为 canonical 存储格式；Markdown 只是 import/export 辅助格式。

---

## Requirements

### Functional Requirements

- **FR-001**: MCP 必须暴露 markdown -> `article_document` 的 typed import tool，复用现有 `MarkdownArticleImporter`。
- **FR-002**: MCP 必须暴露 `article_document` validate tool，返回结构化 validation result 和 actionable errors。
- **FR-003**: MCP 必须暴露 HTML/preview render tool，复用现有 `WechatArticleDocumentRenderer` / exporter，并返回 consumed asset refs 与 warnings。
- **FR-004**: MCP 必须暴露 `article_document` -> `wechat_api_article` publish-ready artifact payload builder，复用现有 `ArticleDocumentToWechatArtifactBuilder`。
- **FR-005**: 新 tools 必须沿用当前 `Result`/error remediation envelope，保持 MCP transport 输出与现有 tools 一致。
- **FR-006**: 工具文档和示例必须展示真实 payload 形态，尤其是 object vs JSON string、`content_text` HTML、artifact metadata 的边界。
- **FR-007**: 新 tools 必须有 unit/contract tests 覆盖 happy path、缺图、缺 cover、无效 doc、unsupported node/mark、MCP registration。

### Non-Functional Requirements

- **NFR-001**: 不依赖真实 WeChat、hermes-db 或网络写操作；测试使用 fixture。
- **NFR-002**: 转换输出必须 deterministic，同一输入产生相同 HTML/hash/metadata 关键字段。
- **NFR-003**: 错误不得泄露完整本地路径、token、HTTP header 或 renderer stack trace。
- **NFR-004**: 保持现有 `wechat_create_draft` 边界：它仍只消费 `publish_ready` 的 `wechat_api_article` artifact。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 一致性 | tools 输出与现有 render/build modules 一致 | 避免 agent 和库层渲染分叉 | 同 fixture 同输出；tests 直接覆盖 module reuse | 是 |
| 可恢复性 | 所有输入错误给出 next action | 减少 agent 探索重试 | error mapping tests | 是 |
| 可演进性 | 后续 facade 可组合这些 tools | roadmap 依赖本 feature | plan 明确 facade 不重复转换逻辑 | 是 |
| 安全性 | 无外部写副作用和敏感泄露 | 工具可放心用于 dry-run/preview | annotations/readOnly 或非 destructive 设计；测试/审查 | 是 |

### Key Entities

- **ArticleDocumentEnvelope**: canonical `article_document.tiptap.v1` object，包含 title、doc、assets、cover、style metadata。
- **Prepared Article Asset**: 已上传/准备好的图片 metadata；正文图需要 `wechat_url`，封面需要 `thumb_media_id`。
- **Render Output**: HTML preview/publish HTML、consumed body images、warnings。
- **Publish-Ready Artifact Payload**: 可传给 hermes upsert 的 `stage=publish_ready`、`type=wechat_api_article` artifact 参数集合。

---

## Out of Scope

- 不生成文章内容、标题、摘要或风格建议。
- 不做 note skill migration、Library/Memory ingestion、agent workflow ownership 决策。
- 不上传、下载、压缩图片；这些属于 `wechat-draft-asset-preflight`。
- 不调用 hermes-db upsert，不创建 workflow run，不管理 artifact version。
- 不调用 WeChat API，不创建、更新、删除草稿；这些属于后续 facade 或 ops CRUD。
- 不改变 `wechat_create_draft` 只接受 `wechat_api_article` 的边界。
- 不把 Markdown 作为 canonical artifact schema。

---

## Unclear Questions

- 是否把 import/validate/render/build 做成 4 个独立 tools，还是合并 validate+render 为一个 preview tool？初始倾向：独立 tools，便于 agent 组合和测试。
- build tool 输入是否直接接受 `WorkflowArtifact` 形态，还是接受 `article_document` object + artifact metadata。初始倾向：两种输入至少支持 object + metadata，避免强依赖 hermes fetch。
- HTML preview 是否需要返回完整 HTML 字符串，还是同时返回 truncated preview。初始倾向：返回完整 HTML，并提供 preview_text/hash/size 便于确认。

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项：无。上述 unclear questions 可在 plan 阶段通过轻量 ADR 固化，不需要回到用户澄清。
