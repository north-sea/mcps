"""
测试 novel agent schema health check

验证 inspect_novel_agent_books_chapters_schema() 能正确检测
migration 0007 引入的 7 个表、外键约束和索引。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from hermes_db_mcp.services.schema import inspect_novel_agent_books_chapters_schema


class TestNovelSchemaHealthCheck:
    """测试 novel agent schema 健康检查"""

    @pytest.mark.asyncio
    async def test_all_tables_present(self):
        """T006: 所有 7 个表存在且字段完整时返回 True"""
        mock_pool = MagicMock()

        # Mock _fetch_column_names 返回完整字段列表
        async def mock_fetch(query, *args):
            table_name = args[1] if len(args) > 1 else ""

            if table_name == "novel_books":
                return [{"column_name": col} for col in [
                    "book_slug", "title", "author", "total_chapters",
                    "created_at", "updated_at"
                ]]
            elif table_name == "novel_chapters":
                return [{"column_name": col} for col in [
                    "chapter_id", "book_slug", "chapter_number", "title",
                    "content", "word_count", "split_source", "created_at", "updated_at"
                ]]
            elif table_name == "novel_chapter_analyses":
                return [{"column_name": col} for col in [
                    "id", "chapter_id", "summary", "plot_points", "characters",
                    "conflicts", "hooks", "dialogue_samples_by_dimension",
                    "style_signals", "created_at", "updated_at"
                ]]
            elif table_name == "novel_style_profiles":
                return [{"column_name": col} for col in [
                    "id", "book_slug", "version", "active", "summary",
                    "dimensions", "prompt_template", "created_at", "updated_at"
                ]]
            elif table_name == "novel_style_anchors":
                return [{"column_name": col} for col in [
                    "id", "style_profile_id", "dimension", "text",
                    "chapter_id", "line_range", "created_at"
                ]]
            elif table_name == "novel_validation_reports":
                return [{"column_name": col} for col in [
                    "id", "book_slug", "is_valid", "total_chapters",
                    "warnings", "errors", "created_at"
                ]]
            elif table_name == "novel_analysis_runs":
                return [{"column_name": col} for col in [
                    "id", "book_slug", "started_at", "completed_at",
                    "stage", "chapters_status", "error", "created_at", "updated_at"
                ]]

            # 约束和索引查询
            elif "pg_constraint" in query or "conname" in query:
                constraint_name = args[2][0] if len(args) > 2 and args[2] else ""
                if "novel_chapters" in constraint_name:
                    return [{"conname": c} for c in [
                        "novel_chapters_pkey",
                        "novel_chapters_book_slug_fkey",
                        "uq_novel_chapters_book_number",
                    ]]
                elif "novel_chapter_analyses" in constraint_name:
                    return [{"conname": c} for c in [
                        "novel_chapter_analyses_pkey",
                        "novel_chapter_analyses_chapter_id_fkey",
                        "uq_novel_chapter_analyses_chapter",
                    ]]
                elif "novel_style_profiles" in constraint_name:
                    return [{"conname": c} for c in [
                        "novel_style_profiles_pkey",
                        "novel_style_profiles_book_slug_fkey",
                        "uq_novel_style_profiles_book_version",
                        "chk_novel_style_profiles_version_positive",
                    ]]
                elif "novel_style_anchors" in constraint_name:
                    return [{"conname": c} for c in [
                        "novel_style_anchors_pkey",
                        "novel_style_anchors_style_profile_id_fkey",
                        "novel_style_anchors_chapter_id_fkey",
                    ]]
            elif "pg_indexes" in query or "indexname" in query:
                return [{"indexname": idx} for idx in [
                    "idx_novel_books_created_at",
                    "idx_novel_chapters_book_slug",
                    "idx_novel_chapter_analyses_chapter_id",
                    "idx_novel_style_profiles_book_active",
                    "idx_novel_style_anchors_profile",
                    "idx_novel_style_anchors_chapter",
                    "idx_novel_validation_reports_book_created",
                    "idx_novel_analysis_runs_book_started",
                ]]

            return []

        mock_conn = AsyncMock()
        mock_conn.fetch = mock_fetch
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        result = await inspect_novel_agent_books_chapters_schema(mock_pool)

        assert "novel_agent_books_chapters" in result
        assert result["novel_agent_books_chapters"] is True

    @pytest.mark.asyncio
    async def test_missing_table_returns_false(self):
        """T006: 缺少关键表时返回 False"""
        mock_pool = MagicMock()

        # Mock 缺少 novel_chapters 表的字段
        async def mock_fetch(query, *args):
            # 如果查询的是约束名称（pg_constraint）
            if "pg_constraint" in query:
                return []  # 返回空约束列表

            table_name = args[1] if len(args) > 1 else ""

            if table_name == "novel_chapters":
                return []  # 模拟表不存在

            # 其他表返回完整字段
            return [{"column_name": "dummy"}]

        mock_conn = AsyncMock()
        mock_conn.fetch = mock_fetch
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        result = await inspect_novel_agent_books_chapters_schema(mock_pool)

        assert result["novel_agent_books_chapters"] is False

    @pytest.mark.asyncio
    async def test_missing_foreign_key_returns_false(self):
        """T006: 缺少外键约束时返回 False"""
        mock_pool = MagicMock()

        async def mock_fetch(query, *args):
            # 返回所有字段，但缺少外键约束
            if "pg_constraint" in query:
                return []  # 无约束
            elif "pg_indexes" in query:
                return [{"indexname": "dummy"}]

            return [{"column_name": "dummy"}]

        mock_conn = AsyncMock()
        mock_conn.fetch = mock_fetch
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        result = await inspect_novel_agent_books_chapters_schema(mock_pool)

        assert result["novel_agent_books_chapters"] is False

    @pytest.mark.asyncio
    async def test_missing_index_returns_false(self):
        """T006: 缺少索引时返回 False"""
        mock_pool = MagicMock()

        async def mock_fetch(query, *args):
            if "pg_indexes" in query:
                return []  # 无索引
            elif "pg_constraint" in query:
                return [{"conname": "dummy"}]

            return [{"column_name": "dummy"}]

        mock_conn = AsyncMock()
        mock_conn.fetch = mock_fetch
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        result = await inspect_novel_agent_books_chapters_schema(mock_pool)

        assert result["novel_agent_books_chapters"] is False
