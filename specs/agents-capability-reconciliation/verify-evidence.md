# Verify Evidence: Agents Capability Reconciliation

**Workspace**: `agents-capability-reconciliation` | **Date**: 2026-06-28  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

---

## Verdict

**Result**: PASS

The reconciliation deliverable is complete for roadmap handoff: source matrix count is 44, reconciliation row count is 44, status enum is used across rows, downstream gates exist for all later roadmap features, and the feature remained documentation-only.

---

## Evidence Table

| Check | Command / Source | Observed Result | Verdict |
|---|---|---|---|
| SDD active feature | `cat specs/.active` | `agents-capability-reconciliation` | PASS |
| Roadmap current feature | [roadmap.md](../note-skill-migration-roadmap/roadmap.md) | `Current Feature: agents-capability-reconciliation` | PASS |
| Source matrix row count | `awk` count between `## Matrix` and `## Count Check` in [migration-matrix.md](../note-skill-inventory-matrix/migration-matrix.md) | `44` | PASS |
| Reconciliation row count | `awk` count between `## Reconciliation Table` and `## Downstream Gates` in [capability-reconciliation.md](capability-reconciliation.md) | `44` | PASS |
| Status enum coverage | `rg` for `verified|partial|absent|stale|contradictory|not-applicable|needs-user-decision` | All rows use one of the planned statuses | PASS |
| Downstream gates | [capability-reconciliation.md](capability-reconciliation.md) | All 6 downstream roadmap features have readiness rows | PASS |
| P0 spot check | `content-ops`, `opencli-integration`, `account-config`, `topic-radar`, `topic-inbox`, `topic-scout`, `wechat-article-pipeline`, `wechat-writer` | All 8 P0 rows have owner, status, evidence, gaps, action, downstream gate, and deletion gate status | PASS |
| Boundary check | [capability-reconciliation.md](capability-reconciliation.md) | Model-generation rows keep execution owner in agents/Hermes/Codex runtime; MCP is only data/contract owner | PASS |
| Context manifest coverage | [context-manifest.md](context-manifest.md) | Implement and Check Context cover spec, plan, tasks, source matrix, roadmap, and reconciliation output | PASS |
| Current repo SDD scope | `git status --short specs/.active specs/note-skill-migration-roadmap specs/agents-capability-reconciliation` | Only SDD files for this roadmap feature are dirty/untracked in this scope | PASS |
| External runtime scope | `git -C /Users/yqg/personal/AI/agents status --short`; `git -C /Users/yqg/learning/biji/note status --short -- .agents/skills .hermes/skills` | No writes were made by this feature; existing external dirty state is outside this feature | PASS |

---

## P0 Spot Check Summary

| Skill | Status | Evidence |
|---|---|---|
| `content-ops` | partial | `workflow-core`, `style-anchor`, and gates exist; caller mapping remains incomplete |
| `opencli-integration` | partial | web-search/topic-radar adapters exist; OpenCLI-specific adapter smoke absent |
| `account-config` | partial | `packages/config` exists with env/wechat config; caller reconciliation remains |
| `topic-radar` | verified | WeChat topic radar service/tests and agents roadmap completion evidence exist |
| `topic-inbox` | partial | hermes-db topic tools and WeChat topic service exist; Hermes entry smoke absent |
| `topic-scout` | partial | topic radar/web-search/storage paths exist; adoption-to-inbox smoke absent |
| `wechat-article-pipeline` | partial | WeChat workflow runtime, wechat-draft workflow, and hermes-db artifacts/articles exist; replacement route not documented |
| `wechat-writer` | partial | writer service and render/draft artifact builders exist; generation-to-draft smoke not captured |

---

## Architecture Drift Check

| Plan Boundary | Observed | Verdict |
|---|---|---|
| Markdown reconciliation table, no DB/script | `capability-reconciliation.md` is Markdown; no new scripts or data model added | PASS |
| One row per original skill | 44 source rows and 44 reconciliation rows | PASS |
| Execution owner separate from data/contract owner | Table has separate owner columns and boundary summary | PASS |
| No note or agents runtime edits | Only `specs/` artifacts in current repo changed | PASS |

---

## Remaining Risk

- `partial`, `absent`, and `needs-user-decision` rows are intentional downstream gates, not completion blockers for this reconciliation feature.
- No live smoke was executed. Smoke belongs to concrete migration/runtime features.
- Existing dirty files in external repos must remain treated as unrelated until the user confirms otherwise.
