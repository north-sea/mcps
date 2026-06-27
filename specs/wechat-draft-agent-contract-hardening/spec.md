# Feature Specification: WeChat Draft Agent Contract Hardening

**Workspace**: `wechat-draft-agent-contract-hardening`
**Created**: 2026-06-27
**Status**: Draft
**Input**: 用户描述: "其他 agent 在公众号 MCP 发草稿全流程中遇到契约不一致、错误不指路、约束不可发现、artifact upsert 幂等反馈不足等问题；需要规划 agent-friendly 改动。"

> 写入本文件后，应同步更新 `specs/.active` 指向当前 workspace。

---

## Feature Traits *(LM 自动检测，用户可 override)*

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | 草稿创建链路包含资产上传、artifact 构建、validate、create draft、ledger/job 状态等多个阶段。 |
| `external-side-effects` | ✅ | 涉及上传微信素材、创建微信草稿、写入 hermes-db workflow artifacts。 |
| `artifact-handoff` | ✅ | `article_document`、`wechat_api_article`、uploaded asset、workflow run/job 在多个工具之间传递。 |
| `user-visible-output` | ✅ | 最终输出是运营可见的微信草稿和 agent 可读的工具响应。 |
| `prior-closure-failure` | ✅ | 已有真实发草稿流程出现多轮重试、隐式契约和错误不可恢复问题。 |
| `bugfix-loop-breaker` | ✅ | 问题表现为重复踩坑和错误恢复循环，需要从契约、验证和错误信封层面阻断复发。 |

**结论**: 下游 plan 需要 Producer-Consumer Matrix、bugfix strategy、Evidence Gate、Workflow Replay 和三维 Verdict。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agent can discover constraints before calling write tools (Priority: P1)

作为调用 WeChat MCP 的 agent，我希望在发草稿前读取账号和工具约束，以便避免靠失败重试学习图片大小、MIME、路径和内容限制。

**Why this priority**: 当前失败链路中多次重试来自约束不可发现，修复后能立刻降低调用次数和错误率。

**Acceptance Scenarios**:

1. **US1-1 constraints are returned with accounts**
   **Given** 已配置 WeChat account
   **When** agent 调用 `wechat_list_accounts`
   **Then** 每个 account 返回 `constraints`，至少包含 cover/body image size、MIME、content limits、accepted path/source 语义。

2. **US1-2 constraints match enforced validation**
   **Given** `wechat_upload_asset` 对图片大小和 MIME 有本地 guard
   **When** constraints 暴露给调用方
   **Then** 返回的限制与实际 guard 保持一致，并有测试覆盖 drift。

**Edge Cases**:

- **US1-3** 未配置 `ASSET_ROOT` 时，constraints 应明确 local path 不可用或需要的 accepted prefix。
- **US1-4** 未经验证的微信能力不得作为确定 constraints 暴露，只能记录为 unsupported 或 experimental。

### User Story 2 - Agent receives actionable remediation on failures (Priority: P1)

作为 agent，我希望工具失败时知道下一步应该调用什么、修什么字段、是否可以重试，以便不用解析 SQL/内部代号/实现细节。

**Why this priority**: 当前错误如 `workflow_artifacts_run_id_fkey`、`artifact_id_conflict`、`T013 limitation` 不能指导 agent 恢复。

**Acceptance Scenarios**:

1. **US2-1 public errors include remediation fields**
   **Given** 工具返回失败
   **When** 失败可由调用方修复
   **Then** 响应包含 `code`、`message`、`next_action`、`remediation_hint`、`retryable`，并在适用时包含 `current_phase`。

2. **US2-2 internal implementation names are not exposed**
   **Given** `create_draft` 遇到 content-ref-only artifact
   **When** 返回错误
   **Then** 错误不包含内部 ticket/code name，而是说明当前只支持 inline `content_text` 以及恢复动作。

3. **US2-3 foreign-key and conflict errors map to agent actions**
   **Given** artifact upsert 发现缺失 workflow run 或 artifact id/hash 冲突
   **When** hermes-db MCP 返回错误
   **Then** agent 能从结构化字段判断是先 upsert workflow run、复用现有 artifact、还是创建新版本。

**Edge Cases**:

- **US2-4** 不可恢复的 adapter/API 错误必须标记 `retryable=false` 或说明人工介入条件。
- **US2-5** 错误详情不得泄露 token、完整本地路径或敏感 HTTP header。

### User Story 3 - Artifact idempotency and conflicts are explicit (Priority: P2)

作为 agent，我希望 hermes artifact upsert 明确告诉我是否发生幂等命中、哪些字段被跳过、现有 hash 与输入 hash 是否一致，以便避免误以为内容已更新。

**Why this priority**: 当前 hash short-circuit 会返回 `created=false`，但不说明 `content_text` 等字段未更新，导致 agent 只能换 artifact id。

**Acceptance Scenarios**:

1. **US3-1 idempotency hit is visible**
   **Given** 相同 hash 的 artifact 已存在
   **When** agent 再次 upsert
   **Then** 响应明确包含 `idempotency_hit=true`、`skipped_update_reason` 和现有 artifact 摘要。

2. **US3-2 conflict is actionable without blind overwrite**
   **Given** 相同 `artifact_id` 但内容 hash 不同
   **When** upsert 失败
   **Then** 响应包含现有/输入 hash 摘要和建议动作，不提供破坏审计语义的裸 `force_update` 作为默认方案。

**Edge Cases**:

- **US3-3** 若后续引入版本化，本 feature 只定义当前冲突反馈，不实现完整版本链。

### User Story 4 - The happy path is documented as executable tool calls (Priority: P2)

作为维护者或 agent，我希望文档展示真实 MCP tool 参数形态，以便不会被示例中的 JSON object/string 差异误导。

**Why this priority**: 现有示例和实际调用层对 `content_text` 的形态容易产生歧义。

**Acceptance Scenarios**:

1. **US4-1 examples use actual transport payload shape**
   **Given** 文档说明 `content_text`
   **When** 示例传递 article document 或 rendered HTML
   **Then** 示例明确说明 string/object 边界，必要时使用 typed helper 或 stringify 入口。

2. **US4-2 standard flow has a short canonical example**
   **Given** agent 需要从 publish-ready artifact 创建草稿
   **When** 阅读文档
   **Then** 能看到 list constraints、upsert run/artifact、validate、create draft 的最短成功路径和常见恢复动作。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `wechat_list_accounts` 必须返回 account-level `constraints`，覆盖当前 tool guard 会拒绝的主要输入条件。
- **FR-002**: WeChat draft MCP 的公开失败响应必须支持 agent-facing remediation fields，并保持现有 `code/message` 的兼容性。
- **FR-003**: `content_ref` only artifact 在 validate 或 create draft 前必须得到明确、可恢复的错误，不得暴露内部代号。
- **FR-004**: hermes workflow artifact upsert 必须在幂等命中和 artifact id/hash 冲突时返回结构化上下文。
- **FR-005**: 文档和示例必须以真实 MCP tool 参数为准，避免把实际应为 string 的 `content_text` 展示成可直接传入的 object。
- **FR-006**: 所有新增错误/constraints 字段必须有单元测试或 contract test 覆盖，防止实现与文档漂移。

### Non-Functional Requirements

- **NFR-001**: 变更必须向后兼容现有 tool 名称和主要响应字段。
- **NFR-002**: 测试不得依赖真实 WeChat 写操作；外部副作用路径使用 mock/fixture 或明确的 smoke 证据。
- **NFR-003**: 错误响应不得泄露 token、敏感 header、完整私有文件路径或原始 SQL 细节。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 可恢复性 | 常见失败都有下一步动作 | agent 需要自愈而不是反复试错 | error contract tests | 是 |
| 一致性 | constraints 与实际 validator 一致 | 避免文档/能力漂移 | schema/service tests | 是 |
| 可演进性 | 后续 E2E facade 可复用同一 contract | 避免第二套错误语义 | plan 中定义 envelope 边界 | 是 |
| 安全性 | 错误和日志不泄露敏感数据 | 工具可能运行在远端 HTTP MCP | redaction tests | 是 |

### Key Entities *(if applicable)*

- **AccountConstraints**: 每个 account 暴露给 agent 的能力约束集合。
- **ToolErrorEnvelope**: 包含 code、message、next_action、remediation_hint、retryable、current_phase 的公开错误结构。
- **ArtifactUpsertOutcome**: hermes-db upsert 的结果摘要，区分 created、idempotency hit、conflict 和 skipped fields。

---

## Out of Scope *(if applicable)*

- 不实现端到端 `wechat_create_draft_e2e` facade。
- 不实现自动压图流水线，只暴露约束和更清晰错误；压缩作为后续 feature。
- 不迁移 `note` skills，不创建 skill inventory/migration matrix，不决定 agents 仓业务 workflow 归属。
- 不把写作生成、标题改写、润色、审稿、选题、文风评估等模型强相关能力沉到 MCP。
- 不实现 Library/Wiki ingestion 或 Memory capture pipeline；这些属于 `note-skill-migration-roadmap` 或知识库流程。
- 不放宽正文图 1MB 限制，除非官方 `media/uploadimg` 文档变化。
- 不直接把封面从 `thumb` 通道切换为 `image` 通道，除非 live evidence 证明 `draft/add.thumb_media_id` 接受该 media id。
- 不实现完整 artifact version chain、rollback、draft CRUD、定时发布或群发。

---

## Unclear Questions *(if applicable)*

- `content_text` 被 `{` 开头字符串解析成 object 的根因是在 MCP client、transport wrapper 还是 hermes-db tool binding 层，需要 plan 阶段定位。
- `content_text` inline 存储上限和 MCP payload 实际可承受大小需要用现有 schema/config 进一步确认。
- artifact conflict 的 diff 粒度需要在 plan 阶段确定：hash-only、metadata summary，还是小体积文本 diff。

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项（如有）：无。上述问题影响方案细节，但不阻塞 plan。
