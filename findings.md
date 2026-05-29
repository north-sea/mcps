# Findings: MCP Release Automation

## Repository State

- `deploy/services/hermes-db.yml` already defines image `${REGISTRY:-ghcr.io/northseacoder}/hermes-db-mcp:${TAG:-latest}`.
- No `.github/workflows` directory exists, so pushes currently do not build or publish images.
- Existing docs describe `build -> tag -> push -> NAS pull -> run`, but the automation is missing.

## NAS State

- Current `hermes-db-mcp` container uses image `ghcr.io/northseacoder/hermes-db-mcp:latest`.
- Runtime env already includes `TRANSPORT=streamable-http`.
- Existing NAS compose lives at `/vol1/1000/Docker/hermes-db-mcp/docker-compose.yml` and uses `.env`.

