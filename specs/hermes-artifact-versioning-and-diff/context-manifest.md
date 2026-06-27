# Context Manifest: Hermes Artifact Versioning And Diff

**Workspace**: `hermes-artifact-versioning-and-diff`
**Created**: 2026-06-27
**Status**: active

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/hermes-artifact-versioning-and-diff/spec.md` | Defines artifact lifecycle contract and boundaries. | implement | yes |
| `specs/hermes-artifact-versioning-and-diff/plan.md` | Defines repo/tool approach and ADRs. | implement | yes |
| `specs/hermes-artifact-versioning-and-diff/tasks.md` | Defines vertical slices. | implement | yes |
| `packages/hermes-db/src/hermes_db_mcp/repositories/workflow_repo.py` | Repo target for version queries and existing immutable upsert. | implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py` | Tool target for new lifecycle/diff tools. | implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/contracts.py` | Error/result vocabulary and validation helpers. | implement / verify | yes |

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/hermes-artifact-versioning-and-diff/spec.md` | Verify FR and out-of-scope. | verify | yes |
| `specs/hermes-artifact-versioning-and-diff/plan.md` | Check ADR drift. | verify | yes |
| `specs/hermes-artifact-versioning-and-diff/tasks.md` | Confirm task completion and evidence. | verify | yes |
| `packages/hermes-db/tests/test_workflow_repo_sql.py` | Repo SQL guard. | verify | yes |
| `packages/hermes-db/tests/test_workflow_tools.py` | Tool contract guard. | verify | yes |

## Rules

- Do not add `force_update`.
- Do not mutate existing artifact content rows.
- Do not change WeChat draft facade.
- Do not add schema migration unless implementation proves current schema insufficient.
- Keep diff output bounded.
