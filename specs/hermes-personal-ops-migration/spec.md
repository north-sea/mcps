# Feature Specification: Hermes Personal Ops Migration

**Workspace**: `hermes-personal-ops-migration`  
**Created**: 2026-07-07  
**Status**: Draft / Specify  
**Input**: note-skill migration roadmap lists personal ops skills that should move out of note active skill registry.

## Goal

Decide and define replacement routes for personal operations skills currently living in note/Hermes skills: `daily-capture`, `goal-setting`, `link-inbox`, `media-download`, `nas-ops`, and `period-digest`.

The feature should identify which work belongs to Hermes/NAS runtime, which needs an MCP/storage contract, which is too high-side-effect to automate, and which should remain a thin skill route.

## User Stories

### US1 - Classify personal ops ownership

As maintainer, I need each personal ops skill to have an owner and route so note stops acting as an active runtime registry.

### US2 - Protect high-side-effect operations

As operator, I need media download, NAS ops, external writes, and link inbox actions to require smoke tests or explicit confirmation before automation.

### US3 - Keep Memory compact

As knowledge-base user, I need Memory to store decisions/summaries/procedures, not raw links, media, or full daily logs.

## Requirements

- **FR-001**: Produce owner table for all 6 personal ops skills.
- **FR-002**: Separate Hermes/NAS runtime work from MCP/storage contracts.
- **FR-003**: Identify required smoke tests and confirmation gates for external side effects.
- **FR-004**: Define Memory/Library handling for links, daily logs, goals, and period summaries.
- **FR-005**: Recommend next implementable personal ops feature or mark rows as user-decision gated.
- **FR-006**: Do not execute downloads, NAS mutations, external writes, or note skill deletion.

## Non-Goals

- No live NAS changes.
- No media download implementation.
- No Karakeep or external write smoke without explicit approval.
- No note skill deletion/archive.

## Acceptance

- All 6 personal ops skills have owner, route, gate, and deletion status.
- High-side-effect rows are not marked deletion-ready without smoke evidence.
- Roadmap next step is explicit: implement a storage contract, create thin routes, or pause for user decision.
