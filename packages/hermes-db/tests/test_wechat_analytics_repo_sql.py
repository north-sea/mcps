from datetime import date
from uuid import uuid4

import pytest

from hermes_db_mcp.repositories import wechat_analytics_repo


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.fetchrow_calls = []
        self.fetch_calls = []
        self.created_values = [True]

    def transaction(self):
        return FakeTransaction()

    async def fetchrow(self, sql, *params):
        self.fetchrow_calls.append((sql, params))
        if "INSERT INTO hermes.analytics_import_runs" in sql:
            return {
                "import_run_id": params[0],
                "account": params[1],
                "source": params[2],
                "status": params[3],
                "total_rows": params[4],
                "created": params[5],
                "updated": params[6],
                "skipped": params[7],
                "unmatched": params[8],
                "errors": params[9],
                "metadata": params[10],
                "created_at": None,
                "updated_at": None,
            }
        if "UPDATE hermes.analytics_import_runs" in sql:
            return {
                "import_run_id": params[0],
                "account": "acct",
                "source": "manual_json",
                "status": params[1],
                "total_rows": params[2],
                "created": params[3],
                "updated": params[4],
                "skipped": params[5],
                "unmatched": params[6],
                "errors": params[7],
                "metadata": params[8],
                "created_at": None,
                "updated_at": None,
            }
        if "INSERT INTO hermes.wechat_article_metric_snapshots" in sql:
            return {"created": self.created_values.pop(0)}
        if "INSERT INTO hermes.wechat_article_channel_daily_metrics" in sql:
            return {"created": self.created_values.pop(0)}
        return None

    async def fetch(self, sql, *params):
        self.fetch_calls.append((sql, params))
        return []


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


def snapshot_row(**overrides):
    row = {
        "article_id": uuid4(),
        "account": "acct",
        "stat_date": date(2026, 4, 13),
        "window_label": "D+1",
        "source": "manual_json",
        "read_user_count": 100,
        "average_stay_seconds": 68.5,
        "completion_rate": 0.36,
        "missing_fields": [],
        "raw_json": {},
    }
    row.update(overrides)
    return row


def channel_row(**overrides):
    row = {
        "article_id": uuid4(),
        "account": "acct",
        "metric_date": date(2026, 4, 13),
        "channel": "全部",
        "source": "manual_json",
        "read_user_count": 100,
        "share_user_count": 5,
        "raw_json": {},
    }
    row.update(overrides)
    return row


@pytest.mark.asyncio
async def test_resolve_article_supports_direct_article_id():
    pool = FakePool()
    article_id = uuid4()

    result = await wechat_analytics_repo.resolve_article(
        pool.conn,
        account="acct",
        article_id=article_id,
    )

    sql, params = pool.conn.fetch_calls[0]
    assert result["status"] == "not_found"
    assert "a.account = $1" in sql
    assert "a.article_id = $2" in sql
    assert params == ("acct", article_id)


@pytest.mark.asyncio
async def test_resolve_article_accepts_pool_and_acquires_connection():
    pool = FakePool()
    article_id = uuid4()

    await wechat_analytics_repo.resolve_article(
        pool,
        account="acct",
        article_id=article_id,
    )

    sql, params = pool.conn.fetch_calls[0]
    assert "a.article_id = $2" in sql
    assert params == ("acct", article_id)


@pytest.mark.asyncio
async def test_resolve_article_supports_external_ref_pair():
    pool = FakePool()

    await wechat_analytics_repo.resolve_article(
        pool.conn,
        account="acct",
        ref_type="canonical_url",
        ref_value="https://mp.weixin.qq.com/s/abc",
    )

    sql, params = pool.conn.fetch_calls[0]
    assert "EXISTS" in sql
    assert "hermes.wechat_article_external_refs" in sql
    assert "r.superseded_at IS NULL" in sql
    assert params == ("acct", "canonical_url", "https://mp.weixin.qq.com/s/abc")


@pytest.mark.asyncio
async def test_create_import_run_serializes_summary_json():
    pool = FakePool()
    import_run_id = uuid4()

    row = await wechat_analytics_repo.create_import_run(
        pool.conn,
        import_run_id=import_run_id,
        account="acct",
        source="manual_json",
        status="completed_with_errors",
        total_rows=2,
        skipped=1,
        unmatched=[{"row": 2}],
        errors=[{"error": "bad"}],
        metadata={"filename": "sample.json"},
    )

    sql, params = pool.conn.fetchrow_calls[0]
    assert "INSERT INTO hermes.analytics_import_runs" in sql
    assert row["import_run_id"] == import_run_id
    assert params[8] == '[{"row": 2}]'
    assert params[9] == '[{"error": "bad"}]'
    assert params[10] == '{"filename": "sample.json"}'


@pytest.mark.asyncio
async def test_upsert_metric_snapshots_uses_snapshot_identity_conflict():
    pool = FakePool()

    result = await wechat_analytics_repo.upsert_metric_snapshots(
        pool.conn,
        [snapshot_row()],
        import_run_id=uuid4(),
    )

    sql, params = pool.conn.fetchrow_calls[0]
    assert result == {"created": 1, "updated": 0}
    assert "INSERT INTO hermes.wechat_article_metric_snapshots" in sql
    assert "ON CONFLICT (article_id, stat_date, window_label, source)" in sql
    assert "RETURNING (xmax = 0) AS created" in sql
    assert params[2] == "acct"
    assert params[3] == date(2026, 4, 13)
    assert params[4] == "D+1"
    assert params[5] == "manual_json"


@pytest.mark.asyncio
async def test_upsert_channel_daily_metrics_uses_channel_identity_conflict():
    pool = FakePool()

    result = await wechat_analytics_repo.upsert_channel_daily_metrics(
        pool.conn,
        [channel_row()],
        import_run_id=uuid4(),
    )

    sql, params = pool.conn.fetchrow_calls[0]
    assert result == {"created": 1, "updated": 0}
    assert "INSERT INTO hermes.wechat_article_channel_daily_metrics" in sql
    assert "ON CONFLICT (article_id, metric_date, channel, source)" in sql
    assert "RETURNING (xmax = 0) AS created" in sql
    assert "SUM(" not in sql
    assert params[2] == "acct"
    assert params[3] == date(2026, 4, 13)
    assert params[4] == "全部"
    assert params[5] == "manual_json"


@pytest.mark.asyncio
async def test_list_metric_snapshots_builds_bounded_filters_without_raw_by_default():
    pool = FakePool()
    article_id = uuid4()

    await wechat_analytics_repo.list_metric_snapshots(
        pool,
        account="acct",
        article_id=article_id,
        date_from=date(2026, 4, 13),
        date_to=date(2026, 4, 20),
        window_label="D+1",
        limit=10,
        offset=5,
    )

    sql, params = pool.conn.fetch_calls[0]
    assert "account = $1" in sql
    assert "article_id = $2" in sql
    assert "window_label = $3" in sql
    assert "stat_date >= $4" in sql
    assert "stat_date <= $5" in sql
    assert "LIMIT $6 OFFSET $7" in sql
    assert "raw_json" not in sql
    assert params == (
        "acct",
        article_id,
        "D+1",
        date(2026, 4, 13),
        date(2026, 4, 20),
        10,
        5,
    )


@pytest.mark.asyncio
async def test_list_metric_snapshots_includes_raw_when_requested():
    pool = FakePool()

    await wechat_analytics_repo.list_metric_snapshots(
        pool,
        account="acct",
        include_raw=True,
    )

    sql, _params = pool.conn.fetch_calls[0]
    assert "raw_json" in sql


@pytest.mark.asyncio
async def test_run_import_transaction_writes_import_run_and_rows_in_one_transaction():
    pool = FakePool()
    pool.conn.created_values = [True, False]

    result = await wechat_analytics_repo.run_import_transaction(
        pool,
        account="acct",
        source="manual_json",
        snapshot_rows=[snapshot_row()],
        channel_rows=[channel_row()],
        skipped=1,
        unmatched=[{"row": 2}],
        metadata={"filename": "sample.json"},
    )

    fetchrow_sql = [call[0] for call in pool.conn.fetchrow_calls]
    assert any("INSERT INTO hermes.analytics_import_runs" in sql for sql in fetchrow_sql)
    assert any("INSERT INTO hermes.wechat_article_metric_snapshots" in sql for sql in fetchrow_sql)
    assert any("INSERT INTO hermes.wechat_article_channel_daily_metrics" in sql for sql in fetchrow_sql)
    assert any("UPDATE hermes.analytics_import_runs" in sql for sql in fetchrow_sql)
    assert result["status"] == "completed_with_errors"
    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["channel_daily_metrics"] == {"created": 0, "updated": 1}
