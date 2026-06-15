"""Novel Validation Reports and Analysis Runs MCP Tools

实现校验报告和分析运行状态的记录：
- create_novel_validation_report: 创建结构校验报告
- create_novel_analysis_run: 创建分析运行记录
- update_novel_analysis_run: 更新分析运行状态
"""

from uuid import UUID

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.server import mcp, AppContext
from hermes_db_mcp.contracts import error
from hermes_db_mcp.repositories import novel_repo


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def create_novel_validation_report(
    book_slug: str,
    is_valid: bool,
    total_chapters: int,
    warnings: list[dict],
    errors: list[dict],
    ctx: Context,
) -> dict:
    """创建结构校验报告。

    warnings/errors 格式：
    [
        {"message": "警告/错误信息", "chapter_id": "ch_001", "line": 10},
        ...
    ]
    """
    app: AppContext = ctx.request_context.lifespan_context

    if not book_slug:
        return error("missing_required_field", field="book_slug")
    if not isinstance(is_valid, bool):
        return error("invalid_field", field="is_valid", details={"type": "must be bool"})
    if total_chapters < 0:
        return error(
            "invalid_field",
            field="total_chapters",
            details={"value": total_chapters, "constraint": "must be >= 0"},
        )
    if not isinstance(warnings, list):
        return error("invalid_field", field="warnings", details={"type": "must be list"})
    if not isinstance(errors, list):
        return error("invalid_field", field="errors", details={"type": "must be list"})

    row = await novel_repo.create_validation_report(
        app.pool,
        book_slug=book_slug,
        is_valid=is_valid,
        total_chapters=total_chapters,
        warnings=warnings,
        errors=errors,
    )

    return {
        "id": str(row["id"]),
        "book_slug": row["book_slug"],
        "is_valid": row["is_valid"],
        "total_chapters": row["total_chapters"],
        "warnings_count": len(warnings),
        "errors_count": len(errors),
        "created_at": str(row["created_at"]),
    }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def create_novel_analysis_run(
    book_slug: str,
    stage: str,
    chapters_status: list[dict],
    ctx: Context,
    error_message: str | None = None,
) -> dict:
    """创建分析运行记录。

    stage: 'split' | 'validate' | 'analyze' | 'aggregate' | 'profile' | 'done'
    chapters_status 格式：
    [
        {"chapter_id": "ch_001", "status": "started|completed|failed", "error": "错误信息"},
        ...
    ]
    """
    app: AppContext = ctx.request_context.lifespan_context

    if not book_slug:
        return error("missing_required_field", field="book_slug")
    if not stage:
        return error("missing_required_field", field="stage")
    if not isinstance(chapters_status, list):
        return error("invalid_field", field="chapters_status", details={"type": "must be list"})

    row = await novel_repo.create_analysis_run(
        app.pool,
        book_slug=book_slug,
        stage=stage,
        chapters_status=chapters_status,
        error=error_message,
    )

    return {
        "id": str(row["id"]),
        "book_slug": row["book_slug"],
        "stage": row["stage"],
        "started_at": str(row["started_at"]),
        "created_at": str(row["created_at"]),
    }


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def update_novel_analysis_run(
    run_id: str,
    ctx: Context,
    stage: str | None = None,
    chapters_status: list[dict] | None = None,
    completed_at: str | None = None,
    error_message: str | None = None,
) -> dict:
    """更新分析运行状态。

    可更新 stage、chapters_status、completed_at 和 error。
    """
    app: AppContext = ctx.request_context.lifespan_context

    if not run_id:
        return error("missing_required_field", field="run_id")

    try:
        run_uuid = UUID(run_id)
    except (ValueError, AttributeError):
        return error("invalid_uuid", field="run_id", details={"value": run_id})

    row = await novel_repo.update_analysis_run(
        app.pool,
        run_id=run_uuid,
        stage=stage,
        chapters_status=chapters_status,
        completed_at=completed_at,
        error=error_message,
    )

    if not row:
        return error("not_found", details={"run_id": run_id})

    return {
        "id": str(row["id"]),
        "book_slug": row["book_slug"],
        "stage": row["stage"],
        "started_at": str(row["started_at"]),
        "completed_at": str(row["completed_at"]) if row["completed_at"] else None,
        "updated_at": str(row["updated_at"]),
    }
