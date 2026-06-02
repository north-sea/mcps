from unittest.mock import AsyncMock

import pytest

from hermes_db_mcp.services.schema import inspect_topic_schema


class FakeRow(dict):
    def __getitem__(self, key):
        return self.get(key)


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, fetch_results):
        self.conn = AsyncMock()
        self.conn.fetch = AsyncMock(side_effect=fetch_results)

    def acquire(self):
        return FakeAcquire(self.conn)


@pytest.mark.asyncio
async def test_inspect_topic_schema_returns_true_for_migrated_topics():
    pool = FakePool(
        [
            [
                FakeRow(column_name="embedding"),
                FakeRow(column_name="revisit_of"),
                FakeRow(column_name="mother_theme"),
            ],
            [
                FakeRow(conname="fk_topics_revisit_of"),
                FakeRow(conname="chk_topics_revisit_of_not_self"),
            ],
        ]
    )

    result = await inspect_topic_schema(pool)

    assert result == {
        "topic_bucket": True,
        "topic_revisit_of": True,
        "list_revisit_chain": True,
    }


@pytest.mark.asyncio
async def test_inspect_topic_schema_reflects_missing_migration():
    pool = FakePool(
        [
            [FakeRow(column_name="embedding")],
            [],
        ]
    )

    result = await inspect_topic_schema(pool)

    assert result == {
        "topic_bucket": True,
        "topic_revisit_of": False,
        "list_revisit_chain": False,
    }
