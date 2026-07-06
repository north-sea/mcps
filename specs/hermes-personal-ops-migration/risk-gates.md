# Risk Gates: Hermes Personal Ops Migration

**Workspace**: `hermes-personal-ops-migration`  
**Date**: 2026-07-07

| Risk Area | Affected Skills | Required Gate | Current Status |
|---|---|---|---|
| External writes | `link-inbox` | Karakeep/API smoke with test link, duplicate handling, and failure recovery | blocked |
| NAS mutation | `nas-ops`, `media-download` | explicit operator approval for every mutating command; read-only status smoke first | blocked |
| Media download/legal risk | `media-download` | source allowlist, destination policy, dry-run manifest, user confirmation | blocked |
| Scheduler/automation | `daily-capture`, `period-digest` | manual replay first, then idempotency proof before cron/scheduler | blocked |
| Durable personal records | `daily-capture`, `goal-setting`, `period-digest` | schema decision and export/backup policy | blocked |
| Memory pollution | all | no raw logs/links/media in Memory; compact summary only | policy set |

## Safety Decision

This feature intentionally performs no live operation. It only records the gates required before future implementation.
