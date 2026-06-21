# Commit Plan: Closeout hermes-db-batch-planning-api

**Feature**: hermes-db-batch-planning-api
**Date**: 2026-06-16
**Type**: closeout

---

## Commit Strategy

**Single commit** - 所有 closeout 相关文件一起提交

---

## Batch 1: Closeout 记录和状态更新

### Files to Include

```
M  specs/.active
M  specs/hermes-db-batch-planning-api/acceptance.md
M  specs/hermes-db-batch-planning-api/deployment-checklist.md
M  specs/hermes-db-batch-planning-api/tasks.md
A  specs/hermes-db-batch-planning-api/CLOSEOUT.md
A  specs/hermes-db-batch-planning-api/closeout-commit-plan.md
A  specs/hermes-db-batch-planning-api/deploy-to-nas.sh
```

### Commit Message

```
docs(hermes-db): closeout hermes-db-batch-planning-api feature

完成 hermes-db-batch-planning-api feature 的正式关闭：

Deployment Status:
- ✅ Migration 0008_novel_planning_tables 已执行
- ✅ 服务已部署到 NAS 生产环境 (v0.2.23)
- ✅ Smoke test 验证通过（14 个 novel_* 表已创建）
- ✅ 工具模块已加载（4 个 MCP tools）

Updated Files:
- acceptance.md: 升级 verdict 从 CONDITIONAL PASS 到 PASS
- deployment-checklist.md: 更新部署日志和验证清单
- tasks.md: 同步任务状态为 CLOSED - PASS
- CLOSEOUT.md: 完整的 closeout 报告和 lessons learned
- closeout-commit-plan.md: 记录 closeout 提交计划
- deploy-to-nas.sh: NAS 部署脚本（归档）
- .active: 保持当前 feature，便于 SDD 续接解析 closeout 状态

Final Verdict: ✅ PASS

Deferred Actions:
- T018: 跨仓库协调（通知 agents 仓库 bookId→bookSlug 变更）

Closes: hermes-db-batch-planning-api
```

### Verification

- [ ] 所有 closeout 相关文件已暂存
- [ ] Commit message 包含部署状态摘要
- [ ] `.active` 指向 hermes-db-batch-planning-api，便于 SDD 解析当前 closeout 状态
- [ ] 无其他未预期的文件

---

## Files NOT Included (Verification)

以下文件不属于本 feature，不应包含在 commit 中：

- `.github/workflows/mcp-release.yml` (已在 7599974 中提交)
- 任何非 specs/ 目录下的文件

---

## Execution Commands

```bash
# 1. 检查 git status
git status

# 2. 暂存 closeout 文件
git add specs/.active
git add specs/hermes-db-batch-planning-api/acceptance.md
git add specs/hermes-db-batch-planning-api/deployment-checklist.md
git add specs/hermes-db-batch-planning-api/tasks.md
git add specs/hermes-db-batch-planning-api/CLOSEOUT.md
git add specs/hermes-db-batch-planning-api/closeout-commit-plan.md
git add specs/hermes-db-batch-planning-api/deploy-to-nas.sh

# 3. 检查暂存内容
git diff --cached --stat

# 4. 提交
git commit -m "docs(hermes-db): closeout hermes-db-batch-planning-api feature

完成 hermes-db-batch-planning-api feature 的正式关闭：

Deployment Status:
- ✅ Migration 0008_novel_planning_tables 已执行
- ✅ 服务已部署到 NAS 生产环境 (v0.2.23)
- ✅ Smoke test 验证通过（14 个 novel_* 表已创建）
- ✅ 工具模块已加载（4 个 MCP tools）

Updated Files:
- acceptance.md: 升级 verdict 从 CONDITIONAL PASS 到 PASS
- deployment-checklist.md: 更新部署日志和验证清单
- tasks.md: 同步任务状态为 CLOSED - PASS
- CLOSEOUT.md: 完整的 closeout 报告和 lessons learned
- closeout-commit-plan.md: 记录 closeout 提交计划
- deploy-to-nas.sh: NAS 部署脚本（归档）
- .active: 保持当前 feature，便于 SDD 续接解析 closeout 状态

Final Verdict: ✅ PASS

Deferred Actions:
- T018: 跨仓库协调（通知 agents 仓库 bookId→bookSlug 变更）

Closes: hermes-db-batch-planning-api"

# 5. 推送到远程（需要用户确认）
# git push origin main
```

---

## Post-Commit Actions

1. ✅ 验证 commit 已创建
2. ⏳ 推送到远程（等待用户确认）
3. ⏳ 通知 agents 仓库团队（T018）

---

## Notes

- 本次提交只包含文档更新，无代码变更
- 部署脚本 `deploy-to-nas.sh` 仅作归档，不影响生产
- `.active` 保持指向 `hermes-db-batch-planning-api`，表示当前 SDD 状态可被续接路由解析为已 closeout
