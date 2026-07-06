# Capability Reconciliation: Novel Runtime Contracts

**Workspace**: `novel-runtime-contracts`  
**Date**: 2026-07-07  
**Scope**: reconcile novel-agent specs and novel note skills before adding MCP implementation.

---

## Agents Novel Spec State

| Spec | Roadmap Signal | Task State | Acceptance State | Classification | Resolution |
|---|---|---:|---|---|---|
| `novel-agent-architecture` | not listed as deliverable feature | no `tasks.md` | none | `reference` | Treat as architecture context only, not an unfinished feature. |
| `novel-agent-txt-analysis-mvp` | `done` in agents roadmap | 32 checked / 0 unchecked | no `acceptance.md` | `done-with-roadmap-evidence` | Roadmap and tests are enough for replacement routing; do not reopen only because acceptance file is absent. |
| `novel-agent-style-profile` | `done` in agents roadmap | 9 checked / 10 unchecked | `PASS` | `stale-task-state` | Acceptance records 73/73 tests and E2E verification; unchecked task file is stale and should be normalized only in agents closeout hygiene. |
| `novel-agent-hermes-db-contract` | `done` in agents roadmap | 35 checked / 8 unchecked | `ACCEPTED WITH MINOR LIMITATIONS` | `stale-task-state` | Existing durable contracts are valid; deferred/missing retrospective contracts are tracked separately as mcps gap. |
| `novel-agent-book-planning` | `done` in agents roadmap | 0 checked / 38 unchecked | `PASS (MVP 可交付)` | `stale-task-state` | Acceptance says MVP is complete; task file is not a reliable remaining-work source. |
| `novel-agent-chapter-production` | `done` in agents roadmap | checklist says all 27 done | `PASS` | `done` | Runtime writing workflow is accepted; writing remains agents-owned. |
| `novel-agent-retrospective-handoff` | `done` in agents roadmap | 41 checked / 0 unchecked | `PASS WITH CONTRACT-GATED LIVE PERSISTENCE` | `done-with-contract-gap` | Agents local/runtime slice is done; live persistence requires mcps retrospective contracts. |
| `novel-agent-automation-interfaces` | `current` in agents roadmap | no `tasks.md` yet | none | `in-progress` | Agents next feature; not an MCP blocker except it will consume stable MCP contracts. |

## Stale Task Resolution

| Pattern | Specs | Decision | Follow-up |
|---|---|---|---|
| Acceptance PASS but tasks unchecked | `style-profile`, `book-planning`, `hermes-db-contract` | Mark as `stale-task-state`, not active unfinished work for this mcps roadmap. | Agents repo may later normalize old task files, but no MCP implementation should be inferred from stale checkboxes. |
| Roadmap done but no acceptance file | `txt-analysis-mvp` | Mark as `done-with-roadmap-evidence`. | Keep replacement gate as thin route plus smoke/doc evidence, not acceptance-file-only gate. |
| Accepted runtime but live MCP persistence deferred | `retrospective-handoff` | Mark as `done-with-contract-gap`. | Create next mcps feature for novel retrospective durable contracts. |
| Spec only / current future work | `automation-interfaces` | Mark as `in-progress`. | Agents roadmap owns API/skill/Hermes scheduling plan. |

## Novel Note Skill Rows

| Skill | Upstream Status | Runtime Owner | Durable Contract Owner | Knowledge Owner | Route / Gate |
|---|---|---|---|---|---|
| `novel-analyzer` | `verified` | `agents/apps/novel-agent` txt analysis | optional existing hermes-db book/chapter/analysis tools | Library for source files and analysis artifacts | Thin route allowed after docs show analyzer command and storage path. |
| `novel-memory-workflow` | `partial` | novel retrospective runtime | hermes-db novel retrospective contracts, currently missing | Memory only for compact decisions | Blocked until storage policy and retrospective MCP tools exist. |
| `novel-platform-rules` | `not-applicable` to runtime | none | none | Library/Wiki | Route to Library page/search, not Memory or MCP runtime. |
| `novel-trend-scout` | `partial` | agents adapter/runtime | none unless sampled source metadata is persisted later | Library for sampled sources | Needs trend scout smoke and platform risk gate. |
| `novel-workflow` | `partial` | `agents/apps/novel-agent` orchestration | existing hermes-db contracts plus missing retrospective contracts | Library/Memory split by material type | Thin aggregate route only after route map exists. |
| `novelist` | `verified` | chapter production runtime | hermes-db book/chapter/planning/style contracts | Memory for compact decisions only | Thin route allowed after writing workflow route doc. |
| `plot-insertion-router` | `partial` | planning workflow | hermes-db planning tools | Memory optional for approved decisions | Needs human-approved writeback smoke. |
| `qidian-scraper` | `absent` | none today | none today | Library only if legal/compliant capture is approved | Requires user/compliance decision before implementation. |
| `novel-capture` | `partial` | Hermes + novel-agent retrospective/capture mode | missing retrospective/report capture contracts | Memory only for distilled decisions | Needs no-write capture route and storage gate. |
| `novel-rules-ask` | `not-applicable` to runtime | none | none | Library/Wiki | Merge with platform-rules Library route; no agent/MCP runtime. |

## Summary

- Novel writing, review, prompt construction, model routing, and human review remain in agents/Hermes/Codex.
- Existing hermes-db novel tools cover book/chapter/analysis/style/planning state.
- The only P0 MCP gap exposed by the completed agents retrospective work is durable retrospective state: reports, alerts, correction constraints, handoff packages, character states, and learning candidates.
- No note novel skill is deletion-ready. Every row still needs a thin route, smoke evidence, or Library route before `note-thin-shell-and-archive`.
