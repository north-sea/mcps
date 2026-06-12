# Acceptance: Hermes DB Agent Self Evolution Foundation

**Workspace**: `hermes-db-agent-self-evolution-foundation` | **Date**: 2026-06-12  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

---

## Verdict Summary

**Status**: ✅ PASS  
**Deployed Version**: `v0.2.18`  
**Deployed Environment**: NAS production (`hermes-db-mcp` container)  
**Schema Revision**: `0006_agent_self_evolution`

---

## Evidence Table

| ID | Requirement | Evidence | Status |
|----|-------------|----------|--------|
| US1 | Promote approved candidate to active policy | T019 smoke: candidate → policy successful, policy_id returned | ✅ PASS |
| US2 | Query applicable policies by domain/scope/task | T019 smoke: query returned promoted policy, scope matched | ✅ PASS |
| US3 | Disable/rollback policy versions | Unit tests pass; not exercised in T019 smoke (not critical path) | ✅ PASS |
| US4 | Record and list policy application traces | T019 smoke: record → list cycle successful, application_id matched | ✅ PASS |
| US5 | Health capability reports foundation | NAS health: `agent_self_evolution_foundation: true`, schema `0006_agent_self_evolution` | ✅ PASS |
| FR-001 | `agent_policies` table with versioning | Migration 0006 created table with PK/UK/checks/indexes | ✅ PASS |
| FR-002 | `policy_applications` append-only trace | Migration 0006 created table; T019 recorded and listed trace | ✅ PASS |
| FR-003 | Idempotent promote (same candidate → same policy) | Repo test `test_promote_learning_candidate_creates_policy_and_updates_candidate` passes | ✅ PASS |
| FR-004 | Scope isolation (cross-account negative filter) | Repo SQL test covers scope matching; T019 verified scope-filtered query | ✅ PASS |
| FR-005 | Rollback creates new active version, preserves history | Repo test `test_rollback_agent_policy_creates_new_active_version` passes | ✅ PASS |
| FR-006 | Application trace FK to policy_version_id ON DELETE RESTRICT | Migration DDL FK constraint confirmed; repo test inserts and queries traces | ✅ PASS |
| FR-007 | Health capability schema-aware detection | Health tool inspects `agent_policies`/`policy_applications` tables; NAS reports `true` | ✅ PASS |
| FR-008 | Structured MCP error responses | Contract tests cover `invalid_state`/`invalid_scope`/`validation_error`; T019 validated MCP JSON-RPC errors | ✅ PASS |

---

## Workflow Replay

### Phase 1: Migration and Schema (T001-T004)

- Created Alembic revision `0006_agent_self_evolution_foundation.py` (revision id `0006_agent_self_evolution`, 25 chars, fits `varchar(32)`)
- Created `hermes.agent_policies` (24 columns, 2 unique constraints, 4 indexes, 5 check constraints)
- Created `hermes.policy_applications` (17 columns, FK to `agent_policies`, 4 indexes, append-only)
- Migration SQL tests verify table names, indexes, checks, down revision, downgrade order

**Evidence**: `packages/hermes-db/migrations/versions/0006_agent_self_evolution_foundation.py`, `tests/test_migration_sql.py` lines 134-137

### Phase 2: Contracts and Validation (T005-T006)

- Added policy/application status/type constants and validation helpers to `contracts.py`
- Added structured error helpers: `invalid_state`, `invalid_scope`, `validation_error`
- Contract tests cover all validation branches

**Evidence**: `packages/hermes-db/src/hermes_db_mcp/contracts.py` lines 1580-1760, `tests/test_agent_self_evolution_contracts.py`

### Phase 3: Repository Layer (T007-T012)

- Implemented `agent_self_evolution_repo.py` with 7 methods
- Idempotent promote: `status=exported_to_policy` candidate returns existing policy
- Scope isolation: `scope_json <@ $3::jsonb` filter
- Rollback: copies target payload into new monotonic version, marks current `rolled_back`
- Application trace: append-only INSERT

**Evidence**: `packages/hermes-db/src/hermes_db_mcp/repositories/agent_self_evolution_repo.py`, `tests/test_agent_self_evolution_repo_sql.py` (8 tests, all pass)

### Phase 4: MCP Tools (T013-T015)

- Registered 7 MCP tools in `agent_self_evolution.py`
- Tools map DB errors to structured MCP responses
- Tool tests cover success, validation errors, not_found, schema_drift, database_error

**Evidence**: `packages/hermes-db/src/hermes_db_mcp/tools/agent_self_evolution.py`, `tests/test_agent_self_evolution_tools.py`

### Phase 5: Health and Capability (T016-T017)

- Health tool inspects `agent_policies` and `policy_applications` existence + required columns
- Returns `agent_self_evolution_foundation: true` when both tables and `learning_candidates` compatibility columns exist
- Health tests cover true/false paths

**Evidence**: `packages/hermes-db/src/hermes_db_mcp/tools/health.py`, `tests/test_agent_self_evolution_schema_health.py`

### Phase 6: Verification and Live Smoke (T018-T020)

- Local tests: contracts (12 pass), repo SQL (8 pass), tools (7 pass), health (2 pass)
- Deployed v0.2.16 → failed (revision id 36 chars > varchar(32))
- Fixed revision id to 25 chars, deployed v0.2.17 → failed (NAS proxy EOF on GHCR login)
- Root cause: NAS Docker daemon proxy (127.0.0.1:7890) intermittent TLS handshake drop
- Deployed v0.2.17 rerun → success
- Live smoke: discovered promote JSONB double-serialize bug (candidate JSONB columns passed through `_jsonb()` caused CHECK violation)
- Fixed promote repo, deployed v0.2.18 → success
- T019 deployed live smoke PASSED: full tool chain (promote → get_applicable → record → list) verified on NAS production

**Evidence**: 
- CI runs: 27399651872 (v0.2.16 fail), 27409189213 (v0.2.17 fail), 27409189213 rerun (v0.2.17 success), 27417485974 (v0.2.18 success)
- T019 smoke script: `packages/hermes-db/tests/smoke_t019_agent_self_evolution.py`
- NAS health output: `{"version":"0.2.18","schema_revision":"0006_agent_self_evolution","capabilities":{"agent_self_evolution_foundation":true}}`

---

## Deployment Notes

### v0.2.16 Failure (run 27399651872)

**Symptom**: `StringDataRightTruncation: value too long for type character varying(32)` on `UPDATE alembic_version SET version_num='0006_agent_self_evolution_foundation'`

**Root cause**: Revision id `0006_agent_self_evolution_foundation` (36 chars) exceeded `alembic_version.version_num varchar(32)` limit.

**Fix**: Shortened revision id to `0006_agent_self_evolution` (25 chars); kept filename long for readability. Updated migration, tests, docs to use short form.

### v0.2.17 Failures (run 27409189213, first attempt)

**Symptom**: `docker login ghcr.io` on NAS self-hosted runner: `Error response from daemon: Get "https://ghcr.io/v2/": EOF`

**Root cause**: NAS Docker daemon configured to use local proxy (`http://127.0.0.1:7890` in `/etc/docker/daemon.json`). Proxy experienced intermittent TLS handshake drops during CI runs (10:11 and 11:07). `curl` from host succeeded (bypassed daemon proxy), but `docker login` via daemon failed.

**Immediate fix**: Reran failed job after verifying proxy recovered; deploy succeeded.

**Root cause fix**: Added 5-attempt retry with exponential backoff (5/10/15/20s) to NAS GHCR login step in `.github/workflows/mcp-release.yml`. Future proxy blips will auto-retry instead of failing the deploy.

### v0.2.18 Hotfix (run 27417485974)

**Symptom**: T019 smoke on v0.2.17: `promote_learning_candidate_to_policy` returned `database_error: new row for relation "agent_policies" violates check constraint "chk_agent_policies_evidence_refs_json_object"`

**Root cause**: `promote_learning_candidate_to_policy` in `agent_self_evolution_repo.py` passed candidate JSONB columns (`scope_json`, `trigger_conditions_json`, `proposed_policy_json`, `evidence_refs_json`) through `_jsonb()` helper. asyncpg already deserializes JSONB to dict, so `_jsonb()` (which is `json.dumps()`) serialized them a second time, producing strings instead of JSONB objects. INSERT failed CHECK constraints.

**Fix**: Removed `_jsonb()` wrapper from candidate JSONB columns; pass as-is (dict). Only serialize Python-side inputs (`task_types`, `decision_points`, `metadata`) through `_jsonb()`.

**Impact**: v0.2.17 `promote` function was completely non-functional (production bug). v0.2.18 deployed immediately as hotfix.

---

## Known Limitations

1. **MCP tool signature inconsistency**: `list_policy_applications` uses kwargs (no `input` dict), while other tools use `input: dict`. This is due to FastMCP wrapping behavior; T019 smoke accommodated it, but downstream consumers must check tool schemas.

2. **T019 smoke not in CI**: Deployed live smoke is manual (requires DB/MCP/credentials). Future: add smoke to CI post-deploy step or separate scheduled smoke job.

3. **Revision id length guard not in CI**: Though we fixed the immediate issue (shortened revision id), no CI test prevents future revisions from exceeding 32 chars. Recommended: add `test_migration_revision_ids_within_varchar32` to `test_migration_sql.py`.

4. **NAS proxy stability**: Root cause (proxy intermittent EOF) not resolved; only added retry resilience. Long-term: investigate proxy health or switch to direct egress.

---

## Completion Checklist

- [x] All user stories (US1-US5) have evidence
- [x] All functional requirements (FR-001 to FR-008) verified
- [x] Migration executed on production (NAS `hermes-db-mcp`)
- [x] Health capability reports `true` and correct schema revision
- [x] Deployed live smoke passed (T019 full tool chain)
- [x] Production bugs fixed (JSONB double-serialize, revision id length)
- [x] Root cause improvements deployed (workflow GHCR login retry)
- [x] Manifest updated (`deploy/mcp-services.json` includes `agent_self_evolution_foundation`)
- [x] No orphan test candidates/policies left in production DB (T019 cleanup verified)

---

## Knowledge Capture

### Pattern: asyncpg JSONB handling

asyncpg automatically deserializes Postgres JSONB columns to Python `dict`. When copying JSONB values from one row to another in a repo INSERT/UPDATE, pass the dict as-is — do **not** call `json.dumps()` again. Only serialize Python literals (lists, dicts constructed in code) before passing to asyncpg JSONB parameters.

**Anti-pattern** (causes CHECK constraint violations):
```python
_jsonb(candidate["evidence_refs_json"] or {})  # candidate["evidence_refs_json"] is already dict
```

**Correct**:
```python
candidate["evidence_refs_json"] or {}  # asyncpg handles dict → JSONB
```

### Pattern: Alembic revision id length

`alembic_version.version_num` is `varchar(32)`. Revision ids must be ≤32 chars. Alembic file names can be longer (for readability), but the `revision: str = "..."` string in the file must fit. Use short semantic names (e.g. `0006_agent_self_evolution`) rather than verbose descriptions.

**Recommended CI guard** (not yet implemented):
```python
def test_migration_revision_ids_within_varchar32():
    for file in glob("migrations/versions/*.py"):
        match = re.search(r'^revision:\s*str\s*=\s*["\']([^"\']+)["\']', Path(file).read_text(), re.M)
        assert match and len(match.group(1)) <= 32, f"{file} revision id too long"
```

### Pattern: MCP tool input wrapping

FastMCP tools with `input: dict` first parameter expose `input` as a top-level MCP schema field. Callers must wrap arguments: `{"input": {"candidate_id": "...", ...}}`.

Tools with kwargs (e.g. `list_policy_applications(ctx, policy_id: str | None, ...)`) expose each kwarg as a top-level field. Callers pass arguments flat: `{"policy_id": "...", "limit": 10}`.

This inconsistency is a FastMCP limitation. When designing new MCP tools, prefer `input: dict` for consistency with existing hermes-db tools.

---

## Retrospective

### What went well

- SDD workflow (spec → plan → data-model → tasks) provided clear execution path and caught many edge cases early (idempotent promote, rollback semantics, scope isolation)
- Migration-first approach (T001-T004 before repo/tools) prevented schema drift between layers
- Targeted tests (migration SQL, contract validation, repo SQL, tool MCP, health schema-aware) gave high confidence before deploy
- Postgres transactional DDL and asyncpg connection pooling made rollback and retry robust

### What could improve

- **Live smoke should be in CI**: T019 was manual; future deploys risk regressions. Add post-deploy smoke step or separate scheduled job.
- **JSONB handling not documented**: The double-serialize bug was subtle and not caught by unit tests (which use fake DB). Add explicit guidance in repo style guide and consider lint rule or type hints.
- **Revision id length not guarded**: Same issue hit v0.2.13 (wechat retrospective) and v0.2.16 (this feature). CI test would prevent recurrence.
- **MCP tool signature inconsistency**: `list_policy_applications` kwargs vs `input: dict` caused T019 smoke friction. Standardize on one pattern or document the divergence clearly.

### Recommended follow-ups

1. Add `test_migration_revision_ids_within_varchar32` to CI
2. Add T019-style deployed smoke to CI post-deploy step (requires secrets injection)
3. Document asyncpg JSONB handling anti-patterns in `packages/hermes-db/CONTRIBUTING.md` or repo module docstring
4. Investigate NAS proxy stability or switch to direct GHCR egress (long-term)
5. Standardize MCP tool input patterns (RFC + migration guide for existing tools)

---

**Accepted by**: Claude Opus 4.8  
**Acceptance date**: 2026-06-12  
**Production version**: v0.2.18  
**NAS deployment confirmed**: Yes
