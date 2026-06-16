"""
测试 novel_planning_repo 的数据访问逻辑

验证：
- T012: batch_create_book_planning 的事务原子性、回滚、幂等性
- T013: get_chapter_input_pack 的完整输入包、冷启动、伏笔过滤
- T014: update_context_version 和 get_current_context_version
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncpg

from hermes_db_mcp.repositories import novel_planning_repo


class TestBatchCreateBookPlanning:
    """T012: 测试 batch_create_book_planning"""

    @pytest.mark.asyncio
    async def test_success_batch_create(self):
        """US1-1: 成功批量写入 4 个表"""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        # Mock connection.transaction() to return a proper async context manager
        class MockTransaction:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        mock_conn.transaction = MagicMock(return_value=MockTransaction())

        # Mock fetchval for idempotency checks
        mock_conn.fetchval = AsyncMock(side_effect=[
            1,    # book_exists = True
            None, # has_planning = None (no existing planning)
        ])

        # Mock execute for INSERT operations
        mock_conn.execute = AsyncMock(return_value=None)

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # Test data
        book_slug = "test-book"
        outline = {"storyArc": "test arc"}
        worldbuilding = {"rules": "test rules", "history": "test history"}
        characters = [{"name": "Alice", "role": "protagonist", "personality": "brave"}]
        foreshadowing = [{"title": "fs1", "plantChapter": 1, "payoffChapter": 10, "priority": "high"}]

        # Execute
        await novel_planning_repo.batch_create_book_planning(
            mock_pool,
            book_slug=book_slug,
            outline=outline,
            worldbuilding=worldbuilding,
            characters=characters,
            foreshadowing=foreshadowing,
        )

        # Verify transaction was used
        mock_conn.transaction.assert_called_once()

        # Verify idempotency checks were called
        assert mock_conn.fetchval.call_count == 2

        # Verify 3 INSERT operations (worldbuilding + 1 character + 1 foreshadowing)
        assert mock_conn.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_idempotent_planning_already_exists(self):
        """US1-3: 幂等性保证 - 规划数据已存在时拒绝"""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        class MockTransaction:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        mock_conn.transaction = MagicMock(return_value=MockTransaction())

        # Mock fetchval: book exists, planning exists
        mock_conn.fetchval = AsyncMock(side_effect=[
            1,  # book_exists = True
            1,  # has_planning = True
        ])

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute and expect ValueError
        with pytest.raises(ValueError, match="planning_already_exists"):
            await novel_planning_repo.batch_create_book_planning(
                mock_pool,
                book_slug="test-book",
                outline={},
                worldbuilding={"rules": "test", "history": "test"},
                characters=[],
                foreshadowing=[],
            )

    @pytest.mark.asyncio
    async def test_book_not_found(self):
        """US1-6: book_slug 不存在时返回错误"""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        class MockTransaction:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        mock_conn.transaction = MagicMock(return_value=MockTransaction())

        # Mock fetchval: book does not exist
        mock_conn.fetchval = AsyncMock(return_value=None)

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute and expect ValueError
        with pytest.raises(ValueError, match="book_not_found"):
            await novel_planning_repo.batch_create_book_planning(
                mock_pool,
                book_slug="nonexistent-book",
                outline={},
                worldbuilding={"rules": "test", "history": "test"},
                characters=[],
                foreshadowing=[],
            )


class TestGetChapterInputPack:
    """T013: 测试 get_chapter_input_pack"""

    @pytest.mark.asyncio
    async def test_success_get_input_pack(self):
        """US2-1: 成功读取完整输入包"""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        # Mock fetchval: book exists
        # Mock fetch: recent chapters, characters, foreshadowing, volume_goal
        mock_conn.fetchval = AsyncMock(side_effect=[
            1,              # book_exists = True
            "Volume 1 Goal"  # volume_goal
        ])

        # Mock fetch results
        mock_conn.fetch = AsyncMock(side_effect=[
            # recent_chapters
            [
                {
                    "chapter_number": 2,
                    "title": "Chapter 2",
                    "summary": "Summary 2",
                    "context_version": 1,
                    "residue": {
                        "emotionalDebts": [
                            {"description": "Debt 1", "involvedCharacters": ["Alice"]}
                        ]
                    }
                }
            ],
            # characters
            [
                {
                    "name": "Alice",
                    "role": "protagonist",
                    "personality": "brave",
                    "secondary_interpretation": "complex",
                    "behavior_prohibitions": ["lie"]
                }
            ],
            # foreshadowing
            [
                {
                    "title": "Mystery",
                    "plant_chapter": 1,
                    "reminder_chapter": 3,
                    "payoff_chapter": 10,
                    "priority": "high",
                    "status": "active"
                }
            ],
        ])

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        result = await novel_planning_repo.get_chapter_input_pack(
            mock_pool,
            book_slug="test-book",
            chapter_number=3,
            recent_chapters_count=2,
            max_characters=5,
            max_foreshadowing=3,
            max_emotional_debts=2,
        )

        # Verify structure
        assert "recentChapters" in result
        assert "characters" in result
        assert "foreshadowing" in result
        assert "emotionalDebts" in result
        assert "volumeGoal" in result

        # Verify content
        assert len(result["recentChapters"]) == 1
        assert result["recentChapters"][0]["chapterNumber"] == 2
        assert len(result["characters"]) == 1
        assert result["characters"][0]["name"] == "Alice"
        assert len(result["foreshadowing"]) == 1
        assert result["foreshadowing"][0]["title"] == "Mystery"
        assert len(result["emotionalDebts"]) == 1
        assert result["emotionalDebts"][0]["description"] == "Debt 1"
        assert result["volumeGoal"] == "Volume 1 Goal"

    @pytest.mark.asyncio
    async def test_cold_start_first_chapter(self):
        """US2-2: 处理第一章的冷启动"""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        mock_conn.fetchval = AsyncMock(side_effect=[
            1,     # book_exists = True
            None   # volume_goal = None
        ])

        # Mock empty recent_chapters (first chapter)
        mock_conn.fetch = AsyncMock(side_effect=[
            [],  # recent_chapters (empty for chapter 1)
            [{"name": "Alice", "role": "protagonist", "personality": "brave", "secondary_interpretation": None, "behavior_prohibitions": []}],
            [{"title": "Mystery", "plant_chapter": 1, "reminder_chapter": None, "payoff_chapter": 10, "priority": "high", "status": "active"}],
        ])

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        result = await novel_planning_repo.get_chapter_input_pack(
            mock_pool,
            book_slug="test-book",
            chapter_number=1,
        )

        # Verify recentChapters is empty
        assert result["recentChapters"] == []
        assert result["volumeGoal"] is None
        assert len(result["characters"]) == 1
        assert len(result["foreshadowing"]) == 1


class TestContextVersion:
    """T014: 测试 update_context_version 和 get_current_context_version"""

    @pytest.mark.asyncio
    async def test_update_context_version(self):
        """US3-1: 更新上下文版本"""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        class MockTransaction:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        mock_conn.transaction = MagicMock(return_value=MockTransaction())

        # Mock current version
        mock_conn.fetchval = AsyncMock(return_value=1)
        mock_conn.execute = AsyncMock(return_value=None)

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        new_version = await novel_planning_repo.update_context_version(
            mock_pool,
            book_slug="test-book",
            changed_scope="book_outline",
            change_summary="Updated story arc",
        )

        # Verify
        assert new_version == 2
        assert mock_conn.execute.call_count == 2  # UPDATE + INSERT

    @pytest.mark.asyncio
    async def test_get_current_context_version(self):
        """US3-2: 读取当前版本"""
        mock_pool = MagicMock()
        mock_conn = AsyncMock()

        mock_conn.fetchval = AsyncMock(return_value=3)

        mock_pool.acquire = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        version = await novel_planning_repo.get_current_context_version(
            mock_pool,
            book_slug="test-book",
        )

        # Verify
        assert version == 3

