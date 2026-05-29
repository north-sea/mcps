# Implementation Plan: MCP Transport Compatibility

**Workspace**: `mcp-transport-compatibility` | **Date**: 2026-05-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/mcp-transport-compatibility/spec.md`

---

## Summary

Make `packages/hermes-db` safer for Codex and Claude Code Streamable HTTP clients by keeping the MCP SDK as the protocol owner while adding a narrow ASGI compatibility layer for auth and diagnostic error responses.

---

## Architecture Overview

The current service builds a `FastMCP` app in `server.py` and wraps the HTTP/SSE ASGI app with `BearerAuthMiddleware`. This feature keeps that shape and extends the wrapper into a transport guard:

```text
Client -> BearerAuthMiddleware -> FastMCP streamable_http_app/sse_app -> tools
             |                         |
             |                         +-- MCP protocol handling stays in SDK
             +-- auth + structured error response fallback
```

No tool registration, database access, Redis cache, embedding call, or domain repository behavior changes.

---

## Quality Attribute Targets

| Attribute | Target | Design impact | Verification |
|-----------|--------|---------------|--------------|
| Compatibility | Codex and Claude Code can both receive valid HTTP responses during startup | Do not replace the MCP SDK transport; only wrap failures | ASGI tests for auth, missing path, and exception fallback |
| Diagnosability | HTTP failures include status, content type, and short body | Add response send inspection/fallback in middleware | Tests assert body and `content-type` |
| Security | Bearer token behavior remains strict | Keep exact `Authorization: Bearer <token>` check | Tests for missing/wrong token |
| Contract stability | Existing tool names and payloads unchanged | Avoid tool modules and repository logic | Scope review + existing tests |

---

## Lightweight ADR

| Decision | Background | Candidates | Conclusion | Cost | Source |
|----------|------------|------------|------------|------|--------|
| ADR-001 Keep FastMCP transport | Codex failure points to HTTP response shape, not tool logic | A: wrap FastMCP app; B: reimplement `/mcp`; C: move fix to ccswitch | Choose A to preserve SDK behavior and minimize blast radius | Some SDK edge cases may still need future follow-up | UNVERIFIED |
| ADR-002 Normalize failures in middleware | Existing auth middleware is the only HTTP boundary owned by this service | A: expand middleware; B: add Starlette exception handlers around mounted app | Choose A because it applies equally to streamable HTTP and SSE wrappers | Middleware needs careful ASGI send handling | UNVERIFIED |

---

## Module Design

### Module: `hermes_db_mcp.middleware`

**Responsibilities**: authenticate HTTP requests when `API_TOKEN` is configured and ensure error responses are diagnosable.

**Changes**:

- Keep successful authorized requests flowing to the wrapped app.
- Return JSON `401` for missing or invalid bearer token.
- Catch exceptions from the wrapped ASGI app and return JSON `500` without leaking internals.
- Inspect completed HTTP responses; when status is an error and the app emitted no body, append a short body and content type where possible.

**Important behavior**:

```text
if token required and Authorization mismatch:
    return 401 application/json {"error":"unauthorized"}
else:
    call wrapped app through guarded send
    if wrapped app raises:
        return 500 application/json {"error":"internal_server_error"}
    if error status had no body/content-type:
        provide short diagnostic fallback
```

### Module: `hermes_db_mcp.server`

**Responsibilities**: choose transport and wrap the SDK app.

**Changes**:

- Keep the existing `streamable-http` and `sse` branching.
- No tool or context changes.
- Normalize README language to make `streamable-http` the recommended HTTP transport.

### Module: `packages/hermes-db/README.md`

**Responsibilities**: document client-specific configuration.

**Changes**:

- Add Codex Streamable HTTP example using `http_headers` or `bearer_token_env_var`.
- Add Claude Code Streamable HTTP example using `headers`.
- Clarify SSE is legacy/optional unless explicitly configured.

---

## Project Structure

```text
packages/hermes-db/src/hermes_db_mcp/middleware.py   # compatibility/auth wrapper
packages/hermes-db/src/hermes_db_mcp/server.py       # transport assembly, unchanged unless needed
packages/hermes-db/tests/test_middleware.py          # new focused ASGI tests
packages/hermes-db/README.md                         # client config docs
```

---

## Risks and Tradeoffs

- Middleware-level response repair cannot change a semantically invalid MCP response into a valid MCP protocol exchange; it only prevents missing-content-type/empty-body diagnostics from hiding the real issue.
- ASGI response inspection must not double-send response start/body events. Tests should cover pass-through, auth rejection, exception fallback, and empty error body fallback.
- Since official Codex/Claude Code client internals are not vendored here, local verification uses protocol-shaped HTTP probes and focused ASGI tests.

---

## Verification Strategy

1. Run existing unit tests for `packages/hermes-db`.
2. Add targeted middleware tests for auth and diagnostic response behavior.
3. Run lint or import checks if available.
4. Review diff to confirm no MCP tool contract changed.

---

## Stage Readiness

- Need `data-model.md`: No. This feature changes HTTP transport behavior only; no entities, storage, state, or relationships change.
- Next step: `tasks`.
- Blockers: None for task breakdown. Full live Codex/Claude verification may require deployed service and real token after local implementation.

---

## Design Artifacts

| Artifact | Needed | Notes |
|----------|--------|-------|
| plan.md | Yes | Main implementation plan |
| data-model.md | No | No data model changes |
| tasks.md | Yes | Next stage output |
| acceptance.md | Later | Capture final verification evidence |

---

## Sources

| Decision | Source URL | Notes |
|----------|------------|-------|
| ADR-001 | UNVERIFIED | Based on current repository code and MCP SDK usage |
| ADR-002 | UNVERIFIED | Based on current ASGI middleware boundary |
