# Progress: MCP Release Automation

## 2026-05-29

- Confirmed user decision: NAS deploys concrete version tags only.
- Started implementing service-level release workflow with tag format `<service>-vX.Y.Z`.
- Working tree was clean before changes.
- Added service manifest, release resolver, NAS deploy script, workflow, and docs.
- Static checks passed: release resolver, shell syntax, workflow YAML parse.
- Compose config check was not run to completion locally because `deploy/nas.local.env` is intentionally gitignored and absent.
- `git diff --check` passed.
