# Feature Specification: WeChat Canonical Article Artifact

**Workspace**: `wechat-canonical-article-artifact`  
**Created**: 2026-06-24  
**Status**: Ready for Tasks  
**Input**: 用户描述: "评估公众号新链路里 md 格式字符串是否真的必须。旧草稿使用 md 是为了人工阅读；新的都会通过 MCP 保存到数据库，如果要阅读，可以让 Agent 获取，或者利用 UI 展示。"

> 本 feature 目标是把新公众号生产链路的核心正文格式从 Markdown 字符串迁移为成熟文档模型驱动的 canonical article artifact。Markdown 仅保留为历史导入、人工导出和调试展示格式，不再作为发布链路的强依赖。首期优先采用 Tiptap/ProseMirror JSON 这类成熟工具库生态，但必须以微信草稿 HTML 直适配能力为最高约束。

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|:---:|---|
| `multi-stage-workflow` | ✅ | 文章生成、样式渲染、图片资产准备、微信草稿创建之间存在明确 pipeline |
| `external-side-effects` | ✅ | 下游会上传微信素材、创建微信草稿，并写入 hermes-db artifact/ledger |
| `artifact-handoff` | ✅ | `article_document` 被 renderer/asset-prep 消费，生成 `wechat_api_article` 后再被 draft MCP 消费 |
| `user-visible-output` | ✅ | 最终产出是用户可见的公众号草稿正文、样式和图片展示 |
| `prior-closure-failure` | ✅ | 本次月亮链路烟测暴露了直接处理 Markdown 字符串会残留 `##`、`**` 等格式标记，说明旧闭环容易只修表象 |
| `bugfix-loop-breaker` | ❌ | 当前是架构和契约调整，不是单个复杂 bugfix；Markdown 残留只是触发需求的症状 |

**结论**: 命中 `multi-stage-workflow`、`external-side-effects`、`artifact-handoff`、`user-visible-output`、`prior-closure-failure`。plan 阶段必须产出 Producer-Consumer Matrix，明确 canonical artifact contract、legacy Markdown 兼容策略、renderer/asset-prep/draft MCP 边界，并在 verify 阶段设置端到端 Evidence Gate。

---

## User Scenarios & Testing

### User Story 1 - 保存结构化文章正文 (Priority: P1)

作为公众号内容生产 agent，我希望能把新生成的文章保存为基于成熟工具库的结构化 `article_document`，而不是 Markdown 字符串，以便后续样式渲染、图片处理、Agent 阅读和 UI 展示都消费同一份语义稳定的正文。

**Why this priority**: 这是摆脱 Markdown 正则处理的核心前提。没有结构化源数据，后续仍会回到对 `##`、`**`、图片语法的字符串补丁。

**Acceptance Scenarios**:

1. **[US1-1] 保存结构化正文**
   **Given** 内容生产流程生成一篇公众号文章  
   **When** 写入 hermes-db workflow artifact  
   **Then** 系统保存 `type="article_document"` 或等价类型，正文优先采用 Tiptap/ProseMirror JSON 文档结构，并包含 `title`、`digest?`、`author?`、`cover?`、`style_profile_id?`、`metadata`

2. **[US1-2] 表达常见公众号语义**
   **Given** 文章包含段落、二级标题、加粗、分割线、图片、链接  
   **When** 转换为 `article_document`  
   **Then** 这些语义必须以结构化字段表达，不依赖 Markdown 控制字符表达

3. **[US1-3] 保留版本与来源**
   **Given** 同一 run 多次生成或编辑文章  
   **When** 多次保存 `article_document`  
   **Then** 系统保留版本顺序，并可追溯 `source_markdown_artifact_id?`、`parent_artifact_id?` 或上游 run/stage

**Edge Cases**:

- **[US1-4]** 缺少标题、正文为空、图片 block 缺少 asset reference 时必须返回结构化 validation error。
- **[US1-5]** 旧 Markdown 导入时允许创建 `source_markdown` artifact，但新生成链路不得只保存 Markdown 而不保存 `article_document`。
- **[US1-6]** 大正文必须遵守现有 artifact 大小策略；列表查询默认不得返回全文 blocks。

### User Story 2 - 生成微信发布就绪产物 (Priority: P1)

作为 wechat-draft MCP 调用方，我希望发布链路消费 `wechat_api_article` 这种已准备好的 artifact，而不是在创建草稿时再解析 Markdown，以便草稿创建阶段只做验证和微信 API 调用。

**Why this priority**: 现有 `wechat-ready artifact` 契约已经定义 draft MCP 不负责渲染、不负责图片归一化；本 feature 应把临时脚本里的渲染/上传逻辑沉到上游正式阶段。

**Acceptance Scenarios**:

1. **[US2-1] article_document 渲染为微信 HTML**
   **Given** 已保存 `article_document`，且有 `style_profile_id="yueliang.default"`  
   **When** renderer 处理该 artifact  
   **Then** 生成 `type="wechat_api_article"` artifact，`content_text` 为微信可用 HTML，不包含 Markdown 控制语法

2. **[US2-2] 图片资产准备完成后再发布**
   **Given** 文章包含封面和正文图片  
   **When** asset-prep 阶段运行  
   **Then** 封面生成 `thumb_media_id`，正文图片替换为 `mmbiz.qpic.cn` URL，并写入 `metadata.wechat_asset_manifest`

3. **[US2-3] draft MCP 只消费 ready artifact**
   **Given** 存在 `stage="publish_ready"`、`type="wechat_api_article"` 的 artifact  
   **When** 调用 `wechat_create_draft`  
   **Then** draft MCP 只验证契约并创建草稿，不解析 Markdown、不上传图片、不重新套样式

**Edge Cases**:

- **[US2-4]** 如果 `wechat_api_article` 中存在非微信图片 URL，draft MCP 必须拒绝创建草稿。
- **[US2-5]** 如果缺少封面 `thumb_media_id`，draft MCP 必须拒绝创建草稿。
- **[US2-6]** renderer 或 asset-prep 失败时必须保存可诊断 artifact/status，不应创建半成品草稿。

### User Story 3 - 支持 Agent/UI 阅读与人工校对 (Priority: P2)

作为运营者，我希望不依赖本地 `.md` 文件也能阅读、检索和校对历史草稿，以便新生产链路可以完全基于数据库 artifact 运转。

**Why this priority**: 用户已经明确提出“如果要阅读，可以让 Agent 获取，或者利用 UI 展示”。这决定 Markdown 不再承担唯一人工可读格式的职责。

**Acceptance Scenarios**:

1. **[US3-1] Agent 按 artifact 查询正文**
   **Given** 文章已保存为 `article_document`  
   **When** Agent 通过 MCP 查询 artifact 内容  
   **Then** 能返回结构化 blocks 或渲染后的阅读视图摘要，便于对话式审阅

2. **[US3-2] UI 或导出层展示文章**
   **Given** 用户需要人工阅读  
   **When** UI 或导出工具读取 `article_document`  
   **Then** 可以渲染为阅读 HTML、预览视图或 Markdown 导出文件

3. **[US3-3] Markdown 作为导出格式**
   **Given** 用户需要复制到笔记或 git 存档  
   **When** 请求导出  
   **Then** 系统可从 `article_document` 生成 Markdown，但该 Markdown 不作为发布链路 source of truth

**Edge Cases**:

- **[US3-4]** UI/Agent 阅读入口不可默认拉取大量历史全文，必须按 artifact id 或分页查询。
- **[US3-5]** Markdown 导出丢失的展示细节必须记录为 export limitation，不应反向影响 canonical artifact。

---

## Requirements

### Functional Requirements

- **FR-001**: 系统必须定义 `article_document` canonical artifact contract，覆盖标题、摘要、作者、封面、正文 blocks、样式 profile、来源引用和 metadata。
- **FR-002**: `article_document` 必须优先基于成熟文档模型库实现，首选 Tiptap/ProseMirror JSON；如 plan 阶段否决该选型，必须记录明确 ADR 和替代理由。
- **FR-003**: 首期允许限制 Tiptap/ProseMirror extension 子集，但必须支持至少 `paragraph`、`heading`、`image`、`divider`、`quote?`、`list?`、`link mark`、`strong mark`。
- **FR-004**: 所选文档模型必须能稳定生成微信草稿可接受的 HTML；微信适配失败的节点或 mark 不得进入 publish-ready artifact。
- **FR-005**: 系统必须支持从 legacy Markdown 导入为 `article_document`，用于旧内容迁移和 smoke test，但新生产链路不得只保存 Markdown。
- **FR-006**: 系统必须支持从 `article_document` 渲染生成 `wechat_api_article`。
- **FR-007**: `wechat_api_article` 必须符合现有 WeChat-ready artifact contract：`stage="publish_ready"`、`type="wechat_api_article"`、`content_text` 为微信 HTML、`metadata.publish_ready=true`、`metadata.wechat_asset_manifest.ready=true`。
- **FR-008**: 图片处理必须通过 asset-prep 阶段完成，保存正文微信图片 URL 和封面 `thumb_media_id`，不得在 draft MCP 创建草稿时临时处理图片。
- **FR-009**: draft MCP 必须继续接受并验证 `wechat_api_article`，不得要求输入 Markdown。
- **FR-010**: 系统必须保留 `source_markdown` 或 `source_markdown_artifact_id?` 作为兼容引用，以支持旧稿追溯。
- **FR-011**: 系统必须提供 Agent 可读的 artifact 查询路径，至少能按 artifact id 获取 `article_document`。
- **FR-012**: 系统应支持从 `article_document` 导出 Markdown 或阅读 HTML，用于人工查看和外部备份。
- **FR-013**: renderer 必须保证输出 HTML 不包含 Markdown 控制语法残留，如 `##`、`**...**`、`![](...)`。
- **FR-014**: 系统必须记录样式版本，例如 `style_profile_id` 和 `style_version`，保证后续复盘知道草稿使用了哪套公众号样式。

### Non-Functional Requirements

- **NFR-001**: artifact 查询默认返回摘要，不默认返回大正文 blocks，避免 MCP 响应失控。
- **NFR-002**: artifact contract 必须可版本化，允许后续新增 block 类型而不破坏旧数据读取。
- **NFR-003**: renderer 和 asset-prep 的错误必须结构化，至少区分 validation、unsupported_block、asset_upload_failed、schema_drift。
- **NFR-004**: 发布链路必须幂等可追溯，重复运行不得无声覆盖历史 `article_document` 或 `wechat_api_article` 版本。
- **NFR-005**: Markdown 导入/导出必须是 best-effort 兼容层，不得成为新链路唯一可用路径。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 可演进性 | 新增 block/style 不破坏旧 artifact | 公众号样式和内容形态会持续扩展 | schema version + backward compatibility tests | 是 |
| 可追溯性 | 任意草稿可追溯 source、article_document、wechat_api_article、draft media id | 生产验证和复盘依赖完整链路 | artifact parent relation + ledger smoke | 是 |
| 可诊断性 | 渲染/图片/草稿失败能定位阶段 | 当前临时脚本问题难以长期维护 | structured errors + failed artifact/status | 是 |
| 用户可见质量 | 微信草稿不残留 Markdown 语法，图片正常展示 | 直接影响运营校对体验 | draft batchget 或后台草稿核验 | 是 |
| 边界清晰 | draft MCP 不负责 Markdown parsing/render/upload | 防止职责再次耦合 | contract tests 验证只消费 ready artifact | 是 |
| 工具成熟度 | 文档模型、序列化和 HTML 输出依赖成熟库 | 避免维护自造 Markdown/富文本解析器 | Tiptap/ProseMirror doc evidence + adapter tests | 是 |
| 微信适配性 | 成熟库输出必须经过微信 HTML adapter 约束 | 微信编辑器不是通用浏览器 HTML 容器 | 微信草稿 live/batchget 样式核验 | 是 |

### Key Entities

- **article_document**: 新链路 canonical 文章 artifact，首选保存 Tiptap/ProseMirror JSON 文档和样式引用。
- **article_node / article_mark**: `article_document` 的正文节点和 inline 标记，表达段落、标题、图片、分割线、加粗、链接等语义。
- **source_markdown**: legacy/导入/导出用 Markdown artifact，不是新链路 source of truth。
- **wechat_api_article**: 微信发布就绪 artifact，保存最终 HTML、封面素材、微信图片 manifest。
- **style_profile**: 公众号样式配置，如 `yueliang.default`、`weiyuchengchun.default`。
- **asset_manifest**: 图片资产准备结果，包含正文微信 URL、封面 `thumb_media_id`、warnings。

---

## Out of Scope

- 不在本 feature 内实现完整 UI；这里只定义 UI/Agent 可消费的数据契约。
- 不迁移所有历史 Markdown 存量文章；首期只要求兼容导入路径和新链路不依赖 Markdown。
- 不改变微信官方 draft/add API adapter 的底层调用方式。
- 不实现自动群发；仍然只创建草稿。
- 不在本 feature 内实现通用富文本编辑器 UI；plan 阶段需要完成文档模型工具库选型和微信适配边界。

---

## Clarified Decisions

- **文档模型选型**: 首期优先使用成熟工具库，不自造完整富文本文档模型。基于当前需求，默认进入 plan 的候选为 Tiptap/ProseMirror JSON。
- **微信草稿优先级**: 工具库选型不能只看编辑器能力；必须证明可生成或适配为微信草稿稳定接受的 HTML。若某些 Tiptap/ProseMirror 节点无法可靠适配微信，应在首期 extension allowlist 中排除。
- **渲染边界**: `article_document -> generic HTML` 可使用 Tiptap/ProseMirror 工具能力；`generic HTML -> WeChat-safe HTML` 必须有项目内 adapter/renderer 负责样式 profile、图片 URL、分割线、标题等微信约束。
- **存储形态**: 首期倾向复用 `workflow_artifacts.content_text` 保存 JSON 字符串，不优先扩展 hermes-db 表结构；plan 阶段需验证当前 size/hash/preview/list contract 是否足够。

## Unclear Questions

- Tiptap/ProseMirror 首期 extension allowlist 具体包含哪些节点/marks，才能兼顾内容表达和微信草稿稳定展示？
- Tiptap/ProseMirror 的 HTML 输出是直接作为微信 renderer 输入，还是仅把 JSON AST 作为 canonical source，由项目内 WeChat renderer 直接遍历 JSON 生成最终 HTML？
- UI 阅读入口首期是否只做 Agent/MCP 查询，还是同步提供一个轻量 HTML preview/export 工具？
- legacy Markdown 导入是否需要支持复杂 Markdown（列表、表格、引用），还是首期只覆盖当前公众号文章常用子集？

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项：无阻塞。工具库优先、微信草稿直适配优先、首期复用 `workflow_artifacts.content_text` 的方向已明确；剩余问题可在 plan 阶段通过 ADR 和 Producer-Consumer Matrix 决策。
