# Decision Record: XHS Workflow Definition

**Workspace**: `xhs-workflow-definition`  
**Date**: 2026-07-07  
**Decision**: pause XHS as a formal workflow; keep `xhs-creator` deletion-blocked.

## Rationale

| Evidence | Decision Impact |
|---|---|
| `apps/xhs-agent` only has placeholder stages and no tests/domain implementation | Cannot claim replacement. |
| Upstream reconciliation says `xhs-creator` requires user confirmation or rewrite/fill-gap | Must keep user-decision gate. |
| XHS publishing/login/scraping would be external high-side-effect work | Must not implement or run without explicit approval. |

## Future Resume Gate

XHS can be resumed only after an explicit keep decision and a new SDD feature that defines:

- platform rules and compliance boundary
- minimum content workflow
- image/card requirements
- review gate and manual publish handoff
- dry-run fixture smoke
- Library/Wiki route for examples and platform rules

## Deletion Gate

`xhs-creator` deletion is not allowed until a replacement route and smoke evidence exist, or the user explicitly chooses archive/delete in `note-thin-shell-and-archive`.
