from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from hermes_db_mcp.tools.topic_plan_feedback import (
    get_topic_plan_feedback_report,
    list_topic_plan_feedback,
    record_topic_plan_feedback,
)


class FakeAppContext:
    def __init__(self):
        self.pool = MagicMock()


class FakeContext:
    def __init__(self, app_context):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = app_context


def feedback_row(*, event_type="accepted", topic_id=None):
    now = datetime(2026, 7, 2, tzinfo=timezone.utc)
    return {
        "event_id": uuid4(),
        "plan_id": uuid4(),
        "account_id": "wechat-ai-tools",
        "track_id": "ai-productivity",
        "event_type": event_type,
        "dedupe_key": "ui-click-1",
        "reason_tags": '["worth-writing"]',
        "note": "looks good",
        "decided_by": "user",
        "topic_id": topic_id,
        "metadata": '{"publication_id": "pub-1"}',
        "event_at": now,
        "created_at": now,
    }


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_success(monkeypatch):
    row = feedback_row()

    async def mock_record_topic_plan_feedback(pool, **kwargs):
        assert kwargs["event_type"] == "accepted"
        assert kwargs["dedupe_key"] == "ui-click-1"
        assert kwargs["reason_tags"] == ["worth-writing"]
        return row

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plan_feedback."
        "topic_plan_feedback_repo.record_topic_plan_feedback",
        mock_record_topic_plan_feedback,
    )

    result = await record_topic_plan_feedback(
        str(row["plan_id"]),
        "accepted",
        FakeContext(FakeAppContext()),
        dedupe_key="ui-click-1",
        reason_tags=["worth-writing"],
        decided_by="user",
    )

    assert result["event_id"] == str(row["event_id"])
    assert result["reason_tags"] == ["worth-writing"]
    assert result["metadata"] == {"publication_id": "pub-1"}


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_returns_not_found(monkeypatch):
    async def mock_record_topic_plan_feedback(pool, **kwargs):
        return None

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plan_feedback."
        "topic_plan_feedback_repo.record_topic_plan_feedback",
        mock_record_topic_plan_feedback,
    )

    result = await record_topic_plan_feedback(
        str(uuid4()),
        "accepted",
        FakeContext(FakeAppContext()),
    )

    assert result["error"] == "not_found"


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_rejects_invalid_event_type():
    result = await record_topic_plan_feedback(
        str(uuid4()),
        "bad",
        FakeContext(FakeAppContext()),
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "event_type"


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_rejects_bad_reason_tags():
    result = await record_topic_plan_feedback(
        str(uuid4()),
        "rejected",
        FakeContext(FakeAppContext()),
        reason_tags=["off-brand", ""],
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "reason_tags"


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_accepts_written_topic_id(monkeypatch):
    row = feedback_row(event_type="written", topic_id=uuid4())

    async def mock_record_topic_plan_feedback(pool, **kwargs):
        assert kwargs["topic_id"] == row["topic_id"]
        return row

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plan_feedback."
        "topic_plan_feedback_repo.record_topic_plan_feedback",
        mock_record_topic_plan_feedback,
    )

    result = await record_topic_plan_feedback(
        str(row["plan_id"]),
        "written",
        FakeContext(FakeAppContext()),
        topic_id=str(row["topic_id"]),
    )

    assert result["event_type"] == "written"
    assert result["topic_id"] == str(row["topic_id"])


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_requires_published_lineage():
    result = await record_topic_plan_feedback(
        str(uuid4()),
        "published",
        FakeContext(FakeAppContext()),
    )

    assert result["error"] == "missing_required_field"
    assert result["field"] == "publication_lineage"


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_accepts_published_metadata_lineage(monkeypatch):
    row = feedback_row(event_type="published")

    async def mock_record_topic_plan_feedback(pool, **kwargs):
        assert kwargs["metadata"] == {"publication_idempotency_key": "pub-key-1"}
        return row

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plan_feedback."
        "topic_plan_feedback_repo.record_topic_plan_feedback",
        mock_record_topic_plan_feedback,
    )

    result = await record_topic_plan_feedback(
        str(row["plan_id"]),
        "published",
        FakeContext(FakeAppContext()),
        metadata={"publication_idempotency_key": "pub-key-1"},
    )

    assert result["event_type"] == "published"


@pytest.mark.asyncio
async def test_record_topic_plan_feedback_rejects_invalid_event_at():
    result = await record_topic_plan_feedback(
        str(uuid4()),
        "accepted",
        FakeContext(FakeAppContext()),
        event_at="not-a-date",
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "event_at"


@pytest.mark.asyncio
async def test_list_topic_plan_feedback_success(monkeypatch):
    row = feedback_row()

    async def mock_list_topic_plan_feedback(pool, **kwargs):
        assert kwargs["event_type"] == "accepted"
        assert kwargs["limit"] == 10
        return [row], 1

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plan_feedback."
        "topic_plan_feedback_repo.list_topic_plan_feedback",
        mock_list_topic_plan_feedback,
    )

    result = await list_topic_plan_feedback(
        FakeContext(FakeAppContext()),
        account_id="wechat-ai-tools",
        event_type="accepted",
        limit=10,
    )

    assert result["total"] == 1
    assert result["items"][0]["event_id"] == str(row["event_id"])
    assert result["items"][0]["event_at"] == str(row["event_at"])


@pytest.mark.asyncio
async def test_list_topic_plan_feedback_validates_pagination():
    result = await list_topic_plan_feedback(
        FakeContext(FakeAppContext()),
        limit=0,
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "limit"


@pytest.mark.asyncio
async def test_list_topic_plan_feedback_validates_event_type():
    result = await list_topic_plan_feedback(
        FakeContext(FakeAppContext()),
        event_type="bad",
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "event_type"


@pytest.mark.asyncio
async def test_list_topic_plan_feedback_validates_time_filter():
    result = await list_topic_plan_feedback(
        FakeContext(FakeAppContext()),
        event_from="not-a-date",
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "event_from"


@pytest.mark.asyncio
async def test_get_topic_plan_feedback_report_success(monkeypatch):
    async def mock_get_topic_plan_feedback_report(pool, **kwargs):
        assert kwargs["account_id"] == "wechat-ai-tools"
        assert kwargs["window_days"] == 14
        assert kwargs["min_sample_size"] == 3
        return {
            "account_id": kwargs["account_id"],
            "track_id": None,
            "window_days": kwargs["window_days"],
            "planned_count": 1,
            "accepted_count": 1,
            "rejected_count": 0,
            "deferred_count": 0,
            "consumed_count": 0,
            "published_count": 0,
            "acceptance_rate": 1.0,
            "consume_rate": 0.0,
            "publish_rate": 0.0,
            "reason_tag_counts": {},
            "by_source": [],
            "by_runtime_version": [],
            "by_track_config_hash": [],
            "sample_warning": True,
            "min_sample_size": kwargs["min_sample_size"],
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plan_feedback."
        "topic_plan_feedback_repo.get_topic_plan_feedback_report",
        mock_get_topic_plan_feedback_report,
    )

    result = await get_topic_plan_feedback_report(
        FakeContext(FakeAppContext()),
        account_id="wechat-ai-tools",
        window_days=14,
        min_sample_size=3,
    )

    assert result["planned_count"] == 1
    assert result["acceptance_rate"] == 1.0


@pytest.mark.asyncio
async def test_get_topic_plan_feedback_report_validates_window_days():
    result = await get_topic_plan_feedback_report(
        FakeContext(FakeAppContext()),
        window_days=0,
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "window_days"


@pytest.mark.asyncio
async def test_get_topic_plan_feedback_report_validates_min_sample_size():
    result = await get_topic_plan_feedback_report(
        FakeContext(FakeAppContext()),
        min_sample_size=0,
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "min_sample_size"
