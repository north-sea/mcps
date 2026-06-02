# Progress: MCP Release Automation

## 2026-05-29

- Confirmed user decision: NAS deploys concrete version tags only.
- Started implementing service-level release workflow with tag format `<service>-vX.Y.Z`.
- Working tree was clean before changes.
- Added service manifest, release resolver, NAS deploy script, workflow, and docs.
- Static checks passed: release resolver, shell syntax, workflow YAML parse.
- Compose config check was not run to completion locally because `deploy/nas.local.env` is intentionally gitignored and absent.
- `git diff --check` passed.

## 2026-06-02

- Started fixing hermes-db embedding compatibility after new-api returned 400 for requests with `dimensions`.
- Error encountered: `rtk rg ... docker* compose* .env*` failed in zsh with `no matches found`; reran search with explicit paths.
- Error encountered: Codex `apply_patch` failed because sandbox helper points to a missing binary under fnm node v22.22.2; switched to `git apply`/`diff -u` for patch-style edits.
- Error encountered: initial hand-written `git apply` patches had invalid hunk counts; generated standard diffs instead.
- Related tests passed: `uv run pytest tests/test_embedding.py tests/test_health.py`.
- Full hermes-db test suite passed: `uv run pytest` (`119 passed, 19 skipped`).
