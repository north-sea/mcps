# Verify Evidence: Hermes Artifact Versioning And Diff

**Workspace**: `hermes-artifact-versioning-and-diff`
**Date**: 2026-06-27
**Status**: PASS

## Verification Runs

| Command | Result | Notes |
|---|---|---|
| `uv run pytest tests/test_workflow_repo_sql.py tests/test_workflow_tools.py` from `packages/hermes-db` | PASS | 19/19 passed. Covers repo SQL shape and tool contracts. |
| `uv run pytest tests/test_workflow_contracts.py tests/test_workflow_schema_health.py tests/test_workflow_integration.py tests/test_migration_sql.py` from `packages/hermes-db` | PASS | 14 passed, 1 skipped. Integration skip is expected without live DB fixture. |
| `git diff --check` | PASS | No whitespace/conflict-marker issues. |

## Coverage

| Area | Evidence | Verdict |
|---|---|---|
| Explicit version creation | `test_create_workflow_artifact_version_derives_parent_fields`, missing parent test | PASS |
| Existing conflict contract | `test_upsert_workflow_artifact_conflict_returns_remediation` now points to `create_workflow_artifact_version` | PASS |
| Version list/latest lookup | `test_list_workflow_artifact_versions_returns_lineage`, `test_get_latest_workflow_artifact_version_returns_highest_version` | PASS |
| Bounded diff | `test_diff_workflow_artifacts_returns_bounded_inline_diff`, `test_diff_workflow_artifacts_does_not_dereference_content_ref` | PASS |
| Repo SQL shape | `test_list_artifact_versions_resolves_artifact_selector_and_orders_by_version`, `test_get_latest_artifact_version_uses_desc_limit_one` | PASS |
| Existing upsert behavior | Existing workflow upsert tests still pass | PASS |

## Architecture Drift Check

- No migration added; existing `version`, `parent_artifact_id`, parent index, and logical version uniqueness are reused.
- No WeChat draft facade changes were made.
- No `force_update` or in-place overwrite path was added.
- Diff output is bounded and does not dereference `content_ref`.

## Remaining Risk

- `list_workflow_artifact_versions` uses logical tuple `run_id/stage/name` as the version family source. Recursive parent-chain traversal remains a future enhancement if artifacts cross logical tuples.
- Live DB integration was not run in this environment; existing integration test skipped by fixture.
