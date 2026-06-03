# Acceptance Record: hermes-db WeChat Publication Ledger

**Feature**: `hermes-db-wechat-publication-ledger`  
**Date**: 2026-06-03  
**Status**: Implemented locally; NAS PG migrated; runtime deployment pending

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
| NAS runtime image | PENDING | Current `hermes-db-mcp` container still runs `ghcr.io/north-sea/hermes-db-mcp:v0.2.9` and does not include revision `0003` or article tools |
| NAS MCP endpoint tools smoke | PENDING | Requires new image deployment; `/mcp` health and `tools/list` should be verified after deployment |

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
| NAS runtime not updated | Open: DB is migrated to `0003`, but current v0.2.9 container cannot resolve that revision via its bundled migrations. Deploy a new image before running container-local Alembic commands. |
| Downstream agents integration | Open; agents repo adapter/service is out of scope for this feature. |
| External ref uniqueness conflict mapping | Covered at tool/repository unit level; real PG unique violation still needs endpoint/integration smoke. |

---

## Release / Deployment Follow-up

- Build and deploy a new `hermes-db-mcp` image containing revision `0003_wechat_publication_ledger`.
- Verify `/mcp` health includes `schema_revision=0003_wechat_publication_ledger` and `capabilities.wechat_publication_ledger=true`.
- Verify `tools/list` includes the four article tools.
- Run one endpoint-level upsert/list/get/update refs smoke against local or NAS MCP endpoint.
