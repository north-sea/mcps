# Plan: Hermes Artifact Versioning And Diff

**Workspace**: `hermes-artifact-versioning-and-diff`
**Date**: 2026-06-27
**Spec**: [spec.md](spec.md)

## Approach

Add explicit Hermes workflow artifact lifecycle tools on top of the existing immutable artifact table:

1. `create_workflow_artifact_version`: side-effecting, creates a child artifact version from a parent artifact.
2. `list_workflow_artifact_versions`: read-only, lists a logical artifact family by artifact ID or `run_id/stage/name`.
3. `get_latest_workflow_artifact_version`: read-only, returns highest version in the family.
4. `diff_workflow_artifacts`: read-only, returns bounded field/metadata/content diff summary.

Do not add `force_update`. Existing `upsert_workflow_artifact` remains the stable idempotent write primitive.

## Current Architecture

| Layer | Current State | Change |
|---|---|---|
| DB schema | `workflow_artifacts` already has `version`, `parent_artifact_id`, parent index, and `UNIQUE(run_id, stage, name, version)`. | No migration for MVP. |
| Repo | `upsert_artifact`, `list_artifacts`, `get_artifact`. | Add version-family helpers and bounded diff helpers. |
| Tool | `upsert/list/get_content`. | Add lifecycle/diff tools in `workflow_artifacts.py`. |
| Contract | Validates upsert/query payloads. | Add small validators for version lookup and diff inputs if needed. |
| WeChat MCP | Consumes upsert conflict remediation. | No change. |

## ADRs

### ADR-001: Immutable Rows, Explicit Versions

Existing artifact rows remain immutable for content updates. Revised content creates a new row linked through `parent_artifact_id` and logical tuple.

Reason: Auditability matters more than update convenience, and current schema already encodes versions.

### ADR-002: Logical Family Is `run_id/stage/name`

For MVP, latest/list queries use either:

- an `artifact_id`, resolved to that artifact's `run_id/stage/name`
- or an explicit `run_id/stage/name`

The parent chain is still returned, but the ordering and latest selection are based on logical tuple + `version`.

Reason: Current uniqueness and auto-versioning are already defined by `run_id/stage/name`.

### ADR-003: Diff Is Bounded And Text-Level

Diff returns:

- top-level field changes
- metadata added/removed/changed keys
- content hash/size changes
- text diff stats and small unified diff preview only when both artifacts have inline `content_text`

No external dereference and no semantic HTML/Tiptap diff.

### ADR-004: Tool Remediation Points Away From `force_update`

`artifact_id_conflict` remediation should name the explicit new-version tool, not suggest mutation.

## Data Flow

### Create Version

```text
create_workflow_artifact_version(parent_artifact_id, content_hash, content_text/ref, optional metadata/name)
  -> get parent artifact
  -> derive defaults from parent: run_id/stage/type/name/task/topic/account
  -> call workflow_repo.upsert_artifact(parent_artifact_id=parent.artifact_id, ...)
  -> return artifact summary + lineage metadata
```

### List / Latest

```text
artifact_id -> parent artifact -> run_id/stage/name
explicit tuple -> run_id/stage/name
repo list ordered by version asc/desc
```

### Diff

```text
get left/right artifacts with inline content
compare summary fields
compare metadata keys
if both inline content: difflib unified diff preview, bounded
else: content_diff_available=false
```

## API Draft

### `create_workflow_artifact_version`

Inputs:

- required: `parent_artifact_id`, `content_hash`, `content_size_bytes`
- optional override: `artifact_id`, `run_id`, `stage`, `type`, `name`, `task_id`, `topic_id`, `account`, `content_preview`, `content_text`, `content_ref`, `metadata`

Defaults derive from parent when optional fields are omitted.

Output:

- serialized artifact summary
- `created`
- `idempotency_hit`
- `parent_artifact_id`
- `lineage_root_artifact_id`
- `next_action`

### `list_workflow_artifact_versions`

Inputs:

- either `artifact_id`
- or `run_id`, `stage`, `name`
- optional `order` asc/desc, `limit`, `offset`

Output:

- `items`
- `lineage_root_artifact_id`
- `latest_artifact_id`

### `get_latest_workflow_artifact_version`

Same selector as list; returns one item or `not_found`.

### `diff_workflow_artifacts`

Inputs:

- `left_artifact_id`
- `right_artifact_id`
- optional `include_text_preview=true`
- optional `max_preview_lines=80`

Output:

- artifact IDs/hashes/versions
- `field_changes`
- `metadata_changes`
- `content_changed`
- `content_diff_available`
- `content_diff`

## Implementation Slices

1. Repo helpers:
   - `list_artifact_versions`
   - `get_latest_artifact_version`
   - `get_artifact_family_selector`
2. Tool validators and serializers:
   - selector validation
   - bounded diff preview
3. Tools:
   - create version
   - list versions
   - latest version
   - diff
4. Tests:
   - repo SQL shape
   - tool contract with monkeypatched repo
   - compatibility for existing upsert tests

## Risks

| Risk | Mitigation |
|---|---|
| Parent chain and logical tuple disagree | MVP documents logical tuple as source of ordering; parent chain returned as metadata only. |
| Diff responses become too large | Bound preview lines and omit full content. |
| Caller mistakes version creation for overwrite | Tool name and output state `created/idempotency_hit`; no `force_update`. |
| Existing upsert clients break | Do not alter required arguments or successful result shape. |

## Verification

- `uv run pytest packages/hermes-db/tests/test_workflow_repo_sql.py packages/hermes-db/tests/test_workflow_tools.py`
- Existing workflow integration tests where DB is available or skipped by fixture.
- `git diff --check`

## Open Follow-Up

- If recursive lineage across parent chains becomes necessary, add a later feature using recursive CTE and cycle detection.
- If WeChat article docs need semantic diff, add it in article-document tooling, not this generic Hermes layer.
