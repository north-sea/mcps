from unittest.mock import AsyncMock

import pytest

from hermes_db_mcp.services.schema import inspect_wechat_publication_ledger_schema


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


@pytest.mark.asyncio
async def test_inspect_wechat_publication_ledger_schema_returns_true_for_complete_schema():
    pool = FakePool(
        [
            [FakeRow(column_name=name) for name in {
                "article_id", "publication_idempotency_key", "account",
                "topic_id", "run_id", "task_id", "draft_artifact_id",
                "published_artifact_id", "publish_artifact_id", "status",
                "dry_run", "title", "published_url", "canonical_url",
                "publish_target", "external_reference", "metadata",
                "published_at", "created_at", "updated_at",
            }],
            [FakeRow(column_name=name) for name in {
                "ref_id", "article_id", "ref_type", "ref_value", "ref_source",
                "is_primary", "metadata", "superseded_at", "created_at",
                "updated_at",
            }],
            [FakeRow(conname=name) for name in {
                "wechat_articles_pkey",
                "uq_wechat_articles_account_idempotency",
                "chk_wechat_articles_status",
                "chk_wechat_articles_reference_for_published",
            }],
            [FakeRow(conname=name) for name in {
                "wechat_article_external_refs_pkey",
                "chk_wechat_article_external_refs_type",
                "chk_wechat_article_external_refs_value_nonempty",
            }],
            [FakeRow(indexname=name) for name in {
                "idx_wechat_articles_account_created",
                "idx_wechat_articles_account_status_created",
                "idx_wechat_articles_topic_created",
                "idx_wechat_articles_run_id",
                "idx_wechat_articles_published_url",
                "idx_wechat_articles_canonical_url",
                "idx_wechat_articles_publish_target_created",
                "uq_wechat_article_external_ref_active",
                "uq_wechat_article_external_ref_article_active",
                "idx_wechat_article_refs_article_created",
                "idx_wechat_article_refs_type_value_active",
            }],
        ]
    )

    assert await inspect_wechat_publication_ledger_schema(pool) == {
        "wechat_publication_ledger": True,
    }


@pytest.mark.asyncio
async def test_inspect_wechat_publication_ledger_schema_reflects_missing_tables():
    pool = FakePool([[], [], [], [], []])

    assert await inspect_wechat_publication_ledger_schema(pool) == {
        "wechat_publication_ledger": False,
    }
