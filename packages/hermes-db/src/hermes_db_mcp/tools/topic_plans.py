from __future__ import annotations

import json
from uuid import UUID

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.contracts import error, validate_pagination
from hermes_db_mcp.repositories import topic_plan_repo
from hermes_db_mcp.server import AppContext, mcp


VALID_PLAN_STATUSES = {"planned", "rejected", "consumed", "archived"}


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def upsert_topic_plan(
    candidate_id: str,
    account_id: str,
    status: str,
    ctx: Context,
    track_id: str | None = None,
    recommended_angle_index: int | None = None,
    topic_angles: list[dict] | None = None,
    outline_pack: dict | None = None,
    writing_brief: dict | None = None,
    image_brief: dict | None = None,
    evidence: dict | list | None = None,
    llm_metadata: dict | None = None,
    rejection_reason: str | None = None,
    topic_id: str | None = None,
    source: str | None = None,
    mark_candidate_shortlisted: bool = False,
) -> dict:
    """幂等写入候选对应的 TopicPlan。MVP 为一个 candidate 一个 plan。"""
    candidate_uuid = _parse_uuid(candidate_id, "candidate_id")
    if isinstance(candidate_uuid, dict):
        return candidate_uuid
    topic_uuid = _parse_optional_uuid(topic_id, "topic_id")
    if isinstance(topic_uuid, dict):
        return topic_uuid
    if err := _validate_plan_payload(
        account_id=account_id,
        status=status,
        recommended_angle_index=recommended_angle_index,
        topic_angles=topic_angles,
        outline_pack=outline_pack,
        writing_brief=writing_brief,
        image_brief=image_brief,
        rejection_reason=rejection_reason,
        mark_candidate_shortlisted=mark_candidate_shortlisted,
    ):
        return err

    app: AppContext = ctx.request_context.lifespan_context
    try:
        result = await topic_plan_repo.upsert_topic_plan(
            app.pool,
            candidate_id=candidate_uuid,
            account_id=account_id,
            track_id=track_id,
            status=status,
            recommended_angle_index=recommended_angle_index,
            topic_angles=topic_angles,
            outline_pack=outline_pack,
            writing_brief=writing_brief,
            image_brief=image_brief,
            evidence=evidence,
            llm_metadata=llm_metadata,
            rejection_reason=rejection_reason,
            topic_id=topic_uuid,
            source=source,
            mark_candidate_shortlisted=mark_candidate_shortlisted,
        )
    except topic_plan_repo.TopicPlanShortlistConflict as exc:
        return error(
            "invalid_transition",
            field="candidate_id",
            details={"candidate_id": str(exc.candidate_id)},
        )
    return {**_serialize_plan(result["item"]), "upserted": result["upserted"]}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_topic_plans(
    ctx: Context,
    account_id: str | None = None,
    track_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """按 account/track/status 查询 TopicPlan。"""
    if status is not None and status not in VALID_PLAN_STATUSES:
        return error("invalid_status", field="status", details={"value": status})
    if err := validate_pagination(limit, offset):
        return err

    app: AppContext = ctx.request_context.lifespan_context
    items, total = await topic_plan_repo.list_topic_plans(
        app.pool,
        account_id=account_id,
        track_id=track_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [_serialize_plan(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_topic_plan(plan_id: str, ctx: Context) -> dict:
    """读取完整 TopicPlan DTO。"""
    plan_uuid = _parse_uuid(plan_id, "plan_id")
    if isinstance(plan_uuid, dict):
        return plan_uuid

    app: AppContext = ctx.request_context.lifespan_context
    row = await topic_plan_repo.get_topic_plan(app.pool, plan_id=plan_uuid)
    if not row:
        return error("not_found", details={"plan_id": plan_id})
    return _serialize_plan(row)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def update_topic_plan_status(
    plan_id: str,
    status: str,
    ctx: Context,
    topic_id: str | None = None,
) -> dict:
    """更新 TopicPlan 生命周期状态。"""
    plan_uuid = _parse_uuid(plan_id, "plan_id")
    if isinstance(plan_uuid, dict):
        return plan_uuid
    topic_uuid = _parse_optional_uuid(topic_id, "topic_id")
    if isinstance(topic_uuid, dict):
        return topic_uuid
    if status not in VALID_PLAN_STATUSES:
        return error("invalid_status", field="status", details={"value": status})

    app: AppContext = ctx.request_context.lifespan_context
    try:
        row = await topic_plan_repo.update_topic_plan_status(
            app.pool,
            plan_id=plan_uuid,
            status=status,
            topic_id=topic_uuid,
        )
    except topic_plan_repo.TopicPlanInvalidTransition as exc:
        return {
            **error("invalid_transition"),
            "from": exc.current,
            "to": exc.target,
            "allowed": exc.allowed,
        }
    if not row:
        return error("not_found", details={"plan_id": plan_id})
    previous_status = row.pop("previous_status")
    return {
        "plan_id": str(row["plan_id"]),
        "previous_status": previous_status,
        "status": row["status"],
        "topic_id": str(row["topic_id"]) if row.get("topic_id") else None,
    }


def _validate_plan_payload(
    *,
    account_id: str,
    status: str,
    recommended_angle_index: int | None,
    topic_angles: list[dict] | None,
    outline_pack: dict | None,
    writing_brief: dict | None,
    image_brief: dict | None,
    rejection_reason: str | None,
    mark_candidate_shortlisted: bool,
) -> dict | None:
    if not account_id:
        return error("missing_required_field", field="account_id")
    if status not in VALID_PLAN_STATUSES:
        return error("invalid_status", field="status", details={"value": status})
    if mark_candidate_shortlisted and status != "planned":
        return error(
            "invalid_field",
            field="mark_candidate_shortlisted",
            details={"status": status},
        )
    if status == "planned":
        if recommended_angle_index is None:
            return error("missing_required_field", field="recommended_angle_index")
        if not isinstance(topic_angles, list) or not 3 <= len(topic_angles) <= 5:
            return error("invalid_field", field="topic_angles")
        for field, value in (
            ("outline_pack", outline_pack),
            ("writing_brief", writing_brief),
            ("image_brief", image_brief),
        ):
            if not isinstance(value, dict):
                return error("invalid_field", field=field)
    if status == "rejected" and not (rejection_reason or "").strip():
        return error("missing_required_field", field="rejection_reason")
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


def _serialize_plan(row: dict) -> dict:
    return {
        "plan_id": str(row["plan_id"]),
        "candidate_id": str(row["candidate_id"]),
        "account_id": row["account_id"],
        "track_id": row.get("track_id"),
        "status": row["status"],
        "recommended_angle_index": row.get("recommended_angle_index"),
        "topic_angles": _json_array(row.get("topic_angles")),
        "outline_pack": _json_object(row.get("outline_pack")),
        "writing_brief": _json_object(row.get("writing_brief")),
        "image_brief": _json_object(row.get("image_brief")),
        "evidence": _decode_json_value(row.get("evidence"), {}),
        "llm_metadata": _json_object(row.get("llm_metadata")),
        "rejection_reason": row.get("rejection_reason"),
        "topic_id": str(row["topic_id"]) if row.get("topic_id") else None,
        "source": row.get("source"),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
        "consumed_at": str(row["consumed_at"]) if row.get("consumed_at") else None,
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
