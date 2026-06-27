# Verify Evidence: WeChat Draft Publish-Ready Facade

**Workspace**: `wechat-draft-publish-ready-facade`
**Created**: 2026-06-27
**Status**: PASS

---

## Baseline / Failed Behavior

| Case | Before Behavior | Evidence Source | After Guard |
|---|---|---|---|
| No one-call draft facade | Agents call validate/build/upsert/validate/create draft manually. | Existing MCP tools in `createMcpServer.ts` before facade. | Add `wechat_create_draft_facade`. |
| Hermes TS client lacks workflow upsert wrappers | Hermes MCP has `upsert_workflow_run` and `upsert_workflow_artifact`; WeChat TS client only wraps read artifact and article ledger. | `HermesDbClient.ts`, Hermes tool files | Add minimal client wrappers. |
| Phase recovery spread across tools | Lower-level errors have remediation, but no facade phase trace. | Contract hardening acceptance | Add facade phase trace and current phase. |

---

## Failed Attempt Ledger

| Time | Attempt | Result | Decision |
|---|---|---|---|
| 2026-06-27 | Considered keeping article-document mode as "build payload only". | Rejected for facade MVP because it would keep Hermes upsert as a manual agent step. | Add minimal Hermes wrappers. |
| 2026-06-27 | Considered implicit asset upload/compression inside facade. | Rejected; asset preflight explicitly deferred real compression and upload remains separate. | Facade requires prepared asset IDs/URLs. |

---

## Verification Runs

| Time | Command | Result | Notes |
|---|---|---|---|
| 2026-06-27 | `pnpm --filter @mcps/wechat-draft build` | PASS | TypeScript compile and executable chmod completed. |
| 2026-06-27 | `pnpm --filter @mcps/wechat-draft test` | PASS | Node test runner: 64/64 tests passed, including facade success/failure paths and HTTP MCP smoke discovery. |
| 2026-06-27 | `git diff --check` | PASS | No whitespace/conflict-marker issues. |

---

## Diffusion Check

| Check | Result | Evidence |
|---|---|---|
| Facade composes existing renderer/build/validation/draft flow | PASS | `WechatDraftService.createDraftFacade` calls `buildPublishReadyArtifact`, `validatePublishArtifact`, and `createDraft`; it does not duplicate renderer or workflow internals. |
| MCP discoverability preserved | PASS | HTTP MCP smoke lists `wechat_create_draft_facade` plus existing low-level tools. |
| No out-of-scope compression/CRUD/scheduling/versioning added | PASS | `rg "auto_compress|compress_image|schedule_publish|list_drafts|update_draft|delete_draft|artifact_diff|force_update"` only matched roadmap/spec/task boundary text, not implementation. |
| Failure recovery fields preserved | PASS | Facade tests cover validation failure, missing cover, Hermes artifact conflict, and non-saved draft remediation. |

---

## Remaining Risk

- Facade adds a broader side-effect surface. This is accepted because `article_document` mode returns `phase_trace` around each side-effect boundary and tests cover early stop before Hermes writes.
- No live WeChat draft creation was run for this feature; verification is component/workflow-contract level with fakes and HTTP MCP smoke.
