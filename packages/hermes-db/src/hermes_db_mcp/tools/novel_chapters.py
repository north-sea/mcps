"""Novel Chapters MCP Tools

实现小说章节的 CRUD 操作：
- create_novel_chapters: 批量创建章节（幂等）
- get_novel_chapter: 查询单章详情
- list_novel_chapters: 列出某本书的所有章节（分页）
"""

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.server import mcp, AppContext
from hermes_db_mcp.services.cache import cache_record, get_cached
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
async def create_novel_chapters(
    book_slug: str,
    chapters: list[dict],
    ctx: Context,
) -> dict:
    """批量创建章节。幂等：(book_slug, chapter_number) 唯一约束保证。

    chapters 格式：
    [
        {
            "chapter_id": "ch_001",
            "chapter_number": 1,
            "title": "第一章",
            "content": "正文...",
            "word_count": 3000,
            "split_source": "auto"
        },
        ...
    ]
    """
    app: AppContext = ctx.request_context.lifespan_context

    if not book_slug:
        return error("missing_required_field", field="book_slug")
    if not chapters or not isinstance(chapters, list):
        return error("missing_required_field", field="chapters")
    if len(chapters) > 500:
        return error(
            "invalid_field",
            field="chapters",
            details={"value": len(chapters), "constraint": "max 500 chapters per batch"},
        )

    # 验证每个 chapter 的必填字段
    for i, ch in enumerate(chapters):
        if not isinstance(ch, dict):
            return error("invalid_field", field=f"chapters[{i}]", details={"type": "must be dict"})
        for required_field in ["chapter_id", "chapter_number", "title", "content", "word_count"]:
            if required_field not in ch:
                return error("missing_required_field", field=f"chapters[{i}].{required_field}")

    created_count = await novel_repo.batch_upsert_chapters(
        app.pool,
        book_slug=book_slug,
        chapters=chapters,
    )

    # 清除 book 和 chapters 缓存
    await app.redis.delete(f"hermes:novel:book:{book_slug}")
    # 清除可能的章节缓存（简单做法：批量删除模式匹配的 key）
    for ch in chapters:
        await app.redis.delete(f"hermes:novel:chapter:{ch['chapter_id']}")

    return {
        "book_slug": book_slug,
        "created_count": created_count,
        "total_submitted": len(chapters),
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_novel_chapter(chapter_id: str, ctx: Context) -> dict:
    """获取单章详情（包含 content），优先读 Redis 缓存。"""
    app: AppContext = ctx.request_context.lifespan_context

    if not chapter_id:
        return error("missing_required_field", field="chapter_id")

    cache_key = f"hermes:novel:chapter:{chapter_id}"
    cached = await get_cached(app.redis, cache_key)
    if cached:
        return cached

    row = await novel_repo.get_chapter(app.pool, chapter_id=chapter_id)
    if not row:
        return error("not_found", details={"chapter_id": chapter_id})

    result = {
        "chapter_id": row["chapter_id"],
        "book_slug": row["book_slug"],
        "chapter_number": row["chapter_number"],
        "title": row["title"],
        "content": row["content"],
        "word_count": row["word_count"],
        "split_source": row["split_source"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }
    await cache_record(app.redis, cache_key, result)
    return result


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_novel_chapters(
    book_slug: str,
    ctx: Context,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """列出某本书的所有章节，按 chapter_number 升序，支持分页。"""
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

    items, total = await novel_repo.list_chapters(
        app.pool,
        book_slug=book_slug,
        limit=limit,
        offset=offset,
    )

    for item in items:
        item["created_at"] = str(item["created_at"])
        item["updated_at"] = str(item["updated_at"])

    return {"items": items, "total": total}
