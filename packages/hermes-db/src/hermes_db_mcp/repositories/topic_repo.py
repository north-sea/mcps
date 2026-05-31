from uuid import UUID

import asyncpg
from pgvector.asyncpg import register_vector


async def ensure_vector_type(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await register_vector(conn)


async def insert_topic(
    pool: asyncpg.Pool,
    *,
    title: str,
    account: str,
    angle: str | None = None,
    priority: str = "B",
    column_name: str | None = None,
    resonance: str | None = None,
    content: str | None = None,
    source: str = "topic-inbox",
    embedding: list[float] | None = None,
) -> dict:
    sql = """
        INSERT INTO hermes.topics (title, angle, account, priority, column_name, resonance, content, source, embedding)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, status, created_at
    """
    async with pool.acquire() as conn:
        await register_vector(conn)
        row = await conn.fetchrow(
            sql,
            title,
            angle,
            account,
            priority,
            column_name,
            resonance,
            content,
            source,
            embedding,
        )
    return dict(row)


async def find_similar(
    pool: asyncpg.Pool,
    *,
    embedding: list[float],
    account: str | None = None,
    threshold: float = 0.85,
    limit: int = 5,
) -> list[dict]:
    conditions = [
        "embedding IS NOT NULL",
        "(status != 'published' OR updated_at >= now() - interval '3 months')",
    ]
    params: list = [embedding, threshold, limit]
    idx = 4

    if account:
        conditions.append(f"account = ${idx}")
        params.append(account)
        idx += 1

    where = " AND ".join(conditions)
    sql = f"""
        SELECT id, title, account, status, created_at,
               1 - (embedding <=> $1) AS similarity
        FROM hermes.topics
        WHERE {where} AND 1 - (embedding <=> $1) >= $2
        ORDER BY similarity DESC
        LIMIT $3
    """
    async with pool.acquire() as conn:
        await register_vector(conn)
        rows = await conn.fetch(sql, *params)
    return [dict(r) for r in rows]


async def update_status(
    pool: asyncpg.Pool, *, topic_id: UUID, new_status: str
) -> dict | None:
    sql = """
        UPDATE hermes.topics SET status = $1 WHERE id = $2
        RETURNING id, status, updated_at
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, new_status, topic_id)
    return dict(row) if row else None


async def publish(
    pool: asyncpg.Pool, *, topic_id: UUID, published_url: str
) -> dict | None:
    sql = """
        UPDATE hermes.topics SET status = 'published', published_url = $1 WHERE id = $2
        RETURNING id, status, published_url, updated_at
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, published_url, topic_id)
    return dict(row) if row else None


async def get_by_id(pool: asyncpg.Pool, *, topic_id: UUID) -> dict | None:
    sql = """
        SELECT id, title, angle, account, status, priority, column_name,
               resonance, content, source, published_url, created_at, updated_at
        FROM hermes.topics WHERE id = $1
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, topic_id)
    return dict(row) if row else None


async def list_by_filter(
    pool: asyncpg.Pool,
    *,
    account: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    exclude_published: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """
    T007: 增强列表查询,支持 priority 过滤和 exclude_published,
    返回项包含运营字段 resonance/column_name
    """
    conditions = []
    params: list = []
    idx = 1

    if account:
        conditions.append(f"account = ${idx}")
        params.append(account)
        idx += 1
    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1
    if priority:
        conditions.append(f"priority = ${idx}")
        params.append(priority)
        idx += 1
    if exclude_published:
        conditions.append("status != 'published'")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    count_sql = f"SELECT count(*) FROM hermes.topics {where}"
    list_sql = f"""
        SELECT id, title, angle, account, status, priority,
               resonance, column_name, created_at
        FROM hermes.topics {where}
        ORDER BY created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    params_with_pagination = params + [limit, offset]

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql, *params)
        rows = await conn.fetch(list_sql, *params_with_pagination)
    return [dict(r) for r in rows], total


async def update_topic_fields(
    pool: asyncpg.Pool,
    *,
    topic_id: UUID,
    fields: dict[str, any],
    embedding: list[float] | None | object = ...,
) -> dict | None:
    """
    T005: 动态部分更新 topic 字段

    Args:
        pool: 数据库连接池
        topic_id: topic UUID
        fields: 要更新的字段字典,键必须在 EDITABLE_TOPIC_FIELDS 白名单中
        embedding: 可选 embedding 更新
            - ... (Ellipsis): 不更新 embedding
            - None: 将 embedding 设为 NULL
            - list[float]: 更新为新向量

    Returns:
        更新后的完整 topic 行,字段集与 get_by_id 一致;若 topic 不存在返回 None
    """
    from hermes_db_mcp.contracts import EDITABLE_TOPIC_FIELDS

    # 字段白名单校验
    invalid = set(fields.keys()) - EDITABLE_TOPIC_FIELDS
    if invalid:
        raise ValueError(f"不可编辑字段: {invalid}")

    if not fields and embedding is ...:
        raise ValueError("未提供任何可更新字段")

    # 构造动态 SET 子句
    set_clauses = []
    params: list = []
    idx = 1

    for key, value in fields.items():
        set_clauses.append(f"{key} = ${idx}")
        params.append(value)
        idx += 1

    # 处理 embedding
    if embedding is not ...:
        set_clauses.append(f"embedding = ${idx}")
        params.append(embedding)
        idx += 1

    params.append(topic_id)

    sql = f"""
        UPDATE hermes.topics
        SET {", ".join(set_clauses)}
        WHERE id = ${idx}
        RETURNING id, title, angle, account, status, priority, column_name,
                  resonance, content, source, published_url, created_at, updated_at
    """

    async with pool.acquire() as conn:
        if embedding is not ...:
            await register_vector(conn)
        row = await conn.fetchrow(sql, *params)

    return dict(row) if row else None


async def batch_update_fields(
    pool: asyncpg.Pool,
    *,
    topic_ids: list[UUID],
    fields: dict[str, any],
) -> list[UUID]:
    """
    T006: 批量更新 topic 运营字段

    Args:
        pool: 数据库连接池
        topic_ids: topic UUID 列表(已去重)
        fields: 要更新的字段字典,键必须在 BULK_TOPIC_FIELDS 白名单中

    Returns:
        实际更新的 topic id 列表
    """
    from hermes_db_mcp.contracts import BULK_TOPIC_FIELDS

    # 字段白名单校验
    invalid = set(fields.keys()) - BULK_TOPIC_FIELDS
    if invalid:
        raise ValueError(f"批量更新不支持字段: {invalid}")

    if not fields:
        raise ValueError("未提供任何可更新字段")

    if not topic_ids:
        return []

    # 构造动态 SET 子句
    set_clauses = []
    params: list = []
    idx = 1

    for key, value in fields.items():
        set_clauses.append(f"{key} = ${idx}")
        params.append(value)
        idx += 1

    params.append(topic_ids)

    sql = f"""
        UPDATE hermes.topics
        SET {", ".join(set_clauses)}
        WHERE id = ANY(${idx})
        RETURNING id
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    return [row["id"] for row in rows]
