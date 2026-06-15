"""Novel Agent Repository

实现小说相关资产的 PostgreSQL 数据访问层。
对应 migration 0007 的 7 个表。
"""

import json
import asyncpg


# ========== Books ==========

async def upsert_book(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    title: str,
    author: str | None = None,
    total_chapters: int = 0,
) -> dict:
    """创建或更新书籍记录（UPSERT 语义）。"""
    sql = """
        INSERT INTO hermes.novel_books (book_slug, title, author, total_chapters)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (book_slug) DO UPDATE SET
            title = EXCLUDED.title,
            author = EXCLUDED.author,
            total_chapters = EXCLUDED.total_chapters,
            updated_at = now()
        RETURNING book_slug, title, author, total_chapters, created_at, updated_at
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, book_slug, title, author, total_chapters)
    return dict(row)


async def get_book(pool: asyncpg.Pool, *, book_slug: str) -> dict | None:
    """查询单本书详情。"""
    sql = """
        SELECT book_slug, title, author, total_chapters, created_at, updated_at
        FROM hermes.novel_books
        WHERE book_slug = $1
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, book_slug)
    return dict(row) if row else None


async def list_books(
    pool: asyncpg.Pool,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """列出所有书籍，按创建时间倒序。"""
    count_sql = "SELECT count(*) FROM hermes.novel_books"
    list_sql = """
        SELECT book_slug, title, author, total_chapters, created_at, updated_at
        FROM hermes.novel_books
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2
    """
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql)
        rows = await conn.fetch(list_sql, limit, offset)
    return [dict(r) for r in rows], total


# ========== Chapters ==========

async def batch_upsert_chapters(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    chapters: list[dict],
) -> int:
    """批量创建或更新章节（UPSERT 语义）。

    返回实际插入或更新的行数。
    """
    sql = """
        INSERT INTO hermes.novel_chapters
            (chapter_id, book_slug, chapter_number, title, content, word_count, split_source)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (book_slug, chapter_number) DO UPDATE SET
            chapter_id = EXCLUDED.chapter_id,
            title = EXCLUDED.title,
            content = EXCLUDED.content,
            word_count = EXCLUDED.word_count,
            split_source = EXCLUDED.split_source,
            updated_at = now()
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            count = 0
            for ch in chapters:
                await conn.execute(
                    sql,
                    ch["chapter_id"],
                    book_slug,
                    ch["chapter_number"],
                    ch["title"],
                    ch["content"],
                    ch["word_count"],
                    ch.get("split_source"),
                )
                count += 1
    return count


async def get_chapter(pool: asyncpg.Pool, *, chapter_id: str) -> dict | None:
    """查询单章详情（包含 content）。"""
    sql = """
        SELECT chapter_id, book_slug, chapter_number, title, content,
               word_count, split_source, created_at, updated_at
        FROM hermes.novel_chapters
        WHERE chapter_id = $1
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, chapter_id)
    return dict(row) if row else None


async def list_chapters(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """列出某本书的所有章节，按 chapter_number 升序。

    注意：不返回 content 字段（避免大量数据）。
    """
    count_sql = """
        SELECT count(*)
        FROM hermes.novel_chapters
        WHERE book_slug = $1
    """
    list_sql = """
        SELECT chapter_id, book_slug, chapter_number, title,
               word_count, split_source, created_at, updated_at
        FROM hermes.novel_chapters
        WHERE book_slug = $1
        ORDER BY chapter_number ASC
        LIMIT $2 OFFSET $3
    """
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql, book_slug)
        rows = await conn.fetch(list_sql, book_slug, limit, offset)
    return [dict(r) for r in rows], total


# ========== Chapter Analyses ==========

async def batch_upsert_chapter_analyses(
    pool: asyncpg.Pool,
    *,
    analyses: list[dict],
) -> int:
    """批量创建或更新章节分析（UPSERT 语义）。

    返回实际插入或更新的行数。
    """
    sql = """
        INSERT INTO hermes.novel_chapter_analyses
            (chapter_id, summary, plot_points, characters, conflicts, hooks,
             dialogue_samples_by_dimension, style_signals)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (chapter_id) DO UPDATE SET
            summary = EXCLUDED.summary,
            plot_points = EXCLUDED.plot_points,
            characters = EXCLUDED.characters,
            conflicts = EXCLUDED.conflicts,
            hooks = EXCLUDED.hooks,
            dialogue_samples_by_dimension = EXCLUDED.dialogue_samples_by_dimension,
            style_signals = EXCLUDED.style_signals,
            updated_at = now()
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            count = 0
            for analysis in analyses:
                await conn.execute(
                    sql,
                    analysis["chapter_id"],
                    analysis["summary"],
                    analysis["plot_points"],
                    analysis["characters"],
                    analysis["conflicts"],
                    analysis["hooks"],
                    analysis["dialogue_samples_by_dimension"],
                    analysis["style_signals"],
                )
                count += 1
    return count


async def list_chapter_analyses(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """列出某本书的所有章节分析，按 chapter_number 升序。"""
    count_sql = """
        SELECT count(*)
        FROM hermes.novel_chapter_analyses a
        JOIN hermes.novel_chapters c ON a.chapter_id = c.chapter_id
        WHERE c.book_slug = $1
    """
    list_sql = """
        SELECT a.id, a.chapter_id, c.chapter_number, a.summary,
               a.plot_points, a.characters, a.conflicts, a.hooks,
               a.created_at, a.updated_at
        FROM hermes.novel_chapter_analyses a
        JOIN hermes.novel_chapters c ON a.chapter_id = c.chapter_id
        WHERE c.book_slug = $1
        ORDER BY c.chapter_number ASC
        LIMIT $2 OFFSET $3
    """
    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql, book_slug)
        rows = await conn.fetch(list_sql, book_slug, limit, offset)
    return [dict(r) for r in rows], total


async def get_chapter_with_analysis(
    pool: asyncpg.Pool,
    *,
    chapter_id: str,
) -> dict | None:
    """合并查询章节 + 分析结果。"""
    sql = """
        SELECT
            c.chapter_id, c.book_slug, c.chapter_number, c.title,
            c.content, c.word_count, c.split_source,
            c.created_at, c.updated_at,
            a.id AS analysis_id,
            a.summary, a.plot_points, a.characters, a.conflicts, a.hooks,
            a.dialogue_samples_by_dimension, a.style_signals,
            a.created_at AS analysis_created_at,
            a.updated_at AS analysis_updated_at
        FROM hermes.novel_chapters c
        LEFT JOIN hermes.novel_chapter_analyses a ON c.chapter_id = a.chapter_id
        WHERE c.chapter_id = $1
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, chapter_id)
    return dict(row) if row else None


# ========== Style Profiles ==========

async def create_style_profile(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    summary: dict,
    dimensions: list[dict],
    prompt_template: str,
) -> dict:
    """创建新版本文风档案。

    自动计算版本号 (MAX + 1)，新版本 active=true，旧版本设为 active=false。
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 获取当前最大版本号
            max_version = await conn.fetchval(
                "SELECT COALESCE(MAX(version), 0) FROM hermes.novel_style_profiles WHERE book_slug = $1",
                book_slug,
            )
            new_version = max_version + 1

            # 将同一 book_slug 的所有版本设为 active=false
            await conn.execute(
                "UPDATE hermes.novel_style_profiles SET active = false WHERE book_slug = $1",
                book_slug,
            )

            # 插入新版本
            row = await conn.fetchrow(
                """
                INSERT INTO hermes.novel_style_profiles
                    (book_slug, version, active, summary, dimensions, prompt_template)
                VALUES ($1, $2, true, $3, $4, $5)
                RETURNING id, book_slug, version, active, created_at
                """,
                book_slug,
                new_version,
                json.dumps(summary),
                json.dumps(dimensions),
                prompt_template,
            )
    return dict(row)


async def get_style_profile(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    version: int | None = None,
) -> dict | None:
    """查询文风档案。默认返回 active=true 的版本。"""
    if version is None:
        sql = """
            SELECT id, book_slug, version, active, summary, dimensions, prompt_template,
                   created_at, updated_at
            FROM hermes.novel_style_profiles
            WHERE book_slug = $1 AND active = true
        """
        params = [book_slug]
    else:
        sql = """
            SELECT id, book_slug, version, active, summary, dimensions, prompt_template,
                   created_at, updated_at
            FROM hermes.novel_style_profiles
            WHERE book_slug = $1 AND version = $2
        """
        params = [book_slug, version]

    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, *params)
    return dict(row) if row else None


async def list_style_profile_versions(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
) -> list[dict]:
    """列出某本书的所有文风档案版本，按 version DESC 排序。"""
    sql = """
        SELECT id, book_slug, version, active, created_at, updated_at
        FROM hermes.novel_style_profiles
        WHERE book_slug = $1
        ORDER BY version DESC
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, book_slug)
    return [dict(r) for r in rows]


async def activate_style_profile(
    pool: asyncpg.Pool,
    *,
    profile_id,
) -> dict | None:
    """切换激活版本。"""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 获取目标 profile 的 book_slug
            target = await conn.fetchrow(
                "SELECT id, book_slug, version FROM hermes.novel_style_profiles WHERE id = $1",
                profile_id,
            )
            if not target:
                return None

            # 将同一 book_slug 的所有版本设为 active=false
            await conn.execute(
                "UPDATE hermes.novel_style_profiles SET active = false WHERE book_slug = $1",
                target["book_slug"],
            )

            # 将目标版本设为 active=true
            row = await conn.fetchrow(
                """
                UPDATE hermes.novel_style_profiles
                SET active = true, updated_at = now()
                WHERE id = $1
                RETURNING id, book_slug, version, active, updated_at
                """,
                profile_id,
            )
    return dict(row) if row else None


# ========== Validation Reports ==========

async def create_validation_report(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    is_valid: bool,
    total_chapters: int,
    warnings: list[dict],
    errors: list[dict],
) -> dict:
    """创建结构校验报告。"""
    sql = """
        INSERT INTO hermes.novel_validation_reports
            (book_slug, is_valid, total_chapters, warnings, errors)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, book_slug, is_valid, total_chapters, created_at
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, book_slug, is_valid, total_chapters, json.dumps(warnings), json.dumps(errors))
    return dict(row)


# ========== Analysis Runs ==========

async def create_analysis_run(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    stage: str,
    chapters_status: list[dict],
    error: str | None = None,
) -> dict:
    """创建分析运行记录。"""
    sql = """
        INSERT INTO hermes.novel_analysis_runs
            (book_slug, started_at, stage, chapters_status, error)
        VALUES ($1, now(), $2, $3, $4)
        RETURNING id, book_slug, stage, started_at, created_at
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, book_slug, stage, json.dumps(chapters_status), error)
    return dict(row)


async def update_analysis_run(
    pool: asyncpg.Pool,
    *,
    run_id,
    stage: str | None = None,
    chapters_status: list[dict] | None = None,
    completed_at: str | None = None,
    error: str | None = None,
) -> dict | None:
    """更新分析运行状态。"""
    updates = []
    params = [run_id]
    idx = 2

    if stage is not None:
        updates.append(f"stage = ${idx}")
        params.append(stage)
        idx += 1

    if chapters_status is not None:
        updates.append(f"chapters_status = ${idx}")
        params.append(json.dumps(chapters_status))
        idx += 1

    if completed_at is not None:
        updates.append(f"completed_at = ${idx}")
        params.append(completed_at)
        idx += 1

    if error is not None:
        updates.append(f"error = ${idx}")
        params.append(error)
        idx += 1

    if not updates:
        # 没有更新字段，只查询返回
        sql = """
            SELECT id, book_slug, stage, started_at, completed_at, updated_at
            FROM hermes.novel_analysis_runs
            WHERE id = $1
        """
        async with pool.acquire() as conn:
            row = await conn.fetchrow(sql, run_id)
        return dict(row) if row else None

    updates.append("updated_at = now()")
    set_clause = ", ".join(updates)

    sql = f"""
        UPDATE hermes.novel_analysis_runs
        SET {set_clause}
        WHERE id = $1
        RETURNING id, book_slug, stage, started_at, completed_at, updated_at
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, *params)
    return dict(row) if row else None

