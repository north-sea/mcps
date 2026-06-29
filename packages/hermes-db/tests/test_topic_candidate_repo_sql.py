from datetime import datetime, timezone
from uuid import uuid4

import pytest

from hermes_db_mcp.repositories import topic_candidate_repo


class FakeConnection:
    def __init__(self):
        self.fetchrow_calls = []
        self.fetch_calls = []
        self.fetchval_calls = []

    async def fetchrow(self, sql, *params):
        self.fetchrow_calls.append((sql, params))
        if "INSERT INTO hermes.topic_candidates" in sql:
            return {
                "id": uuid4(),
                "status": "new",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "created": True,
            }
        if "UPDATE hermes.topic_candidates" in sql:
            return {"id": params[1], "status": params[0], "topic_id": None}
        return None

    async def fetch(self, sql, *params):
        self.fetch_calls.append((sql, params))
        return []

    async def fetchval(self, sql, *params):
        self.fetchval_calls.append((sql, params))
        return 0


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self):
        self.conn = FakeConnection()

    def acquire(self):
        return FakeAcquire(self.conn)


@pytest.mark.asyncio
async def test_upsert_candidate_uses_account_track_dedupe_conflict():
    pool = FakePool()
    captured_at = datetime(2026, 6, 29, tzinfo=timezone.utc)

    row = await topic_candidate_repo.upsert_candidate(
        pool,
        account_id="wechat-ai-tools",
        track_id="ai-productivity",
        source="mock",
        source_url="https://example.invalid/topic",
        source_item_id="mock-1",
        title="Mock topic",
        summary="Summary",
        hot_score=0.8,
        fit_score=0.9,
        novelty_score=0.7,
        dedupe_key="mock:1",
        captured_at=captured_at,
        raw_payload={"id": "mock-1"},
    )

    sql, params = pool.conn.fetchrow_calls[0]
    assert row["created"] is True
    assert "INSERT INTO hermes.topic_candidates" in sql
    assert "ON CONFLICT (account_id, track_id, dedupe_key)" in sql
    assert "RETURNING id, status, created_at, updated_at, (xmax = 0) AS created" in sql
    assert params[0] == "wechat-ai-tools"
    assert params[1] == "ai-productivity"
    assert params[10] == "mock:1"
    assert params[12] == '{"id": "mock-1"}'


@pytest.mark.asyncio
async def test_list_candidates_defaults_to_hiding_rejected_and_expired():
    pool = FakePool()

    await topic_candidate_repo.list_candidates(
        pool,
        account_id="wechat-ai-tools",
        track_id="ai-productivity",
        limit=20,
        offset=0,
    )

    count_sql, count_params = pool.conn.fetchval_calls[0]
    list_sql, list_params = pool.conn.fetch_calls[0]
    assert "status NOT IN ('rejected', 'expired')" in count_sql
    assert "raw_payload" not in list_sql
    assert count_params == ("wechat-ai-tools", "ai-productivity")
    assert list_params == ("wechat-ai-tools", "ai-productivity", 20, 0)


@pytest.mark.asyncio
async def test_expire_candidates_updates_only_active_candidates():
    pool = FakePool()

    await topic_candidate_repo.expire_candidates(
        pool,
        account_id="wechat-ai-tools",
        captured_before=datetime(2026, 6, 28, tzinfo=timezone.utc),
        limit=50,
    )

    sql, params = pool.conn.fetch_calls[0]
    assert "status IN ('new', 'shortlisted')" in sql
    assert "SET status = 'expired'" in sql
    assert params[0] == "wechat-ai-tools"
    assert params[2] == 50
