from unittest.mock import AsyncMock

import pytest

from hermes_db_mcp.services.schema import inspect_wechat_analytics_ingestion_schema


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


IMPORT_COLUMNS = {
    "import_run_id",
    "account",
    "source",
    "status",
    "total_rows",
    "created",
    "updated",
    "skipped",
    "unmatched",
    "errors",
    "metadata",
    "created_at",
    "updated_at",
}

SNAPSHOT_COLUMNS = {
    "snapshot_id",
    "article_id",
    "account",
    "stat_date",
    "window_label",
    "source",
    "read_user_count",
    "average_stay_seconds",
    "completion_rate",
    "new_follow_user_count",
    "share_user_count",
    "wow_user_count",
    "like_user_count",
    "favorite_user_count",
    "reward_cents",
    "comment_count",
    "delivered_user_count",
    "account_message_read_user_count",
    "first_share_user_count",
    "total_share_user_count",
    "share_generated_read_user_count",
    "missing_fields",
    "raw_json",
    "import_run_id",
    "collected_at",
    "created_at",
    "updated_at",
}

CHANNEL_COLUMNS = {
    "metric_id",
    "article_id",
    "account",
    "metric_date",
    "channel",
    "source",
    "read_user_count",
    "share_user_count",
    "raw_json",
    "import_run_id",
    "created_at",
    "updated_at",
}

IMPORT_CONSTRAINTS = {
    "analytics_import_runs_pkey",
    "chk_analytics_import_runs_status",
    "chk_analytics_import_runs_counts_nonnegative",
}

SNAPSHOT_CONSTRAINTS = {
    "wechat_article_metric_snapshots_pkey",
    "wechat_article_metric_snapshots_article_id_fkey",
    "wechat_article_metric_snapshots_import_run_id_fkey",
    "uq_wechat_article_metric_snapshot_identity",
    "chk_wechat_article_metric_snapshot_counts_nonnegative",
    "chk_wechat_article_metric_snapshot_completion_rate",
}

CHANNEL_CONSTRAINTS = {
    "wechat_article_channel_daily_metrics_pkey",
    "wechat_article_channel_daily_metrics_article_id_fkey",
    "wechat_article_channel_daily_metrics_import_run_id_fkey",
    "uq_wechat_article_channel_daily_identity",
    "chk_wechat_article_channel_daily_counts_nonnegative",
}

INDEXES = {
    "idx_analytics_import_runs_account_created",
    "idx_analytics_import_runs_source_created",
    "idx_analytics_import_runs_status_created",
    "idx_wechat_article_metric_snapshots_account_stat",
    "idx_wechat_article_metric_snapshots_article_stat",
    "idx_wechat_article_metric_snapshots_window_stat",
    "idx_wechat_article_metric_snapshots_source_stat",
    "idx_wechat_article_metric_snapshots_import_run",
    "idx_wechat_article_channel_daily_account_date",
    "idx_wechat_article_channel_daily_article_date",
    "idx_wechat_article_channel_daily_channel_date",
    "idx_wechat_article_channel_daily_import_run",
}


def column_rows(names):
    return [FakeRow(column_name=name) for name in names]


def constraint_rows(names):
    return [FakeRow(conname=name) for name in names]


def index_rows(names):
    return [FakeRow(indexname=name) for name in names]


@pytest.mark.asyncio
async def test_inspect_wechat_analytics_ingestion_schema_returns_true_for_complete_schema():
    pool = FakePool(
        [
            column_rows(IMPORT_COLUMNS),
            column_rows(SNAPSHOT_COLUMNS),
            column_rows(CHANNEL_COLUMNS),
            constraint_rows(IMPORT_CONSTRAINTS),
            constraint_rows(SNAPSHOT_CONSTRAINTS),
            constraint_rows(CHANNEL_CONSTRAINTS),
            index_rows(INDEXES),
        ]
    )

    assert await inspect_wechat_analytics_ingestion_schema(pool) == {
        "wechat_analytics_ingestion": True,
    }


@pytest.mark.asyncio
async def test_inspect_wechat_analytics_ingestion_schema_reflects_missing_tables():
    pool = FakePool([[], [], [], [], [], [], []])

    assert await inspect_wechat_analytics_ingestion_schema(pool) == {
        "wechat_analytics_ingestion": False,
    }


@pytest.mark.asyncio
async def test_inspect_wechat_analytics_ingestion_schema_reflects_missing_index():
    pool = FakePool(
        [
            column_rows(IMPORT_COLUMNS),
            column_rows(SNAPSHOT_COLUMNS),
            column_rows(CHANNEL_COLUMNS),
            constraint_rows(IMPORT_CONSTRAINTS),
            constraint_rows(SNAPSHOT_CONSTRAINTS),
            constraint_rows(CHANNEL_CONSTRAINTS),
            index_rows(INDEXES - {"idx_wechat_article_metric_snapshots_source_stat"}),
        ]
    )

    assert await inspect_wechat_analytics_ingestion_schema(pool) == {
        "wechat_analytics_ingestion": False,
    }
