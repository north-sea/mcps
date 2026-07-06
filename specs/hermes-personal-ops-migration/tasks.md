# Tasks: Hermes Personal Ops Migration

**Workspace**: `hermes-personal-ops-migration` | **Date**: 2026-07-07  
**Input**: [spec.md](spec.md), [plan.md](plan.md)

---

## Phase 1: Reconciliation

- [x] T001 [owner] Produce owner table for all 6 personal ops skills
  - slice: owner table
  - blocked_by: none
  - verify: daily-capture, goal-setting, link-inbox, media-download, nas-ops, period-digest all present.

- [x] T002 [boundary] Separate Hermes/NAS runtime from MCP/storage contracts
  - slice: owner table
  - blocked_by: T001
  - verify: runtime/action rows are not assigned directly to MCP.

- [x] T003 [memory] Define Memory/Library/Karakeep/filesystem routes
  - slice: owner table
  - blocked_by: T001
  - verify: no raw links/media/daily logs route to Memory.

## Phase 2: Replacement Routes And Risk Gates

- [x] T004 [route] Produce replacement routes
  - slice: route table
  - blocked_by: T001-T003
  - verify: all 6 skills have target, thin entry, gate, and deletion status.

- [x] T005 [risk] Produce high-side-effect gate table
  - slice: risk gates
  - blocked_by: T004
  - verify: NAS mutations, media downloads, external writes, and schedulers require explicit approval/smoke.

- [x] T006 [safety] Confirm no side-effect execution or note deletion
  - slice: safety
  - blocked_by: T004-T005
  - verify: acceptance records docs-only closeout and deletion_allowed=false.

## Phase 3: Verification And Closeout

- [x] T007 [verify] Record row/count and no-side-effect evidence
  - slice: verification
  - blocked_by: T001-T006
  - verify: `verify-evidence.md` records coverage counts and safety checks.

- [x] T008 [roadmap] Recommend next feature
  - slice: roadmap
  - blocked_by: T007
  - verify: roadmap advances to `xhs-workflow-definition` because personal ops is gated/closed and XHS is the remaining domain-definition feature.

- [x] T009 [acceptance] Close out with acceptance record
  - slice: closeout
  - blocked_by: T007-T008
  - verify: `acceptance.md` records FR-001 through FR-006 verdicts and gates.

## Stage Readiness

- Status: closed for this reconciliation slice.
- Implementation features remain gated by user approval/smoke decisions.
