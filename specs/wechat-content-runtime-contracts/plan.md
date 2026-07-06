# Implementation Plan: WeChat Content Runtime Contracts

**Workspace**: `wechat-content-runtime-contracts` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/wechat-content-runtime-contracts/spec.md`

---

## Summary

本方案把公众号、博客、topic、style、image 和内容复盘类 note skill 收敛为“agents 执行层 + mcps 契约层 + Library/Memory 知识层”的迁移计划。核心不是新建服务，而是补齐 owner 表、Producer-Consumer Matrix、替代路由文档和 dry-run / fixture smoke 证据。

候选方案讨论跳过：只有一个合理方向。上游 roadmap 和对账结果已明确 agents 是业务执行层、mcps 是稳定数据 / MCP 契约层，用户也已确认 Notion/YouMind 不再使用、`monthly-review` 归 WeChat 内容复盘、图片 live provider smoke 为 credential-gated optional。

---

## Architecture Overview

```text
旧 note skill / Hermes skill
  |
  | 只保留薄入口、路由说明、删除门禁
  v
agents runtime
  - apps/wechat-agent: writer/topic/content/analytics/retrospective runtime
  - agents/packages: workflow-core, adapters, style-anchor, config
  |
  | 产生文章、topic、review、image manifest、analytics report 等 artifact
  v
mcps contracts
  - packages/hermes-db: topics, workflow_artifacts, wechat_articles, wechat_analytics
  - packages/wechat-draft: Markdown import, ArticleDocument, DraftWorkflow, AssetSourceLoader
  |
  | 保存状态、artifact、草稿、素材契约
  v
用户可见结果
  - 文章 / 草稿
  - topic shortlist / inbox
  - cover / illustration handoff
  - 内容表现月报
  - replacement route docs
```

边界原则：

- 写作、审稿、选题编排、图片生成留在 agents/Hermes/Codex runtime。
- MCP 只承接稳定数据、artifact、草稿、素材、配置、analytics 和 topic 状态。
- Library 保存来源材料、平台规则、参考文章；Memory 只保存迁移决策和摘要。
- note skill 在替代路径和 smoke evidence 完成前不得删除。

---

## Architecture Reference

| 参考模式 / 模板 | 来源 URL | 适配点 | 不适配点 | 当前阶段 |
|---|---|---|---|---|
| 分层 runtime / contract 边界 | UNVERIFIED，本仓 roadmap 与对账产物 | 能清楚分开模型执行、稳定契约、知识资料和薄入口 | 不引入独立 BFF、事件总线或新服务 | MVP / 迁移期 |
| Producer-Consumer artifact handoff | UNVERIFIED，SDD trait 规则 | 用矩阵防止“生成了 artifact 但没人消费” | 不要求实时事件驱动；优先 dry-run / fixture | MVP / 迁移期 |

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| `apps/wechat-agent/src/app/writer-service.ts` / writing runtime | publish-ready article payload | `packages/wechat-draft/src/render/MarkdownArticleImporter.ts`, `ArticleDocumentToWechatArtifactBuilder.ts`, `DraftWorkflow.ts` | fixture 或 dry-run 记录从文章 payload 到 `ArticleDocument` / WeChat artifact / draft workflow 的转换结果 |
| `apps/wechat-agent/src/workflows/wechat/runtime.ts` | workflow artifact / article state | `packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py`, `wechat_articles.py` | hermes-db tool contract test 或 dry-run 保存 / 读取证据 |
| `apps/wechat-agent/src/app/topic-radar-service.ts` | topic shortlist / candidate topics | `apps/wechat-agent/src/app/topic-service.ts`, `packages/hermes-db/src/hermes_db_mcp/tools/topics.py` | shortlist fixture、topic adopt/inbox dry-run、topic storage readback |
| Hermes `topic-inbox` / `topic-scout` thin entry | topic capture / adoption request | WeChat topic runtime + hermes-db topics | route doc + inbox-to-storage dry-run evidence |
| `agents/packages/adapters/src/image/*` | image manifest / transformed asset input | `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` | fixture manifest + asset loader / upload contract test；live provider smoke 仅 credential-gated optional |
| `wechat-cover` / `wechat-illustration` runtime | cover / illustration asset reference | WeChat article artifact builder / draft renderer | dry-run 证明素材引用可进入 artifact 或草稿渲染输入 |
| `agents/packages/style-anchor/src/index.ts` | style profile / review hints | writer/reviewer runtime | review fixture 或 style profile consumption evidence |
| `apps/wechat-agent/src/app/retrospective-report-service.ts` + analytics import | 内容表现月报输入 / report | WeChat content runtime 用户可见报告 | analytics fixture + report sample；仅覆盖公众号 / 内容表现复盘 |
| `packages/config/src/wechat/index.ts` | account config / runtime config | writer/topic/draft runtime | caller reconciliation 表 + config test 或 dry-run |
| replacement route authoring | route docs / deletion gate table | old note skills / future archive feature | 每个 skill 有替代入口、owner、验证证据和阻塞原因 |

**孤儿 artifact 处理**:

- `youmind-publisher` 和 `notion-media-orchestrator` 不再作为 consumer 或 producer 补齐；只进入 `note-thin-shell-and-archive` 的归档门禁。
- 图片 live provider output 不要求在本 feature 产生真实外部结果；若无凭据，只保留 fixture / dry-run output。
- 个人月报 artifact 不属于当前 feature；若后续需要，进入 `hermes-personal-ops-migration`。

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|---|---|---|---|
| 一致性 | 每个 skill 行只有一个主执行归属和明确契约归属 | 以 owner table 和 route docs 作为主交付，不重复造 MCP runtime | 对账表更新、plan/tasks/acceptance 检查 |
| 可验证性 | 主链都有 dry-run 或 fixture evidence | tasks 必须先补离线证据，再考虑 live smoke | verify-evidence、测试路径、dry-run 输出 |
| 安全性 | 不产生未确认外部发布 / 上传 / 写入 | live provider 和外部写入均 credential-gated 或人工确认 | live-gated 标记、默认 dry-run |
| 可演进性 | 旧 note skill 可逐步收缩为薄入口 | 不在本 feature 删除 note 源文件 | deletion gate table 和 route docs |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|---|---|---|---|---|---|
| ADR-001: 复用 agents runtime，不在 mcps 重做内容执行 | 对账显示 writer/topic/review/image 多数已有 agents 路径 | A: agents 执行 + mcps 契约；B: mcps 重写；C: 保留 note skill 全流程 | 选择 A | 需要补 route docs 和 smoke；不能一次性删除旧 skill | [spec.md](spec.md), [../agents-capability-reconciliation/capability-reconciliation.md](../agents-capability-reconciliation/capability-reconciliation.md) |
| ADR-002: 图片 live provider smoke 不硬阻塞 | provider 调用依赖凭据、额度和外部服务 | A: live 必测；B: dry-run 必测 + live 可选；C: 不测图片链路 | 选择 B | 无法在无凭据环境证明 provider 可用，但可证明契约闭合 | 用户确认， [spec.md](spec.md) |
| ADR-003: `monthly-review` 收窄为内容表现复盘 | owner 曾在 WeChat content、Hermes 个人复盘、shared analytics 间摇摆 | A: WeChat 内容复盘；B: Hermes 个人月报；C: 通用 analytics | 选择 A | 个人月报延后到个人运维 feature | 用户确认， [spec.md](spec.md) |
| ADR-004: Notion/YouMind 不再投入 | 用户确认 Notion 已不再使用，YouMind 后续不会使用 | A: 补 workflow；B: 保留待定；C: 后续归档 | 选择 C | 旧 skill 暂不删除，等归档批次处理 | 用户确认， [spec.md](spec.md) |

---

## Module Design

### Module: Capability Owner Table

**职责**: 把本 feature 覆盖的 content/blog/WeChat/topic/style/image P0/P1 行转成可执行 owner 表。

**YAGNI 决策梯子**: 第 1 层停止。当前只需要 Markdown 表和 SDD artifacts，不需要数据库、schema、生成器或新 CLI。

**改动概述**:

- 从 [capability-reconciliation.md](../agents-capability-reconciliation/capability-reconciliation.md) 继承覆盖行。
- 将 `youmind-publisher`、`notion-media-orchestrator` 标记为不再投入 / 后续归档。
- 将 `monthly-review` 归入 WeChat 内容表现复盘。
- 为每行保留替代入口、验证证据、删除门禁。

### Module: Runtime Route Docs

**职责**: 为旧 note / Hermes skill 生成或更新替代入口说明。

**YAGNI 决策梯子**: 第 1 层停止。先用文档路由，不做自动 dispatcher。

**关键接口 / 行为**:

```text
old skill -> route doc:
  owner: agents runtime / mcps contract / Library / archive
  command or entry: existing CLI/service/package path
  evidence: test/dry-run/fixture path
  deletion gate: blocked/pass/deferred
```

**注意事项**:

- 本 feature 不修改 `/Users/yqg/learning/biji/note` 源目录。
- route docs 必须能支撑 `note-thin-shell-and-archive` 后续清理。

### Module: Article-To-Draft Handoff

**职责**: 证明文章生成结果能被 WeChat draft 契约消费。

**YAGNI 决策梯子**: 第 4 层停止。复用现有 agents writer 和 `packages/wechat-draft`，不新建转换层。

**关键接口 / 行为**:

```text
writer output
  -> MarkdownArticleImporter / ArticleDocumentTypes
  -> ArticleDocumentToWechatArtifactBuilder
  -> DraftWorkflow dry-run / fixture
```

**注意事项**:

- MCP 不负责写正文。
- evidence 可以是 fixture replay，不要求 live 发草稿。

### Module: Topic Runtime Contract

**职责**: 固化 topic scout / inbox / radar 的 producer-consumer 关系。

**YAGNI 决策梯子**: 第 4 层停止。复用 `wechat-agent` topic services、adapters 和 `hermes-db` topics tool。

**关键接口 / 行为**:

```text
research/source input -> topic-radar shortlist
shortlist -> topic-service adopt/inbox
adopt/inbox -> hermes-db topics storage
```

**注意事项**:

- Library 保存调研来源，Memory 只保存决策摘要。
- `topic-radar` 本身已有较强证据，但仍需替代路由文档。

### Module: Image Contract Smoke

**职责**: 证明 cover / illustration / image manifest 能进入素材上传或草稿消费链。

**YAGNI 决策梯子**: 第 4 层停止。复用 `agents/packages/adapters/src/image/*` 和 `packages/wechat-draft/src/wechat/AssetSourceLoader.ts`。

**关键接口 / 行为**:

```text
fixture image manifest
  -> transform / manifest validation
  -> AssetSourceLoader
  -> draft artifact reference

optional:
  credential present + user approval
  -> one minimal live provider smoke
```

**注意事项**:

- dry-run / fixture 是硬门禁。
- live provider smoke 只记录为 credential-gated optional。

### Module: Review / Style / Monthly Retrospective

**职责**: 将 review、style profile、内容表现月报纳入 WeChat 内容 runtime，而不是个人月报。

**YAGNI 决策梯子**: 第 4 层停止。复用 `workflow-core` gates、`style-anchor`、`retrospective-report-service` 和 hermes-db analytics。

**关键接口 / 行为**:

```text
analytics import / content sample
  -> retrospective report service
  -> content performance monthly report
  -> optional style / prompt follow-up decision
```

**注意事项**:

- 个人月报、目标回顾、日常记录归纳不在本 feature。
- report sample 是 closeout evidence 的一部分。

---

## Data Model

不创建 `data-model.md`。本 feature 不新增数据库实体、状态机或存储关系；只复用现有 hermes-db topic、workflow artifact、article、analytics 和 wechat-draft artifact 契约。若 tasks 阶段发现必须新增字段或 schema，再回退补 `data-model.md`。

---

## Project Structure

```text
specs/wechat-content-runtime-contracts/
  spec.md
  plan.md
  tasks.md              # 后续生成
  verify-evidence.md    # verify 阶段生成
  acceptance.md         # closeout 阶段生成

specs/agents-capability-reconciliation/
  capability-reconciliation.md

packages/hermes-db/src/hermes_db_mcp/tools/
  topics.py
  workflow_artifacts.py
  wechat_articles.py
  wechat_analytics.py

packages/wechat-draft/src/
  workflow/DraftWorkflow.ts
  render/MarkdownArticleImporter.ts
  render/ArticleDocumentToWechatArtifactBuilder.ts
  wechat/AssetSourceLoader.ts

/Users/yqg/personal/AI/agents/apps/wechat-agent/src/app/
  writer-service.ts
  content-ops-service.ts
  topic-service.ts
  topic-radar-service.ts
  analytics-import-service.ts
  retrospective-report-service.ts
```

---

## Risks and Tradeoffs

- **跨仓验证风险**: 主要执行层在 `/Users/yqg/personal/AI/agents`，当前仓只拥有 mcps 契约和 SDD 文档。tasks 阶段需要明确哪些验证在本仓跑，哪些只记录外部 evidence 路径。
- **文档先行风险**: 本阶段可能先产出 route docs 和 fixture 计划，真正代码补齐在 tasks/implement。必须在 verify 阶段用 fresh evidence 收口。
- **live provider 风险**: 图片 provider 不做硬阻塞会降低 live 可用性证明，但能避免凭据、额度和外部 API 影响契约交付。
- **旧 skill 清理风险**: Notion/YouMind 已不再使用，但本 feature 仍不删除旧 skill，清理必须留给 `note-thin-shell-and-archive`。

---

## Evolution Path

- **MVP**: Markdown owner table + route docs + dry-run / fixture smoke + deletion gate。
- **成长期**: 若 route docs 稳定且重复使用，再考虑生成机器可读 manifest。
- **成熟期**: 只有在多个 runtime 需要统一消费时，才考虑统一 contract registry 或自动 validator。

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。本计划不引入新服务、队列、BFF 或注册中心。
- 是否引用了外部模式但没有适配检查：否。仅使用本地 SDD / roadmap 的边界原则，来源标记为内部或 UNVERIFIED。
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。本阶段不新增存储状态；外部 live provider 明确为 credential-gated optional。
- 是否把模型生成沉到 MCP：否。写作、审稿、图片生成仍归 runtime。

---

## Verification Strategy

后续 verify 至少需要这些证据：

1. 覆盖行 owner table：content/blog/WeChat/topic/style/image P0/P1 行都有执行归属、契约归属、知识归属、替代入口和删除门禁。
2. Article-to-draft dry-run：writer payload 到 `ArticleDocument` / WeChat artifact / draft workflow 的 fixture 或测试证据。
3. Topic dry-run：topic shortlist 到 adopt/inbox/storage 的 fixture 或测试证据。
4. Image dry-run：manifest / transform / asset loader / draft reference 的 fixture 或测试证据；live provider smoke 标为 optional。
5. Monthly review sample：公众号 / 内容表现月报样例，不包含个人月报。
6. Route docs：旧 note/Hermes skill 能找到替代入口和当前删除门禁。
7. Negative scope proof：Notion/YouMind 不再进入内容链路；本 feature 未删除 note 源 skill。

---

## Stage Readiness

- 是否需要 `data-model.md`：不需要；当前只复用现有状态和存储契约。
- 下一步建议：`tasks`
- 阻塞项（如有）：无；方案已足够支撑任务拆解。

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|---|---|---|
| plan.md | 必须 | 当前文件 |
| data-model.md | 不需要 | 不新增实体、状态、关系或存储 schema |
| tasks.md | 后续阶段生成 | 拆分 owner table、route docs、smoke evidence 和 verify 更新 |
| acceptance.md | 后续阶段生成 | closeout 记录最终三维 verdict |

---

## Sources

| 决策 | 来源 URL | 备注 |
|---|---|---|
| agents runtime / mcps contract 边界 | [spec.md](spec.md), [../agents-capability-reconciliation/capability-reconciliation.md](../agents-capability-reconciliation/capability-reconciliation.md) | 本地 SDD 产物 |
| WeChat draft contract paths | `packages/wechat-draft/src/workflow/DraftWorkflow.ts`, `packages/wechat-draft/src/render/MarkdownArticleImporter.ts`, `packages/wechat-draft/src/render/ArticleDocumentToWechatArtifactBuilder.ts`, `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` | 本地只读探索 |
| hermes-db contract paths | `packages/hermes-db/src/hermes_db_mcp/tools/topics.py`, `workflow_artifacts.py`, `wechat_articles.py`, `wechat_analytics.py` | 本地只读探索 |
| agents runtime paths | `/Users/yqg/personal/AI/agents/apps/wechat-agent/src/app/*`, `/Users/yqg/personal/AI/agents/packages/*` | 本地只读探索 |
