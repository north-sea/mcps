# Context Manifest: Agents Capability Reconciliation

**Workspace**: `agents-capability-reconciliation`
**Created**: 2026-06-28
**Status**: active

> 本文件记录 SDD 各阶段必须读取的高信号上下文。它不是待修改源文件清单，也不替代实现阶段按需阅读代码。

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/agents-capability-reconciliation/spec.md` | Defines feature scope, user stories, requirements, traits, and out-of-scope boundaries. | implement | yes |
| `specs/agents-capability-reconciliation/plan.md` | Defines reconciliation table design, status enum, ADRs, Producer-Consumer Matrix, and verification path. | implement | yes |
| `specs/agents-capability-reconciliation/tasks.md` | Defines executable task order, dependencies, and verification points. | implement | yes |
| `specs/note-skill-inventory-matrix/migration-matrix.md` | Source artifact containing the 44 skill rows and candidate landing zones to reconcile. | implement | yes |
| `specs/note-skill-migration-roadmap/roadmap.md` | Defines roadmap boundaries, current feature, downstream features, and invariants. | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/agents-capability-reconciliation/spec.md` | Verify P0/P1 requirements, out-of-scope boundaries, and feature traits. | verify | yes |
| `specs/agents-capability-reconciliation/plan.md` | Check ADRs, Producer-Consumer Matrix, status enum, and verification strategy. | verify | yes |
| `specs/agents-capability-reconciliation/tasks.md` | Check task completion status, coverage, and dependency order. | verify | yes |
| `specs/agents-capability-reconciliation/capability-reconciliation.md` | Verify 44-row reconciliation table, status coverage, evidence paths, and downstream gates after T003 creates it. | verify | no |
| `specs/note-skill-inventory-matrix/migration-matrix.md` | Compare source row count and original candidates against reconciliation output. | verify | yes |
| `specs/note-skill-migration-roadmap/roadmap.md` | Verify active/current consistency and roadmap handoff state. | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `/Users/yqg/personal/AI/agents/apps` | Candidate execution-layer apps for WeChat, Novel, and XHS rows. | implement / verify | no |
| `/Users/yqg/personal/AI/agents/packages` | Candidate shared packages for workflow, adapters, config, style, and observability rows. | implement / verify | no |
| `/Users/yqg/personal/AI/agents/specs` | Candidate acceptance/tasks/spec evidence for agents-side capability status. | implement / verify | no |
| `packages/hermes-db` | Candidate mcps-side data and MCP contract evidence for topics, articles, artifacts, analytics, retrospective, and novel tools. | implement / verify | no |
| `packages/wechat-draft` | Candidate mcps-side draft/render/asset contract evidence for WeChat rows. | implement / verify | no |

---

## Rules

- 每条 entry 必须有 `Reason`；缺少 reason 的 manifest 不得通过 verify。
- `Required = yes` 的本地文件不存在时，当前阶段必须回退到 `plan` 或 `tasks` 更新 manifest。
- 不要把即将修改的源文件列为固定 context；源文件由 implement / verify 按需检查。
- 不复制长文档；只记录路径、来源、用途和短摘要。
- 不引入 `.trellis/`、Trellis CLI、hook、task.py 或自动 context injection。
