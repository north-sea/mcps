# Tasks: WeChat Draft Agent Contract Hardening

**Workspace**: `wechat-draft-agent-contract-hardening` | **Date**: 2026-06-27
**Input**: `specs/wechat-draft-agent-contract-hardening/spec.md` + `plan.md`
**Prerequisites**: spec.md, plan.md

---

## 执行原则

- 优先按 agent 可见行为闭环拆 slice，而不是按 schema/API/test 横向堆任务。
- 所有新增错误字段必须保持现有 `success/data` 与 `error/code/message/details` 兼容。
- 不实现 `force_update`、E2E facade、自动压图、draft CRUD、note skill 迁移或写作生成。
- bugfix-loop-breaker 生效：每个已知失败类型都要有 before/after 或替代证据。

---

## Phase 1: Baseline And Shared Error Contract

**目标**: 先固定失败基线和最小错误信封，避免后续只修症状。

- [x] T001 [Bugfix] 记录当前失败基线和替代复现证据
  - scope: `specs/wechat-draft-agent-contract-hardening/verify-evidence.md` 或测试 fixture；覆盖 asset constraints、content-ref-only、artifact id/hash conflict、idempotency hit、FK 缺失。
  - slice: agent 当前会遇到的非行动性失败都有可定位 before evidence。
  - blocked_by: none
  - maps_to: Bugfix Context / Failed Attempt Ledger / US2 / US3
  - verify: evidence 记录 old behavior、复现方式或无法 live 复现原因；不得只写“已知问题”。
  - evidence 2026-06-27: 已创建 `verify-evidence.md`，记录 hidden constraints、asset errors、content_ref-only、idempotency hit、artifact conflict、missing run FK 的 before/after 证据。

- [x] T002 [Foundation] 兼容扩展 WeChat 与 hermes 错误信封
  - scope: `packages/wechat-draft/src/schemas/result-types.ts`, `packages/hermes-db/src/hermes_db_mcp/contracts.py`, related helpers/tests
  - slice: 现有调用方仍能读取旧字段，新调用方可读取 `next_action`、`remediation_hint`、`retryable`、`current_phase`。
  - blocked_by: T001
  - maps_to: ADR-001 / FR-002 / NFR-001 / 可恢复性
  - verify: existing WeChat tests pass；新增 schema/helper tests 覆盖 optional fields 和旧字段兼容。
  - evidence 2026-06-27: WeChat `ErrorResult` 和 hermes `ToolError` 增加 optional remediation fields；旧字段保持不变。`pnpm --filter @mcps/wechat-draft test` 44/44 pass，hermes targeted tests 10/10 pass。

---

## Phase 2: Account Constraints Slice

**目标**: agent 在写操作前能通过 `wechat_list_accounts` 发现当前真实约束。

- [x] T003 [US1] 从 asset validator 提取共享 constraints helper
  - scope: `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` or adjacent constraints module
  - slice: body/cover image 的 size、MIME、source semantics 由同一处常量/helper 驱动验证和输出。
  - blocked_by: T002
  - maps_to: US1 / FR-001 / ADR-003 / 一致性
  - verify: unit tests assert exported constraints equal current enforced body 1MB, cover 64KB, MIME/source rules.
  - evidence 2026-06-27: `AssetSourceLoader.getConstraints()` / `getAssetSourceConstraints()` 复用同一限制；测试覆盖 body 1MB、cover 64KB、MIME、source rules。

- [x] T004 [US1] 在 `wechat_list_accounts` 返回 account constraints
  - scope: `packages/wechat-draft/src/schemas/tool-schemas.ts`, `packages/wechat-draft/src/service/WechatDraftService.ts`, list accounts tests
  - slice: agent 调用 `wechat_list_accounts` 即可看到 capabilities + constraints，减少 upload/create draft 试错。
  - blocked_by: T003
  - maps_to: US1 / FR-001 / FR-006
  - verify: list accounts test asserts each enabled account includes constraints；disabled/include_disabled 行为保持不变。
  - evidence 2026-06-27: `WechatDraftService.listAccounts` 和 HTTP MCP smoke 均验证返回 constraints。

---

## Phase 3: WeChat Actionable Errors Slice

**目标**: WeChat draft MCP 常见失败都返回可恢复、可脱敏、phase-aware 的错误。

- [x] T005 [US2] 为 asset 和 adapter 错误添加 remediation mapping
  - scope: `packages/wechat-draft/src/service/errorMapping.ts`, `packages/wechat-draft/src/service/WechatDraftService.ts`, upload asset tests
  - slice: asset size/mime/path、remote fetch、adapter auth/unreachable 等失败返回 `next_action`、`remediation_hint`、`retryable`。
  - blocked_by: T002, T004
  - maps_to: US2 / FR-002 / NFR-003 / 安全性
  - verify: tests cover `asset_size_exceeded`, unsupported mime, local path escape/no asset root, adapter auth and adapter unreachable; details remain sanitized.
  - evidence 2026-06-27: `errorMapping.test` 覆盖 asset size remediation 和路径脱敏；WeChat test suite 44/44 pass。

- [x] T006 [US2] 将 content-ref-only draft failure 改成公开可恢复错误
  - scope: `packages/wechat-draft/src/wechat/DraftPayloadBuilder.ts`, `packages/wechat-draft/src/workflow/DraftWorkflow.ts`, validate/create draft tests
  - slice: agent 传入只有 `content_ref` 的 artifact 时得到明确恢复动作，而不是 `T013 limitation`。
  - blocked_by: T002
  - maps_to: US2 / FR-003 / Bugfix Loop Breaker
  - verify: test asserts response does not contain `T013` and includes action such as re-upsert inline `content_text` or use future document tools.
  - evidence 2026-06-27: `DraftWorkflow returns actionable error for content_ref-only artifacts` 断言 `next_action=re_upsert_inline_content_text` 且 message 不含 `T013`。

- [x] T007 [US2] 为 draft workflow 失败补充 `current_phase` 和 retryability
  - scope: `packages/wechat-draft/src/workflow/DraftWorkflow.ts`, `packages/wechat-draft/src/schemas/tool-schemas.ts`, workflow/status tests
  - slice: validate、payload_build、draft_creating、ledger_update 等阶段失败能指导 agent 是否重试或修输入。
  - blocked_by: T005, T006
  - maps_to: US2 / FR-002 / Producer-Consumer Matrix / 可恢复性
  - verify: workflow tests assert representative invalid_artifact, adapter_unreachable, adapter_auth_failed, wechat_api_error expose phase-aware fields.
  - evidence 2026-06-27: `DraftWorkflow` failure paths now set `current_phase` and retryability; adapter unreachable/content_ref tests pass。

---

## Phase 4: Hermes Artifact Upsert Outcome Slice

**目标**: hermes workflow artifact upsert 对幂等命中和冲突给出明确结果，不靠 agent 猜。

- [x] T008 [US3] 暴露 idempotency hit 与 skipped update semantics
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/workflow_repo.py`, `packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py`, hermes-db tests
  - slice: 同 hash upsert 返回 `idempotency_hit=true`、`skipped_update_reason`、existing artifact summary。
  - blocked_by: T002
  - maps_to: US3 / FR-004 / ADR-002
  - verify: Python tests cover same `artifact_id` + same hash and same `(run_id, stage, name, hash)` lookup path.
  - evidence 2026-06-27: repo/tool return `idempotency_hit`, `skipped_update_reason`, hash context；`uv run pytest tests/test_workflow_tools.py tests/test_workflow_repo_sql.py` 10/10 pass。

- [x] T009 [US3] 为 artifact conflict 和 missing run 返回 remediation context
  - scope: `packages/hermes-db/src/hermes_db_mcp/repositories/workflow_repo.py`, `packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py`, `contracts.py`, tests
  - slice: `artifact_id_conflict` 返回 existing/provided hash 摘要和建议动作；workflow run FK 缺失不暴露裸 SQL，提示先 upsert workflow run。
  - blocked_by: T008
  - maps_to: US2 / US3 / FR-004 / NFR-003
  - verify: tests cover conflict and missing run; no raw `workflow_artifacts_run_id_fkey` leaks to tool response.
  - evidence 2026-06-27: tests cover `artifact_id_conflict` hash details/remediation and missing run mapping to `next_action=upsert_workflow_run`。

---

## Phase 5: Documentation And Diffusion Check

**目标**: 修正示例契约，检查相邻路径没有继续暴露同类问题。

- [x] T010 [US4] 更新 canonical happy path 和 `content_text` string/object 边界文档
  - scope: `docs/article-document-artifact-example.md`, relevant `packages/wechat-draft/README.md` or package docs
  - slice: agent 能看到 list constraints -> upsert run/artifact -> validate -> create draft 的最短路径和恢复动作。
  - blocked_by: T004, T006, T009
  - maps_to: US4 / FR-005
  - verify: static review or doc check confirms examples do not imply raw JSON object can always be passed as `content_text` string field.
  - evidence 2026-06-27: `docs/article-document-artifact-example.md` 增加实际 tool payload string 示例和 agent-facing draft flow。

- [x] T011 [Bugfix] 执行扩散检查并记录结果
  - scope: WeChat MCP tool responses, hermes workflow artifact tools, `specs/wechat-draft-agent-contract-hardening/verify-evidence.md`
  - slice: 同类 raw/internal/non-actionable errors 被发现并处理或明确 deferred。
  - blocked_by: T005, T006, T009
  - maps_to: Bugfix Loop Breaker / Diffusion Check / NFR-003
  - verify: `rg` or targeted tests show no user-facing `T013`, raw FK, or unremediated `artifact_id_conflict` in affected paths; deferred findings are listed with owner.
  - evidence 2026-06-27: `verify-evidence.md` 记录 diffusion check；剩余命中为 specs、测试、schema health 或无关历史文档，不是 WeChat draft runtime 用户错误。

---

## Phase 6: Verification And Closeout Prep

**目标**: 形成 fresh evidence，准备进入 verify/closeout。

- [x] T012 [Verify] 运行 WeChat 和 hermes 相关验证套件
  - scope: `packages/wechat-draft`, `packages/hermes-db`, `specs/wechat-draft-agent-contract-hardening/verify-evidence.md`
  - slice: Component capability 和 workflow contract 都有 fresh evidence。
  - blocked_by: T011
  - maps_to: Verification Strategy / Evidence Gate
  - verify: 记录 `pnpm --filter @mcps/wechat-draft build`, `pnpm --filter @mcps/wechat-draft test`, hermes-db targeted tests 的命令、结果、未执行项原因。
  - evidence 2026-06-27: `pnpm --filter @mcps/wechat-draft build` PASS；`pnpm --filter @mcps/wechat-draft test` PASS 44/44；`uv run pytest tests/test_workflow_tools.py tests/test_workflow_repo_sql.py` PASS 10/10。

- [x] T013 [Closeout Prep] 准备 acceptance 输入和 Knowledge Capture
  - scope: future `acceptance.md`, `verify-evidence.md`, roadmap status
  - slice: closeout 可基于三维 Verdict、Bugfix Closure 和 Knowledge Capture 判断完成。
  - blocked_by: T012
  - maps_to: Acceptance Gate / Knowledge Capture / roadmap current feature
  - verify: acceptance 输入包含 Evidence Table、Workflow Replay、Bugfix Closure、remaining risk、follow-up roadmap impact。
  - evidence 2026-06-27: `verify-evidence.md` 包含 Evidence Table 输入、diffusion check、remaining risk；tasks 覆盖三维 Verdict 所需的 component/workflow/user-visible 证据。下一阶段可进入 `verify` 后生成 `acceptance.md`。

---

## 依赖与顺序

- 关键路径：T001 -> T002 -> T003 -> T004 -> T005/T006 -> T007 -> T008 -> T009 -> T010/T011 -> T012 -> T013。
- T005 和 T006 可在 T002 后并行，但 T007 依赖二者的错误语义稳定。
- T008 可在 T002 后与 WeChat slice 并行；T009 依赖 T008 的 outcome shape。
- T010 必须等核心 contract 落地后再写，避免文档先行后漂移。
- T011 是扩散检查，必须在主要实现完成后执行。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|-------------|----------|
| US1 constraints discoverability | T003, T004 |
| US2 actionable remediation | T002, T005, T006, T007, T009 |
| US3 artifact idempotency/conflict explicit | T008, T009 |
| US4 executable happy path docs | T010 |
| Bugfix loop breaker | T001, T011, T012, T013 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|----------------------|----------|----------|
| ADR-001 extend existing envelopes | T002, T005, T007, T009 | T012 |
| ADR-002 no `force_update` | T008, T009 | T011, T012 |
| ADR-003 conservative WeChat limits | T003, T004, T010 | T012 |
| 可恢复性 | T002, T005, T006, T007, T009 | T012 |
| 一致性 | T003, T004 | T012 |
| 安全性 | T005, T009, T011 | T012 |
| 可演进性 | T010, T013 | acceptance closeout |

---

## Context Manifest

已生成 `context-manifest.md`。本 feature 命中 multi-stage-workflow、external-side-effects、artifact-handoff、user-visible-output、prior-closure-failure 和 bugfix-loop-breaker；实现/验证必须保留高信号上下文，避免跨会话丢失边界和官方限制。

---

## Stage Readiness

- 推荐下一步：`verify`
- 阻塞项：无
- 原因：13/13 tasks 已完成，WeChat build/test、Hermes targeted tests、文档更新和 diffusion check 均有 fresh evidence。
