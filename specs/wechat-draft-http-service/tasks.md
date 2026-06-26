# Tasks: WeChat Draft MCP Service (Streamable HTTP)

**Workspace**: `wechat-draft-http-service` | **Date**: 2026-06-26
**Input**: [spec.md](spec.md) + [plan.md](plan.md) + [data-model.md](data-model.md)

---

## 执行原则

- 优先按可验证的端到端 slice 推进，不把任务拆成孤立的横向重构。
- 横向前置任务只服务于后续 slice：HTTP MCP、SQLite 幂等、资产上传、health、Docker。
- 所有外部副作用路径必须有 mock/integration guard，不能只靠人工 smoke。
- 旧 stdio 入口可保留，但 Docker 服务只启动 Streamable HTTP MCP。

---

## Phase 1: Foundation And Boundaries

**目标**: 准备依赖、入口和模块边界，使后续 slice 可以在清晰结构中落地。

- [x] T001 [Foundation] 升级并收敛 `packages/wechat-draft` 依赖与脚本
  - scope: `packages/wechat-draft/package.json`, lockfile, root scripts if needed
  - slice: 为 HTTP MCP + SQLite + logging slice 提供稳定依赖，不改变业务行为
  - blocked_by: none
  - maps_to: ADR-001, ADR-002, ADR-004
  - verify: `pnpm --filter @mcps/wechat-draft build` 能解析新依赖；package scripts 明确区分 stdio start 和 HTTP service start

- [x] T002 [Foundation] 建立 service / mcp / http 模块边界
  - scope: `packages/wechat-draft/src/{service,mcp,http}`, existing `src/server.ts`
  - slice: MCP tool registry 可以通过 `WechatDraftService` 调用至少一个只读用例
  - blocked_by: T001
  - maps_to: FR-002, FR-005, ADR-001, 可维护性
  - verify: `wechat_list_accounts` 的核心逻辑不再直接散落在 transport handler 中；旧 stdio entrypoint 仍可编译

- [x] T003 [Foundation] 显式初始化配置和运行时依赖
  - scope: `ConfigLoader` usage, service factory, startup path
  - slice: 服务启动时 config/store 初始化失败会阻止服务进入可用状态，而不是 fire-and-forget
  - blocked_by: T002
  - maps_to: FR-005, Health local checks
  - verify: 缺失/非法 config 的测试或手工启动命令返回明确失败；不再出现未 await 的 store 初始化路径

---

## Phase 2: HTTP MCP Slice

**目标**: 本机/NAS agent 可通过标准 HTTP MCP endpoint 调用只读 tool。

- [x] T004 [US1/US2] 实现 Streamable HTTP MCP host
  - scope: `src/http-index.ts`, `src/http/app.ts`, `src/mcp/createMcpServer.ts`
  - slice: `POST /mcp` 可通过 MCP Streamable HTTP 调用 `wechat_list_accounts`
  - blocked_by: T002, T003
  - maps_to: US1-1, US2-1, FR-001, FR-002, ADR-001, ADR-003
  - verify: 使用 MCP client fixture 或 HTTP transport fixture 调 `wechat_list_accounts()` 返回 3 个账号

- [x] T005 [US2] 实现 `/mcp` Bearer auth 和 transport security guard
  - scope: `src/http/auth.ts`, Express app setup
  - slice: 配置 `AUTH_TOKEN` 后，未授权请求被拒绝，授权请求可调用 MCP tool
  - blocked_by: T004
  - maps_to: US2-2, FR-004, 安全
  - verify: auth tests 覆盖 missing token、invalid token、valid token、empty `AUTH_TOKEN`；Host header validation 使用官方 helper 或等价测试覆盖

- [x] T006 [US1/US2] 保持 stdio 旧入口可编译但不进入 Docker 服务
  - scope: `src/index.ts`, package scripts, Docker entrypoint decision
  - slice: 迁移期旧 stdio 可独立运行，新 Docker 服务只运行 HTTP entrypoint
  - blocked_by: T004
  - maps_to: 向后兼容性, Out of Scope 双协议
  - verify: `pnpm --filter @mcps/wechat-draft build` 后 stdio start 和 HTTP start 各自入口清晰；Dockerfile 只使用 HTTP entrypoint

---

## Phase 3: SQLite Job Store And Draft Workflow Slice

**目标**: 通过 SQLite 实现稳定幂等的草稿创建状态流。

- [x] T007 [US1] 实现 `SQLiteJobStore` 和 schema 初始化
  - scope: `src/store/SQLiteJobStore.ts`, store exports, tests
  - slice: 本地 SQLite 可创建 job、更新状态、按 job/artifact/idempotency 查询
  - blocked_by: T001, T003
  - maps_to: FR-006, NFR-004, ADR-004, data-model.md
  - verify: unit tests 覆盖 schema init、status update、get by job_id、get by artifact_id、error_details JSON

- [x] T008 [US1] 实现 7 天幂等窗口和并发冲突语义
  - scope: `SQLiteJobStore.createOrGetJob`, transaction tests
  - slice: 同 `account + idempotency_key` 并发时只创建一个 job，过期后可复用 key
  - blocked_by: T007
  - maps_to: US1-2, US1-3, FR-006, 一致性
  - verify: tests 覆盖 `INSERT OR IGNORE`/unique conflict、expired terminal row cleanup、in-progress row 不被清理、并发调用 adapter 只触发一次

- [x] T009 [US1] 调整 `DraftWorkflow` 使用 SQLite job contract
  - scope: `src/workflow/DraftWorkflow.ts`, `WechatDraftService.createDraft`
  - slice: `wechat_create_draft` 只对新建 job 执行 artifact/adapter/WeChat 外部副作用，重复请求返回已有 job 状态
  - blocked_by: T007, T008
  - maps_to: US1-1, US1-2, external-side-effects
  - verify: integration tests mock hermes-db/adapter，验证 happy path、重复 key、adapter unreachable、artifact missing、ledger failure

- [x] T010 [US1] 保持 MCP tool result 格式和错误码稳定
  - scope: `src/schemas/result-types.ts`, `src/mcp/toolResult.ts`, service error mapping
  - slice: 所有 tools 返回 `{success:true,data}` 或 `{success:false,error}` 的 MCP text content
  - blocked_by: T002, T009
  - maps_to: Error Handling, FR-002
  - verify: snapshot 或 unit tests 覆盖 create/list/status/upload/validate 的 success/error wrapper

---

## Phase 4: Asset Upload Slice

**目标**: 远程 MCP 场景下安全、清晰地处理图片资产来源。

- [x] T011 [US1] 收敛 `wechat_upload_asset` 的 remote/local source 语义
  - scope: `src/wechat/AssetSourceLoader.ts`, config/env for `ASSET_ROOT`
  - slice: `remote_url` 可上传；`local_path` 只能读取容器内 `ASSET_ROOT` 下文件
  - blocked_by: T002, T003
  - maps_to: FR-008, Asset Source Semantics, 安全
  - verify: tests 覆盖 remote_url、local path escape、ASSET_ROOT 内文件、unsupported mime、cover 64KB limit

- [x] T012 [US1] 保持 adapter asset upload 调用链和错误映射
  - scope: `WechatDraftService.uploadAsset`, `WechatAdapterClient`, schema/result mapping
  - slice: body_image 返回 `wechat_url`，cover_image 返回 `thumb_media_id`，错误码对齐现有 Result
  - blocked_by: T011
  - maps_to: US1-6, Asset Upload Result, artifact-handoff
  - verify: mock adapter tests 覆盖 body_image、cover_image、adapter auth failure、asset_size_exceeded

---

## Phase 5: Health, Observability, And Docker Slice

**目标**: 服务能作为稳定 Docker 容器运行，并提供可诊断但不泄密的健康状态。

- [x] T013 [US3] 实现 `HealthMonitor` 和 `/health`
  - scope: `src/service/HealthMonitor.ts`, `src/http/health.ts`
  - slice: `/health` 同步检查本地状态，读取后台 probe 缓存，不在请求内调用外部依赖
  - blocked_by: T003, T007
  - maps_to: US3, FR-003, FR-007, 可观测性
  - verify: tests 覆盖 ok、degraded、runtime/config/db 503、HEAD no body、敏感信息不出现在响应中

- [x] T014 [US3] 接入 pino/pino-http 结构化日志
  - scope: HTTP app, service/workflow logging boundaries
  - slice: 每个 MCP 请求和 tool call 有 request id、tool name、status、duration、error code
  - blocked_by: T004, T009
  - maps_to: Quality Attribute 可观测性, BM-002
  - verify: log snapshot 或 smoke 输出检查不包含 token，包含 request/tool/job correlation 字段

- [ ] T015 [US2/US3] 增加 Dockerfile 和 compose/run 配置
  - scope: `packages/wechat-draft/Dockerfile`, deploy examples, package scripts
  - slice: 容器启动 HTTP MCP 服务，挂载 config/data/assets，healthcheck 使用 Node fetch
  - blocked_by: T004, T007, T013
  - maps_to: Deployment, 可部署性
  - verify: `docker build` 成功；容器内 `/health` 返回 200 或 degraded；镜像不依赖 curl
  - evidence 2026-06-26: Dockerfile、compose 示例和 `docker:build` script 已实现；`pnpm --filter @mcps/wechat-draft build`、`pnpm --filter @mcps/wechat-draft test`、`docker compose config` 通过。Docker build 因 Docker Hub metadata timeout / Alpine package source 长时间无进展未完成，T015 暂不勾选。
  - evidence 2026-06-26 retry: Dockerfile 已改为 builder/runtime 分离，默认 builder `node:22-bookworm`、runtime `node:22-bookworm-slim`，仅在缺少 native build tools 时安装系统包；正式 `docker build` 仍失败于 Docker Hub `node:22-bookworm*` metadata timeout。
  - evidence 2026-06-26 release-align: 部署改为沿用 `hermes-db` 的 `mcp-release.yml` tag 流程；新增 `deploy/mcp-services.json` 的 `wechat-draft` 条目、`deploy/services/wechat-draft.yml` NAS compose 模板、HTTP `/health` release smoke 分支。`node scripts/resolve-mcp-release.mjs wechat-draft-v0.2.0` 和 deploy compose 模板摘要验证通过；仍需 GitHub Actions/GHCR 或 Docker Hub 可达后完成真实 build/smoke。
  - evidence 2026-06-26 nas-prep: NAS `/vol1/1000/Docker/wechat-draft-mcp` 已准备 compose/config/.env；因 `3001` 被 `gpt-load` 占用，宿主机端口改为 `3012:3001`，release smoke URL 改为 `http://127.0.0.1:3012/health`。远端 `docker compose config --quiet` 通过，镜像解析为 `ghcr.io/north-sea/wechat-draft-mcp:v0.2.0`。T015 仍等 tag workflow 真实 build/pull/smoke 后勾选。

- [x] T016 [US1/US2] 更新客户端配置和运行文档
  - scope: README/docs/deployment examples under `packages/wechat-draft` or spec docs
  - slice: 本机 Codex/Claude 和 NAS Hermes 都能按 placeholder token 配置 remote MCP endpoint
  - blocked_by: T004, T005, T015
  - maps_to: US1, US2, 安全
  - verify: 文档示例只含占位符，不含真实 token；配置示例包含 url + Authorization headers
  - evidence 2026-06-26: 新增 `packages/wechat-draft/docs/http-docker-service.md`，README 链接 HTTP Docker 服务配置；`.env.nas.example` 改为占位 token；本机/Claude Code/Codex/NAS Hermes 示例均使用 `url` + `Authorization` header；文档补充 `wechat-draft-vX.Y.Z` tag -> GitHub Actions -> GHCR -> NAS runner 的正式部署链路。静态扫描 4 个相关示例/文档文件，未发现已知 token 片段或疑似真实 token。T015 Docker smoke 仍由 T019 验证。

---

## Phase 6: Verification And Release Readiness

**目标**: 给实现阶段提供 fresh evidence，防止外部副作用路径和 Docker 部署路径只在纸面闭环。

- [x] T017 [Verify] 建立自动化测试入口
  - scope: package test script, test files, mocks/fixtures
  - slice: 单元和集成测试可通过一个 package script 运行
  - blocked_by: T007, T011, T013
  - maps_to: Verification Strategy
  - verify: `pnpm --filter @mcps/wechat-draft test` 或等价命令存在并覆盖 store/auth/health/asset/workflow
  - evidence 2026-06-26: `pnpm --filter @mcps/wechat-draft build` 通过；`pnpm --filter @mcps/wechat-draft test` 通过，39 tests pass，覆盖 config env overlay、auth、HTTP MCP smoke、tool result、logging、health、service upload、error mapping、SQLite store、asset source、workflow idempotency。

- [ ] T018 [Verify] 执行 HTTP MCP end-to-end smoke
  - scope: local service startup, MCP HTTP client fixture, mock hermes-db/adapter
  - slice: 从 `/mcp` 调 `wechat_list_accounts` 和 `wechat_create_draft` 完成端到端闭环
  - blocked_by: T004, T009, T015, T017
  - maps_to: US1-1, US2-1, Producer-Consumer Matrix
  - verify: smoke evidence 记录 endpoint、tool response、job row、mock adapter call count
  - evidence 2026-06-26 partial: 新增 `src/http/httpMcpSmoke.test.ts`，使用官方 `StreamableHTTPClientTransport` 通过本地 `/mcp` 调 `wechat_list_accounts` 与 `wechat_create_draft`，fake hermes-db/adapter + SQLite 临时库验证重复 idempotency 只触发一次 adapter；`pnpm --filter @mcps/wechat-draft test` 通过。因 T015 Docker build/smoke 未完成，T018 暂不勾选。

- [ ] T019 [Verify] 执行 Docker smoke 和 migration fallback check
  - scope: Docker image/container, mounted config/data, old stdio entrypoint
  - slice: 新 HTTP 容器可运行；旧 stdio 入口仍可作为迁移兜底编译运行
  - blocked_by: T015, T017
  - maps_to: Deployment, 向后兼容性, NFR-001
  - verify: Docker healthcheck evidence；旧 entrypoint build/start smoke 记录；无真实 token 写入文档

- [ ] T020 [Closeout Prep] 准备验收记录输入
  - scope: future `acceptance.md`, test/smoke evidence summary
  - slice: closeout 阶段可基于 fresh evidence 判断 Component / Workflow / User-Visible Outcome
  - blocked_by: T018, T019
  - maps_to: external-side-effects, user-visible-output, acceptance gate
  - verify: evidence summary 包含测试命令、结果、已知限制、未执行 live WeChat 调用的原因或证据

---

## 依赖与顺序

- 关键路径：T001 → T002/T003 → T004/T005 → T007/T008/T009 → T013/T015 → T018/T019 → T020。
- 可并行：
  - T007/T008 可与 T004/T005 在接口约定明确后并行。
  - T011/T012 可在 T002/T003 后并行于 SQLite 工作。
  - T014 可在 T004 后并行推进。
  - T016 可在 Docker/client config 明确后与后续验证并行。
- 不应提前做：
  - 在 T007/T008 前不要改 `DraftWorkflow` 外部副作用顺序。
  - 在 T004/T005 前不要写 Docker smoke 结论。
  - 在 T018/T019 前不要进入 closeout。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|-------------|----------|
| US1 本机 agent 通过 HTTP MCP 调工具 | T004, T005, T009, T018 |
| US1 幂等性和并发重复调用 | T007, T008, T009, T018 |
| US1 asset size/source 边界 | T011, T012, T017 |
| US2 NAS Hermes 容器间调用 | T004, T005, T015, T016, T019 |
| US3 health 运维监控 | T013, T014, T015, T019 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|----------------------|----------|----------|
| ADR-001 MCP SDK | T004 | T018 |
| ADR-002 Express thin host / Host validation | T004, T005 | T017, T018 |
| ADR-003 Stateless transport | T004, T009 | T018 |
| ADR-004 SQLite job store | T007, T008, T009 | T017, T018 |
| ADR-005 Asset source semantics | T011, T012 | T017 |
| 可部署性 | T015, T016 | T019 |
| 可观测性 | T013, T014 | T019 |
| 安全 | T005, T011, T013, T016 | T017, T019 |

---

## Context Manifest

已生成 [context-manifest.md](context-manifest.md)，因为该 feature 命中 `external-side-effects`、`artifact-handoff`、`user-visible-output`，且实现/验证需要保留官方文档和代码探索结论。

---

## Stage Readiness

- 推荐下一步：`execute-plan`
- 阻塞项：无
- 原因：任务数量较多，涉及依赖升级、模块拆分、SQLite、HTTP MCP、Docker 和验证，建议先用 `execute-plan` 控制批次，而不是一次性直接实现全部任务。
