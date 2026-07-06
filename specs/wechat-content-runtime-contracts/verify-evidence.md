# Verify Evidence: WeChat Content Runtime Contracts

**Workspace**: `wechat-content-runtime-contracts`  
**Updated**: 2026-07-06  
**Mode**: dry-run / fixture only; no live publish, upload, provider, Notion, or YouMind call.

## Evidence Summary

| Task | Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|---|
| T001 | Content/blog/WeChat/topic/style/image owner coverage | Owner table covers required P0/P1 rows plus `account-config`, `monthly-review`, and negative-scope rows. | `specs/wechat-content-runtime-contracts/owner-table.md` | PASS |
| T002 | Replacement route docs | Route entries include `old_skill`, `route_target`, `entry`, `evidence`, and `deletion_gate`; unverified rows remain blocked. | `specs/wechat-content-runtime-contracts/replacement-routes.md` | PASS |
| T003 | Negative scope and archive gate | Notion and YouMind are marked no further investment; no Notion workflow, YouMind upload smoke, or note-source deletion is requested. | `owner-table.md`; `replacement-routes.md` | PASS |
| T004 | Article-to-draft dry-run evidence | WeChat draft build and full offline tests passed. Relevant passing subtests include Markdown import, article document rendering, publish-ready artifact build, create-draft facade from `article_document`, and DraftWorkflow dry-run behavior. | `rtk pnpm --filter @mcps/wechat-draft build`; `rtk pnpm --filter @mcps/wechat-draft test` -> 67 passed | PASS |
| T005 | Workflow artifact / article state contract evidence | hermes-db workflow and WeChat article tools/contracts passed in isolated package test run. | `rtk uv run pytest tests/test_wechat_article_tools.py tests/test_wechat_article_contracts.py tests/test_workflow_tools.py tests/test_workflow_contracts.py` from `packages/hermes-db` -> included in 71 passed, 19 skipped | PASS |
| T006 | Topic shortlist to inbox/storage dry-run | Previous runner issue is closed in agents: `cli-topic.test.ts` no longer exits nonzero, topic radar/adopt coverage passes, and original mcps-blocking combined command now passes. mcps-side hermes-db topic repo/tool tests were already passing. | `/Users/yqg/personal/AI/agents/specs/agents-wechat-content-runtime-fixes/acceptance.md`; original combined command -> 30 pass / 0 fail / 78 expect | PASS |
| T007 | Image manifest / asset handoff dry-run | MCP-side asset loader/upload preflight tests passed through `wechat-draft`; agents-side image closure E2E is now verified by focused and combined dry-run tests. No live publish/upload/provider call was made. | `/Users/yqg/personal/AI/agents/specs/agents-wechat-content-runtime-fixes/acceptance.md`; focused image closure -> 4 pass / 0 fail / 17 expect | PASS |
| T008 | Content performance monthly review sample | Agents retrospective, analytics import, and config parity offline tests passed; hermes-db analytics tools/contracts passed. Scope remains WeChat/content performance, not personal monthly review. | agents subset -> 25 passed; hermes-db selected tests -> 71 passed, 19 skipped | PASS |
| T009 | Caller reconciliation | Owner table now records caller/route proof for topic planning, article-to-draft, image/asset, content performance, and Library/account-fit source context. | `owner-table.md` Caller Reconciliation | PASS |
| T010 | Architecture drift check | Owner table records invariants: writing generation stays out of MCP, mcps does not reimplement agents runtime, no note skill deletion, Notion/YouMind remain negative scope, durable sources stay out of nmem full-text memory. | `owner-table.md` Architecture Drift Check | PASS |
| T011 | Deletion gate update | Replacement routes now record deletion gate update: no note skill deleted; thin-shell/archive decisions move to `note-thin-shell-and-archive`; full writing/live provider items remain blocked/deferred. | `replacement-routes.md` Deletion Gate Update | PASS |
| T012 | Verify evidence rollup | This table now includes T001-T011 plus Library/Memory boundary and negative-scope proof. | `verify-evidence.md` | PASS |
| T013 | Document consistency | `specs/.active` and roadmap current point to `wechat-content-runtime-contracts`; current phase is closeout. | `../note-skill-migration-roadmap/roadmap.md`; `../.active` | PASS |
| T014 | Acceptance prep | Acceptance inputs exist: evidence table, blocking/negative scope proof, Library/Memory boundary, deferred items, and roadmap next recommendation. | `verify-evidence.md`; `tasks.md`; roadmap | PASS |

## Commands Run

| Command | Result |
|---|---|
| `rtk pnpm --filter @mcps/wechat-draft build` | PASS |
| `rtk pnpm --filter @mcps/wechat-draft test` | PASS: 67 passed |
| `rtk uv run pytest tests/test_topic_repo.py tests/test_topic_repo_updates.py tests/test_wechat_article_tools.py tests/test_wechat_article_contracts.py tests/test_workflow_tools.py tests/test_workflow_contracts.py tests/test_wechat_analytics_tools.py tests/test_wechat_analytics_contracts.py` from `packages/hermes-db` | PASS: 71 passed, 19 skipped |
| `rtk bun test apps/wechat-agent/tests/topic-radar-shortlist.test.ts apps/wechat-agent/tests/cli-topic.test.ts apps/wechat-agent/tests/retrospective-report-service.test.ts apps/wechat-agent/tests/analytics-import.test.ts apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts apps/wechat-agent/tests/config-parity.test.ts` from agents repo | PASS after `agents-wechat-content-runtime-fixes`: 30 pass, 0 fail, 78 expect |
| `rtk bun test apps/wechat-agent/tests/topic-radar-shortlist.test.ts apps/wechat-agent/tests/topic-radar-health-gate.test.ts apps/wechat-agent/tests/topic-radar-context.test.ts apps/wechat-agent/tests/retrospective-report-service.test.ts apps/wechat-agent/tests/analytics-import.test.ts apps/wechat-agent/tests/config-parity.test.ts` from agents repo | PASS: 25 passed |
| `rtk pnpm --filter @mcps/wechat-draft test` on 2026-07-06 | PASS: 67 passed |
| `rtk node -e "JSON.parse(require('fs').readFileSync('specs/knowledge-library-ingestion-plan/ingestion-dry-run-manifest.example.json','utf8')); console.log('manifest ok')"` | PASS |

## Blocking Findings

### Resolved: T006 topic adopt/inbox runner failure

`apps/wechat-agent/tests/cli-topic.test.ts` printed passing topic CLI subtests, including shortlist/adopt behavior, but the file exits nonzero because `afterEach` sets `process.exitCode = undefined`, which Bun rejects with `TypeError: exitCode must be an integer`.

Current conclusion: resolved in `/Users/yqg/personal/AI/agents/specs/agents-wechat-content-runtime-fixes`; T006 is now PASS.

### Resolved: T007 image closure failure

`apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts` failed four E2E assertions:

- dry-run did not produce `transformed-draft`.
- publish payload path remained `blocked`.
- missing cover block surfaced at `brief` instead of `publish`.
- image manifest was not produced with inserted markers.

Current conclusion: resolved in `/Users/yqg/personal/AI/agents/specs/agents-wechat-content-runtime-fixes`; T007 is now PASS.

### Remaining closeout work

No T006/T007 execution blocker remains. T009-T014 closeout materials are now recorded. Remaining work is formal acceptance and roadmap update.

## Negative Scope Proof

- No command performed live publish, live upload, live provider generation, Notion workflow, or YouMind upload.
- No source under `/Users/yqg/learning/biji/note` was modified.
- No agents source file was modified; agents tests were read/run only for evidence.

## Memory / Library Boundary Dependency

`knowledge-memory-architecture` is now an explicit upstream dependency for closeout:

- nmem remains runtime memory, not the long-term source of truth for content materials.
- Long-term source materials, rules, references, durable decisions, and route docs should land in Markdown/Library/Git.
- NAS nmem may be used by Hermes as runtime memory; local Codex/Claude Code should not write NAS nmem.
- NAS domain-space writes, if enabled later, sync back to local only through one-way export/preview/merge-or-skip import gates.

Current conclusion: content runtime closeout should cite `specs/knowledge-memory-architecture/acceptance.md` once available before declaring Library/Memory deletion gates final.

2026-07-06 update: `knowledge-library-ingestion-plan` is PASS and supplies source classification, account-fit source plan, dry-run manifest, and deletion gates. Live Library import remains deferred.
