# Implementation Plan: WeChat Draft Multi-Account Production

**Workspace**: `wechat-draft-multi-account-production` | **Date**: 2026-06-25 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/wechat-draft-multi-account-production/spec.md`

---

## Summary

将 `wechat-draft` 的账号配置从 hardcoded fallback 推进到可部署账号注册表，并以 `xiaban` 为首个新增账号跑通 `wechat-draft -> wechat-draft-adapter -> 微信草稿箱 -> batchget/ledger` 的生产 smoke。

---

## Architecture Overview

```text
packages/wechat-draft/config/accounts.yaml
        |
        v
ConfigLoader -----> wechat_list_accounts
        |
        +-----> DraftWorkflow -----> HermesDbClient -----> hermes-db workflow_artifacts / wechat_articles
        |
        +-----> WechatAdapterClient -----> ECS wechat-draft-adapter
                                      |
                                      +-----> WeChat Official API

Style profile registry:
xiaban.default -> canonical renderer -> wechat_api_article -> wechat_create_draft
```

本次不改变职责边界：`wechat-draft` 不持有 AppSecret，不直连微信官方 API；`wechat-draft-adapter` 继续作为 ECS 固定出口和 token 管理层。

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| `packages/wechat-draft/config/accounts.yaml` | Account registry entries | `ConfigLoader`, `wechat_list_accounts`, `DraftWorkflow` | `wechat_list_accounts` 返回 `xiaban`；draft workflow 能解析 adapter config |
| `packages/wechat-draft-adapter/.env` / ECS `/opt/wechat-adapter/.env` | `ALLOWED_ACCOUNTS` 和 `WECHAT_APPID_XIABAN` / `WECHAT_APPSECRET_XIABAN` | ECS adapter `loadCredentials()` | `/health` 返回 `xiaban`；`check-credentials` success |
| `wechat_upload_asset` | body `wechat_url`, cover `thumb_media_id` | `ArticleDocumentToWechatArtifactBuilder`, `ArtifactValidator` | `wechat_validate_publish_artifact` valid |
| `ArticleDocumentToWechatArtifactBuilder` 或 smoke fixture | `wechat_api_article` publish-ready artifact | `wechat_create_draft` | `wechat_create_draft` 返回 `media_id` |
| `wechat_create_draft` | WeChat draft `media_id` and local job state | `wechat_get_draft_status`, adapter `draft_batchget`, hermes ledger | status saved；batchget 找到 draft；ledger 有 `wechat_media_id` |

**孤儿 artifact 处理**: 不允许新增只生成不消费的配置或 smoke 中间产物；每个 smoke 产物必须进入下一步或记录跳过原因。

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 安全 | secret 只存在 env，不进 git 和验收正文 | 配置文件只放 auth ref / hint；检查输出 redacted | `git status` 不包含 `.env`；smoke 日志不含 secret |
| 一致性 | MCP registry、adapter health、style profile 使用同一 account id | `xiaban` 作为统一 machine id | list accounts、health、smoke 参数一致 |
| 可演进性 | 新公众号主要改一份 registry + style profile | `ConfigLoader` 优先读配置文件，fallback 兼容 | 新增 `xiaban` 不需要改 server tool schema |
| 可验证性 | full MCP path 可 replay | smoke 脚本/步骤固定，acceptance 记录证据 | `acceptance.md` 记录 media_id、batchget、ledger |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001 account id 使用 `xiaban` | 本地 adapter env 已用 `xiaban`，已有 `yueliang` 短拼先例 | `xiaban` / `xiabanbutangping` / 中文名 / 缩写 | 使用 `xiaban` | 与全拼 `weiyuchengchun` 不完全一致，需要文档化命名规则 | 本地 note account-config 和现有项目约定 |
| ADR-002 账号注册表使用文件配置优先 | hardcoded config 导致本地、ECS、MCP 不一致 | 继续 hardcode / env-only / YAML config / remote config | YAML config 优先，inline fallback | 需要轻量解析和验证；不支持热更新 | UNVERIFIED |
| ADR-003 `xiaban.default` 先实现 production-safe profile | 需要先完成草稿可见闭环 | 精细还原品牌视觉 / 先用安全 profile 后续精修 | 先用安全 profile，避免阻塞 smoke | 初版视觉可能不够最终风格化 | note readme/writing-style 可后续增强 |

---

## Key Design Decisions

### Decision 1: 配置加载优先级

- **背景**: 当前 `ConfigLoader` 只使用 inline defaults，新增账号需要改源码。
- **选项**:
  - A: 继续 hardcode — 最小改动，但每次新增账号都会重复出错。
  - B: env-only — 不适合表达 display name、style profile、adapter metadata 等结构化配置。
  - C: YAML/JSON file + fallback — 结构清晰，适合当前规模。
- **结论**: 使用 YAML/JSON file + inline fallback。优先复用现有 `config/accounts.example.yaml` 结构，避免引入远程配置中心。
- **影响**: 需要 `ConfigLoader` 支持读取 `WECHAT_DRAFT_CONFIG_PATH` 或默认 config path，并校验 account id。
- **来源**: UNVERIFIED，本地代码和配置现实。

### Decision 2: 不把 adapter secret 同步逻辑放进 MCP

- **背景**: adapter secret 属于 ECS runtime，MCP 不应持有 AppSecret。
- **结论**: 本 feature 只提供验证和部署步骤；不让 `wechat-draft` 读取 `WECHAT_APPSECRET_*`。
- **影响**: production smoke 需要分别验证 adapter health 和 MCP list accounts。
- **来源**: 既有 `wechat-draft-mcp` spec 的安全边界。

---

## Module Design

### Module: `ConfigLoader`

**职责**: 加载 `ServiceConfig`，并提供 account / adapter 查询。

**YAGNI 决策**: 第 4 层停止，复用已安装或可接受的轻量 YAML 解析能力；不做远程配置、热更新或 schema registry。

**改动概述**:

- 增加 config path 读取，建议优先级：
  1. `WECHAT_DRAFT_CONFIG_PATH`
  2. `packages/wechat-draft/config/accounts.yaml` 或部署时挂载路径
  3. inline fallback
- 校验 account id：小写 ASCII、数字和下划线/连字符如需支持需明确；本轮要求 `xiaban`。
- 校验 adapter `allowed_accounts` 覆盖 enabled account 的 `adapter_account_ref`。

### Module: Account Registry

**职责**: 记录 `weiyuchengchun`、`yueliang`、`xiaban` 账号配置。

**改动概述**:

- 新增或更新 production config 示例。
- 不写 raw secret。
- 为 `xiaban` 写入 display name、adapter ref、style profile metadata。

### Module: `WechatStyleProfile`

**职责**: 提供账号级 HTML style profile。

**YAGNI 决策**: 第 5/6 层停止，用现有静态 profile map 增加 `xiaban.default`；不引入 style profile 动态加载。

**改动概述**:

- 增加 `XIABAN_DEFAULT_PROFILE`。
- `STYLE_PROFILES` 注册 `xiaban.default`。
- 测试证明 unknown profile 仍 fail closed。

### Module: `wechat-draft-adapter` Deployment Sync

**职责**: 让 ECS adapter 运行环境加载本地已准备的 `xiaban` env。

**改动概述**:

- 同步 `.env` 到 ECS 或手工更新 `/opt/wechat-adapter/.env`。
- 重启 `wechat-adapter`。
- 通过 `/health` 和 `check-credentials` 验证，不输出 secret。

### Module: Production Smoke

**职责**: 固定 full MCP path 验收步骤。

**改动概述**:

- 更新或新增 smoke 脚本，支持 `WECHAT_CANONICAL_SMOKE_ACCOUNT=xiaban`。
- 若 `HERMES_DB_AUTH_TOKEN` 缺失，必须 fail/skip with blocker，不走 direct fallback 当作通过。
- 记录 batchget 和 ledger 结果到 `acceptance.md`。

---

## Project Structure

```text
packages/wechat-draft/
  config/accounts.example.yaml
  src/config/loader.ts
  src/config/types.ts
  src/render/WechatStyleProfile.ts
  scripts/live-canonical-smoke.mjs

packages/wechat-draft-adapter/
  .env                  # ignored local secret, source for ECS sync only
  DEPLOYMENT.md
  quick-deploy.sh

specs/wechat-draft-multi-account-production/
  spec.md
  plan.md
  tasks.md
  context-manifest.md
  acceptance.md         # verify/closeout
```

---

## Risks and Tradeoffs

- **ECS env drift**: 本地 `.env` 已有 `xiaban`，ECS 尚未同步。必须把 health 输出作为验收门。
- **Secret 泄漏风险**: 任何同步和日志都必须 redacted；不把 `.env` 纳入 git。
- **微信 API 真实副作用**: 只创建草稿，使用明显测试标题，禁止 publish/mass-send。
- **配置解析复杂度**: 不做动态配置和远程配置，保持 MVP 文件配置。
- **视觉不最终**: `xiaban.default` 初版可以先 production-safe，后续再按 note 风格精修。

---

## Evolution Path

- **MVP**: 文件账号注册表 + `xiaban` onboarding + full MCP smoke。
- **成长期**: style profile 也外部化，账号 registry 绑定 note 仓库资料路径。
- **成熟期**: deployment smoke 成为 release pipeline 的一部分，支持多账号矩阵验证。

---

## Verification Strategy

1. Local build:
   - `rtk pnpm --filter @mcps/wechat-draft build`
   - `rtk pnpm --filter @mcps/wechat-draft-adapter build`
2. Local renderer/config tests:
   - `rtk node packages/wechat-draft/test-article-document-renderer.mjs`
   - 增加或更新 config loader/account registry 测试。
3. Adapter production checks:
   - ECS `/health` includes `xiaban`
   - `/accounts/xiaban/check-credentials` success
4. Full MCP path smoke:
   - upload body image and cover image
   - create publish-ready artifact in hermes-db
   - validate artifact
   - create draft via MCP
   - get draft status
   - batchget verify
   - ledger verify
5. Acceptance:
   - `specs/wechat-draft-multi-account-production/acceptance.md` records media_id, checks and residual risks.

---

## Stage Readiness

- 是否需要 `data-model.md`：不需要。账号 registry 是现有 `ServiceConfig` 的配置外化，不引入新持久化数据库实体。
- 下一步建议：`tasks`
- 阻塞项：无；实现时需确认 YAML 解析依赖选择，优先复用现有依赖或最小新增。

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | 必须 | 主实现计划 |
| data-model.md | 不需要 | 不新增数据库实体 |
| tasks.md | 后续阶段生成 | 由 `tasks` 阶段产出 |
| acceptance.md | 后续阶段生成 | 用于最终验收结论 |

---

## Sources

| 决策 | 来源 | 备注 |
|------|------|------|
| ADR-001 | `/Users/yqg/learning/biji/note/.agents/skills/account-config/SKILL.md` | note 仓库账号配置加载方式 |
| ADR-001 | `/Users/yqg/learning/biji/note/04-副业/公众号/*/readme.md` | 公众号中文 display name 和内容资料 |
| ADR-002 | `packages/wechat-draft/config/accounts.example.yaml` | 现有配置结构示例 |
| ADR-003 | `packages/wechat-draft/src/render/WechatStyleProfile.ts` | 现有 style profile registry |
