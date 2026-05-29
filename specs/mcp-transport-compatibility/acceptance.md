# Acceptance: MCP Transport Compatibility

**Workspace**: `mcp-transport-compatibility` | **Date**: 2026-05-28

---

## Implementation Summary

- Extended `BearerAuthMiddleware` so HTTP requests go through a diagnostic ASGI wrapper.
- Preserved strict bearer token authentication when `API_TOKEN` is configured.
- Added fallback JSON responses for exceptions before response start and empty error responses.
- Added a content-type fallback for error responses that already contain body bytes but omit `Content-Type`.
- Documented Streamable HTTP config differences for Codex and Claude Code.

---

## Verification Evidence

| Check | Result | Evidence |
|-------|--------|----------|
| Middleware auth and diagnostics | Pass | `uv run pytest tests/test_middleware.py -q` -> 6 passed |
| Existing hermes-db unit suite | Pass | `uv run pytest tests -q` -> 26 passed |
| Tool contract scope | Pass | No tool, repository, service, or DB schema files changed |
| Client config docs | Pass | README includes Codex `http_headers` / `bearer_token_env_var`, Claude Code `headers`, and `/mcp` Streamable HTTP examples |

---

## Acceptance Mapping

| Requirement / Scenario | Status | Notes |
|------------------------|--------|-------|
| US1 Codex can receive valid HTTP diagnostics on `/mcp` | Partially accepted | Local middleware coverage prevents missing content type/empty body on error paths. Live Codex initialize still needs deployed endpoint validation. |
| US2 Claude Code remains compatible | Accepted locally | Successful pass-through test and full existing suite; no tool contract changes. Live Claude Code startup still needs deployed endpoint validation. |
| US3 Client-specific config documented | Accepted | README distinguishes Codex and Claude Code config fields. |
| US4 Operators can diagnose failures | Accepted locally | 401, empty error response, missing content type, and pre-start exception paths covered by tests. |

---

## Residual Follow-up

- Run live Codex startup against the deployed `TRANSPORT=streamable-http` service with a real bearer token.
- Run live Claude Code startup against the same endpoint before retiring any old SSE configuration.
