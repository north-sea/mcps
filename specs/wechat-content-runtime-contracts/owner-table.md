# Owner Table: WeChat Content Runtime Contracts

**Workspace**: `wechat-content-runtime-contracts`  
**Source**: `../agents-capability-reconciliation/capability-reconciliation.md`  
**Updated**: 2026-06-28

本表只固化迁移归属和删除门禁，不删除、移动或归档 note 源 skill。状态遵循对账表的 evidence-first 规则：没有 smoke、fixture、测试或验收记录时，不把 `partial` 升为 `verified`。

## 覆盖规则

| 规则 | 结论 |
|---|---|
| 内容 / 博客 / WeChat / topic / style / image P0/P1 | 全部覆盖 |
| `account-config` | 覆盖，作为内容 runtime 配置依赖 |
| `monthly-review` | 覆盖，收窄为公众号 / 内容表现复盘 |
| `gemini-image-provider` | 覆盖为 P2 image optional；live provider smoke 不阻塞 |
| `youmind-publisher` | 覆盖为 negative scope；不再投入，后续归档 |
| `notion-media-orchestrator` | 覆盖为 negative scope；不再投入，后续归档 |

## Owner Matrix

| Skill | Priority | Runtime Owner | Contract Owner | Knowledge Owner | Replacement Entry | Current State | Evidence / Gap | Deletion Gate |
|---|---|---|---|---|---|---|---|---|
| `blog-optimizer` | P1 | agents content runtime | none | Library: source article references | thin route to content optimization workflow | `partial` | has `content-ops-service.ts`, `writer-service.ts`; missing old article smoke | blocked: old article sample smoke |
| `blog-series-optimizer` | P1 | agents content runtime | none | Library: series index | thin route to content series workflow | `partial` | has `content-ops-service.ts`, `workflow-core`; missing series workflow evidence | blocked: series smoke |
| `blog-topic-advisor` | P1 | agents topic/content runtime | hermes-db topics | Library: research input | thin route to topic shortlist/adopt workflow | `partial` | has topic services and topics tool; missing blog topic intake proof | blocked: shortlist smoke; Library ingestion split stays in `knowledge-library-ingestion-plan` |
| `blog-workflow` | P1 | agents content app router | none | Library: references | thin route to agents CLI/content workflow | `partial` | has content service and CLI path; missing aggregate route proof | blocked: replacement route doc |
| `blog-writer` | P1 | agents/Codex writer runtime | none | Library: source references | thin route to writer runtime | `partial` | has `writer-service.ts`, LLM adapter; missing blog article fixture | blocked: single article smoke |
| `content-ops` | P0 | agents shared workflow/style packages | workflow/artifact contract as needed | Memory: decisions only | direct reuse by content runtime | `partial` | has workflow-core and style-anchor; caller coverage incomplete | blocked: caller reconciliation |
| `content-reviewer` | P1 | agents/Codex review runtime | none | Library: style/review references | thin route to review gate/style profile | `partial` | has gates/style/LLM adapter; missing review smoke | blocked: review sample |
| `opencli-integration` | P0 | agents adapters | none | none | thin route to platform/search adapter | `partial` | has web-search/topic-radar adapters; OpenCLI-specific proof missing | blocked: platform adapter smoke; shared with `novel-runtime-contracts` |
| `topic-radar` | P0 | `agents/apps/wechat-agent` topic radar | hermes-db topics | Library: research references | thin route to topic radar workflow | `verified` upstream, `partial` for this feature | upstream local evidence exists; this feature still needs replacement route | blocked: replacement route doc |
| `wechat-article-pipeline` | P0 | `agents/apps/wechat-agent` workflow | `packages/wechat-draft`, hermes-db artifacts/articles | Library: article references | thin route to WeChat article pipeline | `partial` | has runtime, draft workflow, workflow artifacts, articles tool; missing E2E route and draft smoke | blocked: article-to-draft smoke |
| `wechat-cover` | P1 | agents image runtime | `packages/wechat-draft` asset loader/upload contract | none | thin route to cover image workflow | `partial` | has image manifest and upload test path; missing cover fixture | blocked: cover + upload dry-run smoke |
| `wechat-illustration` | P1 | agents image runtime | `packages/wechat-draft` asset contract | none | thin route to illustration workflow | `partial` | has image adapter and asset loader; missing insertion fixture | blocked: illustration insertion dry-run smoke |
| `wechat-image-generator` | P1 | agents image orchestration/runtime | asset manifest/storage contract | none | thin route to image generation workflow | `partial` | has manifest/transform/AssetSourceLoader test paths; missing provider orchestration fixture | blocked: manifest + dry-run provider orchestration; live provider optional |
| `wechat-writer` | P0 | agents/Codex writer runtime | `packages/wechat-draft` publish-ready artifact consumer | Library: source references | thin route to WeChat writer workflow | `partial` | has writer and draft importer/builder paths; missing generation-to-draft handoff smoke | blocked: article generation smoke |
| `content-brainstorm` | P1 | Hermes/Codex content ideation runtime | optional hermes-db topic storage | Memory: decisions only | Hermes thin route to brainstorm handoff | `partial` | has suggestion/topic service candidates; Hermes entry not proven | blocked: brainstorm handoff route |
| `topic-inbox` | P0 | Hermes/agents topic runtime | hermes-db topics | Memory: optional decisions, not raw sources | Hermes thin route to inbox/storage | `partial` | has topics tool/repo and topic service; entry smoke missing | blocked: inbox-to-storage smoke |
| `topic-scout` | P0 | Hermes/agents topic radar runtime | hermes-db topics | Library: research references | Hermes thin route to scout/adopt workflow | `partial` | has topic radar, web-search adapter, topics tool; adopt smoke missing | blocked: scout + adopt smoke |
| `account-config` | P0 | agents config package | optional config contract | none | thin route to shared account config | `partial` | has config package and tests; caller migration graph incomplete | blocked: caller reconciliation |
| `monthly-review` | P1 | WeChat content retrospective runtime | hermes-db analytics | Memory: decisions only | thin route to content performance monthly review | `partial` | has retrospective/analytics service and analytics tool paths; report sample missing | blocked: WeChat content performance report sample |
| `style-analyzer` | P1 | agents style package/runtime | future style storage only if needed | Library: style samples | thin route to style profile/review workflow | `partial` | has style-anchor and novel style service evidence; content style smoke missing | blocked: style profile smoke; shared with `novel-runtime-contracts` |

## Optional / Negative Scope

| Skill | Runtime Owner | Contract Owner | Knowledge Owner | State | Decision | Gate |
|---|---|---|---|---|---|---|
| `gemini-image-provider` | agents image provider adapter/runtime | asset upload contract only | none | `partial` | Keep as credential-gated optional image provider; fixture/dry-run is required, live provider call is not a closeout blocker | blocked for deletion until image fixture path exists; live smoke optional |
| `youmind-publisher` | no further investment | none | none | `stale` | YouMind will not be used; do not add upload smoke, adapter contract, or workflow work in this feature | archive later in `note-thin-shell-and-archive` |
| `notion-media-orchestrator` | no further investment | none | none | `stale` | Notion will not be used; do not add Notion workflow or media orchestration work in this feature | archive later in `note-thin-shell-and-archive` |

## Boundary Decisions

- Writing, review, title rewriting, topic orchestration, and image prompt execution remain in agents/Hermes/Codex runtime.
- MCP/package layers only own stable contracts: topics, artifacts, drafts, assets, analytics, config, and persistence.
- Library stores raw/reference sources and reusable platform/style material; Memory stores decisions, summaries, and migration state.
- Old note/Hermes skills remain callable until replacement routes plus smoke evidence are available.
- No source under `/Users/yqg/learning/biji/note` is changed by this feature.

## Caller Reconciliation

| Owner Group | Caller / Route Proof | Verdict |
|---|---|---|
| topic planning / topic scout | `hermes-db-topic-plan-contract` production smoke; `wechat-topic-draft-trial` Run 001/002 wrote candidates and TopicPlans; agents `hotspot-agent` now has `plan topics --write` and `plans list` focused tests | PASS for trial-ready route; deletion still gated |
| article-to-draft | `packages/wechat-draft` offline tests cover Markdown import, ArticleDocument rendering, publish-ready artifact, create-draft facade, and DraftWorkflow idempotency | PASS for dry-run route |
| image / asset handoff | `wechat-draft` asset loader/preflight/upload tests and agents image closure evidence remain dry-run only | PASS for dry-run route; live provider optional |
| content performance review | agents retrospective/analytics/config tests and hermes-db analytics tests provide content-performance evidence | PASS |
| account config / Library source context | `knowledge-library-ingestion-plan` defines account-fit source plan, source classes, dry-run manifest, and deletion gates | PASS for planning; live Library import deferred |

## Architecture Drift Check

| Invariant | Current Evidence | Verdict |
|---|---|---|
| Do not move writing generation into MCP | Writer/runtime entries remain agents/Codex/Hermes owned; MCP owns draft/artifact contracts only. | PASS |
| Do not reimplement agents runtime in mcps | This feature only documents contracts/routes and consumes existing agents evidence. | PASS |
| Do not delete note skills in this feature | Deletion gates remain blocked/deferred and user-gated. | PASS |
| Keep Notion/YouMind out of active runtime | Both remain negative/deferred archive scope. | PASS |
| Keep durable sources out of nmem full-text memory | Library ingestion plan routes source materials to Library/Markdown/Git; Memory only stores summaries/decisions. | PASS |
