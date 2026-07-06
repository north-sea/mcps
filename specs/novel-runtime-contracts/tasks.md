# Tasks: Novel Runtime Contracts

**Workspace**: `novel-runtime-contracts` | **Date**: 2026-07-07  
**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md)

---

## Phase 1: Current-State Reconciliation

- [x] T001 [reconcile] Build agents novel spec state table
  - slice: current-state table
  - scope: `capability-reconciliation.md`
  - blocked_by: none
  - verify: every `agents/specs/novel-agent-*` feature has roadmap status, task state, acceptance state, and classification.

- [x] T002 [reconcile] Resolve stale tasks versus accepted features
  - slice: current-state table
  - scope: `capability-reconciliation.md`
  - blocked_by: T001
  - verify: accepted features with unchecked tasks are marked `stale-task-state` or justified as `done`.

- [x] T003 [reconcile] Narrow note novel skills into novel-specific rows
  - slice: note-to-runtime route
  - scope: `capability-reconciliation.md`
  - blocked_by: none
  - verify: novel rows from `agents-capability-reconciliation` are present with route/gate fields.

## Phase 2: Owner And Contract Boundaries

- [x] T004 [owner] Produce runtime/contract/Library/Memory owner table
  - slice: owner table
  - scope: `owner-table.md`
  - blocked_by: T001, T003
  - verify: analysis, style profile, book planning, chapter production, retrospective/handoff, automation interface, trend scout, platform rules, and capture each have owner rows.

- [x] T005 [gap] Produce contract gap register
  - slice: contract gap register
  - scope: `contract-gap-register.md`
  - blocked_by: T004
  - verify: agents runtime gaps and mcps/hermes-db contract gaps are separate rows.

- [x] T006 [gap] Confirm MCP does not own writing runtime
  - slice: contract gap register
  - scope: `owner-table.md`, `contract-gap-register.md`
  - blocked_by: T004
  - verify: no row assigns prompt/model routing/writing/review generation to MCP.

## Phase 3: Replacement Routes And Gates

- [x] T007 [route] Produce novel note skill replacement routes
  - slice: note replacement gates
  - scope: `replacement-routes.md`
  - blocked_by: T003, T004
  - verify: all novel note skills have replacement target, gate, and `deletion_allowed=false`.

- [x] T008 [route] Define Library/Wiki route for platform rules and source samples
  - slice: Library route
  - scope: `replacement-routes.md`, `owner-table.md`
  - blocked_by: T004
  - verify: `novel-platform-rules`, `novel-rules-ask`, trend/source samples are routed to Library/Wiki, not Memory.

- [x] T009 [route] Define Memory route for compact decisions only
  - slice: Memory route
  - scope: `owner-table.md`
  - blocked_by: T004
  - verify: no raw novel/source/sample material is assigned to Memory.

## Phase 4: Verification And Roadmap

- [x] T010 [verify] Record table/count and side-effect evidence
  - slice: verification
  - scope: `verify-evidence.md`
  - blocked_by: T001-T009
  - verify: row counts, empty critical column checks, and no-live-write/no-delete evidence recorded.

- [x] T011 [roadmap] Recommend next implementable feature
  - slice: roadmap update
  - scope: `../note-skill-migration-roadmap/roadmap.md`
  - blocked_by: T005, T010
  - verify: roadmap current/next reflects whether to implement mcps retrospective contracts, continue agents retrospective CLI, or move to xhs/personal ops.

- [x] T012 [acceptance] Close out with acceptance record
  - slice: closeout
  - scope: `acceptance.md`
  - blocked_by: T010, T011
  - verify: FR-001 through FR-006 have PASS/PARTIAL verdicts and deferred live actions are explicit.

## Stage Readiness

- Recommended next stage: `execute-plan`.
- Context manifest: required because this feature consumes cross-repo spec/code evidence and gates downstream note skill deletion.
