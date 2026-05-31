# Implementation Plan: hermes-db MCP topic write API

**Workspace**: `topic-write-api` | **Date**: 2026-05-30 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/topic-write-api/spec.md`

---

## Summary

在现有 `packages/hermes-db` FastMCP 服务内补齐 topic 普通字段更新、批量运营字段更新和列表筛选能力，同时把 topic 工具的输入校验、结构化返回、错误契约、缓存一致性和 MCP annotations 收敛成可测试的服务内约定。

本期采用保守的分层增强方案：不改表结构，不引入队列，不拆新服务；只在 tool / repository / cache / contract 层补边界。

---

## Architecture Overview

```text
MCP client / agent
  |
  v
FastMCP tools: topics.py
  - validate request
  - produce structured result / error
  - apply MCP ToolAnnotations
  |
  v
Topic repository: topic_repo.py
  - whitelist editable columns
  - dynamic partial update
  - bulk update operational fields
  - enhanced list filters
  |
  +--> embedding service
  |      - regenerate only for title/angle changes
  |      - None => embedding_pending
  |
  +--> cache service
         - rewrite full row for single update
         - delete keys after batch update
```

现有 `server.register_tools()` 已导入 `topics` 模块，新工具加 `@mcp.tool()` 即可注册。实现应维持当前 asyncpg + Redis + httpx 依赖边界。

---

## Architecture Reference

| 参考模式 / 模板 | 来源 URL | 适配点 | 不适配点 | 当前阶段 |
|-----------------|----------|--------|----------|----------|
| 分层单体 | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | 当前服务已有 tools / services / repositories 分层；本期是单服务内写接口补齐 | 不需要拆微服务、事件流或 CQRS | MVP/成长期之间 |
| MCP structured output + annotations | https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md | Python SDK 支持通过类型注解生成结构化输出，并支持 `annotations` 参数描述工具副作用 | annotations 只是 hint，不能替代服务端校验和权限边界 | 当前 MCP 工具契约升级 |

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| `update_topic` | 更新后的 topic 普通字段与结构化结果 | `get_topic` / 后续 agent 决策 | 更新后 `get_topic` 返回新字段，且缓存不陈旧 |
| `batch_update_topics` | 批量更新后的 priority/resonance/column_name | `list_topics` / 写作选题流程 | `list_topics(priority=...)` 能筛出更新后的记录 |
| `list_topics` | 带 priority/resonance/column_name 的列表结果 | 运营复核 / agent 选择下一批写作选题 | 列表项包含运营字段，无需逐条 `get_topic` |
| topic tool contracts | stable success/error shape | MCP client / agent retry logic | 单测覆盖 error code 和成功结果字段 |

**孤儿 artifact 处理**: 无孤儿 artifact；所有新增写入结果都由读取或后续 agent workflow 消费。

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 一致性 | 写后读不返回旧缓存 | 单条更新重写完整缓存；批量更新删除相关缓存键 | cache service/tool tests |
| 性能 | 100 条以内批量更新避免逐条 SQL | repository 层使用单次批量 UPDATE + RETURNING | repository SQL/参数测试 |
| 安全性 | 不允许任意字段更新或绕过状态机 | tool 和 repo 双层字段白名单；status 留在现有状态机工具 | validation tests |
| 可用性 | embedding/Redis 辅助失败有明确语义 | embedding None => `embedding_pending=true`；Redis 失败不阻断主写入 | embedding/cache failure tests |
| 可演进性 | schema 和错误契约集中维护 | 新增 contracts/validation helper，减少裸 dict 漂移 | output model tests |

---

## Capacity / Scale Notes

- **规模假设**: 单次人工/agent 运营修正常见几十条，本期上限 100 条。
- **读写特征**: topic 读取多于写入；批量写入主要是低频修正或评估回写。
- **失败代价**: 错写和陈旧缓存比短暂失败更严重；因此校验失败必须不写入，写入成功后必须处理缓存。

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001 保持分层单体增强 | 本期只补 hermes-db MCP 内 topic 写能力 | A. 分层增强；B. 事件/队列异步化；C. 独立运营服务 | 选 A | 批量能力受单请求上限约束，但实现和运维成本最低 | architecture reference |
| ADR-002 `clear_fields` 表达清空 | Python/FastMCP 可选参数难区分 missing/null | A. `clear_fields`；B. payload 对象区分 missing/null | 选 A | 参数稍多，但保持现有函数签名风格 | UNVERIFIED |
| ADR-003 embedding 失败不阻断字段更新 | 现有 create_topic 已允许 embedding pending | A. 整体失败；B. 字段成功 + pending | 选 B | 可能短期影响相似检索，但不阻塞人工修正 | existing code |
| ADR-004 批量不支持 status/语义字段 | 避免绕过状态机和批量 embedding 调用 | A. 单独支持运营字段；B. 万能批量 patch | 选 A | 后续复杂批改需新增能力 | spec.md |
| ADR-005 使用 SDK structured output 与 annotations | MCP client 需要稳定契约和副作用 hint | A. Pydantic/TypedDict 模型；B. 继续裸 dict | 选 A | 需要新增 contract 模块和迁移测试 | MCP Python SDK docs |

---

## Key Design Decisions

### Decision 1: Topic 工具增加契约层，不继续扩散裸 dict

- **背景**: 当前 tools 直接返回 dict/list，错误 shape 不统一。
- **选项**:
  - A: 新增轻量 Pydantic/TypedDict contract 模块，工具返回稳定类型。
  - B: 继续裸 dict，只靠测试约束。
- **结论**: 选 A。MCP Python SDK 会基于兼容类型注解生成结构化输出 schema，并可校验结构化输出。
- **影响**: 新增 `contracts.py` 或 `schemas.py`，定义 success/error/list result；工具层负责把异常转成稳定错误。
- **来源**: https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md

### Decision 2: 单条更新使用“读旧值 -> 合并 -> 可选 embedding -> 写入完整行”

- **背景**: title/angle 更新需要基于更新后完整语义文本重算 embedding。
- **选项**:
  - A: 先读旧值并合并后更新。
  - B: 直接 SQL update，再二次读出重算。
- **结论**: 选 A。逻辑更直观，便于在 embedding 失败时写入 `embedding=None` 或 pending 语义。
- **影响**: `update_topic` 会先调用 `get_by_id`；repository update 返回完整行，用于缓存重写和工具结果。
- **来源**: existing code

### Decision 3: 批量更新只做运营字段，缓存采用删除而非重写

- **背景**: 批量更新可能涉及几十条，逐条重写缓存收益低且容易残缺。
- **选项**:
  - A: 删除相关 `hermes:topic:{id}` 缓存键。
  - B: 批量查完整行并逐条重写缓存。
- **结论**: 选 A。下次 `get_topic` 回源重建，行为简单可靠。
- **影响**: cache service 增加 `delete_cached(*keys)`；批量更新成功后按实际更新 id 删除缓存。
- **来源**: existing cache pattern

---

## Module Design

### Module: `tools/topics.py`

**职责**: MCP 工具入口，做输入校验、上下文获取、调用 repo/service、返回结构化结果。

**改动概述**:

- 新增 `update_topic`。
- 新增 `batch_update_topics`。
- 增强 `list_topics` 参数和返回字段。
- 给 topic 工具加 `ToolAnnotations`。
- 将校验和错误返回收敛到 helper/contract。

**关键接口 / 行为**:

```text
update_topic(id, ctx, title=None, angle=None, priority=None,
             column_name=None, resonance=None, content=None,
             clear_fields=None)

batch_update_topics(ids, ctx, priority=None, resonance=None, column_name=None)

list_topics(ctx, account=None, status=None, priority=None,
            exclude_published=False, limit=20, offset=0)
```

**注意事项**:

- `clear_fields` 仅允许 `angle`, `column_name`, `resonance`, `content`。
- `None` 表示不更新；清空必须走 `clear_fields`。
- UUID 解析错误必须返回稳定 error code。
- 批量接口去重并返回 requested_count / unique_count。

### Module: `repositories/topic_repo.py`

**职责**: 数据访问和 SQL 生成，保证字段白名单和参数化。

**改动概述**:

- 新增 `EDITABLE_TOPIC_FIELDS` 和 `BULK_TOPIC_FIELDS` 白名单。
- 新增 `update_topic_fields(pool, topic_id, fields, embedding_marker)`。
- 新增 `batch_update_fields(pool, topic_ids, fields)`。
- 增强 `list_by_filter` 支持 priority / exclude_published，SELECT 补 `resonance`, `column_name`。

**关键接口 / 行为**:

```text
update_topic_fields(...) -> full topic row | None
batch_update_fields(...) -> updated ids
list_by_filter(..., priority=None, exclude_published=False) -> items,total
```

**注意事项**:

- 列名只来自白名单，值全部参数化。
- embedding 字段需要 pgvector register。
- update 返回完整行，字段集与 `get_by_id` 对齐。

### Module: `services/cache.py`

**职责**: 缓存读写删除容错封装。

**改动概述**:

- 新增 `delete_cached(r, *keys)`。
- 保持 Redis 异常吞掉的现有风格，但工具层结果不得声称缓存一定成功。

### Module: contracts / validation helper

**职责**: 工具输入常量、错误 code、结果 shape。

**改动概述**:

- 定义 priority/resonance/clear_fields/batch size 常量。
- 定义 `ToolError`、`TopicUpdateResult`、`BatchTopicUpdateResult`、`TopicListResult` 等结构。
- 提供 `error(code, message, field=None, details=None)` helper。

---

## Data Model

本期不修改数据库表结构。逻辑模型变化是新增可编辑字段集合与批量运营字段集合：

- `Topic Editable Fields`: title, angle, priority, column_name, resonance, content
- `Topic Clearable Fields`: angle, column_name, resonance, content
- `Topic Bulk Operational Fields`: priority, resonance, column_name

不需要单独 `data-model.md`；字段语义已在 `spec.md` 与本计划覆盖。

---

## Project Structure

```text
packages/hermes-db/src/hermes_db_mcp/
  tools/topics.py                 # 新增/增强 MCP tools
  repositories/topic_repo.py       # 新增单条和批量更新 repo 方法
  services/cache.py                # 新增缓存删除 helper
  contracts.py or tools/contracts.py
                                   # 新增结构化结果/错误/校验常量

packages/hermes-db/tests/
  test_topic_repo.py               # SQL 和参数行为
  test_topics_tools.py             # tool 层校验、结果、缓存、embedding
  test_validation.py               # 常量/字段集合
```

---

## Risks and Tradeoffs

- `embedding_pending=true` 允许字段更新成功但短期相似检索不准确；这是为了优先保证运营修正可落库。
- ToolAnnotations 只是客户端提示，不能替代服务端校验；实现仍必须以白名单和状态机为准。
- 动态 SQL 有注入风险；必须用固定列名白名单和参数化值。
- 批量更新删除缓存后，下一次 `get_topic` 会回源；这增加少量 DB 读，但避免缓存残缺。

---

## Evolution Path

- **MVP**: 单条更新、批量运营字段更新、列表增强、稳定契约。
- **成长期**: 增加 `batch_update_topic_status`，逐条状态机校验并返回 per-item result。
- **成熟期**: 如果批量操作变成高频任务，再引入后台 job、审计日志、操作历史和重试队列。

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。未引入队列、微服务或事件溯源。
- 是否引用了外部模式但没有适配检查：否。只参考分层单体和 MCP SDK 工具契约。
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。新增失败模式为 embedding pending 和 cache delete failure，已记录。

---

## Verification Strategy

- **Repository tests**: 验证动态 SQL 字段白名单、参数顺序、priority/exclude_published 条件、batch RETURNING id 和 not_found diff。
- **Tool tests**: 验证 update_topic 成功、非法字段、clear_fields、UUID 错误、not_found、embedding pending、批量去重、批量超限、结构化 error code。
- **Cache tests**: 验证单条更新重写完整缓存，批量更新删除实际更新 id 的缓存。
- **Contract tests**: 验证 MCP tool 返回结果字段稳定，annotations 与只读/写工具语义一致。
- **Regression tests**: 现有 create/status/publish/list/get/find 行为不回归。

---

## Stage Readiness

- 是否需要 `data-model.md`：不需要。本期不改数据库 schema，字段集合和逻辑实体已在 plan 中描述。
- 下一步建议：`tasks`
- 阻塞项：无。

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | 必须 | 当前文件 |
| data-model.md | 不需要 | 不改实体/状态/关系/schema |
| tasks.md | 后续阶段生成 | 由 `tasks` 阶段产出 |
| acceptance.md | 后续阶段生成 | 用于最终验收结论 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| MCP structured output | https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md | Context7 官方文档索引结果 |
| MCP ToolAnnotations | https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/types/_types.py | Context7 官方文档索引结果 |
| FastMCP tool decorator annotations 参数 | https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/mcpserver/server.py | Context7 官方文档索引结果 |
| 分层单体参考 | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | 架构模式参考，非强制套用 |
