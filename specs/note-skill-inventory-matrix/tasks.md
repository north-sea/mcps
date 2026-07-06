# Tasks: Note Skill Inventory Matrix

**Workspace**: `note-skill-inventory-matrix` | **Date**: 2026-06-27  
**Input**: `specs/note-skill-inventory-matrix/spec.md` + `plan.md`  
**Prerequisites**: spec.md, plan.md

---

## 执行原则

- 本 feature 是文档型 inventory，不修改 `/Users/yqg/learning/biji/note`。
- 任务按可验证切片拆分；每个切片必须能产出可定位证据。
- `migration-matrix.md` 中的候选落点保持 `candidate` / `needs reconciliation`，不得宣称已迁移。
- 删除门禁只定义证据要求，不触发删除、归档、外部同步或提交。

---

## Phase 1: SDD State And Scope

**目标**: 激活 roadmap，建立当前 feature 的 SDD 上下文，并锁定“不迁移、不删除”的范围。

- [x] T001 [State] 激活 note skill migration roadmap
  - scope: `specs/.active`, `specs/note-skill-migration-roadmap/roadmap.md`
  - slice: `.active` 与 roadmap `Current Feature` 同步到 `note-skill-inventory-matrix`
  - blocked_by: none
  - maps_to: FR-005, roadmap consistency
  - verify: `cat specs/.active` 输出 `note-skill-inventory-matrix`；roadmap `Current Feature` 同值

- [x] T002 [Spec] 固化 inventory feature 需求边界
  - scope: `specs/note-skill-inventory-matrix/spec.md`
  - slice: spec 明确 44 个 skill、候选归属、删除门禁和不修改 note 源目录
  - blocked_by: T001
  - maps_to: US1, US2, US3, FR-001..FR-006
  - verify: `spec.md` 包含 Feature Traits、User Stories、Requirements、Out of Scope

- [x] T003 [Plan] 设计文档型 inventory 方案
  - scope: `specs/note-skill-inventory-matrix/plan.md`
  - slice: plan 说明 Markdown 矩阵、Producer-Consumer Matrix、ADR、验证路径和 no data-model 决策
  - blocked_by: T002
  - maps_to: ADR-001..ADR-004, Quality Attributes
  - verify: `plan.md` 包含 Producer-Consumer Matrix、Lightweight ADR、Verification Strategy

---

## Phase 2: Migration Matrix

**目标**: 建立 44 行可审查矩阵，覆盖类别、触发条件、候选归属、优先级和删除门禁。

- [x] T004 [US1] 发现并记录全部 note skills
  - scope: `/Users/yqg/learning/biji/note/.agents/skills`, `/Users/yqg/learning/biji/note/.hermes/skills`, `migration-matrix.md`
  - slice: 实际 `SKILL.md` 数量为 44，矩阵正文行数为 44
  - blocked_by: T003
  - maps_to: US1-1, US1-2, FR-001, 完整性
  - verify: `find ... -name SKILL.md | wc -l` 与矩阵行数检查均为 44

- [x] T005 [US2] 为每个 skill 标注候选归属和优先级
  - scope: `specs/note-skill-inventory-matrix/migration-matrix.md`
  - slice: 每行包含 `agents 既有落点`、`mcps 既有落点`、`目标归属`、`优先级`
  - blocked_by: T004
  - maps_to: US2-1, US2-2, FR-002, FR-003, 保守性
  - verify: P0 rows spot check 均包含候选归属和 `needs reconciliation`

- [x] T006 [US3] 为每个 skill 标注删除门禁
  - scope: `specs/note-skill-inventory-matrix/migration-matrix.md`
  - slice: 每行 `删除门禁` 都要求替代入口、smoke/验证证据或 README 指针
  - blocked_by: T004
  - maps_to: US3-1, US3-2, FR-004, FR-005
  - verify: 矩阵每个 skill row 的 `删除门禁` 列非空；没有 note 源目录改动

---

## Phase 3: Context And Verification

**目标**: 留下后续 implement/verify 所需上下文，并用 fresh evidence 验证矩阵闭环。

- [x] T007 [Context] 创建 context manifest
  - scope: `specs/note-skill-inventory-matrix/context-manifest.md`
  - slice: implement/check context 覆盖 spec、plan、tasks、migration matrix 和 roadmap
  - blocked_by: T003
  - maps_to: multi-stage-workflow, artifact-handoff
  - verify: manifest 条目都有 reason；Required local files 存在

- [x] T008 [Verify] 生成 verify evidence
  - scope: `specs/note-skill-inventory-matrix/verify-evidence.md`
  - slice: 记录 source count、matrix row count、roadmap active consistency、P0 spot check、scope boundary
  - blocked_by: T004, T005, T006, T007
  - maps_to: Evidence Gate, Quality Attributes
  - verify: `verify-evidence.md` 包含命令、结果、结论和剩余风险

- [x] T009 [Closeout] 生成 acceptance record 并更新 roadmap
  - scope: `specs/note-skill-inventory-matrix/acceptance.md`, `specs/note-skill-migration-roadmap/roadmap.md`
  - slice: closeout 记录三维 Verdict、Knowledge Capture、提交状态和下一推荐 feature
  - blocked_by: T008
  - maps_to: Workflow Replay, 三维 Verdict, roadmap completion log
  - verify: acceptance Overall PASS/CONDITIONAL/FAIL 明确；roadmap completion log 更新

---

## 依赖与顺序

- 关键路径：T001 → T002 → T003 → T004 → T005/T006/T007 → T008 → T009。
- T005 和 T006 可并行，因为都消费 T004 的矩阵基础。
- T008 必须在矩阵和 manifest 完成后执行，避免无 fresh evidence 收尾。
- T009 必须在 T008 之后执行，不能用任务完成状态替代验证证据。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|---|---|
| US1 盘点全部 note skills | T004, T008 |
| US2 标注迁移候选归属 | T005, T008 |
| US3 建立删除门禁 | T006, T008, T009 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|---|---|---|
| ADR-001 Markdown 矩阵 | T004, T005, T006 | T008 |
| ADR-002 候选落点不等于已验证 | T005 | T008 |
| ADR-003 不修改 note 源目录 | T001, T006 | T008, T009 |
| ADR-004 不生成 data-model.md | T003 | T009 |
| 完整性 | T004 | T008 |
| 可追溯性 | T004, T005 | T008 |
| 保守性 | T005 | T008 |

---

## Context Manifest

已生成 [context-manifest.md](context-manifest.md)，因为该 feature 命中 `multi-stage-workflow`、`artifact-handoff`、`user-visible-output` 和 `prior-closure-failure`。

---

## Stage Readiness

- 推荐下一步：`closeout complete`；roadmap 下一推荐 feature 是 `agents-capability-reconciliation`
- 阻塞项：无；但 note 源仓已有 dirty skill 文件，严格 clean-source proof 记为 conditional
