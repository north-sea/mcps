# Acceptance: Novel Runtime Contracts

**Workspace**: `novel-runtime-contracts`  
**Date**: 2026-07-07  
**Overall**: PASS WITH DEFERRED IMPLEMENTATION

## Evidence Table

| Requirement | Evidence | Verdict |
|---|---|---|
| FR-001 Capability reconciliation | `capability-reconciliation.md` covers 8 agents novel specs and 10 novel note skill rows | PASS |
| FR-002 Stale task resolution | `capability-reconciliation.md` marks accepted-but-unchecked specs as `stale-task-state` rather than active MCP work | PASS |
| FR-003 Contract gaps | `contract-gap-register.md` identifies missing novel retrospective reports, alerts, constraints, handoff packages, character states, learning candidates, and health | PASS |
| FR-004 Library/Memory split | `owner-table.md` and `replacement-routes.md` keep rules/sources/samples in Library/Wiki and compact decisions in Memory | PASS |
| FR-005 Next feature recommendation | Roadmap advances to `hermes-db-novel-retrospective-contracts`; spec created for next SDD stage | PASS |
| FR-006 No live writes/deletes | This closeout changes docs/spec artifacts only; all note routes keep `deletion_allowed=false` | PASS |

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Required reconciliation, owner, gap, and replacement route artifacts exist. |
| Workflow closure | PASS | Current feature's job was decision/contract boundary closeout, not implementation. |
| User-visible outcome | PASS | Maintainer can see what is done, stale, missing, and what to implement next. |

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| Old logic retirement | 不适用 | No runtime logic was added or replaced. | Do not delete note skills until later archive feature. |
| Publish/live side effects | 已完成 | FR-006 docs-only evidence; no live novel content write. | Keep live writes in next feature tests gated. |
| Roadmap update | 已完成 | `note-skill-migration-roadmap/roadmap.md` points to next implementable MCP feature. | Continue with `hermes-db-novel-retrospective-contracts`. |
| Documentation | 已完成 | Added reconciliation, owner, gap, route, and evidence artifacts. | Use them as input to next plan/tasks. |
| Architecture debt | 已完成 | Contract gap register isolates retrospective persistence gap. | Implement missing contracts next. |
| Knowledge capture | 已完成 | See table below. | Recorded locally only. |
| Commit state | 延后 | User did not request commit; dirty worktree contains unrelated/pre-existing work. | No `git add` or `git commit`. |

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| decision | MCP durable only | Novel writing, review, prompt, and model routing stay in agents/Hermes/Codex; MCP owns only durable state contracts. | `owner-table.md`; `contract-gap-register.md` | novel agent + hermes-db boundary | recorded-only | Enforce in `hermes-db-novel-retrospective-contracts`. |
| pattern | Stale task reconciliation | Accepted feature with unchecked tasks is classified as stale task state when acceptance/roadmap/test evidence is stronger. | `capability-reconciliation.md` | SDD roadmap reconciliation | recorded-only | Agents repo can later normalize old task files. |
| follow-up | Retrospective contracts | Agents retrospective local workflow is done, but live persistence needs hermes-db tools. | `verify-evidence.md`; agents retrospective acceptance | novel retrospective persistence | recorded-only | Implement next feature. |

## Completion Record

- **最终结论**: PASS WITH DEFERRED IMPLEMENTATION
- **已完成**: T001-T012 current-state reconciliation, owner boundary, contract gap register, replacement routes, verification, roadmap recommendation, acceptance.
- **延后**: hermes-db novel retrospective implementation; Library/Wiki import smoke; note skill archive/delete.
- **下一项**: `hermes-db-novel-retrospective-contracts`，阶段从 `spec -> plan/tasks` 开始。
