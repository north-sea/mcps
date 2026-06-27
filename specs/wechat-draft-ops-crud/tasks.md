# Tasks: WeChat Draft Ops CRUD

**Workspace**: `wechat-draft-ops-crud` | **Date**: 2026-06-27

## Phase 1: Read-Only Draft List

- [x] T001 [Schema] Add list drafts input/output
  - scope: `tool-schemas.ts`
  - verify: TypeScript build.

- [x] T002 [Adapter] Add batchget method to WeChat adapter client
  - scope: `WechatAdapterClient.ts`
  - verify: service fake adapter compiles.

- [x] T003 [Service] Add `listDrafts`
  - scope: `WechatDraftService.ts`
  - verify: tests cover summary mode, include content mode, capability missing.

- [x] T004 [MCP] Register `wechat_list_drafts`
  - scope: `createMcpServer.ts`, HTTP smoke
  - verify: tool list includes `wechat_list_drafts`.

## Phase 2: Docs And Closeout

- [x] T005 [Docs] Record update/delete deferred safety gate
  - scope: spec/acceptance/roadmap
  - verify: no update/delete implementation added.

- [x] T006 [Verify] Run build/test/checks
  - scope: `@mcps/wechat-draft`
  - verify: build/test/diff-check pass.

- [x] T007 [Closeout] Acceptance and roadmap update
  - scope: `acceptance.md`, roadmap
  - verify: completion record written.
