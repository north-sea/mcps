# Acceptance: WeChat Draft Multi-Account Production

**Workspace**: `wechat-draft-multi-account-production`  
**Date**: 2026-06-25  
**Status**: PASS - local implementation complete and production smoke verified

---

## Verdict Summary

| Dimension | Verdict | Evidence |
|---|---|---|
| Component | PASS | Config loader, account registry, `xiaban.default`, smoke script, Hermes metadata normalize, and JobStore latest-state behavior compile and pass local regression tests. |
| Workflow | PASS | ECS adapter env sync, `/accounts/xiaban/check-credentials`, asset upload, hermes-db run/artifact write, draft create, batchget, and ledger verification all completed. |
| User-visible Outcome | PASS | A real `xiaban` WeChat draft was created and surfaced via batchget. |

---

## Evidence Table

| Requirement / Gate | Status | Evidence |
|---|---|---|
| US1 external account registry | PASS | Config loader tests 9/9; YAML example includes `xiaban`; fallback still works. |
| US2 `xiaban` adapter visibility | PASS | ECS `/health` includes `xiaban`; credential dry-run returned token metadata only. |
| US3 full MCP draft path | PASS | Full smoke run `wechat-canonical-smoke-2026-06-25T15-25-36-654Z` created a saved draft and batchget found it. |
| Artifact handoff | PASS | Workflow run, source artifact, ready artifact, and `wechat_validate_publish_artifact` all passed. |
| User-visible output | PASS | Draft `media_id=U7Qu_0dByR4an5_Az3THT_HNwl9yS9CyG83VJoSyBmXzxe9FupqnYgqiFMqCGeUd`; batchget checks all true. |
| Secret hygiene | PASS | No raw AppSecret, access token, adapter auth token, or Hermes token recorded. |

---

## Local Evidence

- `./node_modules/.bin/tsc -p packages/wechat-draft/tsconfig.json`: PASS
- `./node_modules/.bin/tsc -p packages/wechat-draft-adapter/tsconfig.json`: PASS
- `node packages/wechat-draft/test-config-loader.mjs`: PASS, 9/9
- `node packages/wechat-draft/test-regressions.mjs`: PASS, 5/5
- `node packages/wechat-draft/test-article-document-renderer.mjs`: PASS, 46/46

`pnpm --filter ... build` was attempted but the local wrapper failed with `[ERROR] fetch failed`; direct `tsc` was used as the build evidence for this implementation pass.

- `2026-06-25` full smoke: `run_id=wechat-canonical-smoke-2026-06-25T15-25-36-654Z`, `artifact_id=wechat-canonical-smoke-2026-06-25T15-25-36-654Z-article-document:wechat_api_article`, `media_id=U7Qu_0dByR4an5_Az3THT_HNwl9yS9CyG83VJoSyBmXzxe9FupqnYgqiFMqCGeUd`, `job_status=saved`.
- Batchget checks passed: found `true`, canonical text `true`, no markdown residue `true`, WeChat image `true`.

---

## Completed Scope

- `ConfigLoader` can load YAML/JSON config via `WECHAT_DRAFT_CONFIG_PATH`, injects hermes auth token from env only, and keeps inline fallback.
- Account registry example now includes `weiyuchengchun`, `yueliang`, and `xiaban` without raw secrets.
- Config validation fails on invalid account IDs and adapter `allowed_accounts` drift.
- `xiaban.default` is registered and fails closed for unknown profiles.
- Live canonical smoke uses `${account}.default` by default and refuses direct adapter fallback when `HERMES_DB_AUTH_TOKEN` is missing.
- Existing production-loop fixes are covered: hermes-db string metadata normalization and JobStore latest `updated_at` state lookup.

---

## Production Evidence

- T007: ECS adapter `/health` includes `xiaban` in `allowed_accounts`.
- T008: `xiaban` credential dry-run returned success with token metadata only.
- T009: body image returned a WeChat `mmbiz.qpic.cn` URL; cover image returned `thumb_media_id=U7Qu_0dByR4an5_Az3THTwCNns_ph7t8Q5HIMu6qt1NFbv93s24pQJpCHGGNLPVW`.
- T010: `upsert_workflow_run`, source artifact upsert, ready artifact upsert, and `wechat_validate_publish_artifact` all passed.
- T011: `wechat_create_draft` returned `media_id=U7Qu_0dByR4an5_Az3THT_HNwl9yS9CyG83VJoSyBmXzxe9FupqnYgqiFMqCGeUd` with status `saved`.
- T012: adapter `drafts/batchget` found the draft and passed canonical text, markdown residue, and WeChat image checks.

---

## Closeout Checklist

| Item | Status | Evidence |
|---|---|---|
| Old fallback retirement | Completed | Live smoke now requires `HERMES_DB_AUTH_TOKEN` and refuses direct adapter fallback as full MCP evidence. |
| Production follow-through | Completed | ECS env sync, service restart, `xiaban` credential dry-run, and full smoke completed on 2026-06-25. |
| Documentation | Completed | Account registry, adapter deployment docs, runbook, and canonical artifact docs were updated. |
| Architecture decisions | Completed | `xiaban` account id, YAML config priority, and `xiaban.default` profile are captured in spec/tasks and implementation. |
| Roadmap update | Not applicable | No `roadmap.md` references this feature. |
| Commit plan | Draft | Commit plan generated locally; no `git add` or `git commit` performed without user confirmation. |
| Knowledge Capture | Completed | See table below; recorded locally only. |

---

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| convention | xiaban account id | 《下班不躺平》 uses stable account id `xiaban`; profile id defaults to `xiaban.default`. | `tasks.md` T002/T004, full smoke run | `wechat-draft` account registry and rendering profiles | recorded-only | 无 |
| pattern | Full MCP smoke gate | A production smoke is valid only when it uses Hermes auth, writes workflow run/artifacts, validates publish-ready artifact, creates draft, and verifies batchget. Direct adapter fallback is not completion evidence. | `live-canonical-smoke.mjs`, full smoke run | WeChat draft production verification | recorded-only | 无 |
| gotcha | JSON source artifact content | Source `article_document` JSON is stored through `content_ref` in live smoke while the ready artifact stores HTML `content_text`, avoiding MCP boundary type coercion of JSON-like strings. | `live-canonical-smoke.mjs` | Hermes workflow artifact handoff | recorded-only | 无 |

---

## Completion Record

**Overall Verdict**: PASS  
**Completion Date**: 2026-06-25  
**Completion Evidence**: `run_id=wechat-canonical-smoke-2026-06-25T15-25-36-654Z`  
**Commit Status**: committed locally as `a88eb8f`; `.pnpm-store/` left untracked.

---

## Residual Risk

- `xiaban.default` is production-safe but not final brand styling.
- Final brand-specific typography and visual style can be refined in a separate feature.
