# Data Model: Novel Runtime Contracts

**Workspace**: `novel-runtime-contracts` | **Date**: 2026-07-07

This feature creates reconciliation artifacts, not new database tables.

## Artifact Model

### NovelCapabilityRow

| Field | Type | Required | Notes |
|---|---|---:|---|
| `capability` | string | yes | Capability or note skill group, e.g. `novelist`, `retrospective-handoff` |
| `runtime_owner` | enum | yes | `agents`, `hermes`, `codex`, `none`, `needs-decision` |
| `contract_owner` | enum | yes | `mcps/hermes-db`, `library`, `memory`, `none`, `needs-decision` |
| `status` | enum | yes | `done`, `stale-task-state`, `in-progress`, `blocked`, `backlog`, `not-applicable` |
| `evidence` | string | yes | Local file/spec/test path evidence |
| `gap` | string | no | Missing runtime or contract item |
| `next_gate` | string | yes | Verification or decision required before deletion/archive |

### NovelSpecStateRow

| Field | Type | Required | Notes |
|---|---|---:|---|
| `spec` | string | yes | agents novel spec directory |
| `roadmap_status` | string | yes | Status from agents roadmap |
| `tasks_state` | string | yes | Done/unchecked count or no tasks |
| `acceptance_state` | string | yes | PASS / missing / partial / contradictory |
| `classification` | enum | yes | Same as `NovelCapabilityRow.status` |
| `resolution` | string | yes | Whether to trust roadmap, tasks, acceptance, or re-verify |

### ContractGap

| Field | Type | Required | Notes |
|---|---|---:|---|
| `gap_id` | string | yes | Stable local ID |
| `layer` | enum | yes | `agents-runtime`, `mcps-contract`, `library`, `memory`, `note-route` |
| `description` | string | yes | Concrete missing contract or runtime item |
| `evidence` | string | yes | File path or spec evidence |
| `blocks` | string | no | Downstream feature or deletion gate |
| `recommended_feature` | string | yes | Feature that should own the implementation |

### ReplacementRoute

| Field | Type | Required | Notes |
|---|---|---:|---|
| `note_skill` | string | yes | Original note/Hermes skill |
| `route_type` | enum | yes | `reuse-agent`, `thin-route`, `library-route`, `blocked`, `archive-later` |
| `replacement` | string | yes | Target app/spec/tool/doc |
| `evidence_gate` | string | yes | Smoke, doc, test, or user decision needed |
| `deletion_allowed` | boolean | yes | Always false in this feature |

## Existing Durable Contract Inventory

| Contract Area | Existing mcps path | Current Status |
|---|---|---|
| book metadata | `packages/hermes-db/src/hermes_db_mcp/tools/novel_books.py` | exists |
| raw chapters | `packages/hermes-db/src/hermes_db_mcp/tools/novel_chapters.py` | exists |
| chapter analyses | `packages/hermes-db/src/hermes_db_mcp/tools/novel_chapter_analyses.py` | exists |
| style profiles | `packages/hermes-db/src/hermes_db_mcp/tools/novel_style_profiles.py` | exists |
| validation reports / runs | `packages/hermes-db/src/hermes_db_mcp/tools/novel_reports.py` | exists, list/latest gaps noted by agents adapters historically |
| planning input pack / context version | `packages/hermes-db/src/hermes_db_mcp/tools/novel_planning.py` | exists |
| retrospective reports / alerts / constraints / handoff / character states | agents adapter expects `create_novel_retrospective_*` etc. | missing on mcps server side unless later evidence proves otherwise |

## Invariants

- No row may route creative generation or model selection to MCP.
- No note skill may have `deletion_allowed=true` in this feature.
- Library rows may store source/rule/reference metadata, not execution state.
- Memory rows may store compact decisions/procedures only, not raw source corpora.

