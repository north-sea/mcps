# Feature Specification: WeChat Draft MCP Service (Streamable HTTP)

**Workspace**: `wechat-draft-http-service`
**Created**: 2026-06-26
**Status**: Draft
**Input**: 用户描述: "把现有 wechat-draft stdio MCP 重构为 Docker 化的 Streamable HTTP MCP 服务，参考 hermes-db 架构"

> 本 feature 把现有 stdio MCP 重构为服务型 MCP（Streamable HTTP transport），解决本机和 NAS 都要 fork 子进程、管理 node_modules、配置路径的问题。统一部署为 Docker 容器，所有 agent 通过 HTTP 调用同一 MCP endpoint。

---

## Feature Traits *(LM 自动检测，用户可 override)*

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ❌ | 虽有草稿创建的多步骤工作流，但该流程已封装在 DraftWorkflow 中，本 feature 只是传输协议重构，不改变工作流逻辑 |
| `external-side-effects` | ✅ | 调用 ECS adapter → 微信 API，产生外部草稿；调用 hermes-db MCP 写入发布账本 |
| `artifact-handoff` | ✅ | 从 hermes-db 读取 artifact（ProseMirror JSON），渲染为 HTML 后交付微信 API |
| `user-visible-output` | ✅ | 生成微信公众号草稿（media_id），用户在后台可见 |
| `prior-closure-failure` | ❌ | 非修复性工作，是架构重构 |
| `bugfix-loop-breaker` | ❌ | 非 bugfix，是新架构迁移 |

**结论**: 本 feature 命中 `external-side-effects`、`artifact-handoff`、`user-visible-output` 三项。下游阶段需强化：
- **Plan**: 明确外部调用的重试、幂等性、错误传播策略
- **Verify**: 端到端测试需覆盖 ECS adapter + hermes-db 的集成路径，验证 artifact 渲染正确性

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 本机 AI 客户端通过 HTTP MCP 调用工具 (Priority: P0)

**作为** 本机 Claude Code/Codex 用户
**我希望** 通过统一的 HTTP MCP endpoint 调用 wechat-draft 工具
**以便** 无需在本机安装 Node.js 依赖、管理 stdio 子进程和路径配置

**Why this priority**: 核心迁移路径，解决本机部署痛点

**Acceptance Scenarios**:

1. **[US1-1] 成功调用 MCP tool**
   **Given** 本机 Claude Code 配置 `mcpServers.wechat-draft.url = "http://nas.local:3012/mcp"`，NAS 上 wechat-draft-mcp 容器运行中
   **When** agent 调用 `wechat_create_draft(account="xiaban", artifact_id="art_123")`
   **Then** MCP tool 返回 `{success:true, data:{media_id:"draft_xxx", created_at:"..."}}` 且微信后台草稿箱可见

2. **[US1-2] 幂等性保证**
   **Given** 已创建 media_id=draft_xxx 的草稿（idempotency_key=idem_123）
   **When** 7 天内用相同 idempotency_key 调用 `wechat_create_draft`
   **Then** 返回已有 draft_xxx，SQLite UNIQUE 约束防止重复创建

**Edge Cases**:

- **[US1-3]** 同一 idempotency_key 并发调用时，只允许一个请求创建 job；后续请求返回已有 job 当前状态（如 `draft_creating` 或 `saved`），不等待、不重复调用微信 API
- **[US1-4]** adapter 不可达时，tool 返回 `{success:false, error:{code:"adapter_unreachable", message:"..."}}`
- **[US1-5]** artifact 不存在时，tool 返回 `{success:false, error:{code:"artifact_not_found"}}`
- **[US1-6]** 封面图片超过 64KB 时，tool 返回 `{success:false, error:{code:"asset_size_exceeded", details:"..."}}`

### User Story 2 - NAS Hermes Agent 通过容器内 HTTP MCP 调用 (Priority: P0)

**作为** NAS 上的 Hermes Agent
**我希望** 在容器内通过 localhost MCP endpoint 调用工具
**以便** 无需在 Hermes 容器内安装 Node.js 和 wechat-draft 依赖

**Why this priority**: NAS 部署的主要痛点解决方案

**Acceptance Scenarios**:

1. **[US2-1] 容器间 MCP 调用成功**
   **Given** Hermes 配置 `mcp_servers.wechat-draft.url = "http://wechat-draft-mcp:3001/mcp"`，两容器在同一 Docker 网络
   **When** Hermes 调用 `wechat_list_accounts()`
   **Then** 返回 `{success:true, data:{accounts:[{account_id:"xiaban",...}, ...]}}`

2. **[US2-2] Bearer token 认证**
   **Given** 服务配置了 `AUTH_TOKEN=secret`，Hermes 配置 `headers: {Authorization: "Bearer secret"}`
   **When** 不带 Authorization 头请求 `POST /mcp`
   **Then** 返回 401 Unauthorized

**Edge Cases**:

- **[US2-3]** 服务启动时 hermes-db 不可达，healthcheck 返回 `{"checks":{"hermes_db_reachable":false}}` 但服务不退出
- **[US2-4]** 服务启动时 ECS adapter 不可达，healthcheck 返回 `{"checks":{"adapter_reachable":false}}` 但服务不退出

### User Story 3 - 运维人员通过健康检查监控服务状态 (Priority: P1)

**作为** 运维人员
**我希望** 通过 `/health` 端点快速判断服务及其依赖的状态
**以便** 发现问题时快速定位（adapter 故障 vs hermes-db 故障 vs 服务本身）

**Why this priority**: 运维可观测性需求

**Acceptance Scenarios**:

1. **[US3-1] 容器健康检查**
   **Given** wechat-draft-mcp 容器运行中，所有依赖可达
   **When** Docker 执行 healthcheck（使用容器内 Node fetch 调用 `http://127.0.0.1:3001/health`）
   **Then** 返回 200，`{"status":"ok","version":"0.2.1","checks":{"runtime_writable":true,"config_loaded":true,"adapter_reachable":true,"hermes_db_reachable":true}}`

2. **[US3-2] 部分依赖故障**
   **Given** adapter 不可达
   **When** `GET /health`
   **Then** 返回 200（服务本身可运行，不触发容器重启），`{"status":"degraded","checks":{"adapter_reachable":false,"error":"..."}}`

**Edge Cases**:

- **[US3-3]** `HEAD /health` 快速探测，服务自身可运行时返回 200；runtime/config/数据库文件不可用时返回 503，无 body
- **[US3-4]** runtime 目录不可写时，`{"checks":{"runtime_writable":false,"path":"/app/data"}}`

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 服务必须实现 MCP Streamable HTTP transport，暴露端点 `POST /mcp`
- **FR-002**: 服务必须注册 5 个 MCP tools：`wechat_list_accounts`、`wechat_upload_asset`、`wechat_validate_publish_artifact`、`wechat_create_draft`、`wechat_get_draft_status`
- **FR-003**: 服务必须支持 `GET /health` 和 `HEAD /health` 健康检查（不需要认证）
- **FR-004**: 服务必须支持 Bearer token 认证（通过 `Authorization: Bearer` 头，token 来自环境变量 `AUTH_TOKEN`）
- **FR-005**: 服务必须复用现有 `WechatAdapterClient`、`HermesDbClient`、`DraftWorkflow` 业务逻辑
- **FR-006**: 服务必须实现 7 天幂等窗口（idempotency_key + account + SQLite UNIQUE 约束；事务内清理过期记录后再创建 job）
- **FR-007**: `/health` 端点不得触发副作用（不直接调用 adapter/hermes-db，只读取后台 probe 刷新的连通性缓存）
- **FR-008**: `wechat_upload_asset` 在 HTTP MCP 场景下不得默认暴露调用方本机 `local_path`；MVP 支持 `remote_url` 和服务容器内已挂载路径，推荐通过 artifact/remote URL 传递资产

### Non-Functional Requirements

- **NFR-001**: 服务启动时间 ≤ 5s（不含依赖服务的等待）
- **NFR-002**: 单个草稿创建请求延迟 ≤ 10s（P95，不含微信 API 响应时间）
- **NFR-003**: 支持至少 10 并发请求（受 ECS adapter 限制，单实例足够）
- **NFR-004**: 服务重启不丢失 7 天内的幂等性记录（SQLite 持久化，记录 `idempotency_expires_at`）

### Transport Design

- **协议**: MCP Streamable HTTP (JSON-RPC 2.0 over HTTP)
- **端点**: `POST /mcp`
- **实现**: `@modelcontextprotocol/sdk` 的 `StreamableHTTPServerTransport`
- **服务器**: Express 作为 thin HTTP host
- **状态**: Stateless transport；业务状态由 JobStore (SQLite) 持久化

### Technology Stack (Finalized)

| 组件 | 选型 | 说明 |
|------|------|------|
| **语言** | TypeScript | 复用现有业务逻辑，开发周期短 |
| **MCP SDK** | `@modelcontextprotocol/sdk` 稳定 1.x | 官方 TypeScript SDK；实现前锁定最新稳定 minor |
| **HTTP 服务器** | Express 稳定版 | MCP SDK 官方适配路径；仅作为 thin HTTP host |
| **Schema 验证** | Zod v4 优先 | 跟随 MCP SDK 当前示例；如迁移成本过高再保留 v3 |
| **HTTP 客户端** | Node.js 内置 `fetch` | adapter/hermes-db 调用 |
| **日志** | pino + pino-http 稳定版 | 结构化 JSON 日志；版本由 lockfile 固定 |
| **存储** | better-sqlite3 稳定版 | 同步 SQLite，幂等性 + job 状态；版本由 lockfile 固定 |

### Storage Design

- **引擎**: SQLite (单文件数据库 `/app/data/jobs.db`)
- **Schema**:
  ```sql
  CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    account TEXT NOT NULL,
    status TEXT NOT NULL,
    media_id TEXT,
    idempotency_key TEXT NOT NULL,
    idempotency_expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    error_code TEXT,
    error_message TEXT,
    error_details TEXT,
    UNIQUE(account, idempotency_key)  -- 7 天窗口内的幂等性约束
  );
  CREATE INDEX idx_artifact ON jobs(artifact_id);
  CREATE INDEX idx_created_at ON jobs(created_at);
  CREATE INDEX idx_idempotency_expires_at ON jobs(idempotency_expires_at);
  ```
- **幂等创建流程**:
  1. 开启 `BEGIN IMMEDIATE` 事务
  2. 删除 `idempotency_expires_at <= datetime('now')` 的过期 job
  3. 尝试插入 `queued` job，`idempotency_expires_at = datetime('now', '+7 days')`
  4. 如触发 `UNIQUE(account, idempotency_key)` 冲突，查询并返回已有 job
  5. 提交事务后，只有新建 job 才继续执行微信草稿创建流程
- **并发语义**: 同一 `account + idempotency_key` 的并发调用不等待完成；冲突请求返回已有 job 当前状态（如 `queued`、`draft_creating`、`saved`、`failed`）
- **7 天窗口**: 通过 `idempotency_expires_at` 和事务内过期清理实现；过期后相同 key 可再次创建新 job

### Authentication

- **`POST /mcp`**: 必须携带 `Authorization: Bearer <token>`（token 通过环境变量 `AUTH_TOKEN` 配置）
- **`GET /health` / `HEAD /health`**: 不需要认证（返回非敏感状态摘要）
- **无 token 配置**: 如果 `AUTH_TOKEN` 为空，`/mcp` 也不强制认证（NAS 内网部署场景）

**示例配置**（客户端）：
```json
{
  "mcpServers": {
    "wechat-draft": {
      "url": "http://nas.local:3012/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### Health Design

- **本地检查（请求内同步执行）**: process alive、config loaded、runtime writable、SQLite database readable/writable
- **外部依赖检查（后台刷新）**: adapter reachable、hermes-db reachable
- **刷新频率**: 服务启动后立即执行一次 probe；之后后台 probe 默认每 30s 刷新一次连通性缓存（可通过 `HEALTH_PROBE_INTERVAL_MS` 调整）
- **响应状态码**:
  - 本地检查失败（配置缺失、runtime 不可写、SQLite 不可用）: `503`
  - 本地检查通过但外部依赖不可达: `200` + `status:"degraded"`
  - 全部检查通过: `200` + `status:"ok"`
- **安全要求**: `/health` 不返回 token、完整 URL query、请求头或其他敏感信息；错误信息需截断到可诊断但不泄密

### Asset Source Semantics

- **推荐路径**: `wechat_upload_asset` 优先使用 `remote_url` 或 artifact 中持久化的 asset reference，保证本机 agent 和 NAS agent 语义一致
- **`local_path` 限制**: 如保留 `local_path`，它只表示服务容器内路径，不表示调用方本机路径
- **安全边界**: `local_path` 必须限制在 `ASSET_ROOT`（默认 `/app/data/assets`）之下，禁止读取任意容器文件路径
- **验证要求**: 继续执行图片大小、MIME、扩展名和 WeChat usage 约束；封面超过 64KB 返回 `asset_size_exceeded`

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 可部署性 | Docker 镜像 ≤ 150MB，冷启动 ≤ 10s | NAS 资源受限，需轻量镜像 | `docker images` + 启动日志 | 否（实现阶段优化） |
| 可观测性 | 结构化日志（pino），健康检查覆盖所有依赖 | 运维需快速定位故障 | 日志示例 + healthcheck 测试 | 是（plan 需设计日志格式） |
| 向后兼容性 | 旧 stdio 入口和新 HTTP 服务可并行运行 7 天过渡期 | 平滑迁移，降低风险 | 本机保留旧 stdio 配置，NAS 先试 HTTP；不是同一服务双协议 | 否（部署策略） |

### Key Entities

- **Draft Job**: `{job_id, artifact_id, account, status, media_id?, idempotency_key, idempotency_expires_at, created_at, updated_at, error_code?, error_message?}`
- **Account Config**: `{account_id, display_name, adapter_id, enabled}` (来自 accounts.yaml)
- **Asset Upload Result**: `{wechat_url?, thumb_media_id?, usage, size_bytes, mime_type}`

---

## Deployment *(mandatory)*

### Package Scope

- **实现位置**: 就地重构 `packages/wechat-draft`
- **旧入口**: 现有 stdio entrypoint 可保留为迁移前旧入口，但本 feature 的 Docker 服务只启动 Streamable HTTP MCP
- **新入口**: 新增 HTTP service entrypoint（例如 `dist/http-index.js` 或等价命名），Docker 镜像只运行该入口

### Docker Compose

正式部署应沿用 `hermes-db` 的平台发布链路：推送 `wechat-draft-vX.Y.Z` tag 触发 `.github/workflows/mcp-release.yml`，GitHub Actions 构建并推送 `ghcr.io/north-sea/wechat-draft-mcp:<version>`，NAS self-hosted runner 只拉取精确版本镜像并重启 compose service。NAS 不在本机临时构建镜像，不使用 `latest` 作为运行态版本。

本地 smoke 可使用包内 compose 示例：

```yaml
services:
  wechat-draft-mcp:
    image: ghcr.io/north-sea/wechat-draft-mcp:v0.2.1
    container_name: wechat-draft-mcp
    restart: unless-stopped
    ports:
      - "3012:3001"
    environment:
      - PORT=3001
      - AUTH_TOKEN=${WECHAT_DRAFT_AUTH_TOKEN}
      - HERMES_DB_BASE_URL=http://hermes-db-mcp:8080
      - HERMES_DB_AUTH_TOKEN=${HERMES_DB_AUTH_TOKEN}
      - WECHAT_ADAPTER_BASE_URL=http://100.117.14.128:3000
      - WECHAT_ADAPTER_AUTH_TOKEN=${WECHAT_ADAPTER_AUTH_TOKEN}
      - WECHAT_DRAFT_CONFIG_PATH=/app/config/accounts.yaml
      - DATABASE_PATH=/app/data/jobs.db
      - ASSET_ROOT=/app/data/assets
      - HEALTH_PROBE_INTERVAL_MS=30000
      - NODE_ENV=production
      - LOG_LEVEL=info
    volumes:
      - wechat-draft-data:/app/data
      - ./packages/wechat-draft/config/accounts.yaml:/app/config/accounts.yaml:ro
    healthcheck:
      test: ["CMD-SHELL", "node -e \"fetch('http://127.0.0.1:3001/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))\""]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s
    networks:
      - hermes

volumes:
  wechat-draft-data:

networks:
  hermes:
    external: true
```

### Client Configuration

**本机 Claude Code** (`~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "wechat-draft": {
      "url": "http://nas.local:3012/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

**本机 Codex** (`~/.codex/mcp.json`):
```json
{
  "mcpServers": {
    "wechat-draft": {
      "url": "http://nas.local:3012/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

**NAS Hermes** (`~/.hermes/config.yaml` 或 `/opt/data/config.yaml`):
```yaml
mcp_servers:
  wechat-draft:
    url: http://wechat-draft-mcp:3001/mcp
    headers:
      Authorization: Bearer YOUR_TOKEN_HERE
    enabled: true
    timeout: 60
```

### Environment Variables

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `AUTH_TOKEN` | 否 | `""` | Bearer token，为空则不强制认证 |
| `HERMES_DB_BASE_URL` | 是 | - | hermes-db MCP HTTP 端点 |
| `HERMES_DB_AUTH_TOKEN` | 是 | - | hermes-db 认证 token |
| `WECHAT_ADAPTER_BASE_URL` | 是 | - | ECS adapter 地址 |
| `WECHAT_ADAPTER_AUTH_TOKEN` | 是 | - | ECS adapter 认证 token |
| `WECHAT_DRAFT_CONFIG_PATH` | 是 | - | 账号配置文件路径（容器内推荐 `/app/config/accounts.yaml`） |
| `DATABASE_PATH` | 否 | `/app/data/jobs.db` | SQLite job store 路径 |
| `ASSET_ROOT` | 否 | `/app/data/assets` | 允许读取的容器内资产根目录 |
| `HEALTH_PROBE_INTERVAL_MS` | 否 | `30000` | 后台外部依赖 health probe 间隔 |
| `NODE_ENV` | 否 | `production` | 环境（development/production） |
| `LOG_LEVEL` | 否 | `info` | 日志级别（trace/debug/info/warn/error） |
| `PORT` | 否 | `3001` | 服务监听端口 |
| `WECHAT_DRAFT_HTTP_BIND` | 否 | `3012` | NAS 宿主机端口绑定，容器内部仍监听 `3001` |

---

## Out of Scope *(mandatory)*

明确不在本次功能范围内的内容：

- **stdio 协议支持**: 不在 Docker MCP 服务中实现 stdio transport
  - 现有 `packages/wechat-draft/` 的 stdio 入口保留为迁移前旧版本
  - 是否删除 stdio 代码作为后续 cleanup task（非本 feature 范围）
- **双协议模式**: 不支持同时暴露 stdio 和 HTTP（服务只提供 HTTP）
- **业务级 SSE/进度推送**: 草稿创建同步返回结果；不额外实现业务进度流。MCP transport 需要的协议能力由 SDK 处理
- **Redis 缓存**: 幂等性检查直接查 SQLite，不引入 Redis
- **多实例部署**: 单实例 Docker 足够（受 ECS adapter 单实例限制）
- **账号管理 API**: `accounts.yaml` 手动维护，不提供增删改接口
- **JSONL 格式**: 旧 JobStore 实现已弃用，迁移到 SQLite

---

## Error Handling *(for reference)*

### MCP Tool 错误格式

MCP tool 返回统一 Result 格式（由 MCP SDK 封装）：

**成功**:
```typescript
{
  content: [{
    type: "text",
    text: JSON.stringify({ success: true, data: {...} })
  }]
}
```

**失败**:
```typescript
{
  isError: true,
  content: [{
    type: "text",
    text: JSON.stringify({
      success: false,
      error: { code: "error_code", message: "...", details?: {...} }
    })
  }]
}
```

### HTTP Transport 错误

| 状态码 | 场景 | 响应 |
|--------|------|------|
| 401 | Missing/invalid Bearer token | `{"error":"unauthorized"}` |
| 405 | Method not allowed (非 POST /mcp) | `{"error":"method_not_allowed","allowed":["POST"]}` |
| 500 | Internal server error | `{"error":"internal_server_error"}` |

### 业务错误码（MCP tool 内部）

| Code | 场景 | HTTP 层不感知 |
|------|------|---------------|
| `adapter_unreachable` | ECS adapter 不可达 | Tool 返回 error |
| `adapter_auth_failed` | Adapter token 无效 | Tool 返回 error |
| `artifact_not_found` | hermes-db 无此 artifact | Tool 返回 error |
| `asset_size_exceeded` | 图片超过对应 usage 的大小限制（cover_image 为 64KB） | Tool 返回 error |
| `wechat_api_error` | 微信 API 返回错误 | Tool 返回 error |

---

## Business Metrics *(optional — 上线后度量)*

> **说明**: 此章节定义上线后才能验证的业务度量指标。开发阶段的需求验证由各 User Story 的 Acceptance Scenarios 覆盖。

- **BM-001**: 迁移完成后 7 天内，stdio MCP 调用次数降至 0（监控 `packages/wechat-draft/` 的 stdio server 启动日志）
- **BM-002**: HTTP MCP 服务 P95 延迟 ≤ 10s（通过 pino 日志聚合）
- **BM-003**: 容器健康检查失败次数 ≤ 1 次/周（监控 Docker healthcheck 状态）

---

## Stage Readiness

- **下一步建议**: `plan`
- **阻塞项**: 无（技术栈已明确为 TypeScript + MCP SDK + Express + SQLite）
