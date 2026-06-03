import pytest

from hermes_db_mcp.repositories import wechat_article_repo


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.fetchrow_calls = []
        self.fetch_calls = []

    def transaction(self):
        return FakeTransaction()

    async def fetchrow(self, sql, *params):
        self.fetchrow_calls.append((sql, params))
        if "INSERT INTO hermes.wechat_articles" in sql:
            return {
                "article_id": params[0],
                "publication_idempotency_key": params[1],
                "account": params[2],
                "topic_id": params[3],
                "run_id": params[4],
                "task_id": params[5],
                "draft_artifact_id": params[6],
                "published_artifact_id": params[7],
                "publish_artifact_id": params[8],
                "status": params[9],
                "dry_run": params[10],
                "title": params[11],
                "published_url": params[12],
                "canonical_url": params[13],
                "publish_target": params[14],
                "external_reference": params[15],
                "metadata": params[16],
                "published_at": params[17],
                "created_at": None,
                "updated_at": None,
                "created": True,
            }
        return None

    async def fetch(self, sql, *params):
        self.fetch_calls.append((sql, params))
        return []


class FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self):
        self.conn = FakeConnection()

    def acquire(self):
        return FakeAcquire(self.conn)


@pytest.mark.asyncio
async def test_upsert_article_uses_account_idempotency_conflict():
    pool = FakePool()

    row, created = await wechat_article_repo.upsert_article(
        pool,
        publication_idempotency_key="key-1",
        account="acct",
        run_id="run-1",
        status="published",
        published_url="https://mp.weixin.qq.com/s/abc",
    )

    sql, params = pool.conn.fetchrow_calls[0]
    assert created is True
    assert row["publication_idempotency_key"] == "key-1"
    assert "ON CONFLICT (account, publication_idempotency_key)" in sql
    assert params[1:5] == ("key-1", "acct", None, "run-1")


@pytest.mark.asyncio
async def test_list_articles_builds_parameterized_filters():
    pool = FakePool()

    await wechat_article_repo.list_articles(
        pool,
        account="acct",
        run_id="run-1",
        status="published",
        limit=10,
        offset=5,
    )

    sql, params = pool.conn.fetch_calls[0]
    assert "account = $1" in sql
    assert "run_id = $2" in sql
    assert "status = $3" in sql
    assert "LIMIT $4 OFFSET $5" in sql
    assert params == ("acct", "run-1", "published", 10, 5)
    assert "content_text" not in sql
