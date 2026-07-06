# Acceptance: WeChat Topic / Draft Trial

**Workspace**: `wechat-topic-draft-trial` | **Date**: 2026-07-01

---

## Current Verdict

**TRIAL ACTIVE**: 已完成投入使用前的 SDD 切换和试用边界定义；真实 topic plan / shortlist run 已完成，草稿链路已完成可复放 dry-run replay，live 草稿仍需人工确认。

## Activation Evidence

| Gate | Evidence | Verdict |
|---|---|---|
| Topic planning contract available | `specs/hermes-db-topic-plan-contract/acceptance.md`; `hermes-db-v0.2.28` production smoke | PASS |
| Topic adopt / inbox dry-run available | `specs/wechat-content-runtime-contracts/verify-evidence.md` T006 | PASS |
| Article-to-draft handoff available | `specs/wechat-content-runtime-contracts/verify-evidence.md` T004-T005 | PASS |
| Memory / Library boundary available | `specs/knowledge-memory-architecture/acceptance.md` | PASS |
| Writing feature deferred | User decision on 2026-07-01; `spec.md` out of scope | PASS |
| First topic plan / shortlist run | Production hermes-db candidate `625a39ed-1c65-4d9f-a3bf-6f636a332a85`; TopicPlan `68f1fcde-80a5-402e-b3e0-1e952a9da4c9`; candidate status `shortlisted` | PASS |
| Editorial fit feedback | User accepted Run 001 as a test topic but rejected it for real use because it does not fit the four configured public accounts. | NEEDS_ACCOUNT_FIT_GATE |
| `moon-sleeping` account positioning | User clarified it is a maternal/infant account; add 3-9 month baby topics such as complementary food, soothing to sleep, night waking, routines, feeding anxiety, and mother support. | PASS |
| Four-account config audit | `account-config-audit.md` compares production hermes-db tracks with local agents config and records drift / fit gates. | PASS |
| Draft dry-run replay | `trial-log.md` Run 003; `rtk pnpm --filter @mcps/wechat-draft test` -> 67 passed, including article_document, publish-ready artifact, create-draft facade, and DraftWorkflow dry-run/idempotency paths. | PASS |

## Remaining Trial Gates

- Human adoption decision for shortlisted TopicPlan `68f1fcde-80a5-402e-b3e0-1e952a9da4c9` remains optional and user-gated.
- Next topic trial must target one concrete account/track and pass account-fit before live draft handoff.
- Next `moon-sleeping` topic trial should use 3-9 month baby care topics, not generic sleep/emotion topics.
- Clarify whether production `draft_target=youmind` is stale or staging-only before any live draft creation.
- Live draft creation remains manual-confirmation gated; current evidence is dry-run replay only.

## Trial Decision

| Question | Decision |
|---|---|
| Continue topic planning trial? | Yes, but only after account-fit / source-context improvements. |
| Start full automatic writing feature now? | No. Current topic quality and account fit are not stable enough. |
| Start Library ingestion planning? | Yes. The next useful work is to define how account materials, platform rules, reference articles, and source notes enter Library/Wiki so planning and writing have better context. |
| Keep WeChat draft handoff? | Yes, as dry-run or manual-confirmed live action only. |

## Final Verdict

**PASS WITH MANUAL GATES**: The trial proved the current topic-plan storage path and article-to-draft dry-run handoff are usable. It also exposed that production use needs stronger account-fit and source-context handling before full writing automation. The next roadmap feature is `knowledge-library-ingestion-plan`; complete writing runtime remains deferred.
