# Task Plan: MCP Versioned Release Automation

## Goal

Implement tag-driven CI/CD for `mcps`:

- Git tag format: `<service>-vX.Y.Z`
- Build image in GitHub Actions
- Push `ghcr.io/northseacoder/<image>:vX.Y.Z`
- Deploy the exact version from a NAS self-hosted runner

## Phases

- [x] Confirm existing deployment layout and current NAS behavior
- [x] Add a service manifest and release tag resolver
- [x] Add GitHub Actions workflow for build/push/deploy
- [x] Add NAS deploy helper script
- [x] Update deployment docs
- [x] Run static validation and commit

## Decisions

- NAS uses version tags only, not `latest`, `main`, or sha tags.
- Service-level Git tags are used because this is a monorepo: `hermes-db-v0.1.1`.
- GitHub-hosted runners build and push images; NAS self-hosted runner only pulls and restarts services.
- First supported service is `hermes-db`; the manifest is structured for more MCP services later.

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| Previous NAS build stalled during `pip install uv` | Direct build on NAS | Abandoned; CI/CD will build on GitHub instead |
| Local compose config needs `deploy/nas.local.env` | `docker compose config` | Skipped locally because this private file is intentionally gitignored |
