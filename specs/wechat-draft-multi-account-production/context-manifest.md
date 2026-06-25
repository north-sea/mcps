# Context Manifest: WeChat Draft Multi-Account Production

**Workspace**: `wechat-draft-multi-account-production`  
**Created**: 2026-06-25  
**Status**: active

> 本文件用于记录 SDD 各阶段必须读取的高信号上下文。它不是待修改源文件清单，也不替代实现阶段按需阅读代码。

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-multi-account-production/spec.md` | 理解 `xiaban` account id、验收场景和 out-of-scope | implement | yes |
| `specs/wechat-draft-multi-account-production/plan.md` | 遵守账号注册表、adapter 安全边界和 smoke 方案 | implement | yes |
| `specs/wechat-draft-multi-account-production/tasks.md` | 按依赖顺序执行，避免先触发真实微信副作用 | implement | yes |
| `packages/wechat-draft/src/config/loader.ts` | 当前 hardcoded accounts 和 config fallback 入口 | implement | yes |
| `packages/wechat-draft/src/config/types.ts` | ServiceConfig / AccountConfig 类型边界 | implement | yes |
| `packages/wechat-draft/config/accounts.example.yaml` | 现有账号配置示例结构 | implement | yes |
| `packages/wechat-draft/src/render/WechatStyleProfile.ts` | 现有 style profile registry，需新增 `xiaban.default` | implement | yes |
| `packages/wechat-draft/scripts/live-canonical-smoke.mjs` | 生产 smoke 主入口，需要支持 full MCP path evidence | implement | yes |
| `packages/wechat-draft-adapter/src/server.ts` | adapter allowed accounts / credential env 命名规则 | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-multi-account-production/spec.md` | 验证 P1 user stories 和 no-secret 约束 | verify | yes |
| `specs/wechat-draft-multi-account-production/plan.md` | 检查是否偏离账号注册表和 adapter 安全边界 | verify | yes |
| `specs/wechat-draft-multi-account-production/tasks.md` | 检查任务完成范围和副作用步骤证据 | verify | yes |
| `specs/wechat-canonical-article-artifact/acceptance.md` | 已有 canonical/direct adapter live smoke 证据和缺口 | verify | yes |
| `packages/wechat-draft/docs/canonical-article-artifact.md` | 理解 canonical artifact 与 draft MCP 边界 | verify | yes |
| `packages/wechat-draft/docs/runbook.md` | 对照运维步骤和 adapter 检查方式 | verify | no |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `/Users/yqg/learning/biji/note/.agents/skills/account-config/SKILL.md` | 参考 note 仓库账号配置加载语义，确认它管理中文账号资料，不定义 MCP machine id | plan / implement | yes |
| `/Users/yqg/learning/biji/note/.agents/skills/_shared/naming-convention.md` | 参考 skill 命名约定，确认短稳定命名优先于批量重命名 | plan | yes |
| `/Users/yqg/learning/biji/note/04-副业/公众号/下班不躺平/readme.md` | `xiaban` display name、定位、视觉风格来源 | implement | yes |
| `packages/wechat-draft-adapter/.env` | 本地 ignored secret 文件已包含 `xiaban`；只能做 redacted 检查，不得提交 | implement / verify | yes |

---

## Rules

- 真实 smoke 前必须确认当前命令环境有 `WECHAT_ADAPTER_AUTH_TOKEN` 和 `HERMES_DB_AUTH_TOKEN`，否则不得把 direct adapter fallback 当作 full MCP path PASS。
- 任何验收文档只记录 token/secret 的存在状态、长度或 redacted 摘要，不记录原值。
- `xiaban` 是《下班不躺平》的正式 machine account id；后续实现不得同时引入 `xiabanbutangping` 或 `xiabubutangping` 作为别名，除非另写迁移说明。
