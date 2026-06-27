# Plan: WeChat Draft Ops CRUD

**Workspace**: `wechat-draft-ops-crud`
**Date**: 2026-06-27
**Spec**: [spec.md](spec.md)

## Scope Decision

Implement only the read-only remote draft list slice in this feature. Update/delete remain designed but deferred because adapter endpoints, destructive annotations, and operator confirmation are not yet implemented.

## Architecture

| Layer | Change |
|---|---|
| Schema | Add `ListDraftsInputSchema` / `ListDraftsOutputSchema`. |
| Adapter client | Add `batchGetDrafts(account, { offset, count, no_content })`. |
| Service | Add `listDrafts(input)` that resolves account, checks `draft_batchget`, calls adapter, normalizes summaries, and bounds content by default. |
| MCP | Register `wechat_list_drafts` as read-only. |
| Tests | Service fake adapter test + HTTP MCP smoke discovery. |

## Data Flow

```text
wechat_list_drafts
  -> resolve account and adapter config
  -> require adapter capability draft_batchget
  -> adapterClient.batchGetDrafts(account, { offset, count, no_content })
  -> normalize item.news_item[0] summary
  -> return bounded list
```

## Decisions

- Use `include_content=false` default and map it to adapter `no_content=1`.
- Limit `count` to 20 by default and 50 max.
- Return first article summary per draft for MVP; multi-article details can be added later.
- Do not synthesize `preview_url`.
- Do not implement update/delete in this slice.

## Verification

- `pnpm --filter @mcps/wechat-draft build`
- `pnpm --filter @mcps/wechat-draft test`
- `git diff --check`

## Follow-Up Gate

Before update/delete:

- confirm adapter endpoints and WeChat API behavior
- add destructive tool annotations where supported
- require explicit confirmation payload
- decide how update consumes Hermes artifact versions
