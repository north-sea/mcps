# Context Manifest: Novel Runtime Contracts

**Workspace**: `novel-runtime-contracts` | **Date**: 2026-07-07

## Implement Context

| Path | Reason |
|---|---|
| `mcps/specs/novel-runtime-contracts/spec.md` | Source requirements and scope boundaries |
| `mcps/specs/novel-runtime-contracts/plan.md` | Current plan and ADRs |
| `mcps/specs/novel-runtime-contracts/data-model.md` | Artifact schemas and invariants |
| `mcps/specs/agents-capability-reconciliation/capability-reconciliation.md` | Upstream note skill reconciliation evidence |
| `mcps/specs/note-skill-migration-roadmap/roadmap.md` | Roadmap current/next and wave boundaries |
| `agents/specs/agents-roadmap/roadmap.md` | agents active novel feature and feature statuses |
| `agents/specs/novel-agent-retrospective-handoff/tasks.md` | Current unfinished agents runtime tasks |
| `mcps/packages/hermes-db/src/hermes_db_mcp/tools/novel_*.py` | Existing durable MCP contract inventory |
| `agents/packages/adapters/src/mcp/novel-retrospective-*.ts` | Expected retrospective MCP client contract from agents side |

## Check Context

| Check | Command / Evidence |
|---|---|
| active consistency | `mcps/specs/.active` equals `novel-runtime-contracts`; roadmap current equals same |
| no live side effects | verify feature edits only write `mcps/specs/novel-runtime-contracts/*` and roadmap docs |
| table completeness | count novel note skill rows and required capability rows in generated docs |
| boundary safety | scan generated owner/gap docs for prompt/model/writing assigned to MCP |

## Research Context

No external web/docs research required. This feature relies on local repo evidence and prior SDD artifacts.

