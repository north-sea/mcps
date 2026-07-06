# Roadmap: note skill 迁移与运行时整合

**Umbrella**: `note-skill-migration-roadmap`
**创建日期**: 2026-06-26
**Status**: complete-with-gates
**Current Feature**: `note-thin-shell-and-archive`
**Next Recommended Feature**: none

> 本 roadmap 已于 2026-06-27 激活。`note-skill-inventory-matrix`
> 已完成 closeout；`wechat-content-runtime-contracts` 已把公众号 / 博客 / 内容生产链路的
> agents runtime、mcps 契约、Library/Memory 边界推进到 trial-ready。
> 2026-07-01 刷新：跨仓 `agents-wechat-content-runtime-fixes` 已补齐 topic/image dry-run
> 阻塞证据；`hermes-db-topic-plan-contract` 已发布并完成生产 smoke，应纳入当前内容链路
> topic planning 契约。
> 2026-07-01 追加：因 NAS Nowledge Mem remote 写路径历史超时、本机 nmem 当前 degraded，
> 先切入 `knowledge-memory-architecture`，固化 Hermes-only NAS Mem、单写源、同步/备份和
> Library/Markdown/Git 分层，再回到内容链路 closeout。
> 2026-07-01 试用决策：先把选题和发草稿链路投入使用一段时间，完整写文章 feature 后置；
> 当前切到 `wechat-topic-draft-trial`，用真实试用反馈决定后续写作、Library ingestion 和清理顺序。
> 2026-07-07 closeout：`note-thin-shell-and-archive` 已完成；本 roadmap 进入
> `complete-with-gates`，当前无 next recommended feature。

---

## 目标摘要

目标是让 `/Users/yqg/learning/biji/note` 回归“人读笔记、来源索引、资料暂存”的定位，不再承担大量 agent skill 的执行注册职责。

跨环境稳定能力应迁到：

- `/Users/yqg/personal/AI/mcps`
- NAS Docker 服务
- `hermes-db`
- Nowledge Mem / Library / Wiki
- 已存在的 `/Users/yqg/personal/AI/agents`

模型强相关的“写作生成”能力不应沉到 MCP。正文生成、大纲生成、润色、审稿、标题改写等任务应留在 Hermes / Codex / Claude Code / agents 执行端，因为这些地方可以快速切换不同模型和供应商。

---

## SDD 状态

| 字段 | 当前值 |
|---|---|
| Roadmap 模式 | complete-with-gates |
| 当前仓库 active feature | `note-thin-shell-and-archive` |
| 当前 feature 状态 | closeout complete |
| `specs/.active` 现在应保持 | `note-thin-shell-and-archive` |
| Roadmap 当前 feature | `note-thin-shell-and-archive` |
| 激活后的首个 feature | `note-skill-inventory-matrix` |
| 当前阶段 | closeout complete |
| 下一阶段 | none |
| 激活条件 | 已满足：WeChat draft agent experience roadmap closeout PASS，用户明确启动本 roadmap |

### SDD 一致性说明

`specs/.active` 应同步为 `note-thin-shell-and-archive`，与本 roadmap 的
`Current Feature` 一致。

---

## 现状盘点

### note 中的 skill

来源目录：`/Users/yqg/learning/biji/note`

| 类别 | 数量 | Skills |
|---|---:|---|
| 内容 / 公众号 / 博客 | 19 | `blog-optimizer`, `blog-series-optimizer`, `blog-topic-advisor`, `blog-workflow`, `blog-writer`, `content-ops`, `content-reviewer`, `gemini-image-provider`, `opencli-integration`, `topic-radar`, `wechat-article-pipeline`, `wechat-cover`, `wechat-illustration`, `wechat-image-generator`, `wechat-writer`, `youmind-publisher`, `content-brainstorm`, `topic-inbox`, `topic-scout` |
| 小说 | 10 | `novel-analyzer`, `novel-memory-workflow`, `novel-platform-rules`, `novel-trend-scout`, `novel-workflow`, `novelist`, `plot-insertion-router`, `qidian-scraper`, `novel-capture`, `novel-rules-ask` |
| 小红书 | 1 | `xhs-creator` |
| Hermes 个人运维 | 6 | `daily-capture`, `goal-setting`, `link-inbox`, `media-download`, `nas-ops`, `period-digest` |
| note 工具 | 6 | `account-config`, `acp-note-taker`, `notion-media-orchestrator`, `repo-bootstrap`, `source-import`, `workspace-repair` |
| 质量 / 文风 | 2 | `monthly-review`, `style-analyzer` |

### agents 仓已有能力

来源仓库：`/Users/yqg/personal/AI/agents`

当前已存在的执行层基础设施，但完成度不一致：

| 类型 | 已有内容 |
|---|---|
| apps | `apps/wechat-agent`, `apps/novel-agent`, `apps/xhs-agent` |
| 共享包 | `packages/workflow-core`, `packages/adapters`, `packages/style-anchor`, `packages/config`, `packages/observability`, `packages/deploy-kit` |
| 关键 specs | `agents-roadmap`, `content-agent-monorepo`, `cross-agent-shared-capabilities`, `agent-self-evolution-foundation`, `wechat-*`, `novel-agent-*` |
| 发布/部署约定 | agents 仓有 MCP release preflight、Docker/NAS 部署约定 |

已有记忆中的关键判断：

- agents 仓是业务执行层，mcps 仓是数据/MCP 契约层。
- wechat / novel / xhs 应采用“共享底座 + 领域 pipeline”，不要抽象成万能内容 agent。
- 高复用能力包括 workflow state、artifact、gate、resume、LLM role routing、review gates、style profile、platform runtime。
- 低复用能力保留领域内：小说章节切分/角色状态/伏笔/滚动大纲，公众号排版/账号配置，小红书封面/标签/平台限制。

### agents 仓完成度判断

agents 仓不能视为“已经全部完成、可以直接承接 note skills”。它更准确的状态是：

| 区域 | 当前判断 |
|---|---|
| `apps/wechat-agent` | 代码和测试较多，已有 CLI/MCP/analytics/topic/batch/retrospective/self-evolution 入口，但仍需和当前 `mcps` 的 WeChat draft/runtime 边界重新对账 |
| `apps/novel-agent` | 代码和测试较多，已有分析、章节生产、retrospective/handoff 等部分能力，但多个 spec 仍有未完成 tasks，不能直接视为完整小说 agent |
| `apps/xhs-agent` | 基本是骨架，只有极少源码文件和无测试，不应假定可承接小红书 workflow |
| 共享包 | `workflow-core`、`adapters`、`style-anchor` 等基础包存在，可优先复用，但需要逐项验证接口是否仍符合当前设计 |
| specs | 状态混杂：部分 PASS，部分只有 spec，部分 tasks 大量未完成，部分可能受后续架构变化影响需要重写 |

已核实的代表性 spec 状态：

| Spec | 状态信号 |
|---|---|
| `agent-self-evolution-foundation` | tasks 30/30，acceptance PASS |
| `content-agent-monorepo` | tasks 20/20，但无 acceptance 结论 |
| `novel-agent-txt-analysis-mvp` | tasks 32/32 |
| `novel-agent-chapter-production` | tasks 6/6，acceptance PASS |
| `novel-agent-hermes-db-contract` | tasks 35/43，acceptance 标记 PASS 但仍有 8 个 todo，需复核 |
| `novel-agent-retrospective-handoff` | tasks 28/41，未完成 |
| `novel-agent-style-profile` | tasks 9/19，未完成 |
| `novel-agent-book-planning` | tasks 0/38，但 acceptance 写 MVP 可交付，状态矛盾，需复核 |
| `wechat-batch-multi-account` | tasks 0/103，旧计划大概率需要重写 |
| `wechat-agent-feature-migration` | tasks 10/22，未完成 |
| `wechat-* analytics/artifact/ledger/retrospective/topic-radar` | 多个 tasks 完成，需和 `mcps` 当前实现对账 |
| `agents-wechat-content-runtime-fixes` | acceptance PASS；已修复 `wechat-content-runtime-contracts` 的 T006/T007 阻塞证据 |
| `hermes-db-topic-plan-contract` | mcps acceptance PASS，已发布 `hermes-db-v0.2.28` 并完成生产 smoke；应作为 topic planning 的稳定 MCP 契约 |

因此 `agents-capability-reconciliation` 不是可选项，而是进入迁移实现前的硬门禁。

---

## 架构边界

| 层 | 负责 | 不负责 |
|---|---|---|
| Hermes / Codex / Claude Code | 临时交互、人工触发、模型切换、写作生成、改写、审稿 | 长期共享状态的唯一真相 |
| `/Users/yqg/personal/AI/agents` | 业务执行层、可部署 agent、领域 pipeline、模型编排、HTTP/MCP 触发入口 | 底层数据库 schema 和通用数据 MCP |
| `/Users/yqg/personal/AI/mcps` | MCP 服务、`hermes-db` schema、跨环境稳定契约、发布适配、账本、状态存储 | 固定写作模型或把 prompt 逻辑硬编码进工具 |
| Nowledge Library / Wiki | 来源材料、平台规则、参考文章、长文档、可搜索资料库 | 单次任务执行状态 |
| Nowledge Memories | 决策、流程、踩坑、迁移状态、长期可复用结论 | 整份原始资料 |
| `note` | 人读笔记、来源索引、轻量 README 指针 | active skill registry / 业务执行系统 |

---

## 整合原则：note skills 与 agents 既有能力如何处理

1. **先对账，不迁移。**
   第一阶段必须把 44 个 note skill 与 agents 仓已有 apps/packages/specs 做一一对照，确认是复用、补齐、重写、转 Library，还是归档。

2. **agents 有可用执行层时，不在 mcps 重做业务执行。**
   如果某个 skill 的核心是“跑一个业务流程”，优先检查 agents 仓对应 app 或 package；只有通过对账确认可用或可补齐后，才作为目标落点。mcps 只提供数据契约和工具能力。

3. **skill 只保留薄入口。**
   Codex / Claude Code 需要的本地 skill 应尽量变成薄路由：说明何时调用哪个 agent/MCP/Library，而不是保存完整执行流程。

4. **写作生成留在 agent/runtime。**
   prompt、模型选择、正文生成、润色和审稿不沉到 MCP；MCP 返回输入包、文风档案、上下文材料、保存接口和门禁结果。

5. **Library 与 Memory 分工固定。**
   来源材料进入 Library/Wiki；长期决策和流程进入 Memory；不要把整份资料塞进 Memory，也不要把执行决策只留在 Library。

6. **删除必须有证据。**
   每个 note skill 删除前必须有 deletion gate：目标系统路径、替代入口、smoke/验证证据，以及必要的 README 指针。

---

## 执行波次

| 波次 | 目的 | Features | 退出门禁 |
|---|---|---|---|
| Wave 0: 盘点与对账 | 先建立决策面，不改动旧系统 | `note-skill-inventory-matrix`, `agents-capability-reconciliation` | 44 个 skill 都有目标归属、优先级、删除门禁，并完成 agents 既有能力对账 |
| Wave 1: 内容生产底座 | 复用刚完成生产测试的 WeChat draft/runtime，并处理最大 skill 群 | `wechat-content-runtime-contracts`, `wechat-topic-draft-trial`, `knowledge-library-ingestion-plan` | 先试用选题和发草稿；公众号/博客 skill 有明确 agent/MCP/Library 归属，来源材料有导入规则 |
| Wave 2: 领域扩展 | 处理高价值但领域特化的小说和小红书 | `novel-runtime-contracts`, `hermes-db-novel-retrospective-contracts`, `xhs-workflow-definition` | 写作仍在 agent 端，状态契约清晰 |
| Wave 3: 个人运维拆分 | 把非内容生产的个人自动化移出 note | `hermes-personal-ops-migration` | 每个运维 skill 有 Hermes/NAS 归属和 smoke 检查 |
| Wave 4: 收口清理 | 目标系统验证后再缩减 note | `note-thin-shell-and-archive` | 旧 skill 被删除、归档或替换为薄 README/route doc |

### Roadmap 不变量

- 不先删 skill，再找替代品。
- 不把写作生成沉到 MCP。
- 不在 mcps 重做 agents 已有业务执行层。
- 不把 Library 导入当成 Memory 创建。
- 不让 `note` 在替代路径验证后继续承担 active registry。
- 不跳过 agents 既有能力对账。

---

## Feature Roadmap

| Feature | 目标 | 状态 | 依赖 | 启动条件 | 推荐阶段 | 备注 |
|---|---|---|---|---|---|---|
| `note-skill-inventory-matrix` | 为 44 个 skill 生成可审查迁移矩阵，标记目标归属、优先级、删除门禁 | conditional | 当前 feature 生产测试验收 | 已满足：用户启动本 roadmap | closeout complete | 第一个 feature，不删除任何东西；note 源仓已有 dirty skill 文件，严格 clean-source proof 为 conditional |
| `agents-capability-reconciliation` | 将 note skill 与 agents 仓现有 apps/packages/specs 对账，判断复用、补齐、迁移或废弃 | done | `note-skill-inventory-matrix` | 迁移矩阵初版完成 | closeout complete | 新增前置 feature，防止重复造 agent 能力；44/44 对账已完成 |
| `wechat-content-runtime-contracts` | 确定公众号/博客/content skill 哪些进 agents，哪些进 MCP 契约，哪些进 Library/Memory | done | `note-skill-inventory-matrix`, `agents-capability-reconciliation`; informed by `hermes-db-topic-plan-contract`, `knowledge-memory-architecture`, `wechat-topic-draft-trial`, `knowledge-library-ingestion-plan` | 已满足：trial 和 Library ingestion planning 已完成，topic/image/article-to-draft dry-run evidence 已存在 | closeout complete | PASS WITH DEFERRED LIVE ACTIONS；完整写作、live draft/provider、Library importer、note archive 均后置 |
| `wechat-topic-draft-trial` | 将已验证的选题、topic plan、adopt/inbox 和 WeChat draft handoff 投入一段时间试用；完整写文章 feature 后置 | done | `hermes-db-topic-plan-contract`, `wechat-content-runtime-contracts`, `knowledge-memory-architecture` | 已满足：topic plan 已发布生产、topic/draft dry-run 证据 PASS、用户确认先试用选题和草稿 | closeout complete | PASS WITH MANUAL GATES；topic plan production write 和 draft dry-run replay 已验证；live draft/user adoption 保持人工确认门禁；建议先补 Library/account-fit，不启动完整写作 runtime |
| `knowledge-memory-architecture` | 固化 nmem/NAS/Hermes、本机 Codex/Claude Code、Library/Markdown/Git、Karakeep 和替代工具的职责边界、单写源与同步策略；规划 NAS domain spaces 到本机 matching spaces 的单向同步 | done | `note-skill-inventory-matrix`, `agents-capability-reconciliation`; informs `knowledge-library-ingestion-plan` | 已满足：NAS nmem 历史超时、本机 nmem 已恢复但本机仍不使用 NAS write；用户要求规划单向同步 | closeout complete | PASS。继续 nmem 但降级职责；单向同步 planning/scaffold 完成；真实导入实现延后 |
| `knowledge-library-ingestion-plan` | 规划来源材料、平台规则、参考文章、可复用笔记进入 Nowledge Library/Wiki 的 metadata 和导入流程 | done | `note-skill-inventory-matrix`, `wechat-content-runtime-contracts`, `knowledge-memory-architecture`, `wechat-topic-draft-trial` | 已满足：trial 暴露 account-fit/source-context 缺口；memory/knowledge 主库和同步策略已定稿 | closeout complete | PASS。定义 source classes、metadata、account-fit source plan、dry-run manifest、deletion gates；无 live import/delete/write |
| `novel-runtime-contracts` | 将小说 workflow 拆为 agent 端生成与 `hermes-db`/MCP 状态契约 | done | `note-skill-inventory-matrix`, `agents-capability-reconciliation` | 小说 skill 对账完成，shared style/profile 边界稳定；需先复核 agents 小说 specs 的 acceptance/tasks 状态矛盾 | closeout complete | PASS WITH DEFERRED IMPLEMENTATION；已产出 capability/owner/gap/replacement routes，确认 retrospective 持久化是下一项 MCP 缺口 |
| `hermes-db-novel-retrospective-contracts` | 为 novel retrospective/handoff 增加 hermes-db schema、repository、MCP tools、health 和测试 | done | `novel-runtime-contracts`, agents `novel-agent-retrospective-handoff` | 已满足：agents runtime closeout PASS，但 live persistence contract-gated | closeout complete | PASS WITH DEPLOYMENT GATE；local code/tests ready，live DB migration 和 agents live smoke 延后 |
| `xhs-workflow-definition` | 判断小红书是否成为正式业务线；若是，定义最小 agent/MCP/Library 契约 | done | `note-skill-inventory-matrix`, `agents-capability-reconciliation` | personal ops owner/gate closeout 完成；XHS 仍需 scope decision | closeout complete | PASS WITH USER DECISION GATE；XHS 暂停，`xhs-creator` 删除仍阻塞 |
| `hermes-personal-ops-migration` | 将 daily capture、goal、link inbox、media download、NAS ops、period digest 移出 note skill | done | `note-skill-inventory-matrix` | 运维类 skill 有明确 owner；小说 MCP contract local closeout 完成 | closeout complete | PASS WITH USER/SMOKE GATES；所有 live ops、外部写入和 note 删除延后 |
| `note-thin-shell-and-archive` | 用薄入口、README 指针、archive 或删除替换旧 note skills | done | 所有会影响删除的迁移目标 | 上游 owner/gate 对账已完成；多行仍有 smoke/user-decision gate | closeout complete | PASS WITH ACTION PLAN ONLY；44/44 disposition complete，0 delete-ready，未执行删除/移动 |

---

## 推荐顺序

1. `note-skill-inventory-matrix`
2. `agents-capability-reconciliation`
3. `wechat-content-runtime-contracts`
4. `knowledge-memory-architecture`
5. `wechat-topic-draft-trial`
6. closeout `wechat-content-runtime-contracts` evidence and route gates
7. `knowledge-library-ingestion-plan`
8. deferred writing runtime feature, if trial proves it is worth formalizing
9. `novel-runtime-contracts`
10. `hermes-db-novel-retrospective-contracts`
11. `hermes-personal-ops-migration`
12. `xhs-workflow-definition`
13. `note-thin-shell-and-archive`

`knowledge-library-ingestion-plan` 可以先准备，但正式推进应等
`wechat-content-runtime-contracts` closeout 的 owner table、replacement route 和 deletion gates
定稿，并等 `knowledge-memory-architecture` 给出单写源、同步/备份和 memory/Library 分层结论；
任何业务执行迁移、删除或归档，都不能绕过 agents 对账、当前内容链路证据和知识同步边界。

---

## 迁移矩阵要求

第一个 feature 必须创建矩阵，至少包含这些列：

| 列 | 用途 |
|---|---|
| Skill | frontmatter 中的稳定名称 |
| 当前路径 | note 下的实际路径 |
| 类别 | 内容、小说、小红书、运维、note 工具、质量/文风 |
| 当前触发条件 | 今天什么任务会触发它 |
| 是否模型生成 | 是否负责写作、润色、审稿、标题等模型强相关能力 |
| 是否 NAS 依赖 | 是否依赖 NAS Docker、本地下载器、Karakeep、数据库等 |
| agents 既有落点 | 是否已有 app/package/spec 可承接 |
| mcps 既有落点 | 是否已有 MCP/package/spec 可承接 |
| 目标归属 | `agents`, `mcp`, `hermes-agent`, `thin-skill`, `nowledge-library`, `memory`, `archive` |
| 优先级 | P0/P1/P2/P3 |
| 删除门禁 | 删除或归档前必须具备的证据 |
| 备注 | 风险、疑问、迁移注意事项 |

---

## 完成记录

| Feature | 日期 | Verdict | 证据 | 对 roadmap 的影响 |
|---|---|---|---|---|
| `note-skill-inventory-matrix` | 2026-06-28 | CONDITIONAL PASS | `specs/note-skill-inventory-matrix/acceptance.md`; `specs/note-skill-inventory-matrix/verify-evidence.md`; 44/44 source and matrix count; deletion gates complete | Unblocks `agents-capability-reconciliation`; strict clean-source proof remains conditional because note source tree already has dirty skill files |
| `agents-capability-reconciliation` | 2026-06-28 | PASS | `specs/agents-capability-reconciliation/acceptance.md`; `specs/agents-capability-reconciliation/verify-evidence.md`; 44/44 reconciliation rows; downstream gates complete | Unblocks `wechat-content-runtime-contracts`; XHS and high-side-effect personal ops remain gated by user decision/smoke evidence |
| `wechat-content-runtime-contracts` | 2026-07-01 | TRIAL-READY | `specs/wechat-content-runtime-contracts/verify-evidence.md`; topic/image/article-to-draft PASS evidence; memory boundary PASS | 足够支撑选题/草稿试用；正式 closeout 暂后置到试用反馈之后 |
| `hermes-db-topic-plan-contract` | 2026-07-01 | PASS | `specs/hermes-db-topic-plan-contract/acceptance.md`; `verify-evidence.md`; `hermes-db-v0.2.28`; NAS production smoke with `topic_plans=true` | Unblocks topic planning contract for `wechat-content-runtime-contracts` and downstream agents topic adoption/planning |
| `knowledge-memory-architecture` | 2026-07-01 | PASS | `specs/knowledge-memory-architecture/acceptance.md`; `verify-evidence.md`; policy docs; sync scaffold | 决定继续 nmem 但降级职责、NAS Mem Hermes-only、同步/备份、替代工具试点门禁和单向同步实现门禁；unblocks content runtime closeout and Library ingestion planning |
| `wechat-topic-draft-trial` | 2026-07-06 | PASS WITH MANUAL GATES | `specs/wechat-topic-draft-trial/trial-log.md` Run 001/002/003; `tasks.md` T001-T008; `acceptance.md`; `rtk pnpm --filter @mcps/wechat-draft test` -> 67 passed | Unblocks `knowledge-library-ingestion-plan`; full writing runtime remains deferred; live draft remains manual-confirmation gated |
| `knowledge-library-ingestion-plan` | 2026-07-06 | PASS | `specs/knowledge-library-ingestion-plan/acceptance.md`; `source-classification.md`; `account-fit-source-plan.md`; `ingestion-dry-run-manifest.example.json`; `deletion-gates.md` | Unblocks `wechat-content-runtime-contracts` closeout route/deletion gates; importer remains deferred |
| `wechat-content-runtime-contracts` | 2026-07-06 | PASS WITH DEFERRED LIVE ACTIONS | `specs/wechat-content-runtime-contracts/acceptance.md`; `verify-evidence.md`; owner/replacement route closeout sections | Content P0 contracts are closed; live actions and archive/delete remain deferred; roadmap advances to `novel-runtime-contracts` |
| `novel-runtime-contracts` | 2026-07-07 | PASS WITH DEFERRED IMPLEMENTATION | `specs/novel-runtime-contracts/acceptance.md`; `verify-evidence.md`; `capability-reconciliation.md`; `owner-table.md`; `contract-gap-register.md`; `replacement-routes.md` | 固化小说 workflow 的 agent/MCP/Library/Memory 边界；unblocks `hermes-db-novel-retrospective-contracts` |
| `hermes-db-novel-retrospective-contracts` | 2026-07-07 | PASS WITH DEPLOYMENT GATE | `specs/hermes-db-novel-retrospective-contracts/acceptance.md`; `verify-evidence.md`; migration `0009_novel_retrospective_contracts.py`; 27 focused tests pass | Novel retrospective server contract is implemented locally; live DB migration and agents live smoke remain deployment-gated; roadmap advances to `hermes-personal-ops-migration` |
| `xhs-workflow-definition` | 2026-07-07 | PASS WITH USER DECISION GATE | `specs/xhs-workflow-definition/acceptance.md`; `decision-record.md`; `owner-table.md`; `risk-gates.md`; `verify-evidence.md` | XHS paused/user-decision gated; roadmap advances to `note-thin-shell-and-archive` |
| `hermes-personal-ops-migration` | 2026-07-07 | PASS WITH USER/SMOKE GATES | `specs/hermes-personal-ops-migration/acceptance.md`; `owner-table.md`; `replacement-routes.md`; `risk-gates.md`; `verify-evidence.md` | Personal ops note-skill rows have owner/routes/gates; no live side effects; roadmap advances to `xhs-workflow-definition` |
| `note-thin-shell-and-archive` | 2026-07-07 | PASS WITH ACTION PLAN ONLY | `specs/note-thin-shell-and-archive/acceptance.md`; `final-disposition.md`; `archive-plan.md`; `verify-evidence.md` | 44/44 skills have final disposition; 0 delete-ready; note migration roadmap is complete-with-gates |
| `note-thin-shell-and-archive` | pending | pending | pending | 安全缩减 note 中的旧 skill |

---

## 下一步建议

`knowledge-memory-architecture` 已完成 closeout，verdict 为 PASS。真实 NAS restart、NAS export、本机 import、cron/scheduler、production import implementation 均延后。

`note-thin-shell-and-archive` 已完成 closeout。本 roadmap 现在是 complete-with-gates：44/44 旧 note skills 已有最终 disposition，但 0 个 delete-ready；后续只能在用户明确批准后按 `archive-plan.md` 创建薄路由、归档候选或处理用户决策项。

`note-skill-inventory-matrix` 和 `agents-capability-reconciliation` 已完成；但在各后续 feature 产出替代路径和 smoke 证据前，仍不做任何 note skill 删除或迁移实现。

---

## 后置 Feature

- `knowledge-library-ingestion-plan`：等待当前内容链路 closeout 和 `knowledge-memory-architecture` closeout，明确哪些来源、规则和参考材料需要进入 Library/Wiki，以及如何与 memory 层同步。
- `novel-runtime-contracts`：已完成，后续实施缺口转入 `hermes-db-novel-retrospective-contracts`。
- `hermes-db-novel-retrospective-contracts`：本地实现已完成；等待后续部署窗口执行 live DB migration 和 agents `--use-hermes-db` smoke。
- `hermes-personal-ops-migration`：已完成 owner/gate closeout；具体 daily/goal/link/media/NAS/period 实现后续按单项 smoke/approval gate 拆分。
- `xhs-workflow-definition`：已暂停并记录用户决策门禁。
- `note-thin-shell-and-archive`：已完成；后续不推荐新 note migration feature，除非用户明确要求执行某一批薄路由/归档动作。
