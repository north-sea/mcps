"""Novel Planning Repository

实现小说规划相关的 PostgreSQL 数据访问层。
对应 migration 0008 的批量规划数据写入、章纲输入包查询、上下文版本追踪。
"""

import json
import asyncpg


# ========== Batch Create Book Planning ==========

async def batch_create_book_planning(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    outline: dict,
    worldbuilding: dict,
    characters: list[dict],
    foreshadowing: list[dict],
) -> None:
    """批量创建书籍规划数据（4 个表的事务性写入）。

    Args:
        pool: asyncpg 连接池
        book_slug: 书籍 slug
        outline: 全书大纲（暂不写入，预留字段）
        worldbuilding: 世界观设定
        characters: 角色列表
        foreshadowing: 伏笔列表

    Raises:
        ValueError: 如果规划数据已存在（幂等性检查失败）
        asyncpg.exceptions.ForeignKeyViolationError: 如果 book_slug 不存在
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. 幂等性检查：检查 book_slug 是否存在
            book_exists = await conn.fetchval(
                "SELECT 1 FROM hermes.novel_books WHERE book_slug = $1",
                book_slug
            )
            if not book_exists:
                raise ValueError(f"book_not_found: {book_slug}")

            # 2. 幂等性检查：检查是否已有规划数据
            has_planning = await conn.fetchval(
                """
                SELECT 1 FROM hermes.novel_worldbuilding WHERE book_slug = $1
                UNION ALL
                SELECT 1 FROM hermes.novel_characters WHERE book_slug = $1 LIMIT 1
                UNION ALL
                SELECT 1 FROM hermes.novel_foreshadowing WHERE book_slug = $1 LIMIT 1
                """,
                book_slug
            )
            if has_planning:
                raise ValueError(f"planning_already_exists: {book_slug}")

            # 3. 插入 novel_worldbuilding（单条）
            await conn.execute(
                """
                INSERT INTO hermes.novel_worldbuilding
                    (book_slug, rules, history, magic_system)
                VALUES ($1, $2, $3, $4)
                """,
                book_slug,
                worldbuilding.get("rules", ""),
                worldbuilding.get("history", ""),
                worldbuilding.get("magicSystem"),  # 可选字段
            )

            # 4. 插入 novel_characters（批量，loop inside transaction）
            for char in characters:
                await conn.execute(
                    """
                    INSERT INTO hermes.novel_characters
                        (book_slug, name, role, personality, secondary_interpretation, behavior_prohibitions)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (book_slug, name) DO NOTHING
                    """,
                    book_slug,
                    char["name"],
                    char["role"],
                    char["personality"],
                    char.get("secondaryInterpretation"),
                    char.get("behaviorProhibitions", []),
                )

            # 5. 插入 novel_foreshadowing（批量，loop inside transaction）
            for fs in foreshadowing:
                await conn.execute(
                    """
                    INSERT INTO hermes.novel_foreshadowing
                        (book_slug, title, plant_chapter, reminder_chapter, payoff_chapter, priority)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (book_slug, title) DO NOTHING
                    """,
                    book_slug,
                    fs["title"],
                    fs["plantChapter"],
                    fs.get("reminderChapter"),
                    fs["payoffChapter"],
                    fs["priority"],
                )


# ========== Get Chapter Input Pack ==========

async def get_chapter_input_pack(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    chapter_number: int,
    recent_chapters_count: int = 3,
    max_characters: int = 5,
    max_foreshadowing: int = 3,
    max_emotional_debts: int = 2,
) -> dict:
    """批量读取章纲生成所需的完整输入包。

    Args:
        pool: asyncpg 连接池
        book_slug: 书籍 slug
        chapter_number: 当前章节号
        recent_chapters_count: 最近章节数
        max_characters: 最大角色数
        max_foreshadowing: 最大伏笔数
        max_emotional_debts: 最大情感债数

    Returns:
        包含 recentChapters, characters, foreshadowing, emotionalDebts, volumeGoal 的字典

    Raises:
        ValueError: 如果 book_slug 不存在
    """
    async with pool.acquire() as conn:
        # 1. 检查 book_slug 是否存在
        book_exists = await conn.fetchval(
            "SELECT 1 FROM hermes.novel_books WHERE book_slug = $1",
            book_slug
        )
        if not book_exists:
            raise ValueError(f"book_not_found: {book_slug}")

        # 2. 查询最近 N 章摘要
        recent_chapters_sql = """
            SELECT chapter_number, title, summary, context_version, residue
            FROM hermes.novel_chapter_analyses
            JOIN hermes.novel_chapters USING (chapter_id)
            WHERE book_slug = $1 AND chapter_number < $2
            ORDER BY chapter_number DESC
            LIMIT $3
        """
        recent_chapters_rows = await conn.fetch(
            recent_chapters_sql,
            book_slug,
            chapter_number,
            recent_chapters_count
        )
        recent_chapters = [
            {
                "chapterNumber": row["chapter_number"],
                "title": row["title"],
                "summary": row["summary"],
                "contextVersion": row["context_version"],
            }
            for row in recent_chapters_rows
        ]

        # 3. 查询角色列表
        characters_sql = """
            SELECT name, role, personality, secondary_interpretation, behavior_prohibitions
            FROM hermes.novel_characters
            WHERE book_slug = $1
            LIMIT $2
        """
        characters_rows = await conn.fetch(characters_sql, book_slug, max_characters)
        characters = [
            {
                "name": row["name"],
                "role": row["role"],
                "personality": row["personality"],
                "secondaryInterpretation": row["secondary_interpretation"],
                "behaviorProhibitions": row["behavior_prohibitions"] or [],
            }
            for row in characters_rows
        ]

        # 4. 查询活跃伏笔（status='active' 且 payoff_chapter >= chapter_number）
        foreshadowing_sql = """
            SELECT title, plant_chapter, reminder_chapter, payoff_chapter, priority, status
            FROM hermes.novel_foreshadowing
            WHERE book_slug = $1
              AND status = 'active'
              AND payoff_chapter >= $2
            ORDER BY priority DESC, plant_chapter ASC
            LIMIT $3
        """
        foreshadowing_rows = await conn.fetch(
            foreshadowing_sql,
            book_slug,
            chapter_number,
            max_foreshadowing
        )
        foreshadowing = [
            {
                "title": row["title"],
                "plantChapter": row["plant_chapter"],
                "reminderChapter": row["reminder_chapter"],
                "payoffChapter": row["payoff_chapter"],
                "priority": row["priority"],
                "status": row["status"],
            }
            for row in foreshadowing_rows
        ]

        # 5. 从最近章节的 residue.emotionalDebts 聚合情感债（Python 侧处理）
        emotional_debts = []
        for row in recent_chapters_rows:
            if row["residue"] and "emotionalDebts" in row["residue"]:
                for debt in row["residue"]["emotionalDebts"][:max_emotional_debts]:
                    emotional_debts.append({
                        "description": debt.get("description", ""),
                        "sourceChapter": row["chapter_number"],
                        "involvedCharacters": debt.get("involvedCharacters", []),
                    })
                    if len(emotional_debts) >= max_emotional_debts:
                        break
            if len(emotional_debts) >= max_emotional_debts:
                break

        # 6. 推断 volumeGoal（从 novel_volume_outlines 查询当前卷的 goal）
        volume_goal_sql = """
            SELECT goal
            FROM hermes.novel_volume_outlines
            WHERE book_slug = $1
              AND start_chapter <= $2
              AND end_chapter >= $2
            LIMIT 1
        """
        volume_goal = await conn.fetchval(volume_goal_sql, book_slug, chapter_number)

        return {
            "recentChapters": recent_chapters,
            "characters": characters,
            "foreshadowing": foreshadowing,
            "emotionalDebts": emotional_debts,
            "volumeGoal": volume_goal,
        }


# ========== Context Version Tracking ==========

async def update_context_version(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    changed_scope: str,
    change_summary: str | None = None,
) -> int:
    """更新书籍的上下文版本号，并记录变更日志。

    Args:
        pool: asyncpg 连接池
        book_slug: 书籍 slug
        changed_scope: 变更范围（'book_outline' | 'volume_outline' | 'characters' | 'foreshadowing'）
        change_summary: 变更摘要（可选）

    Returns:
        新的版本号

    Raises:
        ValueError: 如果 book_slug 不存在或 changed_scope 非法
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. 获取当前版本号
            current_version = await conn.fetchval(
                "SELECT context_version FROM hermes.novel_books WHERE book_slug = $1",
                book_slug
            )
            if current_version is None:
                raise ValueError(f"book_not_found: {book_slug}")

            # 2. 递增版本号
            new_version = current_version + 1
            await conn.execute(
                """
                UPDATE hermes.novel_books
                SET context_version = $1, updated_at = now()
                WHERE book_slug = $2
                """,
                new_version,
                book_slug
            )

            # 3. 写入变更日志
            await conn.execute(
                """
                INSERT INTO hermes.novel_context_change_log
                    (book_slug, old_version, new_version, changed_scope, change_summary)
                VALUES ($1, $2, $3, $4, $5)
                """,
                book_slug,
                current_version,
                new_version,
                changed_scope,
                change_summary
            )

            return new_version


async def get_current_context_version(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
) -> int:
    """获取书籍的当前上下文版本号。

    Args:
        pool: asyncpg 连接池
        book_slug: 书籍 slug

    Returns:
        当前版本号

    Raises:
        ValueError: 如果 book_slug 不存在
    """
    async with pool.acquire() as conn:
        version = await conn.fetchval(
            "SELECT context_version FROM hermes.novel_books WHERE book_slug = $1",
            book_slug
        )
        if version is None:
            raise ValueError(f"book_not_found: {book_slug}")
        return version


