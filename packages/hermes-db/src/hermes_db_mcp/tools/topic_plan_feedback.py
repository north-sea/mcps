from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.contracts import error, validate_pagination
from hermes_db_mcp.repositories import topic_plan_feedback_repo
from hermes_db_mcp.server import AppContext, mcp


VALID_EVENT_TYPES = topic_plan_feedback_repo.TOPIC_PLAN_FEEDBACK_EVENT_TYPES


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=False,
    )
)
async def record_topic_plan_feedback(
    plan_id: str,
    event_type: str,
    ctx: Context,
    dedupe_key: str | None = None,
    reason_tags: list[str] | None = None,
    note: str | None = None,
    decided_by: str | None = None,
    topic_id: str | None = None,
    metadata: dict | None = None,
    event_at: str | None = None,
) -> dict:
    """记录 TopicPlan 反馈事件；提供 dedupe_key 时客户端重试是幂等安全的。"""
    plan_uuid = _parse_uuid(plan_id, "plan_id")
    if isinstance(plan_uuid, dict):
        return plan_uuid
    topic_uuid = _parse_optional_uuid(topic_id, "topic_id")
    if isinstance(topic_uuid, dict):
        return topic_uuid
    event_time = _parse_optional_datetime(event_at, "event_at")
    if isinstance(event_time, dict):
        return event_time
    if err := _validate_record_payload(
        event_type=event_type,
        reason_tags=reason_tags,
        metadata=metadata,
        topic_id=topic_id,
    ):
        return err

    app: AppContext = ctx.request_context.lifespan_context
    try:
        row = await topic_plan_feedback_repo.record_topic_plan_feedback(
            app.pool,
            plan_id=plan_uuid,
            event_type=event_type,
            dedupe_key=dedupe_key,
            reason_tags=reason_tags,
            note=note,
            decided_by=decided_by,
            topic_id=topic_uuid,
            metadata=metadata,
            event_at=event_time,
        )
    except ValueError:
        return error("invalid_field", field="event_type", details={"value": event_type})

    if not row:
        return error("not_found", details={"plan_id": plan_id})
    return _serialize_feedback_event(row)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_topic_plan_feedback(
    ctx: Context,
    plan_id: str | None = None,
    account_id: str | None = None,
    track_id: str | None = None,
    event_type: str | None = None,
    event_from: str | None = None,
    event_to: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """按 plan/account/track/type/time 窗口查询 TopicPlan 反馈事件。"""
    plan_uuid = _parse_optional_uuid(plan_id, "plan_id")
    if isinstance(plan_uuid, dict):
        return plan_uuid
    if event_type is not None and event_type not in VALID_EVENT_TYPES:
        return error("invalid_field", field="event_type", details={"value": event_type})
    parsed_times = {}
    for field, value in (
        ("event_from", event_from),
        ("event_to", event_to),
        ("created_from", created_from),
        ("created_to", created_to),
    ):
        parsed = _parse_optional_datetime(value, field)
        if isinstance(parsed, dict):
            return parsed
        parsed_times[field] = parsed
    if err := validate_pagination(limit, offset):
        return err

    app: AppContext = ctx.request_context.lifespan_context
    try:
        items, total = await topic_plan_feedback_repo.list_topic_plan_feedback(
            app.pool,
            plan_id=plan_uuid,
            account_id=account_id,
            track_id=track_id,
            event_type=event_type,
            event_from=parsed_times["event_from"],
            event_to=parsed_times["event_to"],
            created_from=parsed_times["created_from"],
            created_to=parsed_times["created_to"],
            limit=limit,
            offset=offset,
        )
    except ValueError:
        return error("invalid_field", field="event_type", details={"value": event_type})

    return {
        "items": [_serialize_feedback_event(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_topic_plan_feedback_report(
    ctx: Context,
    account_id: str | None = None,
    track_id: str | None = None,
    window_days: int = 30,
    min_sample_size: int = 5,
) -> dict:
    """生成 TopicPlan 反馈采纳率、消费率、发布率和配置分组报告。"""
    if window_days < 1:
        return error("invalid_field", field="window_days", details={"actual": window_days})
    if min_sample_size < 1:
        return error(
            "invalid_field",
            field="min_sample_size",
            details={"actual": min_sample_size},
        )

    app: AppContext = ctx.request_context.lifespan_context
    return await topic_plan_feedback_repo.get_topic_plan_feedback_report(
        app.pool,
        account_id=account_id,
        track_id=track_id,
        window_days=window_days,
        min_sample_size=min_sample_size,
    )


def _validate_record_payload(
    *,
    event_type: str,
    reason_tags: list[str] | None,
    metadata: dict | None,
    topic_id: str | None,
) -> dict | None:
    if event_type not in VALID_EVENT_TYPES:
        return error("invalid_field", field="event_type", details={"value": event_type})
    if reason_tags is not None:
        if not isinstance(reason_tags, list) or any(
            not isinstance(tag, str) or not tag.strip() for tag in reason_tags
        ):
            return error("invalid_field", field="reason_tags")
    if metadata is not None and not isinstance(metadata, dict):
        return error("invalid_field", field="metadata")
    if event_type == "published":
        metadata = metadata or {}
        if not (
            topic_id
            or metadata.get("publication_id")
            or metadata.get("publication_idempotency_key")
        ):
            return error(
                "missing_required_field",
                field="publication_lineage",
                details={
                    "required_any": [
                        "topic_id",
                        "metadata.publication_id",
                        "metadata.publication_idempotency_key",
                    ]
                },
            )
    return None


def _parse_uuid(value: str, field: str) -> UUID | dict:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return error("invalid_uuid", field=field, details={"value": value})


def _parse_optional_uuid(value: str | None, field: str) -> UUID | None | dict:
    if value is None:
        return None
    return _parse_uuid(value, field)


def _parse_optional_datetime(value: str | None, field: str) -> datetime | None | dict:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return error("invalid_field", field=field, details={"value": value})


def _serialize_feedback_event(row: dict) -> dict:
    return {
        "event_id": str(row["event_id"]),
        "plan_id": str(row["plan_id"]),
        "account_id": row["account_id"],
        "track_id": row.get("track_id"),
        "event_type": row["event_type"],
        "dedupe_key": row.get("dedupe_key"),
        "reason_tags": _json_array(row.get("reason_tags")),
        "note": row.get("note"),
        "decided_by": row.get("decided_by"),
        "topic_id": str(row["topic_id"]) if row.get("topic_id") else None,
        "metadata": _json_object(row.get("metadata")),
        "event_at": str(row["event_at"]),
        "created_at": str(row["created_at"]),
    }


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
