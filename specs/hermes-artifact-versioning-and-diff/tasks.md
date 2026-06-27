# Tasks: Hermes Artifact Versioning And Diff

**Workspace**: `hermes-artifact-versioning-and-diff` | **Date**: 2026-06-27
**Input**: `spec.md` + `plan.md`

## Phase 1: Contract And Repo Foundation

- [x] T001 [Spec] Capture current versioning facts and boundaries
  - scope: `spec.md`, `plan.md`
  - verify: spec states no `force_update`, no WeChat facade change, no schema migration for MVP.

- [x] T002 [Repo] Add logical family version queries
  - scope: `workflow_repo.py`
  - slice: list versions and latest by artifact ID or `run_id/stage/name`.
  - verify: repo SQL tests assert selector query, ordering, limit/offset.

## Phase 2: Create Explicit New Version

- [x] T003 [Repo/Tool] Add `create_workflow_artifact_version`
  - scope: `workflow_artifacts.py`, `workflow_repo.py`
  - slice: derive defaults from parent artifact and call existing immutable `upsert_artifact`.
  - verify: tool tests cover success, idempotency hit, missing parent.

- [x] T004 [Contract] Update conflict remediation
  - scope: `workflow_artifacts.py`, tests
  - slice: `artifact_id_conflict.next_action` names `create_workflow_artifact_version`.
  - verify: existing conflict test updated.

## Phase 3: Inspect Versions

- [x] T005 [Tool] Add `list_workflow_artifact_versions`
  - scope: `workflow_artifacts.py`
  - slice: read-only version list with selector validation and bounded pagination.
  - verify: tool tests cover artifact selector and tuple selector.

- [x] T006 [Tool] Add `get_latest_workflow_artifact_version`
  - scope: `workflow_artifacts.py`
  - slice: read-only latest lookup.
  - verify: tool tests cover latest found and not found.

## Phase 4: Diff

- [x] T007 [Tool] Add `diff_workflow_artifacts`
  - scope: `workflow_artifacts.py`
  - slice: compare top-level summary fields, metadata keys, content hash/size, and bounded inline text diff.
  - verify: tool tests cover inline diff and content_ref-only fallback.

## Phase 5: Verification And Closeout Prep

- [x] T008 [Verify] Run Hermes workflow tests
  - scope: `packages/hermes-db`
  - verify: targeted pytest and `git diff --check`.

- [x] T009 [Closeout] Acceptance and roadmap update
  - scope: `acceptance.md`, roadmap
  - verify: evidence table maps FR-001..FR-009.

## Dependency Order

T001 -> T002 -> T003/T004 -> T005/T006 -> T007 -> T008 -> T009.
