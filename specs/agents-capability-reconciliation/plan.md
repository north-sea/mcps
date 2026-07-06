# Implementation Plan: Agents Capability Reconciliation

**Workspace**: `agents-capability-reconciliation` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/agents-capability-reconciliation/spec.md`

---

## Summary

本 feature 采用保守的文档治理方案：生成 [capability-reconciliation.md](capability-reconciliation.md)，把上一阶段 44 行 skill inventory 逐行对账到 agents、mcps、Hermes runtime、Library、Memory 或 thin-skill/archive 候选，并用本地证据路径标注状态。

不新增运行时代码、不修改 `/Users/yqg/learning/biji/note`、不修改 `/Users/yqg/personal/AI/agents`，也不执行 smoke、部署或外部同步。当前阶段的价值是把 `candidate` 和 `needs reconciliation` 转为可审查的决策面。

---

## Continuation Preflight

| 检查项 | 结果 |
|---|---|
| Feature 来源 | `specs/.active` |
| Active feature | `agents-capability-reconciliation` |
| Feature directory | exists |
| `spec.md` | exists |
| `plan.md` | 本文件 |
| `tasks.md` | missing，下一阶段生成 |
| Roadmap current | `agents-capability-reconciliation` |
| Roadmap / active consistency | PASS |

**推荐阶段依据**: `spec.md` 已存在，`plan.md` 缺失；按 SDD continuation routing 进入 `plan`。

---

## Architecture Overview

这是一个跨仓只读审计 + 文档产物 feature，不改变系统运行结构。

```text
specs/note-skill-inventory-matrix/migration-matrix.md
        |
        | 44 rows, candidate landing zones
        v
specs/agents-capability-reconciliation/capability-reconciliation.md
        |
        | verified / partial / absent / stale / contradictory / decision-needed
        v
roadmap gates
  - wechat-content-runtime-contracts
  - knowledge-library-ingestion-plan
  - novel-runtime-contracts
  - xhs-workflow-definition
  - hermes-personal-ops-migration
  - note-thin-shell-and-archive
```

只读证据来源：

- `specs/note-skill-inventory-matrix/migration-matrix.md`
- `/Users/yqg/personal/AI/agents/apps`
- `/Users/yqg/personal/AI/agents/packages`
- `/Users/yqg/personal/AI/agents/specs`
- `packages/hermes-db`
- `packages/wechat-draft`
- `specs/*wechat*`, `specs/*novel*`, `specs/*topic*`, `specs/*artifact*`

---

## Architecture Reference

完整架构质量门不展开为系统设计，因为本 feature 不引入新系统、服务、存储、队列、缓存、权限或外部依赖。适用的成熟模式只是轻量参考：

| 参考模式 / 模板 | 来源 URL | 适配点 | 不适配点 | 当前阶段 |
|---|---|---|---|---|
| Decision table / audit matrix | UNVERIFIED | 适合把 44 个 skill 的能力状态、证据路径、边界决策和后续门禁集中审查 | 不需要规则引擎、数据库、自动迁移器或 UI | MVP |
| Architecture Quality Gate | `/Users/yqg/.agents/skills/sdd/references/architecture-quality-gate.md` | 用于防止跨仓边界漂移、记录 ADR 和 closeout 检查点 | 不引入成熟期架构模板 | MVP |

**候选方案讨论跳过原因**: 只有一个合理方向。当前目标是只读对账和文档决策，不是实现迁移器、数据库或自动化状态机；引入结构化存储或脚本会超过当前 feature 范围。

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| `note-skill-inventory-matrix` | `migration-matrix.md` | `agents-capability-reconciliation` | `capability-reconciliation.md` 保留 44/44 skill row，并引用原始候选归属 |
| `agents-capability-reconciliation` | `capability-reconciliation.md` | `wechat-content-runtime-contracts` | 内容/公众号/blog/quality P0/P1 rows 有 owner、status、gaps 和启动条件 |
| `agents-capability-reconciliation` | `capability-reconciliation.md` | `novel-runtime-contracts` | 小说 rows 明确 novel-agent 可复用能力、未完成 specs 和 Library/Memory 边界 |
| `agents-capability-reconciliation` | `capability-reconciliation.md` | `knowledge-library-ingestion-plan` | Library/Wiki 候选 rows 有资料类型、source evidence 和导入门禁 |
| `agents-capability-reconciliation` | `capability-reconciliation.md` | `hermes-personal-ops-migration` | Hermes 运维 rows 明确 runtime/MCP/NAS/Karakeep 等副作用门禁 |
| `agents-capability-reconciliation` | `capability-reconciliation.md` | `xhs-workflow-definition` | `xhs-creator` 明确 `apps/xhs-agent` placeholder 状态和用户确认门禁 |
| `agents-capability-reconciliation` | `capability-reconciliation.md` | `note-thin-shell-and-archive` | 每行保留 deletion gate status 和替代入口证据要求 |
| `agents-capability-reconciliation` | `verify-evidence.md` | `closeout` | fresh evidence 证明 44/44 对账、证据路径可定位、roadmap 状态一致 |

**孤儿 artifact 处理**: 无孤儿 artifact。`capability-reconciliation.md` 是后续 roadmap 的硬输入；`verify-evidence.md` 被 closeout 消费。

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|---|---|---|---|
| 完整性 | 44/44 skill row 保留 | 对账表一行对应一行，不合并、不省略 | 统计 inventory rows 与 reconciliation rows |
| 可追溯性 | 每个状态都有证据路径或 unknown reason | 表中必须有 `Evidence` 和 `Evidence Gaps` 列 | P0/P1 spot check |
| 保守性 | candidate 不自动升级为 verified | 使用明确 status enum；矛盾状态可标 `contradictory` | grep unresolved 状态和 contradiction notes |
| 边界清晰 | agents 执行层与 mcps 数据契约分离 | 表中拆出 `Execution Owner`、`Data/Contract Owner`、`Thin Entry` | 检查模型生成类 rows 不把 MCP 作为 writing runtime |
| 可交接性 | 能驱动后续 feature | 产出 downstream readiness summary | roadmap gates 映射存在 |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|---|---|---|---|---|---|
| ADR-001: 使用 Markdown 对账表 | 当前需要人工审查和 SDD 交接，不需要机器执行 | A: Markdown table; B: JSON/YAML; C: SQLite | 选择 A | 后续机器消费较弱，但最适合审查和 diff | spec.md |
| ADR-002: 状态枚举必须保守 | agents/mcps 状态混杂，candidate 容易被误解为完成 | A: PASS/FAIL; B: 细分 verified/partial/absent/stale/contradictory | 选择 B | 表更宽，但减少误判 | spec.md |
| ADR-003: 不做自动扫描脚本 | 需要语义判断、边界判断和历史 spec 解释 | A: 写脚本自动分类; B: 人工审查 + shell count/spot check | 选择 B | 人工成本更高，但避免伪确定性 | UNVERIFIED |
| ADR-004: 不生成 data-model.md | 没有新增存储 schema、运行时实体或状态机 | A: 单独 data model; B: 在 plan 中定义表列和状态枚举 | 选择 B | 若后续转结构化 manifest，需要补 data model | spec.md |

---

## Key Design Decisions

### Decision 1: 对账表一行对应一个原始 skill

- **背景**: 后续删除门禁需要回到原始 skill；合并 rows 会破坏追溯性。
- **选项**:
  - A: 按领域合并 rows，减少表宽。
  - B: 保留 44 行，一行一个原始 skill。
- **结论**: 选择 B。
- **影响**: 表更长，但能证明 44/44 对账完整。
- **来源**: `migration-matrix.md`, `spec.md`

### Decision 2: 将执行 owner 与数据/契约 owner 分开

- **背景**: roadmap 明确 agents 是业务执行层，mcps 是数据/MCP 契约层；写作生成不能沉到 MCP。
- **选项**:
  - A: 只写单个 owner。
  - B: 拆为 `Execution Owner`, `Data/Contract Owner`, `Thin Entry`, `Knowledge Owner`。
- **结论**: 选择 B。
- **影响**: 能表达 `wechat-writer` 由 agent/runtime 执行、但 consume `wechat-draft` 或 hermes-db 契约的情况。
- **来源**: `roadmap.md`

### Decision 3: status 判断使用 evidence-first

- **背景**: agents 仓存在 PASS、Draft、Ready for Plan、tasks 未完成和 acceptance 矛盾共存的情况。
- **选项**:
  - A: 以文件名或候选路径存在为 verified。
  - B: 以 spec/tasks/acceptance/test/source evidence 综合判断。
- **结论**: 选择 B。
- **影响**: 可能产生更多 `partial` / `contradictory`，但不会误放行后续删除。
- **来源**: explorer findings, `spec.md`

---

## Module Design

### Module: Reconciliation Table

**职责**: 记录 44 个 skill 的能力承接状态、证据、边界和后续动作。

**改动概述**: 新增 [capability-reconciliation.md](capability-reconciliation.md)。

**关键接口 / 行为**:

```text
Input:
  - migration-matrix.md rows
  - local agents apps/packages/specs evidence
  - local mcps packages/specs evidence

Output columns:
  - Skill
  - Priority
  - Category
  - Source Path
  - Original Candidate
  - Execution Owner
  - Data/Contract Owner
  - Knowledge Owner
  - Thin Entry
  - Capability Status
  - Evidence
  - Evidence Gaps
  - Recommended Action
  - Downstream Gate
  - Deletion Gate Status
  - Notes
```

**YAGNI**: 第 5 层停止。Markdown 表格足够表达当前 44 行审查需求，跳过 JSON schema、数据库和生成器。

**注意事项**:

- `verified` 只能用于有 source/test/spec/acceptance 组合证据的行。
- `partial` 适用于有代码或 spec，但缺 smoke、缺 acceptance 或范围不完整。
- `contradictory` 适用于 acceptance 与 tasks、roadmap 或代码现状冲突。
- `needs-user-decision` 适用于是否保留业务线或 owner 无法从现状推断。

### Module: Evidence Classification Rules

**职责**: 给 status 判定统一口径，避免逐行随意判断。

**改动概述**: 在 plan/tasks 中固定 status enum 和判定规则；实现时写入对账表说明区。

**关键接口 / 行为**:

```text
verified:
  code path exists
  and tests/acceptance or roadmap completion evidence exists
  and capability covers note skill trigger

partial:
  code path exists
  but scope incomplete, no fresh smoke, or only part of skill trigger covered

absent:
  no credible local app/package/spec path

stale:
  old plan/spec exists but current app/package reality appears superseded

contradictory:
  tasks, acceptance, roadmap, or source state disagree

not-applicable:
  candidate was wrong layer, e.g. MCP candidate for pure writing runtime

needs-user-decision:
  business scope or retention value cannot be inferred from repo evidence
```

**YAGNI**: 第 5 层停止。用文本规则和表格枚举即可，跳过自动 validator。

### Module: Boundary Decision Summary

**职责**: 汇总每个领域的 owner 边界和不可跨越规则。

**改动概述**: 在 `capability-reconciliation.md` 增加 `Boundary Summary`。

**关键接口 / 行为**:

```text
WeChat/content:
  execution -> agents/wechat-agent or runtime
  data/contracts -> mcps hermes-db + wechat-draft

Novel:
  execution -> agents/novel-agent
  data/contracts -> mcps hermes-db novel tools
  rules/material -> Library/Wiki

XHS:
  execution -> not verified; apps/xhs-agent placeholder
  gate -> user decision

Personal ops:
  execution -> Hermes/NAS runtime
  data/contracts -> mcps only when stable storage/tool contract exists
```

**YAGNI**: 第 5 层停止。领域摘要即可，不创建新 routing DSL。

### Module: Downstream Readiness Summary

**职责**: 告诉 roadmap 后续 feature 是否可启动，以及必须先补什么。

**改动概述**: 在 `capability-reconciliation.md` 增加 `Downstream Gates`。

**关键接口 / 行为**:

```text
For each downstream feature:
  - Ready / Blocked / Conditional
  - Required rows
  - Blocking gaps
  - Suggested next stage
```

**YAGNI**: 第 5 层停止。Markdown summary 足够，跳过独立 roadmap state machine。

### Module: Verification Evidence

**职责**: closeout 前提供 fresh evidence。

**改动概述**: 后续 verify 阶段生成 [verify-evidence.md](verify-evidence.md)。

**关键接口 / 行为**:

```text
Checks:
  - specs/.active == agents-capability-reconciliation
  - roadmap Current Feature matches active
  - source matrix rows == 44
  - reconciliation rows == 44
  - no empty Capability Status
  - no empty Evidence or Evidence Gaps
  - P0/P1 rows have downstream gate
  - no note or agents runtime files modified by this feature
```

**YAGNI**: 第 2 层停止。标准 shell tools (`rg`, `awk`, `wc`, `git status`) 足够验证文档完整性。

---

## Data Model

不生成独立 `data-model.md`。

原因：本 feature 不新增数据库、持久化 schema、运行时状态机或 API contract。核心实体是 Markdown 对账行，字段已在 Module Design 中定义。若后续决定将 `capability-reconciliation.md` 机器化为 YAML/JSON manifest，再由单独 feature 补数据模型。

---

## Project Structure

```text
specs/
  .active
  note-skill-migration-roadmap/
    roadmap.md
  note-skill-inventory-matrix/
    migration-matrix.md
    acceptance.md
    verify-evidence.md
  agents-capability-reconciliation/
    spec.md
    plan.md
    capability-reconciliation.md   # next implement artifact
    tasks.md                       # next stage
    context-manifest.md            # recommended before implement
    verify-evidence.md             # verify stage
    acceptance.md                  # closeout stage
```

---

## Risks and Tradeoffs

- **人工判断可能不一致**: 用 status enum 和 evidence rules 降低漂移。
- **表格过宽**: 保留宽表，因为它是后续删除门禁和 feature 启动条件的核心证据。
- **历史 spec 状态矛盾**: 不尝试在本 feature 修复 agents 仓状态，只标 `contradictory` / `needs-recheck`。
- **跨仓路径不在当前 repo**: 本 feature 只读引用外部仓路径，不修改外部仓。
- **不执行 live smoke**: 对账可判断本地能力和文档状态，但不能证明部署可用；live smoke 留给后续具体迁移 feature。

---

## Evolution Path

- **MVP**: Markdown 对账表 + 本地证据路径 + fresh evidence。
- **成长期**: 后续 feature 消费后，如需要稳定机器读取，再转 YAML/JSON manifest 并生成 Markdown view。
- **成熟期**: 若 note skill 清理进入批量执行阶段，再建立 deletion gate validator 或 archive script；当前不做。

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。当前不引入数据库、规则引擎、UI 或自动迁移器。
- 是否引用了外部模式但没有适配检查：否。仅使用 decision table / audit matrix 作为轻量参考。
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。只新增 SDD 文档产物。
- 是否把候选归属误当完成迁移：否。status enum 明确保留 partial/absent/stale/contradictory。

---

## Verification Strategy

后续 verify 阶段至少执行：

```bash
rtk awk 'BEGIN{in_matrix=0; count=0} /^## Matrix$/{in_matrix=1; next} /^## Count Check$/{in_matrix=0} in_matrix && /^\| `/{count++} END{print count}' specs/note-skill-inventory-matrix/migration-matrix.md
rtk awk 'BEGIN{in_table=0; count=0} /^## Reconciliation Table$/{in_table=1; next} /^## / && in_table{in_table=0} in_table && /^\| `/{count++} END{print count}' specs/agents-capability-reconciliation/capability-reconciliation.md
rtk rg -n "verified|partial|absent|stale|contradictory|not-applicable|needs-user-decision" specs/agents-capability-reconciliation/capability-reconciliation.md
rtk git status --short specs/.active specs/note-skill-migration-roadmap specs/agents-capability-reconciliation
rtk git -C /Users/yqg/personal/AI/agents status --short
rtk git -C /Users/yqg/learning/biji/note status --short -- .agents/skills .hermes/skills
```

验证结论必须写入 `verify-evidence.md`，并解释外部仓已有 dirty 状态是否属于本 feature 范围。

---

## Stage Readiness

- 是否需要 `data-model.md`：不需要。本 feature 只产出 Markdown 对账表，不新增存储或运行时状态。
- 下一步建议：`tasks`
- 阻塞项（如有）：无。tasks 阶段应拆出矩阵读取、状态规则、P0/P1 对账、全量 44 行对账、downstream gates、verify evidence 和 closeout 准备。

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|---|---|---|
| plan.md | 必须 | 本文件 |
| data-model.md | 不需要 | 无新增数据存储或运行时 schema |
| capability-reconciliation.md | 必须 | implement 阶段核心产物 |
| context-manifest.md | 建议 | implement/verify 前记录必读上下文 |
| tasks.md | 后续阶段生成 | 由 `tasks` 阶段产出 |
| verify-evidence.md | 后续阶段生成 | verify 阶段 fresh evidence |
| acceptance.md | 后续阶段生成 | closeout 阶段持久验收记录 |

---

## Sources

| 决策 | 来源 | 备注 |
|---|---|---|
| ADR-001 | `specs/agents-capability-reconciliation/spec.md` | 当前 feature 范围 |
| ADR-002 | `specs/note-skill-migration-roadmap/roadmap.md` | roadmap 不变量和边界 |
| ADR-003 | `specs/note-skill-inventory-matrix/migration-matrix.md` | candidate / needs reconciliation 输入 |
| Architecture Quality Gate | `/Users/yqg/.agents/skills/sdd/references/architecture-quality-gate.md` | 本地 SDD reference |
