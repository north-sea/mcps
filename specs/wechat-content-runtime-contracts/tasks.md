# Tasks: WeChat Content Runtime Contracts

**Workspace**: `wechat-content-runtime-contracts` | **Date**: 2026-06-28  
**Input**: `specs/wechat-content-runtime-contracts/spec.md` + `plan.md`  
**Prerequisites**: spec.md, plan.md

---

## 执行原则

- 按端到端 slice 拆分：每个主要任务都必须产出可验证证据或明确阻塞原因。
- 本 feature 不删除、不移动、不归档 `/Users/yqg/learning/biji/note` 中的任何 skill。
- 默认 dry-run / fixture；live 外部服务调用必须 credential-gated 且需要用户明确允许。
- agents 执行层只做引用和证据对账；不要在 mcps 仓重写 agents 已有业务 runtime。

---

## Phase 1: 迁移决策面

**目标**: 先把 owner、替代入口和删除门禁做成可执行决策表，服务后续所有 smoke slice。

- [x] T001 [US1] 创建内容能力 owner table
  - scope: `specs/wechat-content-runtime-contracts/owner-table.md`; 来源为 `../agents-capability-reconciliation/capability-reconciliation.md`
  - slice: content/blog/WeChat/topic/style/image P0/P1 行都有执行归属、契约归属、知识归属、状态、证据缺口和删除门禁
  - blocked_by: none
  - maps_to: US1, FR-001, FR-002, ADR-001, 一致性
  - verify: owner table 行覆盖 `blog-*`, `content-*`, `topic-*`, `wechat-*`, `account-config`, `monthly-review`, `style-analyzer`；Notion/YouMind 标为不再投入 / 后续归档

- [x] T002 [US3] 创建 replacement route docs
  - scope: `specs/wechat-content-runtime-contracts/replacement-routes.md`
  - slice: 旧 note/Hermes skill 能查到替代入口、执行 owner、契约 owner、验证证据和删除门禁
  - blocked_by: T001
  - maps_to: US3, FR-002, FR-007, FR-009, ADR-004, 可演进性
  - verify: 每个 route entry 都包含 `old_skill`, `route_target`, `entry`, `evidence`, `deletion_gate`; 未验证项保持 blocked

- [x] T003 [US1] 记录 negative scope 和归档门禁
  - scope: `owner-table.md`, `replacement-routes.md`
  - slice: `notion-media-orchestrator` 和 `youmind-publisher` 不再进入内容链路，后续只由 `note-thin-shell-and-archive` 处理
  - blocked_by: T001, T002
  - maps_to: US1, FR-008, FR-009, ADR-004
  - verify: 文档中不存在要求补 Notion workflow、YouMind upload smoke 或 YouMind adapter contract 的任务

---

## Phase 2: 主链 handoff evidence

**目标**: 为文章、topic、图片和月报四条主链补 dry-run / fixture evidence。

- [x] T004 [US2] Article-to-draft dry-run 证据
  - scope: `packages/wechat-draft/src/render/*`, `packages/wechat-draft/src/workflow/DraftWorkflow.ts`, agents writer output path evidence
  - slice: writer payload 能被 `MarkdownArticleImporter` / `ArticleDocumentToWechatArtifactBuilder` / `DraftWorkflow` 消费
  - blocked_by: T001
  - maps_to: US2, FR-004, ADR-001, 可验证性
  - verify: 记录 fixture 或测试命令结果到 `specs/wechat-content-runtime-contracts/verify-evidence.md`; 无 live 发草稿
  - evidence: `verify-evidence.md` 记录 `@mcps/wechat-draft` build + test 通过，67 passed

- [x] T005 [US2] Workflow artifact / article state contract 证据
  - scope: `packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py`, `wechat_articles.py`
  - slice: article workflow artifact 可保存 / 读取，支撑 article-to-draft handoff 的状态契约
  - blocked_by: T004
  - maps_to: US2, FR-003, FR-004, 一致性
  - verify: hermes-db 相关 contract test 或 dry-run 结果写入 `verify-evidence.md`
  - evidence: `verify-evidence.md` 记录 hermes-db workflow/article selected tests 通过，纳入 71 passed / 19 skipped

- [x] T006 [US2] Topic shortlist 到 inbox/storage dry-run
  - scope: agents `topic-radar-service.ts`, `topic-service.ts`; `packages/hermes-db/src/hermes_db_mcp/tools/topics.py`
  - slice: topic-radar shortlist 能进入 adopt/inbox/storage 路径
  - blocked_by: T001
  - maps_to: US2, FR-006, ADR-001, 可验证性
  - verify: 记录 shortlist fixture、topic adopt/inbox dry-run 或已有测试证据；Library/Memory 边界写入 evidence
  - evidence: `verify-evidence.md` 记录 topic shortlist/context/health、hermes-db topics 证据；跨仓 `agents-wechat-content-runtime-fixes` 已修复 `cli-topic.test.ts` runner exit 1，原始 mcps-blocking 组合命令通过

- [x] T007 [US2] Image manifest / asset handoff dry-run
  - scope: agents `packages/adapters/src/image/*`; `packages/wechat-draft/src/wechat/AssetSourceLoader.ts`
  - slice: cover / illustration / image manifest 能进入 asset loader 或 draft artifact reference
  - blocked_by: T001
  - maps_to: US2, FR-005, ADR-002, 安全性, 可验证性
  - verify: fixture / dry-run smoke 写入 `verify-evidence.md`; live provider 标记为 credential-gated optional，不作为阻塞项
  - evidence: `verify-evidence.md` 记录 `wechat-draft` asset tests 通过；跨仓 `agents-wechat-content-runtime-fixes` 已验证 agents image closure E2E 通过

- [x] T008 [US2] 内容表现月报样例
  - scope: agents `retrospective-report-service.ts`, `analytics-import-service.ts`; `packages/hermes-db/src/hermes_db_mcp/tools/wechat_analytics.py`
  - slice: analytics fixture 能生成公众号 / 内容表现月报样例
  - blocked_by: T001
  - maps_to: US2, FR-011, ADR-003, user-visible-output
  - verify: `verify-evidence.md` 记录样例报告路径或测试证据；明确不包含个人月报 / 目标回顾
  - evidence: `verify-evidence.md` 记录 retrospective/analytics/config agents subset 通过，hermes-db analytics selected tests 通过

---

## Phase 3: 调用方和漂移检查

**目标**: 防止 plan 与真实入口脱节，确保 route docs 能被后续归档 feature 消费。

- [x] T009 [US1] 调用方对账
  - scope: `owner-table.md`, `replacement-routes.md`; agents CLI/service、wechat-draft package、hermes-db tools
  - slice: 每个主 owner 都有至少一个 caller 或明确的 route target
  - blocked_by: T002, T004, T006, T007, T008
  - maps_to: FR-007, ADR-001, 一致性
  - verify: caller reconciliation section 无空 owner；缺口保留为 blocked gate，不写 verified
  - evidence: `owner-table.md` Caller Reconciliation 覆盖 topic planning、article-to-draft、image/asset、content performance、Library/account-fit source context

- [x] T010 [US1] 架构漂移检查
  - scope: `spec.md`, `plan.md`, `owner-table.md`, `replacement-routes.md`, `capability-reconciliation.md`
  - slice: 最终文档仍遵守“不把写作生成沉到 MCP、不重做 agents runtime、不删 note skill”
  - blocked_by: T009
  - maps_to: FR-003, FR-009, ADR-001, Anti-Pattern Check
  - verify: `verify-evidence.md` 记录 drift check 结论和发现；若发现偏离，回退到 plan 或修正文档
  - evidence: `owner-table.md` Architecture Drift Check 记录 5 个 invariant 全部 PASS；`verify-evidence.md` T010 PASS

- [x] T011 [US3] 删除门禁更新
  - scope: `owner-table.md`, `replacement-routes.md`, `../agents-capability-reconciliation/capability-reconciliation.md`
  - slice: 完成 smoke 的行更新删除门禁；仍缺证据的行保持 blocked；Notion/YouMind 保持归档批次处理
  - blocked_by: T009, T010
  - maps_to: US3, FR-002, FR-009, 可演进性
  - verify: 删除门禁无空值；没有任何行要求本 feature 直接删除 note 源文件
  - evidence: `replacement-routes.md` Deletion Gate Update 明确本 feature 不删除 note skill；thin-shell/archive 留给后续 feature

---

## Phase 4: 验证和收尾材料

**目标**: 为 verify / closeout 准备 fresh evidence，保证后续能判断是否 PASS。

- [x] T012 [Verify] 汇总 verify evidence
  - scope: `specs/wechat-content-runtime-contracts/verify-evidence.md`
  - slice: owner table、route docs、article/topic/image/monthly review evidence、negative scope proof 全部可追踪
  - blocked_by: T004, T005, T006, T007, T008, T011, `knowledge-memory-architecture` closeout
  - maps_to: FR-010, Evidence Gate, Workflow Replay
  - verify: evidence table 每项有 `Requirement`, `Evidence`, `Test or File`, `Verdict`；Library/Memory boundary cites `knowledge-memory-architecture`
  - evidence: `verify-evidence.md` 更新到 2026-07-06，覆盖 T001-T014、negative scope、Memory/Library boundary 和 Library ingestion plan

- [x] T013 [Verify] 运行文档一致性检查
  - scope: `specs/wechat-content-runtime-contracts/*.md`, roadmap, capability reconciliation
  - slice: active feature、roadmap current、任务状态、后续阶段一致
  - blocked_by: T012
  - maps_to: SDD status consistency, FR-010
  - verify: `rg` 检查无旧阶段残留；`specs/.active` 与 roadmap current 一致
  - evidence: `specs/.active` 与 roadmap current 均为 `wechat-content-runtime-contracts`；`verify-evidence.md` T013 PASS

- [x] T014 [Closeout Prep] 准备 acceptance 输入
  - scope: `verify-evidence.md`, `tasks.md`, `roadmap.md`
  - slice: closeout 可直接生成三维 Verdict 和 roadmap 影响
  - blocked_by: T012, T013
  - maps_to: FR-010, Workflow Replay, 三维 Verdict
  - verify: acceptance 所需 evidence、阻塞项、延后项、退役结论、提交结论都有来源
  - evidence: `verify-evidence.md`、`tasks.md`、roadmap 已提供 acceptance 输入；`acceptance.md` 已生成

---

## 依赖与顺序

关键路径：

1. T001 owner table
2. T002 replacement route docs
3. T004/T006/T007/T008 主链 dry-run evidence，可并行
4. T009 caller reconciliation
5. T010 architecture drift check
6. T011 deletion gate update
7. T012-T014 verify / closeout prep

相对独立：

- T003 可在 T001/T002 后立即完成。
- T004/T005 是 article-to-draft 子链，T005 依赖 T004。
- T006 topic、T007 image、T008 monthly review 可并行推进。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|---|---|
| US1 内容 skill 有明确替代归属 | T001, T003, T009, T010 |
| US2 端到端 handoff 有最小 smoke 门禁 | T004, T005, T006, T007, T008, T012 |
| US3 旧 skill 只变薄入口，不提前删除 | T002, T011, T014 |
| FR-001 / FR-002 owner 覆盖 | T001, T009, T011 |
| FR-003 runtime/MCP 边界 | T010 |
| FR-004 article-to-draft | T004, T005 |
| FR-005 image dry-run / optional live | T007 |
| FR-006 topic producer-consumer | T006 |
| FR-007 caller reconciliation | T009 |
| FR-008 Notion/YouMind 排除 | T003 |
| FR-009 不删除 note skill | T002, T010, T011 |
| FR-010 roadmap / acceptance 影响 | T012, T013, T014 |
| FR-011 monthly-review 归内容复盘 | T008 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|---|---|---|
| ADR-001 agents runtime / mcps contract | T001, T004, T005, T006, T009 | T010, T012 |
| ADR-002 图片 live provider 不硬阻塞 | T007 | T012 |
| ADR-003 monthly-review 收窄为内容复盘 | T008 | T012 |
| ADR-004 Notion/YouMind 不再投入 | T003 | T011, T012 |
| 一致性 | T001, T009 | T010, T013 |
| 可验证性 | T004-T008 | T012 |
| 安全性 | T007 | T010, T012 |
| 可演进性 | T002, T011 | T014 |

---

## Context Manifest

已生成 [context-manifest.md](context-manifest.md)。原因：本 feature 命中 `multi-stage-workflow`、`artifact-handoff`、`external-side-effects` 和 `user-visible-output`，且实现 / 验证需要跨 `specs/`、`packages/` 和 agents 仓路径恢复上下文。

---

## Stage Readiness

- 推荐下一步：`execute-plan`
- 阻塞项（如有）：无；任务较多且跨文档 / smoke / 验证，建议先用 execute-plan 控制节奏。
