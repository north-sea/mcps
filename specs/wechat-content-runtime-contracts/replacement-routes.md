# Replacement Routes: WeChat Content Runtime Contracts

**Workspace**: `wechat-content-runtime-contracts`  
**Source**: `owner-table.md` + `../agents-capability-reconciliation/capability-reconciliation.md`  
**Updated**: 2026-06-28

本文件给旧 note/Hermes skill 提供迁移期替代入口。`deletion_gate = blocked` 表示旧 skill 不能删除或归档；`deferred-archive` 表示不再投入但仍等待后续归档 feature 处理。

## Route Entries

| old_skill | route_target | entry | evidence | deletion_gate |
|---|---|---|---|---|
| `.agents/skills/blog-optimizer` | agents content optimization runtime | `/Users/yqg/personal/AI/agents/apps/wechat-agent/src/app/content-ops-service.ts`; `writer-service.ts` | owner-table row; pending old article sample smoke | blocked |
| `.agents/skills/blog-series-optimizer` | agents content series workflow | `/Users/yqg/personal/AI/agents/apps/wechat-agent/src/app/content-ops-service.ts`; workflow-core orchestrator | owner-table row; pending series fixture | blocked |
| `.agents/skills/blog-topic-advisor` | agents topic/content workflow + hermes-db topics | topic services in agents; `packages/hermes-db/src/hermes_db_mcp/tools/topics.py` | owner-table row; pending shortlist/adopt smoke | blocked |
| `.agents/skills/blog-workflow` | thin route to agents content workflow | agents content CLI/service entry | this replacement route doc | blocked until aggregate route smoke exists |
| `.agents/skills/blog-writer` | agents/Codex writer runtime | agents writer service + LLM adapter | owner-table row; pending single article fixture | blocked |
| `.agents/skills/content-ops` | agents shared workflow/style packages | workflow-core, style-anchor | owner-table row; pending caller reconciliation | blocked |
| `.agents/skills/content-reviewer` | agents/Codex review gate runtime | workflow-core gates, style-anchor, LLM adapter | owner-table row; pending review sample | blocked |
| `.agents/skills/opencli-integration` | agents platform/search adapters | adapters web-search/topic-radar paths | owner-table row; pending adapter smoke | blocked |
| `.agents/skills/topic-radar` | WeChat topic radar runtime | agents topic-radar service + hermes-db topics | upstream verified evidence plus this route doc; live availability not rechecked | blocked until route is linked from thin skill/archive batch |
| `.agents/skills/wechat-article-pipeline` | WeChat article workflow + draft/artifact contracts | agents WeChat workflow runtime; `packages/wechat-draft`; hermes-db workflow artifacts/articles | owner-table row; pending article-to-draft smoke | blocked |
| `.agents/skills/wechat-cover` | agents image cover workflow + draft asset contract | agents image manifest; `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` | owner-table row; pending cover dry-run | blocked |
| `.agents/skills/wechat-illustration` | agents image illustration workflow + draft asset contract | agents image adapter; `packages/wechat-draft` asset contract | owner-table row; pending illustration insertion dry-run | blocked |
| `.agents/skills/wechat-image-generator` | agents image orchestration/runtime | agents image manifest/transform/provider paths; draft asset loader | owner-table row; pending image manifest dry-run | blocked; live provider optional |
| `.agents/skills/wechat-writer` | agents/Codex WeChat writer runtime | writer service; Markdown importer; ArticleDocument artifact builder | owner-table row; pending generation-to-draft smoke | blocked |
| `.hermes/skills/content-brainstorm` | Hermes/Codex ideation route to topic/content runtime | topic suggestion service, topic service | owner-table row; pending brainstorm handoff route | blocked |
| `.hermes/skills/topic-inbox` | Hermes/agents topic inbox to hermes-db storage | hermes-db topics tool/repository; agents topic service | owner-table row; pending inbox-to-storage smoke | blocked |
| `.hermes/skills/topic-scout` | Hermes/agents topic scout to topic radar/adopt workflow | topic-radar service; web-search adapter; hermes-db topics | owner-table row; pending scout + adopt smoke | blocked |
| `.agents/skills/account-config` | agents shared account config | agents config package and WeChat config tests | owner-table row; pending caller reconciliation | blocked |
| `.agents/skills/monthly-review` | WeChat content performance retrospective | agents retrospective report service; analytics import service; hermes-db analytics | owner-table row; pending content monthly report sample | blocked |
| `.agents/skills/style-analyzer` | agents style profile/review runtime | style-anchor; relevant app style profile services | owner-table row; pending content style profile smoke | blocked |

## Deferred Archive Routes

| old_skill | route_target | entry | evidence | deletion_gate |
|---|---|---|---|---|
| `.agents/skills/gemini-image-provider` | optional agents image provider adapter | image provider adapter/runtime; asset upload contract | fixture/dry-run required later; live call credential-gated optional | blocked until image dry-run exists; live smoke not required |
| `.agents/skills/youmind-publisher` | no replacement runtime; archive later | none | user decision: YouMind will not be used | deferred-archive in `note-thin-shell-and-archive`; do not add YouMind upload smoke |
| `.agents/skills/notion-media-orchestrator` | no replacement runtime; archive later | none | user decision: Notion will not be used | deferred-archive in `note-thin-shell-and-archive`; do not add Notion workflow |

## Caller Reconciliation To Finish Later

| Route Group | Required Caller Proof |
|---|---|
| article/writer routes | PASS for draft handoff dry-run through `packages/wechat-draft` tests; full writing generation remains deferred |
| topic routes | PASS for topic plan storage and trial shortlist; live adoption remains user-gated |
| image routes | PASS for asset/preflight dry-run; live provider/upload remains user-gated |
| monthly review route | PASS through analytics/retrospective focused evidence |
| config/content shared routes | PASS for current closeout via `knowledge-library-ingestion-plan`; live Library import remains deferred |

## Deletion Gate Update

No note skill is deleted by this feature. Replacement entries with PASS evidence may become thin-shell candidates in `note-thin-shell-and-archive`; entries that still require full writing generation, live draft, or live provider work remain blocked or deferred.

## Negative Scope Proof

- No route entry asks for Notion workflow implementation.
- No route entry asks for YouMind upload smoke, YouMind adapter contract, or live publish work.
- No route entry deletes, moves, or archives note source files in this feature.
- All external publish/upload/provider work remains dry-run by default unless explicitly approved later.
