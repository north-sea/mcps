# Implementation Plan: XHS Workflow Definition

**Workspace**: `xhs-workflow-definition` | **Date**: 2026-07-07 | **Spec**: [spec.md](spec.md)

## Summary

Current evidence does not justify implementing XHS as a formal workflow. `agents/apps/xhs-agent` is a placeholder with a simple staged workflow and no domain tests, no platform contract, no publish handoff, no Library rules route, and no user-confirmed business priority.

Decision for this roadmap slice: **pause XHS as a formal workflow and keep `xhs-creator` deletion-blocked**. This completes definition work without pretending the skeleton app can replace the note skill.

## Evidence

| Source | Evidence | Interpretation |
|---|---|---|
| `agents/apps/xhs-agent/src/index.ts` | simple `topic-selection -> drafting -> image-prep -> publishing -> done` placeholder | Not a production workflow. |
| `mcps/specs/agents-capability-reconciliation/spec.md` | says skeleton must keep user confirmation / minimum workflow gate | Cannot mark verified. |
| `mcps/specs/note-skill-inventory-matrix/migration-matrix.md` | `xhs-creator` status: candidate skeleton, needs reconciliation, user confirmation | Deletion is blocked. |

## Decision

| Option | Decision | Reason |
|---|---|---|
| Keep and implement now | rejected | No explicit user/business confirmation and no platform rules/smoke. |
| Pause with user-decision gate | selected | Safest and most honest current state. |
| Archive/delete note skill now | rejected | No replacement route or smoke evidence. |

## Ownership If Resumed Later

| Capability | Owner |
|---|---|
| topic/brief/copy/image/tag/review workflow | `agents/apps/xhs-agent` |
| stable state contracts | MCP only after concrete workflow/data needs exist |
| platform rules/examples/source material | Library/Wiki |
| compact decisions/procedures | Memory |
| posting/publishing | manual/live-gated external side-effect |

## Verification Strategy

- Confirm XHS row exists and is marked user-decision gated.
- Confirm no XHS publishing, scraping, login automation, external write, or note deletion.
- Confirm roadmap advances to final `note-thin-shell-and-archive` gate.
