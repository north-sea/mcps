# Implementation Plan: Hermes Personal Ops Migration

**Workspace**: `hermes-personal-ops-migration` | **Date**: 2026-07-07 | **Spec**: [spec.md](spec.md)

## Summary

This feature is a reconciliation and gate-definition slice. It does not execute NAS changes, downloads, external writes, or note skill deletion. The only safe first step is to classify each personal ops skill by owner, storage need, side-effect risk, Memory/Library route, and deletion gate.

## Architecture Decisions

### ADR-001: Side-Effect Gates Before Automation

- **Decision**: Any row that can mutate NAS, download media, write to Karakeep, or create durable records needs explicit smoke evidence or user confirmation before implementation.
- **Why**: Personal ops skills have higher external side-effect risk than content/novel planning docs.
- **Cost**: Some rows remain blocked or decision-gated.

### ADR-002: Memory Stores Decisions, Not Raw Logs

- **Decision**: Memory can keep compact procedures, decisions, and summaries; raw daily logs, link bodies, media files, and long period reports route to Library/Karakeep/filesystem, not Memory.
- **Why**: This preserves search quality and avoids turning Memory into a raw data lake.

### ADR-003: MCP Only If There Is A Stable Durable Contract

- **Decision**: Do not add MCP tools for every personal ops skill. MCP is only justified for stable data contracts such as goals, capture events, or inbox entries after a concrete consumer exists.
- **Why**: NAS ops and media download are runtime/action workflows, not database contracts.

## Artifacts

| Artifact | Purpose |
|---|---|
| `owner-table.md` | classify all 6 skills by owner, route, storage, risk, and status |
| `replacement-routes.md` | define thin entry and deletion gates |
| `risk-gates.md` | collect smoke/confirmation gates for external side effects |
| `verify-evidence.md` | record row counts and no-side-effect checks |
| `acceptance.md` | closeout record and roadmap recommendation |

## Verification Strategy

| Check | Target |
|---|---|
| Row coverage | all 6 personal ops skills represented in owner and replacement tables |
| Side-effect safety | no row marks deletion-ready; no command performs live NAS/external mutation |
| Memory boundary | no raw links/media/daily logs assigned to Memory |
| Roadmap | next feature selected based on user-decision gates |

## Deferred Work

- Implement actual daily/goal/link storage only after owner/gate acceptance.
- Run Karakeep/NAS/media smoke only after explicit approval.
- Archive/delete note skills only in `note-thin-shell-and-archive`.
