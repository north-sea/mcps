# Tasks: WeChat Article Document Tools

**Workspace**: `wechat-article-document-tools` | **Date**: 2026-06-27
**Input**: `specs/wechat-article-document-tools/spec.md` + `plan.md`
**Prerequisites**: spec.md, plan.md

---

## 执行原则

- 主要任务按端到端 tool slice 拆分：import、validate/render、build、MCP registration。
- 所有工具必须复用现有 render modules，不新增第二套 markdown/Tiptap/HTML 转换器。
- 所有工具必须 side-effect-free：不上传图片、不写 hermes-db、不创建草稿。
- 错误必须沿用现有 remediation envelope，不直接泄露 renderer stack 或 raw exception。
- 不实现写作生成、note skill migration、asset preflight/compression、publish-ready facade 或 draft CRUD。

---

## Phase 1: Baseline And Shared Tool Contract

**目标**: 先固定当前缺口和公共 schema/error 形态，避免每个 tool 各写一套契约。

- [x] T001 [Bugfix] 记录 before evidence 和 failed-attempt ledger
  - scope: `specs/wechat-article-document-tools/verify-evidence.md`
  - slice: 证明当前 MCP 没有 article document import/render/build tools，render 目录没有 tool-level tests，agent 只能手搓转换。
  - blocked_by: none
  - maps_to: Bugfix Context / prior-closure-failure / FR-007
  - verify: evidence 记录 `rg`/tool list/static findings；失败尝试 ledger 初始化。

- [x] T002 [Foundation] 定义 article document tool schemas 和 normalized service input
  - scope: `packages/wechat-draft/src/schemas/tool-schemas.ts` 或新 schema module, `schemas/index.ts`
  - slice: 四个 tools 有 typed input/output；object vs JSON string 在 schema/service 边界被 normalize，不要求 agent 手动绕隐式约定。
  - blocked_by: T001
  - maps_to: FR-001..FR-005 / ADR-004 / 一致性
  - verify: schema/unit tests cover object input, JSON string input where supported, and invalid payload rejection.

- [x] T003 [Foundation] 建立 article document error mapper
  - scope: `packages/wechat-draft/src/service` adjacent helper/tests
  - slice: importer/validator/renderer/builder 抛出的已知输入错误被映射为 `next_action`、`remediation_hint`、`retryable=false`、`current_phase`。
  - blocked_by: T002
  - maps_to: FR-005 / NFR-003 / 可恢复性
  - verify: tests cover missing prepared image, invalid doc, missing body `wechat_url`, missing cover `thumb_media_id`, and no stack trace leakage.

---

## Phase 2: Markdown Import Slice

**目标**: agent 可以把 markdown + prepared assets 转成 canonical article_document。

- [x] T004 [US1] 实现 service-level markdown import
  - scope: `WechatDraftService`, `MarkdownArticleImporter`, tests
  - slice: markdown with title/metadata/body_images -> valid `ArticleDocumentEnvelope` + optional JSON string/content metadata; missing prepared image returns remediation.
  - blocked_by: T002, T003
  - maps_to: US1 / FR-001 / ADR-001
  - verify: service tests import simple markdown with one image and validate output schema/version/assets; missing image test returns `prepare_body_image_assets`.

- [x] T005 [US1] 注册 `wechat_import_article_markdown` MCP tool
  - scope: `createMcpServer.ts`, schemas, MCP smoke/registration tests
  - slice: listed/callable MCP tool returns same import result through `toMcpToolResult` and is described as side-effect-free.
  - blocked_by: T004
  - maps_to: US4 / FR-001 / FR-005
  - verify: MCP test asserts tool registration/call success and error wrapping.

---

## Phase 3: Validate And Render Slice

**目标**: agent 可以在 build 前自检 article_document，并得到可校对 preview。

- [x] T006 [US2] 实现 validate article document service/tool
  - scope: `ArticleDocumentValidator`, `WechatDraftService`, `createMcpServer.ts`, tests
  - slice: object or JSON string -> `valid/errors/schema_version`; bad doc/image ref returns structured validation result and/or remediation.
  - blocked_by: T002, T003
  - maps_to: US2 / FR-002 / FR-005
  - verify: tests cover valid doc, missing title, invalid ProseMirror doc, missing image asset_ref.

- [x] T007 [US2] 实现 render/preview article document service/tool
  - scope: `WechatArticleDocumentRenderer`, `MarkdownArticleExporter`, `WechatDraftService`, `createMcpServer.ts`, tests
  - slice: valid doc + ready body image urls -> HTML preview, consumed image refs, warnings/hash/size; missing `wechat_url` returns `upload_body_images`.
  - blocked_by: T006
  - maps_to: US2 / FR-003 / ADR-002
  - verify: tests cover rendered HTML contains expected text/image URL, consumed_body_images, warnings, missing url remediation.

---

## Phase 4: Publish-Ready Artifact Builder Slice

**目标**: agent 可以从 article_document 得到可 upsert 的 `wechat_api_article` artifact payload。

- [x] T008 [US3] 实现 build publish-ready artifact service/tool
  - scope: `ArticleDocumentToWechatArtifactBuilder`, `WechatDraftService`, `createMcpServer.ts`, tests
  - slice: document + artifact metadata -> hermes upsert-ready payload with `stage=publish_ready`, `type=wechat_api_article`, HTML `content_text`, hash/size, cover metadata, asset manifest.
  - blocked_by: T007
  - maps_to: US3 / FR-004 / ADR-003
  - verify: tests assert payload fields can be passed to hermes upsert shape and then existing publish artifact validator accepts the resulting artifact shape if applicable.

- [x] T009 [US3] Map build precondition failures to recovery actions
  - scope: builder wrapper/error mapper/tests
  - slice: missing cover thumb or missing body image URL returns actionable errors, not raw builder/renderer exceptions.
  - blocked_by: T008
  - maps_to: US3 / FR-005 / 可恢复性
  - verify: tests assert `next_action=upload_cover_image` and `next_action=upload_body_images` paths.

---

## Phase 5: Docs, Diffusion, And Verification

**目标**: 文档和相邻路径改成 tool-first，形成 fresh evidence。

- [x] T010 [Docs] 更新 article document happy path 文档
  - scope: `docs/article-document-artifact-example.md`, package README if relevant
  - slice: docs show import -> validate -> render -> build -> hermes upsert -> create draft, with side-effect boundaries and object/string persistence notes.
  - blocked_by: T005, T007, T008
  - maps_to: US4 / FR-006
  - verify: static review confirms docs no longer recommend hand-rolled Tiptap/HTML for MCP users.

- [x] T011 [Bugfix] 执行 diffusion check
  - scope: WeChat draft MCP docs/source/tests, `verify-evidence.md`
  - slice: no new ad hoc converter/renderer appears in MCP path; raw renderer exceptions are either mapped or intentionally internal.
  - blocked_by: T010
  - maps_to: Bugfix Loop Breaker / NFR-003
  - verify: `rg` findings recorded; deferred findings have owner/roadmap feature.

- [x] T012 [Verify] 运行 build/test 和 targeted contract checks
  - scope: `packages/wechat-draft`, `verify-evidence.md`
  - slice: all new tools and existing draft contract remain green.
  - blocked_by: T011
  - maps_to: FR-007 / Verification Strategy
  - verify: record `pnpm --filter @mcps/wechat-draft build`, `pnpm --filter @mcps/wechat-draft test`, and any targeted MCP smoke commands.

- [x] T013 [Closeout Prep] 准备 acceptance 输入和 roadmap impact
  - scope: `acceptance.md` inputs, roadmap status
  - slice: closeout can judge component capability, workflow closure, user-visible preview/output, bugfix closure, and next roadmap feature.
  - blocked_by: T012
  - maps_to: Acceptance Gate / Knowledge Capture
  - verify: `verify-evidence.md` contains evidence table inputs, failed-attempt ledger, diffusion check, remaining risks, and deferred items.

---

## 依赖与顺序

- 关键路径：T001 -> T002/T003 -> T004 -> T005 -> T006 -> T007 -> T008/T009 -> T010 -> T011 -> T012 -> T013。
- T006 可在 T004 后并行推进，但 T007 依赖 validate/normalization 稳定。
- T008 依赖 renderer output；T009 依赖 build wrapper。
- T010 必须等工具命名和输出稳定后再写，避免文档漂移。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|-------------|----------|
| US1 markdown import | T002, T003, T004, T005 |
| US2 validate/render preview | T002, T003, T006, T007 |
| US3 publish-ready artifact build | T008, T009 |
| US4 agent-friendly contracts/docs | T005, T006, T007, T008, T010 |
| Bugfix loop breaker | T001, T003, T011, T012, T013 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|----------------------|----------|----------|
| ADR-001 thin façade | T004-T008 | T011, T012 |
| ADR-002 separate tools | T005-T008 | T012 |
| ADR-003 side-effect-free | T005-T008, T010 | T011, T012 |
| ADR-004 object-first normalization | T002, T006, T008 | T012 |
| 一致性 | T004, T007, T008 | T012 |
| 可恢复性 | T003, T009 | T012 |
| 安全性 | T003, T011 | T012 |

---

## Context Manifest

已生成 `context-manifest.md`。本 feature 命中 multi-stage-workflow、artifact-handoff、user-visible-output、prior-closure-failure 和 bugfix-loop-breaker；实现和验证必须保留高信号上下文，避免跨会话丢失边界。

---

## Stage Readiness

- 推荐下一步：`verify`
- 阻塞项：无。
- 原因：spec 和 plan 已稳定；13/13 tasks 已完成；build PASS，test 51/51 PASS，文档已更新，diffusion check 已记录。
