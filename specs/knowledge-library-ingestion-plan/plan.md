# Implementation Plan: Knowledge Library Ingestion Plan

## Summary

This feature turns the trial finding "topic quality needs better account-fit/source context" into a concrete Library ingestion plan. It is a planning and dry-run feature, not a bulk import.

## Boundaries

- Library/Wiki or Markdown/Git owns long-lived source materials.
- Memory owns decisions, procedures, and compact summaries only.
- agents owns model execution and account-bound topic planning.
- mcps owns stable data contracts and migration evidence.
- note remains source/inbox until deletion gates prove replacement.

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Proof |
|---|---|---|---|
| note skill inventory | skill/source rows | ingestion matrix | every P0/P1 content row has target |
| account config audit | account-fit gaps | account source plan | four accounts covered |
| Karakeep/source inbox | links/materials | dry-run manifest | metadata only, no import |
| Library ingestion plan | route/deletion gates | roadmap closeout | no skill deletion without gate |

## Execution Strategy

1. Build `source-classification.md` from prior matrix and knowledge architecture.
2. Build `account-fit-source-plan.md` for four accounts.
3. Build `ingestion-dry-run-manifest.example.json` with at least one `moon-sleeping` source.
4. Build `deletion-gates.md` for content P0/P1 note skills.
5. Verify no live import/delete/write occurred.

## YAGNI Decisions

- Use static Markdown/JSON artifacts first; no importer implementation.
- Use source metadata, not copied full article bodies.
- Keep deletion gates as docs until replacement route smoke exists.

## Verification

- File existence and internal consistency checks.
- Secret/path scan for accidental credentials.
- Dry-run manifest parses as JSON and includes `no_side_effects: true`.
- Roadmap references the generated artifacts before closeout.
