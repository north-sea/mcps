# Feature Specification: Novel Runtime Contracts

**Workspace**: `novel-runtime-contracts`  
**Created**: 2026-07-06  
**Status**: Draft / Specify  
**Input**: note skill roadmap has closed content runtime contracts and now needs to reconcile novel note skills with existing `agents/apps/novel-agent`, `agents/specs/novel-agent-*`, and hermes-db novel contracts.

## Goal

Define the boundary between novel generation runtime and durable contracts:

- agents owns analysis, planning, chapter production, retrospective/handoff, and model orchestration.
- mcps/hermes-db owns durable book/chapter/style/profile/run state and MCP access.
- Library/Wiki owns source materials, platform rules, writing samples, and long reference documents.
- Memory owns compact decisions/procedures only.

This feature must first reconcile the status contradictions in existing agents novel specs before adding new implementation.

## User Stories

### US1 - Reconcile existing novel-agent feature state

As the maintainer, I need a current-state table for novel-agent specs so roadmap decisions do not treat stale unchecked tasks or stale acceptance files as truth.

Acceptance:

- Each novel-related agents spec is classified as `done`, `stale-task-state`, `in-progress`, `blocked`, or `backlog`.
- Contradictions such as accepted feature with unchecked tasks are explicitly resolved or gated.

### US2 - Define runtime vs contract ownership

As an implementer, I need to know whether each novel workflow capability belongs in agents, mcps/hermes-db, Library, or Memory.

Acceptance:

- Analysis, style profile, book planning, chapter production, retrospective/handoff, automation interface, and platform rules have owners.
- MCP contract gaps are listed separately from agents runtime gaps.

### US3 - Preserve writing generation outside MCP

As the operator, I need MCP tools to store and retrieve state, not hard-code novel writing prompts or model selection.

Acceptance:

- Writing generation, review, style injection, and model routing stay in agents/Hermes/Codex.
- mcps only exposes durable contracts and retrieval/update tools.

## Requirements

- **FR-001**: Produce a novel capability reconciliation table.
- **FR-002**: Identify stale agents task files versus real unfinished work.
- **FR-003**: Identify hermes-db/MCP contract gaps for novel workflows.
- **FR-004**: Define Library/Memory handling for novel sources, rules, and writing samples.
- **FR-005**: Recommend the next implementable novel feature or closeout action.
- **FR-006**: Do not modify live novel content, publish externally, or delete note skills.

## Non-Goals

- No new novel generation feature in this specify step.
- No live platform publishing.
- No note skill deletion.
- No MCP prompt/runtime generation logic.

## Next Stage

Plan: inspect agents novel specs/tasks/acceptance and mcps hermes-db novel tools, then create reconciliation artifacts and tasks.
