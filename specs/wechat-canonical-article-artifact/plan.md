# Implementation Plan: WeChat Canonical Article Artifact

**Workspace**: `wechat-canonical-article-artifact` | **Date**: 2026-06-24 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/wechat-canonical-article-artifact/spec.md`

---

## Summary

Introduce `article_document` as the canonical source artifact for new WeChat article workflows, using Tiptap/ProseMirror JSON as the mature document model. The publishing path becomes `article_document -> WeChat renderer / asset-prep -> wechat_api_article -> wechat-draft MCP`, with `wechat-draft` continuing to consume only publish-ready artifacts.

Markdown remains an import/export compatibility format, not a required internal source format.

---

## Architecture Overview

```text
Content agent / import flow
  - produces Tiptap/ProseMirror JSON
  - optionally imports legacy Markdown into JSON
        |
        v
hermes.workflow_artifacts
  - type=article_document
  - content_text=<JSON string>
  - metadata.style_profile_id / schema_version / source refs
        |
        v
Article document renderer
  - validates allowed Tiptap nodes/marks
  - converts JSON to WeChat-safe HTML
  - applies account style profile
        |
        v
Asset-prep flow
  - uploads body images and cover assets
  - writes mmbiz.qpic.cn URLs + thumb_media_id
        |
        v
hermes.workflow_artifacts
  - stage=publish_ready
  - type=wechat_api_article
  - content_text=<WeChat-safe HTML>
  - metadata.wechat_asset_manifest.ready=true
        |
        v
packages/wechat-draft
  - validates ready artifact
  - creates WeChat draft
  - writes ledger/job summary
```

The draft MCP boundary stays intentionally narrow: it must not parse Markdown, render rich text, upload images, or repair style. It only validates `wechat_api_article` and calls the existing adapter.

---

## Architecture Reference

| 参考模式 / 模板 | 来源 URL | 适配点 | 不适配点 | 当前阶段 |
|---|---|---|---|---|
| Pipeline / Pipes-and-Filters | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | 文章生产、渲染、资产准备、草稿创建天然是阶段产物交接 | 不引入消息队列或异步调度框架，MVP 仍以显式 workflow 调用为主 | MVP |
| Tiptap/ProseMirror document model | https://github.com/ueberdosis/tiptap-docs/blob/main/src/content/editor/api/utilities/static-renderer.mdx | 成熟 JSON 文档模型，支持静态/服务端 HTML 输出 | 默认 HTML 不等于微信安全 HTML，需要项目内 adapter | MVP |
| Existing WeChat-ready artifact contract | packages/wechat-draft/docs/wechat-ready-artifact-example.md | 已规定 `wechat-draft` 只消费 `wechat_api_article` ready artifact | 不覆盖上游 canonical document schema | MVP |

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| Content agent / Markdown importer | `workflow_artifacts(type=article_document)` | Article document renderer / Agent reader / preview/export tool | Renderer accepts artifact id and validates JSON schema; Agent can fetch by artifact id |
| Article document renderer | Intermediate WeChat-safe HTML draft | Asset-prep flow | HTML contains only allowed nodes and image placeholders/asset refs |
| Asset-prep flow | `workflow_artifacts(type=wechat_api_article, stage=publish_ready)` | `wechat-draft` MCP | `wechat_validate_publish_artifact` passes |
| `wechat-draft` MCP | WeChat draft `media_id` + local job summary | `hermes.wechat_articles` ledger / operator | Job status contains media id; ledger status becomes `drafted` |
| Markdown exporter | Markdown export | Human backup / notes workflow | Export command or Agent response returns Markdown marked as non-canonical |

**孤儿 artifact 处理**: `article_document` has three consumers: renderer, Agent reader, and export/preview. `source_markdown` is explicitly legacy provenance and may be orphaned after migration; it is retained only for traceability, not required for publishing.

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|---|---|---|---|
| 微信适配性 | publish-ready HTML 能被微信草稿稳定展示 | WeChat renderer must own final HTML generation/styling; unsupported nodes are rejected before publish-ready | live draft smoke + `draft/batchget` HTML inspection |
| 可演进性 | Tiptap extension set 可扩展但首期受控 | Maintain allowlist and schema version; reject unknown nodes/marks | fixture tests for allowed/unknown nodes |
| 可追溯性 | source -> article_document -> wechat_api_article -> media_id 可追溯 | Use artifact parent ids and metadata source refs | repository/tool tests + ledger smoke |
| 职责边界 | draft MCP 不处理 Markdown/render/upload | Keep existing `ArtifactValidator` / `DraftPayloadBuilder` boundary | contract tests ensure raw Markdown/article_document is rejected by draft create |
| 可诊断性 | 每个阶段失败可定位 | Structured validation and adapter errors | failure fixtures for unsupported node, missing asset, invalid image URL |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|---|---|---|---|---|---|
| ADR-001 canonical document model | 手写 Markdown/正则 renderer 已暴露格式残留风险 | A: Tiptap/ProseMirror JSON / B: 自定义 block schema / C: 继续 Markdown source | 选择 A，使用成熟文档模型和 extension 生态 | 新增依赖和 schema allowlist；需适配微信 HTML | Tiptap static renderer docs; ProseMirror ref |
| ADR-002 final WeChat HTML generation | Tiptap 可生成通用 HTML，但微信编辑器对样式/图片有约束 | A: 直接用 Tiptap HTML / B: Tiptap HTML 后处理 / C: 遍历 JSON 直接生成 WeChat HTML | MVP 推荐 C，必要时用 Tiptap utilities 做辅助验证/preview | 需要维护 WeChat renderer，但避免通用 HTML 与微信 HTML 偏差 | Existing draft contract + live smoke evidence |
| ADR-003 storage | hermes-db 已有 workflow_artifacts content_text/content_ref | A: 复用 content_text JSON / B: 新增 typed article table / C: 外部对象存储 | MVP 选择 A，不扩表；metadata 标记 schema/version/type | 查询 JSON 内部字段不方便，后续可升级 typed index | hermes-db artifact persistence spec |
| ADR-004 Markdown role | 旧稿和人工阅读依赖 Markdown，但新链路进数据库 | A: Markdown canonical / B: Markdown import/export only | 选择 B，Markdown 只做 legacy import/export/debug | Markdown 导出可能丢失部分样式细节 | User clarification |

---

## Key Design Decisions

### Decision 1: Use Tiptap/ProseMirror JSON as Canonical Article Content

- **背景**: 用户明确要求优先使用成熟工具库；自定义 block schema 会变成自造富文本模型。
- **选项**:
  - A: Tiptap/ProseMirror JSON — 成熟、可扩展、可与未来编辑器 UI 衔接。
  - B: 项目内最小 block schema — 简单但长期维护成本会增长。
  - C: Markdown — 人类可读但不适合作为发布链路 source of truth。
- **结论**: 选择 A。`article_document.content_text` 保存 JSON 字符串，metadata 标记 `schema_version="article_document.tiptap.v1"`。
- **影响**: 需要新增 Tiptap/ProseMirror 依赖和 extension allowlist。
- **来源**: Context7/Tiptap docs show JSON-to-HTML static renderer APIs such as `renderToHTMLString`; ProseMirror docs support JSON serialization and DOM serialization.

### Decision 2: WeChat Renderer Consumes JSON and Produces WeChat-Safe HTML

- **背景**: 微信草稿展示质量是最高优先级；通用 HTML 不能假设直接适配微信编辑器。
- **选项**:
  - A: Tiptap `renderToHTMLString` output goes directly into `wechat_api_article`.
  - B: Tiptap HTML output followed by sanitizer/style post-process.
  - C: Project renderer traverses Tiptap JSON and emits WeChat-safe HTML directly.
- **结论**: MVP 选择 C。Tiptap renderer 可用于 preview/export 或测试对照，但 publish-ready HTML 由项目内 WeChat renderer 输出。
- **影响**: WeChat renderer must support only allowlisted nodes/marks and fail closed on unknown content.
- **来源**: `packages/wechat-draft/docs/wechat-ready-artifact-example.md`; current `DraftPayloadBuilder` validates final HTML/image URLs only.

### Decision 3: Reuse `workflow_artifacts` Without Schema Migration

- **背景**: hermes-db 已有 `workflow_artifacts`，支持 `type`、`stage`、`content_text`、`content_ref`、`metadata`、version 和 parent relation。
- **选项**:
  - A: Store JSON in `content_text`.
  - B: Add typed article document tables.
  - C: Store in external object storage.
- **结论**: MVP 选择 A。No new hermes-db migration required unless implementation discovers size/metadata limitations.
- **影响**: `list_workflow_artifacts` still returns summaries only; full JSON read uses `get_workflow_artifact_content`.
- **来源**: `specs/hermes-db-wechat-artifact-persistence/spec.md`.

---

## Module Design

### Module: Article Document Contract

**职责**: Define and validate canonical artifact shape.

**改动概述**:

- Add TypeScript types for `ArticleDocumentArtifact`, `TiptapArticleDocument`, and metadata.
- Store content as Tiptap/ProseMirror JSON in `workflow_artifacts.content_text`.
- Use metadata:
  - `format="article_document"`
  - `schema_version="article_document.tiptap.v1"`
  - `style_profile_id`
  - `style_version?`
  - `source_markdown_artifact_id?`
  - `allowed_extensions`

**YAGNI stop**: Layer 4, mature dependency. Standard library/platform cannot supply rich-text schema; existing dependencies do not include one.

### Module: Tiptap Extension Allowlist

**职责**: Restrict canonical documents to nodes/marks that can be rendered to WeChat.

**MVP allowlist**:

```text
nodes: doc, paragraph, text, heading(level 2-4), image, horizontalRule, bulletList?, orderedList?, listItem?, blockquote?
marks: bold/strong, link
excluded initially: tables, embeds, codeBlock, taskList, mentions, collaboration nodes
```

**注意事项**:

- Unknown nodes/marks fail validation before renderer.
- Lists/blockquote may be included only if renderer tests prove acceptable WeChat output. Otherwise they remain import-only warnings.

### Module: Article Document Renderer

**职责**: Convert Tiptap JSON into WeChat-safe HTML with account style profile.

**关键行为**:

```text
renderArticleDocumentToWechatHtml(document, styleProfile, assetMap)
  validate schema_version and allowlist
  render paragraph / heading / strong / link / divider / image
  reject unresolved image asset_ref
  output HTML with inline styles and WeChat image URLs
```

**注意事项**:

- Final HTML must not contain Markdown syntax.
- Images must use prepared WeChat URLs before `wechat_api_article` is marked publish-ready.
- Style profile remains account-specific, e.g. `yueliang.default`.

### Module: Asset Prep Integration

**职责**: Convert image asset refs into WeChat assets.

**改动概述**:

- Input: `article_document` with image nodes referencing source assets.
- Output: `wechat_api_article` with `content_text` final HTML and `wechat_asset_manifest`.
- Use existing adapter upload capabilities; do not move upload into `wechat_create_draft`.

### Module: Markdown Import / Export Compatibility

**职责**: Keep legacy `.md` useful without making it canonical.

**改动概述**:

- Import Markdown to Tiptap JSON using mature parser where possible.
- Export Tiptap JSON to Markdown for human backup/debug.
- Mark exported Markdown as lossy if style/profile-specific details cannot be represented.

### Module: Draft MCP Boundary Guard

**职责**: Ensure `wechat-draft` only accepts `wechat_api_article`.

**改动概述**:

- Existing `ArtifactValidator` should continue to reject `type !== "wechat_api_article"`.
- Add fixture proving `article_document` cannot be sent directly to `wechat_create_draft`.
- Keep `DraftPayloadBuilder` unchanged unless contract needs metadata additions.

---

## Data Model

Detailed data model is in [data-model.md](data-model.md).

MVP stores both canonical and publish-ready artifacts in existing `workflow_artifacts`:

```text
article_document:
  stage=draft | transformed-draft | article_document
  type=article_document
  content_text=<Tiptap/ProseMirror JSON string>

wechat_api_article:
  stage=publish_ready
  type=wechat_api_article
  content_text=<WeChat-safe HTML>
```

---

## Project Structure

```text
packages/wechat-draft/src/render/
  ArticleDocumentTypes.ts
  ArticleDocumentValidator.ts
  TiptapExtensionAllowlist.ts
  WechatArticleDocumentRenderer.ts
  MarkdownArticleImporter.ts
  MarkdownArticleExporter.ts

packages/wechat-draft/test-article-document-renderer.mjs
packages/wechat-draft/docs/article-document-artifact-example.md
specs/wechat-canonical-article-artifact/
  spec.md
  plan.md
  data-model.md
  tasks.md
```

Implementation may move shared content-production modules to a different package if `content-orchestrator-agent` owns article generation; tasks stage should confirm ownership.

---

## Risks and Tradeoffs

- Tiptap JSON is mature but more verbose than a custom schema.
- Direct JSON-to-WeChat rendering avoids generic HTML drift but requires maintaining a small renderer.
- Markdown import/export may be lossy for style-specific constructs.
- Adding Tiptap dependencies to `wechat-draft` may be the wrong package boundary if upstream content generation lives elsewhere; tasks should isolate dependency placement.
- WeChat HTML behavior can only be fully verified with live draft/batchget smoke tests.

---

## Evolution Path

- **MVP**: Tiptap/ProseMirror JSON artifact, small allowlist, project WeChat renderer, existing `workflow_artifacts` storage.
- **成长期**: Add preview/export endpoint or UI, expand allowlist based on real article needs, add richer validation diagnostics.
- **成熟期**: If UI editing becomes central, introduce a real Tiptap editor surface and optional indexed typed article metadata.

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。只采用 mature document model，不引入 collaboration/editor UI/cloud services。
- 是否引用外部模式但没有适配检查：否。Tiptap/ProseMirror output is explicitly constrained by WeChat adapter tests.
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：新增 dependency and failure modes are recorded in ADR/module design.

---

## Verification Strategy

- Unit tests:
  - valid Tiptap JSON -> WeChat-safe HTML
  - unknown node/mark rejection
  - missing image asset rejection
  - Markdown import/export smoke fixtures
  - `wechat_create_draft` rejects `article_document`
- Contract tests:
  - `wechat_api_article` generated from `article_document` passes `ArtifactValidator`
  - non-WeChat image URL is rejected
  - missing cover `thumb_media_id` is rejected
- Live smoke:
  - use a small `article_document` fixture for `yueliang.default`
  - generate `wechat_api_article`
  - create WeChat draft
  - fetch via `draft/batchget`
  - assert no Markdown residue and image refs are `mmbiz.qpic.cn`

---

## Stage Readiness

- 是否需要 `data-model.md`：需要。This feature defines a new canonical artifact type and handoff metadata while reusing existing storage.
- 下一步建议：`tasks`
- 阻塞项：无。Remaining choices, such as exact package ownership and allowlist details, can be decomposed into tasks with validation checkpoints.

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|---|---|---|
| plan.md | 必须 | 本文件 |
| data-model.md | 需要 | 定义 `article_document` artifact shape and metadata |
| tasks.md | 后续阶段生成 | 由 `tasks` 阶段产出 |
| acceptance.md | 后续阶段生成 | 验证完成后记录 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|---|---|---|
| Tiptap static renderer / JSON to HTML | https://github.com/ueberdosis/tiptap-docs/blob/main/src/content/editor/api/utilities/static-renderer.mdx | Context7 retrieved current docs showing `renderToHTMLString` |
| Tiptap server-side HTML utility | https://github.com/ueberdosis/tiptap-docs/blob/main/src/content/guides/output-json-html.mdx | Context7 retrieved docs mention `generateHTML` without editor instance |
| ProseMirror JSON / DOM serialization | https://prosemirror.net/docs/ref | Context7 retrieved docs for `toJSON`, `serializeFragment`, `serializeNode` |
| Existing ready artifact contract | packages/wechat-draft/docs/wechat-ready-artifact-example.md | Local contract |
| Existing draft validator | packages/wechat-draft/src/hermes/ArtifactValidator.ts | Local implementation |
