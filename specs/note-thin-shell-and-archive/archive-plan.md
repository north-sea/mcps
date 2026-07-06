# Archive Plan: Note Thin Shell And Archive

**Workspace**: `note-thin-shell-and-archive`  
**Date**: 2026-07-07  
**Execution Status**: plan only; no file operations performed.

## Included Actions For Future Approval

| Action Type | Skills | Required Approval |
|---|---|---|
| Create thin route docs | `content-ops`, `topic-radar`, `novel-analyzer`, `novelist`, `nas-ops`, `account-config` | approve writing route docs in note or replacement repo |
| Archive candidates | `youmind-publisher`, `notion-media-orchestrator` | approve archive move/delete plan |
| User decision needed | `qidian-scraper`, `xhs-creator`, `media-download`, `acp-note-taker`, `repo-bootstrap`, `workspace-repair` | choose keep, rewrite, archive, or delete |

## Excluded Actions

| Excluded | Reason |
|---|---|
| Deleting any note skill | No row has full replacement + smoke + explicit deletion approval. |
| Moving note files to archive | Filesystem mutation requires user approval. |
| Live publish/upload/download/NAS operations | External side-effect gates are not satisfied. |
| MCP implementation for runtime generation | Writing/model/prompt runtime belongs in agents/Hermes/Codex. |
| Raw source import into Memory | Source material belongs in Library/Wiki or external stores. |

## Needs Follow-Up Before Archive/Delete

- Content/image/blog rows need route docs and focused smoke evidence.
- Novel rules/source rows need Library/Wiki retrieval smoke.
- Personal ops rows need explicit side-effect smoke or user decisions.
- XHS remains paused until the user decides whether to keep it.
- Note tooling rows need user value decisions.
