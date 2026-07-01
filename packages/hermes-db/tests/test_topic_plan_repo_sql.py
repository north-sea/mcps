from datetime import datetime, timezone
from uuid import uuid4

import pytest

from hermes_db_mcp.repositories import topic_plan_repo


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, *, created=True, current_status="planned"):
        self.created = created
        self.current_status = current_status
        self.fetchrow_calls = []
        self.fetch_calls = []
        self.fetchval_calls = []
        self.execute_calls = []
        self.plan_id = uuid4()
        self.candidate_id = uuid4()
        self.topic_id = uuid4()

    def transaction(self):
        return FakeTransaction()

    def _plan_row(self, *, status="planned"):
        now = datetime(2026, 7, 1, tzinfo=timezone.utc)
        return {
            "plan_id": self.plan_id,
            "candidate_id": self.candidate_id,
            "account_id": "wechat-ai-tools",
            "track_id": "ai-productivity",
            "status": status,
            "recommended_angle_index": 0,
            "topic_angles": '[{"title": "A"}, {"title": "B"}, {"title": "C"}]',
            "outline_pack": '{"title": "Outline"}',
            "writing_brief": '{"tone": "calm"}',
            "image_brief": '{"cover": {}}',
            "evidence": '{"signals": []}',
            "llm_metadata": '{"model": "test"}',
            "rejection_reason": None,
            "topic_id": self.topic_id if status == "consumed" else None,
            "source": "wechat-agent",
            "created_at": now,
            "updated_at": now,
            "consumed_at": now if status == "consumed" else None,
        }

    async def fetchrow(self, sql, *params):
        self.fetchrow_calls.append((sql, params))
        if "INSERT INTO hermes.topic_plans" in sql:
            return {**self._plan_row(status=params[3]), "created": self.created}
        if "UPDATE hermes.topic_candidates" in sql:
            return {"id": params[0], "status": "shortlisted"}
        if "SELECT status FROM hermes.topic_plans" in sql:
            return {"status": self.current_status}
        if "UPDATE hermes.topic_plans" in sql:
            return self._plan_row(status=params[1])
        if "FROM hermes.topic_plans" in sql:
            return self._plan_row()
        return None

    async def fetch(self, sql, *params):
        self.fetch_calls.append((sql, params))
        return [self._plan_row()]

    async def fetchval(self, sql, *params):
        self.fetchval_calls.append((sql, params))
        return 1

    async def execute(self, sql, *params):
        self.execute_calls.append((sql, params))
        return "UPDATE 1"


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, conn=None):
        self.conn = conn or FakeConnection()

    def acquire(self):
        return FakeAcquire(self.conn)


@pytest.mark.asyncio
async def test_upsert_topic_plan_uses_candidate_conflict_and_returns_created():
    pool = FakePool()

    result = await topic_plan_repo.upsert_topic_plan(
        pool,
        candidate_id=pool.conn.candidate_id,
        account_id="wechat-ai-tools",
        track_id="ai-productivity",
        status="planned",
        recommended_angle_index=0,
        topic_angles=[{"title": "A"}, {"title": "B"}, {"title": "C"}],
        outline_pack={"title": "Outline"},
        writing_brief={"tone": "calm"},
        image_brief={"cover": {}},
        evidence={"signals": []},
        llm_metadata={"model": "test"},
        source="wechat-agent",
    )

    sql, params = pool.conn.fetchrow_calls[0]
    assert "INSERT INTO hermes.topic_plans" in sql
    assert "ON CONFLICT (candidate_id)" in sql
    assert "RETURNING" in sql
    assert params[0] == pool.conn.candidate_id
    assert params[5] == '[{"title": "A"}, {"title": "B"}, {"title": "C"}]'
    assert result["upserted"] == "created"
    assert result["item"]["status"] == "planned"


@pytest.mark.asyncio
async def test_upsert_topic_plan_shortlists_candidate_only_for_planned_status():
    pool = FakePool()

    await topic_plan_repo.upsert_topic_plan(
        pool,
        candidate_id=pool.conn.candidate_id,
        account_id="wechat-ai-tools",
        status="planned",
        topic_angles=[{"title": "A"}, {"title": "B"}, {"title": "C"}],
        outline_pack={},
        writing_brief={},
        image_brief={},
        mark_candidate_shortlisted=True,
    )

    sql, params = pool.conn.fetchrow_calls[1]
    assert "UPDATE hermes.topic_candidates" in sql
    assert "status IN ('new', 'shortlisted')" in sql
    assert params == (pool.conn.candidate_id,)


@pytest.mark.asyncio
async def test_upsert_topic_plan_rejected_does_not_shortlist_candidate():
    pool = FakePool()

    await topic_plan_repo.upsert_topic_plan(
        pool,
        candidate_id=pool.conn.candidate_id,
        account_id="wechat-ai-tools",
        status="rejected",
        rejection_reason="off track",
        mark_candidate_shortlisted=True,
    )

    assert not any("UPDATE hermes.topic_candidates" in sql for sql, _ in pool.conn.fetchrow_calls)


@pytest.mark.asyncio
async def test_upsert_topic_plan_raises_when_shortlist_update_does_not_match_candidate():
    class MissingCandidateConnection(FakeConnection):
        async def fetchrow(self, sql, *params):
            if "UPDATE hermes.topic_candidates" in sql:
                self.fetchrow_calls.append((sql, params))
                return None
            return await super().fetchrow(sql, *params)

    pool = FakePool(MissingCandidateConnection())

    with pytest.raises(topic_plan_repo.TopicPlanShortlistConflict):
        await topic_plan_repo.upsert_topic_plan(
            pool,
            candidate_id=pool.conn.candidate_id,
            account_id="wechat-ai-tools",
            status="planned",
            topic_angles=[{"title": "A"}, {"title": "B"}, {"title": "C"}],
            outline_pack={},
            writing_brief={},
            image_brief={},
            mark_candidate_shortlisted=True,
        )


@pytest.mark.asyncio
async def test_list_topic_plans_filters_by_account_track_and_status():
    pool = FakePool()

    items, total = await topic_plan_repo.list_topic_plans(
        pool,
        account_id="wechat-ai-tools",
        track_id="ai-productivity",
        status="planned",
        limit=10,
        offset=5,
    )

    count_sql, count_params = pool.conn.fetchval_calls[0]
    list_sql, list_params = pool.conn.fetch_calls[0]
    assert "account_id = $1" in count_sql
    assert "track_id = $2" in count_sql
    assert "status = $3" in count_sql
    assert "ORDER BY created_at DESC" in list_sql
    assert count_params == ("wechat-ai-tools", "ai-productivity", "planned")
    assert list_params == ("wechat-ai-tools", "ai-productivity", "planned", 10, 5)
    assert total == 1
    assert items[0]["account_id"] == "wechat-ai-tools"


@pytest.mark.asyncio
async def test_update_topic_plan_status_returns_previous_status():
    pool = FakePool(FakeConnection(current_status="planned"))

    result = await topic_plan_repo.update_topic_plan_status(
        pool,
        plan_id=pool.conn.plan_id,
        status="consumed",
        topic_id=pool.conn.topic_id,
    )

    assert result["previous_status"] == "planned"
    assert result["status"] == "consumed"
    assert result["topic_id"] == pool.conn.topic_id


@pytest.mark.asyncio
async def test_update_topic_plan_status_rejects_invalid_transition():
    pool = FakePool(FakeConnection(current_status="archived"))

    with pytest.raises(topic_plan_repo.TopicPlanInvalidTransition) as exc:
        await topic_plan_repo.update_topic_plan_status(
            pool,
            plan_id=pool.conn.plan_id,
            status="planned",
        )

    assert exc.value.current == "archived"
    assert exc.value.target == "planned"
    assert exc.value.allowed == []
