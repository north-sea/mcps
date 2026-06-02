#!/usr/bin/env bash
set -euo pipefail

required_vars=(
  SERVICE_NAME
  VERSION
  IMAGE
  COMPOSE_PROJECT_DIR
  COMPOSE_FILE
  COMPOSE_SERVICE
  CONTAINER_NAME
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required env var: ${var_name}" >&2
    exit 2
  fi
done

image_ref="${IMAGE}:${VERSION}"
override_file=".mcps-release.override.yml"
migration_command="${MIGRATION_COMMAND:-}"
migration_entrypoint="${MIGRATION_ENTRYPOINT:-}"
smoke_url="${SMOKE_URL:-}"
smoke_token_env="${SMOKE_TOKEN_ENV:-}"
smoke_capabilities="${SMOKE_CAPABILITIES:-}"

cd "${COMPOSE_PROJECT_DIR}"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "Compose file not found: ${COMPOSE_PROJECT_DIR}/${COMPOSE_FILE}" >&2
  exit 1
fi

cat > "${override_file}" <<EOF
services:
  ${COMPOSE_SERVICE}:
    image: ${image_ref}
EOF

echo "Deploying ${SERVICE_NAME} ${VERSION} from ${image_ref}"
docker compose -f "${COMPOSE_FILE}" -f "${override_file}" pull "${COMPOSE_SERVICE}"

if [[ -n "${migration_command}" ]]; then
  echo "Running release migration: ${migration_command}"
  if [[ -n "${migration_entrypoint}" ]]; then
    docker compose -f "${COMPOSE_FILE}" -f "${override_file}" run --rm --entrypoint "${migration_entrypoint}" "${COMPOSE_SERVICE}" ${migration_command}
  else
    docker compose -f "${COMPOSE_FILE}" -f "${override_file}" run --rm "${COMPOSE_SERVICE}" ${migration_command}
  fi
fi

docker compose -f "${COMPOSE_FILE}" -f "${override_file}" up -d "${COMPOSE_SERVICE}"

running="$(docker inspect "${CONTAINER_NAME}" --format '{{.State.Running}}')"
actual_image="$(docker inspect "${CONTAINER_NAME}" --format '{{.Config.Image}}')"

if [[ "${running}" != "true" ]]; then
  echo "Container ${CONTAINER_NAME} is not running after deploy" >&2
  docker logs --tail 120 "${CONTAINER_NAME}" >&2 || true
  exit 1
fi

if [[ "${actual_image}" != "${image_ref}" ]]; then
  echo "Container ${CONTAINER_NAME} is running unexpected image: ${actual_image}" >&2
  echo "Expected: ${image_ref}" >&2
  exit 1
fi

if [[ -n "${smoke_url}" ]]; then
  token=""
  if [[ -n "${smoke_token_env}" ]]; then
    token="${!smoke_token_env:-}"
    if [[ -z "${token}" ]]; then
      token="$(docker inspect "${CONTAINER_NAME}" --format "{{range .Config.Env}}{{println .}}{{end}}" | sed -n "s/^${smoke_token_env}=//p" | head -n 1)"
    fi
    if [[ -z "${token}" ]]; then
      echo "Smoke token env var is empty: ${smoke_token_env}" >&2
      exit 1
    fi
  fi

  echo "Running MCP health smoke: ${smoke_url}"
  python3 - "$smoke_url" "$token" "$smoke_capabilities" <<'PY'
import json
import sys
import urllib.request

url, token, capabilities = sys.argv[1:4]
required = [item for item in capabilities.split(",") if item]
headers = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}
if token:
    headers["Authorization"] = f"Bearer {token}"

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "health",
        "arguments": {},
    },
}
request = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers=headers,
    method="POST",
)
with urllib.request.urlopen(request, timeout=15) as response:
    raw = response.read().decode("utf-8")
data = json.loads(raw)
if "error" in data:
    raise SystemExit(f"MCP health returned error: {data['error']}")

content = data.get("result", {}).get("content", [])
structured = data.get("result", {}).get("structuredContent")
if isinstance(structured, dict):
    health = structured
else:
    if not content:
        raise SystemExit(f"MCP health response missing content: {data}")
    text = content[0].get("text")
    if text is None:
        raise SystemExit(f"MCP health response missing text content: {data}")
    health = json.loads(text)
if health.get("pg") != "ok":
    raise SystemExit(f"PostgreSQL health is not ok: {health.get('pg')}")

capability_map = health.get("capabilities") or {}
missing = [name for name in required if capability_map.get(name) is not True]
if missing:
    raise SystemExit(f"Missing capabilities after deploy: {missing}; health={health}")

print(json.dumps({
    "version": health.get("version"),
    "schema_revision": health.get("schema_revision"),
    "capabilities": capability_map,
}, ensure_ascii=False))
PY
fi

echo "Deployment complete: ${CONTAINER_NAME} -> ${actual_image}"
