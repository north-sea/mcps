# Feature Specification: Note Thin Shell And Archive

**Workspace**: `note-thin-shell-and-archive`  
**Created**: 2026-07-07  
**Status**: Draft / Specify  
**Input**: all upstream note skill migration roadmap waves now have owner, route, or gate decisions.

## Goal

Safely shrink note from active skill registry toward thin route docs, README pointers, archive markers, or explicit deletion decisions, without deleting anything whose replacement route and smoke evidence are incomplete.

## Requirements

- **FR-001**: Reconcile all 44 original note skills against latest upstream acceptance/gate records.
- **FR-002**: Mark each skill as `thin-route-ready`, `archive-ready`, `delete-ready`, `user-decision-gated`, or `blocked`.
- **FR-003**: Do not delete or move any note skill without replacement path, smoke evidence, and explicit approval.
- **FR-004**: Produce final archive/delete plan with included/excluded/needs-decision rows.
- **FR-005**: Keep model generation/runtime out of MCP and raw source material out of Memory.

## Non-Goals

- No automatic note deletion.
- No live external writes.
- No hidden archive operation.
- No git commit unless explicitly requested.

## Acceptance

- All 44 note skills have final disposition and gate evidence.
- Any ready action is written as a plan, not executed.
- Remaining blockers/user decisions are explicit.
