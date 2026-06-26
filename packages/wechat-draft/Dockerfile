ARG BUILDER_IMAGE=node:22-bookworm
ARG RUNTIME_IMAGE=node:22-bookworm-slim

# Build from the repository root:
# docker build -f packages/wechat-draft/Dockerfile -t wechat-draft-mcp:local .

FROM ${BUILDER_IMAGE} AS builder

WORKDIR /repo

RUN if command -v python3 >/dev/null 2>&1 \
    && command -v make >/dev/null 2>&1 \
    && command -v g++ >/dev/null 2>&1; then \
    :; \
  elif command -v apk >/dev/null 2>&1; then \
    apk add --no-cache python3 make g++; \
  else \
    apt-get update \
    && apt-get install -y --no-install-recommends python3 make g++ \
    && rm -rf /var/lib/apt/lists/*; \
  fi \
  && corepack enable \
  && corepack prepare pnpm@8.6.10 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/wechat-draft ./packages/wechat-draft

RUN pnpm install --filter @mcps/wechat-draft... --frozen-lockfile
RUN pnpm --filter @mcps/wechat-draft build
RUN pnpm --filter @mcps/wechat-draft deploy --prod /app

FROM ${RUNTIME_IMAGE} AS runtime

WORKDIR /app

ENV NODE_ENV=production \
  HOST=0.0.0.0 \
  PORT=3001 \
  WECHAT_DRAFT_RUNTIME_PATH=/app/data \
  DATABASE_PATH=/app/data/jobs.db \
  WECHAT_DRAFT_ASSET_ROOT=/app/data/assets \
  HEALTH_PROBE_INTERVAL_MS=30000

COPY --from=builder /app ./

RUN mkdir -p /app/config /app/data/assets \
  && chown -R node:node /app

USER node

EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "const port=process.env.PORT||3001; fetch('http://127.0.0.1:'+port+'/health').then((r)=>process.exit(r.status===200?0:1)).catch(()=>process.exit(1))"

CMD ["node", "dist/http-index.js"]
