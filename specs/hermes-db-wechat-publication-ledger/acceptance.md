# Acceptance Record: hermes-db WeChat Publication Ledger

**Feature**: `hermes-db-wechat-publication-ledger`  
**Date**: 2026-06-03  
**Status**: Released to NAS

---

## Verification Evidence

| Check | Result | Evidence |
|---|---|---|
| Ruff static check | PASS | `uv run ruff check .` -> All checks passed |
| Publication ledger local tests | PASS | `uv run pytest tests/test_migration_sql.py tests/test_wechat_article_contracts.py tests/test_wechat_article_repo_sql.py tests/test_wechat_article_tools.py tests/test_wechat_article_schema_health.py tests/test_wechat_article_integration.py -q` -> 26 passed, 1 skipped |
| Full hermes-db test suite | PASS | `uv run pytest tests -q` -> 158 passed, 21 skipped |
| Real DB publication ledger integration | PASS | Via SSH tunnel to NAS `shared-postgres`, `DATABASE_URL=<NAS tunnel DSN> uv run pytest tests/test_wechat_article_integration.py -q` -> 1 passed |
| NAS PG migration | PASS | Via SSH tunnel to NAS `shared-postgres`, `alembic upgrade head` ran `0002_wechat_workflow_artifacts -> 0003_wechat_publication_ledger` |
| NAS PG revision | PASS | Local Alembic against NAS PG reports `0003_wechat_publication_ledger (head)` |
| GitHub Actions release | PASS | `MCP Release` run `26899394356` completed successfully for `hermes-db-v0.2.10` |
| NAS runtime image | PASS | `hermes-db-mcp` is running `ghcr.io/north-sea/hermes-db-mcp:v0.2.10` |
| NAS runtime schema | PASS | Container `alembic current` reports `0003_wechat_publication_ledger (head)` |
| NAS MCP health | PASS | `/mcp` health returned `version=0.2.10`, `schema_revision=0003_wechat_publication_ledger`, `pg=ok`, `redis=ok`, `embedding=ok`, and all required capabilities true |
| NAS MCP tools list | PASS | `tools/list` includes `upsert_wechat_article`, `list_wechat_articles`, `get_wechat_article`, `update_wechat_article_external_refs` |
| NAS MCP article endpoint smoke | PASS | Created workflow run/artifacts, upserted article, listed/get article, updated refs, then cleaned smoke rows (`articles=0`, `artifacts=0`, `runs=0`) |

---

## Implemented Scope

- Added Alembic revision `0003_wechat_publication_ledger`.
- Added schema health inspection for `capabilities.wechat_publication_ledger`.
- Added article ledger contracts and validators.
- Added `wechat_article_repo.py` repository layer.
- Added MCP tools:
  - `upsert_wechat_article`
  - `list_wechat_articles`
  - `get_wechat_article`
  - `update_wechat_article_external_refs`
- Registered article tools in `server.register_tools()`.
- Updated hermes-db README and deployment notes.

---

## Reviewed Risks

| Risk | Verdict |
|---|---|
| `pgcrypto` availability for `gen_random_uuid()` | Resolved: NAS migration role cannot create `pgcrypto`; migration no longer depends on extension, and repository code generates UUIDs. |
| Real DB FK behavior | Covered by NAS PG integration test. |
| NAS runtime not updated | Resolved: runtime now uses `ghcr.io/north-sea/hermes-db-mcp:v0.2.10` and bundled migrations resolve `0003`. |
| Downstream agents integration | Open; agents repo adapter/service is out of scope for this feature. |
| External ref uniqueness conflict mapping | Covered at tool/repository unit level; real PG unique violation still needs endpoint/integration smoke. |

---

## Release / Deployment Follow-up

- Continue downstream implementation in `agents/specs/wechat-publication-ledger`.
