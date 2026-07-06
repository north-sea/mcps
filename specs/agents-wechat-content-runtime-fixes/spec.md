# Feature Specification: Agents WeChat Content Runtime Fixes

**Workspace**: `agents-wechat-content-runtime-fixes`  
**Intended Repo**: `/Users/yqg/personal/AI/agents`  
**Created From**: `mcps/specs/wechat-content-runtime-contracts/verify-evidence.md`  
**Created**: 2026-06-28  
**Status**: Ready for Plan

> 本目录是跨仓 handoff feature。当前写在 `mcps` 仓，目的是把 agents 仓需要修复的上下文整理成 SDD 产物；实际修复应在 `/Users/yqg/personal/AI/agents` 中进行。不要因此切换 `mcps/specs/.active`。

---

## Problem Statement

`mcps` 的 `wechat-content-runtime-contracts` 已完成 owner table、replacement routes、article-to-draft、workflow/article state、monthly review 等证据，但仍被两个 agents 侧问题阻塞：

1. `T006 Topic shortlist 到 inbox/storage dry-run` 只能判定为 `PARTIAL`。`apps/wechat-agent/tests/cli-topic.test.ts` 中 topic CLI/adopt 子测试打印 pass，但测试文件整体 exit 1，因为 `afterEach` 设置 `process.exitCode = undefined`，Bun 报 `TypeError: exitCode must be an integer`。
2. `T007 Image manifest / asset handoff dry-run` 判定为 `FAIL`。`apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts` 的 4 个 E2E 用例失败，说明 agents producer-side image handoff 尚未闭合到 transformed draft / publish payload / image manifest insertion markers。

本 feature 的目标是修复 agents 侧运行时或测试，使 `mcps` 的 `wechat-content-runtime-contracts` 可以继续 `T006/T007 -> T009 caller reconciliation`。

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| `multi-stage-workflow` | ✅ | 涉及 WeChat workflow 的 `image-prep`、`publish`、topic radar/adopt CLI。 |
| `artifact-handoff` | ✅ | 需要证明 image manifest -> transformed draft -> publish payload，以及 topic shortlist -> adopt/storage。 |
| `external-side-effects` | ✅ | topic adopt 可能写入 topic tools；publish/image provider 可能外部副作用。验证必须保持 mock/dry-run。 |
| `user-visible-output` | ✅ | 输出最终影响公众号文章草稿内容、图片引用、topic 采纳结果。 |
| `bugfix-loop-breaker` | ✅ | 已有失败证据，必须先解释根因，不可盲目改测试期望。 |

---

## User Stories

### US1 - Topic CLI/adopt smoke 能稳定退出 0 (P1)

作为迁移验证者，我希望 `cli-topic.test.ts` 中 topic radar/adopt 测试在 Bun 下稳定通过并退出 0，以便 `mcps` 能把 T006 从 `PARTIAL` 升为 `PASS`。

**Acceptance Scenarios**:

1. Given `apps/wechat-agent/tests/cli-topic.test.ts`  
   When 运行 `rtk bun test apps/wechat-agent/tests/cli-topic.test.ts`  
   Then 测试进程退出 0，不再出现 `TypeError: exitCode must be an integer`

2. Given topic shortlist fixture  
   When 运行 `topic.adopt` 测试  
   Then created topic 包含 `source: topic-radar-adopt`、`revisit_of`、`mother_theme` 等字段，证明 shortlist -> adopt/storage mock path 闭合

### US2 - Image closure E2E 重新闭合 (P1)

作为内容 runtime 维护者，我希望 WeChat workflow 的 image closure E2E 能证明 dry-run 和 publish payload 都消费 image manifest，并生成 `transformed-draft`。

**Acceptance Scenarios**:

1. Given dry-run workflow input  
   When 运行 `wechat-workflow-image-closure.test.ts`  
   Then workflow 产生 `transformed-draft` artifact，内容包含 mock CDN cover URL，并且 publish lifecycle 标记 dry-run

2. Given publish workflow input with mock adapters  
   When 运行 publish payload 用例  
   Then workflow 不 blocked，publish adapter 捕获的 draft 包含 cover 和至少 2 个 inline mock CDN image refs，artifactNames 包含 `transformed-draft`

3. Given `imagePolicy: "block"` and image provider unavailable  
   When image prep/provider 失败  
   Then workflow 应在 publish 阶段 blocked，`missingInputs` 包含 `image-policy`，生成 `image-policy-check` artifact 和 recovery hint

4. Given transform succeeds  
   When image manifest 被消费  
   Then manifest 中至少一个 image item 有 `insertion: "inserted"`

### US3 - 修复后回传 mcps 验证证据 (P2)

作为 `wechat-content-runtime-contracts` 的执行者，我希望 agents 修复完成后有明确命令和结果，便于回到 `mcps` 更新 `verify-evidence.md` 和勾选 T006/T007。

**Acceptance Scenarios**:

1. Given agents 修复完成  
   When 运行目标命令  
   Then 记录完整命令、通过数、失败数、跳过数，以及是否涉及 live external side effect

---

## Functional Requirements

- **FR-001**: 必须修复 `apps/wechat-agent/tests/cli-topic.test.ts` 的 exitCode 清理问题；不得通过删除 topic/adopt 覆盖来让测试通过。
- **FR-002**: 必须保留或增强 topic radar/adopt 对 shortlist -> createTopic mock storage 的断言。
- **FR-003**: 必须定位 `wechat-workflow-image-closure.test.ts` 失败根因，是 runtime stage flow、mock adapter、image adapter、draft content、还是测试期望漂移。
- **FR-004**: 必须让 image closure E2E 的 4 个场景通过，或在确认测试期望过期时更新测试并写明新契约。
- **FR-005**: 验证必须使用 dry-run/mock/fixture；不得触发真实 publish、真实 upload、真实 image provider、YouMind 或 Notion 调用。
- **FR-006**: 修复不得把图片生成 prompt、写作生成、发布业务逻辑下沉到 `mcps`；agents 仍是执行层。
- **FR-007**: 修复完成后必须提供可复制回 `mcps/specs/wechat-content-runtime-contracts/verify-evidence.md` 的 evidence 摘要。

## Non-Functional Requirements

- **NFR-001**: 测试应能在本地无凭据环境稳定通过。
- **NFR-002**: 不引入 sleep、随机网络调用或外部服务依赖。
- **NFR-003**: 不降低错误路径可诊断性；image policy blocked 时必须有 recovery hint。

## Out of Scope

- 不修改 `/Users/yqg/personal/AI/mcps` 的 runtime 代码。
- 不执行 live publish、live upload、live image generation。
- 不恢复 YouMind 或 Notion 工作流。
- 不删除、移动或归档 note skill。
- 不解决 blog writer、review、Library ingestion、novel runtime 等后续迁移问题。

## Known Fresh Evidence

Failing command from agents repo:

```bash
rtk bun test apps/wechat-agent/tests/topic-radar-shortlist.test.ts apps/wechat-agent/tests/cli-topic.test.ts apps/wechat-agent/tests/retrospective-report-service.test.ts apps/wechat-agent/tests/analytics-import.test.ts apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts apps/wechat-agent/tests/config-parity.test.ts
```

Observed result:

- 26 pass, 4 fail, 6 errors
- `cli-topic.test.ts` topic subtests printed pass but file produced unhandled errors from `process.exitCode = undefined`
- `wechat-workflow-image-closure.test.ts` failed 4 image closure assertions

Passing control command:

```bash
rtk bun test apps/wechat-agent/tests/topic-radar-shortlist.test.ts apps/wechat-agent/tests/topic-radar-health-gate.test.ts apps/wechat-agent/tests/topic-radar-context.test.ts apps/wechat-agent/tests/retrospective-report-service.test.ts apps/wechat-agent/tests/analytics-import.test.ts apps/wechat-agent/tests/config-parity.test.ts
```

Observed result:

- 25 pass, 0 fail

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项：无；失败现象、目标文件、验收命令已明确。

