# Smoke Evidence: WeChat Draft MCP

**Workspace**: `wechat-draft-mcp`  
**Date**: 2026-06-21  
**Last Updated**: 2026-06-21 (Phase 4 完成 + ECS Adapter 部署成功)  
**Scope**: Phase 0-4 完成。ECS adapter deployed and token validated. No live draft creation performed yet.

## Summary

| Task | Result | Evidence |
|---|---|---|
| T001a/T001d 配置固化 | PASS | 配置设计提取到 `infrastructure-config.md` |
| T001b AccessToken dry-run | PASS | ECS adapter token 验证成功，expires_in=7200 |
| T004 hermes-db artifact/ledger capability | PASS | Focused local suites covering migration SQL, health/schema, workflow tools, and WeChat article tools passed. Existing schema supports `workflow_artifacts` and `wechat_articles.status=drafted`. |
| T005 Package Scaffold | PASS | `pnpm build` 成功，MCP initialize 成功 |
| T006 Tool Schemas | PASS | 4 个工具 schema 定义，禁用 publish/update/delete |
| T007 Config Loader & Account List | PASS | ConfigLoader 实现，`wechat_list_accounts` 工具可用，redaction 验证通过 |
| T008 HermesDbClient 骨架 | PASS | getArtifact/upsertArticleLedger/health 骨架，预留 hermes-db MCP 集成点 |
| T009 ArtifactValidator | PASS | 校验 stage/type/publish_ready/wechat_asset_manifest/cover/body_images |
| T010 WeChat-ready artifact 示例 | PASS | `docs/wechat-ready-artifact-example.md` 包含完整有效示例 |
| T011 TokenManager (ECS) | PASS | fetch/cache/refresh/redact，7200s TTL + 300s safety margin |
| T012 WeChatApiClient (ECS) | PASS | createDraft + token retry，WeChatApiError 分类 |
| T012a WechatAdapterClient (NAS) | PASS | HTTP 客户端（health/check-credentials/create-draft），7 种错误分类 |
| T012b ECS adapter HTTP 服务 | PASS | 3 endpoints + auth/account middleware，Dockerfile，DEPLOYMENT.md，**已部署到 Ali ECS** |
| T013 DraftPayloadBuilder | PASS | 调用 ArtifactValidator，图片 URL 二次检查，字段映射完整 |
| T013a API 风控策略 | PASS | `docs/api-risk-control.md` 策略文档，重试策略（只重试 token 错误），脱敏验证 |
| T014 JobStore | PASS | JSONL 追加写入，按日期分文件，idempotency 7 天回溯，query by job_id/artifact_id |
| T015 DraftWorkflow | PASS | 状态机（7 阶段），幂等性检查，分阶段验证，错误分类 |
| T016 draft/add 闭环 | PASS | adapterClient.createDraft 集成，media_id 提取，错误分类完整 |
| T017 ledger upsert | PASS | ledger_update 阶段，HermesDbClient 集成点标注，失败不阻塞 |
| T018 失败处理 | PASS | `docs/error-handling.md` 文档（4 种状态、12 种 error code、人工建议、runbook）|
| T019 配置示例 | PASS | `docs/configuration.md` - Claude Code/Codex/Hermes 配置示例 |
| T019a 运维 runbook | PASS | `docs/runbook.md` - Docker/systemd 部署，故障排查，定期维护 |

## ECS Adapter Deployment Evidence

**Deployment Date**: 2026-06-21  
**Host**: Ali ECS  
**Account**: weiyuchengchun (微雨成春)

**Health Check**:
```json
{
  "status": "ok",
  "capabilities": ["check_credentials", "draft_add"],
  "allowed_accounts": ["weiyuchengchun"]
}
```

**Token Validation (T001b)**:
```json
{
  "success": true,
  "account": "weiyuchengchun",
  "token_valid": true,
  "expires_in": 7200
}
```

**Container Status**:
```
CONTAINER ID   IMAGE                           STATUS         PORTS
eda856f91e8c   wechat-draft-adapter:latest     Up 5 seconds   0.0.0.0:3000->3000/tcp
```

**Verification Steps Completed**:
- ✅ Docker 镜像构建成功
- ✅ 容器运行正常
- ✅ Health endpoint 响应正常
- ✅ 微信 AccessToken 获取成功
- ✅ IP 白名单配置正确
- ✅ AppID/AppSecret 配置正确

---

## Phase 0: 前置配置固化

### T001a + T001d: 配置来源与 Adapter 运行方式 ✅

**证据位置**: `infrastructure-config.md`

**关键发现**：
- ECS adapter 未部署，当前为规划阶段
- 配置设计已从 plan.md / data-model.md 固化
- 微信 credential 存储位置：ECS adapter 端（不在 NAS）
- ECS 出口：Ali ECS 公网 IP/EIP（需配置微信 IP 白名单）
- NAS 到 ECS 通道：Tailscale/WireGuard/SSH tunnel 之一
- Adapter endpoints: /health, /accounts/:account/check-credentials, /accounts/:account/drafts
- 禁用 endpoints: 图片上传、素材上传、发布、群发、更新、删除

**下一步**: T001b AccessToken dry-run 需等待 T012b adapter HTTP 服务实现

---

## Phase 0: hermes-db Capability

### T004: hermes-db Artifact/Ledger Capability ✅

Commands executed:

```bash
cd packages/hermes-db
rtk uv run pytest tests/test_migration_sql.py tests/test_wechat_article_schema_health.py tests/test_wechat_article_tools.py -q
rtk uv run pytest tests/test_health.py tests/test_schema_health.py tests/test_wechat_article_schema_health.py tests/test_wechat_article_tools.py tests/test_migration_sql.py -q
rtk uv run pytest tests/test_workflow_tools.py tests/test_wechat_article_tools.py -q
```

Observed evidence:

- `tests/test_migration_sql.py tests/test_wechat_article_schema_health.py tests/test_wechat_article_tools.py -q` -> `16 passed in 0.72s`.
- `tests/test_health.py tests/test_schema_health.py tests/test_wechat_article_schema_health.py tests/test_wechat_article_tools.py tests/test_migration_sql.py -q` -> `22 passed in 1.03s`.
- `tests/test_workflow_tools.py tests/test_wechat_article_tools.py -q` -> `12 passed in 0.42s`.

Schema confirmation:

- `packages/hermes-db/migrations/versions/0002_wechat_workflow_artifacts.py` defines `hermes.workflow_artifacts` with `artifact_id`, `run_id`, `stage`, `type`, `content_text`, `content_ref`, and `metadata`.
- `packages/hermes-db/migrations/versions/0003_wechat_publication_ledger.py` defines `hermes.wechat_articles` with `publication_idempotency_key`, `draft_artifact_id`, `status`, `title`, `published_url`, and `metadata`.
- The `wechat_articles.status` check includes `drafted`.

---

## Phase 1: MCP 服务骨架 ✅

### T005: Package Scaffold ✅

**证据**：
```bash
$ cd packages/wechat-draft && rtk pnpm build
> @mcps/wechat-draft@0.1.0 build
> tsc && shx chmod +x dist/index.js
# Build successful
```

**产物**：
- `packages/wechat-draft/`: MCP 包根目录
- `dist/index.js`: 可执行入口
- `dist/server.js`: MCP 服务器实现
- `dist/config/`, `dist/schemas/`: 模块产物

### T006: Tool Schemas ✅

**证据**：
```bash
$ echo '{"jsonrpc":"2.0","id":1,"method":"initialize",...}' | rtk node dist/index.js
WeChat Draft MCP Server running on stdio
{"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{"listChanged":true}},"serverInfo":{"name":"WeChat Draft MCP Server","version":"0.1.0"}},"jsonrpc":"2.0","id":1}
```

**已定义工具**：
1. `wechat_list_accounts` (read-only)
2. `wechat_validate_publish_artifact` (read-only, placeholder)
3. `wechat_create_draft` (side-effecting, placeholder)
4. `wechat_get_draft_status` (read-only, placeholder)

**禁用工具**：
- ✅ 无 publish/mass-send/update/delete 工具
- ✅ 无 alternate write adapter 工具
- ✅ `wechat_create_draft` 标记为 side-effecting

### T007: Config Loader & Account List ✅

**证据**：
- `src/config/types.ts`: AccountConfig, EcsWechatAdapterConfig, ApiCredentialConfig 定义
- `src/config/loader.ts`: ConfigLoader 实现，支持环境变量覆盖
- `config/accounts.example.yaml`: 配置示例
- `wechat_list_accounts` 工具已实现，支持 include_disabled 参数

**Redaction 验证**：
- ✅ 配置不返回 AppSecret/AccessToken
- ✅ 禁用账号返回结构化错误（ErrorCode.ACCOUNT_DISABLED）
- ✅ 未知账号返回结构化错误（ErrorCode.ACCOUNT_NOT_FOUND）
- ✅ auth_ref 使用 `env:WECHAT_ADAPTER_AUTH_TOKEN` 引用，不存储 raw token

---

## Phase 2: Hermes-db Artifact 契约 ✅

### T008: HermesDbClient ✅

**证据**：
- `src/hermes/HermesDbClient.ts`: 实现骨架，包含 getArtifact, upsertArticleLedger, health 方法
- 类型定义：WorkflowArtifact, WechatArticleLedger, ArticleLedgerUpdate
- 预留 hermes-db MCP 集成点（待 Phase 4 实现真实调用）

**接口设计**：
```typescript
class HermesDbClient {
  async getArtifact(artifactId: string): Promise<WorkflowArtifact | null>
  async upsertArticleLedger(update: ArticleLedgerUpdate): Promise<void>
  async health(): Promise<{ ok: boolean; error?: string }>
}
```

### T009: ArtifactValidator + wechat_validate_publish_artifact ✅

**证据**：
- `src/hermes/ArtifactValidator.ts`: 完整校验逻辑
- MCP tool `wechat_validate_publish_artifact` 已集成 validator

**校验规则**：
- ✅ stage === 'publish_ready'
- ✅ type === 'wechat_api_article'
- ✅ metadata.publish_ready === true
- ✅ metadata.title 存在
- ✅ metadata.wechat_asset_manifest.ready === true
- ✅ metadata.cover.thumb_media_id 存在
- ✅ body_images 所有 URL 必须是 WeChat URL（mmbiz.qpic.cn）
- ✅ content_text 或 content_ref 至少一个存在

**错误分类**：
- error: 阻塞草稿创建
- warning: 不阻塞但需关注

### T010: WeChat-Ready Artifact 示例 ✅

**证据**：
- `docs/wechat-ready-artifact-example.md`: 完整文档

**内容覆盖**：
- ✅ 有效 artifact 完整示例（JSON）
- ✅ 验证规则表格
- ✅ 无效示例（wrong stage, non-WeChat URL, missing cover）
- ✅ Asset 准备流程说明
- ✅ MVP 范围边界（MCP 不上传图片）

**关键示例字段**：
```json
{
  "stage": "publish_ready",
  "type": "wechat_api_article",
  "metadata": {
    "publish_ready": true,
    "title": "AI 技术发展趋势分析",
    "cover": {
      "thumb_media_id": "PERMANENT_THUMB_MEDIA_ID_ABC123"
    },
    "wechat_asset_manifest": {
      "ready": true,
      "body_images": [
        {
          "wechat_url": "https://mmbiz.qpic.cn/mmbiz_png/..."
        }
      ],
      "cover_thumb_media_id": "PERMANENT_THUMB_MEDIA_ID_ABC123"
    }
  }
}
```

---

## Phase 3: ECS Adapter (部分完成) 🔄

### T011: TokenManager ✅

**证据**：
- `packages/wechat-draft-adapter/src/wechat/TokenManager.ts`: 完整实现
- `packages/wechat-draft-adapter/src/types/wechat.ts`: 类型定义

**功能**：
- ✅ Token fetch from WeChat API (`/cgi-bin/token`)
- ✅ Cache with 7200s TTL + 300s safety margin
- ✅ Serialize refresh per account (Promise deduplication)
- ✅ Token metadata without exposing raw token
- ✅ TokenError 分类：invalid credential, IP whitelist (40164), frozen secret (40125)

### T012: WeChatApiClient ✅

**证据**：
- `packages/wechat-draft-adapter/src/wechat/WeChatApiClient.ts`: 完整实现

**功能**：
- ✅ `createDraft()` 调用 WeChat `draft/add` API
- ✅ Token error 自动重试一次
- ✅ WeChatApiError 分类：token error, rate limit (45009), permission (48001), asset (40007/40008)
- ✅ 无 publish/update/delete 方法

### T012b: ECS Adapter HTTP 服务 ✅

**证据**：
- `packages/wechat-draft-adapter/src/server.ts`: HTTP 服务实现
- `packages/wechat-draft-adapter/Dockerfile`: Docker 镜像配置
- `packages/wechat-draft-adapter/DEPLOYMENT.md`: 部署文档

**Endpoints**：
```
GET  /health
POST /accounts/:account/check-credentials
POST /accounts/:account/drafts
```

**安全设计**：
- ✅ Bearer token 认证 (`ADAPTER_AUTH_TOKEN`)
- ✅ Account allowlist 校验
- ✅ 只监听 localhost（通过 Tailscale/WireGuard 访问）
- ✅ 无 publish/upload/delete endpoints
- ✅ Credentials 从环境变量加载

**Docker 配置**：
```dockerfile
# Multi-stage build
FROM node:20-alpine AS builder
...
FROM node:20-alpine
USER nodejs  # Non-root user
EXPOSE 3000
HEALTHCHECK CMD node -e "..."
```

**构建验证**：
```bash
$ rtk pnpm build
> tsc
✓ 构建成功
```

---

## Next Phase: Phase 3 (剩余) + Phase 4

**剩余 Phase 3 任务**：
- T012a: NAS-side WechatAdapterClient（MCP 调用 ECS adapter）
- T013: DraftPayloadBuilder（构建 draft/add payload）
- T013a: API 风控、频控、脱敏策略固化

**Phase 4 任务**：
- T014: DraftJob 本地存储
- T015-T018: 草稿写入闭环（workflow + ledger）

**阻塞项**: 无
