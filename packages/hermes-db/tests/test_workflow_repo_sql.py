import pytest

from hermes_db_mcp.repositories import workflow_repo


class FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self):
        self.fetchrow_calls = []
        self.fetch_calls = []
        self.fetchval_calls = []
        self.execute_calls = []

    def transaction(self):
        return FakeTransaction()

    async def execute(self, sql, *params):
        self.execute_calls.append((sql, params))

    async def fetchrow(self, sql, *params):
        self.fetchrow_calls.append((sql, params))
        if "WHERE artifact_id = $1" in sql and "content_text" in sql:
            return {
                "artifact_id": params[0],
                "run_id": "run-1",
                "task_id": None,
                "topic_id": None,
                "account": None,
                "stage": "draft",
                "type": "draft",
                "name": "draft",
                "version": 1,
                "parent_artifact_id": None,
                "content_hash": "sha256:abc",
                "content_size_bytes": 7,
                "content_preview": None,
                "content_ref": None,
                "content_text": "# Draft",
                "metadata": {},
                "created_at": None,
                "updated_at": None,
            }
        if "INSERT INTO hermes.workflow_artifacts" in sql:
            return {
                "artifact_id": params[0],
                "run_id": params[1],
                "task_id": params[2],
                "topic_id": params[3],
                "account": params[4],
                "stage": params[5],
                "type": params[6],
                "name": params[7],
                "version": params[8],
                "parent_artifact_id": params[9],
                "content_hash": params[10],
                "content_size_bytes": params[11],
                "content_preview": params[12],
                "content_ref": params[14],
                "metadata": params[15],
                "created_at": None,
                "updated_at": None,
            }
        return None

    async def fetch(self, sql, *params):
        self.fetch_calls.append((sql, params))
        if "FROM hermes.workflow_artifacts" in sql and "ORDER BY version" in sql:
            return [
                {
                    "artifact_id": "artifact-1",
                    "run_id": params[0],
                    "task_id": None,
                    "topic_id": None,
                    "account": None,
                    "stage": params[1],
                    "type": "draft",
                    "name": params[2],
                    "version": 1,
                    "parent_artifact_id": None,
                    "content_hash": "sha256:abc",
                    "content_size_bytes": 7,
                    "content_preview": None,
                    "content_ref": None,
                    "metadata": {},
                    "created_at": None,
                    "updated_at": None,
                }
            ]
        return []

    async def fetchval(self, sql, *params):
        self.fetchval_calls.append((sql, params))
        return 1


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
async def test_upsert_artifact_uses_advisory_lock_and_version_query():
    pool = FakePool()

    row, created, outcome = await workflow_repo.upsert_artifact(
        pool,
        artifact_id="artifact-1",
        run_id="run-1",
        stage="draft",
        type="draft",
        name="draft",
        content_hash="sha256:abc",
        content_size_bytes=7,
        content_text="# Draft",
    )

    assert created is True
    assert outcome["idempotency_hit"] is False
    assert outcome["provided_content_hash"] == "sha256:abc"
    assert row["version"] == 1
    assert "pg_advisory_xact_lock" in pool.conn.execute_calls[0][0]
    assert "max(version)" in pool.conn.fetchval_calls[0][0]
    assert "FOR UPDATE" not in pool.conn.fetchval_calls[0][0]


@pytest.mark.asyncio
async def test_list_artifacts_builds_parameterized_filters():
    pool = FakePool()

    await workflow_repo.list_artifacts(
        pool,
        run_id="run-1",
        account="account-a",
        type="draft",
        limit=10,
        offset=5,
    )

    sql, params = pool.conn.fetch_calls[0]
    assert "run_id = $1" in sql
    assert "account = $2" in sql
    assert "type = $3" in sql
    assert "LIMIT $4 OFFSET $5" in sql
    assert params == ("run-1", "account-a", "draft", 10, 5)
    assert "content_text" not in sql


@pytest.mark.asyncio
async def test_list_artifact_versions_resolves_artifact_selector_and_orders_by_version():
    pool = FakePool()

    rows, selector = await workflow_repo.list_artifact_versions(
        pool,
        artifact_id="artifact-1",
        order="desc",
        limit=10,
        offset=0,
    )

    assert selector == {
        "artifact_id": "artifact-1",
        "run_id": "run-1",
        "stage": "draft",
        "name": "draft",
    }
    sql, params = pool.conn.fetch_calls[0]
    assert "WHERE run_id = $1 AND stage = $2 AND name = $3" in sql
    assert "ORDER BY version DESC" in sql
    assert params == ("run-1", "draft", "draft", 10, 0)
    assert rows[0]["artifact_id"] == "artifact-1"


@pytest.mark.asyncio
async def test_get_latest_artifact_version_uses_desc_limit_one():
    pool = FakePool()

    row, selector = await workflow_repo.get_latest_artifact_version(
        pool,
        run_id="run-1",
        stage="draft",
        name="draft",
    )

    sql, params = pool.conn.fetch_calls[0]
    assert selector["run_id"] == "run-1"
    assert "ORDER BY version DESC" in sql
    assert params == ("run-1", "draft", "draft", 1, 0)
    assert row["version"] == 1
