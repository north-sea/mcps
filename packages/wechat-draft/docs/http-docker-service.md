# WeChat Draft HTTP MCP Service

本服务以 Docker 容器运行 Streamable HTTP MCP，只暴露：

- `POST /mcp`: MCP tool endpoint，可选 Bearer token 认证
- `GET /health` / `HEAD /health`: 容器健康检查，不需要认证

旧 `stdio` 入口仍保留为迁移兜底，但 Docker 服务只启动 `dist/http-index.js`。

## Release Deployment

正式部署沿用 `hermes-db` 的平台发布链路：打服务级 Git tag，GitHub Actions 构建并推送 GHCR 镜像，NAS self-hosted runner 拉取精确版本并重启 compose service。

```bash
git tag wechat-draft-v0.2.1
git push origin wechat-draft-v0.2.1
```

发布镜像：

```text
ghcr.io/north-sea/wechat-draft-mcp:v0.2.1
```

发布参数登记在 `deploy/mcp-services.json`，NAS 公共 compose 模板在 `deploy/services/wechat-draft.yml`。本包目录内的 `docker-compose.example.yml` 只用于本地或手工 smoke。

## Local Build

从仓库根目录构建：

```bash
docker build -f packages/wechat-draft/Dockerfile -t wechat-draft-mcp:local .
```

也可以在包目录运行：

```bash
pnpm --filter @mcps/wechat-draft docker:build
```

Dockerfile 使用 workspace lockfile 构建，不能把 `packages/wechat-draft` 作为单独 build context。正式发布不要在 NAS 上构建镜像。

## Local Run With Compose

```bash
cd packages/wechat-draft
cp .env.nas.example .env
docker compose --env-file .env -f docker-compose.example.yml up -d --build
```

`docker-compose.example.yml` 会挂载：

- `./config/accounts.yaml` -> `/app/config/accounts.yaml:ro`
- `wechat-draft-data` -> `/app/data`
- `/app/data/assets` 作为 `local_path` 资产根目录

## Environment

| 变量 | 说明 |
|---|---|
| `WECHAT_DRAFT_AUTH_TOKEN` | `POST /mcp` Bearer token。为空则不强制认证 |
| `HERMES_DB_BASE_URL` | hermes-db HTTP MCP 服务地址 |
| `HERMES_DB_AUTH_TOKEN` | hermes-db Bearer token |
| `WECHAT_ADAPTER_BASE_URL` | WeChat adapter HTTP 地址 |
| `WECHAT_ADAPTER_AUTH_TOKEN` | WeChat adapter token |
| `WECHAT_DRAFT_CONFIG_PATH` | 容器内账号配置路径，推荐 `/app/config/accounts.yaml` |
| `WECHAT_DRAFT_RUNTIME_PATH` | runtime 目录，推荐 `/app/data` |
| `DATABASE_PATH` | SQLite job store，推荐 `/app/data/jobs.db` |
| `ASSET_ROOT` | `wechat_upload_asset(local_path)` 允许读取的根目录 |
| `PORT` | HTTP 监听端口，默认 `3001` |
| `WECHAT_DRAFT_HTTP_BIND` | Docker 宿主机端口绑定，NAS 默认 `3012` |

挂载外部 `accounts.yaml` 时，账号清单来自 YAML；`WECHAT_ADAPTER_BASE_URL`、
`WECHAT_ADAPTER_AUTH_REF`、`HERMES_DB_BASE_URL` 仍会覆盖 YAML 中的 endpoint 设置，
便于 Docker/NAS 环境通过 `.env` 切换下游服务。

## Client Config

本机 Claude Code：

```json
{
  "mcpServers": {
    "wechat-draft": {
      "url": "http://nas.local:3012/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_WECHAT_DRAFT_MCP_TOKEN_HERE"
      }
    }
  }
}
```

本机 Codex：

```json
{
  "mcpServers": {
    "wechat-draft": {
      "url": "http://nas.local:3012/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_WECHAT_DRAFT_MCP_TOKEN_HERE"
      }
    }
  }
}
```

NAS Hermes：

```yaml
mcp_servers:
  wechat-draft:
    url: http://wechat-draft-mcp:3001/mcp
    headers:
      Authorization: Bearer YOUR_WECHAT_DRAFT_MCP_TOKEN_HERE
    enabled: true
    timeout: 60
```

## Health Check

```bash
curl http://127.0.0.1:3012/health
```

本地 runtime/config/SQLite 不可用时返回 `503`。adapter 或 hermes-db 暂时不可达时返回 `200` + `status:"degraded"`，避免容器被反复重启。

## Asset Paths

HTTP MCP 场景下，`local_path` 表示服务容器内路径，不是调用方本机路径。推荐优先使用 `remote_url`；如必须使用 `local_path`，把文件放入挂载到 `/app/data/assets` 的目录，并传相对路径或该目录下的绝对路径。
