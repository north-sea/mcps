# Feature Specification: Note Skill Inventory Matrix

**Workspace**: `note-skill-inventory-matrix`  
**Created**: 2026-06-27  
**Status**: Draft  
**Input**: 用户描述: "开始 note-skill-migration-roadmap"

> 本 feature 属于 umbrella `note-skill-migration-roadmap`。本阶段只建立可审查迁移矩阵，不迁移、不删除、不归档任何 note skill。

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | 该 feature 是迁移 roadmap 的 Wave 0，输出会被后续 agents 对账、内容 runtime、Library ingestion 和清理阶段消费。 |
| `external-side-effects` | ❌ | 本 feature 只读盘点 `/Users/yqg/learning/biji/note` 和相关仓库信号，只写 `specs/` 文档，不调用外部 API，不修改 note skill。 |
| `artifact-handoff` | ✅ | `migration-matrix.md` 是后续 `agents-capability-reconciliation` 和各迁移 feature 的输入产物。 |
| `user-visible-output` | ✅ | 产出用户可审查的迁移矩阵和删除门禁。 |
| `prior-closure-failure` | ✅ | Roadmap 已记录 agents 仓状态混杂、旧 skill 不可先删后补、删除必须有证据等闭环风险。 |
| `bugfix-loop-breaker` | ❌ | 这不是 bugfix；目标是建立迁移决策面。 |

**结论**: 下游需要 Producer-Consumer Matrix、Evidence Gate、Workflow Replay 和三维 Verdict；closeout 时默认生成 `acceptance.md`。

---

## User Scenarios & Testing

### User Story 1 - 盘点全部 note skills (Priority: P1)

作为维护者，我希望看到 note 下所有 active skill 的稳定清单，以便确认迁移范围没有漏项。

**Why this priority**: 没有完整清单就无法判断目标归属、优先级和删除门禁，后续迁移会变成凭记忆改动。

**Acceptance Scenarios**:

1. **US1-1 全量发现**
   **Given** `/Users/yqg/learning/biji/note/.agents/skills` 和 `/Users/yqg/learning/biji/note/.hermes/skills` 中存在 `SKILL.md`  
   **When** 执行本 feature 的盘点  
   **Then** `migration-matrix.md` 必须列出全部 44 个 skill，并保留当前路径和稳定名称。

2. **US1-2 frontmatter 可追溯**
   **Given** 每个 skill 的 `SKILL.md` 包含 name 和 description 信号  
   **When** 矩阵记录 skill  
   **Then** 当前触发条件必须来自 skill 描述或 roadmap 已确认分类，不能凭空补写执行行为。

**Edge Cases**:

- **US1-3** 如果某个 skill 缺少标准 frontmatter，矩阵必须标记 `[NEEDS CLARIFICATION]`，而不是跳过。
- **US1-4** 如果实际发现数量不是 44，必须记录差异并阻塞 closeout。

### User Story 2 - 标注迁移候选归属 (Priority: P1)

作为迁移负责人，我希望每个 skill 都有候选目标归属、优先级和风险备注，以便后续按波次推进，而不是直接改旧目录。

**Why this priority**: Roadmap 的核心原则是先对账、不迁移；矩阵必须能支持后续 `agents-capability-reconciliation`。

**Acceptance Scenarios**:

1. **US2-1 归属候选**
   **Given** roadmap 已定义目标归属枚举  
   **When** 矩阵标注每个 skill  
   **Then** `目标归属` 必须使用 `agents`, `mcp`, `hermes-agent`, `thin-skill`, `nowledge-library`, `memory`, `archive` 或组合候选。

2. **US2-2 对账状态明确**
   **Given** agents 仓有 apps、packages 和 specs，但完成度不一致  
   **When** 矩阵写入 `agents 既有落点`  
   **Then** 允许写候选路径，但必须保留 `needs reconciliation` 状态，直到下一个 feature 完成逐项核验。

**Edge Cases**:

- **US2-3** 写作生成、润色、审稿、标题改写等模型强相关 skill 不得直接判定迁入 MCP。
- **US2-4** Library/Memory 候选项必须区分资料沉淀和长期决策，不得把整份原始资料塞入 Memory。

### User Story 3 - 建立删除门禁 (Priority: P2)

作为维护者，我希望每个 skill 的删除或归档都有证据门禁，以便最终缩减 note 时不会破坏正在使用的入口。

**Why this priority**: 删除风险高，但本 feature 只定义门禁，不执行删除。

**Acceptance Scenarios**:

1. **US3-1 删除前置证据**
   **Given** 某个 skill 被标记为未来可删除或归档  
   **When** 查看矩阵  
   **Then** 必须能看到替代入口、目标系统路径、smoke/验证证据和 README 指针要求。

2. **US3-2 不做副作用**
   **Given** 本 feature 仍在 inventory 阶段  
   **When** 完成 closeout  
   **Then** note 源目录不应发生 skill 删除、移动或重写。

**Edge Cases**:

- **US3-3** 对依赖 NAS、Karakeep、NotebookLM、YouMind、OpenCLI 或外部平台的 skill，删除门禁必须包含真实运行或等价 smoke 证据。
- **US3-4** 对只读规则类 skill，可以候选进入 Library/Wiki，但仍需有新入口说明。

---

## Requirements

### Functional Requirements

- **FR-001**: 系统必须在 `migration-matrix.md` 中列出 44 个 note skill 的稳定名称、当前路径、类别和触发条件。
- **FR-002**: 矩阵必须标注每个 skill 是否模型生成、是否 NAS/外部依赖，以及候选目标归属。
- **FR-003**: 矩阵必须区分 `agents 既有落点`、`mcps 既有落点` 和 `目标归属`，不得把候选落点写成已验证事实。
- **FR-004**: 每个 skill 必须有优先级和删除门禁。
- **FR-005**: 本 feature 必须明确记录不迁移、不删除、不归档旧 skill。
- **FR-006**: 本 feature closeout 前必须检查实际 skill 数量与矩阵行数一致。

### Non-Functional Requirements

- **NFR-001**: 矩阵必须是人工可审查的 Markdown 表格，能被后续 feature 直接引用。
- **NFR-002**: 对不确定项使用 `needs reconciliation` 或 `[NEEDS CLARIFICATION]`，避免制造虚假确定性。
- **NFR-003**: 路径应保留到可定位的当前 skill 目录，便于后续对账读取。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|-------------|-------------|----------------|
| 完整性 | 44/44 skills 被列出 | 缺项会导致后续误删或漏迁 | `find ... -name SKILL.md` 与矩阵计数一致 | 是 |
| 可追溯性 | 每行保留当前路径和候选依据 | 后续对账需要定位原始 skill | 矩阵路径列可回到源文件 | 是 |
| 保守性 | 只标候选，不宣称已完成迁移 | agents 和 mcps 状态仍需核验 | 不确定项保留 needs reconciliation | 是 |
| 可演进性 | 后续 feature 可增量更新矩阵 | roadmap 会按波次消费该产物 | 矩阵列覆盖目标归属、门禁和备注 | 否 |

### Key Entities

- **Skill Inventory Row**: 单个 note skill 的迁移决策记录，包含名称、路径、类别、触发条件、依赖、候选归属、优先级和删除门禁。
- **Migration Matrix**: 44 个 Skill Inventory Row 的集合，是后续对账和迁移计划的输入。
- **Deletion Gate**: 删除或归档旧 skill 前必须满足的替代入口、验证证据和 README 指针条件。
- **Target Ownership**: skill 的未来归属候选，包括 agents、mcp、hermes-agent、thin-skill、nowledge-library、memory、archive。

---

## Out of Scope

- 不修改 `/Users/yqg/learning/biji/note` 中任何 skill 文件。
- 不删除、移动、归档旧 skill。
- 不实现 agents、MCP、Hermes 或 Library 的迁移逻辑。
- 不验证 agents 仓每个候选 app/package/spec 的可用性；该工作属于 `agents-capability-reconciliation`。
- 不把写作生成、润色、审稿、标题改写等模型强相关能力沉入 MCP。
- 不创建外部 Memory、Library、Wiki 或 NotebookLM 内容。

---

## Unclear Questions

- `notion-media-orchestrator` 是否纳入本 roadmap 的内容生产线，还是作为单独 Notion 工作流处理？
- `acp-note-taker` 属于 note 工具、学习资料整理，还是应直接 archive/thin-skill？
- `monthly-review` 的最终 owner 是 agents 内容复盘、Hermes 定时任务，还是 hermes-db analytics？
- 小红书 `xhs-creator` 是否继续作为正式业务线，需要用户在后续 `xhs-workflow-definition` 中确认。

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项（如有）：无阻塞；但下游 plan 必须保留“不迁移、不删除”的范围边界。
