# Contract Gap Register: Novel Runtime Contracts

**Workspace**: `novel-runtime-contracts`  
**Date**: 2026-07-07

## Existing Durable Contracts

| Area | Existing MCP / Repo Evidence | Status |
|---|---|---|
| Books | `tools/novel_books.py`, `repositories/novel_repo.py`, migration `0007_novel_agent_books_chapters.py` | exists |
| Chapters | `tools/novel_chapters.py`, migration `0007_novel_agent_books_chapters.py` | exists |
| Chapter analyses | `tools/novel_chapter_analyses.py`, `novel_repo.py` | exists |
| Style profiles | `tools/novel_style_profiles.py`, `novel_repo.py` | exists |
| Validation reports / analysis runs | `tools/novel_reports.py`, `novel_repo.py` | exists |
| Planning | `tools/novel_planning.py`, `repositories/novel_planning_repo.py`, migration `0008_novel_planning_tables.py` | exists |

## MCP / Hermes-DB Contract Gaps

| Gap | Expected Consumer | Missing Server-Side Shape | Impact | Next Feature |
|---|---|---|---|---|
| Novel retrospective reports | agents adapter `createNovelRetrospectiveReport`, `get`, `list`, `updateReviewStatus` | migration tables, repository, MCP tools, tests | Agents retrospective live persistence cannot use hermes-db. | `hermes-db-novel-retrospective-contracts` |
| Retrospective alerts | agents adapter `createNovelRetrospectiveAlert`, `listNovelRetrospectiveAlerts` | report-linked alert table and tools | Alert history is local/in-memory only. | `hermes-db-novel-retrospective-contracts` |
| Correction constraints | agents adapter `create/get/list/updateNovelCorrectionConstraint*` | constraint table, status update contract | Approved corrections cannot persist across agents sessions. | `hermes-db-novel-retrospective-contracts` |
| Handoff packages | agents adapter `create/get/getLatestNovelHandoffPackage` | handoff package table and latest query | Long-window continuity cannot be served by MCP. | `hermes-db-novel-retrospective-contracts` |
| Character states | agents adapter `upsert/get/listNovelCharacterState*` | character state table keyed by book/character/chapter | Character continuity remains local fixture/runtime state. | `hermes-db-novel-retrospective-contracts` |
| Novel learning candidates | agents adapter `createNovelLearningCandidate`, `listNovelLearningCandidates` | novel-domain candidate table or compatible shared learning contract | Retrospective learnings cannot enter durable self-evolution flow. | `hermes-db-novel-retrospective-contracts` |
| Novel retrospective health | agents adapter `healthNovelRetrospective` | schema health inspection and tool | Automation cannot distinguish missing contract from runtime failure. | `hermes-db-novel-retrospective-contracts` |

## Agents Runtime Gaps

| Gap | Owner | Why It Is Not MCP Work |
|---|---|---|
| `novel-agent-automation-interfaces` plan/tasks absent | agents roadmap | API, skill thin routes, scheduling, and review UI are runtime/entry concerns. |
| Trend scout module absent | agents adapter/runtime | Platform search/compliance and sampling are execution concerns; MCP may later store metadata only. |
| Qidian scraper absent | user decision + agents adapter/runtime | Login/compliance/high-side-effect scraping cannot be introduced as a storage contract. |
| Thin route docs for old note skills | note/agents closeout | MCP cannot prove a user-facing skill route by only adding a table. |

## Non-Gaps For MCP

| Capability | Decision |
|---|---|
| Novel drafting, polishing, review generation | Not MCP-owned. Keep in agents/Hermes/Codex. |
| Prompt templates and model routing | Not MCP-owned. Keep runtime-configurable. |
| Long platform rule documents and source samples | Not MCP-owned. Route to Library/Wiki. |
| Raw novel/source corpus in Memory | Not allowed. Memory only keeps compact decisions/procedures. |
