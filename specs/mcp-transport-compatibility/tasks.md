# Tasks: MCP Transport Compatibility

**Workspace**: `mcp-transport-compatibility` | **Date**: 2026-05-28
**Input**: `specs/mcp-transport-compatibility/spec.md` + `plan.md`
**Prerequisites**: spec.md, plan.md

---

## Execution Principles

- Keep changes scoped to HTTP transport compatibility, diagnostics, tests, and docs.
- Do not alter MCP tool names, schemas, repository behavior, DB schema, Redis behavior, or embedding calls.
- Complete tasks in dependency order; middleware behavior must be tested before final docs/verification closeout.

---

## Phase 1: Transport Guard

**Goal**: Make HTTP auth and error responses deterministic and diagnosable.

- [x] T001 [US1/US4] Extend `BearerAuthMiddleware` into a guarded ASGI wrapper.
  - scope: `packages/hermes-db/src/hermes_db_mcp/middleware.py`
  - maps_to: FR-003, FR-004, US1-3, US1-4, US4-1, ADR-002
  - verify: focused ASGI tests prove 401 JSON, exception fallback JSON, and empty error body fallback

- [x] T002 [US2] Preserve pass-through behavior for authorized requests.
  - scope: `packages/hermes-db/src/hermes_db_mcp/middleware.py`, existing tool modules untouched
  - maps_to: FR-002, FR-005, US2-1, US2-2
  - verify: pass-through ASGI test plus diff review confirms no tool contract edits

## Phase 2: Verification Coverage

**Goal**: Cover the compatibility layer without requiring live PG/Redis.

- [x] T003 [US1/US4] Add middleware tests using minimal ASGI apps.
  - scope: `packages/hermes-db/tests/test_middleware.py`
  - maps_to: FR-007, diagnosability quality target
  - verify: `pytest packages/hermes-db/tests/test_middleware.py`

- [x] T004 [US2] Run existing hermes-db test suite.
  - scope: `packages/hermes-db/tests`
  - maps_to: FR-005, contract stability quality target
  - verify: `pytest packages/hermes-db/tests`

## Phase 3: Client Documentation

**Goal**: Document Codex and Claude Code Streamable HTTP config clearly.

- [x] T005 [US3/US4] Update README client configuration examples.
  - scope: `packages/hermes-db/README.md`
  - maps_to: FR-006, FR-008, US3-1, US3-2, US4-2
  - verify: README includes Codex `http_headers`/`bearer_token_env_var`, Claude Code `headers`, and `TRANSPORT=streamable-http`

## Phase 4: SDD Closeout Prep

**Goal**: Prepare evidence for verify/closeout.

- [x] T006 [Verify] Record implementation evidence and residual live-test gap.
  - scope: `specs/mcp-transport-compatibility/tasks.md`, optional `acceptance.md` after verification
  - maps_to: SDD verify readiness
  - verify: task statuses updated and command results summarized

---

## Dependencies and Order

- T001 must happen before T003.
- T002 is validated alongside T001/T003 and by diff review.
- T005 can happen after middleware behavior is stable.
- T004 and T006 close the implementation loop.

---

## Coverage Check

| Scenario / Requirement | Task |
|------------------------|------|
| Codex receives valid HTTP diagnostics | T001, T003 |
| Claude Code remains compatible | T002, T004 |
| Client config documented | T005 |
| Operators can diagnose failures | T001, T003, T005 |
| Existing tool contracts unchanged | T002, T004 |

| Architecture / Quality Target | Implementation Task | Verification Task |
|-------------------------------|---------------------|-------------------|
| ADR-001 Keep FastMCP transport | T002 | T004, diff review |
| ADR-002 Normalize failures in middleware | T001 | T003 |
| Security | T001 | T003 |
| Diagnosability | T001 | T003 |

---

## Stage Readiness

- Recommended next step: `implement`.
- Blockers: None for local implementation. Live client validation depends on a deployed endpoint and configured token.
