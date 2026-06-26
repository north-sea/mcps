# Context Manifest: WeChat Draft MCP Service (Streamable HTTP)

**Workspace**: `wechat-draft-http-service`
**Created**: 2026-06-26
**Status**: active

> 本文件记录实现和验证阶段必须读取的高信号上下文。它不是待修改源文件清单，也不替代实现阶段按需阅读代码。

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-http-service/spec.md` | 需求边界、用户场景、认证、health、asset source 和 Docker 部署约束 | implement | yes |
| `specs/wechat-draft-http-service/plan.md` | 模块边界、ADR、YAGNI 决策、风险和验证策略 | implement | yes |
| `specs/wechat-draft-http-service/data-model.md` | SQLite `jobs` 表、状态转换、幂等算法和迁移说明 | implement | yes |
| `specs/wechat-draft-http-service/tasks.md` | 执行顺序、任务依赖、验收映射和验证点 | implement | yes |
| `packages/wechat-draft/src/index.ts` | 当前 stdio entrypoint，需要保留迁移兜底并避免 Docker 服务误用 | implement | yes |
| `packages/wechat-draft/src/server.ts` | 当前 MCP tool 注册和业务逻辑耦合点，重构 service/registry 边界时必须参考 | implement | yes |
| `packages/wechat-draft/src/workflow/DraftWorkflow.ts` | 草稿创建核心流程和外部副作用顺序，SQLite 幂等改造不能破坏该流程 | implement | yes |
| `packages/wechat-draft/src/store/JobStore.ts` | 旧 JSONL 行为和查询接口参考，SQLite store 需要替代其业务能力 | implement | yes |
| `packages/wechat-draft/src/config/loader.ts` | 配置加载、账号校验和 env 注入规则，Docker config 挂载需兼容 | implement | yes |
| `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` | 当前 asset source 语义和大小/MIME guard，远程 MCP 安全边界要在此收敛 | implement | yes |
| `packages/wechat-draft/src/hermes/HermesDbClient.ts` | hermes-db HTTP MCP 调用链应保持不变 | implement | yes |
| `packages/wechat-draft/src/wechat/WechatAdapterClient.ts` | ECS adapter 调用和错误映射，create/upload/health smoke 需复用 | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-http-service/spec.md` | 验证 US1/US2/US3、FR、NFR 和 out-of-scope 是否满足 | verify | yes |
| `specs/wechat-draft-http-service/plan.md` | 检查是否出现架构漂移、ADR 违背或未记录依赖/状态 | verify | yes |
| `specs/wechat-draft-http-service/data-model.md` | 验证 SQLite schema、状态转换、幂等窗口与实现一致 | verify | yes |
| `specs/wechat-draft-http-service/tasks.md` | 检查任务完成范围、fresh evidence 和遗留项 | verify | yes |
| `packages/wechat-draft/package.json` | 验证依赖、scripts、entrypoint 和测试命令与任务一致 | verify | yes |
| `packages/wechat-draft/Dockerfile` | 若创建，验证 Docker HTTP MCP 服务入口、healthcheck 和 native dependency build | verify | yes |
| `packages/wechat-draft/config/accounts.yaml` | 若用于容器挂载，验证配置示例和服务读取路径一致 | verify | no |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/server.md | MCP Streamable HTTP transport、stateless/session 语义、JSON response 行为 | plan / implement / verify | yes |
| https://github.com/modelcontextprotocol/typescript-sdk/blob/main/packages/middleware/express/README.md | Express thin adapter 和 Host header validation 相关行为 | plan / implement / verify | yes |
| https://zod.dev | Zod v4 stable，MCP SDK 示例使用 `zod/v4` | plan / implement | yes |
| https://raw.githubusercontent.com/WiseLibs/better-sqlite3/master/docs/api.md | better-sqlite3 同步 transaction 行为，throw rollback，async 不适用 | plan / implement / verify | yes |
| https://sqlite.org/lang_conflict.html | SQLite UNIQUE conflict / OR IGNORE 语义，用于幂等写入 | plan / implement / verify | yes |
| https://sqlite.org/lang_upsert.html | SQLite UPSERT 语义，作为实现时可选策略参考 | implement | yes |
| `packages/wechat-draft-adapter/Dockerfile` | adapter 包已有多阶段 Docker 和 healthcheck 经验，可作为 Dockerfile 参考 | implement | yes |

---

## Rules

- 实现阶段不得跳过 `spec.md`、`plan.md`、`tasks.md` 和 `data-model.md`。
- `packages/wechat-draft/src/server.ts` 重构后应变薄；若继续包含长业务流程，verify 阶段必须标为架构漂移。
- SQLite transaction 内不得执行 hermes-db、adapter 或 WeChat 外部调用。
- `/health` 响应不得包含 token、完整 Authorization header、完整 query URL 或敏感配置值。
- 不引入 `.trellis/`、Trellis CLI、hook、task.py 或自动 context injection。
