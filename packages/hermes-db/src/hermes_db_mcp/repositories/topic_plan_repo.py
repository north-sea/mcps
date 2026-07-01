from __future__ import annotations

import json
from uuid import UUID

import asyncpg


TOPIC_PLAN_TRANSITIONS: dict[str, list[str]] = {
    "planned": ["consumed", "archived"],
    "rejected": ["archived"],
    "consumed": ["archived"],
    "archived": [],
}


class TopicPlanShortlistConflict(Exception):
    def __init__(self, candidate_id: UUID):
        super().__init__(f"candidate {candidate_id} could not be shortlisted")
        self.candidate_id = candidate_id


class TopicPlanInvalidTransition(Exception):
    def __init__(self, current: str, target: str, allowed: list[str]):
        super().__init__(f"invalid topic plan transition: {current} -> {target}")
        self.current = current
        self.target = target
        self.allowed = allowed


def _json(value: object | None, *, default: object) -> str:
    return json.dumps(value if value is not None else default, ensure_ascii=False)


def _row(row) -> dict | None:
    return dict(row) if row else None


PLAN_COLUMNS = """
    plan_id, candidate_id, account_id, track_id, status,
    recommended_angle_index, topic_angles, outline_pack, writing_brief,
    image_brief, evidence, llm_metadata, rejection_reason, topic_id, source,
    created_at, updated_at, consumed_at
"""


async def upsert_topic_plan(
    pool: asyncpg.Pool,
    *,
    candidate_id: UUID,
    account_id: str,
    status: str,
    track_id: str | None = None,
    recommended_angle_index: int | None = None,
    topic_angles: list[dict] | None = None,
    outline_pack: dict | None = None,
    writing_brief: dict | None = None,
    image_brief: dict | None = None,
    evidence: dict | list | None = None,
    llm_metadata: dict | None = None,
    rejection_reason: str | None = None,
    topic_id: UUID | None = None,
    source: str | None = None,
    mark_candidate_shortlisted: bool = False,
) -> dict:
    sql = f"""
        INSERT INTO hermes.topic_plans (
            candidate_id, account_id, track_id, status, recommended_angle_index,
            topic_angles, outline_pack, writing_brief, image_brief, evidence,
            llm_metadata, rejection_reason, topic_id, source
        )
        VALUES (
            $1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8::jsonb, $9::jsonb,
            $10::jsonb, $11::jsonb, $12, $13, $14
        )
        ON CONFLICT (candidate_id)
        DO UPDATE SET
            account_id = EXCLUDED.account_id,
            track_id = EXCLUDED.track_id,
            status = EXCLUDED.status,
            recommended_angle_index = EXCLUDED.recommended_angle_index,
            topic_angles = EXCLUDED.topic_angles,
            outline_pack = EXCLUDED.outline_pack,
            writing_brief = EXCLUDED.writing_brief,
            image_brief = EXCLUDED.image_brief,
            evidence = EXCLUDED.evidence,
            llm_metadata = EXCLUDED.llm_metadata,
            rejection_reason = EXCLUDED.rejection_reason,
            topic_id = EXCLUDED.topic_id,
            source = EXCLUDED.source,
            updated_at = now(),
            consumed_at = CASE
                WHEN EXCLUDED.status = 'consumed' THEN COALESCE(hermes.topic_plans.consumed_at, now())
                ELSE hermes.topic_plans.consumed_at
            END
        RETURNING {PLAN_COLUMNS}, (xmax = 0) AS created
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                sql,
                candidate_id,
                account_id,
                track_id,
                status,
                recommended_angle_index,
                _json(topic_angles, default=[]),
                _json(outline_pack, default={}),
                _json(writing_brief, default={}),
                _json(image_brief, default={}),
                _json(evidence, default={}),
                _json(llm_metadata, default={}),
                rejection_reason,
                topic_id,
                source,
            )
            if mark_candidate_shortlisted and status == "planned":
                updated = await conn.fetchrow(
                    """
                    UPDATE hermes.topic_candidates
                    SET status = 'shortlisted',
                        status_updated_at = now(),
                        updated_at = now()
                    WHERE id = $1
                      AND status IN ('new', 'shortlisted')
                    RETURNING id, status
                    """,
                    candidate_id,
                )
                if not updated:
                    raise TopicPlanShortlistConflict(candidate_id)

    item = dict(row)
    created = item.pop("created")
    return {"upserted": "created" if created else "updated", "item": item}


async def list_topic_plans(
    pool: asyncpg.Pool,
    *,
    account_id: str | None = None,
    track_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
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

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    count_sql = f"SELECT count(*) FROM hermes.topic_plans {where}"
    list_sql = f"""
        SELECT {PLAN_COLUMNS}
        FROM hermes.topic_plans {where}
        ORDER BY created_at DESC, updated_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql, *params)
        rows = await conn.fetch(list_sql, *(params + [limit, offset]))
    return [dict(row) for row in rows], total


async def get_topic_plan(pool: asyncpg.Pool, *, plan_id: UUID) -> dict | None:
    sql = f"""
        SELECT {PLAN_COLUMNS}
        FROM hermes.topic_plans
        WHERE plan_id = $1
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, plan_id)
    return _row(row)


async def update_topic_plan_status(
    pool: asyncpg.Pool,
    *,
    plan_id: UUID,
    status: str,
    topic_id: UUID | None = None,
) -> dict | None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            current = await conn.fetchrow(
                "SELECT status FROM hermes.topic_plans WHERE plan_id = $1",
                plan_id,
            )
            if not current:
                return None
            allowed = TOPIC_PLAN_TRANSITIONS.get(current["status"], [])
            if status not in allowed:
                raise TopicPlanInvalidTransition(current["status"], status, allowed)
            row = await conn.fetchrow(
                f"""
                UPDATE hermes.topic_plans
                SET status = $2,
                    topic_id = COALESCE($3, topic_id),
                    consumed_at = CASE
                        WHEN $2 = 'consumed' THEN COALESCE(consumed_at, now())
                        ELSE consumed_at
                    END,
                    updated_at = now()
                WHERE plan_id = $1
                RETURNING {PLAN_COLUMNS}
                """,
                plan_id,
                status,
                topic_id,
            )
    item = dict(row)
    item["previous_status"] = current["status"]
    return item
