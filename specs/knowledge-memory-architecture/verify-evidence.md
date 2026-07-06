# Verify Evidence: Knowledge Memory Architecture

**Workspace**: `knowledge-memory-architecture`  
**Updated**: 2026-07-01  
**Mode**: planning / scaffold only; no NAS restart, no NAS export, no local import, no remote write.

---

## Evidence Summary

| Task | Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|---|
| T001 | Memory routing policy | Hermes-only NAS Mem, local agents disabled for NAS write, long-term knowledge routed to Markdown/Library/Git. | `routing-policy.md` | PASS |
| T002 | Knowledge class table | Durable decisions, SOPs, source materials, domain memories, runtime memory, and fallback writes all have owners and retention rules. | `knowledge-classes.md` | PASS |
| T003 | Tool evaluation gates | nmem retained as runtime memory; Mem0/Zep/Graphiti are future POC only; Karakeep remains source inbox. | `tool-evaluation-gates.md` | PASS |
| T004 | Export/import and sync strategy | Single-writer model, NAS old-copy handling, domain delta sync, merge/skip import, and no overwrite rules documented. | `sync-strategy.md` | PASS |
| T005 | Write timeout fallback | Memory write timeout behavior avoids blocking and avoids blind retries. | `fallback-policy.md` | PASS |
| T006 | Config checklist | Restart, mapping, import, cleanup, and security gates are listed without secrets. | `config-checklist.md` | PASS |
| T007 | Roadmap dependency | Roadmap current feature is `knowledge-memory-architecture`; Library ingestion waits for this closeout. | `note-skill-migration-roadmap/roadmap.md` | PASS |
| T008 | Content runtime closeout input | WeChat content runtime evidence now cites memory/Library boundary dependency. | `wechat-content-runtime-contracts/verify-evidence.md`; `tasks.md` | PASS |
| T009 | Sync implementation artifact | One-way sync implementation plan exists. | `sync-implementation.md` | PASS |
| T010 | Space mapping file | Example mapping covers selfmedia, novel, xhs, hermes; import modes are merge/skip only. | `scripts/nmem-space-map.example.json` | PASS |
| T011 | Dry-run preview command | Preview scaffold generates local report and does not import; TBD mapping blocks unsafe preview. | `scripts/nmem-nas-domain-sync.sh`; command evidence below | PASS |
| T012 | Import gate | Import requires confirm and still exits before real import; overwrite is rejected by script. | `scripts/nmem-nas-domain-sync.sh`; command evidence below | PASS |
| T013 | Document consistency | Active feature and roadmap current align; task and roadmap status agree. | `rg` checks | PASS |
| T014 | Sensitive info scan | Secret-pattern scan found no real token/API key/cookie/bearer in touched docs/scripts. | `rg` checks | PASS |

---

## Command Evidence

| Command | Result |
|---|---|
| `rtk nmem status` | PASS: local nmem is v0.10.6, status ok, database connected |
| `rtk nmem spaces list` | PASS: spaces are enabled and readable; local selfmedia space exists |
| `rtk ./scripts/nmem-nas-domain-sync.sh --help` | PASS |
| `rtk bash scripts/nmem-nas-domain-sync.sh preview --domain selfmedia --map scripts/nmem-space-map.example.json` | Expected blocked state: preview report created, exit 3 because NAS space is still `TBD`; no import |
| `rtk bash scripts/nmem-nas-domain-sync.sh import --domain selfmedia --map scripts/nmem-space-map.example.json --run-id dummy` | Expected rejection: missing explicit confirm |
| `rtk bash scripts/nmem-nas-domain-sync.sh import --domain selfmedia --map scripts/nmem-space-map.example.json --run-id dummy --confirm I_UNDERSTAND_THIS_IMPORTS_TO_LOCAL_NMEM` | Expected stop: gate passes but real import intentionally not implemented |
| secret-pattern scan across touched docs/scripts | PASS: no real token/API key/cookie/bearer matches |

---

## Workflow Replay

1. User asked whether to keep nmem or replace it, with NAS nmem stopped due to write timeouts.
2. Local facts were checked: NAS container stopped; data exists on NAS; local NowledgeGraph exists and local nmem was later restored to v0.10.6.
3. Official docs were checked: Mem supports one central backend with remote clients, spaces, shared context, and export/import; it does not provide multi-master sync.
4. Architecture decision: keep nmem as runtime memory; use NAS nmem for Hermes only; keep local NowledgeGraph as current primary copy; use Markdown/Library/Git for durable knowledge.
5. Single-direction sync was planned: NAS domain spaces -> export/archive -> preview/mapping/dedupe -> merge/skip into local matching space -> durable summary to Markdown/Library/Git.
6. Safety scaffold was created for mapping, preview, and import gate; real import remains intentionally disabled.

---

## Deferred / Explicitly Not Done

- NAS nmem container was not restarted.
- No NAS export was executed.
- No local nmem import was executed.
- No cron or scheduled sync was enabled.
- No Codex/Claude Code configuration was changed.
- No note source skill was modified or deleted.

---

## Verdict

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Required policy docs, data model, mapping template, and safe script scaffold are present. |
| Workflow closure | PASS | The planned sync workflow is closed at planning/scaffold level: mapping -> preview -> gated import -> audit, with real import deferred. |
| User-visible outcome | PASS | User now has a clear answer and safe next path: single-direction sync only, no double master, no overwrite by default. |

**Overall**: PASS for planning/scaffold scope.
