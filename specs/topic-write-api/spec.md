# Feature Specification: hermes-db MCP topic write API

**Workspace**: `topic-write-api`  
**Created**: 2026-05-30  
**Status**: Clarified  
**Input**: 用户描述: "某次会话中发现所有选题优先级都是 A，想修改时发现 MCP 缺少可编辑写接口；按需求和后端/MCP 最佳实践补强。"

> 本规格基于 [`design.md`](./design.md) 提炼需求，不提前固化实现方案。

---

## Feature Traits *(LM 自动检测，用户可 override)*

| Trait | 是否命中 | 依据 |
|---|---:|---|
| `multi-stage-workflow` | ✅ | 运营/agent 需要经历选题评估、字段回写、列表复核、后续写作消费多个阶段。 |
| `external-side-effects` | ✅ | 新能力会写入 PG topic 记录并影响 Redis 缓存。 |
| `artifact-handoff` | ✅ | 更新后的 priority/resonance/column_name 会被后续选题筛选和写作流程消费。 |
| `user-visible-output` | ❌ | 本次不交付 UI、文档导出或通知；只交付 MCP 工具结构化结果。 |
| `prior-closure-failure` | ✅ | 已出现“选题优先级全为 A 后无法批量修正”的闭环断裂。 |

**结论**: 下游阶段需要启用 Producer-Consumer Matrix、Evidence Gate 和三维 Verdict；本需求涉及写入、缓存、一致性和 MCP 工具契约，进入 `plan` 前应先完成关键歧义澄清。

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 修正单条选题字段 (Priority: P1)

作为使用 hermes-db MCP 的 agent/运营操作者，我希望能修改单条选题的可编辑字段，以便在评估后修正 `priority`、`resonance`、`angle`、`title`、`column_name` 或 `content`。

**Why this priority**: 当前只支持创建、状态流转和发布，无法修正已创建选题的普通字段，是本需求的基础缺口。

**Acceptance Scenarios**:

1. **[US1-1] 单字段更新成功**  
   **Given** 存在一条 `draft` 选题，priority 为 `A`  
   **When** 调用 MCP 写接口将 priority 改为 `B`  
   **Then** 返回结构化成功结果，包含 id、updated_fields、embedding_regenerated、updated_at，并且再次读取该选题能看到 priority 为 `B`

2. **[US1-2] 语义字段更新会触发 embedding 重算**  
   **Given** 存在一条有 title/angle 的选题  
   **When** 更新 title 或 angle  
   **Then** 系统必须按更新后的 title/angle 重新生成 embedding，并在结果中标记 `embedding_regenerated=true`

**Edge Cases**:

- **[US1-3]** priority 非 `A/B/C` 时必须返回稳定错误，不写入数据。
- **[US1-4]** resonance 非 `高/中/低` 时必须返回稳定错误，不写入数据。
- **[US1-5]** title 为空或超过 200 字符时必须返回稳定错误，不写入数据。
- **[US1-6]** 未提供任何可更新字段时必须返回 `no_fields_to_update`。
- **[US1-7]** id 不存在时必须返回 `not_found`。
- **[US1-8]** nullable 字段必须通过显式 `clear_fields` 语义清空，普通可选参数中的 `None` 表示不更新。

### User Story 2 - 批量修正选题优先级和运营标注 (Priority: P1)

作为 agent/运营操作者，我希望能一次性更新多条选题的非语义字段，以便在发现批量误标或完成评估后快速修正。

**Why this priority**: “所有选题优先级都是 A”是本需求的直接触发场景；逐条调用成本高且容易出错。

**Acceptance Scenarios**:

1. **[US2-1] 批量更新同一组字段**  
   **Given** 输入一组 topic id，其中大部分存在  
   **When** 批量将 priority 改为 `B`  
   **Then** 系统只更新存在的记录，返回 matched、updated、updated_fields、not_found_ids，并让后续读取看到新值

2. **[US2-2] 批量接口不修改语义字段**  
   **Given** 调用方尝试通过批量接口修改 title 或 angle  
   **When** 请求到达 MCP 工具  
   **Then** 系统必须拒绝请求并返回稳定错误，避免批量触发 embedding 调用

**Edge Cases**:

- **[US2-3]** ids 为空时必须返回稳定错误，不写入数据。
- **[US2-4]** ids 中有重复值时系统必须自动去重，并在结构化结果中回显去重前后的数量。
- **[US2-5]** ids 中包含非法 UUID 时必须返回稳定错误，不产生部分不可追踪写入。
- **[US2-6]** 单次批量更新必须有上限，默认建议不超过 100 条。
- **[US2-7]** 批量接口本期不得直接修改 status；状态批量流转应另建工具并逐条走状态机。

### User Story 3 - 复核和筛选待处理选题 (Priority: P2)

作为 agent/运营操作者，我希望列表查询能按 priority 筛选、排除 published，并返回运营评估字段，以便复核哪些选题仍需处理。

**Why this priority**: 写接口解决回写，列表增强解决回写前后的核对；没有它，批量修正后的闭环仍不完整。

**Acceptance Scenarios**:

1. **[US3-1] 按 priority 过滤**  
   **Given** 存在 A/B/C 不同优先级的选题  
   **When** list_topics 使用 priority=`A`  
   **Then** 只返回 A 级选题，并包含 total

2. **[US3-2] 排除已发布内容**  
   **Given** 存在 draft、writing、published、archived 多种状态  
   **When** list_topics 使用 exclude_published=true  
   **Then** 结果不得包含 published 状态记录

**Edge Cases**:

- **[US3-3]** list_topics 返回项必须包含 priority、resonance、column_name，避免 agent 为复核再逐条 get。
- **[US3-4]** limit/offset 必须有边界校验，避免过大查询拖慢数据库。

### User Story 4 - MCP 工具契约可被 agent 稳定消费 (Priority: P1)

作为 MCP client/agent，我希望写工具有稳定输入校验、结构化输出和行为提示，以便能安全调用、解析结果并理解副作用。

**Why this priority**: MCP 工具面向 agent，不只是内部函数；不稳定 schema 和模糊错误会导致 agent 误判、重试或重复写入。

**Acceptance Scenarios**:

1. **[US4-1] 结构化输出稳定**  
   **Given** 调用任一新增或增强的 topic 工具  
   **When** 工具返回成功或失败  
   **Then** 返回结构必须可由 MCP 客户端稳定解析，成功结果和错误结果字段契约清晰

2. **[US4-2] 行为注解准确**  
   **Given** MCP client 发现工具列表  
   **When** 查看 list/get/find/update/batch/publish 工具元信息  
   **Then** 只读工具应标记为只读；写工具应明确非只读、是否 destructive、是否 idempotent、是否 open-world

**Edge Cases**:

- **[US4-3]** 工具不得把 Python 异常、数据库异常或缓存异常直接泄漏给 MCP client。
- **[US4-4]** 对可重试失败和不可重试校验失败，错误 code 必须可区分。

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系统必须提供单条 topic 普通字段更新能力，覆盖 `title`、`angle`、`priority`、`column_name`、`resonance`、`content`。
- **FR-002**: 系统必须继续把 status 流转与普通字段更新分离；普通字段更新不得绕过现有状态机。
- **FR-003**: 系统必须在 title 或 angle 变化时基于更新后的完整 title/angle 重新生成 embedding。
- **FR-003a**: 当 title 或 angle 更新但 embedding 生成失败时，字段更新允许成功，结果必须返回 `embedding_pending=true`，且不得把旧 embedding 伪装为已更新向量。
- **FR-004**: 系统必须提供批量更新 topic 非语义字段的能力，至少覆盖 `priority`、`resonance`、`column_name`。
- **FR-005**: 批量更新接口本期不得支持 title、angle、content 等可能触发 embedding 或大字段写入的字段。
- **FR-006**: 批量更新接口本期不得支持 status；如需批量状态流转，必须作为后续独立能力逐条执行状态机校验。
- **FR-007**: list_topics 必须支持 `priority` 过滤和 `exclude_published` 过滤。
- **FR-008**: list_topics 返回项必须包含 `priority`、`resonance`、`column_name`。
- **FR-009**: 新增和增强工具必须提供稳定的结构化成功结果与错误结果。
- **FR-010**: 新增和增强工具必须对 priority、resonance、title、ids、limit、offset 做输入校验。
- **FR-010a**: 单条更新工具必须支持显式 `clear_fields` 参数，只允许清空 `angle`、`column_name`、`resonance`、`content`，不得清空 title、priority、status 或 account。
- **FR-011**: 更新写入成功后，系统必须保证后续 get_topic/list_topics 不返回过期缓存数据。
- **FR-012**: Redis 缓存写入或删除失败不应导致主写入失败，但必须避免把失败后的陈旧缓存作为权威结果长期暴露。
- **FR-013**: MCP 工具必须提供准确的行为提示，区分只读工具和有副作用的写工具。
- **FR-014**: 返回错误必须包含稳定 code，便于 agent 判断是否修正输入、重试或停止。

### Non-Functional Requirements

- **NFR-001**: 单次批量更新默认上限建议为 100 条；超限请求必须被拒绝或要求分页处理。
- **NFR-002**: 批量更新应避免逐条数据库写入导致的线性慢请求；具体 SQL 策略进入 plan 决定。
- **NFR-003**: embedding 重算失败不得产生“字段已更新但 embedding 状态不明”的静默结果；成功结果必须暴露 `embedding_pending=true`。
- **NFR-004**: 工具输出 schema 应尽量由类型注解或模型驱动，减少裸 dict 契约漂移。
- **NFR-005**: 动态字段更新必须有字段白名单，禁止调用方控制数据库列名。
- **NFR-006**: 测试必须覆盖 tool 层校验、repository 层 SQL/参数行为、缓存一致性、批量 not_found 计算。

### Quality Attributes *(architecture-relevant)*

| 属性 | 目标 | 为什么重要 | 验收 / 证据 | 是否阻塞 plan |
|------|------|------------|-------------|----------------|
| 一致性 | 写入后读取不得返回旧 topic 缓存 | 该需求的核心是修正错误数据，陈旧缓存会让修正看似失败 | 缓存失效/重写测试 | 是 |
| 可用性 | Redis/embedding 辅助失败不应无说明地破坏主流程 | 工具被 agent 调用，需要明确失败语义 | 错误 code 与 embedding_pending 证据 | 是 |
| 性能 | 批量更新 100 条以内不应逐条慢写 | 运营修正常涉及几十条记录 | repo 层测试或集成验证 | 是 |
| 安全性 | 写接口不能接受任意字段或绕过状态机 | 防止 agent 误调用造成数据破坏 | 白名单和状态边界测试 | 是 |
| 可演进性 | 工具 schema、错误模型、字段白名单集中可维护 | 后续还会增加 status 批量流转、精细批改 | 类型模型/契约测试 | 否 |
| 可观测性 | 失败必须能定位到校验、DB、embedding 或缓存阶段 | MCP client 的错误上下文有限 | 稳定错误 code 和日志策略 | 否 |

### Key Entities

- **Topic**: 选题记录；关键字段包括 id、title、angle、account、status、priority、column_name、resonance、content、source、published_url、embedding、created_at、updated_at。
- **Topic Editable Fields**: 本期允许普通更新的字段集合；不包含 status、published_url、source、account、created_at、updated_at。
- **Topic Operational Fields**: 可批量更新且不影响语义向量的字段集合；本期为 priority、resonance、column_name。
- **Tool Result**: MCP 工具返回契约；区分 success result 和 error result，并包含稳定 code。

---

## Out of Scope

- 本期不实现批量 status 流转。
- 本期不实现逐条不同字段的复杂批量 updates 形态，除非 plan 阶段确认成本很低。
- 本期不修改 topic 表结构，除非探索发现当前 schema 与需求冲突。
- 本期不提供 UI 或运营后台页面。
- 本期不改变 `create_topic` 的默认 priority 策略，除非澄清阶段确认“全部为 A”的根因来自创建默认值或上游调用约定。

---

## Clarified Decisions

- **CD-001**: 清空 nullable 字段采用显式 `clear_fields` 契约；普通可选参数中的 `None` 保持“不更新”含义，避免 MCP 函数签名无法区分 missing/null。
- **CD-002**: 批量 ids 重复值自动去重，并在结果中返回 requested_count、unique_count、updated_count。
- **CD-003**: title/angle 更新时 embedding 生成失败不阻断主字段更新；结果必须返回 `embedding_pending=true`，并确保旧 embedding 不被误认为新语义向量。
- **CD-004**: 本 feature 先补修正能力与写接口契约；“全部为 A”的上游误写来源作为后续观察项，不阻塞本期。

---

## Stage Readiness

- 下一步建议：`plan`
- 阻塞项：无。剩余上游误写根因属于后续观察项，不阻塞当前写接口方案设计。
