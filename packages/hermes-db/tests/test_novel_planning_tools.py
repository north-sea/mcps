"""
测试 novel_planning MCP tools 的参数校验和错误处理

验证：
- T015: MCP tool 层参数校验（foreshadowing 限制、错误码返回）
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from hermes_db_mcp.tools import novel_planning


class TestBatchCreateBookPlanningTool:
    """T015: 测试 batch_create_book_planning tool"""

    @pytest.mark.asyncio
    async def test_foreshadowing_limit_exceeded(self):
        """US1-5: foreshadowing 数组超过 100 个时拒绝"""
        mock_ctx = MagicMock()
        mock_app = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app

        # Prepare data with 101 foreshadowing items
        foreshadowing = [
            {"title": f"fs{i}", "plantChapter": 1, "payoffChapter": 10, "priority": "high"}
            for i in range(101)
        ]

        # Execute
        result = await novel_planning.batch_create_book_planning(
            book_slug="test-book",
            outline={},
            worldbuilding={"rules": "test", "history": "test"},
            characters=[],
            foreshadowing=foreshadowing,
            ctx=mock_ctx,
        )

        # Verify error
        assert "error" in result
        assert result["error"] == "foreshadowing_limit_exceeded"
        assert "details" in result
        assert result["details"]["count"] == 101
        assert result["details"]["limit"] == 100

    @pytest.mark.asyncio
    async def test_missing_required_field(self):
        """参数校验：缺少必填字段"""
        mock_ctx = MagicMock()
        mock_app = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app

        # Execute with missing worldbuilding.rules
        result = await novel_planning.batch_create_book_planning(
            book_slug="test-book",
            outline={},
            worldbuilding={"history": "test"},  # missing 'rules'
            characters=[],
            foreshadowing=[],
            ctx=mock_ctx,
        )

        # Verify error
        assert "error" in result
        assert result["error"] == "missing_required_field"

    @pytest.mark.asyncio
    async def test_invalid_priority_value(self):
        """参数校验：priority 枚举值非法"""
        mock_ctx = MagicMock()
        mock_app = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app

        # Execute with invalid priority
        result = await novel_planning.batch_create_book_planning(
            book_slug="test-book",
            outline={},
            worldbuilding={"rules": "test", "history": "test"},
            characters=[],
            foreshadowing=[{"title": "fs1", "plantChapter": 1, "payoffChapter": 10, "priority": "invalid"}],
            ctx=mock_ctx,
        )

        # Verify error
        assert "error" in result
        assert result["error"] == "invalid_field"
        assert "foreshadowing[0].priority" in result["field"]

    @pytest.mark.asyncio
    @patch("hermes_db_mcp.tools.novel_planning.novel_planning_repo.batch_create_book_planning")
    async def test_book_not_found_error(self, mock_repo):
        """错误转换：book_not_found"""
        mock_ctx = MagicMock()
        mock_app = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app

        # Mock repository raises ValueError with book_not_found
        mock_repo.side_effect = ValueError("book_not_found: test-book")

        # Execute
        result = await novel_planning.batch_create_book_planning(
            book_slug="test-book",
            outline={},
            worldbuilding={"rules": "test", "history": "test"},
            characters=[],
            foreshadowing=[],
            ctx=mock_ctx,
        )

        # Verify error
        assert "error" in result
        assert result["error"] == "book_not_found"

    @pytest.mark.asyncio
    @patch("hermes_db_mcp.tools.novel_planning.novel_planning_repo.batch_create_book_planning")
    async def test_planning_already_exists_error(self, mock_repo):
        """错误转换：planning_already_exists"""
        mock_ctx = MagicMock()
        mock_app = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app

        # Mock repository raises ValueError with planning_already_exists
        mock_repo.side_effect = ValueError("planning_already_exists: test-book")

        # Execute
        result = await novel_planning.batch_create_book_planning(
            book_slug="test-book",
            outline={},
            worldbuilding={"rules": "test", "history": "test"},
            characters=[],
            foreshadowing=[],
            ctx=mock_ctx,
        )

        # Verify error
        assert "error" in result
        assert result["error"] == "planning_already_exists"


class TestGetChapterInputPackTool:
    """T015: 测试 get_chapter_input_pack tool"""

    @pytest.mark.asyncio
    async def test_invalid_chapter_number(self):
        """参数校验：chapter_number <= 0"""
        mock_ctx = MagicMock()
        mock_app = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app

        # Execute with chapter_number = 0
        result = await novel_planning.get_chapter_input_pack(
            book_slug="test-book",
            chapter_number=0,
            ctx=mock_ctx,
        )

        # Verify error
        assert "error" in result
        assert result["error"] == "invalid_field"
        assert result["field"] == "chapter_number"


class TestUpdateContextVersionTool:
    """T015: 测试 update_context_version tool"""

    @pytest.mark.asyncio
    async def test_invalid_changed_scope(self):
        """参数校验：changed_scope 枚举值非法"""
        mock_ctx = MagicMock()
        mock_app = MagicMock()
        mock_ctx.request_context.lifespan_context = mock_app

        # Execute with invalid changed_scope
        result = await novel_planning.update_context_version(
            book_slug="test-book",
            changed_scope="invalid_scope",
            ctx=mock_ctx,
        )

        # Verify error
        assert "error" in result
        assert result["error"] == "invalid_field"
        assert result["field"] == "changed_scope"
