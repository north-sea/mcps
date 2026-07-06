# Context Manifest: WeChat Content Runtime Contracts

**Workspace**: `wechat-content-runtime-contracts`  
**Created**: 2026-06-28  
**Status**: active

> 本文件记录实现和验证阶段必须恢复的高信号上下文。它不是待修改源文件清单，也不替代实现阶段按需阅读代码。

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-content-runtime-contracts/spec.md` | 需求边界、out of scope、已澄清决策和 acceptance 语义来源 | implement | yes |
| `specs/wechat-content-runtime-contracts/plan.md` | Producer-Consumer Matrix、ADR、模块边界和验证策略来源 | implement | yes |
| `specs/wechat-content-runtime-contracts/tasks.md` | 执行顺序、slice 边界、blocked_by 和 verify 要求 | implement | yes |
| `specs/agents-capability-reconciliation/capability-reconciliation.md` | 44 行对账表、内容类覆盖范围、Notion/YouMind/monthly-review/image 决策来源 | implement | yes |
| `specs/note-skill-migration-roadmap/roadmap.md` | roadmap current feature、后续 feature 和“不先删除 note skill”不变量 | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-content-runtime-contracts/spec.md` | 验证 FR-001 到 FR-011、Feature Traits 和 out-of-scope 是否满足 | verify | yes |
| `specs/wechat-content-runtime-contracts/plan.md` | 检查 Producer-Consumer Matrix、ADR、质量属性和 anti-pattern 是否漂移 | verify | yes |
| `specs/wechat-content-runtime-contracts/tasks.md` | 检查任务是否完成、是否有跳项、是否需要回退 plan | verify | yes |
| `specs/wechat-content-runtime-contracts/verify-evidence.md` | 汇总 fresh evidence、dry-run / fixture 结果和 final verdict 的主要输入 | verify | yes |
| `specs/note-skill-migration-roadmap/roadmap.md` | 验证 roadmap current feature、阶段状态和下一步推荐一致 | verify | yes |
| `specs/agents-capability-reconciliation/capability-reconciliation.md` | 验证对账门禁是否和当前 feature 完成结果一致 | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `packages/wechat-draft/src/workflow/DraftWorkflow.ts` | article-to-draft dry-run 的 draft workflow 消费方 | implement / verify | yes |
| `packages/wechat-draft/src/render/MarkdownArticleImporter.ts` | writer payload 到 ArticleDocument 的导入路径 | implement / verify | yes |
| `packages/wechat-draft/src/render/ArticleDocumentToWechatArtifactBuilder.ts` | ArticleDocument 到 WeChat artifact 的转换路径 | implement / verify | yes |
| `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` | image manifest / asset handoff 的消费方 | implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/topics.py` | topic shortlist / inbox / storage 的契约路径 | implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py` | workflow artifact 状态契约路径 | implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/wechat_articles.py` | article state 契约路径 | implement / verify | yes |
| `packages/hermes-db/src/hermes_db_mcp/tools/wechat_analytics.py` | monthly-review 内容表现复盘的数据契约路径 | implement / verify | yes |
| `/Users/yqg/personal/AI/agents/apps/wechat-agent/src/app/writer-service.ts` | writing runtime owner 证据路径；不在本仓修改 | implement / verify | yes |
| `/Users/yqg/personal/AI/agents/apps/wechat-agent/src/app/topic-radar-service.ts` | topic radar producer 证据路径；不在本仓修改 | implement / verify | yes |
| `/Users/yqg/personal/AI/agents/apps/wechat-agent/src/app/topic-service.ts` | topic adopt/inbox runtime 证据路径；不在本仓修改 | implement / verify | yes |
| `/Users/yqg/personal/AI/agents/apps/wechat-agent/src/app/retrospective-report-service.ts` | monthly-review 内容表现复盘 runtime 证据路径；不在本仓修改 | implement / verify | yes |
| `/Users/yqg/personal/AI/agents/packages/adapters/src/image/*` | image provider / manifest / transform 证据路径；live smoke credential-gated optional | implement / verify | yes |
| `/Users/yqg/personal/AI/agents/packages/style-anchor/src/index.ts` | style / review 复用路径；不在本仓修改 | implement / verify | yes |

---

## Rules

- `Required = yes` 的本地文件不存在时，当前阶段必须回退更新产物。
- 不把 agents 仓文件列为本 feature 的默认修改对象；它们是 evidence / route target，除非后续用户明确要求跨仓实现。
- 不执行 live provider、live publish、live upload，除非用户明确允许。
- 不删除、不移动、不归档 note 源 skill；清理留给 `note-thin-shell-and-archive`。
- 不把正文生成、审稿、标题改写或图片生成 prompt 下沉到 MCP。
