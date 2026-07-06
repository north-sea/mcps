# Replacement Routes: Novel Note Skills

**Workspace**: `novel-runtime-contracts`  
**Date**: 2026-07-07  
**Deletion policy**: all rows keep `deletion_allowed=false` until route docs and smoke evidence exist.

| Skill | Replacement Target | Thin Entry Shape | Required Gate | deletion_allowed | Notes |
|---|---|---|---|---:|---|
| `novel-analyzer` | `agents/apps/novel-agent` txt analysis command/workflow | route to analyzer CLI/API and optional hermes-db persistence | command/doc smoke over fixture novel | false | Existing runtime is verified, but thin route doc is still needed. |
| `novel-memory-workflow` | novel retrospective + Memory decision route | route to retrospective report, approved constraint, compact memory decision | hermes-db retrospective contract + no-raw-memory policy | false | Must not write full reports/source material into Memory. |
| `novel-platform-rules` | Library/Wiki page/search | route to Library query for platform rules | Library page/import manifest and retrieval smoke | false | No agents or MCP runtime needed. |
| `novel-trend-scout` | agents web-search adapter/runtime | route to compliant trend sampling workflow | platform risk decision + sampled-source Library route | false | Do not add scraper logic without compliance gate. |
| `novel-workflow` | novel-agent aggregate route | route to analyze/style/plan/write/retrospective commands | route map, dry-run replay, human review gate proof | false | Skill should become a menu/router, not keep workflow logic. |
| `novelist` | novel-agent chapter production | route to chapter production workflow | writing fixture smoke + review gate proof | false | Writing remains runtime-owned. |
| `plot-insertion-router` | novel-agent planning and correction constraints | route to approved insertion/writeback flow | human-approved writeback smoke | false | Writeback side effects require explicit gate. |
| `qidian-scraper` | no replacement yet | none | user/compliance decision, no-login-bypass design, smoke | false | Current state is absent; keep blocked. |
| `novel-capture` | Hermes + novel-agent capture/retrospective route | route to no-write capture or approved persistence | no-write mode smoke + retrospective storage contract | false | Capture must not silently persist raw material. |
| `novel-rules-ask` | Library/Wiki Q&A route | route to Library retrieval over platform rules | Library retrieval smoke | false | Merge with `novel-platform-rules`. |

## Library / Wiki Route

| Material | Route | Not Memory Because |
|---|---|---|
| Platform rules | Library/Wiki page with source metadata and retrieval smoke | Rules are long reference facts, not compact decisions. |
| Writing samples | Library source collection with provenance | Raw samples are source material. |
| Trend/source samples | Library source index with timestamp, URL/source, account/genre tags | Samples may be large and need provenance. |
| Qidian/platform observations | Library only after compliance approval | External platform facts need source traceability. |

## Memory Route

| Material | Route | Constraint |
|---|---|---|
| Approved correction constraint summaries | Memory decision/procedure entry | Store compact decision and pointer to hermes-db report/constraint only. |
| Process decisions | Memory procedure/decision | No raw novel text, no long report body. |
| Migration status | Memory summary if useful | Must point back to SDD acceptance/evidence files. |
