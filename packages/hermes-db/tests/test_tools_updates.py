"""
测试 MCP 工具层 - update_topic 和 batch_update_topics (Phase 4)
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from hermes_db_mcp.tools.topics import (
    update_topic,
    batch_update_topics,
    list_topics,
    create_topic,
    list_revisit_chain,
)


class FakeAppContext:
    """模拟 AppContext"""

    def __init__(self, pool=None, redis=None, http=None):
        self.pool = pool or MagicMock()
        self.redis = redis or MagicMock()
        self.http = http or MagicMock()


class FakeContext:
    """模拟 FastMCP Context"""

    def __init__(self, app_context):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = app_context


@pytest.mark.asyncio
class TestUpdateTopic:
    """T011: 测试 update_topic 工具"""

    async def test_update_single_field_success(self, monkeypatch):
        """单字段更新成功"""
        topic_id = uuid4()
        current_row = {
            "id": topic_id,
            "title": "旧标题",
            "account": "test",
            "status": "draft",
            "priority": "B",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        updated_row = {**current_row, "priority": "A", "updated_at": datetime.now()}

        # Mock repository
        async def mock_get_by_id(pool, topic_id):
            return current_row

        async def mock_update_fields(pool, topic_id, fields, embedding):
            return updated_row

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.get_by_id", mock_get_by_id
        )
        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.update_topic_fields",
            mock_update_fields,
        )

        # Mock cache
        async def mock_cache_record(redis, key, data):
            pass

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.cache_record", mock_cache_record
        )

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await update_topic(
            id=str(topic_id),
            ctx=ctx,
            priority="A",
        )

        assert result["id"] == str(topic_id)
        assert "priority" in result["updated_fields"]
        assert result["embedding_regenerated"] is False

    async def test_update_title_regenerates_embedding(self, monkeypatch):
        """更新 title 触发 embedding 重算"""
        topic_id = uuid4()
        current_row = {
            "id": topic_id,
            "title": "旧标题",
            "angle": None,
            "account": "test",
            "status": "draft",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        updated_row = {**current_row, "title": "新标题", "updated_at": datetime.now()}

        async def mock_get_by_id(pool, topic_id):
            return current_row

        async def mock_update_fields(pool, topic_id, fields, embedding):
            assert embedding != ...  # 应该传入新 embedding
            return updated_row

        async def mock_generate_embedding(http, text):
            assert text == "新标题"
            return [0.1] * 1024

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.get_by_id", mock_get_by_id
        )
        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.update_topic_fields",
            mock_update_fields,
        )
        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.generate_embedding", mock_generate_embedding
        )
        monkeypatch.setattr("hermes_db_mcp.tools.topics.cache_record", AsyncMock())

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await update_topic(
            id=str(topic_id),
            ctx=ctx,
            title="新标题",
        )

        assert result["embedding_regenerated"] is True

    async def test_update_clear_fields(self, monkeypatch):
        """clear_fields 清空字段"""
        topic_id = uuid4()
        current_row = {
            "id": topic_id,
            "title": "标题",
            "angle": "旧角度",
            "resonance": "高",
            "account": "test",
            "status": "draft",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        updated_row = {
            **current_row,
            "angle": None,
            "resonance": None,
            "updated_at": datetime.now(),
        }

        async def mock_get_by_id(pool, topic_id):
            return current_row

        async def mock_update_fields(pool, topic_id, fields, embedding):
            assert fields["angle"] is None
            assert fields["resonance"] is None
            return updated_row

        async def mock_generate_embedding(http, text):
            # clear angle 会触发 embedding 重算
            return [0.1] * 1024

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.get_by_id", mock_get_by_id
        )
        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.update_topic_fields",
            mock_update_fields,
        )
        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.generate_embedding", mock_generate_embedding
        )
        monkeypatch.setattr("hermes_db_mcp.tools.topics.cache_record", AsyncMock())

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await update_topic(
            id=str(topic_id),
            ctx=ctx,
            clear_fields=["angle", "resonance"],
        )

        assert "angle" in result["updated_fields"]
        assert "resonance" in result["updated_fields"]
        assert result["embedding_regenerated"] is True  # angle 变化触发重算

    async def test_update_invalid_priority(self):
        """非法 priority 返回错误"""
        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await update_topic(
            id=str(uuid4()),
            ctx=ctx,
            priority="D",
        )

        assert result["error"] == "invalid_field"
        assert result["field"] == "priority"

    async def test_update_not_found(self, monkeypatch):
        """topic 不存在返回错误"""

        async def mock_get_by_id(pool, topic_id):
            return None

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.get_by_id", mock_get_by_id
        )

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await update_topic(
            id=str(uuid4()),
            ctx=ctx,
            priority="A",
        )

        assert result["error"] == "not_found"

    async def test_update_revisit_of_success(self, monkeypatch):
        """合法 revisit_of 更新成功且不重算 embedding"""
        topic_id = uuid4()
        parent_id = uuid4()
        current_row = {
            "id": topic_id,
            "title": "标题",
            "angle": None,
            "account": "test",
            "status": "draft",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        parent_row = {
            "id": parent_id,
            "title": "旧母题",
            "status": "published",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        updated_row = {
            **current_row,
            "revisit_of": parent_id,
            "updated_at": datetime.now(),
        }

        async def mock_get_by_id(pool, topic_id):
            if topic_id == parent_id:
                return parent_row
            return current_row

        async def mock_update_fields(pool, topic_id, fields, embedding):
            assert fields["revisit_of"] == parent_id
            assert fields["mother_theme"] == "拖延-早晨场景"
            assert embedding is ...
            return updated_row

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.get_by_id", mock_get_by_id
        )
        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.update_topic_fields",
            mock_update_fields,
        )
        monkeypatch.setattr("hermes_db_mcp.tools.topics.cache_record", AsyncMock())

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await update_topic(
            id=str(topic_id),
            ctx=ctx,
            revisit_of=str(parent_id),
            mother_theme="拖延-早晨场景",
        )

        assert result["embedding_regenerated"] is False
        assert "revisit_of" in result["updated_fields"]
        assert "mother_theme" in result["updated_fields"]

    async def test_update_revisit_of_self_rejected(self, monkeypatch):
        """revisit_of 指向自身返回结构化错误"""
        topic_id = uuid4()

        async def mock_get_by_id(pool, topic_id):
            return {"id": topic_id, "title": "标题", "status": "draft"}

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.get_by_id", mock_get_by_id
        )

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await update_topic(
            id=str(topic_id),
            ctx=ctx,
            revisit_of=str(topic_id),
        )

        assert result["error"] == "invalid_revisit_of_self"

    async def test_update_revisit_target_not_found(self, monkeypatch):
        """revisit_of 目标不存在返回结构化错误"""
        topic_id = uuid4()
        parent_id = uuid4()

        async def mock_get_by_id(pool, topic_id):
            if topic_id == parent_id:
                return None
            return {"id": topic_id, "title": "标题", "status": "draft"}

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.get_by_id", mock_get_by_id
        )

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await update_topic(
            id=str(topic_id),
            ctx=ctx,
            revisit_of=str(parent_id),
        )

        assert result["error"] == "revisit_target_not_found"


@pytest.mark.asyncio
class TestCreateTopicRevisit:
    """测试 create_topic 的 revisit_of 参数"""

    async def test_create_topic_with_revisit_of(self, monkeypatch):
        parent_id = uuid4()
        new_id = uuid4()
        created_at = datetime.now()

        async def mock_get_by_id(pool, topic_id):
            assert topic_id == parent_id
            return {"id": parent_id, "title": "旧母题"}

        async def mock_generate_embedding(http, text):
            return [0.1] * 1024

        async def mock_insert_topic(pool, **kwargs):
            assert kwargs["revisit_of"] == parent_id
            assert kwargs["mother_theme"] == "拖延-早晨场景"
            return {"id": new_id, "status": "draft", "created_at": created_at}

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.get_by_id", mock_get_by_id
        )
        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.generate_embedding", mock_generate_embedding
        )
        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.insert_topic", mock_insert_topic
        )
        monkeypatch.setattr("hermes_db_mcp.tools.topics.update_recent_set", AsyncMock())

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await create_topic(
            title="新角度标题",
            account="test",
            ctx=ctx,
            revisit_of=str(parent_id),
            mother_theme="拖延-早晨场景",
        )

        assert result["id"] == str(new_id)
        assert result["status"] == "draft"

    async def test_create_topic_revisit_target_not_found(self, monkeypatch):
        async def mock_get_by_id(pool, topic_id):
            return None

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.get_by_id", mock_get_by_id
        )

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await create_topic(
            title="新角度标题",
            account="test",
            ctx=ctx,
            revisit_of=str(uuid4()),
        )

        assert result["error"] == "revisit_target_not_found"


@pytest.mark.asyncio
class TestBatchUpdateTopics:
    """T012: 测试 batch_update_topics 工具"""

    async def test_batch_update_success(self, monkeypatch):
        """批量更新成功"""
        id1 = uuid4()
        id2 = uuid4()

        async def mock_batch_update(pool, topic_ids, fields):
            return [id1, id2]

        async def mock_delete_cached(redis, *keys):
            pass

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.batch_update_fields",
            mock_batch_update,
        )
        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.delete_cached", mock_delete_cached
        )

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await batch_update_topics(
            ids=[str(id1), str(id2)],
            ctx=ctx,
            priority="A",
        )

        assert result["requested_count"] == 2
        assert result["unique_count"] == 2
        assert result["matched"] == 2
        assert result["updated"] == 2
        assert "priority" in result["updated_fields"]
        assert result["not_found_ids"] == []

    async def test_batch_update_with_duplicates(self, monkeypatch):
        """批量更新自动去重"""
        id1 = uuid4()

        async def mock_batch_update(pool, topic_ids, fields):
            return [id1]

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.batch_update_fields",
            mock_batch_update,
        )
        monkeypatch.setattr("hermes_db_mcp.tools.topics.delete_cached", AsyncMock())

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await batch_update_topics(
            ids=[str(id1), str(id1), str(id1)],
            ctx=ctx,
            priority="B",
        )

        assert result["requested_count"] == 3
        assert result["unique_count"] == 1
        assert result["matched"] == 1

    async def test_batch_update_partial_not_found(self, monkeypatch):
        """部分 id 不存在"""
        id1 = uuid4()
        id2 = uuid4()

        async def mock_batch_update(pool, topic_ids, fields):
            return [id1]  # 只有 id1 存在

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.batch_update_fields",
            mock_batch_update,
        )
        monkeypatch.setattr("hermes_db_mcp.tools.topics.delete_cached", AsyncMock())

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await batch_update_topics(
            ids=[str(id1), str(id2)],
            ctx=ctx,
            priority="C",
        )

        assert result["matched"] == 1
        assert str(id2) in result["not_found_ids"]

    async def test_batch_update_invalid_field(self):
        """非法 resonance 返回错误"""
        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await batch_update_topics(
            ids=[str(uuid4())],
            ctx=ctx,
            resonance="极高",
        )

        assert result["error"] == "invalid_field"
        assert result["field"] == "resonance"


@pytest.mark.asyncio
class TestListTopicsEnhanced:
    """T013: 测试增强的 list_topics 工具"""

    async def test_list_with_priority_filter(self, monkeypatch):
        """priority 过滤"""

        async def mock_list_by_filter(pool, **kwargs):
            assert kwargs["priority"] == "A"
            return [], 0

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.list_by_filter", mock_list_by_filter
        )

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await list_topics(
            ctx=ctx,
            priority="A",
        )

        assert result["items"] == []
        assert result["total"] == 0

    async def test_list_exclude_published(self, monkeypatch):
        """exclude_published 参数"""

        async def mock_list_by_filter(pool, **kwargs):
            assert kwargs["exclude_published"] is True
            return [], 0

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.list_by_filter", mock_list_by_filter
        )

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await list_topics(
            ctx=ctx,
            exclude_published=True,
        )

        assert result["total"] == 0

    async def test_list_invalid_priority(self):
        """非法 priority 返回错误"""
        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await list_topics(
            ctx=ctx,
            priority="D",
        )

        assert result["error"] == "invalid_field"
        assert result["field"] == "priority"

    async def test_list_invalid_pagination(self):
        """非法分页参数返回错误"""
        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await list_topics(
            ctx=ctx,
            limit=101,
        )

        assert result["error"] == "invalid_field"
        assert result["field"] == "limit"


@pytest.mark.asyncio
class TestListRevisitChain:
    """测试 list_revisit_chain 工具"""

    async def test_list_revisit_chain_success(self, monkeypatch):
        topic_id = uuid4()
        parent_id = uuid4()
        created_at = datetime.now()

        async def mock_get_revisit_chain(pool, topic_id, max_depth):
            return {
                "items": [
                    {
                        "id": topic_id,
                        "title": "新选题",
                        "status": "draft",
                        "created_at": created_at,
                        "published_url": None,
                    },
                    {
                        "id": parent_id,
                        "title": "旧母题",
                        "status": "published",
                        "created_at": created_at,
                        "published_url": "https://example.com/a",
                    },
                ],
                "truncated": False,
            }

        monkeypatch.setattr(
            "hermes_db_mcp.tools.topics.topic_repo.get_revisit_chain",
            mock_get_revisit_chain,
        )

        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await list_revisit_chain(str(topic_id), ctx, max_depth=20)

        assert result["truncated"] is False
        assert result["items"][0]["id"] == str(topic_id)
        assert result["items"][1]["id"] == str(parent_id)
        assert result["items"][0]["created_at"] == str(created_at)

    async def test_list_revisit_chain_invalid_uuid(self):
        app = FakeAppContext()
        ctx = FakeContext(app)

        result = await list_revisit_chain("not-a-uuid", ctx)

        assert result["error"] == "invalid_uuid"
        assert result["field"] == "topic_id"
