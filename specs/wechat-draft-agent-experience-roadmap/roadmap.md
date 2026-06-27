# Roadmap: WeChat Draft Agent Experience

**Umbrella**: `wechat-draft-agent-experience-roadmap`
**Created**: 2026-06-27
**Status**: complete
**Current Feature**: `wechat-draft-agent-experience-roadmap`
**Next Recommended Feature**: `commit-and-deploy-decision`

---

## Summary

This roadmap turns the WeChat draft MCP from a low-level engineering prototype into an agent-friendly publication surface. The work should not be added to `wechat-draft-http-service`: that feature covers the Streamable HTTP service and deployment path, while this roadmap spans tool contracts, actionable errors, artifact persistence semantics, content preparation, asset preflight, and future draft operations.

The first feature is contract hardening. It reduces failed retries by making constraints discoverable, errors actionable, and artifact idempotency explicit before adding larger workflow automation.

This roadmap is intentionally narrower than `note-skill-migration-roadmap`. It does not migrate note skills, decide agents repository ownership, implement writing generation, or move source materials into Library/Memory. It provides stable MCP contracts that those higher-level roadmaps and agents can consume.

---

## Current State

| Field | Value |
|---|---|
| Current feature | `wechat-draft-agent-experience-roadmap` |
| specs/.active expected | `wechat-draft-agent-experience-roadmap` |
| Current stage | `closeout complete` |
| Next stage | `commit/deploy decision` |
| Current objective | Roadmap PASS recorded; decide whether to commit and deploy accumulated changes. |

---

## Boundary With `note-skill-migration-roadmap`

`note-skill-migration-roadmap` is the owner for skill inventory, agents capability reconciliation, content workflow ownership, and Library/Memory routing. This roadmap only owns deterministic MCP/tooling behavior inside the WeChat draft publication boundary.

| Area | Owned By `note-skill-migration-roadmap` | Owned By This Roadmap |
|---|---|---|
| Skill migration | Inventory, deletion gates, thin-skill routing, archive/readme pointers | None |
| Agents reconciliation | Decide whether `apps/wechat-agent` or shared packages should own a business workflow | Provide MCP contracts for agents to call |
| Writing generation | Prompts, model routing, ideation, drafts, rewrites, review gates | None |
| Library/Memory | Source materials, platform rules, long-lived decisions and searchable references | Only document MCP constraints and durable tool contracts |
| WeChat draft publication | Decide how content skills route into publish-ready handoff | Own publish-ready artifact validation, asset upload constraints, draft creation contract, and status/errors |

### Non-Duplication Rules

- Do not recreate `wechat-agent` business workflows in `mcps`; expose deterministic tool contracts for them.
- Do not migrate `note` skills or build the migration matrix here; that remains in `note-skill-migration-roadmap`.
- Do not put prompt/model-dependent writing generation, editing, title generation, style review, or content ideation into this MCP roadmap.
- Do not build Library/Wiki ingestion or Memory capture pipelines here.
- Do not let `wechat-draft-publish-ready-facade` grow past the boundary of "publish-ready content in, WeChat draft out".
- Do not implement generic hermes-db artifact versioning inside a WeChat-only feature unless the scope is explicitly split or handed off.

---

## Feature Roadmap

| Feature | Goal | Status | Depends On | Start Condition | Recommended Stage | Notes |
|---|---|---|---|---|---|---|
| `wechat-draft-agent-contract-hardening` | Expose account/tool constraints, structured remediation hints, content contract validation, and artifact upsert idempotency/conflict details. | done | `wechat-draft-http-service` closeout | HTTP service is released and healthy; failed draft run has concrete failure modes. | closeout complete | P0 completed. Acceptance: `specs/wechat-draft-agent-contract-hardening/acceptance.md`. |
| `wechat-article-document-tools` | Register deterministic article document import/render/preview/build capabilities as MCP tools so agents do not hand-roll tiptap JSON or HTML. | done | `wechat-draft-agent-contract-hardening` | Error/result envelope and content contract are stable. | closeout complete | P1 completed. Acceptance: `specs/wechat-article-document-tools/acceptance.md`. 51/51 tests pass. |
| `wechat-draft-asset-preflight` | Add asset probing, clearer local path diagnostics, and optional explicit compression/preflight for cover/body images. | done | `wechat-draft-agent-contract-hardening` | Constraints are exposed through `wechat_list_accounts`; image-size policy is documented against official WeChat limits. | closeout complete | P1 completed. Acceptance: `specs/wechat-draft-asset-preflight/acceptance.md`. 58/58 tests pass. |
| `wechat-draft-publish-ready-facade` | Provide a single agent-facing facade that accepts publish-ready content/artifacts, validates, uploads required assets, and creates the WeChat draft. | done | `wechat-article-document-tools`, `wechat-draft-asset-preflight` | Builder/render/preflight tools are available and individually verified. | closeout complete | P1 completed. Acceptance: `specs/wechat-draft-publish-ready-facade/acceptance.md`. 64/64 tests pass. |
| `hermes-artifact-versioning-and-diff` | Add explicit artifact versioning/diff/replace semantics instead of overloading `force_update`. | done | `wechat-draft-agent-contract-hardening`, `wechat-draft-publish-ready-facade` | Facade now surfaces Hermes conflict remediation; remaining pain is generic artifact lifecycle semantics. | closeout complete | Completed in Hermes scope. Acceptance: `specs/hermes-artifact-versioning-and-diff/acceptance.md`. |
| `wechat-draft-ops-crud` | Add draft list/update/delete and safer preview/operations capabilities. | done | `wechat-draft-publish-ready-facade`, `hermes-artifact-versioning-and-diff` | Draft creation facade is stable and artifact versioning exists for safer update/recovery. | closeout complete | Read-only draft list completed. Update/delete intentionally deferred to a separate destructive-ops feature. Acceptance: `specs/wechat-draft-ops-crud/acceptance.md`. |

---

## Completion Log

| Feature | Date | Verdict | Evidence | Impact On Roadmap |
|---|---|---|---|---|
| `wechat-draft-http-service` | 2026-06-27 | PASS | Local build/test passed; GitHub Actions run `28273612416` built, pushed, and deployed `ghcr.io/north-sea/wechat-draft-mcp:v0.2.3`; NAS container is healthy and `/health` returns `status=ok`. | Unblocks this roadmap. The service/deployment base is stable enough to harden agent-facing contracts next. |
| `wechat-draft-agent-contract-hardening` | 2026-06-27 | PASS | `pnpm --filter @mcps/wechat-draft build` PASS; `pnpm --filter @mcps/wechat-draft test` PASS 44/44; Hermes workflow pytest targets PASS 10/10 with DB integration fixtures skipped when unavailable; acceptance record complete. | Unblocks `wechat-article-document-tools`; agents now have stable constraints, remediation fields, and artifact upsert outcome semantics. |
| `wechat-article-document-tools` | 2026-06-27 | PASS | `pnpm --filter @mcps/wechat-draft build` PASS; `pnpm --filter @mcps/wechat-draft test` PASS 51/51; acceptance record complete. | Unblocks asset preflight and future publish-ready facade; agents can import, validate, render, and build publish-ready artifact payloads without hand-rolling Tiptap JSON or HTML. |
| `wechat-draft-asset-preflight` | 2026-06-27 | PASS | `pnpm --filter @mcps/wechat-draft build` PASS; `pnpm --filter @mcps/wechat-draft test` PASS 58/58; `git diff --check` PASS; acceptance record complete. | Unblocks publish-ready facade; agents can preflight assets and gate upload without trial-and-error. |
| `wechat-draft-publish-ready-facade` | 2026-06-27 | PASS | `pnpm --filter @mcps/wechat-draft build` PASS; `pnpm --filter @mcps/wechat-draft test` PASS 64/64; `git diff --check` PASS; acceptance record complete. | Agents now have a one-call draft facade. Remaining artifact conflict/version pain should be addressed in Hermes scope, not inside the WeChat facade. |
| `hermes-artifact-versioning-and-diff` | 2026-06-27 | PASS | Hermes targeted pytest PASS 19/19; workflow contract/schema/migration pytest PASS 14 passed, 1 skipped; `git diff --check` PASS; acceptance record complete. | Artifact conflict recovery now has explicit version/list/latest/diff tools. Unblocks safer draft update planning. |
| `wechat-draft-ops-crud` | 2026-06-27 | PASS | `pnpm --filter @mcps/wechat-draft build` PASS; `pnpm --filter @mcps/wechat-draft test` PASS 67/67; `git diff --check` PASS; acceptance record complete. | Remote draft visibility is now available through read-only MCP. Destructive update/delete remain split for a future feature. |

---

## Next Recommendation

Decide whether to commit and deploy the accumulated changes. Destructive draft update/delete should be a separate future feature, not part of this roadmap closeout.

---

## Deferred Features

- `wechat-draft-destructive-ops`: Deferred because update/delete touch remote draft lifecycle and require destructive annotations plus operator confirmation.
- `wechat-draft-schedule-publish`: Deferred beyond this roadmap until publish permission, confirmation UX, and destructive tool annotations are designed.
- `wechat-cover-channel-switch`: Deferred until live evidence proves whether a permanent `image` media id is accepted where WeChat `draft/add` expects `thumb_media_id`.
- `note-skill-migration` work: Deferred to `note-skill-migration-roadmap`; this roadmap only supplies reusable MCP contracts for that migration to consume.
