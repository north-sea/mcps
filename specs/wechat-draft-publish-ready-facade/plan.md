# Implementation Plan: WeChat Draft Publish-Ready Facade

**Workspace**: `wechat-draft-publish-ready-facade` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/wechat-draft-publish-ready-facade/spec.md`

---

## Summary

Add one agent-facing facade tool that turns either an existing publish-ready artifact ID or a canonical `article_document` into a WeChat draft, while preserving phase trace and remediation details. The plan extends `HermesDbClient` with minimal wrappers for existing Hermes MCP `upsert_workflow_run` and `upsert_workflow_artifact` tools; it does not create new Hermes behavior or generic versioning.

---

## Architecture Overview

```text
Agent
  -> wechat_create_draft_facade
    mode=existing_publish_artifact
      -> validatePublishArtifact
      -> createDraft

    mode=article_document
      -> optional asset preflight
      -> validate/render/build publish-ready payload
      -> HermesDbClient.upsertWorkflowRun
      -> HermesDbClient.upsertWorkflowArtifact
      -> validatePublishArtifact
      -> createDraft

  <- facade response: phase_trace + artifact summary + draft job + next_action on failure
```

The facade composes existing service methods and workflows. Low-level tools remain available.

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| Facade existing-artifact mode | validated publish-ready artifact summary | `createDraft` / `DraftWorkflow` | Test asserts validation happens before draft creation and invalid artifact skips draft. |
| `buildPublishReadyArtifact` | Hermes upsert payload | `HermesDbClient.upsertWorkflowArtifact` | Test asserts article-document mode calls upsert with returned payload. |
| `HermesDbClient.upsertWorkflowArtifact` | persisted `publish_ready` artifact ID | `validatePublishArtifact` and `createDraft` | Test asserts facade validates and creates draft using persisted artifact ID. |
| `createDraft` | draft job/media result | Facade response | Test asserts response includes job, media ID, idempotency key, and phase trace. |

**孤儿 artifact 处理**: No orphan artifact should be produced on validation/preflight/build failure. If artifact upsert succeeds but draft creation fails, response must include generated artifact ID and stopped phase for recovery.

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 可恢复性 | Every stopped phase returns current phase and next action | Shared phase trace builder | Failure tests for validate/build/upsert/draft |
| 一致性 | Reuse existing lower-level service methods | Facade orchestrates, does not re-render/revalidate manually | Tests spy/counter lower-level calls |
| 安全性 | No raw Hermes/adapter/path leakage | Map facade errors to existing envelope | Error tests |
| 幂等性 | Repeated calls can reuse idempotency key | Expose and pass idempotency key to `createDraft` | Duplicate call test via job store/workflow mock |
| 可演进性 | Facade output can feed ops/versioning later | Typed phase trace and artifact summary | Schema/tests |

---

## Bugfix Strategy

| Field | Value |
|---|---|
| Observed Behavior | Agents must manually call validate/build/upsert/validate/create draft and recover from each failure themselves. |
| Expected Behavior | One facade call composes the happy path while exposing phase trace and lower-level recovery actions. |
| Reproduction Status | reproducible from prior workflow notes and completed feature evidence. |
| Root Cause Hypothesis | Low-level capabilities exist but no orchestration surface preserves diagnostics across the sequence. |
| Fix Boundary | Add facade service/tool and minimal Hermes client wrappers; no content generation, image compression, draft CRUD, or generic artifact versioning. |
| Failed Attempt Handling | If article-document mode cannot upsert artifact, return structured `upsert_publish_ready_artifact` action and record evidence; do not silently skip draft. |
| Regression Guard Strategy | Unit/contract tests for existing artifact mode, article-document mode, invalid validation, missing assets, upsert conflict, and draft workflow failure propagation. |
| Diffusion Check Strategy | Confirm facade does not duplicate renderer/preflight/draft logic and low-level tools remain registered. |
| Verification Path | `pnpm --filter @mcps/wechat-draft build`; `pnpm --filter @mcps/wechat-draft test`; `git diff --check`. |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001 one facade tool with source mode | User wants one "send to draft" surface | A: one tool with `source_type`; B: two tools; C: keep manual | Choose A | More complex input schema | local roadmap |
| ADR-002 extend HermesDbClient minimally | Hermes MCP has upsert tools, TS client lacks wrappers | A: add wrappers; B: fail and ask agent to upsert; C: add new Hermes MCP behavior | Choose A | More client surface; no new backend behavior | local Hermes tools |
| ADR-003 compose existing service methods | Article/render/preflight/draft logic already exists | A: compose; B: duplicate internal implementation | Choose A | Facade depends on stable service methods | local code |
| ADR-004 no implicit asset upload/compression | Preflight feature intentionally recommendation-only | A: preflight only; B: upload/compress inside facade | Choose A | Agents must prepare assets first | prior acceptance |

---

## Key Design Decisions

### Decision 1: Facade Modes

- **Existing artifact mode**: input has `source_type='publish_ready_artifact'` and `artifact_id`; facade validates then creates draft.
- **Article document mode**: input has `source_type='article_document'`, `article`, `run_id`, `publish_artifact_id`; facade builds/upserts/validates/creates draft.
- **Rationale**: Keeps the tool one-call for agents while keeping state transitions explicit in phase trace.

### Decision 2: Hermes Writes

- **Conclusion**: Add `HermesDbClient.upsertWorkflowRun` and `upsertWorkflowArtifact` wrappers around existing Hermes MCP tools.
- **Rationale**: The backend contract already exists and was hardened; avoiding it would leave article-document facade incomplete.
- **Limit**: Do not add version/diff/force_update semantics.

### Decision 3: Phase Trace

- **Conclusion**: Each facade response includes `phase_trace: Array<{phase,status,artifact_id?,message?}>`, `current_phase`, and `completed_phases`.
- **Rationale**: Prevents facade from becoming a black box and supports recovery.

---

## Module Design

### Module: Schemas

**职责**: Define facade input/output.

**改动概述**:

- Add `CreateDraftFacadeInputSchema` with discriminated `source_type`:
  - `publish_ready_artifact`
  - `article_document`
- Add `CreateDraftFacadeOutputSchema` with:
  - `account`
  - `source_type`
  - `idempotency_key`
  - `publish_artifact_id`
  - `phase_trace`
  - `validation_summary`
  - `draft`
  - `upsert_outcome`

**YAGNI stop**: Layer 4, zod schemas only. No workflow DSL.

### Module: HermesDbClient

**职责**: Minimal wrappers for existing Hermes workflow MCP tools.

**改动概述**:

- Add `upsertWorkflowRun(args)`.
- Add `upsertWorkflowArtifact(args)`.
- Preserve structured errors returned by Hermes tool; throw only transport/JSON-RPC errors.

**YAGNI stop**: Layer 5, wrapper around existing `callTool`. No new backend or versioning.

### Module: WechatDraftService Facade

**职责**: Orchestrate phases and return a rich result.

**改动概述**:

- Add `createDraftFacade(input)`.
- Use internal phase helper:
  - `input_validation`
  - `asset_preflight`
  - `artifact_build`
  - `workflow_run_upsert`
  - `artifact_upsert`
  - `publish_validation`
  - `draft_create`
- Existing artifact mode skips build/upsert phases.
- Article document mode calls existing `buildPublishReadyArtifact`, then Hermes upsert wrappers, then existing `validatePublishArtifact` and `createDraft`.

**YAGNI stop**: Layer 6 minimal orchestration. No persistent job state beyond existing draft job store/Hermes writes.

### Module: MCP Registration

**职责**: Register `wechat_create_draft_facade`.

**改动概述**:

- Add tool with explicit side-effect description.
- It is side-effecting because it can write Hermes and create WeChat drafts.
- Use existing logging and `toMcpToolResult`; mark non-saved draft states as MCP errors similar to `wechat_create_draft`.

**YAGNI stop**: current MCP registration pattern.

### Module: Tests And Docs

**职责**: Prove orchestration and boundaries.

**改动概述**:

- Service tests for existing artifact success/failure.
- Service tests for article document success and missing asset/cover failure.
- Hermes client wrapper tests with mocked `fetch` or service-level fake client.
- HTTP MCP smoke tool discovery.
- Docs update "agent-facing draft flow" to recommend facade after low-level tool details.

---

## Project Structure

```text
packages/wechat-draft/src/schemas/tool-schemas.ts
packages/wechat-draft/src/hermes/HermesDbClient.ts
packages/wechat-draft/src/service/WechatDraftService.ts
packages/wechat-draft/src/service/WechatDraftService.*.test.ts
packages/wechat-draft/src/mcp/createMcpServer.ts
docs/article-document-artifact-example.md
specs/wechat-draft-publish-ready-facade/
```

---

## Risks and Tradeoffs

- Facade increases side-effect surface. It must preserve idempotency and phase trace.
- Hermes client wrappers depend on the HTTP MCP response shape. Existing client already uses this shape for `get_workflow_artifact_content`.
- Article-document mode can create a publish-ready artifact before draft creation fails; phase trace must expose that artifact for retry.
- If Hermes upsert returns idempotency hit/conflict, facade should surface it rather than hiding it.

---

## Evolution Path

- **MVP**: One facade tool, existing artifact mode, article-document mode with Hermes upsert, no asset upload/compression.
- **成长期**: Optional asset upload orchestration once compression/asset prep is mature.
- **成熟期**: Draft ops CRUD and schedule/publish workflows with stronger confirmation controls.

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。No workflow engine; simple orchestration method.
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：No new dependency; side effects documented.
- 是否重复实现 render/preflight/draft logic：No, facade composes existing methods.
- 是否越界到 writing/note migration：No.

---

## Verification Strategy

- `pnpm --filter @mcps/wechat-draft build`
- `pnpm --filter @mcps/wechat-draft test`
- `git diff --check`
- Target tests:
  - existing artifact success validates then creates draft.
  - existing artifact validation failure skips draft.
  - article document success builds/upserts/validates/creates draft.
  - missing cover/body asset returns lower-level next_action and no Hermes write/draft.
  - Hermes artifact conflict/upsert error surfaces current phase and remediation.
  - duplicate idempotency key returns same draft job through existing job store behavior.
  - MCP `listTools` includes facade.

---

## Stage Readiness

- 是否需要 `data-model.md`: 不需要。No durable schema/storage changes; wrappers target existing Hermes tools.
- 下一步建议：`tasks`
- 阻塞项：无。

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| Hermes workflow run/artifact upsert tools | local code | `packages/hermes-db/src/hermes_db_mcp/tools/workflow_runs.py`, `workflow_artifacts.py` |
| Existing draft workflow | local code | `DraftWorkflow.ts`, `WechatDraftService.ts` |
| Article document builder | local code | `ArticleDocumentToWechatArtifactBuilder.ts` |
| Asset preflight | local code | `AssetSourceLoader.ts` |
