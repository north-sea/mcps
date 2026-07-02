from unittest.mock import AsyncMock

import pytest

from hermes_db_mcp.services.schema import inspect_topic_plan_feedback_schema


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


FEEDBACK_COLUMNS = {
    "event_id",
    "plan_id",
    "account_id",
    "track_id",
    "event_type",
    "dedupe_key",
    "reason_tags",
    "note",
    "decided_by",
    "topic_id",
    "metadata",
    "event_at",
    "created_at",
}

CONSTRAINTS = {
    "topic_plan_feedback_events_pkey",
    "fk_topic_plan_feedback_events_plan",
    "fk_topic_plan_feedback_events_topic",
    "chk_topic_plan_feedback_event_type",
    "chk_topic_plan_feedback_reason_tags_array",
    "chk_topic_plan_feedback_metadata_object",
}

INDEXES = {
    "idx_topic_plan_feedback_plan_event_at",
    "idx_topic_plan_feedback_account_track_event_at",
    "idx_topic_plan_feedback_account_event_type_event_at",
    "uq_topic_plan_feedback_dedupe",
    "idx_topic_plan_feedback_topic_id",
}


def column_rows(names):
    return [FakeRow(column_name=name) for name in names]


def constraint_rows(names):
    return [FakeRow(conname=name) for name in names]


def index_rows(names):
    return [FakeRow(indexname=name) for name in names]


@pytest.mark.asyncio
async def test_inspect_topic_plan_feedback_schema_returns_true_for_complete_schema():
    pool = FakePool(
        [
            column_rows(FEEDBACK_COLUMNS),
            constraint_rows(CONSTRAINTS),
            index_rows(INDEXES),
        ]
    )

    assert await inspect_topic_plan_feedback_schema(pool) == {"topic_plan_feedback": True}


@pytest.mark.asyncio
async def test_inspect_topic_plan_feedback_schema_reflects_missing_table():
    pool = FakePool([[], [], []])

    assert await inspect_topic_plan_feedback_schema(pool) == {"topic_plan_feedback": False}


@pytest.mark.asyncio
async def test_inspect_topic_plan_feedback_schema_reflects_missing_constraint():
    pool = FakePool(
        [
            column_rows(FEEDBACK_COLUMNS),
            constraint_rows(CONSTRAINTS - {"chk_topic_plan_feedback_event_type"}),
            index_rows(INDEXES),
        ]
    )

    assert await inspect_topic_plan_feedback_schema(pool) == {"topic_plan_feedback": False}


@pytest.mark.asyncio
async def test_inspect_topic_plan_feedback_schema_reflects_missing_index():
    pool = FakePool(
        [
            column_rows(FEEDBACK_COLUMNS),
            constraint_rows(CONSTRAINTS),
            index_rows(INDEXES - {"uq_topic_plan_feedback_dedupe"}),
        ]
    )

    assert await inspect_topic_plan_feedback_schema(pool) == {"topic_plan_feedback": False}
