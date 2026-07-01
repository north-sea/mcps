from unittest.mock import AsyncMock

import pytest

from hermes_db_mcp.services.schema import inspect_topic_plan_schema


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


PLAN_COLUMNS = {
    "plan_id",
    "candidate_id",
    "account_id",
    "track_id",
    "status",
    "recommended_angle_index",
    "topic_angles",
    "outline_pack",
    "writing_brief",
    "image_brief",
    "evidence",
    "llm_metadata",
    "rejection_reason",
    "topic_id",
    "source",
    "created_at",
    "updated_at",
    "consumed_at",
}

CONSTRAINTS = {
    "topic_plans_pkey",
    "uq_topic_plans_candidate",
    "chk_topic_plans_status",
    "chk_topic_plans_planned_shape",
    "chk_topic_plans_rejected_shape",
}

INDEXES = {
    "idx_topic_plans_account_status_created",
    "idx_topic_plans_account_track_status_created",
    "idx_topic_plans_candidate",
    "idx_topic_plans_topic_id",
}


def column_rows(names):
    return [FakeRow(column_name=name) for name in names]


def constraint_rows(names):
    return [FakeRow(conname=name) for name in names]


def index_rows(names):
    return [FakeRow(indexname=name) for name in names]


@pytest.mark.asyncio
async def test_inspect_topic_plan_schema_returns_true_for_complete_schema():
    pool = FakePool(
        [
            column_rows(PLAN_COLUMNS),
            constraint_rows(CONSTRAINTS),
            index_rows(INDEXES),
        ]
    )

    assert await inspect_topic_plan_schema(pool) == {"topic_plans": True}


@pytest.mark.asyncio
async def test_inspect_topic_plan_schema_reflects_missing_table():
    pool = FakePool([[], [], []])

    assert await inspect_topic_plan_schema(pool) == {"topic_plans": False}


@pytest.mark.asyncio
async def test_inspect_topic_plan_schema_reflects_missing_constraint():
    pool = FakePool(
        [
            column_rows(PLAN_COLUMNS),
            constraint_rows(CONSTRAINTS - {"chk_topic_plans_planned_shape"}),
            index_rows(INDEXES),
        ]
    )

    assert await inspect_topic_plan_schema(pool) == {"topic_plans": False}


@pytest.mark.asyncio
async def test_inspect_topic_plan_schema_reflects_missing_index():
    pool = FakePool(
        [
            column_rows(PLAN_COLUMNS),
            constraint_rows(CONSTRAINTS),
            index_rows(INDEXES - {"idx_topic_plans_account_status_created"}),
        ]
    )

    assert await inspect_topic_plan_schema(pool) == {"topic_plans": False}
