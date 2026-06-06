from datetime import date, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import asyncpg
import pytest

from hermes_db_mcp.tools.wechat_analytics import (
    bulk_upsert_wechat_article_metric_snapshots,
    list_wechat_article_metric_snapshots,
)


class FakeAppContext:
    def __init__(self):
        self.pool = MagicMock()


class FakeContext:
    def __init__(self, app_context):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = app_context


def metric_record(article_id=None, **overrides):
    row = {
        "article_id": str(article_id or uuid4()),
        "stat_date": "2026-04-13",
        "window_label": "D+1",
        "read_user_count": 100,
        "completion_rate": 0.5,
        "raw_json": {"row": 1},
    }
    row.update(overrides)
    return row


def channel_record(article_id=None, **overrides):
    row = {
        "article_id": str(article_id or uuid4()),
        "metric_date": "2026-04-13",
        "channel": "全部",
        "read_user_count": 100,
        "share_user_count": 2,
        "raw_json": {"channel": "全部"},
    }
    row.update(overrides)
    return row


@pytest.mark.asyncio
async def test_bulk_upsert_wechat_article_metric_snapshots_success(monkeypatch):
    article_id = uuid4()
    import_run_id = uuid4()

    async def mock_resolve_article(pool, **kwargs):
        return {"status": "matched", "article": {"article_id": article_id}, "items": []}

    async def mock_run_import_transaction(pool, **kwargs):
        assert kwargs["snapshot_rows"][0]["article_id"] == article_id
        assert kwargs["snapshot_rows"][0]["stat_date"] == date(2026, 4, 13)
        assert kwargs["channel_rows"][0]["article_id"] == article_id
        assert kwargs["metadata"] == {"filename": "sample.json"}
        return {
            "import_run_id": import_run_id,
            "created": 1,
            "updated": 0,
            "status": "completed",
            "channel_daily_metrics": {"created": 1, "updated": 0},
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.resolve_article",
        mock_resolve_article,
    )
    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.run_import_transaction",
        mock_run_import_transaction,
    )

    result = await bulk_upsert_wechat_article_metric_snapshots(
        "acct",
        "manual_json",
        [metric_record(article_id)],
        FakeContext(FakeAppContext()),
        channel_daily_metrics=[channel_record(article_id)],
        import_metadata={"filename": "sample.json"},
    )

    assert result == {
        "import_run_id": str(import_run_id),
        "total_rows": 1,
        "created": 1,
        "updated": 0,
        "skipped": 0,
        "unmatched": [],
        "errors": [],
        "status": "completed",
    }


@pytest.mark.asyncio
async def test_bulk_upsert_dry_run_does_not_write(monkeypatch):
    article_id = uuid4()
    wrote = False

    async def mock_resolve_article(pool, **kwargs):
        return {"status": "matched", "article": {"article_id": article_id}, "items": []}

    async def mock_run_import_transaction(pool, **kwargs):
        nonlocal wrote
        wrote = True

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.resolve_article",
        mock_resolve_article,
    )
    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.run_import_transaction",
        mock_run_import_transaction,
    )

    result = await bulk_upsert_wechat_article_metric_snapshots(
        "acct",
        "manual_json",
        [metric_record(article_id)],
        FakeContext(FakeAppContext()),
        dry_run=True,
    )

    assert wrote is False
    assert result["status"] == "dry_run"
    assert result["created"] == 0


@pytest.mark.asyncio
async def test_bulk_upsert_reports_unknown_article_as_unmatched(monkeypatch):
    async def mock_resolve_article(pool, **kwargs):
        return {"status": "not_found", "items": []}

    async def mock_run_import_transaction(pool, **kwargs):
        return {
            "import_run_id": uuid4(),
            "created": 0,
            "updated": 0,
            "channel_daily_metrics": {"created": 0, "updated": 0},
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.resolve_article",
        mock_resolve_article,
    )
    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.run_import_transaction",
        mock_run_import_transaction,
    )

    result = await bulk_upsert_wechat_article_metric_snapshots(
        "acct",
        "manual_json",
        [metric_record()],
        FakeContext(FakeAppContext()),
    )

    assert result["status"] == "completed_with_errors"
    assert result["unmatched"][0]["index"] == 0


@pytest.mark.asyncio
async def test_bulk_upsert_reports_ambiguous_article_as_row_error(monkeypatch):
    article_id = uuid4()

    async def mock_resolve_article(pool, **kwargs):
        return {
            "status": "ambiguous",
            "items": [{"article_id": article_id}, {"article_id": uuid4()}],
        }

    async def mock_run_import_transaction(pool, **kwargs):
        return {
            "import_run_id": uuid4(),
            "created": 0,
            "updated": 0,
            "channel_daily_metrics": {"created": 0, "updated": 0},
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.resolve_article",
        mock_resolve_article,
    )
    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.run_import_transaction",
        mock_run_import_transaction,
    )

    result = await bulk_upsert_wechat_article_metric_snapshots(
        "acct",
        "manual_json",
        [metric_record()],
        FakeContext(FakeAppContext()),
    )

    assert result["status"] == "completed_with_errors"
    assert result["errors"][0]["error"] == "ambiguous_article"
    assert "matches" in result["errors"][0]


@pytest.mark.asyncio
async def test_bulk_upsert_reports_audience_profiles_skipped(monkeypatch):
    article_id = uuid4()

    async def mock_resolve_article(pool, **kwargs):
        return {"status": "matched", "article": {"article_id": article_id}, "items": []}

    async def mock_run_import_transaction(pool, **kwargs):
        assert kwargs["skipped"] == 1
        assert kwargs["errors"][0]["reasons"] == ["audience_profiles_not_supported_in_mvp"]
        return {
            "import_run_id": uuid4(),
            "created": 1,
            "updated": 0,
            "channel_daily_metrics": {"created": 0, "updated": 0},
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.resolve_article",
        mock_resolve_article,
    )
    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.run_import_transaction",
        mock_run_import_transaction,
    )

    result = await bulk_upsert_wechat_article_metric_snapshots(
        "acct",
        "manual_json",
        [metric_record(article_id)],
        FakeContext(FakeAppContext()),
        audience_profiles=[{"dimension": "gender", "bucket": "male", "ratio": 0.5}],
    )

    assert result["skipped"] == 1
    assert result["errors"][0]["error"] == "skipped"


@pytest.mark.asyncio
async def test_bulk_upsert_maps_schema_drift(monkeypatch):
    async def mock_resolve_article(pool, **kwargs):
        raise asyncpg.UndefinedTableError("missing")

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.resolve_article",
        mock_resolve_article,
    )

    result = await bulk_upsert_wechat_article_metric_snapshots(
        "acct",
        "manual_json",
        [metric_record()],
        FakeContext(FakeAppContext()),
    )

    assert result["error"] == "schema_drift"


@pytest.mark.asyncio
async def test_list_wechat_article_metric_snapshots_omits_raw_by_default(monkeypatch):
    snapshot_id = uuid4()
    article_id = uuid4()

    async def mock_list_metric_snapshots(pool, **kwargs):
        assert kwargs["include_raw"] is False
        return [
            {
                "snapshot_id": snapshot_id,
                "article_id": article_id,
                "account": "acct",
                "stat_date": date(2026, 4, 13),
                "window_label": "D+1",
                "source": "manual_json",
                "read_user_count": 100,
                "raw_json": {"row": 1},
                "updated_at": datetime(2026, 4, 13),
            }
        ]

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.list_metric_snapshots",
        mock_list_metric_snapshots,
    )

    result = await list_wechat_article_metric_snapshots(
        FakeContext(FakeAppContext()),
        account="acct",
    )

    assert result["items"][0]["snapshot_id"] == str(snapshot_id)
    assert result["items"][0]["article_id"] == str(article_id)
    assert result["items"][0]["stat_date"] == "2026-04-13"
    assert "raw_json" not in result["items"][0]


@pytest.mark.asyncio
async def test_list_wechat_article_metric_snapshots_includes_raw_when_requested(monkeypatch):
    async def mock_list_metric_snapshots(pool, **kwargs):
        assert kwargs["include_raw"] is True
        return [{"snapshot_id": uuid4(), "raw_json": {"row": 1}}]

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.list_metric_snapshots",
        mock_list_metric_snapshots,
    )

    result = await list_wechat_article_metric_snapshots(
        FakeContext(FakeAppContext()),
        account="acct",
        include_raw=True,
    )

    assert result["items"][0]["raw_json"] == {"row": 1}


@pytest.mark.asyncio
async def test_list_wechat_article_metric_snapshots_rejects_invalid_query():
    result = await list_wechat_article_metric_snapshots(FakeContext(FakeAppContext()))

    assert result["error"] == "invalid_filter"


@pytest.mark.asyncio
async def test_list_wechat_article_metric_snapshots_maps_schema_drift(monkeypatch):
    async def mock_list_metric_snapshots(pool, **kwargs):
        raise asyncpg.UndefinedColumnError("missing")

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_analytics.wechat_analytics_repo.list_metric_snapshots",
        mock_list_metric_snapshots,
    )

    result = await list_wechat_article_metric_snapshots(
        FakeContext(FakeAppContext()),
        account="acct",
    )

    assert result["error"] == "schema_drift"
