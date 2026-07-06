# Tasks: Agents WeChat Content Runtime Fixes

**Workspace**: `agents-wechat-content-runtime-fixes`  
**Intended Repo**: `/Users/yqg/personal/AI/agents`  
**Input**: `spec.md` + `plan.md`

---

## Phase 1: Topic CLI unblocker

- [ ] T001 [US1] Reproduce `cli-topic.test.ts` failure
  - scope: `apps/wechat-agent/tests/cli-topic.test.ts`
  - command: `rtk bun test apps/wechat-agent/tests/cli-topic.test.ts`
  - verify: failure includes `TypeError: exitCode must be an integer`

- [ ] T002 [US1] Fix exitCode cleanup without weakening topic assertions
  - scope: `apps/wechat-agent/tests/cli-topic.test.ts`
  - expected change: restore `process.exitCode` in a Bun-safe way
  - blocked_by: T001
  - verify: `topic.radar`, `topic.adopt`, invalid pick tests still assert command envelopes and createTopic calls

- [ ] T003 [US1] Verify topic CLI/adopt smoke
  - scope: `apps/wechat-agent/tests/cli-topic.test.ts`
  - blocked_by: T002
  - command: `rtk bun test apps/wechat-agent/tests/cli-topic.test.ts`
  - verify: exits 0; can be used to upgrade mcps T006 from PARTIAL if combined with existing topic radar/context/hermes-db evidence

## Phase 2: Image closure diagnosis

- [ ] T004 [US2] Reproduce image closure failures
  - scope: `apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts`
  - command: `rtk bun test apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts`
  - verify: record which assertions fail and whether workflow reaches `image-prep`

- [ ] T005 [US2] Inspect stage flow and mock adapter contract
  - scope: `apps/wechat-agent/src/workflows/wechat/runtime.ts`, `packages/adapters/src/image/*`, mock adapter exports
  - blocked_by: T004
  - verify: identify root cause category: upstream block, mock adapter drift, image adapter drift, transform placement drift, publish draft selection, or policy-stage semantics

- [ ] T006 [US2] Fix transformed draft artifact production
  - scope: `runtime.ts`, image adapter/test fixtures as needed
  - blocked_by: T005
  - verify: dry-run result contains `transformed-draft` with mock CDN cover URL

- [ ] T007 [US2] Fix publish payload image consumption
  - scope: `runtime.ts`, publish adapter selection path, image manifest/transform as needed
  - blocked_by: T006
  - verify: publish adapter receives draft containing cover + inline image refs; artifactNames includes `transformed-draft`

- [ ] T008 [US2] Fix image policy blocked semantics
  - scope: `runtime.ts`, image policy check, test fixture as needed
  - blocked_by: T005
  - verify: provider failure + `imagePolicy: "block"` returns `currentStage: "publish"`, `missingInputs: ["image-policy"]`, and `image-policy-check` artifact

- [ ] T009 [US2] Fix manifest insertion markers
  - scope: `packages/adapters/src/image/transform.ts`, `packages/adapters/src/image/index.ts`, fixtures as needed
  - blocked_by: T006
  - verify: manifest has at least one `insertion: "inserted"` after successful transform

- [ ] T010 [US2] Verify image closure E2E
  - scope: `apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts`
  - blocked_by: T006, T007, T008, T009
  - command: `rtk bun test apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts`
  - verify: exits 0; no live publish/upload/provider call

## Phase 3: Combined evidence for mcps handoff

- [ ] T011 [US3] Run combined focused regression
  - blocked_by: T003, T010
  - command: `rtk bun test apps/wechat-agent/tests/cli-topic.test.ts apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts`
  - verify: exits 0

- [ ] T012 [US3] Run original mcps-blocking command
  - blocked_by: T011
  - command: `rtk bun test apps/wechat-agent/tests/topic-radar-shortlist.test.ts apps/wechat-agent/tests/cli-topic.test.ts apps/wechat-agent/tests/retrospective-report-service.test.ts apps/wechat-agent/tests/analytics-import.test.ts apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts apps/wechat-agent/tests/config-parity.test.ts`
  - verify: exits 0; record pass/fail count

- [ ] T013 [US3] Produce handoff evidence summary
  - blocked_by: T012
  - scope: agents feature acceptance or notes; later copy into `mcps/specs/wechat-content-runtime-contracts/verify-evidence.md`
  - verify: summary includes commands, result counts, changed files, and confirmation of no live external side effects

## Phase 4: Return Path To mcps

- [ ] T014 [US3] Update mcps T006 evidence after agents topic pass
  - target repo: `/Users/yqg/personal/AI/mcps`
  - blocked_by: T003, T012
  - files: `specs/wechat-content-runtime-contracts/verify-evidence.md`, `tasks.md`
  - verify: T006 becomes PASS only if CLI/adopt smoke exits 0

- [ ] T015 [US3] Update mcps T007 evidence after agents image closure pass
  - target repo: `/Users/yqg/personal/AI/mcps`
  - blocked_by: T010, T012
  - files: `specs/wechat-content-runtime-contracts/verify-evidence.md`, `tasks.md`
  - verify: T007 becomes PASS only if image closure E2E exits 0

## Stage Readiness

- 推荐下一步：在 `/Users/yqg/personal/AI/agents` 进入 `execute-plan`
- 第一执行包：T001-T003 topic CLI unblocker
- 第二执行包：T004-T010 image closure
- 不建议先做 T011+，因为它们依赖前两条失败链路

