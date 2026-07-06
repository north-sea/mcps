# Feature Specification: XHS Workflow Definition

**Workspace**: `xhs-workflow-definition`  
**Created**: 2026-07-07  
**Status**: Draft / Ideate-Specify  
**Input**: note skill roadmap has one XHS skill, `xhs-creator`, while `agents/apps/xhs-agent` is currently only a skeleton.

## Goal

Decide whether 小红书/XHS should remain a formal business workflow. If yes, define the minimum agents/MCP/Library contract for XHS creation. If no, mark the note skill for thin route/archive handling.

## User Stories

### US1 - Decide whether XHS stays in scope

As maintainer, I need an explicit keep/pause/archive decision before investing in XHS implementation.

### US2 - Avoid assuming a skeleton app is production-ready

As implementer, I need the roadmap to reflect that `apps/xhs-agent` is a placeholder until workflow, tests, and platform rules are defined.

### US3 - Keep platform rules in Library

As operator, I need XHS platform rules, examples, and source materials to route to Library/Wiki, not Memory.

## Requirements

- **FR-001**: Confirm keep/pause/archive status for `xhs-creator`.
- **FR-002**: If kept, define minimum workflow: topic/brief, copy, image/card, tags, review, publish handoff.
- **FR-003**: Define agents vs MCP vs Library vs Memory ownership.
- **FR-004**: Identify compliance and platform side-effect gates.
- **FR-005**: Do not publish to XHS or perform external writes.

## Non-Goals

- No XHS posting.
- No scraping/login automation.
- No image generation implementation.
- No note skill deletion.

## Acceptance

- XHS status is no longer ambiguous.
- If kept, next implementable feature is scoped.
- If paused/archive, deletion remains blocked until note archive feature has route evidence.
