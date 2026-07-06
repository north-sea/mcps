from unittest.mock import AsyncMock, MagicMock

import pytest

from hermes_db_mcp.services.schema import inspect_novel_retrospective_contracts_schema


TABLE_COLUMNS = {
    "novel_retrospective_reports": {
        "report_id", "book_slug", "batch_label", "mode", "start_chapter", "end_chapter",
        "scoring_version", "diagnosis_json", "llm_narrative", "confidence", "warnings",
        "review_status", "created_at", "updated_at",
    },
    "novel_retrospective_alerts": {
        "alert_id", "report_id", "alert_type", "severity", "description",
        "evidence_refs", "suggested_action", "created_at",
    },
    "novel_correction_constraints": {
        "constraint_id", "book_slug", "source_report_id", "alert_type", "description",
        "target_chapters", "status", "expires_at", "created_at", "updated_at",
    },
    "novel_handoff_packages": {
        "package_id", "book_slug", "snapshot_chapter", "context_version",
        "progress_json", "character_states_json", "recent_changes", "remaining_tasks",
        "disabled_templates", "stage_reminders", "created_at",
    },
    "novel_character_states": {
        "state_id", "book_slug", "character_name", "last_chapter", "location",
        "relationships_json", "emotional_state", "goals", "conflicts", "arc_progress",
        "dialogue_style", "personality_traits", "created_at", "updated_at",
    },
    "novel_learning_candidates": {
        "candidate_id", "source_report_id", "scope", "trigger_conditions",
        "proposed_action", "evidence_refs", "confidence", "status", "created_at",
        "updated_at",
    },
}


def make_pool(missing_table: str | None = None):
    async def mock_fetch(query, *args):
        if "information_schema.columns" in query:
            table_name = args[1]
            if table_name == missing_table:
                return []
            return [{"column_name": col} for col in TABLE_COLUMNS.get(table_name, set())]
        if "pg_constraint" in query:
            return [{"conname": name} for name in args[2]]
        if "pg_indexes" in query:
            return [{"indexname": name} for name in args[1]]
        return []

    mock_conn = AsyncMock()
    mock_conn.fetch = mock_fetch
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    return mock_pool


@pytest.mark.asyncio
async def test_novel_retrospective_schema_health_passes_when_contracts_exist():
    result = await inspect_novel_retrospective_contracts_schema(make_pool())

    assert result == {"novel_retrospective_contracts": True}


@pytest.mark.asyncio
async def test_novel_retrospective_schema_health_fails_when_table_missing():
    result = await inspect_novel_retrospective_contracts_schema(
        make_pool(missing_table="novel_handoff_packages")
    )

    assert result == {"novel_retrospective_contracts": False}
