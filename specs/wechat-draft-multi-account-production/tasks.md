# Tasks: WeChat Draft Multi-Account Production

**Workspace**: `wechat-draft-multi-account-production` | **Date**: 2026-06-25  
**Input**: `specs/wechat-draft-multi-account-production/spec.md` + `plan.md`  
**Prerequisites**: spec.md ✅, plan.md ✅, data-model.md 不需要

---

## 执行原则

- 按端到端 slice 推进：先让 `xiaban` 在配置层可见，再让 adapter 线上可用，最后跑真实 MCP smoke。
- 不把 AppSecret、AccessToken、adapter auth token 或 hermes token 写入仓库、任务日志或 acceptance 正文。
- 不发布、不群发、不删除，只创建测试草稿。
- 不把 direct adapter fallback 作为 full MCP path 通过证据。

---

## Phase 1: Account Registry Foundation

**目标**: 让 `wechat-draft` 的账号配置从 hardcoded defaults 迁到可部署配置，同时保留 fallback。

- [x] T001 [US1] 实现 `ConfigLoader` 外部配置文件读取
  - scope: `packages/wechat-draft/src/config/loader.ts`, `packages/wechat-draft/src/config/types.ts`
  - slice: 设置 `WECHAT_DRAFT_CONFIG_PATH` 后，`wechat_list_accounts` 返回配置文件中的账号
  - blocked_by: none
  - maps_to: US1, FR-001, NFR-004, ADR-002
  - verify: 新增或更新测试/脚本证明 config path 生效；未设置时 fallback 仍可 build

- [x] T002 [US1] 更新账号注册表示例并正式记录 `xiaban`
  - scope: `packages/wechat-draft/config/accounts.example.yaml`, docs/runbook as needed
  - slice: registry 包含 `weiyuchengchun`, `yueliang`, `xiaban`
  - blocked_by: T001
  - maps_to: US1, US2, FR-002, FR-003, FR-010
  - verify: 示例不含 raw secret；account id 命名规则写明 `xiaban`

- [x] T003 [US1] 增加配置一致性校验
  - scope: `ConfigLoader` or lightweight validation helper
  - slice: adapter `allowed_accounts` 未覆盖 enabled account 时返回可诊断错误
  - blocked_by: T001, T002
  - maps_to: US1 Edge, FR-004, NFR-002
  - verify: 测试覆盖 missing adapter account、invalid account id、disabled account

---

## Phase 2: Xiaban Rendering And MCP Visibility

**目标**: 让 `xiaban` 在 MCP、style profile 和 canonical renderer 中可用。

- [x] T004 [US2] 增加 `xiaban.default` WeChat style profile
  - scope: `packages/wechat-draft/src/render/WechatStyleProfile.ts`
  - slice: `getWechatStyleProfile('xiaban.default')` 返回 account_id `xiaban`
  - blocked_by: none
  - maps_to: US2, FR-005, ADR-003
  - verify: renderer 测试覆盖 `xiaban.default`，unknown profile 仍失败

- [x] T005 [US2] 更新 canonical article builder / smoke 默认配置对多账号友好
  - scope: `ArticleDocumentToWechatArtifactBuilder`, `scripts/live-canonical-smoke.mjs`, fixtures if needed
  - slice: smoke 可通过 env 指定 `WECHAT_CANONICAL_SMOKE_ACCOUNT=xiaban` 和 `style_profile_id=xiaban.default`
  - blocked_by: T004
  - maps_to: US2, US3, FR-003, FR-006
  - verify: 本地 dry-run fixture 生成 `account=xiaban` 的 publish-ready artifact

- [x] T006 [Regression] 收口当前生产闭环相关未提交修复
  - scope: `packages/wechat-draft/src/hermes/HermesDbClient.ts`, `packages/wechat-draft/src/store/JobStore.ts`
  - slice: hermes-db metadata string 可被 validator 消费；status 查询返回最新状态
  - blocked_by: none
  - maps_to: FR-008, FR-009, prior-closure-failure
  - verify: build/test 通过；手工或测试覆盖 metadata normalize 和 updated_at ordering

---

## Phase 3: Adapter Deployment Sync

**目标**: 让 ECS 线上 `wechat-draft-adapter` 真正加载 `xiaban`。

- [x] T007 [US2] 同步 adapter env 到 ECS 并重启服务
  - scope: ECS `/opt/wechat-adapter/.env`, systemd `wechat-adapter`
  - slice: ECS `/health` 返回 `allowed_accounts` 包含 `xiaban`
  - blocked_by: T002
  - maps_to: US2, FR-004, NFR-001, NFR-002
  - verify: `ssh ali 'curl -s http://127.0.0.1:3000/health'` 脱敏记录

- [x] T008 [US2] 执行 `xiaban` credential dry-run
  - scope: ECS adapter `/accounts/xiaban/check-credentials`
  - slice: adapter 从 ECS 出口获取 token metadata，不输出 token
  - blocked_by: T007
  - maps_to: US2, FR-004, FR-007
  - verify: 成功返回 token metadata；失败时记录 IP whitelist / invalid secret / permission 等可操作错误

---

## Phase 4: Full MCP Path Smoke

**目标**: 证明 `xiaban` 从素材上传到微信草稿箱可见的完整闭环。

- [x] T009 [US3] 上传 `xiaban` 正文图和封面图
  - scope: `wechat_upload_asset`, ECS adapter `/accounts/xiaban/assets`
  - slice: body image 返回 `wechat_url`，cover image 返回 `thumb_media_id`
  - blocked_by: T008
  - maps_to: US3, FR-006, external-side-effects
  - verify: 记录 redacted asset result；不得输出 token

- [x] T010 [US3] 写入 hermes-db publish-ready artifact 并验证
  - scope: hermes-db workflow artifact, `wechat_validate_publish_artifact`
  - slice: `account=xiaban`, `style_profile_id=xiaban.default`, assets ready 的 artifact validation pass
  - blocked_by: T005, T009
  - maps_to: US3, FR-006, artifact-handoff
  - verify: `wechat_validate_publish_artifact` 返回 valid=true；若 `HERMES_DB_AUTH_TOKEN` 缺失则标阻塞

- [x] T011 [US3] 通过 MCP 创建真实 `xiaban` 草稿
  - scope: `wechat_create_draft`, `DraftWorkflow`, `JobStore`, `HermesDbClient`
  - slice: 返回 `media_id`，status 为 `saved`
  - blocked_by: T010
  - maps_to: US3, FR-006, user-visible-output
  - verify: `wechat_create_draft` result + `wechat_get_draft_status` evidence

- [x] T012 [US3] batchget 和 ledger 反查
  - scope: adapter `/accounts/xiaban/drafts/batchget`, hermes-db `wechat_articles`
  - slice: batchget 找到 media_id；ledger 记录 `status=drafted`
  - blocked_by: T011
  - maps_to: US3, FR-006, Evidence Gate
  - verify: 记录 batchget found、title、media_id、ledger status

---

## Phase 5: Verification And Closeout

**目标**: 收口构建、测试、验收和部署跟进。

- [x] T013 [Verify] 运行相关 build/test
  - scope: `packages/wechat-draft`, `packages/wechat-draft-adapter`
  - slice: 代码和 smoke 脚本在当前工作区可构建
  - blocked_by: T001-T006
  - maps_to: FR-008
  - verify: `rtk pnpm --filter @mcps/wechat-draft build`; `rtk pnpm --filter @mcps/wechat-draft-adapter build`; renderer/config tests

- [x] T014 [Docs] 更新账号命名和运维文档
  - scope: `packages/wechat-draft/docs/*`, `packages/wechat-draft-adapter/DEPLOYMENT.md`, `specs/wechat-draft-multi-account-production/*`
  - slice: 文档说明 `xiaban` 是《下班不躺平》的正式 account id，记录 ECS sync 和 smoke 步骤
  - blocked_by: T007-T012
  - maps_to: FR-010, closeout
  - verify: 文档不含 secret；步骤可复现

- [x] T015 [Closeout] 生成 acceptance 和 commit plan
  - scope: `specs/wechat-draft-multi-account-production/acceptance.md`, optional `commit-plan.md`
  - slice: 三维 verdict 覆盖 Component / Workflow / User-visible Outcome
  - blocked_by: T013, T014
  - maps_to: prior-closure-failure, Evidence Gate
  - verify: acceptance 记录 PASS/FAIL、media_id、batchget、ledger、残留风险

---

## 依赖与顺序

- 关键路径：T001 -> T002 -> T003 -> T007 -> T008 -> T009 -> T010 -> T011 -> T012 -> T015。
- 可并行：
  - T004 可与 T001-T003 并行。
  - T006 可独立收口，但必须在 T011 前完成。
  - T014 可在 smoke 结果稳定后并行完善。
- T009-T012 是真实外部副作用任务，只创建草稿，不发布。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|-------------|----------|
| US1 外部化账号注册表 | T001, T002, T003 |
| US2 接入《下班不躺平》 | T004, T005, T007, T008 |
| US3 生产 smoke 完整闭环 | T009, T010, T011, T012, T015 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|----------------------|----------|----------|
| ADR-001 `xiaban` account id | T002, T014 | T015 |
| ADR-002 YAML config priority | T001, T003 | T013 |
| ADR-003 `xiaban.default` profile | T004, T005 | T013 |
| 安全 | T002, T007, T008, T014 | T015 |
| 一致性 | T003, T007, T010 | T012, T015 |
| 可验证性 | T009-T012 | T015 |

---

## Context Manifest

已生成 [context-manifest.md](context-manifest.md)。原因：本 feature 命中 `multi-stage-workflow`、`external-side-effects`、`artifact-handoff`、`user-visible-output` 和 `prior-closure-failure`，实现/验证需要保留跨会话上下文。

---

## Stage Readiness

- 推荐下一步：`execute-plan`
- 阻塞项：无。执行前需注意 T007-T012 会触发 ECS 和微信官方 API 真实副作用。
