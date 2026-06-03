from __future__ import annotations

from datetime import datetime
import json
from uuid import UUID, uuid4

import asyncpg


ARTICLE_COLUMNS = """
    article_id, publication_idempotency_key, account, topic_id, run_id, task_id,
    draft_artifact_id, published_artifact_id, publish_artifact_id, status,
    dry_run, title, published_url, canonical_url, publish_target,
    external_reference, metadata, published_at, created_at, updated_at
"""

REF_COLUMNS = """
    ref_id, article_id, ref_type, ref_value, ref_source, is_primary, metadata,
    superseded_at, created_at, updated_at
"""


def _row(row: asyncpg.Record | None) -> dict | None:
    return dict(row) if row else None


def _jsonb(value) -> str:
    return json.dumps(value, ensure_ascii=False)


async def upsert_article(
    pool: asyncpg.Pool,
    *,
    publication_idempotency_key: str,
    account: str,
    run_id: str,
    status: str,
    topic_id: UUID | None = None,
    task_id: str | None = None,
    draft_artifact_id: str | None = None,
    published_artifact_id: str | None = None,
    publish_artifact_id: str | None = None,
    dry_run: bool = False,
    title: str | None = None,
    published_url: str | None = None,
    canonical_url: str | None = None,
    publish_target: str | None = None,
    external_reference: str | None = None,
    metadata: dict | None = None,
    published_at: datetime | None = None,
) -> tuple[dict, bool]:
    sql = f"""
        INSERT INTO hermes.wechat_articles (
            article_id, publication_idempotency_key, account, topic_id, run_id, task_id,
            draft_artifact_id, published_artifact_id, publish_artifact_id,
            status, dry_run, title, published_url, canonical_url,
            publish_target, external_reference, metadata, published_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
        ON CONFLICT (account, publication_idempotency_key) DO UPDATE SET
            topic_id = COALESCE(EXCLUDED.topic_id, hermes.wechat_articles.topic_id),
            run_id = EXCLUDED.run_id,
            task_id = COALESCE(EXCLUDED.task_id, hermes.wechat_articles.task_id),
            draft_artifact_id = COALESCE(EXCLUDED.draft_artifact_id, hermes.wechat_articles.draft_artifact_id),
            published_artifact_id = COALESCE(EXCLUDED.published_artifact_id, hermes.wechat_articles.published_artifact_id),
            publish_artifact_id = COALESCE(EXCLUDED.publish_artifact_id, hermes.wechat_articles.publish_artifact_id),
            status = EXCLUDED.status,
            dry_run = EXCLUDED.dry_run,
            title = COALESCE(EXCLUDED.title, hermes.wechat_articles.title),
            published_url = COALESCE(EXCLUDED.published_url, hermes.wechat_articles.published_url),
            canonical_url = COALESCE(EXCLUDED.canonical_url, hermes.wechat_articles.canonical_url),
            publish_target = COALESCE(EXCLUDED.publish_target, hermes.wechat_articles.publish_target),
            external_reference = COALESCE(EXCLUDED.external_reference, hermes.wechat_articles.external_reference),
            metadata = EXCLUDED.metadata,
            published_at = COALESCE(EXCLUDED.published_at, hermes.wechat_articles.published_at),
            updated_at = now()
        RETURNING {ARTICLE_COLUMNS}, (xmax = 0) AS created
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            sql,
            uuid4(),
            publication_idempotency_key,
            account,
            topic_id,
            run_id,
            task_id,
            draft_artifact_id,
            published_artifact_id,
            publish_artifact_id,
            status,
            dry_run,
            title,
            published_url,
            canonical_url,
            publish_target,
            external_reference,
            _jsonb(metadata or {}),
            published_at,
        )
    result = dict(row)
    return result, bool(result.pop("created"))


async def list_articles(
    pool: asyncpg.Pool,
    *,
    account: str | None = None,
    topic_id: UUID | None = None,
    run_id: str | None = None,
    status: str | None = None,
    publish_target: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = []
    params: list = []
    idx = 1
    for column, value in (
        ("account", account),
        ("topic_id", topic_id),
        ("run_id", run_id),
        ("status", status),
        ("publish_target", publish_target),
    ):
        if value is not None:
            conditions.append(f"{column} = ${idx}")
            params.append(value)
            idx += 1
    if date_from is not None:
        conditions.append(f"created_at >= ${idx}")
        params.append(date_from)
        idx += 1
    if date_to is not None:
        conditions.append(f"created_at <= ${idx}")
        params.append(date_to)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""
        SELECT {ARTICLE_COLUMNS}
        FROM hermes.wechat_articles
        {where}
        ORDER BY created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *(params + [limit, offset]))
    return [dict(row) for row in rows]


async def get_article(pool: asyncpg.Pool, *, article_id: UUID) -> dict | None:
    sql = f"""
        SELECT {ARTICLE_COLUMNS}
        FROM hermes.wechat_articles
        WHERE article_id = $1
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, article_id)
    return _row(row)


async def list_article_refs(pool: asyncpg.Pool, *, article_id: UUID) -> list[dict]:
    sql = f"""
        SELECT {REF_COLUMNS}
        FROM hermes.wechat_article_external_refs
        WHERE article_id = $1
        ORDER BY created_at DESC
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, article_id)
    return [dict(row) for row in rows]


async def insert_or_update_external_refs(
    conn,
    *,
    article_id: UUID,
    refs: list[dict],
) -> list[dict]:
    rows = []
    for ref in refs:
        ref_type = ref["ref_type"]
        ref_value = ref["ref_value"].strip()
        existing = await conn.fetchrow(
            f"""
            SELECT {REF_COLUMNS}
            FROM hermes.wechat_article_external_refs
            WHERE ref_type = $1 AND ref_value = $2 AND superseded_at IS NULL
            """,
            ref_type,
            ref_value,
        )
        if existing and existing["article_id"] != article_id:
            raise ValueError("external_ref_conflict")
        if existing:
            row = await conn.fetchrow(
                f"""
                UPDATE hermes.wechat_article_external_refs
                SET ref_source = COALESCE($3, ref_source),
                    is_primary = $4,
                    metadata = $5,
                    updated_at = now()
                WHERE ref_id = $1 AND article_id = $2
                RETURNING {REF_COLUMNS}
                """,
                existing["ref_id"],
                article_id,
                ref.get("ref_source"),
                bool(ref.get("is_primary", existing.get("is_primary", False))),
                _jsonb(ref.get("metadata") or {}),
            )
            rows.append(dict(row))
            continue
        row = await conn.fetchrow(
            f"""
            INSERT INTO hermes.wechat_article_external_refs (
                ref_id, article_id, ref_type, ref_value, ref_source, is_primary, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING {REF_COLUMNS}
            """,
            uuid4(),
            article_id,
            ref_type,
            ref_value,
            ref.get("ref_source"),
            bool(ref.get("is_primary", False)),
            _jsonb(ref.get("metadata") or {}),
        )
        rows.append(dict(row))
    return rows


async def patch_article_refs_and_summary(
    pool: asyncpg.Pool,
    *,
    article_id: UUID,
    refs: list[dict] | None = None,
    patch: dict | None = None,
) -> tuple[dict | None, list[dict]]:
    refs = refs or []
    patch = patch or {}
    async with pool.acquire() as conn:
        async with conn.transaction():
            article = await conn.fetchrow(
                f"SELECT {ARTICLE_COLUMNS} FROM hermes.wechat_articles WHERE article_id = $1",
                article_id,
            )
            if article is None:
                return None, []

            if patch:
                assignments = []
                params = []
                idx = 1
                for field in (
                    "published_url",
                    "canonical_url",
                    "external_reference",
                    "status",
                    "published_at",
                    "metadata",
                ):
                    if field in patch:
                        assignments.append(f"{field} = ${idx}")
                        value = _jsonb(patch[field]) if field == "metadata" else patch[field]
                        params.append(value)
                        idx += 1
                assignments.append("updated_at = now()")
                sql = f"""
                    UPDATE hermes.wechat_articles
                    SET {", ".join(assignments)}
                    WHERE article_id = ${idx}
                    RETURNING {ARTICLE_COLUMNS}
                """
                article = await conn.fetchrow(sql, *(params + [article_id]))

            ref_rows = await insert_or_update_external_refs(conn, article_id=article_id, refs=refs)
    return dict(article), ref_rows
