# Verify Evidence: Novel Runtime Contracts

**Workspace**: `novel-runtime-contracts`  
**Date**: 2026-07-07  
**Verdict**: PASS WITH DEFERRED IMPLEMENTATION

## Evidence Commands

| Check | Command / Evidence | Result |
|---|---|---|
| Active mcps feature | `cat mcps/specs/.active` | `novel-runtime-contracts` |
| Roadmap alignment before closeout | `rg "Current Feature|Next Recommended" mcps/specs/note-skill-migration-roadmap/roadmap.md` | current/next were `novel-runtime-contracts` |
| Agents active feature | `cat agents/specs/.active` | `novel-agent-automation-interfaces` |
| Agents novel spec scan | shell loop over `agents/specs/novel-agent-*` with `rg -c "^- \\[ \\]"` and acceptance existence | 8 novel spec dirs classified |
| Novel note skill source | `mcps/specs/agents-capability-reconciliation/capability-reconciliation.md` | 10 novel rows copied and narrowed |
| Existing novel MCP tools | `rg "async def (create|get|list|update|upsert|health)_novel" mcps/packages/hermes-db/src/hermes_db_mcp/tools/novel_*.py` | books, chapters, analyses, style, reports, planning exist |
| Missing retrospective server tools | `rg "retrospective|handoff|correction_constraint|character_state|learning_candidate" mcps/packages/hermes-db/src/hermes_db_mcp/tools ...` | only WeChat retrospective/shared learning evidence; no novel retrospective server-side tools |
| Agents expected retrospective client | `rg "createNovel|getNovel|listNovel|healthNovel|upsertNovel|updateNovel" agents/packages/adapters/src/mcp/novel-retrospective-*.ts` | 19 client operations expected |
| Side effects | docs-only changes in `specs/novel-runtime-contracts` and roadmap/spec updates | no live novel write, no publish, no note deletion |

## Count Checks

| Artifact | Required | Observed | Status |
|---|---:|---:|---|
| Agents novel spec rows | all `agents/specs/novel-agent-*` dirs | 8 | PASS |
| Novel note skill rows | all novel rows from capability reconciliation | 10 | PASS |
| Owner rows | analysis, style, planning, production, retrospective, automation, trend, rules, capture | 11 | PASS |
| MCP gap rows | retrospective report/alert/constraint/handoff/character/learning/health | 7 | PASS |
| Replacement route rows | all novel note skills | 10 | PASS |
| Rows allowing note deletion | must be 0 | 0 | PASS |

## FR Evidence

| Requirement | Evidence | Verdict |
|---|---|---|
| FR-001 Produce a novel capability reconciliation table | `capability-reconciliation.md` agents spec table + note skill rows | PASS |
| FR-002 Identify stale agents task files versus real unfinished work | `capability-reconciliation.md` stale task resolution table | PASS |
| FR-003 Identify hermes-db/MCP contract gaps | `contract-gap-register.md` separates existing contracts, MCP gaps, and agents runtime gaps | PASS |
| FR-004 Define Library/Memory handling | `owner-table.md` and `replacement-routes.md` route rules/sources to Library and compact decisions to Memory | PASS |
| FR-005 Recommend next implementable feature | roadmap updated to `hermes-db-novel-retrospective-contracts` | PASS |
| FR-006 Do not modify live content, publish, or delete note skills | docs-only closeout; `deletion_allowed=false` for all 10 novel note skills | PASS |

## Architecture Drift

| Check | Result |
|---|---|
| No MCP writing runtime | PASS: all prompt/model/writing/review rows remain agents/Hermes/Codex-owned. |
| No raw Memory route | PASS: raw rules, samples, source material route to Library/Wiki. |
| No premature note deletion | PASS: replacement routes keep deletion disabled. |
| No direct runtime implementation in this feature | PASS: implementation is deferred to next SDD feature. |

## Deferred Work

- Implement `hermes-db-novel-retrospective-contracts`: migrations, repositories, MCP tools, health checks, tests, and adapter smoke.
- Agents `novel-agent-automation-interfaces` remains agents-side current work and will consume stable contracts.
- Library/Wiki import and retrieval smoke for platform rules/source samples remains deferred.
