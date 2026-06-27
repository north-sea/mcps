# Context Manifest: WeChat Draft Asset Preflight

**Workspace**: `wechat-draft-asset-preflight`
**Created**: 2026-06-27
**Status**: active

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-asset-preflight/spec.md` | Defines preflight requirements, out-of-scope compression/channel changes, and recovery expectations. | implement | yes |
| `specs/wechat-draft-asset-preflight/plan.md` | Defines MVP decision: recommendation only, no real compression dependency. | implement | yes |
| `specs/wechat-draft-asset-preflight/tasks.md` | Defines task slices, dependencies, and verification. | implement | yes |
| `specs/wechat-draft-agent-experience-roadmap/roadmap.md` | Keeps feature inside larger roadmap and deferred publish-ready facade boundary. | implement | yes |
| `specs/wechat-draft-agent-contract-hardening/acceptance.md` | Defines existing constraints/remediation envelope to reuse. | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-asset-preflight/spec.md` | Verify FR-001..FR-008 and out-of-scope constraints. | verify | yes |
| `specs/wechat-draft-asset-preflight/plan.md` | Check ADR drift, especially no compression dependency and no WeChat limit relaxation. | verify | yes |
| `specs/wechat-draft-asset-preflight/tasks.md` | Confirm every task has evidence. | verify | yes |
| `specs/wechat-draft-asset-preflight/verify-evidence.md` | Expected evidence ledger for tests, diffusion, and remaining risk. | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` | Existing source loading and size/MIME guards to extend. | plan / implement / verify | yes |
| `packages/wechat-draft/src/wechat/AssetSourceLoader.test.ts` | Existing asset guard tests to extend. | implement / verify | yes |
| `packages/wechat-draft/src/service/WechatDraftService.ts` | Service method for upload and new preflight method. | implement / verify | yes |
| `packages/wechat-draft/src/service/WechatDraftService.uploadAsset.test.ts` | Existing upload tests to extend for preflight gate. | implement / verify | yes |
| `packages/wechat-draft/src/mcp/createMcpServer.ts` | MCP registration pattern. | implement / verify | yes |
| `packages/wechat-draft/package.json` | Confirms no image processing dependency in MVP. | plan / verify | yes |

---

## Rules

- Do not add a heavy image processing dependency in this feature.
- Do not implement real compression; return transform recommendations only.
- Do not relax body image or cover image constraints.
- Do not leak full private local paths in preflight diagnostics.
- Do not call adapter upload from `wechat_preflight_asset`.
