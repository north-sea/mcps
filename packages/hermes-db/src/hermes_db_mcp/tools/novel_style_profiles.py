"""Novel Style Profiles MCP Tools

实现文风档案的版本管理和查询：
- create_novel_style_profile: 创建新版本文风档案（自动版本号，激活新版）
- get_novel_style_profile: 查询当前激活版本
- list_novel_style_profile_versions: 列出所有版本
- update_novel_style_profile_active: 切换激活版本
"""

from uuid import UUID

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
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def create_novel_style_profile(
    book_slug: str,
    summary: dict,
    dimensions: list[dict],
    prompt_template: str,
    ctx: Context,
) -> dict:
    """创建新版本文风档案。

    自动计算版本号 (MAX + 1)，新版本 active=true，旧版本自动设为 active=false。
    """
    app: AppContext = ctx.request_context.lifespan_context

    if not book_slug:
        return error("missing_required_field", field="book_slug")
    if not summary or not isinstance(summary, dict):
        return error("missing_required_field", field="summary")
    if not dimensions or not isinstance(dimensions, list):
        return error("missing_required_field", field="dimensions")
    if not prompt_template:
        return error("missing_required_field", field="prompt_template")

    row = await novel_repo.create_style_profile(
        app.pool,
        book_slug=book_slug,
        summary=summary,
        dimensions=dimensions,
        prompt_template=prompt_template,
    )

    # 清除缓存
    await app.redis.delete(f"hermes:novel:style_profile:{book_slug}")

    return {
        "id": str(row["id"]),
        "book_slug": row["book_slug"],
        "version": row["version"],
        "active": row["active"],
        "created_at": str(row["created_at"]),
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_novel_style_profile(
    book_slug: str,
    ctx: Context,
    version: int | None = None,
) -> dict:
    """查询文风档案。

    默认返回 active=true 的版本；指定 version 参数可查询历史版本。
    """
    app: AppContext = ctx.request_context.lifespan_context

    if not book_slug:
        return error("missing_required_field", field="book_slug")

    # 只有查询 active 版本时才使用缓存
    cache_key = f"hermes:novel:style_profile:{book_slug}" if version is None else None
    if cache_key:
        cached = await get_cached(app.redis, cache_key)
        if cached:
            return cached

    row = await novel_repo.get_style_profile(
        app.pool,
        book_slug=book_slug,
        version=version,
    )

    if not row:
        details = {"book_slug": book_slug}
        if version is not None:
            details["version"] = version
        return error("not_found", details=details)

    result = {
        "id": str(row["id"]),
        "book_slug": row["book_slug"],
        "version": row["version"],
        "active": row["active"],
        "summary": row["summary"],
        "dimensions": row["dimensions"],
        "prompt_template": row["prompt_template"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }

    if cache_key:
        await cache_record(app.redis, cache_key, result)

    return result


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_novel_style_profile_versions(
    book_slug: str,
    ctx: Context,
) -> dict:
    """列出某本书的所有文风档案版本，按 version DESC 排序。"""
    app: AppContext = ctx.request_context.lifespan_context

    if not book_slug:
        return error("missing_required_field", field="book_slug")

    items = await novel_repo.list_style_profile_versions(
        app.pool,
        book_slug=book_slug,
    )

    for item in items:
        item["id"] = str(item["id"])
        item["created_at"] = str(item["created_at"])
        item["updated_at"] = str(item["updated_at"])

    return {"items": items, "total": len(items)}


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def update_novel_style_profile_active(
    profile_id: str,
    ctx: Context,
) -> dict:
    """切换激活版本。

    将指定 profile_id 设为 active=true，同一 book_slug 的其他版本设为 active=false。
    """
    app: AppContext = ctx.request_context.lifespan_context

    if not profile_id:
        return error("missing_required_field", field="profile_id")

    try:
        profile_uuid = UUID(profile_id)
    except (ValueError, AttributeError):
        return error("invalid_uuid", field="profile_id", details={"value": profile_id})

    result = await novel_repo.activate_style_profile(
        app.pool,
        profile_id=profile_uuid,
    )

    if not result:
        return error("not_found", details={"profile_id": profile_id})

    # 清除缓存
    await app.redis.delete(f"hermes:novel:style_profile:{result['book_slug']}")

    return {
        "id": str(result["id"]),
        "book_slug": result["book_slug"],
        "version": result["version"],
        "active": result["active"],
        "updated_at": str(result["updated_at"]),
    }
