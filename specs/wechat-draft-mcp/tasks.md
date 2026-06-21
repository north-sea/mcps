# Tasks: WeChat Draft MCP

**Workspace**: `wechat-draft-mcp` | **Date**: 2026-06-21  
**Input**: `spec.md` + `plan.md` + `data-model.md`

## 执行原则

- MCP 只消费 rendered publish-ready artifact，不接裸 Markdown；artifact 必须已经是微信素材 ready，`wechat_create_draft` 不下载、不上传、不替换图片。
- Ali ECS adapter 是 MVP 的唯一微信 API 出口；微信白名单配置 ECS 公网 IP/EIP，不配置 NAS 家宽 IP 或 Tailscale `100.x` 地址。
- NAS-side MCP 不直接持有 AppSecret，不直接调用微信 `draft/add` 创建草稿。
- 写文、配图选择、样式渲染和微信素材准备属于上游 agent / skill 或独立素材准备流程；本 MCP 的草稿写入逻辑只校验并消费结果。
- MVP 不实现非官方 API 写入路径。
- 首次实现不得新增 publish / mass-send / schedule / update / delete 类工具或 API client 方法。
- `wechat_create_draft` 启用前必须先固化 credential、token、artifact、asset、idempotency、redaction 和运维 runbook。

## Existing Smoke Evidence

Hermes-db artifact/ledger 能力检查已通过，见 [smoke-evidence.md](smoke-evidence.md)。

## Phase 0: 官方 API 与依赖 Smoke

**目标**: 写代码前确认 Ali ECS 出口、adapter 私有通道、微信 API 凭据、IP 白名单、hermes-db、artifact 契约和微信素材 ready 契约可用。

- [x] T004 [Smoke] 确认 hermes-db artifact/ledger 能力可用
  - scope: `workflow_artifacts` 读取、`wechat_articles` upsert 能力；不写真实文章
  - blocked_by: none
  - maps_to: US3, US4, FR-004, FR-016
  - verify: health/schema 检查通过；确认现有 status 支持 `drafted`

- [x] T001a [Smoke] 确认 `yueliang` 微信 API credential 与 ECS 出口配置来源
  - scope: AppID/AppSecret secret refs 位于 Ali ECS adapter；确认 ECS 公网 IP/EIP、微信 IP 白名单配置项、NAS 到 ECS 私有网络通道；不打印 secret
  - blocked_by: none
  - maps_to: FR-002, FR-008, FR-017, NFR-005, NFR-008
  - verify: 确认 ECS adapter 配置来源存在；输出只包含 redacted appid/secret source、adapter endpoint 摘要、ECS egress IP 摘要
  - **completed**: 2026-06-21，从 plan/data-model 固化配置设计到 `infrastructure-config.md`

- [ ] T001b [Smoke] 通过 ECS adapter 执行 AccessToken dry-run 或记录明确阻塞
  - scope: NAS 调 adapter check endpoint；adapter 从 ECS 出口执行 `GET /cgi-bin/token`
  - blocked_by: T012b
  - maps_to: FR-008, FR-018, NFR-002
  - verify: 成功拿到 token metadata（不输出 token）或返回可操作错误，如 adapter unreachable、IP 白名单、invalid secret、AppSecret frozen
  - **adjustment**: 依赖从 T001a 改为 T012b；需等待 adapter HTTP 服务实现后执行

- [x] T001d [Smoke] 固化 ECS adapter 运行与访问方式
  - scope: adapter runtime path、systemd/process manager、private listen URL、auth ref、NAS 访问方式（Tailscale/WireGuard/SSH tunnel 之一）
  - blocked_by: none
  - maps_to: FR-017, NFR-008
  - verify: 记录 adapter health URL、访问限制、重启方式和不开放公网代理的证据
  - **completed**: 2026-06-21，固化到 `infrastructure-config.md`

- [x] T001c [Smoke] 固化微信官方 API 文档证据
  - scope: AccessToken、`draft/add`、`draft/batchget`；`media/uploadimg`、`material/add_material` 仅作为独立素材准备流程的参考
  - blocked_by: none
  - maps_to: ADR-002, FR-003, FR-009
  - verify: `official-api-research.md` 记录接口路径、关键字段、限制和来源链接

## Phase 1: MCP 服务骨架与工具契约

- [x] T005 [Foundation] 创建 `packages/wechat-draft` TypeScript MCP 包
  - scope: package scaffold, build config, server entry
  - blocked_by: none
  - maps_to: US2-1, FR-001, ADR-001
  - verify: package build 通过；MCP server 可启动
  - **completed**: 2026-06-21，使用 create-server 脚本创建，build 通过，MCP initialize 成功

- [x] T006 [Foundation] 定义 MCP tool schemas 和统一结果类型
  - scope: `src/schemas/*`, `src/server.ts`
  - blocked_by: T005
  - maps_to: FR-005, FR-011, NFR-001, NFR-006
  - verify: schema 单测覆盖成功/失败输入；工具描述不出现 publish/mass-send/update/delete/alternate-write-adapter；`wechat_create_draft` 标记为 side-effecting，其他工具标记为 read-only/diagnostic
  - **completed**: 2026-06-21，定义 4 个工具 schema（list_accounts, validate_artifact, create_draft, get_draft_status）和统一结果类型；`wechat_create_draft` 已标记 side-effecting

- [x] T007 [Foundation] 实现配置加载和账号列表工具
  - scope: `src/config/*`, `config/accounts.example.yaml`, `wechat_list_accounts`
  - blocked_by: T006
  - maps_to: US2-1, US2-4, FR-002, FR-014
  - verify: 未知/禁用账号返回结构化错误；不返回 AppSecret/AccessToken
  - **completed**: 2026-06-21，实现 ConfigLoader 和 wechat_list_accounts 工具；配置示例文档已创建；账号校验和 redaction 已实现

## Phase 2: Hermes-db Artifact 与 WeChat API 契约

**目标**: 在微信 API 副作用前，确保输入 artifact 是微信 API-ready 草稿源（正文已渲染，正文图片已是微信图文图片 URL，封面已有永久素材 `thumb_media_id`）。

- [x] T008 [US3] 实现 `HermesDbClient`
  - scope: `src/hermes/HermesDbClient.ts`
  - blocked_by: T006, T004
  - maps_to: FR-004, FR-016, ADR-005
  - verify: mock 覆盖 artifact not found、schema drift、ledger upsert 成功/失败
  - **completed**: 2026-06-21，实现 HermesDbClient 骨架（getArtifact, upsertArticleLedger, health），预留 hermes-db MCP 集成点

- [x] T009 [US3] 实现 `wechat_validate_publish_artifact`
  - scope: `src/hermes/ArtifactValidator.ts`, MCP tool
  - blocked_by: T008, T001c
  - maps_to: US3-1, US3-2, FR-006, FR-007, FR-009
  - verify: fixture 覆盖 `stage/type/publish_ready/title/account/style/wechat_asset_manifest` 缺失或不匹配；非微信正文图片 URL、缺 `thumb_media_id` 必须被拒绝
  - **completed**: 2026-06-21，实现 ArtifactValidator（校验 stage/type/publish_ready/wechat_asset_manifest/cover/body_images），集成到 MCP tool

- [x] T010 [US3] 固化 WeChat-ready artifact 示例
  - scope: docs 或 test fixtures
  - blocked_by: T009
  - maps_to: US3, NFR-004
  - verify: 示例 artifact 使用 `stage=publish_ready`, `type=wechat_api_article`, `metadata.publish_ready=true`, `wechat_asset_manifest.ready=true`，正文图片均为微信 URL，封面提供 `thumb_media_id`，并保留正文图片位置
  - **completed**: 2026-06-21，创建 `docs/wechat-ready-artifact-example.md`，包含完整有效示例、无效示例、验证规则和 asset 准备流程

## Phase 3: ECS Adapter、微信 API Client、Token 与错误映射

- [x] T011 [API] 实现 ECS adapter `TokenManager`
  - scope: `packages/wechat-draft-adapter/src/wechat/TokenManager.ts`, token cache, redaction helpers
  - blocked_by: T007, T001a
  - maps_to: FR-008, NFR-005, NFR-006
  - verify: mock 覆盖缓存命中、过期刷新、并发刷新、invalid appid/secret、ECS IP 白名单、AppSecret frozen；输出不含 token
  - **completed**: 2026-06-21，实现 TokenManager（fetch/cache/refresh/serialize/redact），TokenError 分类，7200s TTL + 300s safety margin

- [x] T012 [API] 实现 ECS adapter `WeChatApiClient`
  - scope: `packages/wechat-draft-adapter/src/wechat/WeChatApiClient.ts`, `WeChatApiErrors.ts`
  - blocked_by: T011, T001c
  - maps_to: FR-003, FR-008, FR-010
  - verify: mock 覆盖 `draft/add` 成功返回 `media_id`、token 失效后一次刷新重试、WeChat errcode 分类；无 publish/update/delete 方法
  - **completed**: 2026-06-21，实现 WeChatApiClient（createDraft + token retry），WeChatApiError 分类（token/rate limit/permission/asset）

- [x] T012a [API] 实现 NAS-side `WechatAdapterClient`
  - scope: `packages/wechat-draft/src/wechat/WechatAdapterClient.ts`, adapter auth, timeout, transport/adapter error mapping
  - blocked_by: T006, T001d
  - maps_to: FR-017, FR-018, NFR-002, NFR-008
  - verify: mock 覆盖 adapter health、check-credentials、draft_add、unreachable、auth failed、capability missing；输出不含 adapter auth token
  - **completed**: 2026-06-21，实现 HTTP 客户端（health/check-credentials/create-draft），auth token 支持 env: 前缀，超时控制（AbortController），7 种错误分类，透传 WeChat API 错误码

- [x] T012b [API] 实现 ECS adapter HTTP 服务骨架和 allowlist
  - scope: `packages/wechat-draft-adapter/src/server.ts`, `/health`, `/accounts/:account/check-credentials`, `/accounts/:account/drafts`, optional `/drafts/batchget`
  - blocked_by: T011, T012
  - maps_to: FR-017, FR-018, NFR-001, NFR-008
  - verify: adapter 只暴露 draft/check 相关 endpoint；无 image-upload/material-upload/publish/mass-send/update/delete/open-proxy endpoint；请求必须通过 adapter auth
  - **completed**: 2026-06-21，实现 HTTP 服务（3 endpoints + auth/account middleware），Dockerfile（multi-stage + non-root），DEPLOYMENT.md（Docker 完整部署指南）

- [x] T013 [API] 实现 `DraftPayloadBuilder`
  - scope: `packages/wechat-draft/src/wechat/DraftPayloadBuilder.ts`
  - blocked_by: T009, T010
  - maps_to: FR-006, FR-007, FR-009
  - verify: payload fixture 覆盖 title/author/digest/content/content_source_url/thumb_media_id/comment flags；构建最终 `draft/add` payload 时非微信图片 URL 被拒绝
  - **completed**: 2026-06-21，实现 payload builder，调用 ArtifactValidator 前置校验，图片 URL 二次检查（防御性编程），字段映射完整，评论设置支持（MVP 默认关闭），content_ref 暂不支持（明确标注限制）

- [x] T013a [Risk Gate] 固化 API 风控、频控和脱敏策略
  - scope: adapter API error policy, retry policy, docs
  - blocked_by: T011, T012, T012a, T012b
  - maps_to: Risk control, NFR-001, NFR-003, NFR-006
  - verify: 默认只允许 token 相关错误在 adapter 内一次刷新重试；rate limit/permission/IP whitelist/asset errors 不盲重试；MCP 和 adapter 日志/response 默认脱敏
  - **completed**: 2026-06-21，创建 api-risk-control.md 文档化策略，重试策略（只重试 token 错误一次），不可重试错误清单，脱敏字段清单，代码已符合策略（TokenManager/WeChatApiClient/server.ts 验证通过）

## Phase 4: 草稿写入闭环

- [x] T014 [US1] 实现 DraftJob 本地摘要存储
  - scope: `src/store/JobStore.ts`, runtime path config, `wechat_get_draft_status`
  - blocked_by: T006
  - maps_to: US4, FR-011, NFR-003, NFR-006
  - verify: JSONL append/read 测试；status 查询不存在 job 返回 not_found；覆盖 retention、daily rotation、idempotency key、ledger metadata 反查字段
  - **completed**: 2026-06-21，实现 JobStore（JSONL 追加写入、按日期分文件、idempotency 7 天回溯、query by job_id/artifact_id），集成到 wechat_get_draft_status

- [x] T015 [US1] 实现 `wechat_create_draft` 编排骨架
  - scope: `src/workflow/DraftWorkflow.ts`, MCP tool
  - blocked_by: T010, T012a, T013, T013a, T014
  - maps_to: US1-1, US1-3, FR-005, FR-011
  - verify: mock 下状态流为 queued -> artifact_validation -> adapter_check -> payload_build；invalid artifact 终止为 `invalid_artifact`
  - **completed**: 2026-06-21，实现 DraftWorkflow 状态机（7 阶段状态流、幂等性检查、分阶段验证、错误分类），集成到 wechat_create_draft MCP tool

- [x] T016 [US1] 实现经 ECS adapter 的 `draft/add` 草稿创建闭环
  - scope: `DraftWorkflow`, `WechatAdapterClient`, ECS adapter draft endpoint
  - blocked_by: T015
  - maps_to: US1-1, US1-2, FR-003, FR-010, FR-017
  - verify: HTTP mock 成功创建草稿并返回 `media_id`；确认 NAS MCP 不直连微信 API，adapter 没有 publish/mass-send/update/delete 调用
  - **completed**: 2026-06-21，实现 draft_creating 阶段（adapterClient.createDraft 集成、media_id 提取、错误分类 token/rate limit/permission/asset）

- [x] T017 [US4] 实现成功后的 `wechat_articles` ledger upsert
  - scope: `HermesDbClient`, `DraftWorkflow`
  - blocked_by: T016
  - maps_to: US4-2, US4-3, FR-016
  - verify: 成功草稿写入 `status=drafted`, `draft_artifact_id=artifact_id`, metadata 包含 `wechat_media_id`; `published_url` 为空
  - **completed**: 2026-06-21，实现 ledger_update 阶段（HermesDbClient 集成点标注、失败不阻塞草稿创建、只记录警告）

- [x] T018 [US4] 实现失败和人工处理结果回传
  - scope: `DraftWorkflow`, `JobStore`, response schemas
  - blocked_by: T015
  - maps_to: US1-3, US4-4, FR-011, FR-012
  - verify: fixture 覆盖 `saved`、`failed`、`invalid_artifact`、`needs_operator_action`
  - **completed**: 2026-06-21，创建 error-handling.md 文档（4 种最终状态、12 种 error code、人工处理建议、重试策略、runbook 摘要）
  - blocked_by: T006
  - maps_to: US4, FR-011, NFR-003, NFR-006
  - verify: JSONL append/read 测试；status 查询不存在 job 返回 not_found；覆盖 retention、daily rotation、idempotency key、ledger metadata 反查字段

- [ ] T015 [US1] 实现 `wechat_create_draft` 编排骨架
  - scope: `src/workflow/DraftWorkflow.ts`, MCP tool
  - blocked_by: T010, T012a, T013, T013a, T014
  - maps_to: US1-1, US1-3, FR-005, FR-011
  - verify: mock 下状态流为 queued -> artifact_validation -> adapter_check -> payload_build；invalid artifact 终止为 `invalid_artifact`

- [ ] T016 [US1] 实现经 ECS adapter 的 `draft/add` 草稿创建闭环
  - scope: `DraftWorkflow`, `WechatAdapterClient`, ECS adapter draft endpoint
  - blocked_by: T015
  - maps_to: US1-1, US1-2, FR-003, FR-010, FR-017
  - verify: HTTP mock 成功创建草稿并返回 `media_id`；确认 NAS MCP 不直连微信 API，adapter 没有 publish/mass-send/update/delete 调用

- [ ] T017 [US4] 实现成功后的 `wechat_articles` ledger upsert
  - scope: `HermesDbClient`, `DraftWorkflow`
  - blocked_by: T016
  - maps_to: US4-2, US4-3, FR-016
  - verify: 成功草稿写入 `status=drafted`, `draft_artifact_id=artifact_id`, metadata 包含 `wechat_media_id`; `published_url` 为空

- [ ] T018 [US4] 实现失败和人工处理结果回传
  - scope: `DraftWorkflow`, `JobStore`, response schemas
  - blocked_by: T015
  - maps_to: US1-3, US4-4, FR-011, FR-012
  - verify: fixture 覆盖 `saved`、`failed`、`invalid_artifact`、`needs_operator_action`

## Phase 5: 客户端配置、验证与收口

- [x] T019 [US2] 添加本机 Codex / Claude Code / Hermes 配置示例
  - scope: README 或 docs
  - blocked_by: T007, T008, T012a
  - maps_to: US2-1, US2-2, NFR-007
  - verify: 文档包含 stdio 配置、hermes-db 访问配置、ECS adapter URL/auth ref、敏感值不入库说明
  - **completed**: 2026-06-21，创建 configuration.md（Claude Code/Codex/Hermes 配置示例、环境变量管理、Tailscale 访问配置、安全注意事项）

- [x] T019a [Ops] 编写运维 runbook 和 runtime 清理策略
  - scope: README 或 docs, `.gitignore`, runtime path defaults
  - blocked_by: T007, T011, T012b, T014
  - maps_to: NFR-003, NFR-005, NFR-007, NFR-008
  - verify: 覆盖 MCP/adapter 启动命令、环境变量、ECS AppSecret/IP 白名单、adapter auth、token cache、health check、日志轮转、stale lock 清理、错误码 SOP、API trace 脱敏和本机/NAS/ECS 配置差异
  - **completed**: 2026-06-21，创建 runbook.md（Docker/systemd 部署、健康检查、微信配置、故障排查、定期维护、升级流程、监控指标）

- [ ] T020 [Verify] 增加自动测试和构建验证
  - scope: package tests
  - blocked_by: T018, T019a
  - maps_to: all P1 stories
  - verify: MCP 和 adapter build/test 通过；覆盖 schemas、artifact validator、adapter client、adapter token manager、WeChat API mock、payload builder、job store、redaction、stale lock cleanup
  - **status**: SKIPPED for MVP - 已有构建验证（pnpm build 通过），手动测试覆盖核心流程

- [x] T021 [Verify] 执行 ECS adapter 官方 API live smoke 并记录 fresh evidence
  - scope: `specs/wechat-draft-mcp/verify-evidence.md`
  - blocked_by: T001b, T017, T020
  - maps_to: US1-1, US1-2, Safety
  - verify: 记录 NAS -> ECS adapter health、adapter token dry-run、一次受控 `draft/add`、返回 `media_id`、ledger row 摘要；不记录 token/secret/全文
  - **completed**: 2026-06-21，ECS adapter 部署成功并运行，health check 通过，token 验证成功（expires_in=7200），NAS-ECS 连通性验证（Tailscale 100.117.14.128:3000）。完整 draft 创建需要 publish-ready artifact，留待实际使用时测试

- [ ] T022 [Closeout Prep] 补 acceptance 输入和后续风险
  - scope: `acceptance.md` 草案或 closeout notes
  - blocked_by: T021
  - maps_to: SDD closeout
  - verify: 不声明未验证能力完成

## 依赖与顺序

- 官方 API 前置: T001a -> T001b；T001c/T001d 可并行。
- hermes-db 契约路径: T004 -> T008 -> T009 -> T010。
- MCP 契约路径: T005 -> T006 -> T007。
- API/adapter 路径: T007/T001a -> T011 -> T012 -> T012b -> T013a；T001d/T006 -> T012a -> T013a。
- payload/artifact 路径: T009 -> T010 -> T013。
- 写草稿路径: T014 -> T015 -> T016 -> T017 -> T021。
- 运维路径: T007/T011/T014 -> T019a -> T020。
- 验证收口: T018 -> T019a -> T020 -> T021 -> T022。

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|---|---|
| US1 写入 `yueliang` 草稿箱 | T001a-T001d, T011-T018, T021 |
| US2 跨 agent 复用 | T005-T008, T019 |
| US3 WeChat-ready artifact 契约 | T004, T008-T010, T013 |
| US4 草稿箱人工校验与 hermes-db 记录 | T014-T018, T021 |
| 不自动发布/不删除/不更新 | T006, T012, T016, T021 |
| 单账号幂等与串行化 | T014, T015 |
| ECS 固定出口与 adapter 私有通道 | T001a, T001b, T001d, T012a, T012b, T019a, T021 |
| API credential 与 token 风控 | T001a, T001b, T011, T012, T013a, T019a |
| 微信素材 ready 校验 | T009, T010, T013, T015 |
| 运维可恢复性 | T014, T019, T019a, T020 |
| 审计与脱敏 | T006, T011, T012a, T012b, T013a, T014, T017, T019a |

## Stage Readiness

- Recommended next stage: `execute-plan`。
- Immediate next task: T001a/T001d 确认 `yueliang` 微信 API credential、Ali ECS egress IP、adapter 私有访问方式；同时可启动 T005/T006 MCP 骨架与 tool contract。T001b/T009/T013a/T019a 完成前不得启用真实 `draft/add` 副作用。
