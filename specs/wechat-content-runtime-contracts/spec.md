# Feature Specification: WeChat Content Runtime Contracts

**Workspace**: `wechat-content-runtime-contracts`  
**Created**: 2026-06-28  
**Status**: Ready for Plan  
**Input**: 用户描述: "继续 note skill 迁移 roadmap；基于 agents-capability-reconciliation 的对账结果，启动公众号 / 博客 / 内容生产 runtime 契约 feature。"

> 写入本文件后，`specs/.active` 应指向 `wechat-content-runtime-contracts`，且 `specs/note-skill-migration-roadmap/roadmap.md` 的 `Current Feature` 应保持一致。

---

## Feature Traits *(LM 自动检测，用户可 override)*

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | 覆盖 topic scout/inbox、writer、review、image、draft handoff、publisher 等多阶段内容链路。 |
| `external-side-effects` | ✅ | WeChat draft、asset upload、外部搜索 / image provider 都可能调用外部服务或写入外部系统；YouMind 已确认不再使用，不纳入本 feature。 |
| `artifact-handoff` | ✅ | 文章生成结果、图片 manifest、topic shortlist、draft artifact 会被下游 package 或服务消费。 |
| `user-visible-output` | ✅ | 最终产物是用户可检查的文章、草稿、封面 / 插图、选题列表、月度报告或替代路由文档。 |
| `prior-closure-failure` | ✅ | 上游对账显示多个能力已有模块但缺少端到端 smoke、替代路由文档或调用方对账。 |
| `bugfix-loop-breaker` | ❌ | 当前不是修复单个 regression，而是定义下一阶段契约和验收边界。 |

**结论**: 本 feature 启用 Producer-Consumer Matrix、Evidence Gate、Workflow Replay 和三维 Verdict。后续 closeout 默认需要 `acceptance.md`。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 内容 skill 有明确替代归属 (Priority: P1)

作为 note skill 迁移负责人，我希望公众号、博客、topic、style、image 相关 skill 都能映射到明确的执行层、数据契约层或知识层，以便后续不会把写作 runtime 错沉到 MCP，也不会重复建设 agents 已有能力。

**Why this priority**: 这是 Wave 1 的主门禁；没有归属表就不能安全做迁移、删除或归档。

**Acceptance Scenarios**:

1. **内容行归属完整**
   **Given** `agents-capability-reconciliation` 已标出 content/blog/WeChat/topic/style/image 的 P0/P1 行  
   **When** 本 feature 完成规格、方案和执行  
   **Then** 每一行都有执行归属、数据 / 契约归属、知识归属、替代入口和删除门禁状态

2. **写作生成不进入 MCP**
   **Given** `wechat-writer`、`blog-writer`、`content-reviewer` 等能力依赖模型生成  
   **When** 定义契约边界  
   **Then** prompt、模型选择、正文生成、润色、审稿保留在 agents/Hermes/Codex runtime，MCP 只提供稳定输入包、状态、artifact、配置或保存接口

**Edge Cases**:

- **US1-3** 若某个 skill 只有候选落点但无 smoke，应保持 `partial`，不得标为可删除。
- **US1-4** `notion-media-orchestrator` 和 `youmind-publisher` 已由用户确认不再使用；本 feature 不为它们补 workflow 或 live smoke，只记录后续归档门禁。
- **US1-5** 若 agents 仓已有功能但 spec/tasks 状态矛盾，应以 fresh evidence 或显式缺口为准。

### User Story 2 - 端到端 handoff 有最小 smoke 门禁 (Priority: P1)

作为后续实现者，我希望文章生成到 WeChat draft、图片生成到 asset upload、topic scout 到 inbox/storage 的 handoff 都有最小可验证路径，以便 closeout 时能证明用户可见链路真的闭合。

**Why this priority**: 上游对账的主要缺口不是“没有模块”，而是缺少替代路由、调用方覆盖和端到端 smoke。

**Acceptance Scenarios**:

1. **文章生成到草稿**
   **Given** `apps/wechat-agent` 可生成文章内容，`packages/wechat-draft` 可消费 publish-ready artifact  
   **When** 执行最小 handoff 验证  
   **Then** evidence 记录从生成结果到草稿 artifact/render 的路径、输入输出格式和失败处理

2. **图片与素材上传**
   **Given** image provider / manifest / transform / asset upload 已有局部实现  
   **When** 定义或执行图片 smoke  
   **Then** cover、illustration、asset manifest、upload contract 至少有一条可复放验证路径，外部 provider 调用可被安全跳过或标记为 live-gated

3. **topic 捕获与采纳**
   **Given** `topic-radar` 已有较强证据，`topic-inbox` 和 `topic-scout` 仍缺 entry smoke  
   **When** 定义 topic workflow 契约  
   **Then** scout/adopt/inbox/storage 的 producer-consumer 关系清楚，Library 与 Memory 边界清楚

**Edge Cases**:

- **US2-4** live API 不可用时，必须有 fixture / dry-run evidence；provider live smoke 只作为 credential-gated 可选增强，不阻塞本 feature closeout。
- **US2-5** 外部发布、上传、写入类动作必须默认 dry-run 或人工确认，不能在验证阶段产生不可逆副作用。
- **US2-6** 对账表中的 P2 能力可以记录门禁，不应阻塞 P0/P1 内容生产主链。

### User Story 3 - 旧 skill 只变薄入口，不提前删除 (Priority: P2)

作为使用 Codex/Claude/Hermes 的操作者，我希望旧 note skill 在替代链路可用前仍能作为入口存在；替代链路验证后，它们再收缩为薄路由或 README 指针。

**Why this priority**: Roadmap 不变量明确禁止“先删 skill，再找替代品”。

**Acceptance Scenarios**:

1. **替代路由文档**
   **Given** 某个 skill 已确认由 agents 或 MCP/Library 承接  
   **When** 进入删除或归档判断  
   **Then** 必须有用户可读的替代入口说明，包括调用哪个 agent、哪个 MCP 契约、哪些 Library 资料，以及失败时的回退路径

2. **删除门禁保守**
   **Given** 某个 skill 仍缺 smoke 或用户决策  
   **When** 更新迁移状态  
   **Then** 删除门禁保持阻塞，不修改、删除或归档 note 源目录

**Edge Cases**:

- **US3-3** 低价值工具或业务线不确定项只记录用户决策门禁，不在本 feature 中强行迁移。
- **US3-4** 若 replacement route 依赖 agents 仓未合并代码，应记录为 blocked，不用 mcps 重写业务执行。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 必须覆盖 `agents-capability-reconciliation` 中所有 content/blog/WeChat/topic/style/image 的 P0/P1 行，包括 `blog-*`、`content-*`、`topic-*`、`wechat-*`、`account-config`、`monthly-review`、`style-analyzer`。
- **FR-002**: 必须为每个覆盖行明确执行归属、数据 / 契约归属、知识归属、替代入口、删除门禁和当前状态。
- **FR-003**: 必须明确 agents 执行层与 mcps 契约层边界：写作、审稿、选题编排、图片生成保留在 runtime；MCP 只承接稳定数据、artifact、账本、草稿、素材、配置或状态契约。
- **FR-004**: 必须定义文章生成到 WeChat draft 的最小 handoff 验收路径，包括输入、输出、artifact 格式、错误状态和 evidence 位置。
- **FR-005**: 必须定义图片能力的最小 handoff 验收路径，包括 provider、manifest、transform、cover/illustration、asset upload；fixture / dry-run smoke 是必需证据，live provider smoke 是 credential-gated 可选增强，不作为当前 feature 硬阻塞。
- **FR-006**: 必须定义 topic scout/inbox/radar 的最小 producer-consumer 契约，并区分 Library 来源资料、Memory 决策摘要和 hermes-db topic 状态。
- **FR-007**: 必须列出调用方对账范围，至少覆盖 agents CLI/service、wechat-draft package、hermes-db topic/artifact/article tools、现有薄 skill 或 Hermes entry。
- **FR-008**: 必须把 `notion-media-orchestrator`、`youmind-publisher` 标为不纳入本轮、不再投入、后续归档；其他 live publish/upload 外部副作用行必须标注是否需要用户确认、是否只做 dry-run。
- **FR-009**: 不得删除、移动或归档 note 源 skill；本 feature 只允许更新当前 repo 的 SDD 产物和必要的契约 / 测试 / 文档，实际范围由后续 plan 决定。
- **FR-010**: 完成时必须更新 roadmap 和 acceptance，说明本 feature 对 `knowledge-library-ingestion-plan`、`novel-runtime-contracts`、`note-thin-shell-and-archive` 的影响。
- **FR-011**: `monthly-review` 必须归属到 WeChat content runtime 的公众号 / 内容表现复盘；个人月报、目标回顾或日常记录归纳不纳入本 feature，后续如需要应进入 `hermes-personal-ops-migration`。

### Non-Functional Requirements *(if applicable)*

- **NFR-001**: 验证默认可离线或 dry-run 复放；live 外部服务验证必须显式标记并避免不可逆写入。
- **NFR-002**: 契约文档必须可被后续 plan/tasks 直接消费，不能只停留在高层原则。
- **NFR-003**: 状态判断必须证据优先；没有文件、测试、fixture、日志或验收记录时不能把 `partial` 升为 `verified`。

### Quality Attributes *(if architecture-relevant)*

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 一致性 | agents/mcps/Library/Memory 边界一致 | 避免重复造业务执行层或把写作 runtime 固化进 MCP | 对账表、producer-consumer matrix、plan ADR | 是 |
| 可验证性 | 每条主链至少有 dry-run 或 fixture evidence 路径；图片 live provider smoke 不硬阻塞 | closeout 不能只靠文档声明，同时避免凭据和额度依赖阻断契约交付 | smoke 记录、测试路径、verify-evidence、credential-gated 标记 | 是 |
| 可演进性 | 旧 skill 可先变薄入口，后续再归档 | 降低迁移期间中断风险 | replacement route docs、删除门禁表 | 否 |
| 安全性 | 外部发布 / 上传默认不产生不可逆副作用 | 防止验证阶段误发布、误上传、误写入 | dry-run 标记、live-gated 项、人工确认门禁 | 是 |

### Key Entities *(if applicable)*

- **Content Skill Row**: 从能力对账表继承的单个 skill 迁移行，包含 owner、状态、证据、缺口、动作和删除门禁。
- **Runtime Owner**: 执行模型调用、编排、写作、审稿、图片生成或外部服务调用的 agents/Hermes/Codex 层。
- **Contract Owner**: 提供稳定数据、artifact、状态、draft、asset、ledger 或配置接口的 mcps/package 层。
- **Knowledge Owner**: 保存来源材料、平台规则、参考文章或长文档的 Nowledge Library/Wiki；Memory 只保存决策和摘要。
- **Replacement Route**: 旧 note skill 被收缩前必须存在的用户可读替代入口说明。
- **Smoke Evidence**: 可复放的 fixture、dry-run、测试、日志或 live-gated 记录，用于证明 handoff 闭合。

---

## Out of Scope *(if applicable)*

- 不删除、不移动、不归档 `/Users/yqg/learning/biji/note` 中的任何 skill。
- 不把博客、公众号正文生成、审稿、标题改写、图片生成 prompt 下沉为 MCP 业务逻辑。
- 不在本 feature 中解决小说、小红书、个人运维、note 工具归档的完整迁移。
- 不再投入 `notion-media-orchestrator`；Notion 已确认不再使用，后续只进入清理 / 归档门禁。
- 不再投入 `youmind-publisher`；YouMind 后续不会使用，不做 live upload smoke 或 adapter contract 补齐。
- 不默认执行 live 发布、live 上传或外部写入；除非 plan/tasks 后续明确要求并有人工确认。
- 不把 Library 导入等同于 Memory 创建；来源材料导入细节留给 `knowledge-library-ingestion-plan`。

---

## Clarified Decisions

- `monthly-review`: 归属 WeChat content runtime，只覆盖公众号 / 内容表现复盘；个人月报或目标回顾不纳入本 feature。
- 图片 provider live smoke: fixture / dry-run smoke 必测；真实 provider 调用只在凭据存在且用户明确允许时执行，标记为 credential-gated optional，不阻塞当前 feature。

**已澄清**:

- `notion-media-orchestrator`: Notion 已不再使用，不进入内容生产主链，后续只做归档 / 清理门禁。
- `youmind-publisher`: YouMind 后续不会使用，不验证 live upload，不补 adapter contract。

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项（如有）：无；范围澄清已完成，下一阶段可制定 Producer-Consumer Matrix、验证路径和任务拆分。
