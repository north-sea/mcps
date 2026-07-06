# Context Manifest: Note Skill Inventory Matrix

**Workspace**: `note-skill-inventory-matrix`
**Created**: 2026-06-27
**Status**: active

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/note-skill-inventory-matrix/spec.md` | Defines scope, user stories, traits, out-of-scope boundaries, and count requirements. | implement | yes |
| `specs/note-skill-inventory-matrix/plan.md` | Defines Markdown matrix design, ADRs, Producer-Consumer Matrix, and verification strategy. | implement | yes |
| `specs/note-skill-inventory-matrix/tasks.md` | Defines executable task order, dependencies, and verification tasks. | implement | yes |
| `specs/note-skill-inventory-matrix/migration-matrix.md` | Core artifact to validate and hand off to later roadmap features. | implement | yes |
| `specs/note-skill-migration-roadmap/roadmap.md` | Defines umbrella invariants, current feature, next feature, and migration boundaries. | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/note-skill-inventory-matrix/spec.md` | Verify P0/P1 requirements, out-of-scope boundaries, and feature traits. | verify | yes |
| `specs/note-skill-inventory-matrix/plan.md` | Check ADRs, Producer-Consumer Matrix, no-data-model decision, and verification strategy. | verify | yes |
| `specs/note-skill-inventory-matrix/tasks.md` | Check task completion status and coverage. | verify | yes |
| `specs/note-skill-inventory-matrix/migration-matrix.md` | Verify 44 row matrix, P0 spot checks, candidate status, and deletion gates. | verify | yes |
| `specs/note-skill-migration-roadmap/roadmap.md` | Verify roadmap current feature, completion log, and next recommendation. | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `/Users/yqg/learning/biji/note/.agents/skills` | Source directory for 33 agent-facing note skills. | plan / implement / verify | yes |
| `/Users/yqg/learning/biji/note/.hermes/skills` | Source directory for 11 Hermes-facing note skills. | plan / implement / verify | yes |
| `/Users/yqg/personal/AI/agents` | Candidate execution-layer repository referenced by roadmap; only candidate signals are used in this feature. | plan / verify | no |
| `/Users/yqg/personal/AI/mcps/packages` | Candidate MCP/data-contract repository paths referenced by matrix; only candidate signals are used in this feature. | plan / verify | no |

---

## Rules

- This manifest does not authorize edits to `/Users/yqg/learning/biji/note`.
- Candidate landing zones remain unverified until `agents-capability-reconciliation`.
- Verification must use fresh evidence; existing task checkmarks are not enough for closeout.
