# Final Disposition: Note Thin Shell And Archive

**Workspace**: `note-thin-shell-and-archive`  
**Date**: 2026-07-07  
**Policy**: no note skill is deleted or moved by this feature.

## Status Rules

| Status | Meaning |
|---|---|
| `thin-route-ready` | Enough owner evidence exists to write a thin route doc later; deletion still requires approval. |
| `archive-ready` | User/upstream evidence says runtime is no longer used; archive move still requires approval. |
| `user-decision-gated` | Must ask user before keep/archive/rewrite. |
| `blocked` | Replacement path, smoke, Library route, or side-effect gate is missing. |
| `delete-ready` | Replacement, smoke, route, and explicit approval all exist. Current count: 0. |

## Disposition Table

| # | Skill | Category | Final Status | Replacement / Owner | Gate |
|---:|---|---|---|---|---|
| 1 | `blog-optimizer` | content/blog | blocked | agents content runtime | blog-specific smoke and thin route doc |
| 2 | `blog-series-optimizer` | content/blog | blocked | agents content runtime | series workflow evidence |
| 3 | `blog-topic-advisor` | content/blog | blocked | agents topic/content runtime + Library sources | shortlist/account-fit smoke |
| 4 | `blog-workflow` | content/blog | blocked | thin route to content workflow | route doc |
| 5 | `blog-writer` | content/blog | blocked | agents/Codex runtime | blog fixture smoke |
| 6 | `content-ops` | shared content | thin-route-ready | agents shared workflow/style packages | caller route doc before deletion |
| 7 | `content-reviewer` | content quality | blocked | agents/Codex review runtime | review smoke |
| 8 | `gemini-image-provider` | image provider | blocked | optional agents image provider adapter | image dry-run / credential gate |
| 9 | `opencli-integration` | shared source adapter | blocked | agents adapters | platform adapter smoke |
| 10 | `topic-radar` | WeChat/topic | thin-route-ready | `agents/apps/wechat-agent` topic radar | replacement route doc |
| 11 | `wechat-article-pipeline` | WeChat/content | blocked | agents + wechat-draft + hermes-db | generation-to-draft handoff smoke |
| 12 | `wechat-cover` | WeChat/image | blocked | agents image runtime + draft asset upload | cover dry-run |
| 13 | `wechat-illustration` | WeChat/image | blocked | agents image runtime + draft asset upload | illustration dry-run |
| 14 | `wechat-image-generator` | WeChat/image | blocked | agents image runtime | provider orchestration dry-run |
| 15 | `wechat-writer` | WeChat/content | blocked | agents/Codex writer runtime | article generation smoke |
| 16 | `youmind-publisher` | publishing | archive-ready | none; no longer used | approval to archive, no live upload |
| 17 | `content-brainstorm` | Hermes/content | blocked | Hermes/Codex runtime + optional topic storage | brainstorm handoff route |
| 18 | `topic-inbox` | Hermes/topic | blocked | Hermes runtime + hermes-db topics | inbox-to-storage smoke |
| 19 | `topic-scout` | Hermes/topic | blocked | Hermes/agents topic runtime | scout/adopt smoke |
| 20 | `novel-analyzer` | novel | thin-route-ready | `agents/apps/novel-agent` analyzer | thin route doc |
| 21 | `novel-memory-workflow` | novel | blocked | novel retrospective + Memory decision route | no-raw-memory proof and live persistence smoke |
| 22 | `novel-platform-rules` | novel rules | blocked | Library/Wiki | Library retrieval smoke |
| 23 | `novel-trend-scout` | novel trend | blocked | agents adapter/runtime | compliance and trend smoke |
| 24 | `novel-workflow` | novel | blocked | novel-agent aggregate route | route map and dry-run replay |
| 25 | `novelist` | novel writing | thin-route-ready | novel-agent chapter production | writing route doc and review gate proof |
| 26 | `plot-insertion-router` | novel planning | blocked | novel-agent planning/correction constraints | human-approved writeback smoke |
| 27 | `qidian-scraper` | novel source | user-decision-gated | none today | compliance/user decision |
| 28 | `novel-capture` | novel capture | blocked | Hermes + novel-agent capture route | no-write capture route and storage gate |
| 29 | `novel-rules-ask` | novel rules | blocked | Library/Wiki Q&A | Library retrieval smoke |
| 30 | `xhs-creator` | XHS | user-decision-gated | paused; `apps/xhs-agent` skeleton only | explicit keep/archive decision |
| 31 | `daily-capture` | personal ops | blocked | Hermes capture workflow or future event schema | fixture capture and storage policy |
| 32 | `goal-setting` | personal ops | blocked | Hermes planning/goal workflow | schema/manual procedure acceptance |
| 33 | `link-inbox` | personal ops | blocked | Karakeep/Library route | external write smoke |
| 34 | `media-download` | personal ops | user-decision-gated | NAS-confirmed media workflow | user policy and legal/safety gate |
| 35 | `nas-ops` | personal ops | thin-route-ready | existing NAS ops/deploy skills | read-only status route; mutations require approval |
| 36 | `period-digest` | personal ops | blocked | Hermes summarizer | daily/goal input contract |
| 37 | `account-config` | config/tooling | thin-route-ready | agents config package | caller route doc |
| 38 | `acp-note-taker` | note utility | user-decision-gated | none | user value decision |
| 39 | `notion-media-orchestrator` | note utility | archive-ready | none; Notion no longer used | approval to archive |
| 40 | `repo-bootstrap` | note utility | user-decision-gated | thin local utility or archive | user value decision |
| 41 | `source-import` | Library import | blocked | Library ingestion route | importer/manifest smoke |
| 42 | `workspace-repair` | note utility | user-decision-gated | thin local utility or archive | user value decision |
| 43 | `monthly-review` | review/style | blocked | WeChat/content performance retrospective | monthly report sample |
| 44 | `style-analyzer` | style | blocked | style-anchor / novel style profile | cross-domain style storage smoke |

## Count Summary

| Status | Count |
|---|---:|
| `thin-route-ready` | 6 |
| `archive-ready` | 2 |
| `user-decision-gated` | 6 |
| `blocked` | 30 |
| `delete-ready` | 0 |
| **Total** | **44** |
