from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from hermes_db_mcp.tools.topic_plans import (
    get_topic_plan,
    list_topic_plans,
    update_topic_plan_status,
    upsert_topic_plan,
)


class FakeAppContext:
    def __init__(self):
        self.pool = MagicMock()


class FakeContext:
    def __init__(self, app_context):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = app_context


def plan_row(*, status="planned"):
    now = datetime(2026, 7, 1, tzinfo=timezone.utc)
    return {
        "plan_id": uuid4(),
        "candidate_id": uuid4(),
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
        "topic_id": None,
        "source": "wechat-agent",
        "created_at": now,
        "updated_at": now,
        "consumed_at": None,
    }


@pytest.mark.asyncio
async def test_upsert_topic_plan_success(monkeypatch):
    row = plan_row()

    async def mock_upsert_topic_plan(pool, **kwargs):
        assert kwargs["account_id"] == "wechat-ai-tools"
        assert kwargs["mark_candidate_shortlisted"] is True
        return {"upserted": "created", "item": row}

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plans.topic_plan_repo.upsert_topic_plan",
        mock_upsert_topic_plan,
    )

    result = await upsert_topic_plan(
        str(row["candidate_id"]),
        "wechat-ai-tools",
        "planned",
        FakeContext(FakeAppContext()),
        track_id="ai-productivity",
        recommended_angle_index=0,
        topic_angles=[{"title": "A"}, {"title": "B"}, {"title": "C"}],
        outline_pack={"title": "Outline"},
        writing_brief={"tone": "calm"},
        image_brief={"cover": {}},
        mark_candidate_shortlisted=True,
    )

    assert result["upserted"] == "created"
    assert result["plan_id"] == str(row["plan_id"])
    assert result["topic_angles"][0]["title"] == "A"


@pytest.mark.asyncio
async def test_upsert_topic_plan_returns_structured_error_when_candidate_shortlist_fails(
    monkeypatch,
):
    candidate_id = uuid4()

    async def mock_conflict(pool, **kwargs):
        from hermes_db_mcp.repositories.topic_plan_repo import TopicPlanShortlistConflict

        raise TopicPlanShortlistConflict(candidate_id)

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plans.topic_plan_repo.upsert_topic_plan",
        mock_conflict,
    )

    result = await upsert_topic_plan(
        str(candidate_id),
        "wechat-ai-tools",
        "planned",
        FakeContext(FakeAppContext()),
        recommended_angle_index=0,
        topic_angles=[{"title": "A"}, {"title": "B"}, {"title": "C"}],
        outline_pack={},
        writing_brief={},
        image_brief={},
        mark_candidate_shortlisted=True,
    )

    assert result["error"] == "invalid_transition"
    assert result["field"] == "candidate_id"
    assert result["details"]["candidate_id"] == str(candidate_id)


@pytest.mark.asyncio
async def test_upsert_topic_plan_rejects_shortlist_for_rejected_status():
    result = await upsert_topic_plan(
        str(uuid4()),
        "wechat-ai-tools",
        "rejected",
        FakeContext(FakeAppContext()),
        rejection_reason="off track",
        mark_candidate_shortlisted=True,
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "mark_candidate_shortlisted"


@pytest.mark.asyncio
async def test_upsert_topic_plan_requires_planned_payload_shape():
    result = await upsert_topic_plan(
        str(uuid4()),
        "wechat-ai-tools",
        "planned",
        FakeContext(FakeAppContext()),
        topic_angles=[{"title": "only one"}],
    )

    assert result["error"] == "missing_required_field"
    assert result["field"] == "recommended_angle_index"


@pytest.mark.asyncio
async def test_list_topic_plans_validates_status(monkeypatch):
    result = await list_topic_plans(FakeContext(FakeAppContext()), status="bad")

    assert result["error"] == "invalid_status"
    assert result["field"] == "status"


@pytest.mark.asyncio
async def test_list_topic_plans_success(monkeypatch):
    row = plan_row()

    async def mock_list_topic_plans(pool, **kwargs):
        assert kwargs["status"] == "planned"
        return [row], 1

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plans.topic_plan_repo.list_topic_plans",
        mock_list_topic_plans,
    )

    result = await list_topic_plans(
        FakeContext(FakeAppContext()),
        account_id="wechat-ai-tools",
        status="planned",
    )

    assert result["total"] == 1
    assert result["items"][0]["plan_id"] == str(row["plan_id"])


@pytest.mark.asyncio
async def test_get_topic_plan_not_found(monkeypatch):
    async def mock_get_topic_plan(pool, **kwargs):
        return None

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plans.topic_plan_repo.get_topic_plan",
        mock_get_topic_plan,
    )

    result = await get_topic_plan(str(uuid4()), FakeContext(FakeAppContext()))

    assert result["error"] == "not_found"


@pytest.mark.asyncio
async def test_update_topic_plan_status_returns_previous_status(monkeypatch):
    row = plan_row(status="consumed")

    async def mock_update_topic_plan_status(pool, **kwargs):
        assert kwargs["status"] == "consumed"
        return {**row, "previous_status": "planned"}

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plans.topic_plan_repo.update_topic_plan_status",
        mock_update_topic_plan_status,
    )

    result = await update_topic_plan_status(
        str(row["plan_id"]),
        "consumed",
        FakeContext(FakeAppContext()),
        topic_id=str(uuid4()),
    )

    assert result["previous_status"] == "planned"
    assert result["plan_id"] == str(row["plan_id"])
    assert result["status"] == "consumed"


@pytest.mark.asyncio
async def test_update_topic_plan_status_returns_invalid_transition(monkeypatch):
    from hermes_db_mcp.repositories.topic_plan_repo import TopicPlanInvalidTransition

    async def mock_update_topic_plan_status(pool, **kwargs):
        raise TopicPlanInvalidTransition("archived", "planned", [])

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_plans.topic_plan_repo.update_topic_plan_status",
        mock_update_topic_plan_status,
    )

    result = await update_topic_plan_status(
        str(uuid4()),
        "planned",
        FakeContext(FakeAppContext()),
    )

    assert result["error"] == "invalid_transition"
    assert result["from"] == "archived"
    assert result["to"] == "planned"
    assert result["allowed"] == []
