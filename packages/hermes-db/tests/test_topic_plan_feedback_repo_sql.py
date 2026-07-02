from datetime import datetime, timezone
from uuid import uuid4

import pytest

from hermes_db_mcp.repositories import topic_plan_feedback_repo


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, *, plan_exists=True, insert_conflict=False):
        self.plan_exists = plan_exists
        self.insert_conflict = insert_conflict
        self.fetchrow_calls = []
        self.fetch_calls = []
        self.fetchval_calls = []
        self.plan_id = uuid4()
        self.event_id = uuid4()
        self.topic_id = uuid4()

    def transaction(self):
        return FakeTransaction()

    def _plan_row(self):
        return {
            "plan_id": self.plan_id,
            "account_id": "wechat-ai-tools",
            "track_id": "ai-productivity",
            "source": "wechat-agent",
            "llm_metadata": '{"config_snapshot": {}}',
        }

    def _event_row(self):
        now = datetime(2026, 7, 2, tzinfo=timezone.utc)
        return {
            "event_id": self.event_id,
            "plan_id": self.plan_id,
            "account_id": "wechat-ai-tools",
            "track_id": "ai-productivity",
            "event_type": "accepted",
            "dedupe_key": "ui-click-1",
            "reason_tags": '["worth-writing"]',
            "note": "looks good",
            "decided_by": "user",
            "topic_id": self.topic_id,
            "metadata": '{"publication_id": "pub-1"}',
            "event_at": now,
            "created_at": now,
        }

    async def fetchrow(self, sql, *params):
        self.fetchrow_calls.append((sql, params))
        if "FROM hermes.topic_plans" in sql:
            return self._plan_row() if self.plan_exists else None
        if "INSERT INTO hermes.topic_plan_feedback_events" in sql:
            return None if self.insert_conflict else self._event_row()
        if "FROM hermes.topic_plan_feedback_events" in sql:
            return self._event_row()
        return None

    async def fetch(self, sql, *params):
        self.fetch_calls.append((sql, params))
        return [self._event_row()]

    async def fetchval(self, sql, *params):
        self.fetchval_calls.append((sql, params))
        return 1


class ReportConnection(FakeConnection):
    def __init__(self, rows):
        super().__init__()
        self.rows = rows

    async def fetch(self, sql, *params):
        self.fetch_calls.append((sql, params))
        return self.rows


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
async def test_record_topic_plan_feedback_inserts_event_with_plan_context():
    pool = FakePool()

    result = await topic_plan_feedback_repo.record_topic_plan_feedback(
        pool,
        plan_id=pool.conn.plan_id,
        event_type="accepted",
        dedupe_key="ui-click-1",
        reason_tags=["worth-writing"],
        note="looks good",
        decided_by="user",
        topic_id=pool.conn.topic_id,
        metadata={"publication_id": "pub-1"},
    )

    insert_sql, params = pool.conn.fetchrow_calls[1]
    assert "INSERT INTO hermes.topic_plan_feedback_events" in insert_sql
    assert "ON CONFLICT (plan_id, event_type, dedupe_key)" in insert_sql
    assert "WHERE dedupe_key IS NOT NULL" in insert_sql
    assert "DO NOTHING" in insert_sql
    assert params[:5] == (
        pool.conn.plan_id,
        "wechat-ai-tools",
        "ai-productivity",
        "accepted",
        "ui-click-1",
    )
    assert params[5] == '["worth-writing"]'
    assert result["event_type"] == "accepted"


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_returns_none_for_missing_plan():
    pool = FakePool(FakeConnection(plan_exists=False))

    result = await topic_plan_feedback_repo.record_topic_plan_feedback(
        pool,
        plan_id=pool.conn.plan_id,
        event_type="accepted",
    )

    assert result is None
    assert len(pool.conn.fetchrow_calls) == 1


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_rejects_invalid_event_type():
    pool = FakePool()

    with pytest.raises(ValueError):
        await topic_plan_feedback_repo.record_topic_plan_feedback(
            pool,
            plan_id=pool.conn.plan_id,
            event_type="bad",
        )

    assert pool.conn.fetchrow_calls == []


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_fetches_existing_event_on_dedupe_conflict():
    pool = FakePool(FakeConnection(insert_conflict=True))

    result = await topic_plan_feedback_repo.record_topic_plan_feedback(
        pool,
        plan_id=pool.conn.plan_id,
        event_type="accepted",
        dedupe_key="ui-click-1",
    )

    conflict_sql, _ = pool.conn.fetchrow_calls[1]
    existing_sql, existing_params = pool.conn.fetchrow_calls[2]
    assert "DO NOTHING" in conflict_sql
    assert "FROM hermes.topic_plan_feedback_events" in existing_sql
    assert "ORDER BY created_at DESC" in existing_sql
    assert existing_params == (pool.conn.plan_id, "accepted", "ui-click-1")
    assert result["event_id"] == pool.conn.event_id


@pytest.mark.asyncio
async def test_list_topic_plan_feedback_filters_and_orders_by_event_time():
    pool = FakePool()
    event_from = datetime(2026, 7, 1, tzinfo=timezone.utc)
    event_to = datetime(2026, 7, 2, tzinfo=timezone.utc)
    created_from = datetime(2026, 7, 1, 12, tzinfo=timezone.utc)

    items, total = await topic_plan_feedback_repo.list_topic_plan_feedback(
        pool,
        plan_id=pool.conn.plan_id,
        account_id="wechat-ai-tools",
        track_id="ai-productivity",
        event_type="accepted",
        event_from=event_from,
        event_to=event_to,
        created_from=created_from,
        limit=10,
        offset=5,
    )

    count_sql, count_params = pool.conn.fetchval_calls[0]
    list_sql, list_params = pool.conn.fetch_calls[0]
    assert "plan_id = $1" in count_sql
    assert "account_id = $2" in count_sql
    assert "track_id = $3" in count_sql
    assert "event_type = $4" in count_sql
    assert "event_at >= $5" in count_sql
    assert "event_at <= $6" in count_sql
    assert "created_at >= $7" in count_sql
    assert "ORDER BY event_at DESC, created_at DESC" in list_sql
    assert count_params == (
        pool.conn.plan_id,
        "wechat-ai-tools",
        "ai-productivity",
        "accepted",
        event_from,
        event_to,
        created_from,
    )
    assert list_params == (*count_params, 10, 5)
    assert total == 1
    assert items[0]["event_type"] == "accepted"


@pytest.mark.asyncio
async def test_list_topic_plan_feedback_rejects_invalid_event_type():
    pool = FakePool()

    with pytest.raises(ValueError):
        await topic_plan_feedback_repo.list_topic_plan_feedback(
            pool,
            event_type="bad",
        )

    assert pool.conn.fetch_calls == []


def report_row(
    *,
    plan_id,
    event_type=None,
    plan_status="planned",
    source="wechat-agent",
    llm_metadata=None,
    reason_tags="[]",
    event_at=None,
    event_created_at=None,
):
    event_at = event_at or datetime(2026, 7, 2, tzinfo=timezone.utc)
    event_created_at = event_created_at or event_at
    return {
        "plan_id": plan_id,
        "account_id": "wechat-ai-tools",
        "track_id": "ai-productivity",
        "plan_status": plan_status,
        "source": source,
        "llm_metadata": llm_metadata or '{"config_snapshot": {"runtime_version": "v1", "track_config_hash": "h1"}}',
        "event_id": uuid4() if event_type else None,
        "event_type": event_type,
        "reason_tags": reason_tags,
        "event_at": event_at if event_type else None,
        "event_created_at": event_created_at if event_type else None,
    }


@pytest.mark.asyncio
async def test_get_topic_plan_feedback_report_applies_precedence_and_rates():
    plan_1 = uuid4()
    plan_2 = uuid4()
    plan_3 = uuid4()
    rows = [
        report_row(plan_id=plan_1, event_type="accepted"),
        report_row(plan_id=plan_1, event_type="rejected", reason_tags='["too-generic"]'),
        report_row(plan_id=plan_2, event_type="published", plan_status="consumed"),
        report_row(plan_id=plan_3, event_type=None),
    ]
    pool = FakePool(ReportConnection(rows))

    report = await topic_plan_feedback_repo.get_topic_plan_feedback_report(
        pool,
        account_id="wechat-ai-tools",
        track_id="ai-productivity",
        window_days=30,
        min_sample_size=5,
    )

    sql, params = pool.conn.fetch_calls[0]
    assert "FROM hermes.topic_plans p" in sql
    assert "e.event_at >= now() - make_interval(days => $1::int)" in sql
    assert "p.account_id = $2" in sql
    assert "p.track_id = $3" in sql
    assert params == (30, "wechat-ai-tools", "ai-productivity")
    assert report["planned_count"] == 3
    assert report["accepted_count"] == 2
    assert report["rejected_count"] == 0
    assert report["consumed_count"] == 1
    assert report["published_count"] == 1
    assert report["acceptance_rate"] == 2 / 3
    assert report["sample_warning"] is True
    assert report["reason_tag_counts"] == {"too-generic": 1}


@pytest.mark.asyncio
async def test_get_topic_plan_feedback_report_uses_latest_for_same_precedence():
    plan_id = uuid4()
    older = datetime(2026, 7, 1, tzinfo=timezone.utc)
    newer = datetime(2026, 7, 2, tzinfo=timezone.utc)
    rows = [
        report_row(plan_id=plan_id, event_type="accepted", event_at=older),
        report_row(plan_id=plan_id, event_type="rejected", event_at=newer),
        report_row(plan_id=plan_id, event_type="accepted", event_at=newer),
    ]
    pool = FakePool(ReportConnection(rows))

    report = await topic_plan_feedback_repo.get_topic_plan_feedback_report(pool)

    assert report["planned_count"] == 1
    assert report["accepted_count"] == 1
    assert report["rejected_count"] == 0


@pytest.mark.asyncio
async def test_get_topic_plan_feedback_report_groups_config_and_unknown_config():
    rows = [
        report_row(plan_id=uuid4(), event_type="accepted"),
        report_row(plan_id=uuid4(), event_type="accepted", llm_metadata="{}"),
    ]
    pool = FakePool(ReportConnection(rows))

    report = await topic_plan_feedback_repo.get_topic_plan_feedback_report(pool)

    runtime_keys = {item["key"] for item in report["by_runtime_version"]}
    track_hash_keys = {item["key"] for item in report["by_track_config_hash"]}
    source_keys = {item["key"] for item in report["by_source"]}
    assert runtime_keys == {"v1", "unknown_config"}
    assert track_hash_keys == {"h1", "unknown_config"}
    assert source_keys == {"wechat-agent"}


@pytest.mark.asyncio
async def test_get_topic_plan_feedback_report_returns_null_rates_for_empty_scope():
    pool = FakePool(ReportConnection([]))

    report = await topic_plan_feedback_repo.get_topic_plan_feedback_report(pool)

    assert report["planned_count"] == 0
    assert report["acceptance_rate"] is None
    assert report["consume_rate"] is None
    assert report["publish_rate"] is None
