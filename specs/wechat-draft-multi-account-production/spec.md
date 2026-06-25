# Feature Specification: WeChat Draft Multi-Account Production

**Workspace**: `wechat-draft-multi-account-production`  
**Created**: 2026-06-25  
**Status**: Draft  
**Input**: 用户描述: "将 wechat-draft 与 wechat-draft-adapter 的多公众号生产化接入补齐，首个新增账号为《下班不躺平》，机器账号 ID 使用 xiaban。"

> 写入本文件后，应同步更新 `specs/.active` 指向当前 workspace。

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | 需要串联 adapter env、MCP account registry、asset upload、artifact validation、draft create、batchget 和 ledger 验证。 |
| `external-side-effects` | ✅ | 生产 smoke 会调用微信官方 API 上传素材并创建真实草稿。 |
| `artifact-handoff` | ✅ | `wechat_upload_asset` 产出的 `wechat_url` / `thumb_media_id` 会进入 publish-ready artifact，再被 `wechat_create_draft` 消费。 |
| `user-visible-output` | ✅ | 最终产物是微信公众号后台可见草稿。 |
| `prior-closure-failure` | ✅ | 既有链路已有 direct adapter smoke，但 full MCP path 与部署配置闭环尚未稳定验证。 |
| `bugfix-loop-breaker` | ❌ | 本 feature 是生产化补齐和配置治理，不是重复失败的未知根因 bugfix。 |

**结论**: 下游必须启用 Producer-Consumer Matrix、Evidence Gate、Workflow Replay 和三维 Verdict。closeout 需要持久化 `acceptance.md`，不能只在对话里宣布完成。

---

## User Scenarios & Testing

### User Story 1 - 外部化公众号账号注册表 (Priority: P1)

作为 `wechat-draft` MCP 的维护者，我希望公众号账号配置来自一个可部署的账号注册表，而不是散落在 TypeScript 默认值和 adapter env 中，以便新增公众号时能稳定复现、审查和部署。

**Why this priority**: 当前新增 `xiaban` 时已出现本地 env、ECS env、MCP hardcoded accounts 不一致的问题；先治理账号注册表，后续生产 smoke 才有稳定前提。

**Acceptance Scenarios**:

1. **[US1-1] 配置文件优先**
   **Given** 存在 `packages/wechat-draft/config/accounts.yaml` 或等价生产配置  
   **When** `wechat-draft` 启动并调用 `wechat_list_accounts`  
   **Then** 返回配置文件中的 enabled accounts，包含 `weiyuchengchun`、`yueliang`、`xiaban`

2. **[US1-2] 默认值兼容**
   **Given** 生产配置文件不存在  
   **When** `wechat-draft` 启动  
   **Then** 仍使用安全的 inline fallback，不破坏现有本地开发路径

**Edge Cases**:

- **[US1-3]** 账号 ID 必须为小写 ASCII、env-safe、稳定短拼；`xiaban` 是《下班不躺平》的正式机器 ID。
- **[US1-4]** 配置文件不能包含 raw AppSecret、AccessToken 或 adapter auth token。
- **[US1-5]** adapter `allowed_accounts` 与 MCP `accounts` 不一致时，验证或 smoke 必须暴露差异。

### User Story 2 - 接入《下班不躺平》账号 (Priority: P1)

作为内容生产调用方，我希望能用 `account="xiaban"` 将准备好的文章保存到《下班不躺平》公众号草稿箱，以便后续人工校验和发布。

**Why this priority**: `xiaban` 是本轮新增账号，也是验证多账号机制是否真的可用的首个生产切片。

**Acceptance Scenarios**:

1. **[US2-1] Adapter 账号可用**
   **Given** ECS adapter 已加载 `WECHAT_APPID_XIABAN`、`WECHAT_APPSECRET_XIABAN` 且 `ALLOWED_ACCOUNTS` 包含 `xiaban`  
   **When** 调用 `/accounts/xiaban/check-credentials`  
   **Then** 返回 token metadata success，且响应不输出 token 或 secret

2. **[US2-2] MCP 账号可发现**
   **Given** `wechat-draft` 已加载账号注册表  
   **When** 调用 `wechat_list_accounts`  
   **Then** 返回 `account_id="xiaban"`、`display_name="下班不躺平"`、`adapter_account_ref="xiaban"` 的可用账号

3. **[US2-3] 风格 profile 可用**
   **Given** artifact 使用 `style_profile_id="xiaban.default"`  
   **When** canonical renderer 构造 WeChat-safe HTML  
   **Then** 渲染使用《下班不躺平》的风格 profile，不回退到 `yueliang.default`

**Edge Cases**:

- **[US2-4]** 如果 ECS 尚未同步 `xiaban` env，`check_credentials` 或 draft create 必须返回可操作错误。
- **[US2-5]** 如果 `xiaban.default` 不存在，artifact builder 或 renderer 必须失败，而不是静默套用其他账号样式。

### User Story 3 - 生产 smoke 证明完整闭环 (Priority: P1)

作为维护者，我希望部署后能用固定 smoke 步骤验证从素材上传到微信草稿可见的完整链路，以便确认生产环境真的可用。

**Why this priority**: 之前已有 direct adapter smoke，但 full MCP path 尚未成为可重复验收证据。

**Acceptance Scenarios**:

1. **[US3-1] 素材上传闭环**
   **Given** `account="xiaban"` 且 adapter credentials 有效  
   **When** 调用 `wechat_upload_asset` 上传正文图和封面图  
   **Then** 正文图返回 `wechat_url`，封面图返回 `thumb_media_id`

2. **[US3-2] 草稿创建闭环**
   **Given** hermes-db 中存在 `stage="publish_ready"`、`type="wechat_api_article"`、`account="xiaban"` 的 artifact  
   **When** 依次调用 `wechat_validate_publish_artifact` 和 `wechat_create_draft`  
   **Then** 返回 `media_id`，`wechat_get_draft_status` 为 `saved`

3. **[US3-3] 反查和 ledger**
   **Given** `wechat_create_draft` 返回 `media_id`  
   **When** adapter `draft_batchget` 反查草稿，且 hermes-db 查询 article ledger  
   **Then** 能找到同一草稿，ledger 记录 `status="drafted"` 和 `wechat_media_id`

**Edge Cases**:

- **[US3-4]** 生产 smoke 只创建草稿，不发布、不群发、不删除。
- **[US3-5]** 如果 hermes-db token 缺失，验收必须标为阻塞，不能走 direct adapter fallback 冒充 full MCP path。

---

## Requirements

### Functional Requirements

- **FR-001**: `wechat-draft` 必须支持从外部账号注册表加载 accounts、adapters、credentials hints 和 hermes-db runtime config。
- **FR-002**: 系统必须正式支持 `account_id="xiaban"`，display name 为 `下班不躺平`。
- **FR-003**: `xiaban` 的 adapter account ref、MCP account id、style profile id 必须一致可追踪。
- **FR-004**: `wechat-draft-adapter` 的本地 env 与 ECS env 必须能验证是否一致，至少通过 `/health` 和 `check-credentials` 证明。
- **FR-005**: `xiaban.default` style profile 必须存在，并可被 canonical renderer 使用。
- **FR-006**: 生产 smoke 必须走 full MCP path，不得以 direct adapter fallback 替代。
- **FR-007**: 所有测试和文档不得输出 raw AppSecret、AccessToken、adapter auth token 或 hermes-db token。
- **FR-008**: 已有 `weiyuchengchun` 和 `yueliang` 行为不得回退。
- **FR-009**: 当前未提交但影响生产闭环的 `HermesDbClient` metadata normalize 和 `JobStore` 最新状态读取修复必须纳入实现或明确排除原因。
- **FR-010**: 文档必须记录账号 ID 命名规则：稳定短拼、ASCII、小写、env-safe，已上线后不轻易改名。

### Non-Functional Requirements

- **NFR-001**: 新增配置加载不得引入会提交 secret 的路径。
- **NFR-002**: 配置不一致时错误必须可操作，指出是 MCP registry、adapter allowed accounts、credential env 还是 hermes token 问题。
- **NFR-003**: 生产 smoke 的真实微信副作用必须最小化，只创建可人工检查的测试草稿。
- **NFR-004**: 账号注册表应保持 MVP 复杂度，不引入远程配置中心、数据库配置管理或动态热更新。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 安全 | 不落库、不提交 secret | 公众号 AppSecret 和 token 泄漏代价高 | `.env` 不入库；日志/验收只输出 redacted 状态 | 是 |
| 一致性 | MCP、adapter、style profile 使用同一 account id | 避免本地能跑、部署不可见 | `wechat_list_accounts`、adapter `/health`、smoke 输出一致 | 是 |
| 可演进性 | 新公众号不需要改多处硬编码 | 后续可能继续新增公众号 | 账号注册表新增一项即可驱动 MCP list/config | 是 |
| 可验证性 | full MCP path 有固定 replay | 之前闭环证据不足 | smoke evidence 写入 acceptance | 是 |

### Key Entities

- **Account Registry Entry**: 公众号机器 ID、display name、adapter ref、style profile、enabled 状态和 metadata。
- **Adapter Env Account**: `ALLOWED_ACCOUNTS` 中的 account id 及对应 `WECHAT_APPID_<ACCOUNT>` / `WECHAT_APPSECRET_<ACCOUNT>`。
- **Style Profile**: `xiaban.default` 等账号级微信安全 HTML 样式配置。
- **Production Smoke Record**: 记录 account、asset upload result、artifact id、media_id、batchget 结果和 ledger 结果的验收证据。

---

## Out of Scope

- 不实现自动发布、群发、删除、更新草稿或定时发布。
- 不把微信 AppSecret 移入 `wechat-draft` MCP 或 hermes-db。
- 不引入远程配置中心或 UI 管理后台。
- 不重构 hermes-db schema。
- 不批量迁移 note 仓库的公众号内容资产。

---

## Unclear Questions

- `xiaban.default` 的最终视觉样式是否应完全来自 note 仓库 `下班不躺平/writing-style.md`，还是先用 minimal production-safe profile 后续再精修。
- 生产 smoke 是否在本机触发，还是在 NAS 部署后的目标 runtime 触发。

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项：无硬阻塞；上述 unclear questions 不影响先设计 MVP 方案。
