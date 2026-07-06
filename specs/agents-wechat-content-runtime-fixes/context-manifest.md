# Context Manifest: Agents WeChat Content Runtime Fixes

**Workspace**: `agents-wechat-content-runtime-fixes`  
**Intended Repo**: `/Users/yqg/personal/AI/agents`  
**Status**: active handoff context

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `apps/wechat-agent/tests/cli-topic.test.ts` | Topic CLI/adopt failure source; contains Bun-incompatible `process.exitCode = undefined` cleanup | implement | yes |
| `apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts` | Image closure failing E2E; defines transformed draft, publish payload, policy block, insertion marker contract | implement | yes |
| `apps/wechat-agent/src/workflows/wechat/runtime.ts` | Stage handlers for `image-prep`, `publish`, blocked semantics, artifact creation, and `executeWechatHappyPath` | implement | yes |
| `apps/wechat-agent/src/workflows/wechat/definition.ts` | Stage order includes `image-prep` before `publish` | implement | yes |
| `packages/adapters/src/image/index.ts` | `PlaceholderImageAdapter`, `ImagePrepAdapter`, manifest generation, transform call, insertion marking | implement | yes |
| `packages/adapters/src/image/manifest.ts` | Image manifest shape, policy summary/recovery hint behavior | implement | yes |
| `packages/adapters/src/image/transform.ts` | Draft image insertion behavior and placement matching | implement | yes |
| `packages/adapters/src/index.ts` and mock adapter source | `createMockAdapters()` behavior may have drifted from image closure test expectations | implement | yes |
| `/Users/yqg/personal/AI/mcps/specs/wechat-content-runtime-contracts/verify-evidence.md` | Upstream evidence and blocking reason to update after fix | verify / closeout | yes |
| `/Users/yqg/personal/AI/mcps/specs/wechat-content-runtime-contracts/tasks.md` | Upstream T006/T007 status to update only after fresh passing evidence | verify / closeout | yes |

## Known Commands

Failing reproducer:

```bash
rtk bun test apps/wechat-agent/tests/topic-radar-shortlist.test.ts apps/wechat-agent/tests/cli-topic.test.ts apps/wechat-agent/tests/retrospective-report-service.test.ts apps/wechat-agent/tests/analytics-import.test.ts apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts apps/wechat-agent/tests/config-parity.test.ts
```

Focused commands:

```bash
rtk bun test apps/wechat-agent/tests/cli-topic.test.ts
rtk bun test apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts
rtk bun test apps/wechat-agent/tests/cli-topic.test.ts apps/wechat-agent/tests/wechat-workflow-image-closure.test.ts
```

Already passing control subset:

```bash
rtk bun test apps/wechat-agent/tests/topic-radar-shortlist.test.ts apps/wechat-agent/tests/topic-radar-health-gate.test.ts apps/wechat-agent/tests/topic-radar-context.test.ts apps/wechat-agent/tests/retrospective-report-service.test.ts apps/wechat-agent/tests/analytics-import.test.ts apps/wechat-agent/tests/config-parity.test.ts
```

Observed result: 25 passed, 0 failed.

## Rules

- Use mock/dry-run only.
- Do not call real publish, image provider, upload, Notion, or YouMind.
- Do not weaken tests merely to pass; if contract changed, update spec/plan and provide stronger replacement evidence.
- Do not modify `mcps` runtime code for this agents-side feature.
- Return evidence to `mcps/wechat-content-runtime-contracts` only after target commands exit 0.

