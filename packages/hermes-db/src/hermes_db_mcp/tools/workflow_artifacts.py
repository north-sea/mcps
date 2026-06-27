from datetime import datetime
from difflib import unified_diff

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.server import mcp, AppContext
from hermes_db_mcp.repositories import workflow_repo
from hermes_db_mcp.contracts import (
    DEFAULT_WORKFLOW_ARTIFACT_LIMIT,
    error,
    validate_optional_uuid,
    validate_workflow_artifact_payload,
    validate_workflow_artifact_query,
)


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _serialize_artifact(row: dict, *, include_content: bool = False) -> dict:
    result = dict(row)
    for key in ("topic_id",):
        if result.get(key) is not None:
            result[key] = str(result[key])
    for key in ("created_at", "updated_at"):
        if result.get(key) is not None:
            result[key] = str(result[key])
    if not include_content:
        result.pop("content_text", None)
    else:
        result["content_inline"] = result.get("content_text") is not None
    return result


def _selector_error() -> dict:
    return error(
        "invalid_filter",
        details={"required": "artifact_id or run_id+stage+name"},
        next_action="provide_artifact_id_or_logical_tuple",
        remediation_hint="Pass artifact_id, or pass run_id, stage, and name together.",
        retryable=False,
        current_phase="artifact_version_lookup",
    )


def _lineage_root(items: list[dict], selector: dict | None) -> str | None:
    if not items:
        return selector.get("artifact_id") if selector else None
    by_id = {item["artifact_id"]: item for item in items}
    current = items[0]
    seen = set()
    while current.get("parent_artifact_id") and current["parent_artifact_id"] in by_id:
        if current["artifact_id"] in seen:
            break
        seen.add(current["artifact_id"])
        current = by_id[current["parent_artifact_id"]]
    return current.get("artifact_id")


def _metadata_changes(left: dict, right: dict) -> dict:
    left_metadata = left.get("metadata") if isinstance(left.get("metadata"), dict) else {}
    right_metadata = right.get("metadata") if isinstance(right.get("metadata"), dict) else {}
    left_keys = set(left_metadata)
    right_keys = set(right_metadata)
    changed = sorted(key for key in left_keys & right_keys if left_metadata[key] != right_metadata[key])
    return {
        "added": sorted(right_keys - left_keys),
        "removed": sorted(left_keys - right_keys),
        "changed": changed,
    }


def _field_changes(left: dict, right: dict) -> dict:
    fields = [
        "run_id",
        "stage",
        "type",
        "name",
        "version",
        "parent_artifact_id",
        "content_hash",
        "content_size_bytes",
        "content_ref",
    ]
    return {
        field: {"left": left.get(field), "right": right.get(field)}
        for field in fields
        if left.get(field) != right.get(field)
    }


def _bounded_text_diff(left_text: str, right_text: str, *, max_preview_lines: int) -> dict:
    left_lines = left_text.splitlines()
    right_lines = right_text.splitlines()
    diff_lines = list(
        unified_diff(
            left_lines,
            right_lines,
            fromfile="left",
            tofile="right",
            lineterm="",
            n=3,
        )
    )
    truncated = len(diff_lines) > max_preview_lines
    return {
        "left_line_count": len(left_lines),
        "right_line_count": len(right_lines),
        "preview": diff_lines[:max_preview_lines],
        "truncated": truncated,
    }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def upsert_workflow_artifact(
    run_id: str,
    stage: str,
    type: str,
    name: str,
    content_hash: str,
    content_size_bytes: int,
    ctx: Context,
    artifact_id: str | None = None,
    task_id: str | None = None,
    topic_id: str | None = None,
    account: str | None = None,
    parent_artifact_id: str | None = None,
    content_preview: str | None = None,
    content_text: str | None = None,
    content_ref: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """保存 workflow artifact 摘要、hash、metadata 和正文或引用。"""
    app: AppContext = ctx.request_context.lifespan_context

    validation_error = validate_workflow_artifact_payload(
        run_id=run_id,
        stage=stage,
        type=type,
        name=name,
        content_hash=content_hash,
        content_size_bytes=content_size_bytes,
        content_text=content_text,
        content_ref=content_ref,
        topic_id=topic_id,
        parent_artifact_id=parent_artifact_id,
    )
    if validation_error:
        return validation_error
    parsed_topic_id, topic_error = validate_optional_uuid(topic_id, "topic_id")
    if topic_error:
        return topic_error

    try:
        repo_result = await workflow_repo.upsert_artifact(
            app.pool,
            artifact_id=artifact_id,
            run_id=run_id,
            task_id=task_id,
            topic_id=parsed_topic_id,
            account=account,
            stage=stage,
            type=type,
            name=name,
            parent_artifact_id=parent_artifact_id,
            content_hash=content_hash,
            content_size_bytes=content_size_bytes,
            content_preview=content_preview,
            content_text=content_text,
            content_ref=content_ref,
            metadata=metadata,
        )
        if len(repo_result) == 2:
            row, created = repo_result
            outcome = {}
        else:
            row, created, outcome = repo_result
    except ValueError as exc:
        if isinstance(exc, workflow_repo.ArtifactIdConflictError):
            return error(
                "artifact_id_conflict",
                field="artifact_id",
                details={
                    "existing_content_hash": exc.existing_content_hash,
                    "provided_content_hash": exc.provided_content_hash,
                },
                next_action="create_workflow_artifact_version",
                remediation_hint="artifact_id already exists with a different content_hash. Create an explicit new artifact version or fetch the existing artifact before retrying.",
                retryable=False,
                current_phase="artifact_upsert",
            )
        if str(exc) == "artifact_id_conflict":
            return error(
                "artifact_id_conflict",
                field="artifact_id",
                details={
                    "existing_content_hash": None,
                    "provided_content_hash": None,
                },
                next_action="create_workflow_artifact_version",
                remediation_hint="artifact_id already exists with a different content_hash. Create an explicit new artifact version or fetch the existing artifact before retrying.",
                retryable=False,
                current_phase="artifact_upsert",
            )
        return error("invalid_field", details={"message": str(exc)})
    except Exception as exc:
        message = str(exc)
        if "workflow_artifacts_run_id_fkey" in message or (
            "workflow_artifacts" in message and "run_id" in message and "fkey" in message
        ):
            return error(
                "database_error",
                field="run_id",
                details={"reason": "workflow_run_missing"},
                next_action="upsert_workflow_run",
                remediation_hint="Create the workflow run first, then retry upserting the artifact with the same run_id.",
                retryable=False,
                current_phase="artifact_upsert",
            )
        return error("database_error", details={"message": message})

    return {**_serialize_artifact(row), "created": created, **outcome}


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def create_workflow_artifact_version(
    parent_artifact_id: str,
    content_hash: str,
    content_size_bytes: int,
    ctx: Context,
    artifact_id: str | None = None,
    run_id: str | None = None,
    stage: str | None = None,
    type: str | None = None,
    name: str | None = None,
    task_id: str | None = None,
    topic_id: str | None = None,
    account: str | None = None,
    content_preview: str | None = None,
    content_text: str | None = None,
    content_ref: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """从已有 workflow artifact 创建显式新版本，不覆盖父 artifact。"""
    app: AppContext = ctx.request_context.lifespan_context
    if not parent_artifact_id or not parent_artifact_id.strip():
        return error("missing_required_field", field="parent_artifact_id")

    try:
        parent = await workflow_repo.get_artifact(app.pool, artifact_id=parent_artifact_id)
    except Exception as exc:
        return error("database_error", details={"message": str(exc)})
    if parent is None:
        return error(
            "not_found",
            field="parent_artifact_id",
            details={"parent_artifact_id": parent_artifact_id},
            next_action="fetch_or_create_parent_artifact",
            remediation_hint="Fetch the parent artifact or create the initial artifact before creating a version.",
            retryable=False,
            current_phase="artifact_version_create",
        )

    resolved_run_id = run_id or parent["run_id"]
    resolved_stage = stage or parent["stage"]
    resolved_type = type or parent["type"]
    resolved_name = name or parent["name"]
    resolved_task_id = task_id if task_id is not None else parent.get("task_id")
    parent_topic_id = parent.get("topic_id")
    resolved_topic_id = topic_id if topic_id is not None else (str(parent_topic_id) if parent_topic_id is not None else None)
    resolved_account = account if account is not None else parent.get("account")
    resolved_metadata = metadata if metadata is not None else parent.get("metadata")

    validation_error = validate_workflow_artifact_payload(
        run_id=resolved_run_id,
        stage=resolved_stage,
        type=resolved_type,
        name=resolved_name,
        content_hash=content_hash,
        content_size_bytes=content_size_bytes,
        content_text=content_text,
        content_ref=content_ref,
        topic_id=resolved_topic_id,
        parent_artifact_id=parent_artifact_id,
    )
    if validation_error:
        return validation_error
    parsed_topic_id, topic_error = validate_optional_uuid(resolved_topic_id, "topic_id")
    if topic_error:
        return topic_error

    try:
        row, created, outcome = await workflow_repo.upsert_artifact(
            app.pool,
            artifact_id=artifact_id,
            run_id=resolved_run_id,
            task_id=resolved_task_id,
            topic_id=parsed_topic_id,
            account=resolved_account,
            stage=resolved_stage,
            type=resolved_type,
            name=resolved_name,
            parent_artifact_id=parent_artifact_id,
            content_hash=content_hash,
            content_size_bytes=content_size_bytes,
            content_preview=content_preview,
            content_text=content_text,
            content_ref=content_ref,
            metadata=resolved_metadata,
        )
    except workflow_repo.ArtifactIdConflictError as exc:
        return error(
            "artifact_id_conflict",
            field="artifact_id",
            details={
                "existing_content_hash": exc.existing_content_hash,
                "provided_content_hash": exc.provided_content_hash,
            },
            next_action="retry_without_artifact_id_or_choose_new_artifact_id",
            remediation_hint="The requested artifact_id already exists with different content. Retry without artifact_id or choose a new explicit artifact_id.",
            retryable=False,
            current_phase="artifact_version_create",
        )
    except Exception as exc:
        return error("database_error", details={"message": str(exc)})

    versions, selector = await workflow_repo.list_artifact_versions(
        app.pool,
        artifact_id=row["artifact_id"],
        order="asc",
        limit=100,
        offset=0,
    )
    return {
        **_serialize_artifact(row),
        "created": created,
        **outcome,
        "lineage_root_artifact_id": _lineage_root(versions, selector),
        "next_action": "use_artifact_id_for_downstream_consumer",
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_workflow_artifacts(
    ctx: Context,
    run_id: str | None = None,
    topic_id: str | None = None,
    account: str | None = None,
    type: str | None = None,
    stage: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = DEFAULT_WORKFLOW_ARTIFACT_LIMIT,
    offset: int = 0,
) -> dict:
    """按 run/topic/account/date/type 查询 workflow artifact 摘要。"""
    app: AppContext = ctx.request_context.lifespan_context
    explicit_limit = limit != DEFAULT_WORKFLOW_ARTIFACT_LIMIT
    validation_error = validate_workflow_artifact_query(
        run_id=run_id,
        topic_id=topic_id,
        account=account,
        type=type,
        stage=stage,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        explicit_limit=explicit_limit,
    )
    if validation_error:
        return validation_error
    parsed_topic_id, topic_error = validate_optional_uuid(topic_id, "topic_id")
    if topic_error:
        return topic_error

    try:
        rows = await workflow_repo.list_artifacts(
            app.pool,
            run_id=run_id,
            topic_id=parsed_topic_id,
            account=account,
            type=type,
            stage=stage,
            date_from=_parse_datetime(date_from),
            date_to=_parse_datetime(date_to),
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        return error("database_error", details={"message": str(exc)})
    return {"items": [_serialize_artifact(row) for row in rows], "limit": limit, "offset": offset}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_workflow_artifact_versions(
    ctx: Context,
    artifact_id: str | None = None,
    run_id: str | None = None,
    stage: str | None = None,
    name: str | None = None,
    order: str = "asc",
    limit: int = DEFAULT_WORKFLOW_ARTIFACT_LIMIT,
    offset: int = 0,
) -> dict:
    """列出 workflow artifact 逻辑版本族。"""
    app: AppContext = ctx.request_context.lifespan_context
    if not artifact_id and not (run_id and stage and name):
        return _selector_error()
    if order not in ("asc", "desc"):
        return error("invalid_field", field="order", details={"valid_values": ["asc", "desc"]})
    validation_error = validate_workflow_artifact_query(
        run_id=run_id,
        stage=stage,
        limit=limit,
        offset=offset,
        explicit_limit=True,
    )
    if validation_error:
        return validation_error

    try:
        rows, selector = await workflow_repo.list_artifact_versions(
            app.pool,
            artifact_id=artifact_id,
            run_id=run_id,
            stage=stage,
            name=name,
            order=order,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        return error("database_error", details={"message": str(exc)})
    if selector is None:
        return error("not_found", field="artifact_id" if artifact_id else "run_id")

    latest = max(rows, key=lambda item: item.get("version") or 0) if rows else None
    return {
        "items": [_serialize_artifact(row) for row in rows],
        "lineage_root_artifact_id": _lineage_root(rows, selector),
        "latest_artifact_id": latest.get("artifact_id") if latest else None,
        "limit": limit,
        "offset": offset,
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_latest_workflow_artifact_version(
    ctx: Context,
    artifact_id: str | None = None,
    run_id: str | None = None,
    stage: str | None = None,
    name: str | None = None,
) -> dict:
    """读取 workflow artifact 逻辑版本族中的最高版本。"""
    app: AppContext = ctx.request_context.lifespan_context
    if not artifact_id and not (run_id and stage and name):
        return _selector_error()
    try:
        row, selector = await workflow_repo.get_latest_artifact_version(
            app.pool,
            artifact_id=artifact_id,
            run_id=run_id,
            stage=stage,
            name=name,
        )
    except Exception as exc:
        return error("database_error", details={"message": str(exc)})
    if selector is None or row is None:
        return error("not_found", field="artifact_id" if artifact_id else "run_id")
    return {
        "artifact": _serialize_artifact(row),
        "lineage_root_artifact_id": row.get("parent_artifact_id") or selector.get("artifact_id") or row.get("artifact_id"),
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_workflow_artifact_content(artifact_id: str, ctx: Context) -> dict:
    """读取 workflow artifact 的 inline 正文或 content_ref metadata。"""
    app: AppContext = ctx.request_context.lifespan_context
    if not artifact_id or not artifact_id.strip():
        return error("missing_required_field", field="artifact_id")

    try:
        row = await workflow_repo.get_artifact(app.pool, artifact_id=artifact_id)
    except Exception as exc:
        return error("database_error", details={"message": str(exc)})
    if row is None:
        return error("not_found", field="artifact_id", details={"artifact_id": artifact_id})
    return _serialize_artifact(row, include_content=True)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def diff_workflow_artifacts(
    left_artifact_id: str,
    right_artifact_id: str,
    ctx: Context,
    include_text_preview: bool = True,
    max_preview_lines: int = 80,
) -> dict:
    """比较两个 workflow artifacts，返回有界 diff 摘要。"""
    app: AppContext = ctx.request_context.lifespan_context
    if not left_artifact_id or not left_artifact_id.strip():
        return error("missing_required_field", field="left_artifact_id")
    if not right_artifact_id or not right_artifact_id.strip():
        return error("missing_required_field", field="right_artifact_id")
    if max_preview_lines < 0 or max_preview_lines > 200:
        return error("invalid_field", field="max_preview_lines", details={"min": 0, "max": 200})

    try:
        left = await workflow_repo.get_artifact(app.pool, artifact_id=left_artifact_id)
        right = await workflow_repo.get_artifact(app.pool, artifact_id=right_artifact_id)
    except Exception as exc:
        return error("database_error", details={"message": str(exc)})
    if left is None:
        return error("not_found", field="left_artifact_id", details={"artifact_id": left_artifact_id})
    if right is None:
        return error("not_found", field="right_artifact_id", details={"artifact_id": right_artifact_id})

    left_text = left.get("content_text")
    right_text = right.get("content_text")
    content_diff_available = isinstance(left_text, str) and isinstance(right_text, str)
    content_diff = None
    if include_text_preview and content_diff_available:
        content_diff = _bounded_text_diff(
            left_text,
            right_text,
            max_preview_lines=max_preview_lines,
        )

    return {
        "left": {
            "artifact_id": left["artifact_id"],
            "version": left.get("version"),
            "content_hash": left.get("content_hash"),
        },
        "right": {
            "artifact_id": right["artifact_id"],
            "version": right.get("version"),
            "content_hash": right.get("content_hash"),
        },
        "field_changes": _field_changes(left, right),
        "metadata_changes": _metadata_changes(left, right),
        "content_changed": left.get("content_hash") != right.get("content_hash"),
        "content_diff_available": content_diff_available,
        "content_diff": content_diff,
        "remediation_hint": None if content_diff_available else "Inline content diff requires both artifacts to store content_text; content_ref is not dereferenced.",
    }
