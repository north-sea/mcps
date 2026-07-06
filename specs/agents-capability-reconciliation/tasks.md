# Tasks: Agents Capability Reconciliation

**Workspace**: `agents-capability-reconciliation` | **Date**: 2026-06-28  
**Input**: `specs/agents-capability-reconciliation/spec.md` + `plan.md`  
**Prerequisites**: spec.md, plan.md

---

## 执行原则

- 本 feature 是只读对账和文档治理，不修改 `/Users/yqg/learning/biji/note` 或 `/Users/yqg/personal/AI/agents` 运行代码。
- 主要任务按可验证 slice 拆分；每个 slice 都必须能产出可定位证据。
- `capability-reconciliation.md` 必须保留 44/44 skill 行，不合并、不省略、不重命名原始 skill。
- `candidate` 和 `needs reconciliation` 不能直接升级为 `verified`；必须有 evidence-first 判断。
- 删除门禁只更新状态和证据要求，不触发删除、归档、迁移、外部同步或提交。

---

## Phase 1: State, Context, And Reconciliation Frame

**目标**: 锁定 SDD 状态、建立实现上下文和对账表框架，防止后续执行时丢失边界。

- [x] T001 [State] 校验 active feature 与 roadmap current 一致
  - scope: `specs/.active`, `specs/note-skill-migration-roadmap/roadmap.md`
  - slice: 续接执行前能确认 `agents-capability-reconciliation` 是唯一 current feature
  - blocked_by: none
  - maps_to: roadmap consistency, FR-009
  - verify: `cat specs/.active` 输出 `agents-capability-reconciliation`；roadmap `Current Feature` 同值

- [x] T002 [Context] 维护 context manifest
  - scope: `specs/agents-capability-reconciliation/context-manifest.md`
  - slice: implement/check/research context 覆盖 spec、plan、tasks、migration matrix、roadmap 和关键外部仓路径
  - blocked_by: T001
  - maps_to: multi-stage-workflow, artifact-handoff
  - verify: manifest 每条 entry 都有 reason；Required local files 存在

- [x] T003 [Framework] 创建 `capability-reconciliation.md` 框架
  - scope: `specs/agents-capability-reconciliation/capability-reconciliation.md`
  - slice: 文件包含 Status Rules、Boundary Summary、Reconciliation Table、Downstream Gates、Count Check 章节
  - blocked_by: T001
  - maps_to: ADR-001, ADR-002, FR-001, FR-002
  - verify: `rg` 能找到 `## Status Rules`, `## Boundary Summary`, `## Reconciliation Table`, `## Downstream Gates`, `## Count Check`

- [x] T004 [Framework] 固化 status enum 和 evidence-first 规则
  - scope: `capability-reconciliation.md`
  - slice: 表前说明 `verified`, `partial`, `absent`, `stale`, `contradictory`, `not-applicable`, `needs-user-decision` 的判定口径
  - blocked_by: T003
  - maps_to: FR-002, ADR-002, 保守性
  - verify: `rg -n "verified|partial|absent|stale|contradictory|not-applicable|needs-user-decision" capability-reconciliation.md`

---

## Phase 2: P0/P1 Capability Slices

**目标**: 优先对账后续 roadmap 最容易阻塞的高优先级能力。

- [x] T005 [US1/US2] 对账 P0 shared foundation rows
  - scope: `content-ops`, `opencli-integration`, `account-config`, related agents packages and mcps contracts
  - slice: P0 共享底座 rows 有 execution owner、data/contract owner、capability status、evidence、recommended action 和 deletion gate status
  - blocked_by: T003, T004
  - maps_to: US1, US2, FR-002..FR-006, ADR-003
  - verify: P0 rows `content-ops`, `opencli-integration`, `account-config` 均有非空 Evidence 和 Downstream Gate

- [x] T006 [US1/US2] 对账 P0 WeChat/topic rows
  - scope: `topic-radar`, `topic-inbox`, `topic-scout`, `wechat-article-pipeline`, `wechat-writer`; agents `apps/wechat-agent`; mcps `packages/hermes-db`, `packages/wechat-draft`
  - slice: 内容 P0 rows 明确 WeChat agent 执行层、mcps 数据/草稿契约层和未完成 gap
  - blocked_by: T003, T004
  - maps_to: US1, US2, FR-003, FR-004, FR-005, 边界清晰
  - verify: P0 WeChat/topic rows 不把 MCP 写成 writing runtime；有 agents 和 mcps 证据路径或 evidence gaps

- [x] T007 [US1/US2] 对账 P1 content/blog/image/style rows
  - scope: `blog-*`, `wechat-cover`, `wechat-illustration`, `wechat-image-generator`, `content-reviewer`, `content-brainstorm`, `source-import`, `monthly-review`, `style-analyzer`
  - slice: P1 内容和质量 rows 有 owner、status、action，并区分写作 runtime、image workflow、Library ingestion 和 analytics/retrospective
  - blocked_by: T005, T006
  - maps_to: US1, US2, FR-005, FR-006, FR-007
  - verify: P1 content rows 均有 status；模型生成类 rows 的 `Data/Contract Owner` 不替代 `Execution Owner`

- [x] T008 [US1/US2] 对账 P1 novel rows
  - scope: `novel-analyzer`, `novel-memory-workflow`, `novel-trend-scout`, `novel-workflow`, `novelist`, `novel-capture`; agents `apps/novel-agent`; mcps novel specs/tools
  - slice: P1 小说 rows 明确 novel-agent 可复用能力、未完成 retrospective/handoff gap、Library/Memory 边界
  - blocked_by: T003, T004
  - maps_to: US1, US2, FR-003, FR-004, FR-005
  - verify: novel rows 有 agents evidence；涉及规则/资料的 rows 标出 Library/Wiki 或 Memory owner

---

## Phase 3: Remaining Rows And Downstream Gates

**目标**: 补齐 P2/P3 和全量 44 行，并把结果映射到后续 roadmap 门禁。

- [x] T009 [US1] 对账 P2/P3 remaining rows
  - scope: `gemini-image-provider`, `youmind-publisher`, `novel-platform-rules`, `plot-insertion-router`, `qidian-scraper`, `novel-rules-ask`, `xhs-creator`, Hermes ops rows, note tooling rows
  - slice: 低优先级和高副作用 rows 也有明确 status、evidence gap、recommended action、deletion gate status
  - blocked_by: T003, T004
  - maps_to: US1, US2, FR-001, FR-006
  - verify: reconciliation table row count 达到 44；P2/P3 rows 没有空 status

- [x] T010 [US2] 写 Boundary Summary
  - scope: `capability-reconciliation.md`
  - slice: 文档按 WeChat/content、Novel、XHS、Hermes personal ops、Library/Memory、thin-skill/archive 总结 owner 边界
  - blocked_by: T005, T006, T008, T009
  - maps_to: US2, FR-004, FR-005, ADR-002
  - verify: Boundary Summary 明确 agents 执行层与 mcps 数据契约层分离；XHS 标记用户确认门禁

- [x] T011 [US3] 写 Downstream Gates
  - scope: `capability-reconciliation.md`, `specs/note-skill-migration-roadmap/roadmap.md`
  - slice: 每个后续 feature 有 Ready/Conditional/Blocked、required rows、blocking gaps、suggested next stage
  - blocked_by: T005, T006, T007, T008, T009, T010
  - maps_to: US3, FR-007, 可交接性
  - verify: `wechat-content-runtime-contracts`, `knowledge-library-ingestion-plan`, `novel-runtime-contracts`, `xhs-workflow-definition`, `hermes-personal-ops-migration`, `note-thin-shell-and-archive` 均出现在 Downstream Gates

- [x] T012 [US1] 执行 44/44 count 和 empty-field 检查
  - scope: `capability-reconciliation.md`
  - slice: source matrix count 与 reconciliation table count 一致，关键字段没有空值
  - blocked_by: T009, T011
  - maps_to: FR-001, FR-002, FR-009, 完整性
  - verify: source matrix rows = 44；reconciliation rows = 44；status/evidence/downstream gate 关键列无空值或有明确 `none/not-applicable` 原因

---

## Phase 4: Verify And Closeout Prep

**目标**: 生成 fresh evidence，准备 closeout，不跳过验收记录。

- [x] T013 [Verify] 生成 verify evidence
  - scope: `specs/agents-capability-reconciliation/verify-evidence.md`
  - slice: 记录 count check、P0/P1 spot check、status enum check、boundary check、no runtime side effects check
  - blocked_by: T012
  - maps_to: FR-009, Evidence Gate, Quality Attributes
  - verify: `verify-evidence.md` 包含命令、结果、结论和剩余风险

- [x] T014 [Closeout] 生成 acceptance record 并更新 roadmap
  - scope: `specs/agents-capability-reconciliation/acceptance.md`, `specs/note-skill-migration-roadmap/roadmap.md`
  - slice: closeout 记录三维 Verdict、Knowledge Capture、后续推荐 feature 和未解决的 user decision gates
  - blocked_by: T013
  - maps_to: Workflow Replay, 三维 Verdict, roadmap completion log
  - verify: acceptance Overall PASS/CONDITIONAL/FAIL 明确；roadmap completion log 更新；不自动提交

---

## 依赖与顺序

- 关键路径：T001 → T002/T003 → T004 → T005/T006/T008 → T007/T009 → T010 → T011 → T012 → T013 → T014。
- T005、T006、T008 可在 T004 后并行推进，分别处理 shared foundation、WeChat/topic、novel。
- T007 依赖 P0 内容边界基本稳定；T009 可与 T007 部分并行，但必须在 T012 前完成。
- T010 和 T011 是交接层任务，必须在主要 rows 完成后执行。
- T013 不能用任务完成状态替代，必须基于 fresh evidence。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|---|---|
| US1 对账 44 个 note skills | T003, T004, T005, T006, T007, T008, T009, T012 |
| US2 明确 agents / mcps 边界 | T005, T006, T007, T008, T010 |
| US3 生成后续 roadmap 门禁 | T011, T013, T014 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|---|---|---|
| ADR-001 Markdown 对账表 | T003 | T012, T013 |
| ADR-002 保守状态枚举 | T004 | T012, T013 |
| ADR-003 不做自动扫描脚本 | T005-T011 | T013 |
| ADR-004 不生成 data-model.md | T003, T014 | T013 |
| 完整性 | T009, T012 | T013 |
| 可追溯性 | T005-T009 | T013 |
| 边界清晰 | T006, T010 | T013 |
| 可交接性 | T011 | T014 |

---

## Context Manifest

已生成 [context-manifest.md](context-manifest.md)，因为该 feature 命中 `multi-stage-workflow`、`artifact-handoff`、`user-visible-output` 和 `prior-closure-failure`。

---

## Stage Readiness

- 推荐下一步：`execute-plan`
- 阻塞项：无；执行阶段应先完成 T001-T004，再分块推进 P0/P1 rows，对账完成后再进入 verify。
