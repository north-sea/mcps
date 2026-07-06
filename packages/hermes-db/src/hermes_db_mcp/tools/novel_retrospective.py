"""Novel retrospective MCP tools."""

from __future__ import annotations

from uuid import UUID

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.contracts import error
from hermes_db_mcp.repositories import novel_retrospective_repo
from hermes_db_mcp.server import AppContext, mcp
from hermes_db_mcp.services.schema import inspect_novel_retrospective_contracts_schema


REPORT_MODES = {"batch", "volume"}
REPORT_CONFIDENCE = {"high", "low"}
REPORT_REVIEW_STATUSES = {"pending", "approved", "rejected"}
ALERT_TYPES = {
    "high_similarity",
    "character_single_reaction",
    "foreshadowing_expired",
    "emotional_debt_overdue",
}
ALERT_SEVERITIES = {"red", "yellow", "green"}
CONSTRAINT_TARGETS = {"next", "remaining"}
CONSTRAINT_STATUSES = {"pending", "approved", "rejected", "expired"}
LEARNING_CONFIDENCE = {"high", "medium", "low"}
LEARNING_STATUSES = {"pending", "approved", "rejected"}
DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def _uuid(value: str, field: str) -> UUID | dict:
    try:
        return UUID(value)
    except (TypeError, ValueError):
        return error("invalid_uuid", field=field, details={"value": value})


def _limit(value: int | None) -> int:
    if value is None:
        return DEFAULT_LIMIT
    return min(value, MAX_LIMIT)


def _offset(value: int | None) -> int:
    return value or 0


def _require(value: object, field: str) -> dict | None:
    if value is None or value == "":
        return error("missing_required_field", field=field)
    return None


def _enum(value: str, field: str, allowed: set[str]) -> dict | None:
    if value not in allowed:
        return error("invalid_field", field=field, details={"allowed": sorted(allowed)})
    return None


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def create_novel_retrospective_report(input: dict, ctx: Context) -> dict:
    """Create a novel retrospective report."""
    required = [
        "book_slug",
        "batch_label",
        "mode",
        "start_chapter",
        "end_chapter",
        "scoring_version",
        "diagnosis_json",
        "confidence",
    ]
    for field in required:
        if err := _require(input.get(field), field):
            return err
    if err := _enum(input["mode"], "mode", REPORT_MODES):
        return err
    if err := _enum(input["confidence"], "confidence", REPORT_CONFIDENCE):
        return err
    review_status = input.get("review_status", "pending")
    if err := _enum(review_status, "review_status", REPORT_REVIEW_STATUSES):
        return err
    if input["start_chapter"] <= 0 or input["end_chapter"] < input["start_chapter"]:
        return error("invalid_field", field="chapter_range")

    app: AppContext = ctx.request_context.lifespan_context
    return await novel_retrospective_repo.create_retrospective_report(
        app.pool,
        {**input, "review_status": review_status},
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_novel_retrospective_report(report_id: str, ctx: Context) -> dict:
    report_uuid = _uuid(report_id, "report_id")
    if isinstance(report_uuid, dict):
        return report_uuid
    app: AppContext = ctx.request_context.lifespan_context
    row = await novel_retrospective_repo.get_retrospective_report(app.pool, report_uuid)
    return row or error("not_found", details={"report_id": report_id})


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_novel_retrospective_reports(
    book_slug: str,
    ctx: Context,
    limit: int | None = None,
    offset: int | None = None,
) -> dict:
    if err := _require(book_slug, "book_slug"):
        return err
    app: AppContext = ctx.request_context.lifespan_context
    items = await novel_retrospective_repo.list_retrospective_reports(
        app.pool,
        book_slug=book_slug,
        limit=_limit(limit),
        offset=_offset(offset),
    )
    return {"items": items}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def update_novel_retrospective_report_review_status(
    report_id: str,
    review_status: str,
    ctx: Context,
) -> dict:
    report_uuid = _uuid(report_id, "report_id")
    if isinstance(report_uuid, dict):
        return report_uuid
    if err := _enum(review_status, "review_status", REPORT_REVIEW_STATUSES):
        return err
    app: AppContext = ctx.request_context.lifespan_context
    row = await novel_retrospective_repo.update_retrospective_report_review_status(
        app.pool,
        report_uuid,
        review_status,
    )
    return row or error("not_found", details={"report_id": report_id})


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def create_novel_retrospective_alert(input: dict, ctx: Context) -> dict:
    for field in ("report_id", "alert_type", "severity", "description"):
        if err := _require(input.get(field), field):
            return err
    if err := _enum(input["alert_type"], "alert_type", ALERT_TYPES):
        return err
    if err := _enum(input["severity"], "severity", ALERT_SEVERITIES):
        return err
    if isinstance(_uuid(input["report_id"], "report_id"), dict):
        return _uuid(input["report_id"], "report_id")
    app: AppContext = ctx.request_context.lifespan_context
    return await novel_retrospective_repo.create_retrospective_alert(app.pool, input)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_novel_retrospective_alerts(report_id: str, ctx: Context) -> dict:
    report_uuid = _uuid(report_id, "report_id")
    if isinstance(report_uuid, dict):
        return report_uuid
    app: AppContext = ctx.request_context.lifespan_context
    return {"items": await novel_retrospective_repo.list_retrospective_alerts(app.pool, report_uuid)}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def create_novel_correction_constraint(input: dict, ctx: Context) -> dict:
    for field in ("book_slug", "source_report_id", "alert_type", "description", "target_chapters"):
        if err := _require(input.get(field), field):
            return err
    if err := _enum(input["target_chapters"], "target_chapters", CONSTRAINT_TARGETS):
        return err
    status = input.get("status", "pending")
    if err := _enum(status, "status", CONSTRAINT_STATUSES):
        return err
    if isinstance(_uuid(input["source_report_id"], "source_report_id"), dict):
        return _uuid(input["source_report_id"], "source_report_id")
    app: AppContext = ctx.request_context.lifespan_context
    return await novel_retrospective_repo.create_correction_constraint(
        app.pool,
        {**input, "status": status},
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_novel_correction_constraint(constraint_id: str, ctx: Context) -> dict:
    constraint_uuid = _uuid(constraint_id, "constraint_id")
    if isinstance(constraint_uuid, dict):
        return constraint_uuid
    app: AppContext = ctx.request_context.lifespan_context
    row = await novel_retrospective_repo.get_correction_constraint(app.pool, constraint_uuid)
    return row or error("not_found", details={"constraint_id": constraint_id})


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_novel_correction_constraints(
    book_slug: str,
    ctx: Context,
    status: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict:
    if err := _require(book_slug, "book_slug"):
        return err
    if status and (err := _enum(status, "status", CONSTRAINT_STATUSES)):
        return err
    app: AppContext = ctx.request_context.lifespan_context
    items = await novel_retrospective_repo.list_correction_constraints(
        app.pool,
        book_slug=book_slug,
        status=status,
        limit=_limit(limit),
        offset=_offset(offset),
    )
    return {"items": items}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def update_novel_correction_constraint_status(
    constraint_id: str,
    status: str,
    ctx: Context,
) -> dict:
    constraint_uuid = _uuid(constraint_id, "constraint_id")
    if isinstance(constraint_uuid, dict):
        return constraint_uuid
    if err := _enum(status, "status", CONSTRAINT_STATUSES):
        return err
    app: AppContext = ctx.request_context.lifespan_context
    row = await novel_retrospective_repo.update_correction_constraint_status(
        app.pool,
        constraint_uuid,
        status,
    )
    return row or error("not_found", details={"constraint_id": constraint_id})


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def create_novel_handoff_package(input: dict, ctx: Context) -> dict:
    for field in ("book_slug", "snapshot_chapter", "context_version", "progress_json"):
        if err := _require(input.get(field), field):
            return err
    if input["snapshot_chapter"] <= 0:
        return error("invalid_field", field="snapshot_chapter")
    if input["context_version"] <= 0:
        return error("invalid_field", field="context_version")
    app: AppContext = ctx.request_context.lifespan_context
    return await novel_retrospective_repo.create_handoff_package(app.pool, input)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_novel_handoff_package(package_id: str, ctx: Context) -> dict:
    package_uuid = _uuid(package_id, "package_id")
    if isinstance(package_uuid, dict):
        return package_uuid
    app: AppContext = ctx.request_context.lifespan_context
    row = await novel_retrospective_repo.get_handoff_package(app.pool, package_uuid)
    return row or error("not_found", details={"package_id": package_id})


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_latest_novel_handoff_package(book_slug: str, ctx: Context) -> dict:
    if err := _require(book_slug, "book_slug"):
        return err
    app: AppContext = ctx.request_context.lifespan_context
    row = await novel_retrospective_repo.get_latest_handoff_package(app.pool, book_slug)
    return row or error("not_found", details={"book_slug": book_slug})


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True))
async def upsert_novel_character_state(input: dict, ctx: Context) -> dict:
    required = [
        "book_slug",
        "character_name",
        "last_chapter",
        "location",
        "emotional_state",
        "arc_progress",
        "dialogue_style",
    ]
    for field in required:
        if err := _require(input.get(field), field):
            return err
    if input["last_chapter"] <= 0:
        return error("invalid_field", field="last_chapter")
    app: AppContext = ctx.request_context.lifespan_context
    return await novel_retrospective_repo.upsert_character_state(app.pool, input)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_novel_character_state(
    book_slug: str,
    character_name: str,
    last_chapter: int,
    ctx: Context,
) -> dict:
    for field, value in (
        ("book_slug", book_slug),
        ("character_name", character_name),
        ("last_chapter", last_chapter),
    ):
        if err := _require(value, field):
            return err
    if last_chapter <= 0:
        return error("invalid_field", field="last_chapter")
    app: AppContext = ctx.request_context.lifespan_context
    row = await novel_retrospective_repo.get_character_state(
        app.pool,
        book_slug=book_slug,
        character_name=character_name,
        last_chapter=last_chapter,
    )
    return row or error("not_found", details={"book_slug": book_slug, "character_name": character_name})


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_novel_character_states(
    book_slug: str,
    ctx: Context,
    character_name: str | None = None,
    last_chapter: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict:
    if err := _require(book_slug, "book_slug"):
        return err
    if last_chapter is not None and last_chapter <= 0:
        return error("invalid_field", field="last_chapter")
    app: AppContext = ctx.request_context.lifespan_context
    items = await novel_retrospective_repo.list_character_states(
        app.pool,
        book_slug=book_slug,
        character_name=character_name,
        last_chapter=last_chapter,
        limit=_limit(limit),
        offset=_offset(offset),
    )
    return {"items": items}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False))
async def create_novel_learning_candidate(input: dict, ctx: Context) -> dict:
    for field in ("source_report_id", "scope", "trigger_conditions", "proposed_action", "confidence"):
        if err := _require(input.get(field), field):
            return err
    if isinstance(_uuid(input["source_report_id"], "source_report_id"), dict):
        return _uuid(input["source_report_id"], "source_report_id")
    if err := _enum(input["confidence"], "confidence", LEARNING_CONFIDENCE):
        return err
    status = input.get("status", "pending")
    if err := _enum(status, "status", LEARNING_STATUSES):
        return err
    app: AppContext = ctx.request_context.lifespan_context
    return await novel_retrospective_repo.create_learning_candidate(
        app.pool,
        {**input, "status": status},
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_novel_learning_candidates(source_report_id: str, ctx: Context) -> dict:
    report_uuid = _uuid(source_report_id, "source_report_id")
    if isinstance(report_uuid, dict):
        return report_uuid
    app: AppContext = ctx.request_context.lifespan_context
    return {"items": await novel_retrospective_repo.list_learning_candidates(app.pool, report_uuid)}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def health_novel_retrospective(ctx: Context) -> dict:
    app: AppContext = ctx.request_context.lifespan_context
    result = await inspect_novel_retrospective_contracts_schema(app.pool)
    ready = result.get("novel_retrospective_contracts", False)
    return {"status": "ok" if ready else "missing_schema", **result}
