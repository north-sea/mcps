# Implementation Plan: Note Thin Shell And Archive

**Workspace**: `note-thin-shell-and-archive` | **Date**: 2026-07-07 | **Spec**: [spec.md](spec.md)

## Summary

This is a final disposition and action-plan feature, not a file-deletion feature. Upstream roadmap work now provides owner/gate records for content, Library, novel, XHS, and personal ops rows. The safe closeout is to classify all 44 note skills and produce an archive/delete/thin-route plan without moving or deleting note files.

## Decision

| Decision | Rationale |
|---|---|
| No automatic deletion | Many rows still require smoke, user decision, Library route, or thin README route evidence. |
| No automatic archive move | Archive is still a filesystem mutation in the note source tree and needs explicit approval. |
| Thin-route docs are the default safe action | They preserve discoverability while moving runtime ownership out of note. |
| `delete-ready` count remains 0 | Current evidence supports planning, not irreversible removal. |

## Artifacts

| Artifact | Purpose |
|---|---|
| `final-disposition.md` | final status for all 44 note skills |
| `archive-plan.md` | non-executed action plan: thin route, archive candidate, blocked, or user decision |
| `verify-evidence.md` | row counts and safety checks |
| `acceptance.md` | roadmap closeout record |

## Verification Strategy

- Count all 44 original skills in `final-disposition.md`.
- Confirm zero `delete-ready` rows.
- Confirm all archive/delete actions are plans only.
- Confirm raw source/material and writing runtime boundaries are preserved.
