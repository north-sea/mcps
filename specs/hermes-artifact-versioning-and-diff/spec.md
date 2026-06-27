# Spec: Hermes Artifact Versioning And Diff

**Workspace**: `hermes-artifact-versioning-and-diff`
**Date**: 2026-06-27
**Roadmap**: `wechat-draft-agent-experience-roadmap`
**Status**: draft

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| external-side-effects | ✅ | 新增 Hermes artifact 写入工具会创建版本记录。 |
| data-model-impact | ✅ | 复用现有 `version` / `parent_artifact_id` 字段，可能新增读取/索引或约束检查。 |
| user-visible-output | ✅ | Agent 看到版本、lineage、diff、replace guidance。 |
| multi-stage-workflow | ✅ | 冲突 -> 创建新版本 -> 查询 lineage/diff -> 下游消费。 |
| bugfix-loop-breaker | ✅ | 解决 upsert 冲突和 hash short-circuit 反复让 agent 换 ID/污染历史的问题。 |

## Problem

Hermes workflow artifacts already contain `version` and `parent_artifact_id`, and `upsert_workflow_artifact` already returns idempotency/conflict details. But the agent-facing contract is still incomplete:

- Same `artifact_id` with same hash is an idempotency hit and does not update content fields.
- Same `artifact_id` with different hash returns `artifact_id_conflict`.
- Creating a revised artifact requires the caller to invent a new `artifact_id` and manually set `parent_artifact_id`.
- There is no explicit tool to list an artifact lineage, get latest version for a logical artifact, or diff two artifact versions.

This should be solved in `hermes-db`, not in WeChat draft facade. A WeChat-only `force_update` would overload audit semantics and make non-WeChat artifacts inconsistent.

## Goals

- Provide explicit artifact lifecycle tools for version creation, lineage lookup, latest-version lookup, and diff.
- Preserve immutable artifact semantics: existing artifact rows are not overwritten by default.
- Make conflict recovery deterministic for agents: when conflict happens, next action can be `create_workflow_artifact_version`.
- Keep current `upsert_workflow_artifact` idempotency behavior backward-compatible.
- Support WeChat draft use cases without introducing WeChat-specific artifact version semantics.

## Non-Goals

- No `force_update` parameter that mutates an existing artifact row in place.
- No WeChat MCP facade changes except consuming clearer Hermes outputs later if needed.
- No semantic HTML/Tiptap/image diff in this feature; start with structured metadata plus text-level diff summaries.
- No rollback/promotion workflow for published WeChat drafts.
- No migration of content generation or note skills into Hermes.

## User Stories

### User Story 1 - Create A New Artifact Version (P1)

As an agent recovering from `artifact_id_conflict`, I want to create a new version from an existing artifact, so that history remains linked without overwriting the original row.

**Acceptance Scenarios**

1. **US1-1 conflict recovery new version**
   - Given artifact `A` exists with `content_hash=old`
   - When the agent calls `create_workflow_artifact_version(parent_artifact_id=A, content_hash=new, ...)`
   - Then Hermes creates a new artifact row with `parent_artifact_id=A`
   - And returns `version`, `artifact_id`, `parent_artifact_id`, `created=true`, and `lineage_root_artifact_id`.

2. **US1-2 duplicate new version request**
   - Given a child version already exists under the same logical lineage with the same `run_id/stage/name/content_hash`
   - When the same new-version request is retried
   - Then Hermes returns the existing row with `idempotency_hit=true`, not a duplicate row.

3. **US1-3 missing parent**
   - Given `parent_artifact_id` does not exist
   - When creating a version
   - Then Hermes returns `not_found`, `field=parent_artifact_id`, and `next_action=fetch_or_create_parent_artifact`.

### User Story 2 - Inspect Artifact Versions (P1)

As an agent choosing what to publish or compare, I want to list versions in a lineage and fetch the latest version, so that I do not blindly use stale artifacts.

**Acceptance Scenarios**

1. **US2-1 list lineage**
   - Given root artifact `A` and revisions `B`, `C`
   - When calling `list_workflow_artifact_versions(artifact_id=A)`
   - Then Hermes returns ordered versions with artifact IDs, parent IDs, hashes, timestamps, stage/type/name, and content availability flags.

2. **US2-2 latest version**
   - Given multiple versions in a lineage
   - When calling `get_latest_workflow_artifact_version(artifact_id=A)`
   - Then Hermes returns the highest version in that lineage.

3. **US2-3 filter by run/stage/name**
   - Given agent knows logical tuple but not artifact ID
   - When calling latest/list with `run_id/stage/name`
   - Then Hermes can return versions for that logical artifact family.

### User Story 3 - Diff Artifact Versions (P1)

As an agent resolving whether to update, publish, or discard a revision, I want a compact diff between two artifacts, so that I can explain what changed before choosing a version.

**Acceptance Scenarios**

1. **US3-1 metadata and content hash diff**
   - Given two artifacts
   - When calling `diff_workflow_artifacts(left_artifact_id, right_artifact_id)`
   - Then Hermes returns changed top-level fields, metadata key changes, content hash/size changes, and content availability.

2. **US3-2 inline text diff summary**
   - Given both artifacts have inline `content_text`
   - When diffing
   - Then Hermes returns bounded text diff statistics and a small unified diff preview.

3. **US3-3 content_ref-only diff**
   - Given either artifact has only `content_ref`
   - When diffing
   - Then Hermes does not dereference external content and returns `content_diff_available=false` with a remediation hint.

### User Story 4 - Preserve Existing Upsert Contract (P1)

As existing clients, WeChat draft MCP, and tests, we need `upsert_workflow_artifact` to keep its idempotency semantics, so that this feature does not create surprise overwrites or duplicate writes.

**Acceptance Scenarios**

1. **US4-1 same artifact/hash remains idempotent**
   - Existing same `artifact_id/content_hash` returns `idempotency_hit=true`.

2. **US4-2 same artifact/different hash remains conflict**
   - Existing same `artifact_id` with different hash still returns `artifact_id_conflict`.

3. **US4-3 conflict points to explicit version tool**
   - Conflict remediation points to `create_workflow_artifact_version`, not `force_update`.

## Requirements

### Functional Requirements

- **FR-001**: Add a side-effecting tool for creating a new workflow artifact version from a parent artifact.
- **FR-002**: New-version creation must preserve existing immutable artifact rows and set `parent_artifact_id`.
- **FR-003**: New-version creation must be idempotent for same logical tuple and `content_hash`.
- **FR-004**: Add read-only tools to list versions/lineage and get latest version by artifact ID or logical tuple.
- **FR-005**: Add read-only diff tool for two workflow artifacts.
- **FR-006**: Diff output must be bounded and safe for MCP responses; do not return unbounded full content by default.
- **FR-007**: Existing `upsert_workflow_artifact` contract remains backward-compatible.
- **FR-008**: Error responses must include `next_action`, `remediation_hint`, `retryable`, and `current_phase` where useful.
- **FR-009**: Tools must not leak raw SQL, secrets, or unbounded content.

### Non-Functional Requirements

- **NFR-001**: Prefer repository functions over SQL in tool handlers.
- **NFR-002**: Use existing `version` and `parent_artifact_id` columns before adding schema.
- **NFR-003**: Tests must cover repository SQL shape and MCP tool contract.
- **NFR-004**: Keep WeChat draft facade unchanged unless a later feature explicitly consumes the new tools.
- **NFR-005**: Diff must have deterministic output and bounded preview size.

## Existing Design Facts

- `workflow_artifacts` already has `version`, `parent_artifact_id`, and a logical version uniqueness constraint.
- `workflow_repo.upsert_artifact` already uses an advisory lock on `run_id/stage/name`.
- `upsert_workflow_artifact` already returns idempotency hit context and structured `artifact_id_conflict`.
- `get_workflow_artifact_content` can include inline content when requested.

## Out Of Scope

- In-place artifact overwrite.
- Rich semantic document diff.
- External content dereferencing for `content_ref`.
- Draft list/update/delete/schedule.
- WeChat cover channel switch.

## Open Questions

- Should lineage root be computed recursively from `parent_artifact_id`, or should version families be limited to the existing logical tuple `run_id/stage/name`?
- Should `create_workflow_artifact_version` allow caller-provided `artifact_id`, or always generate a new ID unless explicitly supplied?
- Should diff output include JSON Patch for metadata, or only key-level added/removed/changed summaries?

## Success Criteria

- Agents can recover from `artifact_id_conflict` without inventing unrelated IDs.
- Agents can inspect latest/previous artifact versions before publishing.
- Agents can compare two versions without fetching full content into the conversation.
- Existing WeChat facade and low-level upsert behavior continue to pass tests.
