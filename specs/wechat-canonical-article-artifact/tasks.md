# Tasks: WeChat Canonical Article Artifact

**Workspace**: `wechat-canonical-article-artifact` | **Date**: 2026-06-24  
**Input**: `specs/wechat-canonical-article-artifact/spec.md` + `plan.md`  
**Prerequisites**: spec.md ✅, plan.md ✅, data-model.md ✅

---

## 执行原则

- 按端到端 slice 推进：先让一个 Tiptap/ProseMirror JSON fixture 变成微信安全 HTML，再接入 publish-ready artifact 和 draft MCP 边界。
- 不把 Markdown import/export 当主路径；它只服务 legacy 兼容和人工备份。
- 所有 publish-ready 验证都以微信草稿可直接适配为准，而不是以通用 HTML 渲染成功为准。
- `wechat_create_draft` 仍只接受 `wechat_api_article`，不接受 `article_document`。

---

## Phase 1: Contract And Dependency Foundation

**目标**: 建立成熟文档模型依赖、artifact 类型和 validator 基础，为后续 renderer slice 服务。

- [x] T001 [Foundation] 添加 Tiptap/ProseMirror 运行时依赖并记录包边界
  - scope: `packages/wechat-draft/package.json`, lockfile
  - slice: 为 T003/T004 提供成熟 JSON 文档模型和类型/工具能力
  - blocked_by: none
  - maps_to: ADR-001, FR-002, 工具成熟度
  - verify: `pnpm --filter @mcps/wechat-draft build` 能解析新增依赖；依赖只包含 Tiptap/ProseMirror MVP 所需包，不引入 editor UI/cloud/collaboration 包

- [x] T002 [Foundation] 定义 `article_document` artifact 类型、metadata 和 schema version
  - scope: `packages/wechat-draft/src/render/ArticleDocumentTypes.ts`, `packages/wechat-draft/src/render/index.ts`
  - slice: 可用 TypeScript 表达 `article_document.tiptap.v1` envelope、assets、metadata、source refs
  - blocked_by: T001
  - maps_to: US1, FR-001, FR-014, data-model.md
  - verify: `tsc -p packages/wechat-draft/tsconfig.json` 通过；新增 fixture 可 typecheck

- [x] T003 [Foundation] 实现 Tiptap/ProseMirror allowlist validator
  - scope: `ArticleDocumentValidator.ts`, `TiptapExtensionAllowlist.ts`, renderer tests
  - slice: valid JSON 通过，未知 node/mark、缺 title、缺 image asset_ref 失败
  - blocked_by: T002
  - maps_to: US1, FR-003, FR-004, 可演进性, 可诊断性
  - verify: 新增测试覆盖 valid fixture、unknown node、unknown mark、missing image asset、invalid schema_version

---

## Phase 2: WeChat Renderer Slice

**目标**: 从 canonical `article_document` 生成微信安全 HTML，证明不再依赖 Markdown 字符串处理。

- [x] T004 [US2] 实现 Tiptap JSON -> WeChat-safe HTML renderer
  - scope: `WechatArticleDocumentRenderer.ts`, `WechatStyleProfile.ts`, `render/index.ts`
  - slice: 包含 paragraph、heading、bold、link、image、divider 的 fixture 可渲染为内联样式 HTML
  - blocked_by: T003
  - maps_to: US2, FR-006, FR-013, ADR-002, 微信适配性
  - verify: renderer 测试断言无 `##`、`**`、`![](...)` 残留；输出包含 profile heading/divider/image style

- [x] T005 [US2] 实现 unresolved asset 和非微信图片 URL 的 fail-closed 行为
  - scope: `WechatArticleDocumentRenderer.ts`, validator tests
  - slice: image node 缺 asset 或 asset 未准备时不得生成 publish-ready HTML
  - blocked_by: T004
  - maps_to: US2 Edge, FR-008, NFR-003, 可诊断性
  - verify: 测试覆盖 missing asset_ref、asset_map 缺项、非 `mmbiz.qpic.cn` URL，错误码/字段可诊断

- [x] T006 [US2] 生成 `wechat_api_article` artifact payload builder
  - scope: `ArticleDocumentToWechatArtifactBuilder.ts`, `ArtifactValidator.ts` fixtures
  - slice: `article_document` + prepared asset map -> `stage=publish_ready,type=wechat_api_article` artifact
  - blocked_by: T004, T005
  - maps_to: US2, FR-007, FR-008, ADR-003
  - verify: 生成的 artifact 可通过现有 `ArtifactValidator.validate()`；缺 cover `thumb_media_id` 时失败

---

## Phase 3: Draft MCP Boundary And Compatibility

**目标**: 保证草稿 MCP 直接适配 publish-ready artifact，同时拒绝错误输入。

- [x] T007 [US2] 增加 draft MCP 边界回归测试：拒绝 `article_document`
  - scope: `ArtifactValidator.ts`, `DraftPayloadBuilder.ts`, new test fixture
  - slice: 调用 draft payload builder 时，`type=article_document` 必须失败，不能被当作 HTML 草稿
  - blocked_by: T002
  - maps_to: US2, FR-009, 职责边界
  - verify: 测试断言 `Expected 'wechat_api_article'` 或等价结构化错误

- [x] T008 [US2] 更新 WeChat-ready artifact 示例文档，补充 source article link
  - scope: `packages/wechat-draft/docs/wechat-ready-artifact-example.md`, `docs/article-document-artifact-example.md`
  - slice: 文档展示 `article_document -> wechat_api_article` 的父子/metadata 链路
  - blocked_by: T006
  - maps_to: US2, FR-010, 可追溯性
  - verify: 文档包含 `source_article_document_artifact_id`, `schema_version`, `style_profile_id`, `wechat_asset_manifest`

---

## Phase 4: Markdown Import / Export Compatibility

**目标**: 保留旧 Markdown 能力，但不让它回到 canonical 主路径。

- [x] T009 [US1/US3] 实现 legacy Markdown -> `article_document` importer 的最小子集
  - scope: `MarkdownArticleImporter.ts`, fixtures based on current 月亮/微雨文章样式
  - slice: H1/H2、段落、粗体、分割线、图片语法可转成 Tiptap JSON envelope
  - blocked_by: T002, T003
  - maps_to: US1, FR-005, NFR-005
  - verify: importer 测试证明输入 Markdown 只用于生成 `article_document`；输出 JSON 不包含 Markdown 控制语法作为结构

- [x] T010 [US3] 实现 `article_document` -> Markdown/HTML preview exporter
  - scope: `MarkdownArticleExporter.ts`, optional preview helper
  - slice: Agent 或人工备份可从 canonical document 导出可读 Markdown，并标记 non-canonical/possibly lossy
  - blocked_by: T003
  - maps_to: US3, FR-012, NFR-005
  - verify: export 测试覆盖 heading、paragraph、bold、image alt；导出 metadata 或文档说明包含 non-canonical 标记

---

## Phase 5: End-To-End Evidence

**目标**: 证明从 mature document model 到微信草稿的闭环成立。

- [x] T011 [US2] 建立本地端到端 fixture：`article_document` -> `wechat_api_article` -> DraftPayloadBuilder
  - scope: test fixture, renderer, artifact builder, `DraftPayloadBuilder`
  - slice: 不调用真实微信 API，也能证明 ready artifact payload 可构造
  - blocked_by: T006, T007
  - maps_to: US2, FR-006, FR-007, FR-009, 微信适配性
  - verify: 单命令测试通过；断言 payload content 为微信安全 HTML，thumb_media_id 存在，body image URL 为 `mmbiz.qpic.cn`

- [x] T012 [US2] 执行月亮账号 live smoke：创建草稿并 batchget 核验
  - scope: smoke script / manual runbook; only create draft, no publish
  - slice: 使用 `yueliang.default` fixture 真实创建草稿，并读取草稿 HTML 统计
  - blocked_by: T011
  - maps_to: US2, user-visible-output, external-side-effects, Evidence Gate
  - verify: 记录 media_id；`draft/batchget` 断言 no Markdown residue、3 类图片/样式字段正常、正文图片为微信 URL

- [x] T013 [Verify] 运行全量相关验证并整理 evidence
  - scope: build/test commands, `specs/wechat-canonical-article-artifact/acceptance.md`
  - slice: 所有核心需求有 fresh evidence
  - blocked_by: T001-T012
  - maps_to: 所有 US/FR, Quality Attributes
  - verify: `pnpm --filter @mcps/wechat-draft build`、renderer/import/export tests、artifact validator tests、live smoke evidence 记录完成

---

## Phase 6: Documentation And Closeout Prep

**目标**: 让后续生产验证和维护者能理解边界和使用方式。

- [x] T014 [Docs] 更新运行手册和架构说明
  - scope: `packages/wechat-draft/docs/`, feature docs
  - slice: 说明 `article_document`、`wechat_api_article`、Markdown import/export、draft MCP 边界
  - blocked_by: T008, T011
  - maps_to: artifact-handoff, prior-closure-failure
  - verify: docs 明确写出“Markdown is non-canonical”和“draft MCP only consumes `wechat_api_article`”

- [x] T015 [Closeout] 准备 acceptance 和 commit plan
  - scope: `specs/wechat-canonical-article-artifact/acceptance.md`, optional `commit-plan.md`
  - slice: 完成 SDD closeout 前置记录
  - blocked_by: T013, T014
  - maps_to: closeout, Evidence Gate
  - verify: acceptance verdict、阻塞项、残留风险、live smoke media_id/证据路径写入

---

## 依赖与顺序

- 关键路径：T001 -> T002 -> T003 -> T004/T005 -> T006 -> T011 -> T012 -> T013 -> T015。
- 可并行：
  - T007 可在 T002 后并行推进。
  - T009/T010 可在 T003 后与 renderer 主线并行。
  - T008/T014 可在对应实现稳定后并行完善。
- T012 是唯一真实外部副作用任务，只创建草稿，不自动发布。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|---|---|
| US1 保存结构化文章正文 | T001, T002, T003, T009 |
| US2 生成微信发布就绪产物 | T004, T005, T006, T007, T011, T012 |
| US3 Agent/UI 阅读与人工校对 | T010, T014 |
| Markdown 非 canonical | T009, T010, T014 |
| Draft MCP 只消费 ready artifact | T007, T011 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|---|---|---|
| ADR-001 Tiptap/ProseMirror canonical model | T001, T002, T003 | T011, T013 |
| ADR-002 WeChat renderer 直接输出安全 HTML | T004, T005 | T012, T013 |
| ADR-003 复用 workflow_artifacts | T006, T008 | T011, T013 |
| ADR-004 Markdown import/export only | T009, T010, T014 | T013 |
| 微信适配性 | T004, T005, T006 | T012 |
| 可追溯性 | T006, T008 | T013 |
| 职责边界 | T007 | T011 |

---

## Context Manifest

已生成 [context-manifest.md](context-manifest.md)。原因：本 feature 命中 `multi-stage-workflow`、`artifact-handoff`、`external-side-effects`、`user-visible-output`，并且依赖 Context7/Tiptap/ProseMirror 文档结论和现有 WeChat-ready artifact contract。

---

## Stage Readiness

- 推荐下一步：`execute-plan`
- 阻塞项：无。任务较多且包含真实微信草稿副作用，建议通过 `execute-plan` 分批推进，而不是一次性实现全部。
