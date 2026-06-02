# Acceptance Record: hermes-db topic bucket & revisit_of

**Feature**: `hermes-db-topic-bucket-revisit`  
**Date**: 2026-06-01  
**Status**: Released to NAS

---

## Verification Evidence

| Check | Result | Evidence |
|---|---|---|
| Full unit/integration test suite | PASS | `uv run pytest -q` -> 115 passed, 19 skipped |
| Ruff static check | PASS | `uv run ruff check .` -> All checks passed |
| Alembic SQL generation | PASS | `uv run alembic upgrade head --sql` generated `0001_topic_revisit` SQL |
| Whitespace check | PASS | `git diff --check` produced no output |
| Release manifest resolution | PASS | `node scripts/resolve-mcp-release.mjs hermes-db-v0.2.6` resolved migration entrypoint `alembic`, command `upgrade head`, and MCP health smoke capabilities |
| Release image immutability gate | PASS | `v0.2.0` and `v0.2.1` were rejected because their GHCR image tags already exist; `docker buildx imagetools inspect` also found `v0.2.2` occupied; `v0.2.3` built successfully but NAS pull was denied before deploy; `v0.2.4` pulled but migration failed because `PG_DSN` used non-owner `hermes_user`; `v0.2.5` deployed and migrated but smoke raced startup, so release was bumped to `v0.2.6` with health smoke retry |
| GitHub Actions release | PASS | `MCP Release` run `26796453419` completed successfully for `hermes-db-v0.2.6` |
| NAS runtime image | PASS | `hermes-db-mcp` is running `ghcr.io/northseacoder/hermes-db-mcp:v0.2.6` |
| NAS MCP health | PASS | `/mcp` health returned `version=0.2.6`, `schema_revision=0001_topic_revisit`, `pg=ok`, and required capabilities enabled |
| NAS DB schema | PASS | `alembic_version=0001_topic_revisit`; `hermes.topics` has `mother_theme`, `revisit_of`, `chk_topics_revisit_of_not_self`, and `fk_topics_revisit_of` |
| Deploy script syntax | PASS | `bash -n scripts/nas-deploy-mcp.sh` and workflow deploy shell body parsed successfully |
| NAS baseline health | PASS | Pre-release NAS `hermes-db-mcp` was `v0.1.13` with `pg=ok`, `redis=ok`, and no `version/schema_revision/capabilities` yet |
| Local Docker build | BLOCKED | Build reached Docker Hub metadata resolution, then `python:3.12-slim` timed out; Dockerfile still covered by release workflow build |
| Dirty generated artifacts | PASS | `.pytest_cache`, `.ruff_cache`, `.venv`, `dist`, `__pycache__`, `uv.lock` are ignored and not in `git status --short` |
| Dead-code scan | PASS | Only expected cache exception `pass` blocks and test no-op mocks found |

---

## Reviewed Risks

| Risk | Verdict |
|---|---|
| Migration bound to service startup | Mitigated: Docker `ENTRYPOINT` remains `hermes-db-mcp`; migration is documented as explicit release step |
| `revisit_of` self-reference | Mitigated: tool-layer self-check plus DB `chk_topics_revisit_of_not_self` |
| FK idempotency | Mitigated: migration checks `pg_constraint` before adding `fk_topics_revisit_of` |
| UUID serialization | Mitigated: `id` / `revisit_of` conversion skips null values in cache and tool responses |
| bucket threshold drift | Mitigated: thresholds live in server config fields |
| capabilities false positive | Mitigated: `health` now derives capabilities from DB schema and exposes `schema_revision` |
| deploy health too shallow | Mitigated in code/config and verified in release: deploy manifest declares release migration plus MCP health smoke with retry/backoff |
| migration DB privileges | Mitigated: Alembic now prefers `MIGRATION_PG_DSN`, so release migration can use a schema-owner role while the service keeps `PG_DSN` as the app role |
| HTTP auth diagnostics | Mitigated: 401 responses include `WWW-Authenticate: Bearer realm="hermes-db"` |
| inspiration tool annotations / error shape drift | Mitigated: inspiration tools now carry read/write annotations and use shared `ToolError` helper for common failures |

---

## Release Evidence

- Target environment release completed for `hermes-db-v0.2.6`.
- `docker compose` pulled `ghcr.io/northseacoder/hermes-db-mcp:v0.2.6`, ran `alembic upgrade head`, recreated `hermes-db-mcp`, and workflow health smoke passed.
- Runtime verification confirmed `health().version == "0.2.6"`, `health().schema_revision == "0001_topic_revisit"`, and `capabilities.topic_bucket/topic_revisit_of/list_revisit_chain == true`.
- DB verification confirmed `revisit_of`, `mother_theme`, `fk_topics_revisit_of`, and `chk_topics_revisit_of_not_self`.
