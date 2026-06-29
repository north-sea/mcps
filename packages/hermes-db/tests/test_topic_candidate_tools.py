from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from hermes_db_mcp.tools.topic_candidates import (
    adopt_topic_candidate,
    list_topic_candidate_tracks,
    list_topic_candidates,
    sync_topic_candidate_tracks,
    reject_topic_candidate,
    upsert_topic_candidate,
)


class FakeAppContext:
    def __init__(self):
        self.pool = MagicMock()


class FakeContext:
    def __init__(self, app_context):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = app_context


@pytest.mark.asyncio
async def test_upsert_topic_candidate_success(monkeypatch):
    candidate_id = uuid4()

    async def mock_upsert_candidate(pool, **kwargs):
        assert kwargs["account_id"] == "wechat-ai-tools"
        assert kwargs["track_id"] == "ai-productivity"
        assert kwargs["source_item_id"] == "mock-1"
        return {
            "id": candidate_id,
            "status": "new",
            "created_at": datetime(2026, 6, 29, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 6, 29, tzinfo=timezone.utc),
            "created": True,
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_candidates.topic_candidate_repo.upsert_candidate",
        mock_upsert_candidate,
    )

    result = await upsert_topic_candidate(
        "wechat-ai-tools",
        "ai-productivity",
        "mock",
        "Mock topic",
        "mock:1",
        "2026-06-29T00:00:00Z",
        FakeContext(FakeAppContext()),
        source_item_id="mock-1",
    )

    assert result == {
        "candidate_id": str(candidate_id),
        "status": "new",
        "created_at": "2026-06-29 00:00:00+00:00",
        "updated_at": "2026-06-29 00:00:00+00:00",
        "upserted": "created",
    }


@pytest.mark.asyncio
async def test_upsert_topic_candidate_requires_account_track_and_source_identity():
    ctx = FakeContext(FakeAppContext())

    result = await upsert_topic_candidate(
        "",
        "ai-productivity",
        "mock",
        "Mock topic",
        "mock:1",
        "2026-06-29T00:00:00Z",
        ctx,
        source_item_id="mock-1",
    )
    assert result["error"] == "missing_required_field"
    assert result["field"] == "account_id"

    result = await upsert_topic_candidate(
        "wechat-ai-tools",
        "ai-productivity",
        "mock",
        "Mock topic",
        "mock:1",
        "2026-06-29T00:00:00Z",
        ctx,
    )
    assert result["field"] == "source_url_or_source_item_id"


@pytest.mark.asyncio
async def test_list_topic_candidates_serializes_rows_without_raw_by_default(
    monkeypatch,
):
    candidate_id = uuid4()

    async def mock_list_candidates(pool, **kwargs):
        assert kwargs["include_raw"] is False
        return [
            {
                "id": candidate_id,
                "account_id": "wechat-ai-tools",
                "track_id": "ai-productivity",
                "source": "mock",
                "source_url": "https://example.invalid/topic",
                "source_item_id": "mock-1",
                "title": "Mock topic",
                "summary": "Summary",
                "hot_score": 0.8,
                "fit_score": 0.9,
                "novelty_score": 0.7,
                "status": "new",
                "dedupe_key": "mock:1",
                "captured_at": datetime(2026, 6, 29, tzinfo=timezone.utc),
                "topic_id": None,
                "created_at": datetime(2026, 6, 29, tzinfo=timezone.utc),
                "updated_at": datetime(2026, 6, 29, tzinfo=timezone.utc),
                "raw_payload": {"id": "mock-1"},
            }
        ], 1

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_candidates.topic_candidate_repo.list_candidates",
        mock_list_candidates,
    )

    result = await list_topic_candidates(
        FakeContext(FakeAppContext()), account_id="wechat-ai-tools"
    )

    assert result["total"] == 1
    assert "raw_payload" not in result["items"][0]
    assert result["items"][0]["candidate_id"] == str(candidate_id)


@pytest.mark.asyncio
async def test_reject_topic_candidate_uses_state_machine(monkeypatch):
    candidate_id = uuid4()

    async def mock_get_candidate(pool, **kwargs):
        return {"id": candidate_id, "status": "new"}

    async def mock_update_status(pool, **kwargs):
        assert kwargs["new_status"] == "rejected"
        assert kwargs["rejection_reason"] == "off track"
        return {"id": candidate_id, "status": "rejected", "topic_id": None}

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_candidates.topic_candidate_repo.get_candidate",
        mock_get_candidate,
    )
    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_candidates.topic_candidate_repo.update_status",
        mock_update_status,
    )

    result = await reject_topic_candidate(
        str(candidate_id),
        FakeContext(FakeAppContext()),
        reason="off track",
    )

    assert result == {
        "candidate_id": str(candidate_id),
        "previous_status": "new",
        "status": "rejected",
        "topic_id": None,
    }


@pytest.mark.asyncio
async def test_adopt_topic_candidate_returns_existing_topic_idempotently(monkeypatch):
    candidate_id = uuid4()
    topic_id = uuid4()

    async def mock_get_candidate(pool, **kwargs):
        return {"id": candidate_id, "status": "adopted", "topic_id": topic_id}

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_candidates.topic_candidate_repo.get_candidate",
        mock_get_candidate,
    )

    result = await adopt_topic_candidate(
        str(candidate_id), FakeContext(FakeAppContext())
    )

    assert result == {
        "candidate_id": str(candidate_id),
        "topic_id": str(topic_id),
        "previous_status": "adopted",
        "status": "adopted",
        "duplicate_warning": False,
    }


@pytest.mark.asyncio
async def test_list_topic_candidate_tracks(monkeypatch):
    async def mock_list_tracks(pool, **kwargs):
        assert kwargs["account_id"] == "wechat-ai-tools"
        return [
            {
                "account_id": "wechat-ai-tools",
                "display_name": "AI Tools",
                "enabled": True,
                "draft_target": None,
            }
        ], [
            {
                "account_id": "wechat-ai-tools",
                "track_id": "ai-productivity",
                "name": "AI Productivity",
                "keywords": ["agent"],
                "negative_keywords": [],
                "sources": ["mock"],
                "scoring_profile": {"freshness": 0.4},
                "daily_quota": 5,
                "enabled": True,
            }
        ]

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_candidates.topic_candidate_repo.list_tracks",
        mock_list_tracks,
    )

    result = await list_topic_candidate_tracks(
        FakeContext(FakeAppContext()),
        account_id="wechat-ai-tools",
    )

    assert result["accounts"][0]["account_id"] == "wechat-ai-tools"
    assert result["tracks"][0]["track_id"] == "ai-productivity"


@pytest.mark.asyncio
async def test_sync_topic_candidate_tracks_upserts_valid_config(monkeypatch):
    async def mock_sync_track_config(pool, **kwargs):
        assert kwargs["accounts"] == [
            {
                "account_id": "wechat-ai-tools",
                "display_name": "AI Tools",
                "enabled": True,
                "draft_target": "wechat-ai-tools",
                "metadata": {"aliases": ["AI工具"]},
            }
        ]
        assert kwargs["tracks"][0]["track_id"] == "ai-productivity"
        return {
            "accounts_upserted": 1,
            "tracks_upserted": 1,
            "account_ids": ["wechat-ai-tools"],
            "track_ids": ["wechat-ai-tools:ai-productivity"],
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.topic_candidates.topic_candidate_repo.sync_track_config",
        mock_sync_track_config,
    )

    result = await sync_topic_candidate_tracks(
        [
            {
                "account_id": "wechat-ai-tools",
                "display_name": "AI Tools",
                "draft_target": "wechat-ai-tools",
                "metadata": {"aliases": ["AI工具"]},
            }
        ],
        [
            {
                "account_id": "wechat-ai-tools",
                "track_id": "ai-productivity",
                "name": "AI Productivity",
                "keywords": ["agent"],
                "negative_keywords": [],
                "sources": ["mock"],
                "scoring_profile": {"freshness": 0.4},
                "daily_quota": 5,
            }
        ],
        FakeContext(FakeAppContext()),
    )

    assert result == {
        "accounts_upserted": 1,
        "tracks_upserted": 1,
        "account_ids": ["wechat-ai-tools"],
        "track_ids": ["wechat-ai-tools:ai-productivity"],
    }


@pytest.mark.asyncio
async def test_sync_topic_candidate_tracks_rejects_unknown_account_reference():
    result = await sync_topic_candidate_tracks(
        [],
        [
            {
                "account_id": "missing",
                "track_id": "ai-productivity",
                "name": "AI Productivity",
                "keywords": ["agent"],
                "sources": ["mock"],
            }
        ],
        FakeContext(FakeAppContext()),
    )

    assert result["error"] == "invalid_reference"
    assert result["field"] == "tracks[0].account_id"
