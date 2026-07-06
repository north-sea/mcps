# Feature Specification: Agents Capability Reconciliation

**Workspace**: `agents-capability-reconciliation`  
**Created**: 2026-06-28  
**Status**: Draft  
**Input**: 用户描述: "继续当前 roadmap"

> 本 feature 属于 umbrella `note-skill-migration-roadmap`。本阶段只做能力对账和决策记录，不迁移、不删除、不归档任何 note skill，不修改 `/Users/yqg/personal/AI/agents` 或 `/Users/yqg/learning/biji/note` 运行代码。

---

## Continuation Preflight

| 检查项 | 结果 |
|---|---|
| Feature 来源 | `specs/.active` 原指向 `note-skill-inventory-matrix`，该 feature 已 closeout complete |
| 上一 feature verdict | CONDITIONAL PASS；44/44 source and matrix count；deletion gates complete |
| Roadmap current before switch | `note-skill-inventory-matrix` |
| Roadmap next recommended | `agents-capability-reconciliation` |
| 本阶段推荐 | `specify` |
| 状态修正 | 将 `specs/.active` 与 roadmap `Current Feature` 切到 `agents-capability-reconciliation` |

**推荐阶段依据**: `note-skill-inventory-matrix` 已有 `acceptance.md` 和 `verify-evidence.md`，roadmap 明确要求在任何业务执行迁移、删除或归档前先完成 agents 既有能力对账。

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | 本 feature 是 roadmap Wave 0 的第二步，输出会被内容 runtime、novel runtime、Library ingestion、personal ops 和 archive/cleanup 等后续 feature 消费。 |
| `external-side-effects` | ❌ | 本 feature 只读检查本地仓库和写入 `specs/` 文档，不调用外部 API，不部署，不改 note 或 agents 源码。 |
| `artifact-handoff` | ✅ | `capability-reconciliation.md` 将成为后续迁移、补齐、归档和删除门禁的输入。 |
| `user-visible-output` | ✅ | 产出用户可审查的 44 行能力对账表、gap list 和下游 feature 启动条件。 |
| `prior-closure-failure` | ✅ | Roadmap 已记录 agents 仓状态混杂、部分 specs 与 tasks/acceptance 矛盾、不能把候选落点当已验证事实。 |
| `bugfix-loop-breaker` | ❌ | 这不是 bugfix；目标是对账和决策，不是修复回归。 |

**结论**: 下游需要 Producer-Consumer Matrix、Evidence Gate、Workflow Replay 和三维 Verdict；closeout 时默认生成 `acceptance.md`。

---

## Exploration Findings

| Source | Finding | 对本 feature 的影响 |
|---|---|---|
| `specs/note-skill-inventory-matrix/migration-matrix.md` | 当前矩阵 44/44 行；类别分布为内容 19、小说 10、小红书 1、Hermes 运维 6、note 工具 6、质量/文风 2；优先级分布 P0=8、P1=19、P2=13、P3=4。 | 对账必须保留全量 44 行，并优先处理 P0/P1。 |
| `specs/note-skill-inventory-matrix/migration-matrix.md` | 39 行显式 `needs reconciliation`，34 行带 `candidate:`。 | 本 feature 的核心不是新增候选，而是把候选转为 verified/partial/absent/stale/contradictory。 |
| `/Users/yqg/personal/AI/agents/apps/wechat-agent` | WeChat app 已有 CLI、MCP stdio/http 入口、测试和共享包依赖。 | 内容/公众号 P0 skill 应优先对账 wechat-agent，而不是在 mcps 重做执行层。 |
| `/Users/yqg/personal/AI/agents/apps/novel-agent` | Novel app 已有 domain/app 模块、build/test/typecheck、planning/production/retrospective 代码。 | 小说 skill 不能视为无落点，但仍需按 spec/tasks/acceptance 逐项判断完成度。 |
| `/Users/yqg/personal/AI/agents/apps/xhs-agent` | XHS 仍是 placeholder 入口。 | `xhs-creator` 必须保留 `needs-user-decision` 或 `rewrite/fill-gap` 门禁。 |
| `/Users/yqg/personal/AI/agents/packages/*` | `workflow-core`, `adapters`, `style-anchor`, `config`, `observability`, `deploy-kit` 已存在。 | 共享底座类 skill 可优先找复用点，但不能只凭包名判定 verified。 |
| `packages/hermes-db` and `packages/wechat-draft` | mcps 仓已有 topic/article/artifact/analytics/retrospective 工具，以及 WeChat draft/render/asset 服务。 | mcps 侧应记录为数据/MCP/草稿契约资产，不作为业务写作 runtime。 |
| `/Users/yqg/personal/AI/agents/specs` | 部分 specs 已 closeout/PASS，部分仍 Draft/Ready for Plan，部分 tasks 与 acceptance 状态不一致。 | 对账状态需要支持 `contradictory` 和 `stale`，并保留复核门禁。 |

---

## User Scenarios & Testing

### User Story 1 - 对账 44 个 note skills (Priority: P1)

作为维护者，我希望把 `migration-matrix.md` 中 44 个 skill 逐行对账到 agents/mcps/Library/Memory/薄入口候选，以便后续迁移不再依赖未验证猜测。

**Why this priority**: inventory feature 已证明候选矩阵完整，但所有 `candidate` / `needs reconciliation` 仍不是事实；继续迁移前必须先把候选落点拆成 verified、partial、absent、stale 或 not applicable。

**Acceptance Scenarios**:

1. **US1-1 全量保留行身份**  
   **Given** `specs/note-skill-inventory-matrix/migration-matrix.md` 有 44 行 skill  
   **When** 执行本 feature 的对账  
   **Then** `capability-reconciliation.md` 必须保留全部 44 个 skill，不得合并、跳过或重命名原始 skill。

2. **US1-2 候选状态可审查**  
   **Given** 某个 skill 在 matrix 中标记了 agents 或 mcps candidate  
   **When** 对账该 candidate  
   **Then** 必须记录状态为 `verified`, `partial`, `absent`, `stale`, `contradictory`, `not-applicable` 或 `needs-user-decision`，并附本地证据路径。

**Edge Cases**:

- **US1-3** 如果 agents 仓 spec 写 PASS 但 tasks 仍有未完成项，必须标记 `contradictory` 或 `partial`，不能记为 verified。
- **US1-4** 如果 skill 是模型写作、润色、审稿或标题改写能力，不能把 MCP 契约误判为执行层替代品。

### User Story 2 - 明确 agents / mcps 边界 (Priority: P1)

作为迁移负责人，我希望知道每个 skill 的执行层、数据契约层、资料层和薄入口分别应该落在哪里，以便后续 feature 不重复造业务 agent，也不把写作 runtime 沉到 MCP。

**Why this priority**: 当前 repo 是 `mcps`，但 roadmap 明确 agents 仓是业务执行层，mcps 是数据和 MCP 契约层；本 feature 要防止跨仓边界混乱。

**Acceptance Scenarios**:

1. **US2-1 agents 能力证据**  
   **Given** `/Users/yqg/personal/AI/agents` 中存在 apps、packages 或 specs  
   **When** 对账一个内容、小说、小红书或共享底座 skill  
   **Then** 必须记录可复用的 agents 路径、完成状态、测试/acceptance 信号，以及缺口。

2. **US2-2 mcps 契约证据**  
   **Given** `mcps` 仓存在 `packages/hermes-db`、`packages/wechat-draft` 或相关 specs  
   **When** 对账一个需要存储、账本、artifact、draft、topic 或 analytics 的 skill  
   **Then** 必须记录 MCP 是否已有契约、是否只负责数据层，以及后续是否需要补 contract feature。

**Edge Cases**:

- **US2-3** 如果某个 skill 只适合 Nowledge Library/Wiki 或 Memory，必须区分资料沉淀与长期决策，不得强行落 agents 或 mcps。
- **US2-4** 如果 `apps/xhs-agent` 只有骨架，必须保留用户确认和最小 workflow 定义门禁，不能宣称可承接 `xhs-creator`。

### User Story 3 - 生成后续 roadmap 门禁 (Priority: P2)

作为 roadmap owner，我希望对账结果能直接告诉我哪些后续 feature 可以启动、哪些必须先补齐或重写，以便安全推进迁移波次。

**Why this priority**: 本 feature 是进入 Wave 1+ 的硬门禁；没有可消费的 gap list 和下游启动条件，后续 feature 仍会回到猜测状态。

**Acceptance Scenarios**:

1. **US3-1 下游启动条件**  
   **Given** 后续 roadmap 包含 `wechat-content-runtime-contracts`, `knowledge-library-ingestion-plan`, `novel-runtime-contracts`, `xhs-workflow-definition`, `hermes-personal-ops-migration`, `note-thin-shell-and-archive`  
   **When** 完成对账  
   **Then** 每个后续 feature 必须有明确的启动条件、阻塞缺口和优先推进建议。

2. **US3-2 删除门禁继承**  
   **Given** inventory matrix 已为每个 skill 定义删除门禁  
   **When** 对账完成  
   **Then** 不得删除、迁移或归档 note skill；只能更新门禁状态和替代路径证据需求。

**Edge Cases**:

- **US3-3** 对外部平台、NAS、Karakeep、YouMind 或微信发布相关能力，若缺少 smoke 证据，必须保留 block，不得放行删除。
- **US3-4** 对旧 specs、旧 tasks 或旧 acceptance 状态矛盾的能力，必须记录复核要求，而不是把历史文档当完成事实。

---

## Requirements

### Functional Requirements

- **FR-001**: 系统必须读取并保留 `migration-matrix.md` 的 44 个 skill 行，输出一行对应一行的 `capability-reconciliation.md`。
- **FR-002**: 每个 skill 必须记录 agents capability status，枚举为 `verified`, `partial`, `absent`, `stale`, `contradictory`, `not-applicable`, `needs-user-decision`。
- **FR-003**: 每个 agents candidate 必须附本地证据路径，例如 app/package 源码、测试、spec、tasks、acceptance 或 roadmap 行；没有证据时必须标 `absent` 或 `needs-user-decision`。
- **FR-004**: 每个 mcps candidate 必须区分数据/MCP 契约、draft/render/asset service、topic/artifact/ledger/analytics storage、或 `not-applicable`。
- **FR-005**: 对模型生成类 skill，输出必须明确执行层 owner 在 agents/Hermes/Codex/Claude Code runtime，MCP 只能作为数据、上下文或保存契约。
- **FR-006**: 输出必须给出每个 skill 的 recommended action：`reuse`, `fill-gap`, `rewrite`, `split`, `thin-route`, `library`, `memory`, `archive-later`, `needs-user-decision`。
- **FR-007**: 输出必须汇总 P0/P1 blocking gaps，并映射到后续 roadmap feature 的启动条件。
- **FR-008**: 本 feature 不得修改 `/Users/yqg/learning/biji/note`、不得修改 `/Users/yqg/personal/AI/agents`，不得删除、移动、归档任何 skill。
- **FR-009**: 本 feature closeout 前必须生成 fresh evidence，证明 44/44 对账完成、证据路径可定位、roadmap active/current 一致。

### Non-Functional Requirements

- **NFR-001**: 对账表必须是 Markdown，便于人工审查和 diff；后续若需要机器消费再另立 feature。
- **NFR-002**: 不确定项必须显式标记为 `needs-user-decision` 或 `needs-recheck`，避免制造虚假确定性。
- **NFR-003**: 证据路径必须尽量精确到文件，必要时精确到行号，方便后续 plan/verify 复核。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 完整性 | 44/44 skills 有对账行 | 缺项会导致后续误删或漏迁 | source matrix count 与 reconciliation count 一致 | 是 |
| 可追溯性 | 每个结论都有本地证据路径或明确 unknown | 后续迁移必须能复核判断来源 | spot check P0/P1 rows evidence | 是 |
| 保守性 | candidate 不自动升级为 verified | agents/mcps 状态混杂，错误放行风险高 | grep 检查 unresolved 状态未被写成 PASS | 是 |
| 边界清晰 | agents 执行层与 mcps 数据契约层分离 | 防止在 mcps 重做业务 agent 或把写作 prompt 硬编码进 MCP | 每行有 owner/action/boundary 字段 | 是 |
| 可交接性 | 输出能驱动后续 roadmap feature | 这是 Wave 0 到 Wave 1+ 的门禁 | downstream feature readiness summary | 否 |

### Key Entities

- **Capability Reconciliation Row**: 单个 note skill 的对账记录，包含原始矩阵行、候选落点、证据、状态、recommended action、后续门禁。
- **Capability Status**: 对候选能力是否能承接 note skill 的判断，必须保守且可追溯。
- **Boundary Decision**: 对 agents、mcps、Hermes runtime、thin skill、Library、Memory、archive 的分工判断。
- **Downstream Gate**: 后续 roadmap feature 启动或删除旧 skill 前必须满足的证据条件。

---

## Out of Scope

- 不迁移、删除、移动、归档或重写 `/Users/yqg/learning/biji/note` 下任何 skill。
- 不在 `/Users/yqg/personal/AI/agents` 中实现缺失能力。
- 不在 `mcps` 仓实现新的 MCP tool、schema、service 或 adapter。
- 不执行外部 smoke、部署、发布、NotebookLM/Library/Memory 同步。
- 不把 `migration-matrix.md` 改写成最终迁移结论；本 feature 产出单独的对账表。
- 不决定小红书业务线是否继续投入；只记录现状和用户确认门禁。

---

## Unclear Questions

- `notion-media-orchestrator` 是否并入内容生产线，还是作为单独 Notion workflow 保留薄入口？
- `acp-note-taker`, `repo-bootstrap`, `workspace-repair` 是否属于本 roadmap 的迁移范围，还是应保留为本地 note 工具或 archive-later？
- 小红书 `xhs-creator` 是否继续作为正式业务线，需要在 `xhs-workflow-definition` 前由用户确认。
- `monthly-review` 最终 owner 是 wechat-agent retrospective、Hermes 定时任务，还是 hermes-db analytics 触发的复盘流程？

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项（如有）：无阻塞；plan 必须保留只读对账范围，并定义 `capability-reconciliation.md` 的列、状态枚举、P0/P1 spot check 和 fresh evidence 路径。
