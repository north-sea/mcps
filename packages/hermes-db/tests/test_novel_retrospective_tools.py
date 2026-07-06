from unittest.mock import MagicMock, patch

import pytest

from hermes_db_mcp.tools import novel_retrospective


REPORT_ID = "11111111-1111-1111-1111-111111111111"
CONSTRAINT_ID = "22222222-2222-2222-2222-222222222222"
PACKAGE_ID = "33333333-3333-3333-3333-333333333333"


def ctx():
    mock_ctx = MagicMock()
    mock_ctx.request_context.lifespan_context = MagicMock(pool=MagicMock())
    return mock_ctx


@pytest.mark.asyncio
async def test_create_report_validates_mode():
    result = await novel_retrospective.create_novel_retrospective_report(
        {
            "book_slug": "book",
            "batch_label": "ch_001-003",
            "mode": "invalid",
            "start_chapter": 1,
            "end_chapter": 3,
            "scoring_version": "v1",
            "diagnosis_json": {},
            "confidence": "high",
        },
        ctx(),
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "mode"


@pytest.mark.asyncio
@patch("hermes_db_mcp.tools.novel_retrospective.novel_retrospective_repo.create_retrospective_report")
async def test_create_report_calls_repo(mock_create):
    mock_create.return_value = {"report_id": REPORT_ID}

    result = await novel_retrospective.create_novel_retrospective_report(
        {
            "book_slug": "book",
            "batch_label": "ch_001-003",
            "mode": "batch",
            "start_chapter": 1,
            "end_chapter": 3,
            "scoring_version": "v1",
            "diagnosis_json": {"alerts": []},
            "confidence": "high",
        },
        ctx(),
    )

    assert result == {"report_id": REPORT_ID}
    assert mock_create.await_count == 1


@pytest.mark.asyncio
@patch("hermes_db_mcp.tools.novel_retrospective.novel_retrospective_repo.list_retrospective_reports")
async def test_list_reports_wraps_items(mock_list):
    mock_list.return_value = [{"report_id": REPORT_ID}]

    result = await novel_retrospective.list_novel_retrospective_reports("book", ctx())

    assert result == {"items": [{"report_id": REPORT_ID}]}


@pytest.mark.asyncio
async def test_update_report_status_rejects_bad_uuid():
    result = await novel_retrospective.update_novel_retrospective_report_review_status(
        "bad-id",
        "approved",
        ctx(),
    )

    assert result["error"] == "invalid_uuid"
    assert result["field"] == "report_id"


@pytest.mark.asyncio
async def test_create_alert_validates_alert_type():
    result = await novel_retrospective.create_novel_retrospective_alert(
        {
            "report_id": REPORT_ID,
            "alert_type": "bad",
            "severity": "yellow",
            "description": "desc",
        },
        ctx(),
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "alert_type"


@pytest.mark.asyncio
@patch("hermes_db_mcp.tools.novel_retrospective.novel_retrospective_repo.create_correction_constraint")
async def test_create_correction_constraint_defaults_status(mock_create):
    mock_create.return_value = {"constraint_id": CONSTRAINT_ID}

    await novel_retrospective.create_novel_correction_constraint(
        {
            "book_slug": "book",
            "source_report_id": REPORT_ID,
            "alert_type": "high_similarity",
            "description": "fix pacing",
            "target_chapters": "next",
        },
        ctx(),
    )

    assert mock_create.await_args.args[1]["status"] == "pending"


@pytest.mark.asyncio
@patch("hermes_db_mcp.tools.novel_retrospective.novel_retrospective_repo.create_handoff_package")
async def test_create_handoff_package_calls_repo(mock_create):
    mock_create.return_value = {"package_id": PACKAGE_ID}

    result = await novel_retrospective.create_novel_handoff_package(
        {
            "book_slug": "book",
            "snapshot_chapter": 10,
            "context_version": 2,
            "progress_json": {"completed_chapters": 10, "total_planned_chapters": 100},
        },
        ctx(),
    )

    assert result == {"package_id": PACKAGE_ID}


@pytest.mark.asyncio
async def test_upsert_character_state_requires_last_chapter_positive():
    result = await novel_retrospective.upsert_novel_character_state(
        {
            "book_slug": "book",
            "character_name": "A",
            "last_chapter": 0,
            "location": "city",
            "emotional_state": "calm",
            "arc_progress": "start",
            "dialogue_style": "short",
        },
        ctx(),
    )

    assert result["error"] == "invalid_field"
    assert result["field"] == "last_chapter"


@pytest.mark.asyncio
@patch("hermes_db_mcp.tools.novel_retrospective.inspect_novel_retrospective_contracts_schema")
async def test_health_novel_retrospective_reports_ready(mock_inspect):
    mock_inspect.return_value = {"novel_retrospective_contracts": True}

    result = await novel_retrospective.health_novel_retrospective(ctx())

    assert result == {"status": "ok", "novel_retrospective_contracts": True}


@pytest.mark.asyncio
@patch("hermes_db_mcp.tools.novel_retrospective.novel_retrospective_repo.list_learning_candidates")
async def test_list_learning_candidates_wraps_items(mock_list):
    mock_list.return_value = [{"candidate_id": "c"}]

    result = await novel_retrospective.list_novel_learning_candidates(REPORT_ID, ctx())

    assert result == {"items": [{"candidate_id": "c"}]}
