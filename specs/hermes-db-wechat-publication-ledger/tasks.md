# Tasks: hermes-db WeChat Publication Ledger

**Workspace**: `hermes-db-wechat-publication-ledger` | **Date**: 2026-06-03  
**Input**: `specs/hermes-db-wechat-publication-ledger/spec.md` + `plan.md` + `data-model.md`  
**Prerequisites**: spec.md, plan.md, data-model.md

---

## 执行原则

- 按依赖顺序推进：migration 先于 schema health，contracts 先于 repository/tools，repository 先于 MCP tools，tools 先于端到端验证。
- 每个实现任务必须带对应测试或明确验证任务。
- 不改变现有 topic、workflow run、workflow artifact、inspiration tools 的参数、返回结构和 transport 行为。
- Article ledger 不复制 artifact 正文；正文读取仍通过现有 `get_workflow_artifact_content`。
- URL/canonical 复杂解析不在 hermes-db MVP 内实现；调用方负责提供 canonical/platform refs，hermes-db 负责持久化、约束和诊断。

---

## Phase 1: Migration and Schema Health

**目标**: 建立 article ledger 存储结构，并让 health 能诊断 publication ledger capability。

- [x] T001 [US1, US2, US3] 新增 Alembic migration `0003_wechat_publication_ledger.py`
  - scope: `packages/hermes-db/migrations/versions/0003_wechat_publication_ledger.py`
  - maps_to: FR-001, FR-002, FR-003, FR-008, ADR-001-006, data-model.md
  - verify: migration 文件包含 `wechat_articles`、`wechat_article_external_refs`、FK、CHECK、UNIQUE、partial indexes 和 `down_revision = "0002_wechat_workflow_artifacts"`

- [x] T002 [US1, US2, US3] 为 publication ledger migration 增加静态 SQL 测试
  - scope: `packages/hermes-db/tests/test_migration_sql.py`
  - maps_to: FR-001, FR-002, NFR-004, 查询性能
  - verify: `uv run pytest tests/test_migration_sql.py -q`

- [x] T003 [US4] 扩展 schema inspection 支持 publication ledger capability
  - scope: `packages/hermes-db/src/hermes_db_mcp/services/schema.py`
  - maps_to: FR-010, US4-1, 可诊断性
  - verify: 单元测试覆盖表缺失、约束缺失、索引缺失、完整 schema 四类结果

- [x] T004 [US4] 更新 `health` 合并 `wechat_publication_ledger` capability
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/health.py`
  - maps_to: FR-010, US4-1, US4-3
  - verify: `health()["capabilities"]` 保留现有 topic/workflow keys，并新增 `wechat_publication_ledger`

- [x] T005 [US4] 增加 publication ledger schema health 测试
  - scope: `packages/hermes-db/tests/test_wechat_article_schema_health.py`, `packages/hermes-db/tests/test_health.py`
  - maps_to: FR-010, NFR-003, 兼容性
  - verify: `uv run pytest tests/test_health.py tests/test_wechat_article_schema_health.py -q`

---

## Phase 2: Contracts and Validation

**目标**: 固化 article/ref 入参、状态语义、幂等键推导、查询边界和结构化错误。

- [x] T006 [US1, US3] 扩展 publication ledger 常量和错误码
  - scope: `packages/hermes-db/src/hermes_db_mcp/contracts.py`
  - maps_to: FR-003, FR-008, NFR-003, ADR-002, ADR-006
  - verify: constants 包含 article statuses、ref types、默认/最大 list limit、URL/ref 长度限制；error codes 包含 `conflict` 或等价结构化冲突码

- [x] T007 [US1] 实现 `derive_publication_idempotency_key`
  - scope: `packages/hermes-db/src/hermes_db_mcp/contracts.py`
  - maps_to: FR-002, FR-008, ADR-001, ADR-002
  - verify: 按 canonical URL、external reference、publish artifact、published artifact 的优先级推导；无可用输入时返回 `missing_required_field`

- [x] T008 [US1, US2] 新增 `validate_wechat_article_payload`
  - scope: `packages/hermes-db/src/hermes_db_mcp/contracts.py`
  - maps_to: FR-004, US1-1, US1-2, US1-4, US1-5, US2, NFR-003
  - verify: 校验 `account/run_id/status`、UUID 字段、status-specific reference 要求、空串归一、artifact refs 形态

- [x] T009 [US3] 新增 `validate_wechat_article_query`
  - scope: `packages/hermes-db/src/hermes_db_mcp/contracts.py`
  - maps_to: FR-005, FR-006, US3-1, US3-2, NFR-002
  - verify: 校验至少一个 filter 或显式 bounded limit，默认 limit 50，最大 limit 200，日期格式和 offset 范围

- [x] T010 [US3] 新增 `validate_wechat_article_ref_payload`
  - scope: `packages/hermes-db/src/hermes_db_mcp/contracts.py`
  - maps_to: FR-007, FR-009, US3-3, NFR-005, ADR-005
  - verify: 校验 ref type/value、至少一个 ref 或 patch 字段、可 patch 字段白名单、空 ref 拒绝

- [x] T011 [US1, US2, US3] 增加 publication ledger contract 测试
  - scope: `packages/hermes-db/tests/test_wechat_article_contracts.py`
  - maps_to: T006-T010
  - verify: `uv run pytest tests/test_wechat_article_contracts.py -q`

---

## Phase 3: Repository Layer

**目标**: 用 repository 封装 SQL，实现 article 幂等 upsert、refs 历史、查询和冲突诊断所需的结构。

- [x] T012 [US1] 实现 `upsert_article`
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/wechat_article_repo.py`
  - maps_to: FR-001, FR-004, FR-008, US1-1, US1-2, US1-6, ADR-001, ADR-002
  - verify: 同一 `(account, publication_idempotency_key)` 重复写入返回同一 article；返回 `(row, created)` 语义

- [x] T013 [US2] 实现 run/artifact 强 FK 写入路径和异常识别
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/wechat_article_repo.py`
  - maps_to: FR-002, US2-1, US2-2, US2-3, US2-4, ADR-003
  - verify: 不存在 run/artifact 触发可由 tool 映射的 FK constraint 诊断；nullable artifact 字段允许 repair/dry-run 场景

- [x] T014 [US3] 实现 `insert_or_update_external_refs`
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/wechat_article_repo.py`
  - maps_to: FR-007, FR-009, US3-3, NFR-005, ADR-005
  - verify: active refs 唯一；同 article 重复 ref 幂等；跨 article active ref 返回可识别 conflict；历史 ref 可 supersede

- [x] T015 [US3] 实现 `list_articles`
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/wechat_article_repo.py`
  - maps_to: FR-005, US3-1, NFR-002, 查询性能
  - verify: 支持 `account/topic_id/run_id/status/publish_target/date_from/date_to/limit/offset`，返回摘要不含 artifact content

- [x] T016 [US3] 实现 `get_article` 和 `list_article_refs`
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/wechat_article_repo.py`
  - maps_to: FR-006, US3-2, ADR-005
  - verify: article detail 返回 artifact ids、metadata、active/historical refs；不存在 article 返回 `None`

- [x] T017 [US3] 实现 `patch_article_refs_and_summary`
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/wechat_article_repo.py`
  - maps_to: FR-007, FR-009, US3-3, NFR-005
  - verify: update refs 可同时 patch `published_url/canonical_url/external_reference/status/published_at/metadata`

- [x] T018 [US1, US2, US3] 增加 repository SQL/单元测试
  - scope: `packages/hermes-db/tests/test_wechat_article_repo_sql.py`, `packages/hermes-db/tests/test_wechat_article_repo.py`
  - maps_to: T012-T017, 幂等性, 可追溯性, 可演进性
  - verify: `uv run pytest tests/test_wechat_article_repo_sql.py tests/test_wechat_article_repo.py -q`

---

## Phase 4: MCP Article Tools

**目标**: 暴露下游 agents、analytics、repair 可调用的 MCP tools，并保持 structured result/error 语义。

- [x] T019 [US1, US2] 实现 `upsert_wechat_article` MCP tool
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/wechat_articles.py`
  - maps_to: FR-004, US1, US2, ADR-001-004
  - verify: tool 测试覆盖 published、dry-run drafted、missing URL with external reference、missing reference repair metadata、same key retry

- [x] T020 [US3] 实现 `list_wechat_articles` MCP tool
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/wechat_articles.py`
  - maps_to: FR-005, US3-1, NFR-002
  - verify: tool 测试确认 bounded query、filters、生效 limit/offset、结果不含 artifact body

- [x] T021 [US3] 实现 `get_wechat_article` MCP tool
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/wechat_articles.py`
  - maps_to: FR-006, US3-2
  - verify: tool 测试覆盖存在 article、refs 列表、not_found、不返回 artifact content

- [x] T022 [US3] 实现 `update_wechat_article_external_refs` MCP tool
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/wechat_articles.py`
  - maps_to: FR-007, FR-009, US3-3, NFR-005
  - verify: tool 测试覆盖追加 ref、supersede/patch、跨 article ref conflict、缺 ref/patch 参数

- [x] T023 [US4] 注册新 tools 且不改变现有 tools
  - scope: `packages/hermes-db/src/hermes_db_mcp/server.py`, `packages/hermes-db/src/hermes_db_mcp/tools/__init__.py`
  - maps_to: FR-011, US4-2, US4-4
  - verify: 现有 topic/workflow/inspiration tests 仍通过；工具注册不影响 health/transport

- [x] T024 [US1, US2, US3] 增加 MCP tool 测试
  - scope: `packages/hermes-db/tests/test_wechat_article_tools.py`
  - maps_to: T019-T022, NFR-003, 可诊断性
  - verify: `uv run pytest tests/test_wechat_article_tools.py -q`

---

## Phase 5: Integration, Regression, and Evidence

**目标**: 补齐真实链路验证、兼容性验证、部署说明和最终证据。

- [x] T025 [US1, US2, US3] 增加 publication ledger 集成测试
  - scope: `packages/hermes-db/tests/test_wechat_article_integration.py`
  - maps_to: 持久性, 幂等性, 可追溯性, artifact-handoff
  - verify: 创建 workflow run/artifacts -> upsert article -> list/get -> update refs；可用 `DATABASE_URL` 时跑真实 PG

- [x] T026 [US4] 更新 hermes-db README 或部署文档说明新 capability 和 tools
  - scope: `packages/hermes-db/README.md`, `docs/hermes-db-deployment.md`
  - maps_to: FR-010, FR-011, release readiness
  - verify: 文档包含 `capabilities.wechat_publication_ledger`、四个新 tool 名称、`alembic upgrade head` 提醒

- [x] T027 [US4] 跑 publication ledger 相关局部测试
  - scope: `packages/hermes-db/tests`
  - maps_to: T001-T025
  - verify: `uv run pytest tests/test_migration_sql.py tests/test_wechat_article_contracts.py tests/test_wechat_article_repo_sql.py tests/test_wechat_article_tools.py tests/test_wechat_article_schema_health.py -q`

- [x] T028 [US4] 跑现有 hermes-db 回归测试
  - scope: `packages/hermes-db/tests`
  - maps_to: FR-011, 兼容性
  - verify: `uv run pytest tests -q`

- [x] T029 [US1, US2, US3] 可选 NAS/真实 endpoint smoke
  - scope: NAS hermes-db runtime or local Streamable HTTP endpoint
  - maps_to: Evidence Gate, artifact-handoff
  - verify: NAS PG `alembic upgrade head` 已到 `0003_wechat_publication_ledger`，真实 PG article integration 通过；runtime `/mcp` health 和 `tools/list` 需待新版镜像部署后验证

- [x] T030 [Closeout Prep] 记录实现证据和残留风险
  - scope: `specs/hermes-db-wechat-publication-ledger/acceptance.md`
  - maps_to: prior-closure-failure, Evidence Gate
  - verify: acceptance 记录测试命令、结果、未执行项、部署状态、下游 agents 联调状态

---

## 依赖与顺序

- 关键路径：T001 -> T003/T004 -> T006-T011 -> T012-T018 -> T019-T024 -> T027/T028 -> T030。
- T002 可在 T001 后立即完成。
- T003/T004 可与 T006-T011 并行，但最终 health 验证依赖 migration schema 定义。
- T012/T013 是 repository 的关键入口；T014-T017 依赖 T012 的 article row 写入语义。
- T019 依赖 T006-T018；T020/T021 依赖 T015/T016；T022 依赖 T014/T017。
- T026 可与 Phase 4 后半段并行，但文档内容应以最终 tool 名称和 capability key 为准。
- T029 依赖 migration、tools 和运行环境；若没有 NAS/endpoint 权限可跳过，但必须在 T030 记录原因。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|-------------|----------|
| US1 创建 article、dry-run、缺 URL/reference、幂等 | T001, T006-T008, T012, T019, T024, T025 |
| US2 绑定 run/draft/final/publish artifacts | T001, T008, T013, T019, T024, T025 |
| US3 list/get/update refs | T009, T010, T014-T017, T020-T022, T024, T025 |
| US4 health、兼容现有 tools/transport | T003-T005, T023, T026-T028 |
| FR-001/FR-002 新实体和字段 | T001, T002 |
| FR-004-FR-007 MCP tools | T019-T022, T024 |
| FR-008 幂等唯一 | T001, T007, T012, T018, T019 |
| FR-009 外部 refs 补写 | T010, T014, T017, T022 |
| FR-010 health capability | T003-T005 |
| FR-011 兼容性 | T023, T028 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|----------------------|----------|----------|
| ADR-001 server article id | T001, T012, T019 | T002, T018, T024 |
| ADR-002 idempotency key | T001, T007, T012, T019 | T011, T018, T024 |
| ADR-003 strong FK nullable refs | T001, T013, T019 | T002, T018, T024, T025 |
| ADR-004 caller canonicalization | T008, T014, T019, T022 | T011, T024 |
| ADR-005 external refs table | T001, T010, T014, T017, T022 | T002, T018, T024 |
| ADR-006 TEXT + CHECK status | T001, T006, T008 | T002, T011, T024 |
| 幂等性 | T007, T012, T014, T019 | T018, T024, T025 |
| 可追溯性 | T001, T013, T016, T021 | T018, T024, T025 |
| 可诊断性 | T003-T011, T019-T024 | T005, T011, T024 |
| 查询性能 | T001, T009, T015, T020 | T002, T018, T024 |
| 兼容性 | T023, T028 | T028 |

---

## Notes

- 当前任务数量较多，且横跨 migration、contracts、repository、tools、health、docs、真实验证和验收记录，不建议直接跳到一次性 implement。
- `pgcrypto/gen_random_uuid()` 可在实现期根据 NAS PG 环境确认；若不可用，repository/tool 层生成 UUID 也符合 plan。
- External refs 的 active uniqueness 是 analytics 绑定的关键约束；实现时需要明确 conflict 映射，不能吞掉 unique violation。
- 本 feature 不实现 agents 仓 `PublicationLedgerService`；下游联调证据可在 acceptance 中标记为待 agents feature 消费。

---

## Stage Readiness

- 推荐下一步：`execute-plan`
- 阻塞项：无
