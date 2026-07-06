# Tasks: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture` | **Date**: 2026-07-01  
**Input**: `specs/knowledge-memory-architecture/spec.md` + `plan.md` + `data-model.md`  
**Prerequisites**: spec.md, plan.md, data-model.md

---

## 执行原则

- 本 feature 先交付架构边界、同步/备份门禁和配置审查，不执行 NAS 容器重启。
- 不把本机 Codex/Claude Code 配置切到 NAS nmem。
- 不保存真实 token、API key、cookie、bearer。
- 不做双主同步；所有导入/覆盖必须人工确认。
- 不把替代工具 POC 混入当前完成条件。

---

## Phase 1: 决策与路由边界

**目标**: 把 nmem、NAS、Hermes、本机 agent、Library/Markdown/Git 的职责边界写成可审查产物。

- [x] T001 [US1] 创建 memory routing policy
  - scope: `specs/knowledge-memory-architecture/routing-policy.md`
  - slice: 明确 Hermes 可写 NAS nmem；Codex/Claude Code 不写 NAS nmem；长期资料写 Library/Markdown/Git
  - blocked_by: none
  - maps_to: US1, US2, FR-001, FR-002, FR-003, ADR-001, ADR-002, 一致性
  - verify: policy 中每个 `MemoryEndpoint` 都有 read/write/mode/timeout_policy；`mac-codex-claude-to-nas-nmem.write_allowed=false`

- [x] T002 [US1] 创建 knowledge class table
  - scope: `specs/knowledge-memory-architecture/knowledge-classes.md`
  - slice: durable decision、procedure、source material、bookmark inbox、Hermes runtime memory、Codex evidence、fallback write 都有目标系统和同步方式
  - blocked_by: T001
  - maps_to: US1, US3, FR-001, FR-004, Library/Memory 分层
  - verify: 每类资料都有 source_of_truth、runtime_index、sync_method、retention、deletion_gate_impact

- [x] T003 [US1] 替代工具评估门禁
  - scope: `specs/knowledge-memory-architecture/tool-evaluation-gates.md`
  - slice: nmem、Mem0/OpenMemory、Zep/Graphiti、Obsidian/Markdown/Git、Karakeep 的适用/不适用范围和 POC 触发条件
  - blocked_by: T001
  - maps_to: US1, FR-006, FR-007, ADR-004, 可演进性
  - verify: 结论明确为“继续 nmem 但降级职责”；替代工具不进入当前实现范围

---

## Phase 2: 同步、备份与降级策略

**目标**: 明确如何备份 NAS nmem、如何避免双主、写超时时如何降级。

- [x] T004 [US2] 定义 nmem export/import 策略
  - scope: `specs/knowledge-memory-architecture/sync-strategy.md`
  - slice: NAS nmem export 产物、备份目录、校验、导入模式、冲突处理和回滚原则；补充 NAS domain space 写入后的 delta sync 和 space mapping
  - blocked_by: T001, T002
  - maps_to: US2, US3, FR-004, NFR-002, NFR-003, 可恢复性
  - verify: 策略默认 `merge` 或 `skip`，禁止默认 `overwrite`；说明何时人工导入 Mac

- [x] T005 [US2] 定义 write timeout 降级策略
  - scope: `specs/knowledge-memory-architecture/fallback-policy.md`
  - slice: memory add/update 超时时不阻塞 Hermes，不盲目重复写，先确认副作用，必要时写 fallback queue/log；记录本机 NowledgeGraph 已是当前主数据副本，且本机 nmem 重启后已恢复
  - blocked_by: T001
  - maps_to: US2, FR-005, FR-008, NFR-001, 可用性
  - verify: 覆盖 MCP 写工具超时但可能已落库、本机 nmem degraded、NAS remote API 超时三种场景

- [x] T006 [US2] 配置审查 checklist
  - scope: `specs/knowledge-memory-architecture/config-checklist.md`
  - slice: 开启 NAS nmem 前后应检查哪些配置，不包含真实 token
  - blocked_by: T001, T004, T005
  - maps_to: FR-002, FR-011, 安全性
  - verify: checklist 包含 Hermes endpoint、本机 Codex/Claude Code 禁用 NAS write、敏感信息脱敏、export 备份、NAS-to-local space mapping 和非 overwrite 导入

---

## Phase 3: Roadmap 和后续 feature 对齐

**目标**: 让当前 memory 架构成为 `knowledge-library-ingestion-plan` 和 note skill 删除门禁的前置条件。

- [x] T007 [US3] 回填 note skill roadmap 依赖
  - scope: `specs/note-skill-migration-roadmap/roadmap.md`
  - slice: `knowledge-library-ingestion-plan` 依赖本 feature closeout；`wechat-content-runtime-contracts` 暂停收尾后续可恢复
  - blocked_by: T001, T002, T004
  - maps_to: US3, FR-009
  - verify: roadmap current、next recommended、feature table、后置 feature 一致

- [x] T008 [US3] 更新 content runtime closeout 输入
  - scope: `specs/wechat-content-runtime-contracts/tasks.md`, `verify-evidence.md` 或后续 acceptance 输入
  - slice: 说明内容 runtime closeout 的 Library/Memory 边界依赖本 feature，而不是直接让 nmem 承担长期资料主库
  - blocked_by: T002, T007
  - maps_to: US3, FR-009
  - verify: 不改变已完成 T006/T007 evidence；只增加 memory/Library 边界引用

---

## Phase 3b: 单向同步实现规划

**目标**: 把 NAS domain space -> 本机 matching space 的同步实现拆成可执行、可验证、默认 dry-run 的 slice。

- [x] T009 [US4] 定义 sync implementation artifact
  - scope: `specs/knowledge-memory-architecture/sync-implementation.md`
  - slice: 明确 inventory、preview、import 三阶段；默认 dry-run；import 需要 preview run-id 和人工确认
  - blocked_by: T004
  - maps_to: US4, FR-012, FR-013, FR-014, ADR-003
  - verify: 文档包含 commands shape、mapping template、safety gates、open implementation questions

- [x] T010 [US4] 设计 NAS-to-local space mapping 文件
  - scope: future `scripts/nmem-space-map.example.json` or documented JSON template
  - slice: selfmedia/novel/xhs/hermes generic 都有 domain、NAS space、local space、import_mode、auto_import_allowed
  - blocked_by: T009
  - maps_to: US4, FR-012, 一致性
  - verify: 默认 import mode 是 `merge` 或 `skip`；没有默认 `overwrite`

- [x] T011 [US4] 设计 dry-run preview 命令
  - scope: future `scripts/nmem-nas-domain-sync.sh preview`
  - slice: 可以在不修改本机 nmem 的情况下生成 export archive、preview report、dedupe estimate
  - blocked_by: T009, T010
  - maps_to: US4, FR-013, NFR-005, 可恢复性
  - verify: preview 缺 mapping 时失败；preview 输出不含 secrets

- [x] T012 [US4] 设计 import gate
  - scope: future `scripts/nmem-nas-domain-sync.sh import`
  - slice: import 必须引用 preview run-id，必须显式 confirm，只允许 merge/skip，写 audit record
  - blocked_by: T011
  - maps_to: US4, FR-012, FR-013, 安全性, 一致性
  - verify: overwrite 被拒绝；无 preview run-id 被拒绝；无 confirm 被拒绝

---

## Phase 4: 验证与收尾准备

**目标**: 确认文档、配置和安全边界无矛盾，准备 closeout。

- [x] T013 [Verify] 文档一致性检查
  - scope: `specs/.active`, `roadmap.md`, `spec.md`, `plan.md`, `data-model.md`, generated policy docs
  - slice: active feature 与 roadmap current 一致；没有两个 feature 同时 current
  - blocked_by: T007, T009
  - maps_to: SDD consistency, FR-009
  - verify: `rg` 检查 current/status/next recommended 无冲突

- [x] T014 [Verify] 敏感信息扫描
  - scope: `specs/knowledge-memory-architecture/*.md`, touched roadmap docs
  - slice: 不包含真实 token、API key、cookie、bearer
  - blocked_by: T006
  - maps_to: FR-011, 安全性
  - verify: `rg -i "token|api[_-]?key|cookie|bearer"` 只命中文档规则或占位引用，不命中真实值

- [x] T015 [Verify] 三维 verdict evidence
  - scope: `specs/knowledge-memory-architecture/verify-evidence.md`
  - slice: Component capability、Workflow closure、User-visible outcome 均有证据或明确延后项
  - blocked_by: T001-T014
  - maps_to: Evidence Gate, Workflow Replay
  - verify: evidence table 覆盖所有 FR/NFR 和关键 ADR

- [x] T016 [Closeout Prep] 准备 acceptance
  - scope: `specs/knowledge-memory-architecture/acceptance.md`
  - slice: 记录最终推荐：继续 nmem 但降级职责，NAS nmem Hermes-only，长期资料主库为 Library/Markdown/Git，替代工具为后续 POC
  - blocked_by: T015
  - maps_to: acceptance, roadmap closeout
  - verify: acceptance 写入 verdict、阻塞项、延后项、roadmap 影响和下一步推荐

---

## 依赖与顺序

关键路径：

1. T001 routing policy
2. T002 knowledge class table
3. T004 sync strategy
4. T005 fallback policy
5. T006 config checklist
6. T007-T008 roadmap/content runtime 对齐
7. T009-T012 单向同步实现规划
8. T013-T016 verify / closeout

可并行：

- T003 可在 T001 后与 T002/T004 并行。
- T004 和 T005 可在 T001/T002 后并行。
- T010-T012 属于 sync implementation 子链，T009 后顺序推进。
- T013/T014 可在文档齐备后并行。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|-------------|----------|
| US1 明确知识主库与 memory 职责 | T001, T002, T003 |
| US2 NAS nmem Hermes-only | T001, T004, T005, T006 |
| US3 Library ingestion 前置条件 | T002, T007, T008, T016 |
| US4 NAS domain space 单向同步可执行 | T009, T010, T011, T012 |
| FR-001 / FR-002 / FR-003 | T001 |
| FR-004 | T004 |
| FR-005 / FR-008 | T005 |
| FR-006 / FR-007 | T003 |
| FR-009 | T007, T008, T013 |
| FR-010 | T006, T016 |
| FR-011 | T006, T014 |
| FR-012 / FR-013 / FR-014 | T009, T010, T011, T012 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|----------------------|----------|----------|
| ADR-001 nmem 降级职责 | T001, T002 | T015, T016 |
| ADR-002 NAS nmem Hermes-only | T001, T006 | T013, T015 |
| ADR-003 export/import 非双主 | T004 | T015 |
| ADR-003 单向 domain sync | T009-T012 | T015 |
| ADR-004 替代工具 POC 门禁 | T003 | T016 |
| 一致性 | T001, T004, T007 | T013 |
| 可用性 | T005 | T015 |
| 可恢复性 | T004 | T015 |
| 安全性 | T006 | T014 |
| 可演进性 | T003 | T016 |

---

## Stage Readiness

- 推荐下一步：`execute-plan`
- 阻塞项（如有）：无；执行范围是文档和配置审查，不涉及立即重启 NAS 或迁移数据。
