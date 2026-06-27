# Context Manifest: WeChat Draft Agent Contract Hardening

**Workspace**: `wechat-draft-agent-contract-hardening`
**Created**: 2026-06-27
**Status**: active

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-agent-contract-hardening/spec.md` | Defines user stories, scope, out-of-scope boundaries, and feature traits. | implement | yes |
| `specs/wechat-draft-agent-contract-hardening/plan.md` | Defines ADRs, module boundaries, Producer-Consumer Matrix, YAGNI limits, and verification strategy. | implement | yes |
| `specs/wechat-draft-agent-contract-hardening/tasks.md` | Defines execution order, slice boundaries, and verification requirements. | implement | yes |
| `specs/wechat-draft-agent-experience-roadmap/roadmap.md` | Defines roadmap boundary with `note-skill-migration-roadmap` and prevents duplicate implementation. | implement | yes |
| `packages/wechat-draft/src/schemas/result-types.ts` | Existing WeChat result/error envelope to extend compatibly. | implement | yes |
| `packages/wechat-draft/src/schemas/tool-schemas.ts` | Existing MCP input/output schemas and draft job status surface. | implement | yes |
| `packages/wechat-draft/src/service/WechatDraftService.ts` | Owns list accounts, validate/create draft, upload asset service behavior. | implement | yes |
| `packages/wechat-draft/src/service/errorMapping.ts` | Existing operational error mapping and sanitization boundary. | implement | yes |
| `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` | Source of current asset size/MIME/path validation constraints. | implement | yes |
| `packages/wechat-draft/src/wechat/DraftPayloadBuilder.ts` | Current `content_text`/`content_ref` guard and `T013` failure source. | implement | yes |
| `packages/wechat-draft/src/workflow/DraftWorkflow.ts` | Draft workflow phase transitions and failure mapping. | implement | yes |
| `packages/hermes-db/src/hermes_db_mcp/contracts.py` | Existing `ToolError` structure and shared error code mapping. | implement | yes |
| `packages/hermes-db/src/hermes_db_mcp/repositories/workflow_repo.py` | Artifact upsert idempotency/conflict behavior. | implement | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py` | Public hermes workflow artifact tool response mapping. | implement | yes |
| `docs/article-document-artifact-example.md` | Existing example that must clarify `content_text` string-vs-object boundary. | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-agent-contract-hardening/spec.md` | Verify FR/US/out-of-scope coverage. | verify | yes |
| `specs/wechat-draft-agent-contract-hardening/plan.md` | Check architecture drift, ADR compliance, and no scope creep into E2E/versioning/note migration. | verify | yes |
| `specs/wechat-draft-agent-contract-hardening/tasks.md` | Check each task has fresh evidence and done criteria. | verify | yes |
| `specs/wechat-draft-agent-contract-hardening/verify-evidence.md` | Store before/after, test commands, diffusion check, and skipped live-test rationale. | verify | yes |
| `packages/wechat-draft/package.json` | Verify build/test commands and package-level test entrypoints. | verify | yes |
| `packages/wechat-draft/src/**/*.test.ts` | Verify TypeScript coverage for constraints, error envelope, workflow, and upload paths. | verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/**/*.py` | Verify hermes error/outcome implementation and tests. | verify | yes |
| `specs/wechat-draft-http-service/acceptance.md` | Confirms HTTP service base is already closed and should not be reopened by this feature. | verify | no |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial.html | Official permanent material constraints: image 10M, thumb 64KB JPG, uploadimg note. | plan / implement / verify | yes |
| https://developers.weixin.qq.com/doc/service/api/material/permanent/api_uploadimage.html | Official content image upload constraints: jpg/png under 1MB. | plan / implement / verify | yes |
| https://developers.weixin.qq.com/doc/service/api/draftbox/draftmanage/api_draft_add.html | Official draft add fields including `thumb_media_id` and content constraints. | plan / implement / verify | yes |
| `specs/note-skill-migration-roadmap/roadmap.md` | Boundary reference: skill migration, agents reconciliation, writing generation, Library/Memory are not owned here. | plan / implement / verify | yes |
| `/Users/yqg/.agents/skills/sdd/references/bugfix-loop-breaker.md` | Required because this feature must record failed attempts, regression guards, and diffusion checks. | plan / tasks / verify | yes |
| `/Users/yqg/.agents/skills/sdd/references/vertical-slice-decomposition.md` | Required to keep tasks as end-to-end slices. | tasks / verify | yes |

---

## Rules

- Required context must be re-read before implementation or verification decisions that depend on it.
- Do not implement `force_update`, E2E facade, image compression, draft CRUD, note skill migration, writing generation, or Library/Memory ingestion in this feature.
- Official WeChat media limits must be treated as constraints unless live evidence proves a different API path.
- Do not copy large logs or raw external docs into this manifest; record only source, reason, and verification status.
- Do not introduce `.trellis/`, Trellis CLI, hook, task.py, or automatic context injection.
