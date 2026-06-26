# Implementation Plan: WeChat Draft MCP Service (Streamable HTTP)

**Workspace**: `wechat-draft-http-service` | **Date**: 2026-06-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/wechat-draft-http-service/spec.md`

---

## Summary

把现有 `packages/wechat-draft` 从 stdio-only MCP 重构为 Docker 化 Streamable HTTP MCP 服务。本次采用官方 MCP TypeScript SDK + thin Express host + service layer + SQLite job store，保留现有草稿业务能力，同时清理 transport 和业务逻辑耦合。

---

## Architecture Overview

```text
Local Agent / NAS Agent
        |
        | MCP Streamable HTTP
        v
POST /mcp  +  GET/HEAD /health
Express thin host
        |
        v
MCP tool registry
        |
        v
WechatDraftService
  |-- ConfigLoader
  |-- SQLiteJobStore
  |-- DraftWorkflow
  |-- AssetSourceLoader
  |-- HealthMonitor
        |
        +--> HermesDbClient ----> hermes-db MCP
        +--> WechatAdapterClient -> ECS adapter -> WeChat API
```

服务只暴露 MCP transport 和 health endpoint。MCP tools 仍是用户可见契约；REST 草稿管理 API 不在范围内。

---

## Architecture Reference

| 参考模式 / 模板 | 来源 URL | 适配点 | 不适配点 | 当前阶段 |
|-----------------|----------|--------|----------|----------|
| 分层单体 / modular monolith | https://github.com/study8677/awesome-architecture | 单容器、单部署单元，内部按 transport/service/workflow/store 分层 | 不拆微服务，不引入消息队列 | MVP |
| Official MCP Streamable HTTP server | https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/server.md | 用官方 transport 承载 MCP 协议，避免手写 JSON-RPC | 不采用通用 REST-first API 框架设计 | MVP |

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| hermes-db `get_workflow_artifact_content` | publish-ready artifact / article document | `DraftWorkflow` + `DraftPayloadBuilder` | `wechat_create_draft` 能渲染 payload 并调用 adapter |
| `wechat_upload_asset` | WeChat body image URL 或 thumb media id | article artifact / draft payload | artifact manifest 或 draft payload 中引用对应资产 |
| `DraftWorkflow` | draft job row | `wechat_get_draft_status` / idempotency lookup | 同 job_id 或 idempotency_key 可查到最新状态 |
| ECS adapter / WeChat API | `media_id` | 用户和 Hermes ledger | 微信后台草稿可见，ledger metadata 写入 media_id |
| `HealthMonitor` background probe | dependency health snapshot | `/health` | health 响应包含缓存后的 adapter/hermes-db 状态 |

**孤儿 artifact 处理**: 无孤儿 artifact。所有跨阶段产物都有明确消费方；业务级进度流不生成中间 artifact。

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 可部署性 | 单 Docker 服务，冷启动 ≤ 10s | 不引入 Redis/队列；SQLite 单文件持久化 | `docker build`、容器启动日志、healthcheck |
| 一致性 | 同 account + idempotency_key 7 天内只创建一个 job | SQLite `UNIQUE` + `BEGIN IMMEDIATE` | 并发测试验证只调用一次 adapter |
| 安全 | `/mcp` 支持 Bearer token；health 不泄密 | auth middleware 只包 `/mcp`；health 截断错误 | auth/health 单元测试 |
| 可观测性 | 结构化 JSON 日志 | pino + request id + tool call outcome | 日志 snapshot / smoke evidence |
| 可维护性 | transport 与业务逻辑解耦 | `WechatDraftService` 统一承载 MCP tools 业务 | server/tool registry 中不出现长业务流程 |

---

## Capacity / Scale Notes

- **规模假设**: 单实例 NAS 容器；本机 agent 和 NAS agent 共用；并发目标 10。
- **读写特征**: 草稿创建低频写；状态查询和 health 读多。
- **失败代价**: 重复调用微信 API 会产生重复草稿，是最高优先级风险；ledger 写失败可记录为部分成功。

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001 MCP 核心依赖 | 需要服务型 MCP，而不是 REST API | 官方 SDK / FastMCP TS / mcp-framework | 继续用 `@modelcontextprotocol/sdk` | 需要自己组织 service 层 | https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/server.md |
| ADR-002 HTTP host | 需要挂载 Streamable HTTP endpoint 和 health | Express / Fastify | Express thin host | 放弃 Fastify 内建 schema/logging；必须保留 Host header validation | https://github.com/modelcontextprotocol/typescript-sdk/blob/main/packages/middleware/express/README.md |
| ADR-003 transport state | 多 agent 统一调用，但业务状态不依赖 MCP session | Stateful transport / Stateless transport | Stateless transport | 每次请求需从 store/config 恢复业务状态 | https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/server.md |
| ADR-004 job store | JSONL 并发弱，Redis 过重 | JSONL / SQLite / Redis | SQLite + `better-sqlite3` | 单实例写锁，不支持多实例扩展；事务必须同步执行 | https://raw.githubusercontent.com/WiseLibs/better-sqlite3/master/docs/api.md |
| ADR-005 asset source | 远程 MCP 下调用方本机 path 语义不成立 | 透传 local_path / 禁用 local_path / 限制容器内路径 | 推荐 remote_url；local_path 限制在 ASSET_ROOT | 需要迁移旧本机路径调用习惯 | UNVERIFIED |

---

## Key Design Decisions

### Decision 1: 使用官方 MCP SDK + Streamable HTTP

- **背景**: 目标是标准 MCP 服务，客户端应通过 MCP endpoint 调 tools。
- **选项**:
  - A: 官方 SDK + Streamable HTTP transport，贴近协议实现。
  - B: FastMCP / mcp-framework，上层抽象更多。
- **结论**: 选 A。当前只有 5 个 tools，不需要自动发现或完整框架。
- **影响**: 需要在本仓库内明确 service 层边界，避免 tool handler 变胖。
- **来源**: https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/server.md

### Decision 2: Express 只作为 thin host

- **背景**: 服务需要 `/mcp` 和 `/health`，不是 REST-first API。
- **选项**:
  - A: Express，贴 MCP SDK 官方示例。
  - B: Fastify，性能和 schema 能力更强，但需要适配 transport。
- **结论**: 选 A。性能不是瓶颈，减少 MCP transport 胶水优先。
- **影响**: schema 仍由 MCP tool Zod schema 和 service 内验证承担；若不用官方 Express helper，必须显式实现等价 Host header validation。
- **来源**: https://github.com/modelcontextprotocol/typescript-sdk/blob/main/packages/middleware/express/README.md

### Decision 3: SQLite 替换 JSONL JobStore

- **背景**: JSONL append-only 无法可靠表达并发幂等。
- **选项**:
  - A: JSONL + 进程内 lock。
  - B: SQLite unique constraint + transaction。
  - C: Redis。
- **结论**: 选 B。SQLite 是平台原生持久化能力，足够支撑单实例并发和重启恢复。
- **影响**: 新增 native dependency `better-sqlite3` 和 schema initialization；多实例部署仍 out of scope；事务内不得执行 async 外部调用。
- **来源**: https://raw.githubusercontent.com/WiseLibs/better-sqlite3/master/docs/api.md

### Decision 4: Stateless MCP transport with JSON responses

- **背景**: 业务状态由 SQLite 持久化，当前不需要 MCP session resumability。
- **选项**:
  - A: Stateful transport，启用 session id 和 resumability。
  - B: Stateless transport，`sessionIdGenerator: undefined`，并启用 JSON response。
- **结论**: 选 B。每次 tool call 独立，部署和调试更简单。
- **影响**: 不支持 transport 层 resumability；长流程恢复通过 `wechat_get_draft_status` 查询 job 状态完成。
- **来源**: https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/server.md

---

## Module Design

### Module: HTTP Host

**YAGNI stop**: 第 4 层，使用成熟依赖 Express 和 MCP SDK middleware/transport，不写自定义 HTTP 框架。

**职责**: 启动 Docker 服务，挂载 `/mcp`、`/health`，处理 auth、日志和 graceful shutdown。

**改动概述**:
- 新增 HTTP entrypoint，例如 `src/http-index.ts`。
- `POST /mcp` 使用 MCP Streamable HTTP transport，优先 `sessionIdGenerator: undefined` 和 JSON response。
- `GET/HEAD /health` 调用 `HealthMonitor`。
- Docker 镜像只启动 HTTP entrypoint。
- 发布部署沿用 `hermes-db` 的 `mcp-release.yml`：`wechat-draft-vX.Y.Z` tag -> GitHub Actions build/push GHCR -> NAS self-hosted runner pull/up；NAS 不本地构建镜像。

**注意事项**:
- `/mcp` 走 Bearer auth；`/health` 不鉴权但不泄密。
- 使用官方 Express helper 或实现等价 Host header validation，避免 DNS rebinding 类风险。
- 不新增 REST 草稿 API。

### Module: MCP Tool Registry

**YAGNI stop**: 第 6 层，保留显式注册 5 个 tools，不引入自动发现框架。

**职责**: 创建 `McpServer` 并注册 5 个 tools，把请求转发到 `WechatDraftService`。

**改动概述**:
- 将当前 `server.ts` 中的长 handler 拆成 thin handlers。
- 保留 `Result<T>` 文本 JSON 返回格式，保持 MCP 客户端兼容。
- 当前 `server.ts` 同时初始化 config/client/store 并注册 tools；重构后应只保留 tool registry 职责。

**注意事项**:
- tool handler 不直接操作 adapter/hermes/job store。
- 统一错误映射由 service 或 helper 处理。

### Module: WechatDraftService

**YAGNI stop**: 第 6 层，需要一个明确 service 层消除 transport 复制逻辑。

**职责**: 承载 5 个 tool 的业务用例：list accounts、validate artifact、upload asset、create draft、get status。

**改动概述**:
- 初始化并持有 `ConfigLoader`、`HermesDbClient`、`SQLiteJobStore`、`DraftWorkflow` 依赖。
- 复用现有 `DraftWorkflow`，但把账号检查、adapter 解析、result 构造集中到 service。
- 保持 `HermesDbClient` 调 hermes-db HTTP MCP `/mcp` 的调用链不变。

**注意事项**:
- 启动时同步初始化 config 和 store；失败则服务不可用。
- `createDraft` 只对新建 job 执行外部副作用。

### Module: SQLiteJobStore

**YAGNI stop**: 第 3 层，使用 SQLite `UNIQUE` 和事务，而不是应用层自造幂等锁。

**职责**: 持久化 job 状态，实现 7 天幂等窗口和状态查询。

**关键行为**:
```text
createOrGetJob(account, artifactId, idempotencyKey):
  BEGIN IMMEDIATE
  delete expired idempotency rows
  try insert queued row with expires_at = now + 7 days
  on unique conflict select existing row
  COMMIT
  return { job, created }
```

**注意事项**:
- 每次状态更新写同一行，而不是 append-only。
- `error_details` 存 JSON 字符串，避免过早设计多表结构。
- `better-sqlite3` transaction 不包 async 函数；事务内只做本地 SQLite 操作，外部 API 调用必须在事务外。

### Module: HealthMonitor

**YAGNI stop**: 第 6 层，写最小后台 probe，不引入监控系统或队列。

**职责**: 提供本地 readiness 检查和外部依赖连通性缓存。

**改动概述**:
- 启动后立即 probe 一次 adapter/hermes-db。
- 后台定时刷新缓存。
- `/health` 同步检查 config/runtime/db，读取外部缓存。

**注意事项**:
- 外部依赖失败返回 `200 + degraded`，不触发容器反复重启。
- 本地不可运行状态返回 `503`。

### Module: AssetSourceLoader

**YAGNI stop**: 第 2/3 层，使用 Node 标准库 path 规范化和文件读取；使用现有 fetch。

**职责**: 在远程 MCP 场景下安全 materialize 资产。

**改动概述**:
- `remote_url` 继续支持。
- `local_path` 只允许解析到 `ASSET_ROOT` 下。
- 错误码对齐 `asset_size_exceeded` / `asset_format_unsupported` 等现有 schema。

**注意事项**:
- 不再暗示调用方本机路径可用。
- 后续如需要真正文件上传，再单独设计 MCP resource 或 artifact ingestion。

---

## Data Model

需要 `data-model.md`。核心实体是 `jobs` 表，负责 job 状态、media_id、幂等 key 和过期时间。详细 DDL 和状态转换见 [data-model.md](data-model.md)。

---

## Project Structure

```text
packages/wechat-draft/
  Dockerfile
  package.json
  src/
    http-index.ts
    http/
      app.ts
      auth.ts
      health.ts
    mcp/
      createMcpServer.ts
      toolResult.ts
    service/
      WechatDraftService.ts
      HealthMonitor.ts
    store/
      SQLiteJobStore.ts
      JobStore.ts            # legacy or compatibility boundary
    workflow/
      DraftWorkflow.ts       # update to use SQLiteJobStore contract
```

Exact filenames can be adjusted during implementation, but transport, MCP registry, service, workflow and store boundaries should remain separate.

---

## Risks and Tradeoffs

- **Native dependency risk**: `better-sqlite3` may affect Docker build image requirements. Mitigation: pin Node image, build in multi-stage Dockerfile, verify on NAS target.
- **MCP remote client config drift**: Codex/Claude/Hermes may differ in remote MCP config shape. Mitigation: include smoke tests and keep client config examples as placeholders.
- **Partial success**: draft may be created while ledger update fails. Mitigation: status remains `saved` with warning/error metadata, and logs include correlation id.
- **Asset path confusion**: old `local_path` calls may break. Mitigation: clear error message and docs recommending `remote_url` / artifact references.
- **Transport security drift**: bypassing the MCP Express helper could omit Host validation. Mitigation: use the official helper or implement equivalent checks with tests.

---

## Evolution Path

- **MVP**: 单实例 Docker + SQLite + Streamable HTTP MCP + 5 existing tools。
- **成长期**: 如果 tool 数量明显增长，再考虑 `mcp-framework` 自动发现；如果资产流转变复杂，设计 artifact/resource upload。
- **成熟期**: 如果需要多实例或高并发，迁移 job store 到 Postgres/Redis，并重新设计 distributed idempotency。

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。没有引入 Redis、队列、多实例、插件框架。
- 是否引用了外部模式但没有适配检查：否。仅参考官方 MCP transport 和分层单体。
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。新增 SQLite、health cache、Bearer auth 均已记录。

---

## Verification Strategy

- **Unit**:
  - `SQLiteJobStore` schema init、unique conflict、expired key reuse、status update。
  - `AssetSourceLoader` local path escape、remote URL、size/MIME guard。
  - auth middleware 401/allow cases。
- **Integration**:
  - 启动 HTTP MCP app，用 MCP client 或 HTTP transport fixture 调 `wechat_list_accounts`。
  - mock adapter/hermes-db，验证 `wechat_create_draft` happy path、adapter unreachable、artifact missing、ledger failure。
  - 并发同 idempotency key，验证只创建一个 job 且 adapter 只被调用一次。
- **Docker smoke**:
  - build image。
  - run with mounted config/data。
  - `/health` ok/degraded/503 cases。
  - client config placeholder validation。

---

## Stage Readiness

- 是否需要 `data-model.md`：需要。此 feature 引入 SQLite job store、状态转换和幂等窗口。
- 下一步建议：`tasks`
- 阻塞项：无。实现前需在 tasks 中明确 dependency upgrade、Docker build 和 integration test 顺序。

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | 必须 | 主实现计划 |
| data-model.md | 需要 | SQLite job store 和状态转换 |
| tasks.md | 后续阶段生成 | 由 `tasks` 阶段产出 |
| acceptance.md | 后续阶段生成 | 因 external-side-effects / user-visible-output 命中，closeout 需要验收记录 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| MCP Streamable HTTP | https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/server.md | 官方 SDK server docs |
| MCP Express integration | https://github.com/modelcontextprotocol/typescript-sdk/blob/main/packages/middleware/express/README.md | 官方 Express middleware docs |
| Zod v4 | https://zod.dev | Zod 4 stable；MCP docs use `zod/v4` |
| better-sqlite3 transactions | https://raw.githubusercontent.com/WiseLibs/better-sqlite3/master/docs/api.md | 同步 transaction，throw 回滚 |
| SQLite conflict handling | https://sqlite.org/lang_conflict.html | UNIQUE conflict / OR IGNORE |
| Architecture Quality Gate | https://github.com/study8677/awesome-architecture | SDD reference |
