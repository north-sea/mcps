# Verify Evidence: WeChat Draft Multi-Account Production

**Date**: 2026-06-25  
**Verdict**: PASS

---

## Implementation Scope

- `wechat-draft` account registry now supports external YAML/JSON config and includes `xiaban`.
- `xiaban.default` rendering profile is registered and covered by renderer tests.
- Production smoke uses the full MCP path: upload assets, create Hermes workflow run/artifacts, validate publish-ready artifact, create draft, check status, and verify batchget.
- Regression fixes remain in scope: Hermes metadata normalization and latest `JobStore` status lookup.

---

## Verification Commands

| Check | Result |
|---|---|
| `./node_modules/.bin/tsc -p packages/wechat-draft/tsconfig.json` | PASS |
| `./node_modules/.bin/tsc -p packages/wechat-draft-adapter/tsconfig.json` | PASS |
| `node packages/wechat-draft/test-config-loader.mjs` | PASS, 9/9 |
| `node packages/wechat-draft/test-regressions.mjs` | PASS, 5/5 |
| `node packages/wechat-draft/test-article-document-renderer.mjs` | PASS, 46/46 |
| `node --check packages/wechat-draft/scripts/live-canonical-smoke.mjs` | PASS |

`pnpm --filter ... build` was attempted earlier but failed in this environment with `[ERROR] fetch failed`; direct `tsc` is the build substitute evidence.

---

## Production Smoke Evidence

| Step | Result |
|---|---|
| Start | `account=xiaban`, `style_profile_id=xiaban.default`, `run_id=wechat-canonical-smoke-2026-06-25T15-25-36-654Z` |
| Body image upload | PASS, returned WeChat `mmbiz.qpic.cn` URL |
| Cover upload | PASS, `thumb_media_id=U7Qu_0dByR4an5_Az3THTwCNns_ph7t8Q5HIMu6qt1NFbv93s24pQJpCHGGNLPVW` |
| Workflow run | PASS, `workflow_run_upserted` |
| Source artifact | PASS, `wechat-canonical-smoke-2026-06-25T15-25-36-654Z-article-document` |
| Ready artifact | PASS, `wechat-canonical-smoke-2026-06-25T15-25-36-654Z-article-document:wechat_api_article` |
| Artifact validation | PASS, `valid=true` |
| Draft creation | PASS, `status=saved`, `media_id=U7Qu_0dByR4an5_Az3THT_HNwl9yS9CyG83VJoSyBmXzxe9FupqnYgqiFMqCGeUd` |
| Draft status | PASS, `found=true`, `status=saved` |
| Batchget | PASS, found draft, canonical text present, no markdown residue, WeChat image present |

---

## Context Manifest Coverage

`context-manifest.md` covers spec, plan, tasks, config loader, renderer, Hermes client, JobStore, adapter deployment docs, live smoke, and acceptance. It covers the active P0/P1 paths for config, production adapter visibility, artifact handoff, and user-visible draft outcome.

---

## Architecture Drift

No blocking drift found. The implementation follows the plan: account config remains in `wechat-draft`, adapter secrets remain outside the repo, Hermes remains the required artifact store for full MCP evidence, and direct adapter fallback is no longer accepted as production completion evidence.

---

## Unresolved Risks

| Risk | Impact | Status |
|---|---|---|
| Final `xiaban` brand styling | Visual polish, not correctness | Deferred to a separate feature |
| Existing dirty files outside current feature | Commit hygiene | Captured in `commit-plan.md` Needs User Decision |

---

## Verdict

PASS. The feature can be closed out. No blocker remains for the stated multi-account production smoke goal.
