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

echo "Deployment complete: ${CONTAINER_NAME} -> ${actual_image}"
