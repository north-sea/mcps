"""
测试 cache 服务的批量删除和序列化 helper (Phase 3)
"""

import pytest
from datetime import datetime
from uuid import uuid4

from hermes_db_mcp.services.cache import delete_cached, serialize_topic_row


class FakeRedis:
    """模拟 Redis 客户端"""

    def __init__(self, should_fail=False):
        self.deleted_keys = []
        self.should_fail = should_fail

    async def delete(self, *keys):
        if self.should_fail:
            raise Exception("Redis error")
        self.deleted_keys.extend(keys)


@pytest.mark.asyncio
class TestDeleteCached:
    """T008: 测试 delete_cached"""

    async def test_delete_single_key(self):
        """删除单个缓存键"""
        redis = FakeRedis()
        await delete_cached(redis, "hermes:topic:123")

        assert redis.deleted_keys == ["hermes:topic:123"]

    async def test_delete_multiple_keys(self):
        """批量删除多个缓存键"""
        redis = FakeRedis()
        await delete_cached(
            redis,
            "hermes:topic:123",
            "hermes:topic:456",
            "hermes:topic:789",
        )

        assert len(redis.deleted_keys) == 3
        assert "hermes:topic:123" in redis.deleted_keys
        assert "hermes:topic:456" in redis.deleted_keys
        assert "hermes:topic:789" in redis.deleted_keys

    async def test_delete_empty_keys(self):
        """空键列表不调用 Redis"""
        redis = FakeRedis()
        await delete_cached(redis)

        assert redis.deleted_keys == []

    async def test_delete_redis_failure_silent(self):
        """Redis 异常不抛出"""
        redis = FakeRedis(should_fail=True)

        # 不应抛出异常
        await delete_cached(redis, "hermes:topic:123")


class TestSerializeTopicRow:
    """T009: 测试 serialize_topic_row"""

    def test_serialize_converts_datetime_fields(self):
        """id/created_at/updated_at 转为字符串"""
        topic_id = uuid4()
        created_at = datetime(2025, 1, 1, 12, 0, 0)
        updated_at = datetime(2025, 1, 2, 12, 0, 0)

        row = {
            "id": topic_id,
            "title": "测试选题",
            "account": "test_account",
            "status": "draft",
            "priority": "B",
            "created_at": created_at,
            "updated_at": updated_at,
        }

        result = serialize_topic_row(row)

        assert result["id"] == str(topic_id)
        assert result["created_at"] == str(created_at)
        assert result["updated_at"] == str(updated_at)
        # 其他字段保持原样
        assert result["title"] == "测试选题"
        assert result["account"] == "test_account"
        assert result["status"] == "draft"
        assert result["priority"] == "B"

    def test_serialize_preserves_other_fields(self):
        """其他字段类型保持不变"""
        row = {
            "id": uuid4(),
            "title": "测试选题",
            "angle": "技术视角",
            "priority": "A",
            "resonance": "高",
            "column_name": "技术专栏",
            "content": "详细内容",
            "source": "topic-inbox",
            "published_url": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        result = serialize_topic_row(row)

        assert result["title"] == "测试选题"
        assert result["angle"] == "技术视角"
        assert result["priority"] == "A"
        assert result["resonance"] == "高"
        assert result["column_name"] == "技术专栏"
        assert result["content"] == "详细内容"
        assert result["source"] == "topic-inbox"
        assert result["published_url"] is None

    def test_serialize_handles_none_values(self):
        """处理 None 值"""
        row = {
            "id": uuid4(),
            "title": "测试选题",
            "angle": None,
            "column_name": None,
            "resonance": None,
            "content": None,
            "published_url": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        result = serialize_topic_row(row)

        assert result["angle"] is None
        assert result["column_name"] is None
        assert result["resonance"] is None
        assert result["content"] is None
        assert result["published_url"] is None

    def test_serialize_field_set_matches_get_topic(self):
        """序列化字段集与 get_topic 返回一致"""
        # 模拟 get_by_id 返回的完整行
        row = {
            "id": uuid4(),
            "title": "测试选题",
            "angle": "技术视角",
            "account": "test_account",
            "status": "draft",
            "priority": "B",
            "column_name": "技术专栏",
            "resonance": "高",
            "content": "详细内容",
            "source": "topic-inbox",
            "published_url": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        result = serialize_topic_row(row)

        # 验证所有字段都存在
        expected_fields = {
            "id",
            "title",
            "angle",
            "account",
            "status",
            "priority",
            "column_name",
            "resonance",
            "content",
            "source",
            "published_url",
            "created_at",
            "updated_at",
        }
        assert set(result.keys()) == expected_fields
