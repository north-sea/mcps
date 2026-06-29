from __future__ import annotations

from datetime import datetime
from uuid import UUID

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.contracts import error, validate_pagination
from hermes_db_mcp.repositories import topic_candidate_repo
from hermes_db_mcp.server import AppContext, mcp
from hermes_db_mcp.services.state_machine import validate_transition


VALID_CANDIDATE_STATUSES = {"new", "shortlisted", "adopted", "rejected", "expired"}


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def upsert_topic_candidate(
    account_id: str,
    track_id: str,
    source: str,
    title: str,
    dedupe_key: str,
    captured_at: str,
    ctx: Context,
    source_url: str | None = None,
    source_item_id: str | None = None,
    summary: str | None = None,
    hot_score: float | None = None,
    fit_score: float | None = None,
    novelty_score: float | None = None,
    raw_payload: dict | None = None,
) -> dict:
    """幂等写入热点候选。候选必须绑定 account_id 和 track_id。"""
    if not account_id:
        return error("missing_required_field", field="account_id")
    if not track_id:
        return error("missing_required_field", field="track_id")
    if not source:
        return error("missing_required_field", field="source")
    if not title:
        return error("missing_required_field", field="title")
    if not dedupe_key:
        return error("missing_required_field", field="dedupe_key")
    if not source_url and not source_item_id:
        return error("missing_required_field", field="source_url_or_source_item_id")

    captured = _parse_datetime(captured_at, "captured_at")
    if isinstance(captured, dict):
        return captured

    app: AppContext = ctx.request_context.lifespan_context
    row = await topic_candidate_repo.upsert_candidate(
        app.pool,
        account_id=account_id,
        track_id=track_id,
        source=source,
        source_url=source_url,
        source_item_id=source_item_id,
        title=title,
        summary=summary,
        hot_score=hot_score,
        fit_score=fit_score,
        novelty_score=novelty_score,
        dedupe_key=dedupe_key,
        captured_at=captured,
        raw_payload=raw_payload,
    )
    return {
        "candidate_id": str(row["id"]),
        "status": row["status"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "upserted": "created" if row["created"] else "updated",
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_topic_candidates(
    ctx: Context,
    account_id: str | None = None,
    track_id: str | None = None,
    status: str | None = None,
    source: str | None = None,
    limit: int = 20,
    offset: int = 0,
    include_raw: bool = False,
) -> dict:
    """按 account/track/status/source 查询候选池。默认排除 rejected/expired。"""
    if status is not None and status not in VALID_CANDIDATE_STATUSES:
        return error("invalid_status", field="status", details={"value": status})
    if err := validate_pagination(limit, offset):
        return err

    app: AppContext = ctx.request_context.lifespan_context
    items, total = await topic_candidate_repo.list_candidates(
        app.pool,
        account_id=account_id,
        track_id=track_id,
        status=status,
        source=source,
        limit=limit,
        offset=offset,
        include_raw=include_raw,
    )
    return {
        "items": [_serialize_candidate(item, include_raw=include_raw) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_topic_candidate_tracks(
    ctx: Context,
    account_id: str | None = None,
    enabled: bool | None = None,
) -> dict:
    """列出候选池账号和赛道配置。"""
    app: AppContext = ctx.request_context.lifespan_context
    accounts, tracks = await topic_candidate_repo.list_tracks(
        app.pool,
        account_id=account_id,
        enabled=enabled,
    )
    return {
        "accounts": [_serialize_account(item) for item in accounts],
        "tracks": [_serialize_track(item) for item in tracks],
    }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def reject_topic_candidate(
    candidate_id: str,
    ctx: Context,
    reason: str | None = None,
) -> dict:
    """拒绝候选。"""
    return await _update_one_status(candidate_id, "rejected", ctx, reason=reason)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def shortlist_topic_candidate(candidate_id: str, ctx: Context) -> dict:
    """将候选标记为 shortlisted。"""
    return await _update_one_status(candidate_id, "shortlisted", ctx)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def expire_topic_candidates(
    ctx: Context,
    account_id: str | None = None,
    track_id: str | None = None,
    captured_before: str | None = None,
    limit: int = 100,
) -> dict:
    """批量过期候选。"""
    if limit < 1 or limit > 500:
        return error("invalid_pagination", field="limit", details={"limit": limit})
    before = None
    if captured_before:
        before = _parse_datetime(captured_before, "captured_before")
        if isinstance(before, dict):
            return before

    app: AppContext = ctx.request_context.lifespan_context
    ids = await topic_candidate_repo.expire_candidates(
        app.pool,
        account_id=account_id,
        track_id=track_id,
        captured_before=before,
        limit=limit,
    )
    return {"expired": len(ids), "candidate_ids": [str(candidate_id) for candidate_id in ids]}


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def adopt_topic_candidate(
    candidate_id: str,
    ctx: Context,
    title: str | None = None,
    angle: str | None = None,
    priority: str = "B",
    column_name: str | None = None,
    resonance: str | None = None,
    content: str | None = None,
    force_duplicate: bool = False,
) -> dict:
    """采纳候选为正式 topic，并保留 candidate -> topic lineage。"""
    candidate_uuid = _parse_uuid(candidate_id, "candidate_id")
    if isinstance(candidate_uuid, dict):
        return candidate_uuid

    app: AppContext = ctx.request_context.lifespan_context
    current = await topic_candidate_repo.get_candidate(app.pool, candidate_id=candidate_uuid)
    if not current:
        return error("not_found", details={"candidate_id": candidate_id})

    if current["status"] == "adopted" and current.get("topic_id"):
        return {
            "candidate_id": candidate_id,
            "topic_id": str(current["topic_id"]),
            "previous_status": "adopted",
            "status": "adopted",
            "duplicate_warning": False,
        }

    if err := validate_transition("topic_candidate", current["status"], "adopted"):
        return err

    result = await topic_candidate_repo.adopt_candidate(
        app.pool,
        candidate_id=candidate_uuid,
        title=title,
        angle=angle,
        priority=priority,
        column_name=column_name,
        resonance=resonance,
        content=content,
    )
    if not result:
        return error("not_found", details={"candidate_id": candidate_id})
    return {
        "candidate_id": candidate_id,
        "topic_id": str(result["topic_id"]),
        "previous_status": current["status"],
        "status": "adopted",
        "duplicate_warning": False if force_duplicate is not None else False,
    }


async def _update_one_status(
    candidate_id: str,
    target_status: str,
    ctx: Context,
    *,
    reason: str | None = None,
) -> dict:
    candidate_uuid = _parse_uuid(candidate_id, "candidate_id")
    if isinstance(candidate_uuid, dict):
        return candidate_uuid

    app: AppContext = ctx.request_context.lifespan_context
    current = await topic_candidate_repo.get_candidate(app.pool, candidate_id=candidate_uuid)
    if not current:
        return error("not_found", details={"candidate_id": candidate_id})
    if err := validate_transition("topic_candidate", current["status"], target_status):
        return err

    row = await topic_candidate_repo.update_status(
        app.pool,
        candidate_id=candidate_uuid,
        new_status=target_status,
        rejection_reason=reason,
    )
    if not row:
        return error("not_found", details={"candidate_id": candidate_id})
    return {
        "candidate_id": candidate_id,
        "previous_status": current["status"],
        "status": row["status"],
        "topic_id": str(row["topic_id"]) if row.get("topic_id") else None,
    }


def _parse_uuid(value: str, field: str) -> UUID | dict:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return error("invalid_uuid", field=field, details={"value": value})


def _parse_datetime(value: str, field: str) -> datetime | dict:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return error("invalid_datetime", field=field, details={"value": value})


def _serialize_candidate(row: dict, *, include_raw: bool = False) -> dict:
    item = {
        "candidate_id": str(row["id"]),
        "account_id": row["account_id"],
        "track_id": row["track_id"],
        "source": row["source"],
        "source_url": row.get("source_url"),
        "source_item_id": row.get("source_item_id"),
        "title": row["title"],
        "summary": row.get("summary"),
        "hot_score": _maybe_float(row.get("hot_score")),
        "fit_score": _maybe_float(row.get("fit_score")),
        "novelty_score": _maybe_float(row.get("novelty_score")),
        "status": row["status"],
        "dedupe_key": row["dedupe_key"],
        "captured_at": str(row["captured_at"]),
        "topic_id": str(row["topic_id"]) if row.get("topic_id") else None,
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]) if row.get("updated_at") else None,
    }
    if include_raw:
        item["raw_payload"] = row.get("raw_payload") or {}
    return item


def _serialize_account(row: dict) -> dict:
    return {
        "account_id": row["account_id"],
        "display_name": row["display_name"],
        "enabled": row["enabled"],
        "draft_target": row.get("draft_target"),
    }


def _serialize_track(row: dict) -> dict:
    return {
        "account_id": row["account_id"],
        "track_id": row["track_id"],
        "name": row["name"],
        "keywords": row.get("keywords") or [],
        "negative_keywords": row.get("negative_keywords") or [],
        "sources": row.get("sources") or [],
        "scoring_profile": row.get("scoring_profile") or {},
        "daily_quota": row.get("daily_quota"),
        "enabled": row["enabled"],
    }


def _maybe_float(value):
    return float(value) if value is not None else None
