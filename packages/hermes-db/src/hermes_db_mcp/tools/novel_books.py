"""Novel Books MCP Tools

实现小说书籍的 CRUD 操作：
- create_novel_book: 创建书籍记录（幂等）
- get_novel_book: 查询单本书详情（缓存优先）
- list_novel_books: 列出所有书籍（分页）
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
async def create_novel_book(
    book_slug: str,
    title: str,
    ctx: Context,
    author: str | None = None,
    total_chapters: int = 0,
) -> dict:
    """创建书籍记录。幂等：相同 book_slug 返回已有记录。"""
    app: AppContext = ctx.request_context.lifespan_context

    if not book_slug:
        return error("missing_required_field", field="book_slug")
    if not title:
        return error("missing_required_field", field="title")
    if total_chapters < 0:
        return error(
            "invalid_field",
            field="total_chapters",
            details={"value": total_chapters, "constraint": "must be >= 0"},
        )

    row = await novel_repo.upsert_book(
        app.pool,
        book_slug=book_slug,
        title=title,
        author=author,
        total_chapters=total_chapters,
    )

    # 清除缓存，确保下次 get 读到最新
    cache_key = f"hermes:novel:book:{book_slug}"
    await app.redis.delete(cache_key)

    return {
        "book_slug": row["book_slug"],
        "title": row["title"],
        "author": row["author"],
        "total_chapters": row["total_chapters"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_novel_book(book_slug: str, ctx: Context) -> dict:
    """获取单本书详情，优先读 Redis 缓存。"""
    app: AppContext = ctx.request_context.lifespan_context

    if not book_slug:
        return error("missing_required_field", field="book_slug")

    cache_key = f"hermes:novel:book:{book_slug}"
    cached = await get_cached(app.redis, cache_key)
    if cached:
        return cached

    row = await novel_repo.get_book(app.pool, book_slug=book_slug)
    if not row:
        return error("not_found", details={"book_slug": book_slug})

    result = {
        "book_slug": row["book_slug"],
        "title": row["title"],
        "author": row["author"],
        "total_chapters": row["total_chapters"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }
    await cache_record(app.redis, cache_key, result)
    return result


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_novel_books(
    ctx: Context,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """列出所有书籍，按创建时间倒序，支持分页。"""
    app: AppContext = ctx.request_context.lifespan_context

    if limit < 1 or limit > 100:
        return error(
            "invalid_field",
            field="limit",
            details={"value": limit, "constraint": "must be 1-100"},
        )
    if offset < 0:
        return error(
            "invalid_field",
            field="offset",
            details={"value": offset, "constraint": "must be >= 0"},
        )

    items, total = await novel_repo.list_books(
        app.pool,
        limit=limit,
        offset=offset,
    )

    for item in items:
        item["created_at"] = str(item["created_at"])
        item["updated_at"] = str(item["updated_at"])

    return {"items": items, "total": total}
