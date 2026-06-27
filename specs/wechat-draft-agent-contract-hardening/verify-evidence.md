# Verify Evidence: WeChat Draft Agent Contract Hardening

**Workspace**: `wechat-draft-agent-contract-hardening`
**Created**: 2026-06-27
**Status**: pass

---

## Baseline / Failed Behavior

| Case | Before Behavior | Evidence Source | After Guard |
|---|---|---|---|
| Hidden image constraints | Agent learned cover/body image limits through upload failures. | `AssetSourceLoader` had private size/MIME constants only. | `wechat_list_accounts` now returns `constraints.assets`; tests assert values match guards. |
| Asset errors not actionable | Asset failures returned code/message/details without next action. | Existing `errorMapping.ts` and upload tests. | `mapOperationalErrorToResult` adds `next_action`, `remediation_hint`, `retryable`, `current_phase` and redacts source paths. |
| `content_ref` only artifact | Draft payload builder threw internal `T013 limitation` text. | Previous `DraftPayloadBuilder.extractContent` throw. | `DraftWorkflow` returns `re_upsert_inline_content_text`; test asserts no `T013` in message. |
| Artifact idempotency hit | Hermes artifact upsert returned `created=false` without skipped update reason. | `workflow_repo.upsert_artifact` short-circuit path. | Tool response includes `idempotency_hit`, `skipped_update_reason`, and hash context. |
| Artifact id conflict | Tool returned only `artifact_id_conflict`. | `workflow_artifacts.py` mapped conflict without details. | Conflict response includes existing/provided hash and remediation fields. |
| Missing workflow run FK | Raw FK detail could leak as generic database error. | DB exception path for `workflow_artifacts_run_id_fkey`. | Tool maps this to `field=run_id`, `next_action=upsert_workflow_run`, and no raw SQL detail. |

---

## Verification Runs

| Time | Command | Result | Notes |
|---|---|---|---|
| 2026-06-27 | `pnpm --filter @mcps/wechat-draft build` | PASS | TypeScript build passed after contract/error changes. |
| 2026-06-27 | `pnpm --filter @mcps/wechat-draft test` | PASS | 44 tests passed, including constraints, error mapping, HTTP MCP smoke, and workflow remediation tests. |
| 2026-06-27 | `uv run pytest tests/test_workflow_tools.py tests/test_workflow_repo_sql.py` from `packages/hermes-db` | PASS | 10 tests passed, including artifact outcome, conflict remediation, missing run mapping, and repo return shape. |
| 2026-06-27 | `uv run pytest tests/test_workflow_tools.py tests/test_workflow_repo_sql.py tests/test_workflow_integration.py tests/test_wechat_article_integration.py tests/test_wechat_analytics_integration.py` from `packages/hermes-db` | PASS | 10 passed, 3 skipped. Skipped tests require DB integration fixture; non-DB workflow contract tests passed. |
| 2026-06-27 | `git diff --check` | PASS | No whitespace errors. |
| 2026-06-27 | `bash /Users/yqg/.agents/skills/sdd/scripts/validate-sdd.sh` | PARTIAL | Script reported `missing file: specs/.active`, but direct workspace check shows `/Users/yqg/personal/AI/mcps/specs/.active` exists and points to this feature. Treated as validator working-directory/package-hygiene mismatch, not feature blocker. |
| 2026-06-27 | `rg -n -- "- \\[ \\]" specs/wechat-draft-agent-contract-hardening/tasks.md specs/wechat-draft-http-service/tasks.md` | PASS | No open task checkboxes in the active feature or closed prerequisite feature. |

---

## Diffusion Check

Command:

```bash
rg -n "T013|workflow_artifacts_run_id_fkey|artifact_id_conflict|content_ref is not yet supported" packages/wechat-draft packages/hermes-db docs specs/wechat-draft-agent-contract-hardening
```

Findings:

- WeChat runtime source no longer contains `content_ref is not yet supported` or the old `T013 limitation` user-facing throw.
- Remaining `T013` hits are SDD/spec references, unrelated package docs, or unrelated hermes topic/novel tests.
- `workflow_artifacts_run_id_fkey` remains in schema health expected-constraint checks and in the mapper/test that converts the DB exception into `next_action=upsert_workflow_run`.
- `artifact_id_conflict` remains as the public stable error code, now with hash context and remediation in workflow artifact tools.

---

## Remaining Risk

- JSON `content_text` object-vs-string parsing root cause may still involve MCP client/tool binding outside this package. This feature mitigates it by documenting the actual string payload shape; typed article document tools remain a later roadmap feature.
- Cover media channel remains conservative: `thumb`/64KB. Switching to permanent `image` requires live WeChat evidence and is deferred.
