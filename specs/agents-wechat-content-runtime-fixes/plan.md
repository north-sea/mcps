# Implementation Plan: Agents WeChat Content Runtime Fixes

**Workspace**: `agents-wechat-content-runtime-fixes`  
**Intended Repo**: `/Users/yqg/personal/AI/agents`  
**Spec**: `spec.md`

---

## Summary

本 feature 是 `mcps/wechat-content-runtime-contracts` 的跨仓 unblocker。实现应在 agents 仓完成，目标是让 topic CLI/adopt smoke 和 image closure E2E 在 mock/dry-run 条件下稳定通过。

方案分两条 slice：

1. **Topic CLI Stability**：修复 `cli-topic.test.ts` afterEach 对 `process.exitCode` 的恢复方式，让已有 topic/adopt 断言能正常贡献 T006 evidence。
2. **Image Closure Contract**：查清 `executeWechatHappyPath` 在 `image-prep` 和 `publish` 阶段为什么没有产出/消费 `transformed-draft`、manifest insertion markers 和 policy block artifact，并修复 runtime 或测试契约。

---

## Architecture Context

```text
mcps/wechat-content-runtime-contracts
  T006 waits on agents topic CLI/adopt evidence
  T007 waits on agents image producer evidence

agents/apps/wechat-agent
  tests/cli-topic.test.ts
    -> createCliProgram()
    -> topic.radar / topic.adopt
    -> mock topicToolsPort.createTopic()

  tests/wechat-workflow-image-closure.test.ts
    -> executeWechatHappyPath()
    -> runtime stages: input-parse ... image-prep -> publish
    -> adapters.image.prepareImage()
    -> transformDraftWithImages()
    -> adapters.publish.publishDraft()
```

MCP-side contract 已通过：

- `@mcps/wechat-draft` build + test: 67 passed
- `packages/hermes-db` topic/article/workflow/analytics selected tests: 71 passed, 19 skipped

因此本 feature 不应去 mcps 重写契约；应修复 agents producer/CLI 证据。

---

## Module Design

### Module 1: Topic CLI Test Exit Handling

**Files**:

- `apps/wechat-agent/tests/cli-topic.test.ts`

**Current finding**:

```ts
afterEach(() => {
  vi.restoreAllMocks();
  process.exitCode = undefined;
  ...
});
```

Bun rejects `process.exitCode = undefined` with `TypeError: exitCode must be an integer`.

**Recommended fix**:

- Capture prior `process.exitCode` before each test or at file start.
- Restore only valid integer values.
- If no prior exit code exists, delete/reset via an approach Bun accepts, or set to `0` only if that does not mask command failure semantics.

**Acceptance command**:

```bash
rtk bun test apps/wechat-agent/tests/cli-topic.test.ts
```

**YAGNI**: Do not rewrite CLI framework or command parsing. This is a test/runtime hygiene fix.

### Module 2: Image Closure Runtime Contract

**Files to inspect first**:

- `apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts`
- `apps/wechat-agent/src/workflows/wechat/runtime.ts`
- `apps/wechat-agent/src/workflows/wechat/definition.ts`
- `packages/adapters/src/image/index.ts`
- `packages/adapters/src/image/manifest.ts`
- `packages/adapters/src/image/transform.ts`
- `packages/adapters/src/index.ts` or mock adapter exports

**Current failing assertions**:

- `transformed-draft` artifact is undefined after dry-run.
- publish path remains `blocked`.
- `imagePolicy: "block"` failure surfaces at `brief`, not `publish`.
- `image-prep` manifest is undefined or lacks inserted markers.

**Likely investigation branches**:

1. Stage gating: earlier stage blocks before `image-prep`, possibly due to changed validation/review/brief behavior.
2. Mock adapter drift: `createMockAdapters()` may no longer provide enough draft/review/image/publish data for full stage execution.
3. Image adapter drift: `PlaceholderImageAdapter` returns a manifest but no `transformedDraft`; E2E may require `ImagePrepAdapter` with generated/uploaded/mock CDN URLs.
4. Draft content drift: `transformDraftWithImages()` only inserts inline images when `placement` matches body blocks; mock draft/manifest placement may no longer align.
5. Policy check drift: publish stage may check image policy before image-prep artifacts exist, or stage runner may preserve `currentStage` incorrectly when blocked.

**Recommended fix order**:

1. Run only image closure test and inspect result state via temporary local debugging, then remove debug output.
2. Confirm whether workflow reaches `image-prep`.
3. If it does not reach `image-prep`, fix upstream mock inputs/adapters or stage gating.
4. If it reaches `image-prep` but no `transformed-draft`, fix image adapter/runtime artifact creation.
5. If transformed draft exists but publish ignores it, fix publish stage draft selection.
6. If policy block stage is wrong, fix blocked response currentStage semantics or update test only if the product contract intentionally changed.

**Acceptance command**:

```bash
rtk bun test apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts
```

### Module 3: Combined Regression Evidence

**Commands**:

```bash
rtk bun test apps/wechat-agent/tests/cli-topic.test.ts apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts
rtk bun test apps/wechat-agent/tests/topic-radar-shortlist.test.ts apps/wechat-agent/tests/cli-topic.test.ts apps/wechat-agent/tests/retrospective-report-service.test.ts apps/wechat-agent/tests/analytics-import.test.ts apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts apps/wechat-agent/tests/config-parity.test.ts
```

**Expected**:

- Both commands exit 0.
- No live external side effects.
- Evidence summary can be copied back to `mcps/specs/wechat-content-runtime-contracts/verify-evidence.md`.

---

## Risks

- **Masking failures**: Setting `process.exitCode = 0` blindly can hide CLI failures. Prefer preserving/restoring prior valid state.
- **Updating tests to match broken runtime**: Do not weaken image closure assertions unless runtime contract has intentionally changed and replacement evidence is stronger.
- **Live side effects**: Do not use real publish/image provider/upload to make E2E pass.
- **Cross-repo drift**: This fix unblocks mcps docs, but the source of truth for code behavior is agents tests.

## Verification Plan

1. `rtk bun test apps/wechat-agent/tests/cli-topic.test.ts`
2. `rtk bun test apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts`
3. `rtk bun test apps/wechat-agent/tests/cli-topic.test.ts apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts`
4. `rtk bun test apps/wechat-agent/tests/topic-radar-shortlist.test.ts apps/wechat-agent/tests/cli-topic.test.ts apps/wechat-agent/tests/retrospective-report-service.test.ts apps/wechat-agent/tests/analytics-import.test.ts apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts apps/wechat-agent/tests/config-parity.test.ts`

After pass, return to `mcps` and update:

- `specs/wechat-content-runtime-contracts/verify-evidence.md`: T006/T007 verdicts
- `specs/wechat-content-runtime-contracts/tasks.md`: check T006/T007 if evidence is complete

## Stage Readiness

- 下一步建议：`tasks`
- 阻塞项：无；实现入口和验证命令明确。

