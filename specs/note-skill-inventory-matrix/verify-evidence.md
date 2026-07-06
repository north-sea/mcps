# Verify Evidence: Note Skill Inventory Matrix

**Workspace**: `note-skill-inventory-matrix` | **Date**: 2026-06-28  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

---

## Verdict

**Result**: CONDITIONAL PASS

The matrix deliverable is complete enough to hand off to `agents-capability-reconciliation`: source skill count is 44, matrix row count is 44, deletion gates are non-empty, P0 rows keep candidate/reconciliation markers, and SDD active/roadmap state is consistent.

The condition is external to this feature: `/Users/yqg/learning/biji/note` already has dirty skill files. This feature did not edit that directory, but the current git status cannot prove a globally clean note source tree.

---

## Evidence Table

| Check | Command / Source | Observed Result | Verdict |
|---|---|---|---|
| Source skill count | `find /Users/yqg/learning/biji/note/.agents/skills /Users/yqg/learning/biji/note/.hermes/skills -name SKILL.md -type f \| wc -l` | `44` | PASS |
| Matrix row count | `awk` count between `## Matrix` and `## Count Check` in [migration-matrix.md](migration-matrix.md) | `44` | PASS |
| Deletion gates | `awk` check for empty deletion gate cells | `rows=44 empty_deletion_gate=0` | PASS |
| P0 spot check | `rg` for `account-config`, `content-ops`, `opencli-integration`, `topic-radar`, `topic-inbox`, `topic-scout`, `wechat-article-pipeline`, `wechat-writer` | All 8 P0 rows present with candidate landing zones and deletion gates | PASS |
| Candidate status discipline | `rg -n "needs reconciliation\|candidate" migration-matrix.md` | Candidate/reconciliation markers remain across unresolved landing-zone rows | PASS |
| Context manifest integrity | Required local file check over [context-manifest.md](context-manifest.md) | `missing_required=0` | PASS |
| SDD active feature | `cat specs/.active` | `note-skill-inventory-matrix` | PASS |
| Roadmap current feature | [roadmap.md](../note-skill-migration-roadmap/roadmap.md) | `Current Feature: note-skill-inventory-matrix` | PASS |
| Current repo SDD scope | `git status --short specs/.active specs/note-skill-migration-roadmap specs/note-skill-inventory-matrix` | Only SDD files for this feature are dirty/untracked in this scope | PASS |
| Note source worktree cleanliness | `git -C /Users/yqg/learning/biji/note status --short -- .agents/skills .hermes/skills` | Existing dirty files under `.agents/skills`; no evidence they were created by this feature | PARTIAL |

---

## P0 Spot Check Summary

| Skill | Evidence |
|---|---|
| `account-config` | Row present, P0, candidate `packages/config`, target `agents + mcp + thin-skill`, deletion gate requires replacement config loader and README pointer |
| `content-ops` | Row present, P0, candidate workflow/style packages, target `agents + mcp`, deletion gate requires shared replacement and caller reconciliation |
| `opencli-integration` | Row present, P0, candidate adapters package, target `agents + thin-skill`, deletion gate requires platform adapter smoke |
| `topic-radar` | Row present, P0, candidate topic specs and hermes-db tools, target `agents + mcp + thin-skill` |
| `topic-inbox` | Row present, P0, candidate topic workflow and hermes-db bucket, target `hermes-agent + mcp + thin-skill` |
| `topic-scout` | Row present, P0, candidate topic radar workflow, target `hermes-agent + agents + mcp` |
| `wechat-article-pipeline` | Row present, P0, candidate `apps/wechat-agent` and `packages/wechat-draft`, target `agents + mcp + thin-skill` |
| `wechat-writer` | Row present, P0, candidate `apps/wechat-agent`, target `agents + thin-skill`, model generation kept outside MCP |

---

## Boundary Evidence

This feature wrote only under `/Users/yqg/personal/AI/mcps/specs` plus `specs/.active`.

The note source tree is dirty before closeout evidence capture:

```text
 M .agents/skills/account-config/references/account-registry.md
 M .agents/skills/wechat-article-pipeline/SKILL.md
 M .agents/skills/wechat-image-generator/scripts/generate-image-manifest.py
 M .agents/skills/wechat-writer/SKILL.md
 M .agents/skills/youmind-publisher/scripts/extract-note.py
 M .agents/skills/youmind-publisher/scripts/publish-note-api.py
?? .agents/skills/wechat-article-pipeline/references/
```

This prevents a strict PASS on "note source tree clean". It does not block the matrix handoff because the matrix count and rows still match the source skill inventory.

---

## Remaining Risk

- Existing dirty files in `/Users/yqg/learning/biji/note` should be treated as unrelated work until the user confirms otherwise.
- `agents 既有落点` and `mcps 既有落点` remain candidates, not verified facts.
- No note skill should be deleted, moved, or archived until later features attach replacement path and smoke evidence.
