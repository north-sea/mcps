# Replacement Routes: Hermes Personal Ops

**Workspace**: `hermes-personal-ops-migration`  
**Date**: 2026-07-07  
**Deletion policy**: all rows keep `deletion_allowed=false`.

| Skill | Replacement Target | Thin Entry Shape | Required Gate | deletion_allowed |
|---|---|---|---|---:|
| `daily-capture` | Hermes capture workflow or future event schema | route to capture command plus storage policy | fixture capture + no-raw-memory proof | false |
| `goal-setting` | Hermes planning/goal workflow | route to current goal doc/Memory decision workflow | schema or manual procedure acceptance | false |
| `link-inbox` | Karakeep/Library route | route to save/read link with metadata | external write smoke, dedupe proof, rollback/repair doc | false |
| `media-download` | NAS-confirmed media workflow | route to explicit confirmation command | user policy, allowlist, storage target, dry-run, legal/safety confirmation | false |
| `nas-ops` | existing NAS ops/deploy skills | route to specialized ops skill/runbook | read-only status smoke; mutation requires explicit approval | false |
| `period-digest` | Hermes summarizer over approved inputs | route to digest generation once inputs exist | daily/goal input contract and summary fixture | false |

## Memory Route

Allowed in Memory:

- approved goals and goal rationale
- compact daily/period summaries
- operational procedures and decisions
- migration status and follow-ups

Not allowed in Memory:

- raw daily logs
- full media files or download manifests
- raw link bodies or bookmark archives
- NAS command output logs beyond concise incident summaries
