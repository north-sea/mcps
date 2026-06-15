"""Novel Chapter Analyses MCP Tools

实现章节分析结果的 CRUD 操作：
- create_novel_chapter_analyses: 批量创建章节分析（幂等）
- list_novel_chapter_analyses: 列出某本书的所有章节分析
- get_novel_chapter_with_analysis: 合并查询章节 + 分析结果
"""

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.server import mcp, AppContext
from hermes_db_mcp.contracts import error
from hermes_db_mcp.repositories import novel_repo


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def create_novel_chapter_analyses(
    analyses: list[dict],
    ctx: Context,
) -> dict:
    """批量创建章节分析。幂等：chapter_id 唯一约束保证。

    analyses 格式：
    [
        {
            "chapter_id": "ch_001",
            "summary": "本章摘要...",
            "plot_points": ["情节点1", "情节点2"],
            "characters": ["角色A", "角色B"],
            "conflicts": ["冲突类型"],
            "hooks": ["开头钩子"],
            "dialogue_samples_by_dimension": {
                "sentence_rhythm": [...],
                "dialogue_style": [...],
                "narrative_perspective": [...]
            },
            "style_signals": {...}
        },
        ...
    ]
    """
    app: AppContext = ctx.request_context.lifespan_context

    if not analyses or not isinstance(analyses, list):
        return error("missing_required_field", field="analyses")
    if len(analyses) > 500:
        return error(
            "invalid_field",
            field="analyses",
            details={"value": len(analyses), "constraint": "max 500 analyses per batch"},
        )

    # 验证每个 analysis 的必填字段
    for i, analysis in enumerate(analyses):
        if not isinstance(analysis, dict):
            return error("invalid_field", field=f"analyses[{i}]", details={"type": "must be dict"})
        required_fields = [
            "chapter_id", "summary", "plot_points", "characters",
            "conflicts", "hooks", "dialogue_samples_by_dimension", "style_signals"
        ]
        for required_field in required_fields:
            if required_field not in analysis:
                return error("missing_required_field", field=f"analyses[{i}].{required_field}")

    created_count = await novel_repo.batch_upsert_chapter_analyses(
        app.pool,
        analyses=analyses,
    )

    # 清除相关章节的缓存
    for analysis in analyses:
        await app.redis.delete(f"hermes:novel:chapter:{analysis['chapter_id']}")

    return {
        "created_count": created_count,
        "total_submitted": len(analyses),
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_novel_chapter_analyses(
    book_slug: str,
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """列出某本书的所有章节分析（不含 content），按 chapter_number 升序。"""
    app: AppContext = ctx.request_context.lifespan_context

    if not book_slug:
        return error("missing_required_field", field="book_slug")
    if limit < 1 or limit > 500:
        return error(
            "invalid_field",
            field="limit",
            details={"value": limit, "constraint": "must be 1-500"},
        )
    if offset < 0:
        return error(
            "invalid_field",
            field="offset",
            details={"value": offset, "constraint": "must be >= 0"},
        )

    items, total = await novel_repo.list_chapter_analyses(
        app.pool,
        book_slug=book_slug,
        limit=limit,
        offset=offset,
    )

    for item in items:
        item["created_at"] = str(item["created_at"])
        item["updated_at"] = str(item["updated_at"])

    return {"items": items, "total": total}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_novel_chapter_with_analysis(
    chapter_id: str,
    ctx: Context,
) -> dict:
    """合并查询：章节 + 分析结果。"""
    app: AppContext = ctx.request_context.lifespan_context

    if not chapter_id:
        return error("missing_required_field", field="chapter_id")

    result = await novel_repo.get_chapter_with_analysis(
        app.pool,
        chapter_id=chapter_id,
    )

    if not result:
        return error("not_found", details={"chapter_id": chapter_id})

    # 格式化时间戳
    result["created_at"] = str(result["created_at"])
    result["updated_at"] = str(result["updated_at"])
    if result.get("analysis_created_at"):
        result["analysis_created_at"] = str(result["analysis_created_at"])
    if result.get("analysis_updated_at"):
        result["analysis_updated_at"] = str(result["analysis_updated_at"])

    return result
