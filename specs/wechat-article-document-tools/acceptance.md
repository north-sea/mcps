# Acceptance Record: WeChat Article Document Tools

**Workspace**: `wechat-article-document-tools` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| FR-001 markdown import tool | `wechat_import_article_markdown` is registered and `WechatDraftService.importArticleMarkdown` wraps `MarkdownArticleImporter`. | `createMcpServer.ts`; `WechatDraftService.articleDocument.test.ts` | PASS |
| FR-002 article_document validate tool | `wechat_validate_article_document` accepts object/JSON string, validates with `ArticleDocumentValidator`, and returns structured errors. | `WechatDraftService.validateArticleDocument accepts objects and rejects invalid JSON` | PASS |
| FR-003 render/preview tool | `wechat_render_article_document` renders HTML/Markdown previews via existing renderer/exporter and returns hash, size, preview text, consumed images, warnings. | `WechatDraftService.renderArticleDocument returns HTML and consumed image refs` | PASS |
| FR-004 publish-ready artifact builder | `wechat_build_publish_ready_artifact` returns a hermes upsert payload for `publish_ready` `wechat_api_article` with inline HTML and metadata. | `WechatDraftService.buildPublishReadyArtifact returns hermes upsert payload` | PASS |
| FR-005 remediation envelope | Known import/render/build failures map to `next_action`, `remediation_hint`, `retryable=false`, and `current_phase`. | missing image, invalid JSON, missing body URL, missing cover tests | PASS |
| FR-006 docs show real payload flow | Docs now recommend typed tools and clarify object vs persisted `content_text` JSON string boundary. | `docs/article-document-artifact-example.md` | PASS |
| FR-007 tests cover contract | Build passes and 51 tests pass, including 7 article-document service tests and MCP tool discovery. | `verify-evidence.md` | PASS |

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Schemas, service methods, MCP registration, docs, and tests are implemented. |
| Workflow closure | PASS | Agent can import, validate, render, and build publish-ready artifact payloads without hand-writing Tiptap JSON or HTML. |
| User-visible outcome | PASS | Tools are discoverable through MCP and return preview/build payloads plus actionable errors. |

**Overall**: PASS

## Workflow Replay

- **输入摘要**: Markdown or article_document object with prepared image metadata.
- **最终 payload 摘要**: Validated `article_document`, rendered preview HTML, and hermes upsert payload for `stage=publish_ready`, `type=wechat_api_article`.
- **用户可见结果断言**: Agent no longer needs to hand-roll Tiptap nodes or rendered HTML before hermes upsert.
- **Replay 类型**: fixture. No WeChat or hermes writes are part of this feature.

## Bugfix Closure

| Field | Value |
|---|---|
| Root Cause / Hypothesis | Conversion/render modules existed only as library code, so agents rebuilt article document and HTML logic externally. |
| Fix Mechanism | Exposed side-effect-free MCP tools over existing importer, validator, renderer/exporter, and publish-ready builder. |
| Prevention Mechanism | Added service tests and MCP tool discovery smoke; docs now point to tool-first flow. |
| Failed Attempts Summary | Rejected mega E2E draft tool and duplicate converter implementation; both would overlap later roadmap features. |
| Regression Guard | `pnpm --filter @mcps/wechat-draft build`; `pnpm --filter @mcps/wechat-draft test`; diffusion `rg` recorded in `verify-evidence.md`. |
| Diffusion Check | New errors route through remediation fields; docs no longer instruct MCP users to hand-roll render/build flow. |
| Remaining Risk | Markdown importer remains intentionally small; full Markdown support and automatic asset preparation remain future work. |

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | 已完成 | Manual tool-less article document flow is replaced in docs by typed MCP tools. Existing library modules retained as implementation. | 无 |
| 发布、提交、CI 或 follow-through | 延后 | 未提交、未发布；用户尚未要求 commit。 | 需要提交时先做 commit plan。 |
| 文档、阶段说明、模板或验收记录更新 | 已完成 | `docs/article-document-artifact-example.md`, `verify-evidence.md`, `acceptance.md`, roadmap. | 无 |
| ADR、架构债或演进触发信号 | 已完成 | Asset preparation, publish-ready facade, and broader Markdown parsing remain deferred. | 进入 `wechat-draft-asset-preflight`。 |
| Knowledge Capture | 已完成 | 见下表；仅记录到本地 acceptance。 | 无 |

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| pattern | Article document tools are side-effect-free | Import/validate/render/build tools return payloads only; hermes upsert and draft creation stay explicit downstream calls. | `createMcpServer.ts`; `acceptance.md` | WeChat draft MCP | recorded-only | Publish-ready facade can compose them later |
| convention | Article document object vs persisted string | Tools can accept article document objects, but hermes `content_text` stores JSON string. | `docs/article-document-artifact-example.md` | Article artifact handoff | recorded-only | Keep examples aligned |
| follow-up | Asset preflight is next | Missing `wechat_url` or `thumb_media_id` now returns remediation, but the MCP still lacks probing/compression/preflight helpers. | tests; roadmap | WeChat asset handling | recorded-only | `wechat-draft-asset-preflight` |

## Commit Result

| Field | Value |
|---|---|
| Status | not_submitted |
| Commit Hashes | 无 |
| Commit Messages | 无 |
| Included Files | 无 |
| Excluded / Remaining Files | 工作区仍有本 roadmap 多个 feature 的代码、测试、文档和 untracked specs。 |
| Reason | SDD closeout 不自动提交；提交需要用户明确确认。 |

## Completion Record

- **最终结论**: PASS
- **完成依据**: FR-001 到 FR-007 均有文件和测试证据；三维 Verdict 全 PASS。
- **阻塞项**: 无。
- **延后项**: asset preflight/compression、publish-ready facade、full Markdown parsing、draft CRUD。
- **退役结论**: tool-less manual article document flow 已在文档层退役；底层 render modules 保留并复用。
- **提交结论**: not_submitted。
- **后续动作**: 回到 roadmap，启动 `wechat-draft-asset-preflight` 的 specify 阶段。
