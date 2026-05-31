# hermes-db MCP 选题写接口扩展 — 设计方案

> 交付对象：实现 agent
> 目标：补齐选题（topic）的字段更新能力，支撑"评估共鸣度 → 批量调整优先级"等运营场景
> 现状：写接口只有 `create_topic` / `update_topic_status` / `publish_topic`，无法修改 `priority`、`angle`、`resonance` 等字段

---

## 1. 现状与缺口

### 现有 topic 工具（`tools/topics.py`）

| 工具 | 能力 | 缺口 |
|------|------|------|
| `create_topic` | 插入新选题 | — |
| `update_topic_status` | 仅改 status，带状态机校验 | 不能改其他字段 |
| `publish_topic` | status→published + url | — |
| `list_topics` | 按 account/status 过滤分页 | 不能按 priority 过滤；不返回 resonance/column_name |
| `get_topic` | 单条详情（带缓存） | — |
| `find_similar_topics` | 语义检索 | — |

### 核心缺口

1. **无法更新非 status 字段**：`priority`、`angle`、`resonance`、`column_name`、`title`、`content` 均不可改。运营评估完共鸣度后无法回写优先级。
2. **无批量能力**：一次评估常涉及几十上百条，逐条调用成本高。
3. **list 过滤维度不足**：无法按 `priority` 筛选，无法排除已发布。

---

## 2. 新增接口

### 2.1 `update_topic`（单条字段更新）

```python
@mcp.tool()
async def update_topic(
    id: str,
    ctx: Context,
    title: str | None = None,
    angle: str | None = None,
    priority: str | None = None,
    column_name: str | None = None,
    resonance: str | None = None,
    content: str | None = None,
) -> dict:
    """更新选题的可编辑字段（不含 status，状态流转走 update_topic_status）。
    仅更新显式传入的字段；title/angle 变化时重新生成 embedding。"""
```

**设计要点**

- **部分更新语义**：只更新非 `None` 的入参。用"是否传入"判断，不能用真值判断（否则无法把 `angle` 清空——但本场景无清空需求，故 `None=不更新` 即可）。
- **status 不在此接口**：状态流转有状态机约束，继续走 `update_topic_status`，职责分离。
- **embedding 重算**：当 `title` 或 `angle` 任一被更新时，需重新生成 embedding（embed_text 规则与 `create_topic` 一致：`f"{title} {angle}"` 或 `title`）。重算需要拿到更新后的完整 title+angle，所以要先读旧值合并。
- **校验**：
  - `priority` ∈ {A, B, C}（CHAR(1)，见数据模型）
  - `resonance` ∈ {高, 中, 低}
  - `title` 非空且 ≤200
  - 至少传一个可更新字段，否则返回 `{"error": "no_fields_to_update"}`
- **缓存**：更新后用**完整行**重写缓存（见 §4 缓存一致性）。

**返回**

```json
{
  "id": "...",
  "updated_fields": ["priority", "resonance"],
  "embedding_regenerated": false,
  "updated_at": "..."
}
```

不存在时返回 `{"error": "not_found", "id": id}`。

---

### 2.2 `batch_update_topics`（批量更新）

两种调用形态，二选一，不可混用：

**形态 A — 按 id 列表统一改同一组字段**（最常用：批量调优先级）

```python
@mcp.tool()
async def batch_update_topics(
    ids: list[str],
    ctx: Context,
    priority: str | None = None,
    resonance: str | None = None,
    column_name: str | None = None,
    status: str | None = None,   # 见下方说明
) -> dict:
    """批量更新多条选题的同一组字段。"""
```

**形态 B — 逐条指定不同字段**（精细批改）

```python
# 通过 updates 参数：[{"id": "...", "priority": "A"}, {"id": "...", "resonance": "中"}]
updates: list[dict] | None = None
```

> **建议优先实现形态 A**，它覆盖当前 90% 需求（批量调级）。形态 B 可作为后续增量。下面以形态 A 为主描述。

**设计要点**

- **不重算 embedding**：批量接口只允许改 `priority`/`resonance`/`column_name`/`status` 这类不影响语义向量的字段。**禁止批量改 title/angle**——避免 N 次 embedding 调用拖垮接口。如需改语义字段，走单条 `update_topic`。
- **status 的处理**：批量改 status 会绕过状态机校验，风险高。两个选项：
  - **方案一（推荐）**：批量接口**不支持 status**，只允许 priority/resonance/column_name。status 批量流转另开 `batch_update_topic_status` 并对每条做状态机校验。
  - 方案二：支持 status 但逐条校验，校验失败的进 `failed` 列表。
  实现时**采用方案一**，保持批量接口纯粹（只改无约束的标量字段）。
- **单条 SQL 批量更新**：用 `WHERE id = ANY($n::uuid[])` 一次性更新，而非循环。
- **校验**：同 `update_topic` 的 priority/resonance 取值校验；`ids` 非空且去重；至少传一个可更新字段。
- **缓存**：批量更新的行可能已被缓存，需逐个失效或重写。最简方案：**删除这些 id 的缓存键**（`DEL hermes:topic:{id}`），让下次 `get_topic` 回源重建。比逐个重写更简单可靠（见 §4）。

**返回**

```json
{
  "matched": 47,
  "updated": 47,
  "updated_fields": ["priority"],
  "not_found_ids": []
}
```

`matched` 来自 SQL 影响行数，传入 id 中未命中的进 `not_found_ids`（用 `RETURNING id` 与入参 diff 得出）。

---

### 2.3 `list_topics` 增强（小改，强烈建议）

给现有 `list_topics` 增加过滤与返回字段，否则"评估"环节拿不到 resonance、无法按 priority 复核：

```python
async def list_topics(
    ctx, account=None, status=None,
    priority: str | None = None,          # 新增过滤
    exclude_published: bool = False,      # 新增：只看待处理
    limit=20, offset=0,
)
```

- list SQL 的 SELECT 补上 `priority, resonance, column_name`（当前已返回 priority，补 resonance/column_name）。
- 新增 `priority` 过滤条件、`exclude_published`（`status != 'published'`）。

---

## 3. 数据层改动（`repositories/topic_repo.py`）

### 3.1 `update_topic_fields`（支撑 2.1）

```python
async def update_topic_fields(
    pool, *, topic_id: UUID, fields: dict, embedding: list[float] | None = None,
) -> dict | None:
    """动态拼接 SET 子句，只更新 fields 中的键。embedding 非 None 时一并更新。
    updated_at 由 DB 触发器或显式 SET now() 维护。RETURNING 完整行。"""
```

实现注意：

- 动态构造 `SET col = $n` 列表，参数化（**禁止字符串插值列值**；列名来自固定白名单 set，防注入）。
- 列名白名单：`{"title","angle","priority","column_name","resonance","content"}`，embedding 单独处理。
- `RETURNING` 返回 §4 需要的全部列（与 `get_by_id` 同列集），供重写缓存。
- 涉及 embedding 时 `async with pool.acquire()` 内先 `await register_vector(conn)`（参考 `insert_topic`）。

### 3.2 `batch_update_fields`（支撑 2.2）

```python
async def batch_update_fields(
    pool, *, topic_ids: list[UUID], fields: dict,
) -> list[UUID]:
    """WHERE id = ANY($k::uuid[]) 批量更新固定字段，RETURNING id 列表。"""
```

- 同样用固定列白名单 + 参数化。
- 返回实际更新到的 id 列表（用于算 not_found）。

### 3.3 `list_by_filter` 增强

- SELECT 补 `resonance, column_name`。
- 增加 `priority`、`exclude_published` 条件分支（沿用现有 `idx` 递增拼参数的写法）。

---

## 4. 缓存一致性（重要 — 现有代码有隐患）

**现状问题**：`update_topic_status` 当前这样写缓存：

```python
await cache_record(app.redis, f"hermes:topic:{id}", {**current, "status": new_status})
```

`current` 来自 `get_by_id`（完整行），尚可。但要注意 `update_status`/`publish` 的 `RETURNING` 只返回部分列——若未来有人用 RETURNING 的结果去写缓存就会残缺。

**新接口的缓存规则（统一约定）**：

- **`update_topic`（单条）**：用 `update_topic_fields` 的 `RETURNING` 完整行，序列化后 `cache_record` 重写 `hermes:topic:{id}`。完整行字段集必须与 `get_topic` 返回一致（id/created_at/updated_at 转 str）。
- **`batch_update_topics`（批量）**：**直接删除**涉及 id 的缓存键（`redis.delete(*keys)`），不重写。理由：批量重写要逐个序列化、收益低、易错；删除后下次 `get_topic` 自然回源。
- 缓存写入/删除失败不应让主流程报错（沿用 `cache.py` 里 `try/except pass` 的容错风格）。

---

## 5. 注册与测试

- **注册**：新工具加 `@mcp.tool()` 即自动注册（`server.register_tools()` 已 import `topics` 模块，无需改 server）。
- **测试**（`tests/` 目录已存在，沿用其风格）：
  1. `update_topic` 单字段更新 → 字段变更、其他字段不变、updated_at 刷新
  2. `update_topic` 改 title → embedding_regenerated=true
  3. `update_topic` 非法 priority/resonance → 校验错误
  4. `update_topic` 空入参 → no_fields_to_update
  5. `update_topic` 不存在 id → not_found
  6. `batch_update_topics` 混合存在/不存在 id → matched 数正确、not_found_ids 正确
  7. `batch_update_topics` 改 priority 后 `get_topic` 读到新值（验证缓存已失效）
  8. `list_topics` 按 priority 过滤、exclude_published 生效、返回含 resonance

---

## 6. 实现优先级

| 优先级 | 项 | 理由 |
|--------|----|----|
| P0 | `update_topic` + `update_topic_fields` | 解锁单条任意字段更新，最基础 |
| P0 | `batch_update_topics`(形态A) + `batch_update_fields` | 解锁批量调级，当前直接需求 |
| P1 | `list_topics` 增强（priority 过滤 + resonance 返回） | 评估环节需要 |
| P2 | `batch_update_topic_status`（带逐条状态机校验） | status 批量流转 |
| P2 | `batch_update_topics` 形态B（updates 列表） | 精细批改，按需 |

---

## 7. 边界与约定速查

- `priority`：CHAR(1)，取值 `A` / `B` / `C`，默认 `B`
- `resonance`：VARCHAR(10)，取值 `高` / `中` / `低`
- `status`：`draft` / `writing` / `published` / `archived`，流转见状态机，**写接口不碰**
- `title`：≤200 字符，非空
- 缓存键：`hermes:topic:{id}`，TTL 7 天
- embedding 文本：`f"{title} {angle}"`（有 angle）或 `title`
