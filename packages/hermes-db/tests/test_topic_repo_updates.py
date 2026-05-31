"""
测试 topic_repo 的更新能力 (Phase 2)
"""

import pytest
from uuid import uuid4

from hermes_db_mcp.repositories import topic_repo


@pytest.mark.asyncio
class TestGetByIdCompleteness:
    """T004: 确认 get_by_id 返回完整行"""

    async def test_get_by_id_returns_full_row(self, db_pool, sample_topic):
        """get_by_id 返回的字段集与工具层需要的字段一致"""
        row = await topic_repo.get_by_id(db_pool, topic_id=sample_topic["id"])

        assert row is not None
        # 核心字段
        assert "id" in row
        assert "title" in row
        assert "account" in row
        assert "status" in row
        # 可编辑字段
        assert "angle" in row
        assert "priority" in row
        assert "column_name" in row
        assert "resonance" in row
        assert "content" in row
        # 系统字段
        assert "source" in row
        assert "published_url" in row
        assert "created_at" in row
        assert "updated_at" in row


@pytest.mark.asyncio
class TestUpdateTopicFields:
    """T005: 测试 update_topic_fields"""

    async def test_update_single_field(self, db_pool, sample_topic):
        """单字段更新成功"""
        result = await topic_repo.update_topic_fields(
            db_pool,
            topic_id=sample_topic["id"],
            fields={"priority": "A"},
        )

        assert result is not None
        assert result["priority"] == "A"
        assert result["id"] == sample_topic["id"]

    async def test_update_multiple_fields(self, db_pool, sample_topic):
        """多字段更新成功"""
        result = await topic_repo.update_topic_fields(
            db_pool,
            topic_id=sample_topic["id"],
            fields={
                "priority": "C",
                "resonance": "高",
                "column_name": "技术专栏",
            },
        )

        assert result is not None
        assert result["priority"] == "C"
        assert result["resonance"] == "高"
        assert result["column_name"] == "技术专栏"

    async def test_update_with_embedding_none(self, db_pool, sample_topic):
        """embedding 设为 None 成功"""
        result = await topic_repo.update_topic_fields(
            db_pool,
            topic_id=sample_topic["id"],
            fields={"title": "新标题"},
            embedding=None,
        )

        assert result is not None
        assert result["title"] == "新标题"
        # embedding 字段不在 RETURNING 中,但更新应成功

    async def test_update_with_new_embedding(self, db_pool, sample_topic):
        """更新 embedding 向量成功"""
        new_embedding = [0.1] * 1024

        result = await topic_repo.update_topic_fields(
            db_pool,
            topic_id=sample_topic["id"],
            fields={"title": "新标题"},
            embedding=new_embedding,
        )

        assert result is not None
        assert result["title"] == "新标题"

    async def test_update_not_found(self, db_pool):
        """topic 不存在返回 None"""
        result = await topic_repo.update_topic_fields(
            db_pool,
            topic_id=uuid4(),
            fields={"priority": "A"},
        )

        assert result is None

    async def test_update_invalid_field_raises(self, db_pool, sample_topic):
        """不可编辑字段抛出异常"""
        with pytest.raises(ValueError, match="不可编辑字段"):
            await topic_repo.update_topic_fields(
                db_pool,
                topic_id=sample_topic["id"],
                fields={"status": "published"},
            )

    async def test_update_no_fields_raises(self, db_pool, sample_topic):
        """未提供任何字段抛出异常"""
        with pytest.raises(ValueError, match="未提供任何可更新字段"):
            await topic_repo.update_topic_fields(
                db_pool,
                topic_id=sample_topic["id"],
                fields={},
            )

    async def test_update_returns_full_row(self, db_pool, sample_topic):
        """RETURNING 返回完整行,字段集与 get_by_id 一致"""
        result = await topic_repo.update_topic_fields(
            db_pool,
            topic_id=sample_topic["id"],
            fields={"priority": "A"},
        )

        assert result is not None
        # 验证字段集与 get_by_id 一致
        assert "id" in result
        assert "title" in result
        assert "angle" in result
        assert "account" in result
        assert "status" in result
        assert "priority" in result
        assert "column_name" in result
        assert "resonance" in result
        assert "content" in result
        assert "source" in result
        assert "published_url" in result
        assert "created_at" in result
        assert "updated_at" in result


@pytest.mark.asyncio
class TestBatchUpdateFields:
    """T006: 测试 batch_update_fields"""

    async def test_batch_update_success(self, db_pool, sample_topics):
        """批量更新成功,返回实际更新的 id"""
        ids = [t["id"] for t in sample_topics[:3]]

        updated_ids = await topic_repo.batch_update_fields(
            db_pool,
            topic_ids=ids,
            fields={"priority": "A"},
        )

        assert len(updated_ids) == 3
        assert set(updated_ids) == set(ids)

    async def test_batch_update_partial_not_found(self, db_pool, sample_topics):
        """部分 id 不存在时,只更新存在的记录"""
        existing_id = sample_topics[0]["id"]
        non_existing_id = uuid4()

        updated_ids = await topic_repo.batch_update_fields(
            db_pool,
            topic_ids=[existing_id, non_existing_id],
            fields={"priority": "C"},
        )

        assert len(updated_ids) == 1
        assert updated_ids[0] == existing_id

    async def test_batch_update_multiple_fields(self, db_pool, sample_topics):
        """批量更新多个运营字段"""
        ids = [t["id"] for t in sample_topics[:2]]

        updated_ids = await topic_repo.batch_update_fields(
            db_pool,
            topic_ids=ids,
            fields={
                "priority": "B",
                "resonance": "中",
                "column_name": "运营专栏",
            },
        )

        assert len(updated_ids) == 2

        # 验证更新生效
        for topic_id in ids:
            row = await topic_repo.get_by_id(db_pool, topic_id=topic_id)
            assert row["priority"] == "B"
            assert row["resonance"] == "中"
            assert row["column_name"] == "运营专栏"

    async def test_batch_update_empty_ids(self, db_pool):
        """空 ids 列表返回空结果"""
        updated_ids = await topic_repo.batch_update_fields(
            db_pool,
            topic_ids=[],
            fields={"priority": "A"},
        )

        assert updated_ids == []

    async def test_batch_update_invalid_field_raises(self, db_pool, sample_topics):
        """批量更新不支持的字段抛出异常"""
        ids = [t["id"] for t in sample_topics[:2]]

        with pytest.raises(ValueError, match="批量更新不支持字段"):
            await topic_repo.batch_update_fields(
                db_pool,
                topic_ids=ids,
                fields={"title": "新标题"},
            )

    async def test_batch_update_no_fields_raises(self, db_pool, sample_topics):
        """未提供任何字段抛出异常"""
        ids = [t["id"] for t in sample_topics[:2]]

        with pytest.raises(ValueError, match="未提供任何可更新字段"):
            await topic_repo.batch_update_fields(
                db_pool,
                topic_ids=ids,
                fields={},
            )


@pytest.mark.asyncio
class TestListByFilterEnhanced:
    """T007: 测试增强的 list_by_filter"""

    async def test_list_with_priority_filter(
        self, db_pool, sample_topics_mixed_priority
    ):
        """按 priority 过滤"""
        items, total = await topic_repo.list_by_filter(
            db_pool,
            priority="A",
            limit=20,
            offset=0,
        )

        assert total > 0
        assert all(item["priority"] == "A" for item in items)

    async def test_list_exclude_published(self, db_pool, sample_topics_mixed_status):
        """排除 published 状态"""
        items, total = await topic_repo.list_by_filter(
            db_pool,
            exclude_published=True,
            limit=20,
            offset=0,
        )

        assert all(item["status"] != "published" for item in items)

    async def test_list_returns_operational_fields(self, db_pool, sample_topics):
        """返回项包含运营字段 resonance/column_name"""
        items, total = await topic_repo.list_by_filter(
            db_pool,
            limit=20,
            offset=0,
        )

        assert len(items) > 0
        for item in items:
            assert "resonance" in item
            assert "column_name" in item
            assert "priority" in item

    async def test_list_combined_filters(self, db_pool, sample_topics_mixed):
        """组合过滤条件"""
        items, total = await topic_repo.list_by_filter(
            db_pool,
            account="test_account",
            priority="B",
            exclude_published=True,
            limit=10,
            offset=0,
        )

        for item in items:
            assert item["account"] == "test_account"
            assert item["priority"] == "B"
            assert item["status"] != "published"
