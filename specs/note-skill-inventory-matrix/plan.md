# Implementation Plan: Note Skill Inventory Matrix

**Workspace**: `note-skill-inventory-matrix` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/note-skill-inventory-matrix/spec.md`

---

## Summary

本 feature 采用最小文档型方案：用 [migration-matrix.md](migration-matrix.md) 作为 44 个 note skill 的唯一盘点产物，用只读命令验证源 skill 数量、矩阵行数和 roadmap/active 一致性。

当前不新增运行时代码、不写自动迁移脚本、不接入外部 Memory/Library/API；所有候选归属都保持 `needs reconciliation`，交给后续 `agents-capability-reconciliation` 验证。

---

## Continuation Preflight

| 检查项 | 结果 |
|---|---|
| Feature 来源 | `specs/.active` |
| Active feature | `note-skill-inventory-matrix` |
| Feature directory | exists |
| `spec.md` | exists |
| `plan.md` | 本文件 |
| `tasks.md` | missing，下一阶段生成 |
| Roadmap current | `note-skill-inventory-matrix` |
| Roadmap / active consistency | PASS |

**推荐阶段依据**: `spec.md` 已存在，`plan.md` 缺失；按 SDD continuation routing 进入 `plan`。

---

## Architecture Overview

这是一个文档治理 feature，不改变系统运行结构。

```text
/Users/yqg/learning/biji/note
  .agents/skills/*/SKILL.md
  .hermes/skills/*/SKILL.md
        |
        | read-only inventory
        v
specs/note-skill-inventory-matrix/migration-matrix.md
        |
        | consumed by
        v
agents-capability-reconciliation
wechat-content-runtime-contracts
knowledge-library-ingestion-plan
novel-runtime-contracts
hermes-personal-ops-migration
note-thin-shell-and-archive
```

模块边界：

- `note` 源目录：只读输入，不允许本 feature 修改。
- `migration-matrix.md`：本 feature 的核心交付物，记录候选归属和删除门禁。
- `roadmap.md`：只记录当前 feature 状态和下一推荐 feature。
- 后续 feature：消费矩阵，但必须重新验证候选落点，不能把候选当事实。

---

## Architecture Reference

完整架构质量门不展开为成熟系统设计，因为本 feature 不引入新系统、服务、存储、队列、缓存、权限或外部依赖。唯一可参考模式是“inventory + decision table + evidence gate”的治理型文档流。

| 参考模式 / 模板 | 来源 URL | 适配点 | 不适配点 | 当前阶段 |
|---|---|---|---|---|
| Decision table / inventory gate | UNVERIFIED | 适合把 44 个 skill 的候选归属、风险和门禁放在一处审查 | 不需要引入规则引擎、数据库或自动化迁移器 | MVP |

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| `note-skill-inventory-matrix` specify/plan/tasks | `migration-matrix.md` | `agents-capability-reconciliation` | 对账 feature 能逐行读取 `Skill`、候选 `agents 既有落点`、`mcps 既有落点`、`目标归属` 并更新验证状态 |
| `note-skill-inventory-matrix` | 44/44 count check | `verify` / `closeout` | `find ... -name SKILL.md` 的数量与矩阵正文行数一致 |
| `note-skill-inventory-matrix` | deletion gate column | `note-thin-shell-and-archive` | 每个 skill 删除前能引用对应门禁，不允许无替代入口直接删除 |
| `note-skill-inventory-matrix` | category and priority tags | roadmap later waves | 后续 feature 能按 P0/P1/P2/P3 和类别选择推进顺序 |

**孤儿 artifact 处理**: 无孤儿 artifact。`migration-matrix.md` 是后续 Wave 0 和 Wave 4 的共享输入；count check 和 deletion gate 都有明确 verify/closeout 消费方。

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|---|---|---|---|
| 完整性 | 44/44 note skills 进入矩阵 | 保留源目录 count check，不手工宣称完成 | `find ... -name SKILL.md` 与矩阵正文行数一致 |
| 可追溯性 | 每行能回到原始 skill 目录 | 路径列使用 note 下相对路径，不抽象成类别名 | spot check 路径存在 |
| 保守性 | 候选归属不等于已验证归属 | `agents/mcps 既有落点` 用 `candidate` / `needs reconciliation` 标注 | grep 检查候选列没有伪装成 PASS |
| 可审查性 | 人能直接阅读和修改 | 使用 Markdown 表格，不引入 JSON/DB | 文件在 repo 中可 diff |
| 无副作用 | 不修改 note 源目录 | 本 feature 只写 `specs/` | git status / diff 不包含 note 路径 |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|---|---|---|---|---|---|
| ADR-001: 使用 Markdown 矩阵作为 MVP 载体 | 当前目标是人工审查迁移路线，不是自动迁移 | A: Markdown table; B: JSON/YAML inventory; C: SQLite/DB | 选择 Markdown table | 后续机器处理较弱，但审查和 diff 最直接 | UNVERIFIED |
| ADR-002: 本 feature 不验证 agents/mcps 候选落点 | Roadmap 已定义对账为独立 feature | A: 当前 feature 完成所有对账; B: 当前 feature 只列候选 | 选择 B | 矩阵不是最终迁移结论，需要后续对账 | roadmap.md |
| ADR-003: 不修改 note 源目录 | 删除或迁移前必须有替代路径和 smoke 证据 | A: inventory 后直接清理; B: 只建立 deletion gate | 选择 B | 旧 registry 暂时继续存在 | spec.md |
| ADR-004: 不为矩阵生成 data-model.md | 实体关系已在 spec 和矩阵列中表达，未新增存储 schema | A: 单独 data-model; B: plan 中描述核心实体 | 选择 B | 若后续要机器化矩阵，需补数据模型 | UNVERIFIED |

---

## Key Design Decisions

### Decision 1: 只做文档型 inventory，不做自动迁移器

- **背景**: 当前最大风险是误删或重复造能力；自动化迁移会在归属未对账前放大风险。
- **选项**:
  - A: 写脚本读取所有 `SKILL.md` 并自动生成归属。
  - B: 维护人工可审查矩阵，配合只读命令做完整性校验。
- **结论**: 选择 B。归属判断需要结合 roadmap 边界、agents 完成度和用户偏好，不适合自动决定。
- **影响**: 后续任务以校验和补全矩阵为主；不会触碰 note 源目录。
- **来源**: `spec.md` / `roadmap.md`

### Decision 2: 候选落点必须保持未验证状态

- **背景**: agents 仓已有 apps/packages/specs，但 roadmap 明确记录完成度混杂。
- **选项**:
  - A: 当前矩阵直接判定最终 owner。
  - B: 当前矩阵只标候选 owner，并要求后续对账验证。
- **结论**: 选择 B。
- **影响**: `agents-capability-reconciliation` 是硬门禁，不能跳过。
- **来源**: `roadmap.md`

### Decision 3: 删除门禁作为首轮矩阵必填列

- **背景**: roadmap 不变量要求“不先删 skill，再找替代品”。
- **选项**:
  - A: 先分类，删除门禁等最后再补。
  - B: 每行从一开始就带 deletion gate。
- **结论**: 选择 B。
- **影响**: 矩阵更长，但后续清理阶段不会缺少安全约束。
- **来源**: `spec.md`

---

## YAGNI Decision Ladder

| 模块 / 产物 | 停止层级 | 跳过内容 | 理由 |
|---|---|---|---|
| `migration-matrix.md` | 5. 能用简单表格表达 | JSON schema、数据库、生成器脚本 | 44 行规模适合人工审查，Markdown diff 足够 |
| Count check | 2. 标准 shell 能做 | 自定义 validator | `find`、`awk`、`wc` 已能覆盖核心完整性 |
| Roadmap 状态 | 5. 直接改现有 markdown | 新状态机或 metadata 文件 | SDD 已使用 `.active` 和 `roadmap.md` 表达状态 |
| Deletion gate | 5. 表格列 | 独立 gate DSL | 当前只需要人工审查条件，不需要自动执行 |

---

## Module Design

### Module: Inventory Matrix

**职责**: 记录 44 个 note skill 的迁移候选、优先级和删除门禁。

**改动概述**: 维护 [migration-matrix.md](migration-matrix.md) 的表格内容和 count check。

**关键接口 / 行为**:

```text
Input:
  - note/.agents/skills/*/SKILL.md
  - note/.hermes/skills/*/SKILL.md
  - note-skill-migration-roadmap/roadmap.md

Output:
  - migration-matrix.md
  - Count Check section

Rules:
  - every discovered SKILL.md must map to one matrix row
  - candidate landing zones stay marked needs reconciliation
  - deletion gate is required for every row
```

**注意事项**:

- 不把 `candidate` 写成 PASS。
- 不新增或删除 note skill。
- 不把写作生成迁入 MCP。

### Module: SDD Roadmap State

**职责**: 保持 `.active` 与 roadmap current 一致。

**改动概述**: `specs/.active` 指向 `note-skill-inventory-matrix`；roadmap `Current Feature` 同步。

**关键接口 / 行为**:

```text
specs/.active == note-skill-inventory-matrix
specs/note-skill-migration-roadmap/roadmap.md Current Feature == note-skill-inventory-matrix
```

**注意事项**:

- 当前 feature closeout 前不切换到 `agents-capability-reconciliation`。
- closeout 后再更新 roadmap completion log 和 next feature。

### Module: Verification Commands

**职责**: 给 verify/closeout 提供 fresh evidence。

**改动概述**: 使用只读 shell 命令验证数量、状态和无副作用边界。

**关键接口 / 行为**:

```text
find note/.agents/skills note/.hermes/skills -name SKILL.md -type f | wc -l
awk matrix rows between "## Matrix" and "## Count Check"
cat specs/.active
git status --short specs/ /Users/yqg/learning/biji/note
```

**注意事项**:

- `git status` 对 note 外部路径可能受仓库边界影响；验证无副作用时以当前 repo diff 和人工说明结合。
- 若实际 skill 数不等于 44，必须回到 `specify` 或更新矩阵。

---

## Data Model

不生成独立 `data-model.md`。本 feature 没有新增数据库、持久状态 schema 或运行时实体；核心实体已由 `spec.md` 的 Key Entities 和 `migration-matrix.md` 列结构表达。

若后续决定把矩阵机器化为 JSON/YAML 或数据库，再由对应 feature 补充 data model。

---

## Project Structure

```text
specs/
  .active
  note-skill-migration-roadmap/
    roadmap.md
  note-skill-inventory-matrix/
    spec.md
    plan.md
    migration-matrix.md
    tasks.md              # next stage
    verify-evidence.md    # verify stage
    acceptance.md         # closeout stage
```

---

## Risks and Tradeoffs

- **矩阵人工维护会出错**: 用 count check、路径 spot check 和后续对账降低风险。
- **候选归属可能过早影响判断**: 所有候选落点必须标 `needs reconciliation`，closeout 不得宣称迁移完成。
- **表格较宽**: 保留宽表，因为它让删除门禁和归属判断在一处可审查。
- **外部 note 目录不在本 repo**: 本 feature 不写外部目录；验证以只读 discover 命令为准。

---

## Evolution Path

- **MVP**: Markdown 矩阵 + 手动审查 + 只读 count check。
- **成长期**: `agents-capability-reconciliation` 更新每行候选落点为 verified/rejected/needs work。
- **成熟期**: 若矩阵需要被工具消费，再迁为 YAML/JSON manifest，并生成 Markdown view。

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。当前不引入数据库、生成器或自动迁移器。
- 是否引用了外部模式但没有适配检查：否。只用治理型决策表作为轻量参考，来源标记 `UNVERIFIED`。
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。只新增 SDD 文档。
- 是否把候选归属误当成完成迁移：否。矩阵明确保留 `needs reconciliation`。

---

## Verification Strategy

后续 `verify` 阶段至少需要记录这些 fresh evidence：

1. 源目录 skill 数量：
   ```bash
   find /Users/yqg/learning/biji/note/.agents/skills /Users/yqg/learning/biji/note/.hermes/skills -name SKILL.md -type f | wc -l
   ```
2. 矩阵正文行数：
   ```bash
   awk 'BEGIN{in_matrix=0; count=0} /^## Matrix$/{in_matrix=1; next} /^## Count Check$/{in_matrix=0} in_matrix && /^\\| `/{count++} END{print count}' specs/note-skill-inventory-matrix/migration-matrix.md
   ```
3. SDD 状态一致性：
   ```bash
   cat specs/.active
   rg -n "^\\*\\*Current Feature\\*\\*:" specs/note-skill-migration-roadmap/roadmap.md
   ```
4. 范围边界：
   ```bash
   git status --short
   ```
   验证本 feature 只新增/修改 `specs/` 文档，不修改 note skill 源文件。
5. 内容质量 spot check：
   - 至少抽查 P0 rows：`account-config`, `content-ops`, `opencli-integration`, `topic-radar`, `topic-inbox`, `topic-scout`, `wechat-article-pipeline`, `wechat-writer`。
   - 检查每行有目标归属、优先级、删除门禁和 `needs reconciliation`。

---

## Stage Readiness

- 是否需要 `data-model.md`：不需要。本 feature 不新增运行时存储或状态 schema；矩阵列本身已表达实体属性。
- 下一步建议：`tasks`
- 阻塞项（如有）：无。任务阶段应拆出矩阵补全、P0 spot check、状态一致性校验、verify evidence 生成和 closeout 准备。

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|---|---|---|
| plan.md | 必须 | 本文件 |
| data-model.md | 不需要 | 无新增存储 schema |
| tasks.md | 后续阶段生成 | 拆出可执行检查点 |
| verify-evidence.md | 后续阶段生成 | 记录 fresh evidence |
| acceptance.md | 后续阶段生成 | 记录三维 Verdict 和 roadmap 影响 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|---|---|---|
| SDD continuation routing | `/Users/yqg/.agents/skills/sdd/references/continuation-routing.md` | 本地 skill reference |
| SDD plan stage | `/Users/yqg/.agents/skills/sdd/references/stages/plan.md` | 本地 skill reference |
| Architecture quality gate | `/Users/yqg/.agents/skills/sdd/references/architecture-quality-gate.md` | 本地 skill reference |
| Roadmap boundary | `specs/note-skill-migration-roadmap/roadmap.md` | 本 repo artifact |
| Feature requirements | `specs/note-skill-inventory-matrix/spec.md` | 本 repo artifact |
