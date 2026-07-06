# Owner Table: Hermes Personal Ops Migration

**Workspace**: `hermes-personal-ops-migration`  
**Date**: 2026-07-07

| Skill | Primary Owner | Contract / Storage Owner | Knowledge Route | Side-Effect Risk | Status | Decision |
|---|---|---|---|---|---|---|
| `daily-capture` | Hermes runtime / local capture command | future event/capture schema only if a stable consumer exists | Memory for distilled decisions; Library/files for raw daily notes | medium: may create durable records | `absent` today | Specify storage only after a concrete daily capture workflow is selected. |
| `goal-setting` | Hermes runtime / planning workflow | future OKR/goal contract if needed | Memory for current goals and decisions | low/medium: durable goal writes | `absent` today | Keep as thin route until goal schema is justified. |
| `link-inbox` | Hermes runtime or Karakeep client | Karakeep/external bookmark service, not hermes-db by default | Karakeep/Library for links; Memory only for decisions | high: external write | `absent` local MCP | Requires Karakeep save smoke and duplicate handling before migration. |
| `media-download` | NAS/runtime tool with confirmation | filesystem/NAS path, not MCP database | no Memory route for raw media | high: download/storage/legal risk | `needs-user-decision` | Do not automate without explicit policy and confirmation flow. |
| `nas-ops` | NAS ops skills / deploy runbooks | ops runtime; MCP only if a stable inventory/status contract is later needed | Memory for procedures/decisions | high: infrastructure mutation | `partial` via existing NAS skills | Keep specialized ops skills; do not fold into note migration. |
| `period-digest` | Hermes runtime summarizer | depends on daily/goal/event inputs | Memory for compact period summary; Library/file for long report | medium: derived durable summary | `absent` contract | Blocked until daily/goal input contracts exist. |

## Boundary Summary

| Boundary | Decision |
|---|---|
| Hermes/NAS runtime | owns actions, scheduling, downloads, command execution, and operator confirmation |
| MCP/hermes-db | only owns stable capture/goal/event contracts after concrete consumers exist |
| Karakeep/Library/filesystem | owns raw links, source material, media, and long notes |
| Memory | owns compact decisions, summaries, procedures, and migration state only |
| note skills | remain thin route candidates; no deletion-ready rows yet |
