# Tasks: Hermes-DB Novel Retrospective Contracts

**Workspace**: `hermes-db-novel-retrospective-contracts` | **Date**: 2026-07-07  
**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md)

---

## Phase 1: Schema Slice

- [x] T001 [schema] Add migration `0009_novel_retrospective_contracts.py`
  - slice: retrospective schema
  - blocked_by: none
  - verify: migration creates reports, alerts, constraints, handoff packages, character states, and novel learning candidates with checks/indexes.

- [x] T002 [schema] Add schema inspector for `novel_retrospective_contracts`
  - slice: health/schema
  - blocked_by: T001
  - verify: inspector checks required columns, constraints, and indexes.

- [x] T003 [schema] Wire global `health` capability key
  - slice: health/schema
  - blocked_by: T002
  - verify: `health` result includes `novel_retrospective_contracts`.

## Phase 2: Repository Slice

- [x] T004 [repo] Implement report and alert repository functions
  - slice: reports/alerts
  - blocked_by: T001
  - verify: create/get/list/update report and create/list alerts over fixture rows.

- [x] T005 [repo] Implement correction constraint repository functions
  - slice: correction constraints
  - blocked_by: T001
  - verify: create/get/list/update status supports `book_slug` and `status` filters.

- [x] T006 [repo] Implement handoff package repository functions
  - slice: handoff packages
  - blocked_by: T001
  - verify: create/get/latest-by-book returns newest package.

- [x] T007 [repo] Implement character state repository functions
  - slice: character states
  - blocked_by: T001
  - verify: upsert/get/list handles `(book_slug, character_name, last_chapter)`.

- [x] T008 [repo] Implement novel learning candidate repository functions
  - slice: learning candidates
  - blocked_by: T001
  - verify: create/list by source report preserves status/confidence/evidence fields.

## Phase 3: MCP Tool Slice

- [x] T009 [tools] Add `tools/novel_retrospective.py` report and alert tools
  - slice: reports/alerts
  - blocked_by: T004
  - verify: tool names match agents adapter and validation returns structured errors.

- [x] T010 [tools] Add correction constraint tools
  - slice: correction constraints
  - blocked_by: T005
  - verify: create/get/list/update status tool tests pass.

- [x] T011 [tools] Add handoff package tools
  - slice: handoff packages
  - blocked_by: T006
  - verify: create/get/latest tool tests pass.

- [x] T012 [tools] Add character state tools
  - slice: character states
  - blocked_by: T007
  - verify: upsert/get/list tool tests pass.

- [x] T013 [tools] Add learning candidate and health tools
  - slice: learning/health
  - blocked_by: T002, T008
  - verify: create/list candidate and `health_novel_retrospective` tool tests pass.

## Phase 4: Verification And Closeout

- [x] T014 [tests] Add migration/schema/repository tests
  - slice: verification
  - blocked_by: T001-T008
  - verify: focused pytest for schema and repo passes.

- [x] T015 [tests] Add MCP tool validation tests
  - slice: verification
  - blocked_by: T009-T013
  - verify: focused pytest for tool validation/response shape passes.

- [x] T016 [adapter-smoke] Add or record cross-repo adapter smoke
  - slice: contract smoke
  - blocked_by: T009-T015
  - verify: agents adapter expected tool names and server tool names are reconciled; no live novel content write.

- [x] T017 [verify] Record verify evidence
  - slice: closeout evidence
  - blocked_by: T014-T016
  - verify: `verify-evidence.md` includes commands, row counts, health result, and no-runtime-boundary check.

- [x] T018 [roadmap] Update roadmap next recommendation
  - slice: roadmap
  - blocked_by: T017
  - verify: current feature marked done/conditional and next feature selected.

- [x] T019 [acceptance] Close out with acceptance record
  - slice: closeout
  - blocked_by: T017, T018
  - verify: `acceptance.md` records FR-001 through FR-008 verdicts and deferred live actions.

## Stage Readiness

- Recommended next stage: `execute-plan`.
- Context manifest: required because implementation spans migration, repository, MCP tools, health, tests, and cross-repo adapter contract.
