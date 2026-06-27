# Implementation Plan: WeChat Article Document Tools

**Workspace**: `wechat-article-document-tools` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/wechat-article-document-tools/spec.md`

---

## Summary

Expose the existing article-document render pipeline as thin MCP tools: import markdown, validate article documents, render previews, and build publish-ready `wechat_api_article` artifact payloads. The implementation should not duplicate conversion logic or add side effects; it only wraps existing modules with typed schemas, actionable errors, and contract tests.

There is one reasonable architecture direction: a thin service/tool façade over existing render modules. A separate workflow engine, storage layer, or E2E draft façade would duplicate later roadmap features and is intentionally skipped.

---

## Architecture Overview

```text
Agent
  -> MCP tools in createMcpServer.ts
    -> WechatDraftService article-document methods
      -> MarkdownArticleImporter
      -> ArticleDocumentValidator
      -> WechatArticleDocumentRenderer / MarkdownArticleExporter
      -> ArticleDocumentToWechatArtifactBuilder
  -> returns Result<T> payloads only

No WeChat API calls
No hermes-db writes
No asset download/upload/compression
No draft creation
```

The new tools sit beside existing `wechat_list_accounts`, `wechat_upload_asset`, `wechat_validate_publish_artifact`, and `wechat_create_draft`. They produce deterministic intermediate payloads that downstream Hermes and draft tools already understand.

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| `wechat_import_article_markdown` | `ArticleDocumentEnvelope` object / JSON string candidate | `wechat_validate_article_document`, `wechat_render_article_document`, `wechat_build_publish_ready_artifact`, hermes `upsert_workflow_artifact` | Contract test imports markdown and validates/render/builds the returned object. |
| `wechat_validate_article_document` | Validation result with normalized schema/version/errors | Agent and `wechat_build_publish_ready_artifact` preflight | Tests assert invalid image refs and unsupported nodes return actionable errors before build. |
| `wechat_render_article_document` | HTML preview + consumed body image refs + warnings/hash/size | Agent/operator preview; future publish-ready facade | Tests assert body image refs are consumed and missing `wechat_url` is reported. |
| `wechat_build_publish_ready_artifact` | Hermes upsert payload for `stage=publish_ready`, `type=wechat_api_article` | Hermes `upsert_workflow_artifact`; existing `wechat_create_draft` after upsert | Test builds payload then validates shape against existing publish artifact expectations. |

**孤儿 artifact 处理**: No orphan artifacts are introduced. Markdown preview is non-canonical and only a diagnostic/export output; the canonical handoff remains `article_document`.

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 一致性 | Tool output must match existing render/build modules | No second renderer or ad hoc HTML builder | Fixture tests call tool/service methods and assert renderer-derived output. |
| 可恢复性 | Input errors return next action | Wrap thrown renderer/importer/build errors into existing remediation envelope | Tests for missing image, invalid doc, missing cover, missing `wechat_url`. |
| 可演进性 | Future publish-ready facade composes these tools | Keep tools side-effect-free and typed | Plan/tasks forbid hermes upsert and draft creation. |
| 安全性 | No external writes or sensitive leakage | No network/storage calls; sanitize error details | Tests assert no stack trace in tool error messages. |

---

## Bugfix Strategy

| Field | Value |
|---|---|
| Observed Behavior | Agents hand-roll Tiptap JSON and WeChat HTML; `content_text` object/string mismatch and content_ref limitation cause repeated retries. |
| Expected Behavior | Agents call typed tools that return validated article documents, preview HTML, or publish-ready artifact payloads with clear recovery actions. |
| Reproduction Status | reproducible via prior draft flow notes and existing docs showing `article_document` must be JSON string when persisted. |
| Root Cause Hypothesis | Library-level conversion/rendering exists but is not exposed as MCP tools, so agents rebuild hidden logic outside the server. |
| Fix Boundary | Register side-effect-free tools and schemas; do not upload assets, write hermes-db, create drafts, or generate content. |
| Failed Attempt Handling | If a wrapper exposes module exceptions directly, add a mapped error case and regression test before closeout. |
| Regression Guard Strategy | Unit/contract tests for importer, validator, renderer, builder, MCP registration, and error envelope fields. |
| Diffusion Check Strategy | Search for new ad hoc HTML/Tiptap builders in MCP paths; ensure docs point to tools rather than manual Python/string construction. |
| Verification Path | Before evidence: no render tests and no MCP tools. After evidence: build/test pass plus tool registration smoke. |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001 thin façade over existing modules | Render/import modules already exist | A: expose modules via MCP; B: implement new end-to-end tool; C: duplicate conversion in agent | Choose A | More tools for agent to compose; avoids premature E2E coupling | local code |
| ADR-002 separate validate/render/build tools | Agent needs inspectable checkpoints | A: four explicit tools; B: one mega preview/build tool | Choose A for MVP | Slightly more calls; better diagnostics and future facade reuse | local code |
| ADR-003 side-effect-free outputs | Asset upload and draft creation are separate roadmap features | A: pure payload tools; B: auto upsert/create draft | Choose A | Agent must still call hermes upsert/create draft; avoids hidden writes | roadmap |
| ADR-004 accept object first, JSON string where useful | MCP callers should not stringify article docs manually | A: accept object; B: only JSON string; C: both | Prefer object input for tools; support source artifact `content_text` string in build for compatibility | Schemas are slightly broader | local code |

---

## Key Design Decisions

### Decision 1: Tool Set

- **结论**: Add four MCP tools:
  - `wechat_import_article_markdown`
  - `wechat_validate_article_document`
  - `wechat_render_article_document`
  - `wechat_build_publish_ready_artifact`
- **理由**: These align to existing module boundaries and give agents debuggable checkpoints.
- **影响**: A later `wechat-draft-publish-ready-facade` can call the same service methods internally instead of reimplementing conversion.

### Decision 2: Result Shape

- **结论**: Return existing `Result<T>` through `toMcpToolResult`; failures use `createErrorResult` with remediation fields.
- **理由**: Contract hardening already established the envelope; adding a second shape would fragment agent behavior.
- **影响**: Tool outputs remain compatible with existing logging and MCP transport helpers.

### Decision 3: No Persistent Data Model

- **结论**: Do not create `data-model.md`.
- **理由**: No database/storage schema changes. Existing `ArticleDocumentEnvelope` and `WorkflowArtifact` shapes are reused.
- **影响**: Data shape details live in schemas and tests, not a new persistence model.

---

## Module Design

### Module: Tool Schemas

**职责**: Define typed input/output contracts for new MCP tools.

**改动概述**:

- Add schemas in `packages/wechat-draft/src/schemas/tool-schemas.ts` or a sibling article-document schema module exported via `schemas/index.ts`.
- Use zod object schemas for document/asset metadata where practical; allow unknown `doc` JSON but validate with `ArticleDocumentValidator`.
- Include output metadata: `schema_version`, `html`, `content_hash`, `content_size_bytes`, `warnings`, `consumed_body_images`, and `upsert_payload`.

**YAGNI stop**: Layer 4, reuse existing zod dependency and render types. No generated OpenAPI/JSON Schema layer.

### Module: Service Methods

**职责**: Wrap render modules and convert exceptions into `Result<T>`.

**改动概述**:

- Add methods on `WechatDraftService`:
  - `importArticleMarkdown(input)`
  - `validateArticleDocument(input)`
  - `renderArticleDocument(input)`
  - `buildPublishReadyArtifact(input)`
- Use existing `MarkdownArticleImporter`, `ArticleDocumentValidator`, `WechatArticleDocumentRenderer`, `MarkdownArticleExporter`, and `ArticleDocumentToWechatArtifactBuilder`.
- Add small local error mapper for known article document failures:
  - missing prepared image -> `next_action=prepare_body_image_assets`
  - invalid document -> `next_action=fix_article_document`
  - missing cover thumb -> `next_action=upload_cover_image`
  - missing body image URL -> `next_action=upload_body_images`

**YAGNI stop**: Layer 5/6, minimal wrapper methods. No new workflow/state machine.

### Module: MCP Registration

**职责**: Register tools and route through logging/result helpers.

**改动概述**:

- Add four `server.registerTool` calls in `createMcpServer.ts`.
- Descriptions must say side-effect-free and no WeChat/hermes writes.
- Use existing `runLoggedTool` and `toMcpToolResult`.

**YAGNI stop**: Layer 3/4, reuse MCP SDK registration already used by server.

### Module: Tests

**职责**: Prove module reuse, tool contracts, and error recovery.

**改动概述**:

- Add render/service tests under `packages/wechat-draft/src/render` or `src/service`.
- Add MCP smoke/registration assertions through existing HTTP/MCP smoke pattern if low-cost.
- Add docs/static fixture examples for canonical payloads.

**YAGNI stop**: Layer 4, use Node test runner already configured. No new test framework.

### Module: Documentation

**职责**: Replace manual construction guidance with tool-first flow.

**改动概述**:

- Update `docs/article-document-artifact-example.md` with:
  - import markdown -> validate -> render -> build -> hermes upsert -> create draft flow.
  - object vs persisted `content_text` JSON string boundary.
  - clear note that these tools do not upload images or create drafts.

**YAGNI stop**: Layer 5, edit existing docs. No new docs site.

---

## Project Structure

```text
packages/wechat-draft/src/schemas/tool-schemas.ts
packages/wechat-draft/src/service/WechatDraftService.ts
packages/wechat-draft/src/mcp/createMcpServer.ts
packages/wechat-draft/src/render/*.ts
packages/wechat-draft/src/render/*.test.ts        # new or expanded
packages/wechat-draft/src/service/*.test.ts       # new or expanded
docs/article-document-artifact-example.md
specs/wechat-article-document-tools/
```

---

## Risks and Tradeoffs

- Existing `MarkdownArticleImporter` is intentionally simple. This feature should document limitations rather than expand it into a full Markdown parser unless tests prove a narrow gap blocks the use case.
- Tool outputs may be large because HTML can be full article content. Plan should keep outputs useful but may include `preview_text`, `content_hash`, and `content_size_bytes` for quick inspection.
- `ArticleDocumentToWechatArtifactBuilder` currently expects cover `thumb_media_id`. This stays aligned with existing draft boundary; cover-channel experimentation remains deferred.
- Accepting both object and string inputs improves ergonomics but can make schemas broader. Service validation must normalize early and return clear errors.

---

## Evolution Path

- **MVP**: Four side-effect-free tools over existing modules, with focused tests and docs.
- **成长期**: `wechat-draft-asset-preflight` supplies prepared assets; tools can accept its output directly.
- **成熟期**: `wechat-draft-publish-ready-facade` composes import/render/build/preflight and optional hermes upsert/draft creation behind one higher-level workflow.

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。没有新 workflow engine、storage, queue, or facade.
- 是否引用了外部模式但没有适配检查：否。方案基于本地模块边界。
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。新增的是 pure tools and typed errors.
- 是否重复实现 note-skill-migration 功能：否。没有写作生成、技能迁移、Library/Memory ingestion。

---

## Verification Strategy

- `pnpm --filter @mcps/wechat-draft build`
- `pnpm --filter @mcps/wechat-draft test`
- Targeted tests:
  - import markdown with prepared images returns valid `article_document`.
  - import markdown missing image asset returns remediation.
  - validate catches invalid doc/image ref.
  - render returns HTML, consumed images, hash/size, warnings.
  - render/build missing body `wechat_url` or cover `thumb_media_id` returns remediation.
  - build returns hermes upsert-ready `wechat_api_article` payload.
  - MCP registration exposes all four tools and marks side-effect-free behavior in descriptions/annotations where supported.
- Static diffusion:
  - `rg` for manual Tiptap/HTML construction docs in WeChat draft paths.
  - `rg` for raw renderer errors leaking through MCP service methods.

---

## Stage Readiness

- 是否需要 `data-model.md`: 不需要。无 durable schema/storage change；复用现有 TypeScript interfaces and artifact payload shapes.
- 下一步建议：`tasks`
- 阻塞项：无。工具拆分和 input normalization 决策已在 ADR 中固定，足以拆任务。

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | 必须 | 当前文件 |
| data-model.md | 不需要 | 无存储/关系/状态变化 |
| tasks.md | 后续阶段生成 | 拆成 import、validate/render、build、MCP registration、docs/tests slices |
| acceptance.md | 后续阶段生成 | 因 traits 命中，需要最终验收 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| Existing importer/renderer/builder modules | local code | `packages/wechat-draft/src/render/*` |
| Existing MCP registration/result helper pattern | local code | `packages/wechat-draft/src/mcp/createMcpServer.ts`, `toolResult.ts` |
| Roadmap boundary | local roadmap | `specs/wechat-draft-agent-experience-roadmap/roadmap.md` |
