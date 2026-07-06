# Fallback Policy: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01

---

## Goal

Memory 写入失败不能阻塞 Hermes 主流程，也不能导致重复写入污染 nmem。

---

## Timeout Handling

```text
attempt memory write
  -> success: continue
  -> timeout/unknown: do not retry blindly
      -> search/show by dedupe key or title if possible
      -> if found: mark confirmed-saved
      -> if not found: continue main workflow
      -> optional: write fallback record
```

---

## Known Failure Modes

| Failure | Handling |
|---|---|
| MCP tool timeout but write may have landed | Search first; do not repeat immediately |
| NAS remote API PATCH timeout | Treat as unknown; check server logs or search |
| Docker network write timeout but loopback ok | Prefer Hermes container/network-local path if proven; otherwise fail open |
| Mac local nmem degraded/database disconnected | Do not use as required write path; after recovery, still keep NAS write disabled for local agents |
| FTS/search degraded | Allow workflow continuation; record degraded status |

---

## Fallback Record

If enabled, fallback records must be:

- short
- deduplicated
- redacted
- temporary
- reviewed or expired

Minimum fields:

```text
dedupe_key
source_agent
attempted_endpoint
operation
summary
status
created_at
```

---

## Hard Rules

- Never block Hermes publication/topic/runtime workflow solely because nmem write failed.
- Never write secrets into fallback logs.
- Never retry add/update in a tight loop.
- Never assume timeout means failure; confirm first where possible.
