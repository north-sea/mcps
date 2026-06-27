# Commit Plan: WeChat Draft Agent Experience Roadmap

**Workspace**: `wechat-draft-agent-experience-roadmap`
**Date**: 2026-06-27
**Status**: pending user confirmation

## Verification Baseline

| Check | Result |
|---|---|
| `pnpm --filter @mcps/wechat-draft build` | PASS |
| `pnpm --filter @mcps/wechat-draft test` | PASS, 67/67 |
| `uv run pytest tests/test_workflow_repo_sql.py tests/test_workflow_tools.py` from `packages/hermes-db` | PASS, 19/19 |
| `uv run pytest tests/test_workflow_contracts.py tests/test_workflow_schema_health.py tests/test_workflow_integration.py tests/test_migration_sql.py` from `packages/hermes-db` | PASS, 14 passed, 1 skipped |
| `git diff --check` | PASS |

## Included Files

### Batch 1: WeChat Draft Agent-Facing MCP

Suggested commit message:

```text
feat(wechat-draft): harden agent draft workflow tools
```

Files:

- `docs/article-document-artifact-example.md`
- `packages/wechat-draft/src/hermes/HermesDbClient.ts`
- `packages/wechat-draft/src/http/httpMcpSmoke.test.ts`
- `packages/wechat-draft/src/mcp/createMcpServer.ts`
- `packages/wechat-draft/src/mcp/toolResult.test.ts`
- `packages/wechat-draft/src/schemas/result-types.ts`
- `packages/wechat-draft/src/schemas/tool-schemas.ts`
- `packages/wechat-draft/src/service/WechatDraftService.ts`
- `packages/wechat-draft/src/service/WechatDraftService.articleDocument.test.ts`
- `packages/wechat-draft/src/service/WechatDraftService.facade.test.ts`
- `packages/wechat-draft/src/service/WechatDraftService.listDrafts.test.ts`
- `packages/wechat-draft/src/service/WechatDraftService.uploadAsset.test.ts`
- `packages/wechat-draft/src/service/articleDocumentErrors.ts`
- `packages/wechat-draft/src/service/errorMapping.ts`
- `packages/wechat-draft/src/service/errorMapping.test.ts`
- `packages/wechat-draft/src/wechat/AssetSourceLoader.ts`
- `packages/wechat-draft/src/wechat/AssetSourceLoader.test.ts`
- `packages/wechat-draft/src/wechat/DraftPayloadBuilder.ts`
- `packages/wechat-draft/src/wechat/WechatAdapterClient.ts`
- `packages/wechat-draft/src/workflow/DraftWorkflow.ts`
- `packages/wechat-draft/src/workflow/DraftWorkflow.test.ts`

Rationale:

- Adds constraints/remediation, article-document tools, asset preflight, publish-ready facade, and read-only remote draft list.
- Keeps update/delete/schedule/group-send out of implementation.

### Batch 2: Hermes Artifact Lifecycle

Suggested commit message:

```text
feat(hermes-db): add workflow artifact version and diff tools
```

Files:

- `packages/hermes-db/src/hermes_db_mcp/contracts.py`
- `packages/hermes-db/src/hermes_db_mcp/repositories/workflow_repo.py`
- `packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py`
- `packages/hermes-db/tests/test_workflow_integration.py`
- `packages/hermes-db/tests/test_workflow_repo_sql.py`
- `packages/hermes-db/tests/test_workflow_tools.py`

Rationale:

- Adds explicit version/list/latest/diff tools and conflict recovery guidance.
- Preserves immutable artifact rows and avoids `force_update`.

### Batch 3: SDD Roadmap And Acceptance Records

Suggested commit message:

```text
docs(specs): close wechat draft agent experience roadmap
```

Files:

- `specs/.active`
- `specs/wechat-draft-agent-experience-roadmap/`
- `specs/wechat-draft-agent-contract-hardening/`
- `specs/wechat-article-document-tools/`
- `specs/wechat-draft-asset-preflight/`
- `specs/wechat-draft-publish-ready-facade/`
- `specs/hermes-artifact-versioning-and-diff/`
- `specs/wechat-draft-ops-crud/`

Rationale:

- Records roadmap planning, feature specs/plans/tasks/evidence/acceptance, and roadmap closeout.

## Excluded Files

| File / Path | Reason |
|---|---|
| `.pnpm-store/` | Generated dependency cache; should not be committed. |
| `DEPLOYMENT_SUMMARY.md` | Appears deployment-specific and not part of this roadmap scope unless user confirms. |
| `NAS_DEPLOYMENT_GUIDE.md` | Appears deployment-specific and not part of this roadmap scope unless user confirms. |
| `specs/note-skill-migration-roadmap/` | Separate roadmap used as reference; not owned by this roadmap commit unless user confirms. |
| `specs/wechat-draft-http-service/tasks.md` | Existing HTTP service feature file changed before/alongside this work; include only if user confirms it belongs in this batch. |
| `specs/wechat-draft-http-service/acceptance.md` | Existing HTTP service closeout record; include only if user confirms it belongs in this batch. |

## Needs User Decision

| Item | Question |
|---|---|
| Deployment docs | Should `DEPLOYMENT_SUMMARY.md` and `NAS_DEPLOYMENT_GUIDE.md` be committed separately, ignored, or left untracked? |
| HTTP service specs | Should `specs/wechat-draft-http-service/tasks.md` and `acceptance.md` be included in a separate docs commit? |
| Note-skill roadmap | Should `specs/note-skill-migration-roadmap/` be committed now, or remain outside this roadmap? |
| Commit execution | Confirm whether to run the three suggested commits, adjust batches, or leave changes uncommitted. |

## Risks

- The working tree contains unrelated or prior feature files. Use explicit path-based `git add`; do not use `git add -A`.
- Live WeChat and live Hermes DB integration were not run for every new path; local contract tests pass.
- Deployment may need package versioning or image rebuild beyond this commit plan.

## Commands After Confirmation

Only after explicit user confirmation, run path-specific `git add` for each batch and one `git commit` per batch. Do not push automatically.
