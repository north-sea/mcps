from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import asyncpg


def _json(value: object | None) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


async def sync_track_config(
    pool: asyncpg.Pool,
    *,
    accounts: list[dict],
    tracks: list[dict],
) -> dict:
    account_sql = """
        INSERT INTO hermes.topic_candidate_accounts (
            account_id, display_name, enabled, draft_target, metadata
        )
        VALUES ($1, $2, $3, $4, $5::jsonb)
        ON CONFLICT (account_id)
        DO UPDATE SET
            display_name = EXCLUDED.display_name,
            enabled = EXCLUDED.enabled,
            draft_target = EXCLUDED.draft_target,
            metadata = EXCLUDED.metadata,
            updated_at = now()
    """
    track_sql = """
        INSERT INTO hermes.topic_candidate_tracks (
            account_id, track_id, name, keywords, negative_keywords, sources,
            scoring_profile, daily_quota, enabled
        )
        VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7::jsonb, $8, $9)
        ON CONFLICT (account_id, track_id)
        DO UPDATE SET
            name = EXCLUDED.name,
            keywords = EXCLUDED.keywords,
            negative_keywords = EXCLUDED.negative_keywords,
            sources = EXCLUDED.sources,
            scoring_profile = EXCLUDED.scoring_profile,
            daily_quota = EXCLUDED.daily_quota,
            enabled = EXCLUDED.enabled,
            updated_at = now()
    """
    account_ids: list[str] = []
    track_ids: list[str] = []

    async with pool.acquire() as conn:
        async with conn.transaction():
            for account in accounts:
                await conn.execute(
                    account_sql,
                    account["account_id"],
                    account["display_name"],
                    account["enabled"],
                    account.get("draft_target"),
                    _json(account.get("metadata")),
                )
                account_ids.append(account["account_id"])

            for track in tracks:
                await conn.execute(
                    track_sql,
                    track["account_id"],
                    track["track_id"],
                    track["name"],
                    _json(track["keywords"]),
                    _json(track["negative_keywords"]),
                    _json(track["sources"]),
                    _json(track["scoring_profile"]),
                    track.get("daily_quota"),
                    track["enabled"],
                )
                track_ids.append(f"{track['account_id']}:{track['track_id']}")

    return {
        "accounts_upserted": len(account_ids),
        "tracks_upserted": len(track_ids),
        "account_ids": account_ids,
        "track_ids": track_ids,
    }


async def upsert_candidate(
    pool: asyncpg.Pool,
    *,
    account_id: str,
    track_id: str,
    source: str,
    source_url: str | None,
    source_item_id: str | None,
    title: str,
    summary: str | None,
    hot_score: float | None,
    fit_score: float | None,
    novelty_score: float | None,
    dedupe_key: str,
    captured_at: datetime,
    raw_payload: dict | None = None,
) -> dict:
    sql = """
        INSERT INTO hermes.topic_candidates (
            account_id, track_id, source, source_url, source_item_id,
            title, summary, hot_score, fit_score, novelty_score,
            dedupe_key, captured_at, raw_payload
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb)
        ON CONFLICT (account_id, track_id, dedupe_key)
        DO UPDATE SET
            source = EXCLUDED.source,
            source_url = EXCLUDED.source_url,
            source_item_id = EXCLUDED.source_item_id,
            title = EXCLUDED.title,
            summary = EXCLUDED.summary,
            hot_score = EXCLUDED.hot_score,
            fit_score = EXCLUDED.fit_score,
            novelty_score = EXCLUDED.novelty_score,
            captured_at = EXCLUDED.captured_at,
            raw_payload = EXCLUDED.raw_payload,
            updated_at = now()
        RETURNING id, status, created_at, updated_at, (xmax = 0) AS created
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            sql,
            account_id,
            track_id,
            source,
            source_url,
            source_item_id,
            title,
            summary,
            hot_score,
            fit_score,
            novelty_score,
            dedupe_key,
            captured_at,
            _json(raw_payload),
        )
    return dict(row)


async def list_candidates(
    pool: asyncpg.Pool,
    *,
    account_id: str | None = None,
    track_id: str | None = None,
    status: str | None = None,
    source: str | None = None,
    limit: int = 20,
    offset: int = 0,
    include_raw: bool = False,
) -> tuple[list[dict], int]:
    conditions = []
    params: list = []
    idx = 1

    if account_id:
        conditions.append(f"account_id = ${idx}")
        params.append(account_id)
        idx += 1
    if track_id:
        conditions.append(f"track_id = ${idx}")
        params.append(track_id)
        idx += 1
    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1
    else:
        conditions.append("status NOT IN ('rejected', 'expired')")
    if source:
        conditions.append(f"source = ${idx}")
        params.append(source)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    raw_column = ", raw_payload" if include_raw else ""
    count_sql = f"SELECT count(*) FROM hermes.topic_candidates {where}"
    list_sql = f"""
        SELECT id, account_id, track_id, source, source_url, source_item_id,
               title, summary, hot_score, fit_score, novelty_score, status,
               dedupe_key, captured_at, topic_id, created_at, updated_at
               {raw_column}
        FROM hermes.topic_candidates {where}
        ORDER BY captured_at DESC, created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql, *params)
        rows = await conn.fetch(list_sql, *(params + [limit, offset]))
    return [dict(row) for row in rows], total


async def get_candidate(
    pool_or_conn,
    *,
    candidate_id: UUID,
    include_raw: bool = False,
) -> dict | None:
    raw_column = ", raw_payload" if include_raw else ""
    sql = """
        SELECT id, account_id, track_id, source, source_url, source_item_id,
               title, summary, hot_score, fit_score, novelty_score, status,
               dedupe_key, captured_at, topic_id, created_at, updated_at
               {raw_column}
        FROM hermes.topic_candidates
        WHERE id = $1
    """.format(raw_column=raw_column)
    if hasattr(pool_or_conn, "fetchrow"):
        row = await pool_or_conn.fetchrow(sql, candidate_id)
        return dict(row) if row else None

    async with pool_or_conn.acquire() as conn:
        row = await conn.fetchrow(sql, candidate_id)
    return dict(row) if row else None


async def update_status(
    pool: asyncpg.Pool,
    *,
    candidate_id: UUID,
    new_status: str,
    rejection_reason: str | None = None,
) -> dict | None:
    sql = """
        UPDATE hermes.topic_candidates
        SET status = $1,
            rejection_reason = COALESCE($3, rejection_reason),
            status_updated_at = now(),
            updated_at = now()
        WHERE id = $2
        RETURNING id, status, topic_id, updated_at
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, new_status, candidate_id, rejection_reason)
    return dict(row) if row else None


async def expire_candidates(
    pool: asyncpg.Pool,
    *,
    account_id: str | None = None,
    track_id: str | None = None,
    captured_before: datetime | None = None,
    limit: int = 100,
) -> list[UUID]:
    conditions = ["status IN ('new', 'shortlisted')"]
    params: list = []
    idx = 1
    if account_id:
        conditions.append(f"account_id = ${idx}")
        params.append(account_id)
        idx += 1
    if track_id:
        conditions.append(f"track_id = ${idx}")
        params.append(track_id)
        idx += 1
    if captured_before:
        conditions.append(f"captured_at < ${idx}")
        params.append(captured_before)
        idx += 1

    sql = f"""
        WITH selected AS (
            SELECT id
            FROM hermes.topic_candidates
            WHERE {" AND ".join(conditions)}
            ORDER BY captured_at ASC
            LIMIT ${idx}
        )
        UPDATE hermes.topic_candidates candidate
        SET status = 'expired',
            status_updated_at = now(),
            updated_at = now()
        FROM selected
        WHERE candidate.id = selected.id
        RETURNING candidate.id
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *(params + [limit]))
    return [row["id"] for row in rows]


async def list_tracks(
    pool: asyncpg.Pool,
    *,
    account_id: str | None = None,
    enabled: bool | None = None,
) -> tuple[list[dict], list[dict]]:
    account_conditions = []
    track_conditions = []
    params: list = []
    idx = 1
    if account_id:
        account_conditions.append(f"account_id = ${idx}")
        track_conditions.append(f"account_id = ${idx}")
        params.append(account_id)
        idx += 1
    if enabled is not None:
        account_conditions.append(f"enabled = ${idx}")
        track_conditions.append(f"enabled = ${idx}")
        params.append(enabled)

    account_where = (
        "WHERE " + " AND ".join(account_conditions) if account_conditions else ""
    )
    track_where = "WHERE " + " AND ".join(track_conditions) if track_conditions else ""
    account_sql = f"""
        SELECT account_id, display_name, enabled, draft_target
        FROM hermes.topic_candidate_accounts {account_where}
        ORDER BY account_id
    """
    track_sql = f"""
        SELECT account_id, track_id, name, keywords, negative_keywords, sources,
               scoring_profile, daily_quota, enabled
        FROM hermes.topic_candidate_tracks {track_where}
        ORDER BY account_id, track_id
    """
    async with pool.acquire() as conn:
        accounts = await conn.fetch(account_sql, *params)
        tracks = await conn.fetch(track_sql, *params)
    return [dict(row) for row in accounts], [dict(row) for row in tracks]


async def adopt_candidate(
    pool: asyncpg.Pool,
    *,
    candidate_id: UUID,
    title: str | None = None,
    angle: str | None = None,
    priority: str = "B",
    column_name: str | None = None,
    resonance: str | None = None,
    content: str | None = None,
) -> dict | None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            candidate = await get_candidate(conn, candidate_id=candidate_id)
            if not candidate:
                return None
            if candidate["status"] == "adopted" and candidate.get("topic_id"):
                return {
                    "candidate": candidate,
                    "topic_id": candidate["topic_id"],
                    "created": False,
                }

            topic_row = await conn.fetchrow(
                """
                INSERT INTO hermes.topics (
                    title, angle, account, priority, column_name, resonance,
                    content, source
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, status, created_at
                """,
                title or candidate["title"],
                angle,
                candidate["account_id"],
                priority,
                column_name,
                resonance,
                content,
                f"topic-candidate:{candidate_id}",
            )
            updated = await conn.fetchrow(
                """
                UPDATE hermes.topic_candidates
                SET status = 'adopted',
                    topic_id = $2,
                    adopted_at = now(),
                    status_updated_at = now(),
                    updated_at = now()
                WHERE id = $1
                RETURNING id, status, topic_id, updated_at
                """,
                candidate_id,
                topic_row["id"],
            )
            return {
                "candidate": candidate,
                "updated": dict(updated),
                "topic_id": topic_row["id"],
                "created": True,
            }
