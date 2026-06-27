from datetime import datetime
from unittest.mock import MagicMock

import pytest

from hermes_db_mcp.tools import workflow_artifacts
from hermes_db_mcp.tools.workflow_artifacts import (
    create_workflow_artifact_version,
    diff_workflow_artifacts,
    get_latest_workflow_artifact_version,
    get_workflow_artifact_content,
    list_workflow_artifact_versions,
    list_workflow_artifacts,
    upsert_workflow_artifact,
)
from hermes_db_mcp.tools.workflow_runs import finish_workflow_run, upsert_workflow_run


class FakeAppContext:
    def __init__(self):
        self.pool = MagicMock()


class FakeContext:
    def __init__(self, app_context):
        self.request_context = MagicMock()
        self.request_context.lifespan_context = app_context


@pytest.mark.asyncio
async def test_upsert_workflow_run_success(monkeypatch):
    async def mock_upsert_run(pool, **kwargs):
        return {
            **kwargs,
            "summary": None,
            "failure_reason": None,
            "missing_inputs": [],
            "next_action": None,
            "completed_at": None,
            "created_at": datetime(2026, 6, 3),
            "updated_at": datetime(2026, 6, 3),
            "created": True,
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.workflow_runs.workflow_repo.upsert_run",
        mock_upsert_run,
    )

    result = await upsert_workflow_run("run-1", "draft", "running", FakeContext(FakeAppContext()))

    assert result["run_id"] == "run-1"
    assert result["created"] is True


@pytest.mark.asyncio
async def test_finish_workflow_run_not_found(monkeypatch):
    async def mock_finish_run(pool, **kwargs):
        return None

    monkeypatch.setattr(
        "hermes_db_mcp.tools.workflow_runs.workflow_repo.finish_run",
        mock_finish_run,
    )

    result = await finish_workflow_run("run-404", "done", "completed", FakeContext(FakeAppContext()))

    assert result["error"] == "not_found"
    assert result["field"] == "run_id"


@pytest.mark.asyncio
async def test_upsert_workflow_artifact_success(monkeypatch):
    async def mock_upsert_artifact(pool, **kwargs):
        return {
            **kwargs,
            "artifact_id": kwargs["artifact_id"] or "artifact-1",
            "version": 1,
            "created_at": datetime(2026, 6, 3),
            "updated_at": datetime(2026, 6, 3),
        }, True, {"idempotency_hit": False, "provided_content_hash": kwargs["content_hash"]}

    monkeypatch.setattr(
        "hermes_db_mcp.tools.workflow_artifacts.workflow_repo.upsert_artifact",
        mock_upsert_artifact,
    )

    result = await upsert_workflow_artifact(
        "run-1",
        "draft",
        "draft",
        "draft",
        "sha256:abc",
        7,
        FakeContext(FakeAppContext()),
        content_text="# Draft",
    )

    assert result["artifact_id"] == "artifact-1"
    assert result["version"] == 1
    assert result["created"] is True
    assert result["idempotency_hit"] is False
    assert result["provided_content_hash"] == "sha256:abc"
    assert "content_text" not in result


@pytest.mark.asyncio
async def test_upsert_workflow_artifact_idempotency_hit_returns_context(monkeypatch):
    async def mock_upsert_artifact(pool, **kwargs):
        return {
            **kwargs,
            "artifact_id": kwargs["artifact_id"] or "artifact-1",
            "version": 1,
            "created_at": datetime(2026, 6, 3),
            "updated_at": datetime(2026, 6, 3),
        }, False, {
            "idempotency_hit": True,
            "skipped_update_reason": "artifact_id_content_hash_match",
            "existing_content_hash": "sha256:abc",
            "provided_content_hash": "sha256:abc",
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.workflow_artifacts.workflow_repo.upsert_artifact",
        mock_upsert_artifact,
    )

    result = await upsert_workflow_artifact(
        "run-1",
        "draft",
        "draft",
        "draft",
        "sha256:abc",
        7,
        FakeContext(FakeAppContext()),
        artifact_id="artifact-1",
        content_text="# Draft",
    )

    assert result["created"] is False
    assert result["idempotency_hit"] is True
    assert result["skipped_update_reason"] == "artifact_id_content_hash_match"
    assert result["existing_content_hash"] == "sha256:abc"


@pytest.mark.asyncio
async def test_upsert_workflow_artifact_conflict_returns_remediation(monkeypatch):
    async def mock_upsert_artifact(pool, **kwargs):
        raise workflow_artifacts.workflow_repo.ArtifactIdConflictError(
            existing_content_hash="sha256:old",
            provided_content_hash="sha256:new",
        )

    monkeypatch.setattr(
        "hermes_db_mcp.tools.workflow_artifacts.workflow_repo.upsert_artifact",
        mock_upsert_artifact,
    )

    result = await upsert_workflow_artifact(
        "run-1",
        "draft",
        "draft",
        "draft",
        "sha256:new",
        7,
        FakeContext(FakeAppContext()),
        artifact_id="artifact-1",
        content_text="# Draft",
    )

    assert result["error"] == "artifact_id_conflict"
    assert result["field"] == "artifact_id"
    assert result["details"]["existing_content_hash"] == "sha256:old"
    assert result["details"]["provided_content_hash"] == "sha256:new"
    assert result["next_action"] == "create_workflow_artifact_version"
    assert result["retryable"] is False


@pytest.mark.asyncio
async def test_create_workflow_artifact_version_derives_parent_fields(monkeypatch):
    parent = make_artifact("artifact-parent", version=1)

    async def mock_get_artifact(pool, *, artifact_id):
        assert artifact_id in ("artifact-parent", "artifact-child")
        return parent if artifact_id == "artifact-parent" else make_artifact("artifact-child", version=2, parent_artifact_id="artifact-parent")

    async def mock_upsert_artifact(pool, **kwargs):
        assert kwargs["run_id"] == parent["run_id"]
        assert kwargs["stage"] == parent["stage"]
        assert kwargs["name"] == parent["name"]
        assert kwargs["parent_artifact_id"] == "artifact-parent"
        return {
            **kwargs,
            "artifact_id": "artifact-child",
            "version": 2,
            "created_at": datetime(2026, 6, 4),
            "updated_at": datetime(2026, 6, 4),
        }, True, {"idempotency_hit": False, "provided_content_hash": kwargs["content_hash"]}

    async def mock_list_artifact_versions(pool, **kwargs):
        return [
            parent,
            make_artifact("artifact-child", version=2, parent_artifact_id="artifact-parent"),
        ], {"artifact_id": "artifact-child", "run_id": "run-1", "stage": "draft", "name": "draft"}

    monkeypatch.setattr("hermes_db_mcp.tools.workflow_artifacts.workflow_repo.get_artifact", mock_get_artifact)
    monkeypatch.setattr("hermes_db_mcp.tools.workflow_artifacts.workflow_repo.upsert_artifact", mock_upsert_artifact)
    monkeypatch.setattr("hermes_db_mcp.tools.workflow_artifacts.workflow_repo.list_artifact_versions", mock_list_artifact_versions)

    result = await create_workflow_artifact_version(
        "artifact-parent",
        "sha256:new",
        11,
        FakeContext(FakeAppContext()),
        content_text="# Revision",
    )

    assert result["artifact_id"] == "artifact-child"
    assert result["parent_artifact_id"] == "artifact-parent"
    assert result["version"] == 2
    assert result["created"] is True
    assert result["lineage_root_artifact_id"] == "artifact-parent"


@pytest.mark.asyncio
async def test_create_workflow_artifact_version_missing_parent(monkeypatch):
    async def mock_get_artifact(pool, *, artifact_id):
        return None

    monkeypatch.setattr("hermes_db_mcp.tools.workflow_artifacts.workflow_repo.get_artifact", mock_get_artifact)

    result = await create_workflow_artifact_version(
        "missing-parent",
        "sha256:new",
        11,
        FakeContext(FakeAppContext()),
        content_text="# Revision",
    )

    assert result["error"] == "not_found"
    assert result["field"] == "parent_artifact_id"
    assert result["next_action"] == "fetch_or_create_parent_artifact"


@pytest.mark.asyncio
async def test_upsert_workflow_artifact_missing_run_returns_next_action(monkeypatch):
    async def mock_upsert_artifact(pool, **kwargs):
        raise Exception('insert or update on table "workflow_artifacts" violates foreign key constraint "workflow_artifacts_run_id_fkey"')

    monkeypatch.setattr(
        "hermes_db_mcp.tools.workflow_artifacts.workflow_repo.upsert_artifact",
        mock_upsert_artifact,
    )

    result = await upsert_workflow_artifact(
        "missing-run",
        "draft",
        "draft",
        "draft",
        "sha256:abc",
        7,
        FakeContext(FakeAppContext()),
        content_text="# Draft",
    )

    assert result["error"] == "database_error"
    assert result["field"] == "run_id"
    assert result["details"] == {"reason": "workflow_run_missing"}
    assert result["next_action"] == "upsert_workflow_run"
    assert result["retryable"] is False


@pytest.mark.asyncio
async def test_list_workflow_artifacts_omits_content_text(monkeypatch):
    async def mock_list_artifacts(pool, **kwargs):
        return [
            {
                "artifact_id": "artifact-1",
                "run_id": kwargs["run_id"],
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
                "content_preview": "# Draft",
                "content_ref": None,
                "content_text": "# Draft",
                "metadata": {},
                "created_at": datetime(2026, 6, 3),
                "updated_at": datetime(2026, 6, 3),
            }
        ]

    monkeypatch.setattr(
        "hermes_db_mcp.tools.workflow_artifacts.workflow_repo.list_artifacts",
        mock_list_artifacts,
    )

    result = await list_workflow_artifacts(FakeContext(FakeAppContext()), run_id="run-1")

    assert result["items"][0]["artifact_id"] == "artifact-1"
    assert "content_text" not in result["items"][0]


@pytest.mark.asyncio
async def test_list_workflow_artifact_versions_returns_lineage(monkeypatch):
    async def mock_list_artifact_versions(pool, **kwargs):
        assert kwargs["artifact_id"] == "artifact-parent"
        return [
            make_artifact("artifact-parent", version=1),
            make_artifact("artifact-child", version=2, parent_artifact_id="artifact-parent"),
        ], {"artifact_id": "artifact-parent", "run_id": "run-1", "stage": "draft", "name": "draft"}

    monkeypatch.setattr(
        "hermes_db_mcp.tools.workflow_artifacts.workflow_repo.list_artifact_versions",
        mock_list_artifact_versions,
    )

    result = await list_workflow_artifact_versions(
        FakeContext(FakeAppContext()),
        artifact_id="artifact-parent",
    )

    assert [item["version"] for item in result["items"]] == [1, 2]
    assert result["lineage_root_artifact_id"] == "artifact-parent"
    assert result["latest_artifact_id"] == "artifact-child"


@pytest.mark.asyncio
async def test_list_workflow_artifact_versions_requires_selector():
    result = await list_workflow_artifact_versions(FakeContext(FakeAppContext()))

    assert result["error"] == "invalid_filter"
    assert result["next_action"] == "provide_artifact_id_or_logical_tuple"


@pytest.mark.asyncio
async def test_get_latest_workflow_artifact_version_returns_highest_version(monkeypatch):
    async def mock_get_latest_artifact_version(pool, **kwargs):
        assert kwargs["run_id"] == "run-1"
        return make_artifact("artifact-child", version=2, parent_artifact_id="artifact-parent"), {
            "artifact_id": None,
            "run_id": "run-1",
            "stage": "draft",
            "name": "draft",
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.workflow_artifacts.workflow_repo.get_latest_artifact_version",
        mock_get_latest_artifact_version,
    )

    result = await get_latest_workflow_artifact_version(
        FakeContext(FakeAppContext()),
        run_id="run-1",
        stage="draft",
        name="draft",
    )

    assert result["artifact"]["artifact_id"] == "artifact-child"
    assert result["artifact"]["version"] == 2


@pytest.mark.asyncio
async def test_diff_workflow_artifacts_returns_bounded_inline_diff(monkeypatch):
    async def mock_get_artifact(pool, *, artifact_id):
        if artifact_id == "left":
            return make_artifact("left", version=1, content_text="hello\nold\n")
        return make_artifact("right", version=2, parent_artifact_id="left", content_hash="sha256:right", content_text="hello\nnew\n")

    monkeypatch.setattr("hermes_db_mcp.tools.workflow_artifacts.workflow_repo.get_artifact", mock_get_artifact)

    result = await diff_workflow_artifacts("left", "right", FakeContext(FakeAppContext()), max_preview_lines=20)

    assert result["content_changed"] is True
    assert result["content_diff_available"] is True
    assert result["metadata_changes"] == {"added": [], "removed": [], "changed": []}
    assert any("-old" in line for line in result["content_diff"]["preview"])
    assert any("+new" in line for line in result["content_diff"]["preview"])


@pytest.mark.asyncio
async def test_diff_workflow_artifacts_does_not_dereference_content_ref(monkeypatch):
    async def mock_get_artifact(pool, *, artifact_id):
        if artifact_id == "left":
            return make_artifact("left", version=1, content_text=None, content_ref="s3://left")
        return make_artifact("right", version=2, content_text="inline")

    monkeypatch.setattr("hermes_db_mcp.tools.workflow_artifacts.workflow_repo.get_artifact", mock_get_artifact)

    result = await diff_workflow_artifacts("left", "right", FakeContext(FakeAppContext()))

    assert result["content_diff_available"] is False
    assert result["content_diff"] is None
    assert "content_ref is not dereferenced" in result["remediation_hint"]


@pytest.mark.asyncio
async def test_get_workflow_artifact_content_returns_inline(monkeypatch):
    async def mock_get_artifact(pool, artifact_id):
        return {
            "artifact_id": artifact_id,
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
            "content_preview": "# Draft",
            "content_ref": None,
            "content_text": "# Draft",
            "metadata": {},
            "created_at": datetime(2026, 6, 3),
            "updated_at": datetime(2026, 6, 3),
        }

    monkeypatch.setattr(
        "hermes_db_mcp.tools.workflow_artifacts.workflow_repo.get_artifact",
        mock_get_artifact,
    )

    result = await get_workflow_artifact_content("artifact-1", FakeContext(FakeAppContext()))

    assert result["content_text"] == "# Draft"
    assert result["content_inline"] is True


def make_artifact(
    artifact_id,
    *,
    version=1,
    parent_artifact_id=None,
    content_hash="sha256:abc",
    content_text="# Draft",
    content_ref=None,
):
    return {
        "artifact_id": artifact_id,
        "run_id": "run-1",
        "task_id": None,
        "topic_id": None,
        "account": None,
        "stage": "draft",
        "type": "draft",
        "name": "draft",
        "version": version,
        "parent_artifact_id": parent_artifact_id,
        "content_hash": content_hash,
        "content_size_bytes": len(content_text.encode("utf-8")) if isinstance(content_text, str) else 0,
        "content_preview": content_text[:40] if isinstance(content_text, str) else None,
        "content_ref": content_ref,
        "content_text": content_text,
        "metadata": {},
        "created_at": datetime(2026, 6, 3),
        "updated_at": datetime(2026, 6, 3),
    }
