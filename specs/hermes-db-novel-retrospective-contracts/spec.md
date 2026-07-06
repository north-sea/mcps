# Feature Specification: Hermes-DB Novel Retrospective Contracts

**Workspace**: `hermes-db-novel-retrospective-contracts`  
**Created**: 2026-07-07  
**Status**: Draft / Specify  
**Input**: `novel-runtime-contracts` identified missing server-side contracts required by agents `novel-agent-retrospective-handoff`.

## Goal

Implement hermes-db MCP durable contracts for novel retrospective state so agents can persist and query batch/volume retrospective reports, alerts, correction constraints, handoff packages, character states, and novel learning candidates.

## User Stories

### US1 - Persist retrospective reports and alerts

As novel-agent runtime, I need to create, list, retrieve, and review-status-update retrospective reports and their alerts so batch/volume quality checks survive process and session boundaries.

### US2 - Persist approved correction constraints

As chapter planning/production, I need approved correction constraints to be queryable by book/chapter/status so the next chapter input pack can consume them without relying on local JSON state.

### US3 - Persist handoff packages and character states

As the operator, I need the latest handoff package and character state snapshots to be retrievable before starting a new long-context writing session.

### US4 - Preserve runtime boundary

As maintainer, I need MCP tools to store/query state only, not generate reviews, prompts, or writing text.

## Requirements

- **FR-001**: Add schema/migrations for novel retrospective reports and report alerts.
- **FR-002**: Add schema/migrations for correction constraints with status transitions.
- **FR-003**: Add schema/migrations for handoff packages with latest-by-book query.
- **FR-004**: Add schema/migrations for character states keyed by book, character, and chapter/snapshot.
- **FR-005**: Add novel learning candidate persistence or a clearly compatible route into existing learning candidate infrastructure.
- **FR-006**: Expose MCP tools matching agents adapter expectations in `agents/packages/adapters/src/mcp/novel-retrospective-tools.ts`.
- **FR-007**: Add health/schema checks and focused tests.
- **FR-008**: Do not implement prompt generation, writing generation, model routing, or note skill deletion.

## Non-Goals

- No novel drafting or review generation in MCP.
- No platform publishing.
- No Library/Wiki import.
- No note skill archive/delete.
- No changes to agents automation interfaces unless needed for contract smoke tests.

## Acceptance

- Existing and new hermes-db tests pass for novel retrospective tools.
- Tool names and payload semantics match the agents adapter contract or the adapter/spec is explicitly updated in the same feature.
- Schema health reports retrospective readiness.
- A no-live-content smoke proves create/list/get/update flow on fixture data.
