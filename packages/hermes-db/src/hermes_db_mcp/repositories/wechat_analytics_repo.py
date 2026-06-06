from __future__ import annotations

from datetime import date
import json
from uuid import UUID, uuid4

import asyncpg


SNAPSHOT_COLUMNS_BASE = """
    snapshot_id, article_id, account, stat_date, window_label, source,
    read_user_count, average_stay_seconds, completion_rate,
    new_follow_user_count, share_user_count, wow_user_count, like_user_count,
    favorite_user_count, reward_cents, comment_count, delivered_user_count,
    account_message_read_user_count, first_share_user_count, total_share_user_count,
    share_generated_read_user_count, missing_fields, import_run_id,
    collected_at, created_at, updated_at
"""

SNAPSHOT_COLUMNS_WITH_RAW = f"{SNAPSHOT_COLUMNS_BASE}, raw_json"


def _jsonb(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _row(row: asyncpg.Record | None) -> dict | None:
    return dict(row) if row else None


async def _fetch(pool_or_conn, sql: str, *params):
    if hasattr(pool_or_conn, "acquire"):
        async with pool_or_conn.acquire() as conn:
            return await conn.fetch(sql, *params)
    return await pool_or_conn.fetch(sql, *params)


async def resolve_article(
    pool_or_conn,
    *,
    account: str,
    article_id: UUID | None = None,
    published_url: str | None = None,
    canonical_url: str | None = None,
    external_reference: str | None = None,
    ref_type: str | None = None,
    ref_value: str | None = None,
) -> dict:
    conditions = ["a.account = $1"]
    params: list = [account]
    idx = 2

    if article_id is not None:
        conditions.append(f"a.article_id = ${idx}")
        params.append(article_id)
        idx += 1
    if published_url:
        conditions.append(f"a.published_url = ${idx}")
        params.append(published_url)
        idx += 1
    if canonical_url:
        conditions.append(f"a.canonical_url = ${idx}")
        params.append(canonical_url)
        idx += 1
    if external_reference:
        conditions.append(f"a.external_reference = ${idx}")
        params.append(external_reference)
        idx += 1
    if ref_type and ref_value:
        conditions.append(
            f"""
            EXISTS (
                SELECT 1
                FROM hermes.wechat_article_external_refs r
                WHERE r.article_id = a.article_id
                  AND r.ref_type = ${idx}
                  AND r.ref_value = ${idx + 1}
                  AND r.superseded_at IS NULL
            )
            """
        )
        params.extend([ref_type, ref_value])

    if len(conditions) == 1:
        return {"status": "not_found", "items": []}

    sql = f"""
        SELECT a.article_id, a.account, a.title, a.published_url, a.canonical_url,
               a.external_reference, a.created_at, a.updated_at
        FROM hermes.wechat_articles a
        WHERE {" AND ".join(conditions)}
        LIMIT 2
    """
    rows = await _fetch(pool_or_conn, sql, *params)
    items = [dict(row) for row in rows]
    if not items:
        return {"status": "not_found", "items": []}
    if len(items) > 1:
        return {"status": "ambiguous", "items": items}
    return {"status": "matched", "article": items[0], "items": items}


async def create_import_run(
    conn,
    *,
    import_run_id: UUID | None = None,
    account: str,
    source: str,
    status: str,
    total_rows: int = 0,
    created: int = 0,
    updated: int = 0,
    skipped: int = 0,
    unmatched: list | None = None,
    errors: list | None = None,
    metadata: dict | None = None,
) -> dict:
    import_run_id = import_run_id or uuid4()
    row = await conn.fetchrow(
        """
        INSERT INTO hermes.analytics_import_runs (
            import_run_id, account, source, status, total_rows, created, updated,
            skipped, unmatched, errors, metadata
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING import_run_id, account, source, status, total_rows, created,
                  updated, skipped, unmatched, errors, metadata, created_at, updated_at
        """,
        import_run_id,
        account,
        source,
        status,
        total_rows,
        created,
        updated,
        skipped,
        _jsonb(unmatched or []),
        _jsonb(errors or []),
        _jsonb(metadata or {}),
    )
    return dict(row)


async def update_import_run(
    conn,
    *,
    import_run_id: UUID,
    status: str,
    total_rows: int,
    created: int,
    updated: int,
    skipped: int,
    unmatched: list | None = None,
    errors: list | None = None,
    metadata: dict | None = None,
) -> dict:
    row = await conn.fetchrow(
        """
        UPDATE hermes.analytics_import_runs
        SET status = $2,
            total_rows = $3,
            created = $4,
            updated = $5,
            skipped = $6,
            unmatched = $7,
            errors = $8,
            metadata = $9,
            updated_at = now()
        WHERE import_run_id = $1
        RETURNING import_run_id, account, source, status, total_rows, created,
                  updated, skipped, unmatched, errors, metadata, created_at, updated_at
        """,
        import_run_id,
        status,
        total_rows,
        created,
        updated,
        skipped,
        _jsonb(unmatched or []),
        _jsonb(errors or []),
        _jsonb(metadata or {}),
    )
    return dict(row)


def _snapshot_params(record: dict, import_run_id: UUID | None) -> list:
    return [
        record.get("snapshot_id") or uuid4(),
        record["article_id"],
        record["account"],
        record["stat_date"],
        record["window_label"],
        record["source"],
        record.get("read_user_count"),
        record.get("average_stay_seconds"),
        record.get("completion_rate"),
        record.get("new_follow_user_count"),
        record.get("share_user_count"),
        record.get("wow_user_count"),
        record.get("like_user_count"),
        record.get("favorite_user_count"),
        record.get("reward_cents"),
        record.get("comment_count"),
        record.get("delivered_user_count"),
        record.get("account_message_read_user_count"),
        record.get("first_share_user_count"),
        record.get("total_share_user_count"),
        record.get("share_generated_read_user_count"),
        record.get("missing_fields") or [],
        _jsonb(record.get("raw_json") or {}),
        import_run_id,
        record.get("collected_at"),
    ]


async def upsert_metric_snapshots(
    conn,
    rows: list[dict],
    *,
    import_run_id: UUID | None = None,
) -> dict:
    created = 0
    updated = 0
    for record in rows:
        row = await conn.fetchrow(
            """
            INSERT INTO hermes.wechat_article_metric_snapshots (
                snapshot_id, article_id, account, stat_date, window_label, source,
                read_user_count, average_stay_seconds, completion_rate,
                new_follow_user_count, share_user_count, wow_user_count, like_user_count,
                favorite_user_count, reward_cents, comment_count, delivered_user_count,
                account_message_read_user_count, first_share_user_count, total_share_user_count,
                share_generated_read_user_count, missing_fields, raw_json, import_run_id,
                collected_at
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
                $21, $22, $23, $24, $25
            )
            ON CONFLICT (article_id, stat_date, window_label, source) DO UPDATE SET
                account = EXCLUDED.account,
                read_user_count = EXCLUDED.read_user_count,
                average_stay_seconds = EXCLUDED.average_stay_seconds,
                completion_rate = EXCLUDED.completion_rate,
                new_follow_user_count = EXCLUDED.new_follow_user_count,
                share_user_count = EXCLUDED.share_user_count,
                wow_user_count = EXCLUDED.wow_user_count,
                like_user_count = EXCLUDED.like_user_count,
                favorite_user_count = EXCLUDED.favorite_user_count,
                reward_cents = EXCLUDED.reward_cents,
                comment_count = EXCLUDED.comment_count,
                delivered_user_count = EXCLUDED.delivered_user_count,
                account_message_read_user_count = EXCLUDED.account_message_read_user_count,
                first_share_user_count = EXCLUDED.first_share_user_count,
                total_share_user_count = EXCLUDED.total_share_user_count,
                share_generated_read_user_count = EXCLUDED.share_generated_read_user_count,
                missing_fields = EXCLUDED.missing_fields,
                raw_json = EXCLUDED.raw_json,
                import_run_id = EXCLUDED.import_run_id,
                collected_at = COALESCE(EXCLUDED.collected_at, hermes.wechat_article_metric_snapshots.collected_at),
                updated_at = now()
            RETURNING (xmax = 0) AS created
            """,
            *_snapshot_params(record, import_run_id),
        )
        if row["created"]:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated}


def _channel_params(record: dict, import_run_id: UUID | None) -> list:
    return [
        record.get("metric_id") or uuid4(),
        record["article_id"],
        record["account"],
        record["metric_date"],
        record["channel"],
        record["source"],
        record.get("read_user_count"),
        record.get("share_user_count"),
        _jsonb(record.get("raw_json") or {}),
        import_run_id,
    ]


async def upsert_channel_daily_metrics(
    conn,
    rows: list[dict],
    *,
    import_run_id: UUID | None = None,
) -> dict:
    created = 0
    updated = 0
    for record in rows:
        row = await conn.fetchrow(
            """
            INSERT INTO hermes.wechat_article_channel_daily_metrics (
                metric_id, article_id, account, metric_date, channel, source,
                read_user_count, share_user_count, raw_json, import_run_id
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (article_id, metric_date, channel, source) DO UPDATE SET
                account = EXCLUDED.account,
                read_user_count = EXCLUDED.read_user_count,
                share_user_count = EXCLUDED.share_user_count,
                raw_json = EXCLUDED.raw_json,
                import_run_id = EXCLUDED.import_run_id,
                updated_at = now()
            RETURNING (xmax = 0) AS created
            """,
            *_channel_params(record, import_run_id),
        )
        if row["created"]:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated}


async def list_metric_snapshots(
    pool: asyncpg.Pool,
    *,
    account: str | None = None,
    article_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    window_label: str | None = None,
    limit: int = 50,
    offset: int = 0,
    include_raw: bool = False,
) -> list[dict]:
    conditions = []
    params: list = []
    idx = 1
    for column, value in (
        ("account", account),
        ("article_id", article_id),
        ("window_label", window_label),
    ):
        if value is not None:
            conditions.append(f"{column} = ${idx}")
            params.append(value)
            idx += 1
    if date_from is not None:
        conditions.append(f"stat_date >= ${idx}")
        params.append(date_from)
        idx += 1
    if date_to is not None:
        conditions.append(f"stat_date <= ${idx}")
        params.append(date_to)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    columns = SNAPSHOT_COLUMNS_WITH_RAW if include_raw else SNAPSHOT_COLUMNS_BASE
    sql = f"""
        SELECT {columns}
        FROM hermes.wechat_article_metric_snapshots
        {where}
        ORDER BY stat_date DESC, updated_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *(params + [limit, offset]))
    return [dict(row) for row in rows]


async def run_import_transaction(
    pool: asyncpg.Pool,
    *,
    account: str,
    source: str,
    snapshot_rows: list[dict],
    channel_rows: list[dict] | None = None,
    skipped: int = 0,
    unmatched: list | None = None,
    errors: list | None = None,
    metadata: dict | None = None,
) -> dict:
    channel_rows = channel_rows or []
    unmatched = unmatched or []
    errors = errors or []
    metadata = metadata or {}
    status = "completed_with_errors" if skipped or unmatched or errors else "completed"

    async with pool.acquire() as conn:
        async with conn.transaction():
            import_run = await create_import_run(
                conn,
                account=account,
                source=source,
                status=status,
                total_rows=len(snapshot_rows),
                skipped=skipped,
                unmatched=unmatched,
                errors=errors,
                metadata=metadata,
            )
            snapshot_counts = await upsert_metric_snapshots(
                conn,
                snapshot_rows,
                import_run_id=import_run["import_run_id"],
            )
            channel_counts = await upsert_channel_daily_metrics(
                conn,
                channel_rows,
                import_run_id=import_run["import_run_id"],
            )
            created = snapshot_counts["created"]
            updated = snapshot_counts["updated"]
            import_run = await update_import_run(
                conn,
                import_run_id=import_run["import_run_id"],
                status=status,
                total_rows=len(snapshot_rows),
                created=created,
                updated=updated,
                skipped=skipped,
                unmatched=unmatched,
                errors=errors,
                metadata={
                    **metadata,
                    "channel_daily_metrics": channel_counts,
                },
            )
    return {
        **import_run,
        "created": created,
        "updated": updated,
        "channel_daily_metrics": channel_counts,
    }
