# Commit Plan: WeChat Draft Multi-Account Production

**Workspace**: `wechat-draft-multi-account-production`  
**Date**: 2026-06-25  
**Status**: Confirmed / Committed locally

> 已获得用户确认并完成本地 commit。

---

## Summary

当前 feature 已 PASS。建议把核心实现、验证脚本、文档和 SDD 产物按 3 个 commit 批次提交。工作区还有若干此前已存在或归属不完全确定的 dirty files，需要用户确认后才能纳入提交。

---

## Included Files

| File | Reason | Evidence |
|---|---|---|
| `packages/wechat-draft/package.json` | 新增 YAML 配置读取依赖 | T001, local tests |
| `pnpm-lock.yaml` | 锁定 YAML 依赖版本 | T001, local tests |
| `packages/wechat-draft/src/config/loader.ts` | 外部 YAML/JSON account registry 与一致性校验 | T001, T003 |
| `packages/wechat-draft/config/accounts.example.yaml` | 记录 `weiyuchengchun`、`yueliang`、`xiaban` 示例配置 | T002 |
| `packages/wechat-draft/src/render/WechatStyleProfile.ts` | 注册 `xiaban.default` profile | T004 |
| `packages/wechat-draft/test-config-loader.mjs` | 覆盖配置加载和校验 | T001, T003 |
| `packages/wechat-draft/test-regressions.mjs` | 覆盖 Hermes metadata 和 JobStore 回归 | T006 |
| `packages/wechat-draft/test-article-document-renderer.mjs` | 覆盖 `xiaban.default` rendering | T004 |
| `packages/wechat-draft/src/hermes/HermesDbClient.ts` | metadata string normalize 修复 | T006 |
| `packages/wechat-draft/src/store/JobStore.ts` | status 查询返回最新 `updated_at` 状态 | T006 |
| `packages/wechat-draft/scripts/live-canonical-smoke.mjs` | full MCP smoke：强制 Hermes、创建 workflow run/artifacts、创建 draft、batchget 验证 | T005, T009-T012 |
| `packages/wechat-draft/README.md` | 多账号与生产 smoke 文档 | T014 |
| `packages/wechat-draft/docs/api-risk-control.md` | 风险控制文档更新 | T014 |
| `packages/wechat-draft/docs/canonical-article-artifact.md` | canonical artifact handoff 文档更新 | T014 |
| `packages/wechat-draft/docs/configuration.md` | 配置优先级和 account registry 文档更新 | T014 |
| `packages/wechat-draft/docs/error-handling.md` | 错误处理文档更新 | T014 |
| `packages/wechat-draft/docs/runbook.md` | 生产 smoke/runbook 更新 | T014 |
| `packages/wechat-draft/docs/wechat-ready-artifact-example.md` | publish-ready artifact 示例更新 | T014 |
| `packages/wechat-draft-adapter/DEPLOYMENT-GUIDE.md` | adapter 部署说明更新 | T014 |
| `packages/wechat-draft-adapter/DEPLOYMENT.md` | adapter deployment/runbook 更新 | T014 |
| `packages/wechat-draft-adapter/README.md` | adapter 多账号能力说明更新 | T014 |
| `specs/.active` | 指向当前 feature | SDD continuation |
| `specs/wechat-draft-multi-account-production/README.md` | feature 入口文档 | SDD artifacts |
| `specs/wechat-draft-multi-account-production/spec.md` | 需求规格 | SDD artifacts |
| `specs/wechat-draft-multi-account-production/plan.md` | 实现方案 | SDD artifacts |
| `specs/wechat-draft-multi-account-production/tasks.md` | 已完成任务清单 | SDD artifacts |
| `specs/wechat-draft-multi-account-production/context-manifest.md` | 跨阶段上下文清单 | SDD artifacts |
| `specs/wechat-draft-multi-account-production/verify-evidence.md` | Verify evidence package | closeout |
| `specs/wechat-draft-multi-account-production/acceptance.md` | PASS 验收、closeout、knowledge capture | T015 |
| `specs/wechat-draft-multi-account-production/commit-plan.md` | 提交前确认计划 | closeout |

---

## Excluded Files

| File | Reason |
|---|---|
| `.pnpm-store/` | 本地 pnpm runtime/cache 文件，不应提交。 |
| `specs/wechat-asset-upload/acceptance.md` | 属于前一个 `wechat-asset-upload` feature，不属于当前提交范围。 |

---

## Needs User Decision

| File | Why Uncertain | Question |
|---|---|---|
| `packages/wechat-draft-adapter/Dockerfile.simple` | 只是启动注释变更，且此前已脏；不影响当前 feature 验收证据。 | 是否纳入 adapter 部署修正 commit？ |
| `packages/wechat-draft-adapter/package.json` | `start` 从 `dist/server.js` 改为 `dist/index.js`，可能是部署必要修复，但此前已脏。 | 是否和当前 feature 一起提交？ |
| `packages/wechat-draft-adapter/quick-deploy.sh` | 新增部署脚本，包含 xiaban 模板，但未作为验收必需路径使用。 | 是否纳入当前 feature，还是另起部署工具 commit？ |
| `packages/wechat-draft/test-adapter-client-upload.mjs` | 将 httpbin 依赖改成本地 HTTP server，属于 asset upload 测试稳定性，不是当前 multi-account 主线。 | 是否纳入当前 feature，还是留给 asset upload/测试稳定性提交？ |

只要这些文件没有明确归属，就不得执行提交。

---

## Risks

| Risk | Impact | Handling |
|---|---|---|
| Existing dirty files | 可能混入用户或上一 feature 的改动 | 未确认文件列入 Needs User Decision。 |
| Real external side effects | 已创建真实 `xiaban` 草稿和上传素材 | acceptance 已记录 media/artifact evidence；不发布、不删除。 |
| Secrets | `.env` 和 token 不应进入仓库 | commit plan 不包含 `.env`；验收只记录脱敏证据。 |
| Local cache | `.pnpm-store/` 出现在未跟踪文件中 | 明确排除。 |

---

## Commit Batches

| Batch | Files | Commit Message | Rationale |
|---|---|---|---|
| 1 | config loader, account YAML, style profile, package/lock, config/render tests | `feat(wechat-draft): add xiaban account registry support` | 核心账号注册和渲染能力。 |
| 2 | Hermes/JobStore regression fixes, live canonical smoke | `fix(wechat-draft): harden production draft smoke path` | 生产闭环必需修复和 full MCP smoke。 |
| 3 | docs and `specs/wechat-draft-multi-account-production/*`, `specs/.active` | `docs(wechat-draft): record multi-account production rollout` | 文档、SDD 产物、验收和提交计划。 |

---

## Execution Rules

- 未获得用户明确确认前，不得执行 `git add` 或 `git commit`。
- 只允许 add `Included Files` 中属于已确认 batch 的文件。
- 不得使用 `git add -A`、`git add .` 或等价宽泛命令。
- 每个 batch 单独提交；任一 batch 失败时停止后续 batch。
- 不自动执行 `git push`。push 必须由用户另行明确要求。

---

## User Confirmation

已完成本地提交。`.pnpm-store/` 仍保持未跟踪状态。
