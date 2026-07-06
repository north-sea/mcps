# Owner Table: Novel Runtime Contracts

**Workspace**: `novel-runtime-contracts`  
**Date**: 2026-07-07

| Capability | Primary Owner | Contract Owner | Library / Wiki Owner | Memory Owner | MCP Must Not Own |
|---|---|---|---|---|---|
| TXT analysis and chapter splitting | `agents/apps/novel-agent` | hermes-db book/chapter/analysis tools when persisted | source novels and derived long reports | compact decisions only | LLM analysis prompts or model choice |
| Style profile generation and injection | `agents/apps/novel-agent` | hermes-db style profile tools | reference samples and style source material | approved style decisions only | prompt generation strategy |
| Book planning and rolling chapter outlines | `agents/apps/novel-agent` | hermes-db planning tools | long planning references | compact planning decisions | outline-generation prompts |
| Chapter production and polishing | `agents/apps/novel-agent` | hermes-db book/chapter/writeback contracts | writing samples and platform references | approved constraints only | drafting, polishing, review, model routing |
| Retrospective report and alerts | `agents/apps/novel-agent` computes; Hermes/Codex may trigger | missing hermes-db novel retrospective tools | long report renderings if retained | approved learnings only | alert detection logic as fixed prompt/runtime |
| Correction constraints | `agents/apps/novel-agent` creates from approved review | missing hermes-db correction constraint tools | none | approved compact constraint summaries | deciding creative fixes without human/runtime gate |
| Handoff packages | `agents/apps/novel-agent` builds JSON package | missing hermes-db handoff package tools | optional rendered Markdown | compact continuation decision only | Markdown as source of truth |
| Automation interfaces | `agents/apps/novel-agent` / Hermes agent | consumes hermes-db contracts | route docs | procedures/decisions | scheduling business runtime |
| Trend scout and external source sampling | agents adapter/runtime after compliance gate | optional source metadata contract later | sampled sources, citations, platform observations | summarized decisions only | scraping/login bypass or source corpus storage |
| Platform rules and Q&A | none as runtime | none | Library/Wiki | no raw rules; decisions only | platform rule execution or long rule storage |
| Capture / memory workflow | Hermes + novel-agent route | missing retrospective/capture state contracts | long captured material | distilled decisions and procedures | raw capture corpus storage |

## Boundary Rules

| Rule | Status | Evidence |
|---|---|---|
| MCP owns durable state only | locked | `plan.md` ADR-002; existing `novel_*.py` tools are CRUD/query style. |
| Writing runtime stays outside MCP | locked | `spec.md` US3; `novelist` row routes runtime to agents. |
| Library/Wiki stores long source material | locked | `knowledge-library-ingestion-plan`; novel rules rows are not runtime rows. |
| Memory stores compact decisions only | locked | roadmap architecture boundary and this table; no raw source/sample rows route to Memory. |
