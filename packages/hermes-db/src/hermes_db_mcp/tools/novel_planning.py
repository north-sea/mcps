"""Novel Planning MCP Tools

实现小说规划相关的批量操作：
- batch_create_book_planning: 批量创建书籍规划数据（事务保证）
- get_chapter_input_pack: 获取章纲生成输入包
- update_context_version: 更新上下文版本号
- get_current_context_version: 获取当前上下文版本号
"""

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.server import mcp, AppContext
from hermes_db_mcp.contracts import error
from hermes_db_mcp.repositories import novel_planning_repo


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def batch_create_book_planning(
    book_slug: str,
    outline: dict,
    worldbuilding: dict,
    characters: list[dict],
    foreshadowing: list[dict],
    ctx: Context,
) -> dict:
    """批量创建书籍规划数据（4 个表的事务性写入）。

    Args:
        book_slug: 书籍 slug
        outline: 全书大纲 {"storyArc": str, "mainCharacters": [str], ...}
        worldbuilding: 世界观设定 {"rules": str, "history": str, "magicSystem": str?}
        characters: 角色列表 [{"name": str, "role": str, "personality": str, ...}]
        foreshadowing: 伏笔列表 [{"title": str, "plantChapter": int, ...}]

    Returns:
        {"success": true} 或错误
    """
    app: AppContext = ctx.request_context.lifespan_context

    # 1. 参数校验
    if not book_slug:
        return error("missing_required_field", field="book_slug")
    if not worldbuilding or not isinstance(worldbuilding, dict):
        return error("missing_required_field", field="worldbuilding")
    if not isinstance(characters, list):
        return error("invalid_field", field="characters", details={"type": "must be list"})
    if not isinstance(foreshadowing, list):
        return error("invalid_field", field="foreshadowing", details={"type": "must be list"})

    # 2. 校验 foreshadowing 数量限制（US1-5）
    if len(foreshadowing) > 100:
        return error(
            "foreshadowing_limit_exceeded",
            details={"count": len(foreshadowing), "limit": 100}
        )

    # 3. 校验 worldbuilding 必填字段
    if "rules" not in worldbuilding or "history" not in worldbuilding:
        return error("missing_required_field", field="worldbuilding.rules or worldbuilding.history")

    # 4. 校验 characters 数组元素
    for i, char in enumerate(characters):
        if not isinstance(char, dict):
            return error("invalid_field", field=f"characters[{i}]", details={"type": "must be dict"})
        for required_field in ["name", "role", "personality"]:
            if required_field not in char:
                return error("missing_required_field", field=f"characters[{i}].{required_field}")

    # 5. 校验 foreshadowing 数组元素
    for i, fs in enumerate(foreshadowing):
        if not isinstance(fs, dict):
            return error("invalid_field", field=f"foreshadowing[{i}]", details={"type": "must be dict"})
        for required_field in ["title", "plantChapter", "payoffChapter", "priority"]:
            if required_field not in fs:
                return error("missing_required_field", field=f"foreshadowing[{i}].{required_field}")
        # 校验 priority 枚举值
        if fs["priority"] not in ("high", "medium", "low"):
            return error("invalid_field", field=f"foreshadowing[{i}].priority", details={"value": fs["priority"]})

    # 6. 调用 repository 层
    try:
        await novel_planning_repo.batch_create_book_planning(
            app.pool,
            book_slug=book_slug,
            outline=outline,
            worldbuilding=worldbuilding,
            characters=characters,
            foreshadowing=foreshadowing,
        )
    except ValueError as e:
        error_msg = str(e)
        if "book_not_found" in error_msg:
            return error("book_not_found", details={"book_slug": book_slug})
        elif "planning_already_exists" in error_msg:
            return error("planning_already_exists", details={"book_slug": book_slug})
        else:
            return error("transaction_failed", details={"reason": error_msg})
    except Exception as e:
        return error("database_error", details={"reason": str(e)})

    return {"success": True}


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def get_chapter_input_pack(
    book_slug: str,
    chapter_number: int,
    ctx: Context,
    recent_chapters_count: int = 3,
    max_characters: int = 5,
    max_foreshadowing: int = 3,
    max_emotional_debts: int = 2,
) -> dict:
    """获取章纲生成所需的完整输入包（批量读取）。

    Args:
        book_slug: 书籍 slug
        chapter_number: 当前章节号
        recent_chapters_count: 最近章节数（默认 3）
        max_characters: 最大角色数（默认 5）
        max_foreshadowing: 最大伏笔数（默认 3）
        max_emotional_debts: 最大情感债数（默认 2）

    Returns:
        {
            "recentChapters": [...],
            "characters": [...],
            "foreshadowing": [...],
            "emotionalDebts": [...],
            "volumeGoal": str | null
        }
    """
    app: AppContext = ctx.request_context.lifespan_context

    # 1. 参数校验
    if not book_slug:
        return error("missing_required_field", field="book_slug")
    if chapter_number <= 0:
        return error("invalid_field", field="chapter_number", details={"value": chapter_number, "constraint": "> 0"})

    # 2. 调用 repository 层
    try:
        result = await novel_planning_repo.get_chapter_input_pack(
            app.pool,
            book_slug=book_slug,
            chapter_number=chapter_number,
            recent_chapters_count=recent_chapters_count,
            max_characters=max_characters,
            max_foreshadowing=max_foreshadowing,
            max_emotional_debts=max_emotional_debts,
        )
    except ValueError as e:
        error_msg = str(e)
        if "book_not_found" in error_msg:
            return error("book_not_found", details={"book_slug": book_slug})
        else:
            return error("database_error", details={"reason": error_msg})
    except Exception as e:
        return error("database_error", details={"reason": str(e)})

    return result


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def update_context_version(
    book_slug: str,
    changed_scope: str,
    ctx: Context,
    change_summary: str | None = None,
) -> dict:
    """更新书籍的上下文版本号，并记录变更日志。

    Args:
        book_slug: 书籍 slug
        changed_scope: 变更范围（'book_outline' | 'volume_outline' | 'characters' | 'foreshadowing'）
        change_summary: 变更摘要（可选）

    Returns:
        {"newVersion": int}
    """
    app: AppContext = ctx.request_context.lifespan_context

    # 1. 参数校验
    if not book_slug:
        return error("missing_required_field", field="book_slug")
    if not changed_scope:
        return error("missing_required_field", field="changed_scope")

    valid_scopes = ("book_outline", "volume_outline", "characters", "foreshadowing")
    if changed_scope not in valid_scopes:
        return error("invalid_field", field="changed_scope", details={"value": changed_scope, "valid": list(valid_scopes)})

    # 2. 调用 repository 层
    try:
        new_version = await novel_planning_repo.update_context_version(
            app.pool,
            book_slug=book_slug,
            changed_scope=changed_scope,
            change_summary=change_summary,
        )
    except ValueError as e:
        error_msg = str(e)
        if "book_not_found" in error_msg:
            return error("book_not_found", details={"book_slug": book_slug})
        else:
            return error("database_error", details={"reason": error_msg})
    except Exception as e:
        return error("database_error", details={"reason": str(e)})

    return {"newVersion": new_version}


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def get_current_context_version(
    book_slug: str,
    ctx: Context,
) -> dict:
    """获取书籍的当前上下文版本号。

    Args:
        book_slug: 书籍 slug

    Returns:
        {"contextVersion": int}
    """
    app: AppContext = ctx.request_context.lifespan_context

    # 1. 参数校验
    if not book_slug:
        return error("missing_required_field", field="book_slug")

    # 2. 调用 repository 层
    try:
        version = await novel_planning_repo.get_current_context_version(
            app.pool,
            book_slug=book_slug,
        )
    except ValueError as e:
        error_msg = str(e)
        if "book_not_found" in error_msg:
            return error("book_not_found", details={"book_slug": book_slug})
        else:
            return error("database_error", details={"reason": error_msg})
    except Exception as e:
        return error("database_error", details={"reason": str(e)})

    return {"contextVersion": version}

