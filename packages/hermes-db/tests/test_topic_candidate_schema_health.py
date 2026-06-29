from unittest.mock import AsyncMock

import pytest

from hermes_db_mcp.services.schema import inspect_topic_candidate_schema


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


ACCOUNT_COLUMNS = {
    "account_id",
    "display_name",
    "enabled",
    "draft_target",
    "metadata",
    "created_at",
    "updated_at",
}

TRACK_COLUMNS = {
    "track_id",
    "account_id",
    "name",
    "keywords",
    "negative_keywords",
    "sources",
    "scoring_profile",
    "daily_quota",
    "enabled",
    "created_at",
    "updated_at",
}

CANDIDATE_COLUMNS = {
    "id",
    "account_id",
    "track_id",
    "source",
    "source_url",
    "source_item_id",
    "title",
    "summary",
    "hot_score",
    "fit_score",
    "novelty_score",
    "status",
    "dedupe_key",
    "captured_at",
    "raw_payload",
    "topic_id",
    "rejection_reason",
    "adopted_at",
    "status_updated_at",
    "created_at",
    "updated_at",
}

CONSTRAINTS = {
    "topic_candidates_pkey",
    "fk_topic_candidates_track",
    "uq_topic_candidates_dedupe",
    "chk_topic_candidates_status",
    "chk_topic_candidates_source_identity",
}

INDEXES = {
    "idx_topic_candidate_accounts_enabled",
    "idx_topic_candidate_tracks_enabled",
    "idx_topic_candidates_pool",
    "idx_topic_candidates_source",
    "idx_topic_candidates_topic_id",
}


def column_rows(names):
    return [FakeRow(column_name=name) for name in names]


def constraint_rows(names):
    return [FakeRow(conname=name) for name in names]


def index_rows(names):
    return [FakeRow(indexname=name) for name in names]


@pytest.mark.asyncio
async def test_inspect_topic_candidate_schema_returns_true_for_complete_schema():
    pool = FakePool(
        [
            column_rows(ACCOUNT_COLUMNS),
            column_rows(TRACK_COLUMNS),
            column_rows(CANDIDATE_COLUMNS),
            constraint_rows(CONSTRAINTS),
            index_rows(INDEXES),
        ]
    )

    assert await inspect_topic_candidate_schema(pool) == {"topic_candidates": True}


@pytest.mark.asyncio
async def test_inspect_topic_candidate_schema_reflects_missing_tables():
    pool = FakePool([[], [], [], [], []])

    assert await inspect_topic_candidate_schema(pool) == {"topic_candidates": False}


@pytest.mark.asyncio
async def test_inspect_topic_candidate_schema_reflects_missing_index():
    pool = FakePool(
        [
            column_rows(ACCOUNT_COLUMNS),
            column_rows(TRACK_COLUMNS),
            column_rows(CANDIDATE_COLUMNS),
            constraint_rows(CONSTRAINTS),
            index_rows(INDEXES - {"idx_topic_candidates_pool"}),
        ]
    )

    assert await inspect_topic_candidate_schema(pool) == {"topic_candidates": False}
