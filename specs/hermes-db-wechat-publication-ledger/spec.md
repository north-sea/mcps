# Feature Specification: hermes-db WeChat Publication Ledger

**Workspace**: `hermes-db-wechat-publication-ledger`  
**Created**: 2026-06-03  
**Status**: Ready for Plan  
**Input**: 用户描述: "`agents/specs/wechat-publication-ledger` 需要 hermes-db 提供公众号文章发布台账 schema 与 MCP tools；这部分从 agents 仓拆出，在 mcps 仓按 SDD 新建独立 feature，agents 侧只保留 adapter/service 消费端开发。"

> 本 feature 是 `agents/specs/wechat-publication-ledger` 的上游数据层能力。完成并部署后，agents 仓的 wechat-agent 才能把 topic、workflow run、draft artifact、最终发布稿、发布结果和后续 analytics 稳定串到同一个 article id。

---

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|:---:|---|
| `multi-stage-workflow` | ❌ | hermes-db 只提供存储与 MCP tools，不编排公众号 workflow |
| `external-side-effects` | ✅ | 需要新增 PG schema migration、MCP 写入/查询工具、health capability |
| `artifact-handoff` | ✅ | 本 feature 交付的 article ledger tools 会被 agents 仓 `PublicationLedgerService` 和后续 analytics ingestion 消费 |
| `user-visible-output` | ❌ | 不交付 UI；只交付 MCP 结构化结果 |
| `prior-closure-failure` | ✅ | 当前只有 topic `published_url` 和 publish artifact，缺少稳定 article entity，后续 analytics 无法可靠绑定 |

**结论**: 命中 `external-side-effects` + `artifact-handoff` + `prior-closure-failure`。plan 阶段必须明确 schema migration、MCP tool contract、幂等写入、外部引用补写、health capability、以及 agents 仓联调 Evidence Gate。

---

## User Scenarios & Testing

### User Story 1 - 创建文章发布台账主实体 (Priority: P1)

作为 wechat-agent，我希望 hermes-db 能在发布成功或 dry-run 完成后创建/更新一条 article ledger 记录，以便每篇文章都有稳定 article id 可供复盘和 analytics 绑定。

**Why this priority**: 微信阅读数据和复盘对象是文章，不是一次 workflow run 或 topic；缺 article id 会导致后续只能靠标题/URL 模糊匹配。

**Acceptance Scenarios**:

1. **[US1-1] 发布成功创建 article**
   **Given** agents 调用 `upsert_wechat_article`，传入 `run_id`、`account`、`draft_artifact_id`、`published_artifact_id`、`publish_artifact_id?`、`status="published"`、`published_url` 或 `external_reference`  
   **When** hermes-db 写入成功  
   **Then** 数据库存在一条 `wechat_articles` 记录，返回 `{ article_id, created?, status, updated_at }`

2. **[US1-2] dry-run 创建 drafted article**
   **Given** agents 调用 `upsert_wechat_article`，传入 `dry_run=true`、`status="drafted"`、draft/final artifact 引用  
   **When** hermes-db 写入成功  
   **Then** article 被保存为预发布台账，analytics 默认可通过 `dry_run=false` 过滤掉

**Edge Cases**:

- **[US1-3]** `topic_id` 可为空，临时任务仍必须能创建 article。
- **[US1-4]** 发布结果缺 `published_url` 但有 `external_reference` 时，记录状态为 `published_missing_url`。
- **[US1-5]** 发布结果缺 `published_url` 且缺 `external_reference` 时，记录状态为 `publish_reference_missing`，并保留 repair 所需 metadata。
- **[US1-6]** 同一发布事实重复 upsert 必须返回同一 article，不产生重复台账。

### User Story 2 - 绑定 workflow run 与 artifacts (Priority: P1)

作为运营者或复盘 agent，我希望每条 article 能追溯到 workflow run、原始草稿和最终发布稿，以便解释后续表现。

**Why this priority**: 标题、正文和配图版本差异会影响阅读表现，复盘必须知道实际发布的是哪版。

**Acceptance Scenarios**:

1. **[US2-1] 保存 draft artifact 引用**
   **Given** `workflow_artifacts` 中存在 `draft` artifact  
   **When** 创建 article  
   **Then** `draft_artifact_id` 被保存，且列表/详情查询返回该引用

2. **[US2-2] 保存最终发布稿引用**
   **Given** `workflow_artifacts` 中存在 `transformed-draft` 或 fallback `draft`  
   **When** 创建 article  
   **Then** `published_artifact_id` 被保存，且不得返回 artifact 正文

3. **[US2-3] 保存 publish-result artifact 引用**
   **Given** workflow 保存了 `publish-result` artifact  
   **When** 创建 article  
   **Then** `publish_artifact_id` 可被保存，用于追溯发布 metadata

**Edge Cases**:

- **[US2-4]** artifact id 不存在时，tool 必须返回结构化 validation/schema error；不得创建缺关键引用且无诊断的 article。
- **[US2-5]** image-prep 失败导致没有 transformed draft 时，允许 `published_artifact_id=draft_artifact_id`。
- **[US2-6]** `workflow_artifacts` capability 不可用或 migration 未执行时，article tools 应返回可诊断 schema error，不应让 MCP server crash。

### User Story 3 - 支持按文章维度查询与补写外部标识 (Priority: P1)

作为 analytics ingestion，我希望能按 URL、发布目标 reference、微信平台标识或 article id 查询文章，并补写后续采集到的微信文章标识。

**Why this priority**: 后续数据采集必须绑定到稳定 article，而不是靠标题或 topic 近似匹配。

**Acceptance Scenarios**:

1. **[US3-1] 按过滤条件列表查询**
   **Given** 已存在多条 article  
   **When** 调用 `list_wechat_articles(account?, topic_id?, run_id?, status?, publish_target?, date_from?, date_to?, limit, offset)`  
   **Then** 返回 article 摘要列表，不包含 artifact 正文

2. **[US3-2] 按 article id 读取详情**
   **Given** 已存在 article  
   **When** 调用 `get_wechat_article(article_id)`  
   **Then** 返回完整 article 元数据和外部引用列表，但不返回 artifact content

3. **[US3-3] 补写外部引用**
   **Given** analytics 或 repair 拿到 `published_url`、`canonical_url`、`wechat_msg_id`、`biz/mid/idx/sn` 或 YouMind reference  
   **When** 调用 `update_wechat_article_external_refs`  
   **Then** 外部引用被保存，主表可按 patch 更新 `published_url`、`canonical_url`、`status`

**Edge Cases**:

- **[US3-4]** 标题重复时不得只靠 title 绑定。
- **[US3-5]** URL 变更或补全时必须保留历史引用，不得无声覆盖唯一历史。
- **[US3-6]** 查询参数必须受 limit 约束，避免无界全表扫描。

### User Story 4 - 保持现有 hermes-db 能力兼容 (Priority: P2)

作为现有 hermes-db MCP 调用方，我希望新增 publication ledger tools 时不破坏 topic、workflow artifact、health 和 transport 行为。

**Why this priority**: agents 仓已依赖 topic 与 workflow artifact tools；publication ledger 是增量能力。

**Acceptance Scenarios**:

1. **[US4-1] health 暴露 capability**
   **Given** migration 和 tools 可用  
   **When** 调用 `health`  
   **Then** `capabilities.wechat_publication_ledger=true`

2. **[US4-2] 现有 tools 兼容**
   **Given** 新 migration 已合入  
   **When** 调用现有 topic/workflow artifact tools  
   **Then** 参数、返回结构和错误语义保持兼容

**Edge Cases**:

- **[US4-3]** migration 未执行时，新 tools 返回结构化 schema error。
- **[US4-4]** Codex / Claude Code Streamable HTTP 连接行为不因新增 tools 改变。

---

## Requirements

### Functional Requirements

- **FR-001**: 系统必须新增 `wechat_articles` 或等价文章发布台账主表。
- **FR-002**: 系统必须支持 `article_id`、`publication_idempotency_key`、`account`、`topic_id?`、`run_id`、`task_id`、draft/final/publish artifact 引用。
- **FR-003**: 系统必须支持文章状态 `drafted`、`published`、`published_missing_url`、`publish_reference_missing`、`archived`。
- **FR-004**: 系统必须提供 `upsert_wechat_article` MCP tool。
- **FR-005**: 系统必须提供 `list_wechat_articles` MCP tool，默认只返回摘要和引用，不返回 artifact 正文。
- **FR-006**: 系统必须提供 `get_wechat_article` MCP tool。
- **FR-007**: 系统必须提供 `update_wechat_article_external_refs` MCP tool。
- **FR-008**: 系统必须通过唯一约束或等价逻辑保证同一发布事实幂等 upsert。
- **FR-009**: 系统必须支持后续补写 `published_url`、`canonical_url`、微信平台标识和发布目标 reference。
- **FR-010**: `health` 必须暴露 `wechat_publication_ledger` capability。
- **FR-011**: 新增 tools 不得删除、改名或破坏现有 topic/workflow artifact tools。

### Non-Functional Requirements

- **NFR-001**: 所有写入 tool 必须幂等，支持 agents 仓 workflow 重试。
- **NFR-002**: 列表查询必须有索引支持，不得默认全表拉 artifact 正文。
- **NFR-003**: MCP tool 错误必须结构化，包含 validation/not_found/schema_drift/transport 类别中的可诊断信息。
- **NFR-004**: migration 必须只新增表、索引、约束和 tools，不破坏现有 topic/workflow artifact 表。
- **NFR-005**: URL/reference 更新必须保留历史外部引用，支持审计和 repair。

### Quality Attributes

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|---|---|---|---|---|
| 幂等性 | 同一发布事实重复 upsert 只得到一条 article | 发布重试常见，重复 article 会污染 analytics | repository/tool 重复调用测试 | 是 |
| 可追溯性 | article 可追溯 run、topic、draft、final、publish-result | 复盘需要解释具体发布版本 | tool tests + agents live smoke | 是 |
| 兼容性 | 现有 topic/workflow artifact tools 不回退 | agents 当前链路依赖这些能力 | 现有测试套件通过 | 是 |
| 可诊断性 | schema/tool 错误结构化 | 跨仓联调需要快速定位问题 | schema missing / not_found tests | 是 |
| 可演进性 | analytics 可按 article id/URL/ref 绑定 | 后续数据采集依赖稳定文章实体 | query/update refs contract tests | 是 |

### Key Entities

- **wechat_articles**: 公众号文章发布台账主实体，保存 article id、幂等键、账号、topic/run/task、artifact 引用、状态、发布链接和发布目标引用。
- **wechat_article_external_refs**: article 的多源外部标识表，保存 URL 历史、微信平台标识、YouMind reference、人工 repair reference 等。
- **publication_idempotency_key**: 防止重复 article 的幂等键，优先来自 account + target + external reference 或 canonical URL，缺失时 fallback 到 account + run + publish artifact。

---

## Out of Scope

- 不实现 wechat-agent 侧 adapter、`PublicationLedgerService` 或 workflow 接入；该部分由 `agents/specs/wechat-publication-ledger` 负责。
- 不实现微信发布 API。
- 不采集阅读/分享/收藏等 metrics；该部分属于后续 `wechat-analytics-ingestion`。
- 不生成复盘报告或 topic optimizer。
- 不把 artifact 正文复制进 article 表；article 只引用 artifact id。
- 不改变现有 topic 状态机。

---

## Upstream / Downstream Contract

- **上游实现仓**: `/Users/yqg/personal/AI/mcps/packages/hermes-db`
- **下游消费仓**: `/Users/yqg/personal/AI/agents`
- **下游 feature**: `agents/specs/wechat-publication-ledger`
- **依赖 feature**: `mcps/specs/hermes-db-wechat-artifact-persistence` 已提供 `wechat_workflow_runs` 和 `workflow_artifacts`
- **联调顺序**:
  1. hermes-db 完成 article schema + MCP tools + health capability。
  2. agents 仓实现 `HermesArticleLedgerTools` adapter 和 `PublicationLedgerService`。
  3. 使用本地或 NAS hermes-db endpoint 做 upsert/list/get/update refs live smoke。

---

## Unclear Questions

- `wechat_articles` 是否必须通过 FK 强约束引用 `workflow_artifacts`，还是允许弱引用以兼容历史数据；建议 plan 阶段结合现有 migration 风格决定。
- `published_url` 与 `canonical_url` 的规范化规则由 hermes-db 计算，还是由 agents/analytics 调用方传入；建议 MVP 允许调用方传入，hermes-db 只做唯一约束和基础校验。
- `article_id` 由服务端生成还是可由客户端传入；建议服务端生成，客户端只传幂等键。

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项：无阻塞；上述 unclear questions 属于 plan 阶段设计决策，不阻塞进入 plan。
