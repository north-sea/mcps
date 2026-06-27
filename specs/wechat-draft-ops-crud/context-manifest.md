# Context Manifest: WeChat Draft Ops CRUD

**Workspace**: `wechat-draft-ops-crud`
**Created**: 2026-06-27
**Status**: active

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-ops-crud/spec.md` | Defines read-only slice and destructive boundaries. | implement | yes |
| `specs/wechat-draft-ops-crud/plan.md` | Defines schema/client/service/MCP approach. | implement | yes |
| `packages/wechat-draft/src/wechat/WechatAdapterClient.ts` | Adapter client target. | implement / verify | yes |
| `packages/wechat-draft/src/service/WechatDraftService.ts` | Service target. | implement / verify | yes |
| `packages/wechat-draft/src/mcp/createMcpServer.ts` | MCP registration target. | implement / verify | yes |
| `packages/wechat-draft-adapter/src/server.ts` | Existing batchget endpoint contract. | research | yes |

## Rules

- Implement read-only list first.
- Do not implement update/delete/schedule/group-send.
- Do not synthesize preview URLs.
- Full content must be opt-in.
