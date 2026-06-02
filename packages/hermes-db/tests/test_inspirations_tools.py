from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from hermes_db_mcp.tools.inspirations import (
    create_novel_inspiration,
    find_similar_inspirations,
    get_inspiration,
)


class FakeAppContext:
    def __init__(self):
        self.pool = MagicMock()
        self.redis = MagicMock()
        self.http = MagicMock()


class FakeContext:
    def __init__(self, app_context):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = app_context


@pytest.mark.asyncio
async def test_create_novel_inspiration_invalid_category_returns_structured_error():
    result = await create_novel_inspiration(
        content="灵感",
        book_id=str(uuid4()),
        category="invalid",
        ctx=FakeContext(FakeAppContext()),
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "category"
    assert "valid_values" in result["details"]


@pytest.mark.asyncio
async def test_find_similar_inspirations_embedding_failure_returns_known_error(monkeypatch):
    async def mock_generate_embedding(http, text):
        return None

    monkeypatch.setattr(
        "hermes_db_mcp.tools.inspirations.generate_embedding",
        mock_generate_embedding,
    )

    result = await find_similar_inspirations(
        text="test",
        ctx=FakeContext(FakeAppContext()),
    )

    assert result["error"] == "embedding_unavailable"
    assert "message" in result


@pytest.mark.asyncio
async def test_get_inspiration_invalid_uuid_returns_structured_error():
    result = await get_inspiration("not-a-uuid", FakeContext(FakeAppContext()))

    assert result["error"] == "invalid_uuid"
    assert result["field"] == "id"


@pytest.mark.asyncio
async def test_create_novel_inspiration_success(monkeypatch):
    inspiration_id = uuid4()
    created_at = datetime.now()

    async def mock_generate_embedding(http, text):
        return [0.1] * 1024

    async def mock_insert_inspiration(pool, **kwargs):
        return {
            "id": inspiration_id,
            "status": "candidate",
            "created_at": created_at,
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.inspirations.generate_embedding",
        mock_generate_embedding,
    )
    monkeypatch.setattr(
        "hermes_db_mcp.tools.inspirations.inspiration_repo.insert_inspiration",
        mock_insert_inspiration,
    )
    monkeypatch.setattr(
        "hermes_db_mcp.tools.inspirations.update_recent_set",
        AsyncMock(),
    )

    result = await create_novel_inspiration(
        content="灵感",
        book_id=str(uuid4()),
        category="hook",
        ctx=FakeContext(FakeAppContext()),
    )

    assert result["id"] == str(inspiration_id)
    assert result["status"] == "candidate"
    assert result["created_at"] == str(created_at)
