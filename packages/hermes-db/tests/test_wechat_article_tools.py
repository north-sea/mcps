from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from hermes_db_mcp.tools.wechat_articles import (
    get_wechat_article,
    list_wechat_articles,
    update_wechat_article_external_refs,
    upsert_wechat_article,
)


class FakeAppContext:
    def __init__(self):
        self.pool = MagicMock()


class FakeContext:
    def __init__(self, app_context):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = app_context


def article_row(**overrides):
    row = {
        "article_id": uuid4(),
        "publication_idempotency_key": "key-1",
        "account": "acct",
        "topic_id": None,
        "run_id": "run-1",
        "task_id": None,
        "draft_artifact_id": "artifact-draft",
        "published_artifact_id": "artifact-final",
        "publish_artifact_id": "artifact-publish",
        "status": "published",
        "dry_run": False,
        "title": "Title",
        "published_url": "https://mp.weixin.qq.com/s/abc",
        "canonical_url": None,
        "publish_target": "wechat-mp",
        "external_reference": None,
        "metadata": {},
        "published_at": None,
        "created_at": datetime(2026, 6, 3),
        "updated_at": datetime(2026, 6, 3),
    }
    row.update(overrides)
    return row


def ref_row(article_id, **overrides):
    row = {
        "ref_id": uuid4(),
        "article_id": article_id,
        "ref_type": "published_url",
        "ref_value": "https://mp.weixin.qq.com/s/abc",
        "ref_source": "publisher",
        "is_primary": True,
        "metadata": {},
        "superseded_at": None,
        "created_at": datetime(2026, 6, 3),
        "updated_at": datetime(2026, 6, 3),
    }
    row.update(overrides)
    return row


@pytest.mark.asyncio
async def test_upsert_wechat_article_success(monkeypatch):
    row = article_row()

    async def mock_upsert_article(pool, **kwargs):
        assert kwargs["publication_idempotency_key"] == "key-1"
        return row, True

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_articles.wechat_article_repo.upsert_article",
        mock_upsert_article,
    )

    result = await upsert_wechat_article(
        "acct",
        "run-1",
        "published",
        FakeContext(FakeAppContext()),
        publication_idempotency_key="key-1",
        published_url="https://mp.weixin.qq.com/s/abc",
    )

    assert result["article_id"] == str(row["article_id"])
    assert result["created"] is True
    assert result["external_refs"] == []


@pytest.mark.asyncio
async def test_upsert_wechat_article_rejects_missing_reference_for_published():
    result = await upsert_wechat_article(
        "acct",
        "run-1",
        "published",
        FakeContext(FakeAppContext()),
        publication_idempotency_key="key-1",
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "published_url"


@pytest.mark.asyncio
async def test_list_wechat_articles_omits_artifact_content(monkeypatch):
    row = article_row()

    async def mock_list_articles(pool, **kwargs):
        return [row]

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_articles.wechat_article_repo.list_articles",
        mock_list_articles,
    )

    result = await list_wechat_articles(FakeContext(FakeAppContext()), account="acct")

    assert result["items"][0]["article_id"] == str(row["article_id"])
    assert "content_text" not in result["items"][0]


@pytest.mark.asyncio
async def test_get_wechat_article_returns_refs(monkeypatch):
    row = article_row()
    ref = ref_row(row["article_id"])

    async def mock_get_article(pool, article_id):
        return row

    async def mock_list_article_refs(pool, article_id):
        return [ref]

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_articles.wechat_article_repo.get_article",
        mock_get_article,
    )
    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_articles.wechat_article_repo.list_article_refs",
        mock_list_article_refs,
    )

    result = await get_wechat_article(str(row["article_id"]), FakeContext(FakeAppContext()))

    assert result["article_id"] == str(row["article_id"])
    assert result["external_refs"][0]["ref_value"] == ref["ref_value"]


@pytest.mark.asyncio
async def test_get_wechat_article_not_found(monkeypatch):
    async def mock_get_article(pool, article_id):
        return None

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_articles.wechat_article_repo.get_article",
        mock_get_article,
    )

    result = await get_wechat_article(str(uuid4()), FakeContext(FakeAppContext()))

    assert result["error"] == "not_found"
    assert result["field"] == "article_id"


@pytest.mark.asyncio
async def test_update_wechat_article_external_refs_success(monkeypatch):
    row = article_row()
    ref = ref_row(row["article_id"], ref_type="canonical_url")

    async def mock_patch_article_refs_and_summary(pool, article_id, refs, patch):
        return row, [ref]

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_articles.wechat_article_repo.patch_article_refs_and_summary",
        mock_patch_article_refs_and_summary,
    )

    result = await update_wechat_article_external_refs(
        str(row["article_id"]),
        FakeContext(FakeAppContext()),
        refs=[{"ref_type": "canonical_url", "ref_value": "https://mp.weixin.qq.com/s/abc"}],
        patch={"status": "published"},
    )

    assert result["article_id"] == str(row["article_id"])
    assert result["external_refs"][0]["ref_type"] == "canonical_url"


@pytest.mark.asyncio
async def test_update_wechat_article_external_refs_conflict(monkeypatch):
    row = article_row()

    async def mock_patch_article_refs_and_summary(pool, article_id, refs, patch):
        raise ValueError("external_ref_conflict")

    monkeypatch.setattr(
        "hermes_db_mcp.tools.wechat_articles.wechat_article_repo.patch_article_refs_and_summary",
        mock_patch_article_refs_and_summary,
    )

    result = await update_wechat_article_external_refs(
        str(row["article_id"]),
        FakeContext(FakeAppContext()),
        refs=[{"ref_type": "canonical_url", "ref_value": "https://mp.weixin.qq.com/s/abc"}],
    )

    assert result["error"] == "conflict"
    assert result["field"] == "external_ref"
