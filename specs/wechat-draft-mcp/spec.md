# Feature Specification: WeChat Draft MCP

**Workspace**: `wechat-draft-mcp`  
**Created**: 2026-06-21  
**Status**: Clarified  
**Input**: 将 Hermes / Codex / Claude Code 可复用的微信公众号草稿箱写入能力抽成 MCP。官方微信公众号 API 是唯一写草稿路径。

---

## PRD Summary

`wechat-draft-mcp` 的目标是提供一个可复用、可审计、保守的微信公众号草稿箱写入能力。它消费上游写文 agent / style skill 已生成的 hermes-db publish-ready artifact，通过 Ali ECS 上的 WeChat API adapter 调用微信官方服务端 API 创建公众号草稿，并把草稿 `media_id` 和状态回写到本地 job summary 与 `hermes.wechat_articles`。

本 MCP 不负责选题、文章生成、文风改写、最终发布、群发或删除。MVP 只支持 `yueliang`，只创建草稿，不自动发布。

官方 API 是唯一 MVP 写入路径。MVP 部署边界是 NAS 侧 MCP + Ali ECS 侧 WeChat API adapter：微信后台 IP 白名单配置 ECS 公网 IP，NAS 通过私有网络通道调用 adapter。

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | publish-ready artifact 需要经过账号校验、AccessToken、素材/图片校验、草稿 API、结果回写。 |
| `external-side-effects` | ✅ | MCP 会调用微信官方 API 并创建真实草稿。 |
| `artifact-handoff` | ✅ | 上游交付 hermes-db workflow artifact，MCP 回写草稿 job 和 article ledger。 |
| `user-visible-output` | ✅ | 输出出现在公众号后台草稿箱，由用户人工校验和发布。 |

---

## Problem Statement

Hermes roadmap 中已有公众号草稿箱写入流程。微信官方服务号/公众号文档提供草稿管理 API，包括 `/cgi-bin/draft/add` 和 `/cgi-bin/draft/batchget`。

用官方 API 作为唯一写入路径，可以把风险集中在 AppSecret、AccessToken、IP 白名单、微信素材 ready 契约和 API 错误码处理。

由于 NAS 是家庭服务器，不能假设家宽公网出口 IP 稳定，也不能把 Tailscale `100.x` 内网地址配置到微信 IP 白名单。MVP 选择 Ali ECS 作为唯一微信 API 出口：公众号后台白名单填 ECS 公网 IP/EIP；ECS adapter 持有 AppID/AppSecret、缓存 AccessToken 并调用微信官方 API；NAS MCP 通过 Tailscale、WireGuard 或 SSH 内网通道调用 ECS adapter。

### Proposed Solution

在 `/Users/yqg/personal/AI/mcps` 下新增独立 `wechat-draft-mcp`。它对外提供：

- 账号列表与 API credential 配置检查。
- ECS adapter 连接检查、出口 IP/白名单说明和 API credential dry-run。
- publish-ready artifact 与微信素材 ready 契约校验。
- 经 ECS adapter 调用微信官方 `draft/add` 创建草稿。
- 返回 job 状态、草稿 `media_id`/定位信息，并回写 hermes-db article ledger。

MCP 的主输入是 `artifact_id`，不是完整正文。裸 Markdown 不作为 MVP 输入。

---

## User Scenarios & Testing

### User Story 1 - 通过官方 API 写入 `yueliang` 草稿箱 (P1)

作为 Hermes / Codex / Claude Code 调用方，我希望把一个已经准备好的发布 artifact 写入 `yueliang` 公众号草稿箱，以便我之后在公众号后台人工校验和发布。

**Acceptance Scenarios**:

1. **[US1-1] 成功创建草稿**  
   **Given** `yueliang` 的 AppID/AppSecret 已配置在 Ali ECS adapter，ECS 公网 IP 已加入微信 IP 白名单，`workflow_artifact` 已是 publish-ready  
   **When** 调用 `wechat_create_draft` 并传入 `artifact_id`  
   **Then** MCP 必须通过 ECS adapter 调用微信官方 `draft/add` 创建草稿，并返回 `job_id`、账号、标题、状态、时间和 `media_id`

2. **[US1-2] 不自动发布**  
   **Given** 草稿创建成功  
   **When** MCP 返回结果  
   **Then** 文章只能处于草稿箱状态，不得触发发布、群发、定时发布、删除草稿或更新草稿

**Edge Cases**:

- **[US1-3]** ECS adapter 不可达、AccessToken 获取失败、AppSecret 冻结、ECS IP 白名单不匹配、权限不足或 API 限流时，返回结构化错误和人工处理建议。
- **[US1-4]** 正文图片不是微信图文图片 URL、封面没有永久素材 `thumb_media_id`、正文过大或字段超限时，MCP 必须拒绝创建草稿，且不得在 `wechat_create_draft` 中下载或上传素材。
- **[US1-5]** 同一账号相同 artifact/idempotency key 重复调用时，不得静默创建重复草稿。

### User Story 2 - 跨 Agent 复用 (P1)

作为本机 Codex / Claude Code / Hermes 用户，我希望只要能创建 publish-ready artifact，就能用同一个 MCP 写入草稿箱。

**Acceptance Scenarios**:

1. **[US2-1] 标准 MCP tool 可发现**  
   工具 discovery 中必须看到清晰命名的草稿箱相关工具和参数说明。

2. **[US2-2] 调用方无需了解微信 API 细节**  
   调用方只传 `artifact_id` 和目标账号，不需要知道 ECS 出口、AccessToken 缓存、AppSecret、微信素材契约细节或微信错误码细节。

**Edge Cases**:

- **[US2-3]** MCP 无法访问 hermes-db、ECS adapter 或微信 API 时，错误必须指出缺失依赖。
- **[US2-4]** 未配置账号或账号禁用时，返回已配置账号或新增账号提示，不返回敏感值。

### User Story 3 - Publish-ready Artifact 契约 (P1)

作为写文 agent / style skill，我希望能把已排版、图片已处理的文章保存为标准 artifact，以便草稿 MCP 不再关心内容生产细节。

**Acceptance Scenarios**:

1. **[US3-1] Artifact 必须声明发布格式**  
   **Given** artifact 存在于 `hermes.workflow_artifacts`  
   **When** MCP 读取 artifact  
   **Then** artifact 必须包含可提交给微信 `draft/add` 的正文，推荐 `type=wechat_api_article`，并在 metadata 标明 `publish_ready=true`

2. **[US3-2] Artifact 必须声明素材元数据**  
   **Given** artifact 由写文 agent 生成  
   **When** MCP 校验 artifact  
   **Then** metadata 必须包含目标账号、标题、样式 profile/version、内容 hash、正文图片清单（每项已有微信图文图片 URL）、封面永久素材 `thumb_media_id`

**Edge Cases**:

- **[US3-3]** artifact 仍是裸 Markdown、目标账号不匹配、metadata 缺失或图片仍指向非微信图片 URL 时，MCP 必须拒绝写入。
- **[US3-4]** MCP 不对正文做二次样式渲染，避免发布阶段修改内容语义或视觉规范。

### User Story 4 - 草稿箱人工校验与 hermes-db 记录 (P1)

作为用户，我希望写入草稿后在公众号后台校验并发布，同时 hermes-db 能记录后续分析需要的 article ledger。

**Acceptance Scenarios**:

1. **[US4-1] 草稿箱作为人工预览入口**  
   MCP 成功创建草稿后，用户在公众号后台草稿箱人工预览、校验和发布。

2. **[US4-2] 成功后回写 article ledger**  
   MCP 成功创建草稿后，应创建或更新 `hermes.wechat_articles`，`status=drafted`，`draft_artifact_id=<publish_ready_artifact_id>`，metadata 记录微信草稿 `media_id`。

3. **[US4-3] 发布后再更新 published**  
   人工发布产生最终 URL 后，由后续确认流程把同一 article ledger 更新为 `status=published` 并补 `published_url` / 微信外部引用。

**Edge Cases**:

- **[US4-4]** MCP 失败时不要伪造 `drafted` article ledger；失败保留在 `DraftJob`、workflow run 日志或诊断 artifact 中。
- **[US4-5]** MCP 创建草稿阶段不能填 `published_url`，因为此时尚未人工发布。

---

## Requirements

### Functional Requirements

- **FR-001**: 系统必须提供 MCP server，供 Hermes、Codex、Claude Code 通过标准 MCP 配置调用。
- **FR-002**: 系统必须支持账号配置，MVP 至少支持 `yueliang`。
- **FR-003**: 系统必须通过微信官方服务端 API 作为唯一 MVP 写草稿路径。
- **FR-004**: 系统必须以 hermes-db `workflow_artifacts` 中的 publish-ready artifact 作为主输入。
- **FR-005**: `wechat_create_draft` MVP 必须要求 `artifact_id`，不接受裸 Markdown。
- **FR-006**: 系统必须校验 artifact 的 publish-ready metadata，包括目标账号、内容格式、微信素材 ready 图片清单、样式 profile/version。
- **FR-007**: 系统必须从 artifact 读取标题、正文、摘要、封面图片引用等写入所需字段；缺失时返回 validation error。
- **FR-008**: 系统必须支持 AccessToken 获取、缓存、过期刷新和错误映射。
- **FR-009**: 系统必须校验微信素材 ready 契约：正文图片必须是微信图文图片 URL，封面必须提供永久素材 `thumb_media_id`。
- **FR-009a**: `wechat_create_draft` 不得下载外部图片、读取本地图片或自动上传微信素材；缺素材时必须返回 `asset_validation` / `invalid_artifact` 类结构化错误。
- **FR-009b**: 系统必须在构建 `draft/add` payload 前拒绝非微信正文图片 URL，避免把不可用素材提交到微信 API。
- **FR-010**: 系统必须保证 MVP 不触发自动发表、群发、定时发布、删除草稿或更新草稿等高风险动作。
- **FR-011**: 系统必须返回结构化结果，包含账号、artifact、操作状态、时间、错误类型和人工处理建议。
- **FR-012**: 系统应提供草稿状态查询或最近草稿定位信息，便于用户在公众号后台找到 MCP 创建的草稿。
- **FR-013**: 系统应支持单账号任务串行化或幂等拒重。
- **FR-014**: 系统应为后续新增账号提供配置扩展点。
- **FR-015**: 所有 MVP 写草稿动作必须走官方 API，不提供替代写入路径。
- **FR-016**: 成功保存草稿后，系统应通过 hermes-db article ledger 写入 `status=drafted`、`draft_artifact_id`、微信 `media_id` 和 metadata。
- **FR-017**: MVP 必须支持 Ali ECS WeChat API adapter 作为微信官方 API 的唯一出站执行点，NAS MCP 不直接持有 AppSecret 或直连微信 API 创建草稿。
- **FR-018**: `wechat_check_api_credentials` 必须检查 ECS adapter 可达性、账号配置摘要、token dry-run 结果和 ECS 出口 IP 白名单提示，不返回 AppSecret、AccessToken 或完整 HTTP trace。

### Non-Functional Requirements

- **NFR-001**: 安全边界默认保守：只写草稿，不自动发布。
- **NFR-002**: 错误信息必须面向 agent 可操作。
- **NFR-003**: 所有外部副作用必须可审计，至少记录账号、artifact、标题、状态、微信 `media_id` 和时间。
- **NFR-004**: MCP 不应修改正文语义、样式或图片引用。
- **NFR-005**: 敏感配置不得硬编码，包括 AppID、AppSecret、AccessToken、adapter token、token cache、数据库连接。
- **NFR-006**: MCP 返回内容必须控制长度，避免返回完整正文、完整 token、完整 HTTP trace 或长日志。
- **NFR-007**: 系统必须能在 NAS Hermes 和本机 agent 两类运行环境中配置使用；微信 API 出口固定为 Ali ECS adapter。
- **NFR-008**: ECS adapter 必须只允许受信任客户端访问，默认通过 Tailscale/WireGuard/SSH 内网通道或等价私有网络，不提供开放公网代理。

### Quality Attributes

| 属性 | 目标 | 验收 / 证据 |
|---|---|---|
| 安全性 | 默认无发布能力 | 工具列表中没有 publish/mass_send/delete/update；端到端测试只产生草稿 |
| 出口稳定性 | 微信 API 请求从 Ali ECS 固定公网 IP 出口 | token dry-run / live smoke 证据记录 ECS 出口 IP 已进微信白名单 |
| 可复用性 | Hermes/Codex/Claude 共用同一 MCP | 至少两类客户端配置示例 |
| 可维护性 | 微信 API client 和错误映射集中封装 | API client 边界清晰，错误可诊断 |
| Artifact 契约稳定性 | MCP 只消费 publish-ready artifact | 裸 Markdown / 图片未 ready artifact 被拒绝 |
| 可观测性 | 每次写入有状态和摘要日志 | `wechat_get_draft_status` 可查 compact summary |

### Key Entities

- **Account**: 公众号账号配置。关键属性包括 `account_id`、`display_name`、启用状态、ECS adapter account ref、IP 白名单说明。
- **EcsWechatAdapter**: Ali ECS 上的微信 API 出口服务。关键属性包括 adapter base URL、auth ref、allowed account、egress public IP、health/token/draft capabilities。
- **AccessTokenState**: 微信 API 调用凭据状态。关键属性包括 token provider、过期时间、刷新结果和错误码。
- **PublishReadyArtifact**: 上游写文 agent 保存到 hermes-db 的发布产物。关键属性包括 `artifact_id`、`run_id`、`stage`、`type`、正文、title/digest/cover metadata、style profile/version、微信图片 manifest。
- **DraftJob**: 一次草稿写入任务。关键属性包括 job id、账号、artifact id、状态、时间、错误类型、草稿 `media_id`、人工处理建议。
- **ArticleLedgerUpdate**: MCP 成功后对 `hermes.wechat_articles` 的更新。关键属性包括 account、run_id、status=`drafted`、draft_artifact_id、title、metadata.media_id。

---

## MCP Tool Requirements

- **`wechat_list_accounts`**: 列出可用公众号账号和 API 配置摘要。
- **`wechat_check_api_credentials`**: 检查指定账号配置是否完整；可选执行 token dry-run。
- **`wechat_validate_publish_artifact`**: 读取并校验 artifact 是否可提交给微信草稿 API。
- **`wechat_create_draft`**: 根据 `artifact_id` 调用微信官方 API 创建草稿。
- **`wechat_get_draft_status`**: 查询一次写入任务的结果状态。

`wechat_create_draft` 是有副作用工具；它通过 ECS adapter 产生真实微信草稿。其他工具是只读或低副作用诊断工具。MVP 不提供命令行预览 tool，不提供样式渲染 tool，不接受裸 Markdown。

---

## MVP Scope & Phasing

### Phase 1: MVP

- 建立 `wechat-draft-mcp` 的 MCP server 和基础工具边界。
- 建立 Ali ECS WeChat API adapter，作为固定公网出口和 AppSecret/AccessToken 边界。
- 支持 `yueliang` 单账号 adapter 配置。
- 支持读取 hermes-db workflow artifact。
- 支持校验 `publish_ready=true` 的 `wechat_api_article` artifact。
- 支持校验微信素材 ready artifact：正文图片已是微信图文图片 URL，封面已是永久素材 `thumb_media_id`。
- 支持 ECS adapter 侧 AccessToken 获取/缓存/刷新。
- 支持通过 ECS adapter 调用 `draft/add` 创建草稿，返回微信 `media_id`。
- 成功保存草稿后写入或更新 `wechat_articles.status=drafted`。
- 明确禁止自动发布、更新草稿、删除草稿和非官方 API 写入能力。

**MVP Definition**: 调用方传入一个 publish-ready artifact id，NAS MCP 通过 Ali ECS adapter 调用微信官方 API，把文章保存到 `yueliang` 公众号草稿箱，并返回微信草稿 `media_id`；失败时返回可操作的 adapter / 微信 API 错误映射。

### Phase 2: Enhancements

- 多公众号账号配置。
- 草稿列表/草稿定位增强。
- WeCom 或其他通知渠道集成。

### Out of Scope

- 自动群发、发表、定时发布、删除草稿、更新草稿。
- 文章选题、生成、事实核查、改稿和文风控制。
- Markdown -> 微信 HTML 样式渲染。
- `wechat_create_draft` 内置图片下载、外部图床迁移、图片压缩、微信素材上传或 URL 替换。
- 非官方 API 的后台写入流程。
- 绕过微信 API 权限、IP 白名单、额度、风控或平台限制。
- 第一阶段支持多个公众号同时写入。

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation Strategy |
|---|---:|---:|---|
| AppSecret 泄露或误提交 | Medium | Critical | 只允许环境变量/secret manager；禁止日志和返回值泄露。 |
| AccessToken 无效、过期或非最新 | Medium | High | ECS adapter 缓存并按错误码刷新一次；返回可操作错误。 |
| ECS IP 不在微信白名单 | Medium | High | `wechat_check_api_credentials` 通过 adapter dry-run 显式检查并提示配置 ECS 公网 IP。 |
| ECS adapter 不可达或私有网络断开 | Medium | High | MCP 返回 `needs_operator_action`，runbook 覆盖 Tailscale/WireGuard/SSH 通道和 adapter health check。 |
| Artifact 未真正 publish-ready | Medium | High | 严格校验 metadata、正文格式和图片引用清单；裸 Markdown 直接拒绝。 |
| 正文图片或封面素材不符合微信 API 要求 | High | High | MCP 在 artifact 校验和 payload 构建前拒绝：正文图片必须是微信图文图片 URL，封面必须有 `thumb_media_id`。 |
| 草稿记录没有进入后续分析链路 | Medium | Medium | 成功后回写 `wechat_articles.status=drafted` 和 `media_id` metadata。 |
| 重复调用创建多个草稿 | Medium | Medium | 使用 idempotency key 和本地 job store 拒重。 |
| 误触发布/删除 | Low | Critical | 不实现 publish/update/delete API 工具。 |

---

## Dependencies & Blockers

**Dependencies:**

- `yueliang` 公众号 AppID/AppSecret 配置在 Ali ECS adapter。
- Ali ECS 绑定稳定公网 IP/EIP，且该公网 IP 已配置到微信接口 IP 白名单。
- NAS 到 Ali ECS adapter 的私有网络通道可用。
- hermes-db 可读取 `workflow_artifacts`，可写入 `wechat_articles`。
- 上游写文 agent / style skill 或独立素材准备流程能生成微信素材 ready artifact。

**Known Blockers:**

- 如果没有微信 API credential 或 ECS adapter 不可达，MCP 只能完成 artifact 校验，不能创建草稿。
- 如果 artifact 缺少微信图文图片 URL 或封面 `thumb_media_id`，MCP 返回结构化错误，不创建草稿。

---

## Business Metrics

- **BM-001**: `yueliang` 草稿 API 写入成功率：前 10 次真实写入中至少 8 次无需代码修改即可创建草稿。
- **BM-002**: Hermes 和至少一个本机 agent 都能通过同一 MCP 配置完成一次草稿写入或状态查询。
- **BM-003**: MCP 生成草稿后，用户只需做内容审核和少量排版检查，不需要重新复制整篇文章。
- **BM-004**: MVP 阶段自动发布/误群发/误删除次数必须为 0。

---

## Resolved Decisions

- 官方微信 API 是唯一 MVP 写草稿路径。
- Ali ECS adapter 是 MVP 的唯一微信 API 出口；NAS MCP 不直接用家宽 IP 调用微信写草稿。
- 不提供非官方 API 写入路径。
- 样式管理不在本 MCP；由写文 agent / skill 生成 publish-ready artifact。
- MCP 主输入是 `artifact_id`，不接受裸 Markdown。
- MCP 草稿写入只消费微信素材 ready artifact；素材准备不属于本 feature。
- 内容生产进度用 `workflow_artifacts.stage` 表达；`wechat_articles.status` 只表达微信侧结果，如 `drafted` / `published`。

## Open Questions

- ~~publish-ready artifact 的具体 `type` 命名：建议从 `wechat_html` 改为 `wechat_api_article`。~~ → 已确定使用 `wechat_api_article`
- ~~上游素材链路是否已经能产出正文微信图片 URL 和封面永久 `thumb_media_id`。~~ → 已确定 `wechat_create_draft` 只消费微信素材 ready artifact，素材准备独立处理
- MCP 读取 hermes-db 是通过 hermes-db MCP tool 还是直连数据库，plan 阶段确定。

---

## Stage Readiness

- 下一步建议：进入 `execute-plan`。
- 阻塞项：需要上游 style skill / 写文 agent 或独立素材准备流程明确微信素材 ready artifact 契约。
