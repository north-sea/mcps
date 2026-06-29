from __future__ import annotations

import json
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
        "items": [
            _serialize_candidate(item, include_raw=include_raw) for item in items
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def sync_topic_candidate_tracks(
    accounts: list[dict],
    tracks: list[dict],
    ctx: Context,
) -> dict:
    """幂等同步候选池账号和赛道配置。不会删除未出现在输入中的线上配置。"""
    normalized_accounts = []
    account_ids = set()
    for index, account in enumerate(accounts):
        normalized = _normalize_account_config(account, index)
        if isinstance(normalized, dict) and "error" in normalized:
            return normalized
        normalized_accounts.append(normalized)
        account_ids.add(normalized["account_id"])

    normalized_tracks = []
    seen_tracks = set()
    for index, track in enumerate(tracks):
        normalized = _normalize_track_config(track, index)
        if isinstance(normalized, dict) and "error" in normalized:
            return normalized
        if normalized["account_id"] not in account_ids:
            return error(
                "invalid_reference",
                field=f"tracks[{index}].account_id",
                details={"account_id": normalized["account_id"]},
            )
        key = (normalized["account_id"], normalized["track_id"])
        if key in seen_tracks:
            return error(
                "duplicate_track",
                field=f"tracks[{index}].track_id",
                details={"account_id": key[0], "track_id": key[1]},
            )
        seen_tracks.add(key)
        normalized_tracks.append(normalized)

    app: AppContext = ctx.request_context.lifespan_context
    return await topic_candidate_repo.sync_track_config(
        app.pool,
        accounts=normalized_accounts,
        tracks=normalized_tracks,
    )


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
    return {
        "expired": len(ids),
        "candidate_ids": [str(candidate_id) for candidate_id in ids],
    }


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
    current = await topic_candidate_repo.get_candidate(
        app.pool, candidate_id=candidate_uuid
    )
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
    current = await topic_candidate_repo.get_candidate(
        app.pool, candidate_id=candidate_uuid
    )
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


def _normalize_account_config(value: dict, index: int) -> dict:
    if not isinstance(value, dict):
        return error("invalid_payload", field=f"accounts[{index}]")
    account_id = _required_text(value, "account_id", f"accounts[{index}].account_id")
    if isinstance(account_id, dict):
        return account_id
    display_name = _required_text(
        value, "display_name", f"accounts[{index}].display_name"
    )
    if isinstance(display_name, dict):
        return display_name
    enabled = value.get("enabled", True)
    if not isinstance(enabled, bool):
        return error("invalid_field", field=f"accounts[{index}].enabled")
    draft_target = value.get("draft_target")
    if draft_target is not None and not isinstance(draft_target, str):
        return error("invalid_field", field=f"accounts[{index}].draft_target")
    metadata = value.get("metadata", {})
    if not isinstance(metadata, dict):
        return error("invalid_field", field=f"accounts[{index}].metadata")
    return {
        "account_id": account_id,
        "display_name": display_name,
        "enabled": enabled,
        "draft_target": draft_target,
        "metadata": metadata,
    }


def _normalize_track_config(value: dict, index: int) -> dict:
    if not isinstance(value, dict):
        return error("invalid_payload", field=f"tracks[{index}]")
    account_id = _required_text(value, "account_id", f"tracks[{index}].account_id")
    if isinstance(account_id, dict):
        return account_id
    track_id = _required_text(value, "track_id", f"tracks[{index}].track_id")
    if isinstance(track_id, dict):
        return track_id
    name = _required_text(value, "name", f"tracks[{index}].name")
    if isinstance(name, dict):
        return name
    keywords = _string_list(value.get("keywords"), f"tracks[{index}].keywords")
    if isinstance(keywords, dict):
        return keywords
    negative_keywords = _string_list(
        value.get("negative_keywords", []),
        f"tracks[{index}].negative_keywords",
        allow_empty=True,
    )
    if isinstance(negative_keywords, dict):
        return negative_keywords
    sources = _string_list(value.get("sources"), f"tracks[{index}].sources")
    if isinstance(sources, dict):
        return sources
    scoring_profile = value.get("scoring_profile", {})
    if not isinstance(scoring_profile, dict):
        return error("invalid_field", field=f"tracks[{index}].scoring_profile")
    daily_quota = value.get("daily_quota")
    if daily_quota is not None and not isinstance(daily_quota, int):
        return error("invalid_field", field=f"tracks[{index}].daily_quota")
    enabled = value.get("enabled", True)
    if not isinstance(enabled, bool):
        return error("invalid_field", field=f"tracks[{index}].enabled")
    return {
        "account_id": account_id,
        "track_id": track_id,
        "name": name,
        "keywords": keywords,
        "negative_keywords": negative_keywords,
        "sources": sources,
        "scoring_profile": scoring_profile,
        "daily_quota": daily_quota,
        "enabled": enabled,
    }


def _required_text(value: dict, key: str, field: str) -> str | dict:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        return error("missing_required_field", field=field)
    return item.strip()


def _string_list(
    value: object, field: str, *, allow_empty: bool = False
) -> list[str] | dict:
    if not isinstance(value, list) or (not value and not allow_empty):
        return error("invalid_field", field=field)
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return error("invalid_field", field=field)
    return [item.strip() for item in value]


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
        item["raw_payload"] = _json_object(row.get("raw_payload"))
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
        "keywords": _json_array(row.get("keywords")),
        "negative_keywords": _json_array(row.get("negative_keywords")),
        "sources": _json_array(row.get("sources")),
        "scoring_profile": _json_object(row.get("scoring_profile")),
        "daily_quota": row.get("daily_quota"),
        "enabled": row["enabled"],
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


def _maybe_float(value):
    return float(value) if value is not None else None
