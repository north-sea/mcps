# hermes-db-mcp

Hermes 领域级 DB MCP Server — 语义化数据访问工具。

对外暴露领域工具（create_topic / find_similar_topics 等），内部封装 embedding 生成、PG 读写、Redis 缓存、状态机校验。

> 本服务已迁入 `mcps` 平台仓。源码位于 `packages/hermes-db/`，公共部署描述位于 `deploy/services/hermes-db.yml`。本目录内的 `docker-compose.yml` 是服务自带的本地开发样例，NAS 部署沿用平台层 compose。详见 [`docs/hermes-db-deployment.md`](../../docs/hermes-db-deployment.md)。

## 工具列表

| Tool | 说明 |
|------|------|
| `health` | PG/Redis/Embedding 三项探活 |
| `create_topic` | 创建选题（自动 embedding + 缓存） |
| `find_similar_topics` | 语义相似选题检索 |
| `update_topic_status` | 状态流转（内置状态机） |
| `list_topics` | 列表查询（分页 + 过滤） |
| `get_topic` | 单条详情（缓存优先） |
| `create_novel_inspiration` | 创建灵感 |
| `find_similar_inspirations` | 语义相似灵感检索 |
| `list_inspirations` | 灵感列表 |
| `get_inspiration` | 灵感详情 |

## 本地开发（stdio 模式）

```bash
cp .env.example .env
# 编辑 .env 填入真实连接信息
uv sync
uv run hermes-db-mcp
```

## 部署（docker compose + Streamable HTTP 模式）

```bash
cp .env.example .env
# 编辑 .env: TRANSPORT=streamable-http, API_TOKEN, PG_DSN, REDIS_URL, EMBEDDING_*
docker compose up -d
```

Server 在 proxy 网络内监听 `8080` 端口，不映射宿主机端口。

## MCP Client 配置

推荐使用 Streamable HTTP `/mcp` endpoint。服务端使用标准 HTTP `Authorization: Bearer <token>` 认证；不同客户端只是配置字段名不同。

### Codex

Codex 可以直接写静态 header：

```toml
[mcp_servers.hermes-db]
type = "streamable-http"
url = "http://hermes-db-mcp:8080/mcp"
http_headers = { Authorization = "Bearer <token>" }
```

也可以用环境变量承载 token：

```toml
[mcp_servers.hermes-db]
type = "streamable-http"
url = "http://hermes-db-mcp:8080/mcp"
bearer_token_env_var = "HERMES_DB_MCP_TOKEN"
```

### Claude Code

Claude Code 使用 `headers` 字段：

```json
{
  "mcpServers": {
    "hermes-db": {
      "type": "streamable-http",
      "url": "http://hermes-db-mcp:8080/mcp",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```

### SSE legacy

如果仍需要旧 SSE transport，需要显式设置 `TRANSPORT=sse`，并使用 `/sse` endpoint：

```json
{
  "mcpServers": {
    "hermes-db": {
      "url": "http://hermes-db-mcp:8080/sse"
    }
  }
}
```

除非现有客户端只能使用 SSE，否则新配置应优先使用 Streamable HTTP。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PG_DSN` | - | PostgreSQL 连接串 |
| `REDIS_URL` | - | Redis 连接 URL |
| `EMBEDDING_BASE_URL` | - | OpenAI 兼容 embedding API |
| `EMBEDDING_API_KEY` | - | API Key |
| `EMBEDDING_MODEL` | text-embedding-v3 | 模型名 |
| `EMBEDDING_DIMENSION` | 1024 | 向量维度 |
| `TRANSPORT` | stdio | stdio、sse 或 streamable-http |
| `API_TOKEN` | - | HTTP/SSE bearer token；为空时不启用认证，生产环境必须配置 |
