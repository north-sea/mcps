# Verify Evidence: Hermes DB Topic Plan Contract

**Workspace**: `hermes-db-topic-plan-contract` | **Date**: 2026-07-01  
**Mode**: local unit/SQL/schema verification; no live Postgres migration execution and no agents repo smoke in this pass.

---

## Evidence Summary

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| `topic_plans` is first-class storage with constraints and indexes | Added Alembic migration `0010_topic_plan_contracts.py` with `hermes.topic_plans`, candidate/topic FKs, unique candidate plan, status/shape checks, and listing indexes. | `tests/test_migration_sql.py::test_topic_plan_contracts_migration_contains_required_schema_changes` | PASS |
| Health exposes `topic_plans` capability | Added `inspect_topic_plan_schema` and merged `topic_plans` into health capabilities. | `tests/test_topic_plan_schema_health.py`; `tests/test_health.py` | PASS |
| Repository supports idempotent upsert and candidate shortlist transaction | Added `topic_plan_repo.upsert_topic_plan` with `ON CONFLICT(candidate_id)` and same-transaction candidate shortlist update for planned status. | `tests/test_topic_plan_repo_sql.py` | PASS |
| Repository supports list/get/status lifecycle | Added `list_topic_plans`, `get_topic_plan`, and `update_topic_plan_status`. | `tests/test_topic_plan_repo_sql.py` | PASS |
| MCP tools expose TopicPlan contract | Added `tools/topic_plans.py` with upsert/list/get/update tools and registered it in `server.py`. | `tests/test_topic_plan_tools.py`; `server.py` import registration | PASS |
| Candidate raw payload can be fetched only when requested | Extended `get_candidate(..., include_raw=False)` and added `get_topic_candidate(include_raw)` MCP tool. | `tests/test_topic_candidate_repo_sql.py`; `tests/test_topic_candidate_tools.py` | PASS |
| Existing hermes-db behavior is not regressed | Full hermes-db test suite passed. | `rtk uv run pytest` from `packages/hermes-db` -> 383 passed, 23 skipped | PASS |

---

## Commands Run

| Command | Result |
|---|---|
| `rtk uv run pytest tests/test_migration_sql.py tests/test_topic_candidate_repo_sql.py tests/test_topic_candidate_tools.py tests/test_topic_plan_repo_sql.py tests/test_topic_plan_tools.py tests/test_topic_plan_schema_health.py tests/test_health.py` | PASS: 47 passed |
| `rtk uv run pytest` | PASS: 383 passed, 23 skipped |

---

## Workflow Replay

1. Migration contract is text-checked before runtime use.
2. Schema inspector proves health can expose `topic_plans` only when required columns, constraints, and indexes exist.
3. Repository tests prove the persistence and lifecycle SQL shape, including idempotent candidate upsert and planned-status shortlist coupling.
4. Tool tests prove agents-facing validation and DTO serialization.
5. Candidate raw read remains hidden by default and explicit through `include_raw=true`.

---

## Remaining Risks

| Risk | Status | Follow-up |
|---|---|---|
| Live Postgres migration not executed in this pass | Accepted local verification gap | Run deployment/preflight migration check before release |
| agents-side topic planning smoke not run | Accepted downstream integration gap | Use this MCP contract from agents after deployment |
| SQL tests use fake connections, not a real DB | Existing repo pattern | Optional integration test can be added if live test DB becomes standard |

---

## Verdict

**Overall**: PASS

The feature meets local component capability and MCP contract verification. External deployment and agents smoke remain follow-up evidence, not blockers for this repository feature implementation.
