# Tasks: XHS Workflow Definition

**Workspace**: `xhs-workflow-definition` | **Date**: 2026-07-07  
**Input**: [spec.md](spec.md), [plan.md](plan.md)

---

- [x] T001 [evidence] Confirm XHS app status
  - slice: current-state
  - verify: `agents/apps/xhs-agent/src/index.ts` is classified as placeholder/skeleton, not production runtime.

- [x] T002 [decision] Record keep/pause/archive decision
  - slice: decision
  - verify: `decision-record.md` marks XHS as paused/user-decision gated.

- [x] T003 [owner] Define ownership if XHS is resumed
  - slice: owner boundary
  - verify: agents/MCP/Library/Memory boundaries are recorded.

- [x] T004 [gate] Define compliance and side-effect gates
  - slice: risk gates
  - verify: no publish/scrape/login/external write can happen without explicit approval/smoke.

- [x] T005 [verify] Record no-side-effect evidence
  - slice: verification
  - verify: `verify-evidence.md` records no XHS external write and no note deletion.

- [x] T006 [roadmap] Advance roadmap to final archive gate
  - slice: roadmap
  - verify: `note-skill-migration-roadmap` moves current/next to `note-thin-shell-and-archive`.

- [x] T007 [acceptance] Close out with acceptance record
  - slice: closeout
  - verify: `acceptance.md` records PASS WITH USER DECISION GATE.
