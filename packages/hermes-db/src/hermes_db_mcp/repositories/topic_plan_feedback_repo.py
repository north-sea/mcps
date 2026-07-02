from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import asyncpg


TOPIC_PLAN_FEEDBACK_EVENT_TYPES = frozenset(
    {
        "accepted",
        "rejected",
        "deferred",
        "archived",
        "written",
        "published",
        "score_adjusted",
    }
)

EVENT_PRECEDENCE = {
    "published": 6,
    "written": 5,
    "accepted": 4,
    "deferred": 3,
    "rejected": 2,
    "archived": 1,
    "score_adjusted": 0,
}

FEEDBACK_COLUMNS = """
    event_id, plan_id, account_id, track_id, event_type, dedupe_key,
    reason_tags, note, decided_by, topic_id, metadata, event_at, created_at
"""


def _json(value: object | None, *, default: object) -> str:
    return json.dumps(value if value is not None else default, ensure_ascii=False)


def _row(row) -> dict | None:
    return dict(row) if row else None


async def record_topic_plan_feedback(
    pool: asyncpg.Pool,
    *,
    plan_id: UUID,
    event_type: str,
    dedupe_key: str | None = None,
    reason_tags: list[str] | None = None,
    note: str | None = None,
    decided_by: str | None = None,
    topic_id: UUID | None = None,
    metadata: dict | None = None,
    event_at: datetime | None = None,
) -> dict | None:
    if event_type not in TOPIC_PLAN_FEEDBACK_EVENT_TYPES:
        raise ValueError(f"invalid topic plan feedback event_type: {event_type}")

    async with pool.acquire() as conn:
        async with conn.transaction():
            plan = await conn.fetchrow(
                """
                SELECT plan_id, account_id, track_id, source, llm_metadata
                FROM hermes.topic_plans
                WHERE plan_id = $1
                """,
                plan_id,
            )
            if not plan:
                return None

            row = await conn.fetchrow(
                f"""
                INSERT INTO hermes.topic_plan_feedback_events (
                    plan_id, account_id, track_id, event_type, dedupe_key,
                    reason_tags, note, decided_by, topic_id, metadata, event_at
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10::jsonb,
                    COALESCE($11, now())
                )
                ON CONFLICT (plan_id, event_type, dedupe_key)
                    WHERE dedupe_key IS NOT NULL
                DO NOTHING
                RETURNING {FEEDBACK_COLUMNS}
                """,
                plan_id,
                plan["account_id"],
                plan.get("track_id"),
                event_type,
                dedupe_key,
                _json(reason_tags, default=[]),
                note,
                decided_by,
                topic_id,
                _json(metadata, default={}),
                event_at,
            )
            if not row and dedupe_key is not None:
                row = await conn.fetchrow(
                    f"""
                    SELECT {FEEDBACK_COLUMNS}
                    FROM hermes.topic_plan_feedback_events
                    WHERE plan_id = $1
                      AND event_type = $2
                      AND dedupe_key = $3
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    plan_id,
                    event_type,
                    dedupe_key,
                )

    return _row(row)


async def list_topic_plan_feedback(
    pool: asyncpg.Pool,
    *,
    plan_id: UUID | None = None,
    account_id: str | None = None,
    track_id: str | None = None,
    event_type: str | None = None,
    event_from: datetime | None = None,
    event_to: datetime | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict], int]:
    if event_type is not None and event_type not in TOPIC_PLAN_FEEDBACK_EVENT_TYPES:
        raise ValueError(f"invalid topic plan feedback event_type: {event_type}")

    conditions = []
    params: list = []
    idx = 1
    for field, value in (
        ("plan_id", plan_id),
        ("account_id", account_id),
        ("track_id", track_id),
        ("event_type", event_type),
    ):
        if value is not None:
            conditions.append(f"{field} = ${idx}")
            params.append(value)
            idx += 1
    for field, op, value in (
        ("event_at", ">=", event_from),
        ("event_at", "<=", event_to),
        ("created_at", ">=", created_from),
        ("created_at", "<=", created_to),
    ):
        if value is not None:
            conditions.append(f"{field} {op} ${idx}")
            params.append(value)
            idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    count_sql = f"SELECT count(*) FROM hermes.topic_plan_feedback_events {where}"
    list_sql = f"""
        SELECT {FEEDBACK_COLUMNS}
        FROM hermes.topic_plan_feedback_events {where}
        ORDER BY event_at DESC, created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql, *params)
        rows = await conn.fetch(list_sql, *(params + [limit, offset]))
    return [dict(row) for row in rows], total


async def get_topic_plan_feedback_report(
    pool: asyncpg.Pool,
    *,
    account_id: str | None = None,
    track_id: str | None = None,
    window_days: int = 30,
    min_sample_size: int = 5,
) -> dict:
    conditions = [f"p.created_at >= now() - make_interval(days => $1::int)"]
    params: list = [window_days]
    idx = 2
    if account_id:
        conditions.append(f"p.account_id = ${idx}")
        params.append(account_id)
        idx += 1
    if track_id:
        conditions.append(f"p.track_id = ${idx}")
        params.append(track_id)
        idx += 1

    where = "WHERE " + " AND ".join(conditions)
    sql = f"""
        SELECT
            p.plan_id,
            p.account_id,
            p.track_id,
            p.status AS plan_status,
            p.source,
            p.llm_metadata,
            e.event_id,
            e.event_type,
            e.reason_tags,
            e.event_at,
            e.created_at AS event_created_at
        FROM hermes.topic_plans p
        LEFT JOIN hermes.topic_plan_feedback_events e
          ON e.plan_id = p.plan_id
         AND e.event_at >= now() - make_interval(days => $1::int)
        {where}
        ORDER BY p.created_at DESC, e.event_at DESC, e.created_at DESC
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    return _build_report(
        [dict(row) for row in rows],
        account_id=account_id,
        track_id=track_id,
        window_days=window_days,
        min_sample_size=min_sample_size,
    )


def _build_report(
    rows: list[dict],
    *,
    account_id: str | None,
    track_id: str | None,
    window_days: int,
    min_sample_size: int,
) -> dict:
    plans: dict[UUID, dict] = {}
    for row in rows:
        plan_id = row["plan_id"]
        plan = plans.setdefault(
            plan_id,
            {
                "account_id": row.get("account_id"),
                "track_id": row.get("track_id"),
                "status": row.get("plan_status"),
                "source": row.get("source") or "unknown_source",
                "config": _config_snapshot(row.get("llm_metadata")),
                "events": [],
            },
        )
        if row.get("event_id"):
            plan["events"].append(row)

    planned_count = len(plans)
    accepted_count = 0
    rejected_count = 0
    deferred_count = 0
    consumed_count = 0
    published_count = 0
    reason_tag_counts: dict[str, int] = {}
    source_groups: dict[str, dict] = {}
    runtime_groups: dict[str, dict] = {}
    track_config_groups: dict[str, dict] = {}

    for plan in plans.values():
        effective = _effective_event(plan["events"])
        effective_type = effective.get("event_type") if effective else None
        if effective_type in {"accepted", "written", "published"}:
            accepted_count += 1
        if effective_type == "rejected":
            rejected_count += 1
        if effective_type == "deferred":
            deferred_count += 1
        if plan["status"] == "consumed" or effective_type in {"written", "published"}:
            consumed_count += 1
        if effective_type == "published":
            published_count += 1
        for event in plan["events"]:
            if event.get("event_type") in {"rejected", "deferred"}:
                for tag in _json_array(event.get("reason_tags")):
                    reason_tag_counts[tag] = reason_tag_counts.get(tag, 0) + 1

        _add_group(source_groups, plan["source"], effective_type, plan["status"])
        config = plan["config"]
        _add_group(
            runtime_groups,
            config.get("runtime_version", "unknown_config"),
            effective_type,
            plan["status"],
        )
        _add_group(
            track_config_groups,
            config.get("track_config_hash", "unknown_config"),
            effective_type,
            plan["status"],
        )

    sample_warning = planned_count < min_sample_size
    return {
        "account_id": account_id,
        "track_id": track_id,
        "window_days": window_days,
        "planned_count": planned_count,
        "accepted_count": accepted_count,
        "rejected_count": rejected_count,
        "deferred_count": deferred_count,
        "consumed_count": consumed_count,
        "published_count": published_count,
        "acceptance_rate": _rate(accepted_count, planned_count),
        "consume_rate": _rate(consumed_count, planned_count),
        "publish_rate": _rate(published_count, planned_count),
        "reason_tag_counts": reason_tag_counts,
        "by_source": _finalize_groups(source_groups, min_sample_size),
        "by_runtime_version": _finalize_groups(runtime_groups, min_sample_size),
        "by_track_config_hash": _finalize_groups(track_config_groups, min_sample_size),
        "sample_warning": sample_warning,
        "min_sample_size": min_sample_size,
    }


def _effective_event(events: list[dict]) -> dict | None:
    lifecycle_events = [
        event for event in events if EVENT_PRECEDENCE.get(event.get("event_type"), 0) > 0
    ]
    if not lifecycle_events:
        return None
    return max(
        lifecycle_events,
        key=lambda event: (
            EVENT_PRECEDENCE[event["event_type"]],
            event.get("event_at") or datetime.min,
            event.get("event_created_at") or datetime.min,
        ),
    )


def _config_snapshot(value: object) -> dict:
    metadata = _json_object(value)
    snapshot = metadata.get("config_snapshot")
    return snapshot if isinstance(snapshot, dict) else {}


def _add_group(
    groups: dict[str, dict],
    key: str,
    effective_type: str | None,
    plan_status: str | None,
) -> None:
    group = groups.setdefault(
        key or "unknown_config",
        {
            "key": key or "unknown_config",
            "planned_count": 0,
            "accepted_count": 0,
            "consumed_count": 0,
            "published_count": 0,
        },
    )
    group["planned_count"] += 1
    if effective_type in {"accepted", "written", "published"}:
        group["accepted_count"] += 1
    if plan_status == "consumed" or effective_type in {"written", "published"}:
        group["consumed_count"] += 1
    if effective_type == "published":
        group["published_count"] += 1


def _finalize_groups(groups: dict[str, dict], min_sample_size: int) -> list[dict]:
    result = []
    for group in groups.values():
        planned_count = group["planned_count"]
        result.append(
            {
                **group,
                "acceptance_rate": _rate(group["accepted_count"], planned_count),
                "consume_rate": _rate(group["consumed_count"], planned_count),
                "publish_rate": _rate(group["published_count"], planned_count),
                "sample_warning": planned_count < min_sample_size,
            }
        )
    return sorted(result, key=lambda item: item["key"])


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _json_array(value: object) -> list:
    decoded = _decode_json_value(value, [])
    return decoded if isinstance(decoded, list) else []


def _json_object(value: object) -> dict:
    decoded = _decode_json_value(value, {})
    return decoded if isinstance(decoded, dict) else {}


def _decode_json_value(value: object, fallback: object) -> object:
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value
