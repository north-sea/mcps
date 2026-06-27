# Context Manifest: WeChat Draft Publish-Ready Facade

**Workspace**: `wechat-draft-publish-ready-facade`
**Created**: 2026-06-27
**Status**: active

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-publish-ready-facade/spec.md` | Defines facade modes, side-effect boundaries, and out-of-scope items. | implement | yes |
| `specs/wechat-draft-publish-ready-facade/plan.md` | Defines ADRs, Hermes wrapper decision, phase trace, and verification strategy. | implement | yes |
| `specs/wechat-draft-publish-ready-facade/tasks.md` | Defines vertical slices and task verification. | implement | yes |
| `specs/wechat-draft-agent-experience-roadmap/roadmap.md` | Keeps facade inside roadmap and non-duplication rules. | implement | yes |
| `specs/wechat-article-document-tools/acceptance.md` | Establishes article-document build/render tools to compose. | implement | yes |
| `specs/wechat-draft-asset-preflight/acceptance.md` | Establishes asset preflight boundary and no-compression decision. | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-publish-ready-facade/spec.md` | Verify FR-001..FR-009 and out-of-scope. | verify | yes |
| `specs/wechat-draft-publish-ready-facade/plan.md` | Check ADR drift and side-effect boundaries. | verify | yes |
| `specs/wechat-draft-publish-ready-facade/tasks.md` | Confirm task completion and evidence mapping. | verify | yes |
| `specs/wechat-draft-publish-ready-facade/verify-evidence.md` | Expected evidence ledger for tests/diffusion/risks. | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `packages/wechat-draft/src/service/WechatDraftService.ts` | Existing service methods to compose and facade implementation target. | implement / verify | yes |
| `packages/wechat-draft/src/hermes/HermesDbClient.ts` | Needs minimal workflow run/artifact upsert wrappers. | implement / verify | yes |
| `packages/wechat-draft/src/workflow/DraftWorkflow.ts` | Existing draft creation and idempotency behavior. | implement / verify | yes |
| `packages/wechat-draft/src/mcp/createMcpServer.ts` | MCP registration target. | implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/workflow_runs.py` | Existing Hermes workflow run upsert contract. | implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py` | Existing Hermes workflow artifact upsert contract. | implement / verify | yes |

---

## Rules

- Do not duplicate renderer, preflight, publish validation, or draft workflow logic.
- Do not generate or rewrite content.
- Do not perform implicit image upload/compression.
- Do not add draft CRUD/schedule/group-send.
- Preserve phase trace for every stopped side-effect boundary.
