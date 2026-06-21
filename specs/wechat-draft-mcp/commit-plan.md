# Commit Plan: WeChat Draft MCP

**Workspace**: `wechat-draft-mcp`
**Date**: 2026-06-21
**Status**: Awaiting User Confirmation

---

## Summary

当前 feature 有大量相关 diff：
- **Modified**: 3 个文件（package.json, pnpm-lock.yaml, specs/.active）
- **Untracked**: 3 个目录（packages/wechat-draft/, packages/wechat-draft-adapter/, specs/wechat-draft-mcp/）

所有修改均与 wechat-draft-mcp feature 直接相关，无无关 dirty files。

**建议提交策略**: 分 2 个 batch
1. Batch 1: specs 文档（规格、方案、任务、验收）
2. Batch 2: 代码实现 + 根目录配置（MCP server, ECS adapter, monorepo scripts）

---

## Included Files

| File | Reason | Evidence |
|---|---|---|
| `specs/.active` | 切换当前 active feature 为 wechat-draft-mcp | tasks.md T005-T021, spec.md |
| `specs/wechat-draft-mcp/*.md` | 完整 SDD 文档（spec, plan, tasks, data-model, infrastructure-config, official-api-research, context-manifest, smoke-evidence, MVP-COMPLETION-SUMMARY, acceptance） | SDD workflow 产物，tasks.md 21/22 完成 |
| `package.json` | 新增 wechat-draft 和 wechat-draft-adapter monorepo scripts | 根目录 workspace 管理，便于 pnpm build/dev/start |
| `pnpm-lock.yaml` | wechat-draft 和 wechat-draft-adapter 依赖锁定 | pnpm install 自动生成 |
| `packages/wechat-draft/**/*` | NAS MCP server 完整实现（src/, dist/, docs/, config/, scripts/, package.json, tsconfig.json, README.md） | tasks.md T005-T019, smoke-evidence.md Phase 1-2-4 |
| `packages/wechat-draft-adapter/**/*` | ECS adapter 完整实现（src/, dist/, Dockerfile, .env.example, DEPLOYMENT.md, DEPLOYMENT-GUIDE.md, package.json, tsconfig.json） | tasks.md T011-T013a, smoke-evidence.md Phase 3, ECS 已部署 |

**所有文件均属于 wechat-draft-mcp feature，无跨 feature 混入。**

---

## Excluded Files

无。所有 modified 和 untracked 文件均属于当前 feature。

---

## Needs User Decision

无。所有文件归属明确。

---

## Risks

| Risk | Impact | Handling |
|---|---|---|
| 大量新增文件 (100+ files) | 单次 commit 较大 | 分 2 个 batch：specs 先提交，代码实现后提交 |
| pnpm-lock.yaml 包含 @types/node 版本回退 | 可能影响其他 package 类型检查 | 风险低：只影响 wechat-draft-adapter dev 依赖，不影响 runtime；其他 package 保持原有版本 |
| specs/.active 切换到新 feature | 可能影响其他开发者的 SDD 续接 | 风险低：单人开发，.active 正确反映当前完成的 feature |
| ECS adapter .env.example 包含示例配置 | 可能泄露配置结构 | 风险低：已脱敏，只含变量名和格式说明，无真实密钥 |

---

## Commit Batches

| Batch | Files | Commit Message | Rationale |
|---|---|---|---|
| 1 | `specs/.active`<br>`specs/wechat-draft-mcp/*.md` | `docs(wechat-draft): complete SDD documentation`<br><br>- Add spec.md (requirements and user stories)<br>- Add plan.md (architecture and implementation strategy)<br>- Add tasks.md (21/22 tasks completed, 95.5%)<br>- Add data-model.md, infrastructure-config.md, official-api-research.md<br>- Add smoke-evidence.md, MVP-COMPLETION-SUMMARY.md, acceptance.md<br>- Update specs/.active to wechat-draft-mcp<br><br>Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com> | SDD 文档独立 batch，便于 review 规格和方案 |
| 2 | `package.json`<br>`pnpm-lock.yaml`<br>`packages/wechat-draft/**/*`<br>`packages/wechat-draft-adapter/**/*` | `feat(wechat-draft): implement WeChat draft MCP with ECS adapter`<br><br>Implements three-layer architecture:<br>- NAS MCP Server (packages/wechat-draft)<br>- ECS Adapter (packages/wechat-draft-adapter, deployed to 100.117.14.128:3000)<br>- WeChat Official API (draft/add via adapter)<br><br>Features:<br>- 4 MCP tools: list_accounts, validate_artifact, create_draft, get_draft_status<br>- 7-stage state machine with error classification (12 error codes)<br>- JSONL audit logging with 7-day idempotency<br>- Token caching (7200s TTL + 300s safety margin)<br>- Security: AppSecret only on ECS, Tailscale private network, Bearer auth<br>- Complete documentation (configuration, runbook, error handling, API risk control)<br><br>Scope:<br>- MVP supports weiyuchengchun account only<br>- Draft creation only (no publish/update/delete)<br>- Requires publish-ready artifact with WeChat assets<br>- Material upload out of scope (Phase 2)<br><br>Verification:<br>- ECS adapter deployed and running<br>- Token validation passed (expires_in=7200)<br>- NAS-ECS connectivity verified (Tailscale)<br>- Architecture and security boundaries validated<br><br>Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com> | 代码实现 + 根目录配置同批，保证原子性 |

**说明**：
- Batch 1 仅 specs 文档，便于独立 review
- Batch 2 包含代码实现和 monorepo 配置，确保构建可用
- 每个 batch commit message 包含功能摘要、验证状态和 Co-Authored-By

---

## Execution Rules

- 未获得用户明确确认前，不得执行 `git add` 或 `git commit`。
- 只允许 add `Included Files` 中属于已确认 batch 的文件。
- 不得使用 `git add -A`、`git add .` 或等价宽泛命令。
- 每个 batch 单独提交；任一 batch 失败时停止后续 batch。
- 不自动执行 `git push`。push 必须由用户另行明确要求。

**执行命令预览**:

```bash
# Batch 1
rtk git add specs/.active specs/wechat-draft-mcp/*.md
rtk git commit -F- <<'EOF'
docs(wechat-draft): complete SDD documentation

- Add spec.md (requirements and user stories)
- Add plan.md (architecture and implementation strategy)
- Add tasks.md (21/22 tasks completed, 95.5%)
- Add data-model.md, infrastructure-config.md, official-api-research.md
- Add smoke-evidence.md, MVP-COMPLETION-SUMMARY.md, acceptance.md
- Update specs/.active to wechat-draft-mcp

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF

# Batch 2
rtk git add package.json pnpm-lock.yaml packages/wechat-draft packages/wechat-draft-adapter
rtk git commit -F- <<'EOF'
feat(wechat-draft): implement WeChat draft MCP with ECS adapter

Implements three-layer architecture:
- NAS MCP Server (packages/wechat-draft)
- ECS Adapter (packages/wechat-draft-adapter, deployed to 100.117.14.128:3000)
- WeChat Official API (draft/add via adapter)

Features:
- 4 MCP tools: list_accounts, validate_artifact, create_draft, get_draft_status
- 7-stage state machine with error classification (12 error codes)
- JSONL audit logging with 7-day idempotency
- Token caching (7200s TTL + 300s safety margin)
- Security: AppSecret only on ECS, Tailscale private network, Bearer auth
- Complete documentation (configuration, runbook, error handling, API risk control)

Scope:
- MVP supports weiyuchengchun account only
- Draft creation only (no publish/update/delete)
- Requires publish-ready artifact with WeChat assets
- Material upload out of scope (Phase 2)

Verification:
- ECS adapter deployed and running
- Token validation passed (expires_in=7200)
- NAS-ECS connectivity verified (Tailscale)
- Architecture and security boundaries validated

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
```

---

## User Confirmation

等待用户确认：

- **`确认提交`**: 按上述 batches 执行本地提交。
- **`修改计划`**: 根据用户要求调整 included/excluded/batches。
- **`暂不提交`**: closeout 记录 not_submitted 和剩余 dirty files；feature 已可使用（MCP 和 adapter 均已部署）。
