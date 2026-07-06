"""Novel retrospective repository functions."""

from __future__ import annotations

import json
from uuid import UUID

import asyncpg


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load_json(value: object, default: object) -> object:
    if value is None:
        return default
    if isinstance(value, str):
        return json.loads(value)
    return value


def _report(row: asyncpg.Record) -> dict:
    return {
        "report_id": str(row["report_id"]),
        "book_slug": row["book_slug"],
        "batch_label": row["batch_label"],
        "mode": row["mode"],
        "start_chapter": row["start_chapter"],
        "end_chapter": row["end_chapter"],
        "scoring_version": row["scoring_version"],
        "diagnosis_json": _load_json(row["diagnosis_json"], {}),
        "llm_narrative": row["llm_narrative"],
        "confidence": row["confidence"],
        "warnings": list(row["warnings"] or []),
        "review_status": row["review_status"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _alert(row: asyncpg.Record) -> dict:
    return {
        "alert_id": str(row["alert_id"]),
        "report_id": str(row["report_id"]),
        "alert_type": row["alert_type"],
        "severity": row["severity"],
        "description": row["description"],
        "evidence_refs": list(row["evidence_refs"] or []),
        "suggested_action": row["suggested_action"],
        "created_at": str(row["created_at"]),
    }


def _constraint(row: asyncpg.Record) -> dict:
    return {
        "constraint_id": str(row["constraint_id"]),
        "book_slug": row["book_slug"],
        "source_report_id": str(row["source_report_id"]),
        "alert_type": row["alert_type"],
        "description": row["description"],
        "target_chapters": row["target_chapters"],
        "status": row["status"],
        "created_at": str(row["created_at"]),
        "expires_at": str(row["expires_at"]) if row["expires_at"] else None,
        "updated_at": str(row["updated_at"]),
    }


def _handoff(row: asyncpg.Record) -> dict:
    return {
        "package_id": str(row["package_id"]),
        "book_slug": row["book_slug"],
        "snapshot_chapter": row["snapshot_chapter"],
        "context_version": row["context_version"],
        "progress_json": _load_json(row["progress_json"], {}),
        "character_states_json": _load_json(row["character_states_json"], []),
        "recent_changes": list(row["recent_changes"] or []),
        "remaining_tasks": list(row["remaining_tasks"] or []),
        "disabled_templates": list(row["disabled_templates"] or []),
        "stage_reminders": list(row["stage_reminders"] or []),
        "created_at": str(row["created_at"]),
    }


def _character_state(row: asyncpg.Record) -> dict:
    return {
        "state_id": str(row["state_id"]),
        "book_slug": row["book_slug"],
        "character_name": row["character_name"],
        "last_chapter": row["last_chapter"],
        "location": row["location"],
        "relationships_json": _load_json(row["relationships_json"], {}),
        "emotional_state": row["emotional_state"],
        "goals": list(row["goals"] or []),
        "conflicts": list(row["conflicts"] or []),
        "arc_progress": row["arc_progress"],
        "dialogue_style": row["dialogue_style"],
        "personality_traits": list(row["personality_traits"] or []),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _candidate(row: asyncpg.Record) -> dict:
    return {
        "candidate_id": str(row["candidate_id"]),
        "source_report_id": str(row["source_report_id"]),
        "scope": row["scope"],
        "trigger_conditions": _load_json(row["trigger_conditions"], {}),
        "proposed_action": row["proposed_action"],
        "evidence_refs": list(row["evidence_refs"] or []),
        "confidence": row["confidence"],
        "status": row["status"],
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


async def create_retrospective_report(pool: asyncpg.Pool, data: dict) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO hermes.novel_retrospective_reports (
            book_slug, batch_label, mode, start_chapter, end_chapter, scoring_version,
            diagnosis_json, llm_narrative, confidence, warnings, review_status
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9, $10, $11)
        RETURNING *
        """,
        data["book_slug"],
        data["batch_label"],
        data["mode"],
        data["start_chapter"],
        data["end_chapter"],
        data["scoring_version"],
        _json(data.get("diagnosis_json", {})),
        data.get("llm_narrative"),
        data["confidence"],
        data.get("warnings", []),
        data.get("review_status", "pending"),
    )
    return _report(row)


async def get_retrospective_report(pool: asyncpg.Pool, report_id: UUID) -> dict | None:
    row = await pool.fetchrow(
        "SELECT * FROM hermes.novel_retrospective_reports WHERE report_id = $1",
        report_id,
    )
    return _report(row) if row else None


async def list_retrospective_reports(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT * FROM hermes.novel_retrospective_reports
        WHERE book_slug = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
        """,
        book_slug,
        limit,
        offset,
    )
    return [_report(row) for row in rows]


async def update_retrospective_report_review_status(
    pool: asyncpg.Pool,
    report_id: UUID,
    review_status: str,
) -> dict | None:
    row = await pool.fetchrow(
        """
        UPDATE hermes.novel_retrospective_reports
        SET review_status = $2, updated_at = now()
        WHERE report_id = $1
        RETURNING *
        """,
        report_id,
        review_status,
    )
    return _report(row) if row else None


async def create_retrospective_alert(pool: asyncpg.Pool, data: dict) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO hermes.novel_retrospective_alerts (
            report_id, alert_type, severity, description, evidence_refs, suggested_action
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        UUID(data["report_id"]),
        data["alert_type"],
        data["severity"],
        data["description"],
        data.get("evidence_refs", []),
        data.get("suggested_action"),
    )
    return _alert(row)


async def list_retrospective_alerts(pool: asyncpg.Pool, report_id: UUID) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT * FROM hermes.novel_retrospective_alerts
        WHERE report_id = $1
        ORDER BY created_at
        """,
        report_id,
    )
    return [_alert(row) for row in rows]


async def create_correction_constraint(pool: asyncpg.Pool, data: dict) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO hermes.novel_correction_constraints (
            book_slug, source_report_id, alert_type, description, target_chapters,
            status, expires_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7::timestamptz)
        RETURNING *
        """,
        data["book_slug"],
        UUID(data["source_report_id"]),
        data["alert_type"],
        data["description"],
        data["target_chapters"],
        data.get("status", "pending"),
        data.get("expires_at"),
    )
    return _constraint(row)


async def get_correction_constraint(pool: asyncpg.Pool, constraint_id: UUID) -> dict | None:
    row = await pool.fetchrow(
        "SELECT * FROM hermes.novel_correction_constraints WHERE constraint_id = $1",
        constraint_id,
    )
    return _constraint(row) if row else None


async def list_correction_constraints(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = ["book_slug = $1"]
    params: list[object] = [book_slug]
    if status:
        params.append(status)
        conditions.append(f"status = ${len(params)}")
    params.extend([limit, offset])
    rows = await pool.fetch(
        f"""
        SELECT * FROM hermes.novel_correction_constraints
        WHERE {' AND '.join(conditions)}
        ORDER BY created_at DESC
        LIMIT ${len(params) - 1} OFFSET ${len(params)}
        """,
        *params,
    )
    return [_constraint(row) for row in rows]


async def update_correction_constraint_status(
    pool: asyncpg.Pool,
    constraint_id: UUID,
    status: str,
) -> dict | None:
    row = await pool.fetchrow(
        """
        UPDATE hermes.novel_correction_constraints
        SET status = $2, updated_at = now()
        WHERE constraint_id = $1
        RETURNING *
        """,
        constraint_id,
        status,
    )
    return _constraint(row) if row else None


async def create_handoff_package(pool: asyncpg.Pool, data: dict) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO hermes.novel_handoff_packages (
            book_slug, snapshot_chapter, context_version, progress_json,
            character_states_json, recent_changes, remaining_tasks,
            disabled_templates, stage_reminders
        )
        VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7, $8, $9)
        RETURNING *
        """,
        data["book_slug"],
        data["snapshot_chapter"],
        data["context_version"],
        _json(data.get("progress_json", {})),
        _json(data.get("character_states_json", [])),
        data.get("recent_changes", []),
        data.get("remaining_tasks", []),
        data.get("disabled_templates", []),
        data.get("stage_reminders", []),
    )
    return _handoff(row)


async def get_handoff_package(pool: asyncpg.Pool, package_id: UUID) -> dict | None:
    row = await pool.fetchrow(
        "SELECT * FROM hermes.novel_handoff_packages WHERE package_id = $1",
        package_id,
    )
    return _handoff(row) if row else None


async def get_latest_handoff_package(pool: asyncpg.Pool, book_slug: str) -> dict | None:
    row = await pool.fetchrow(
        """
        SELECT * FROM hermes.novel_handoff_packages
        WHERE book_slug = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        book_slug,
    )
    return _handoff(row) if row else None


async def upsert_character_state(pool: asyncpg.Pool, data: dict) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO hermes.novel_character_states (
            book_slug, character_name, last_chapter, location, relationships_json,
            emotional_state, goals, conflicts, arc_progress, dialogue_style,
            personality_traits
        )
        VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (book_slug, character_name, last_chapter)
        DO UPDATE SET
            location = EXCLUDED.location,
            relationships_json = EXCLUDED.relationships_json,
            emotional_state = EXCLUDED.emotional_state,
            goals = EXCLUDED.goals,
            conflicts = EXCLUDED.conflicts,
            arc_progress = EXCLUDED.arc_progress,
            dialogue_style = EXCLUDED.dialogue_style,
            personality_traits = EXCLUDED.personality_traits,
            updated_at = now()
        RETURNING *
        """,
        data["book_slug"],
        data["character_name"],
        data["last_chapter"],
        data["location"],
        _json(data.get("relationships_json", {})),
        data["emotional_state"],
        data.get("goals", []),
        data.get("conflicts", []),
        data["arc_progress"],
        data["dialogue_style"],
        data.get("personality_traits", []),
    )
    return _character_state(row)


async def get_character_state(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    character_name: str,
    last_chapter: int,
) -> dict | None:
    row = await pool.fetchrow(
        """
        SELECT * FROM hermes.novel_character_states
        WHERE book_slug = $1 AND character_name = $2 AND last_chapter = $3
        """,
        book_slug,
        character_name,
        last_chapter,
    )
    return _character_state(row) if row else None


async def list_character_states(
    pool: asyncpg.Pool,
    *,
    book_slug: str,
    character_name: str | None = None,
    last_chapter: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = ["book_slug = $1"]
    params: list[object] = [book_slug]
    if character_name:
        params.append(character_name)
        conditions.append(f"character_name = ${len(params)}")
    if last_chapter:
        params.append(last_chapter)
        conditions.append(f"last_chapter = ${len(params)}")
    params.extend([limit, offset])
    rows = await pool.fetch(
        f"""
        SELECT * FROM hermes.novel_character_states
        WHERE {' AND '.join(conditions)}
        ORDER BY last_chapter DESC, updated_at DESC
        LIMIT ${len(params) - 1} OFFSET ${len(params)}
        """,
        *params,
    )
    return [_character_state(row) for row in rows]


async def create_learning_candidate(pool: asyncpg.Pool, data: dict) -> dict:
    row = await pool.fetchrow(
        """
        INSERT INTO hermes.novel_learning_candidates (
            source_report_id, scope, trigger_conditions, proposed_action,
            evidence_refs, confidence, status
        )
        VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7)
        RETURNING *
        """,
        UUID(data["source_report_id"]),
        data["scope"],
        _json(data.get("trigger_conditions", {})),
        data["proposed_action"],
        data.get("evidence_refs", []),
        data["confidence"],
        data.get("status", "pending"),
    )
    return _candidate(row)


async def list_learning_candidates(pool: asyncpg.Pool, source_report_id: UUID) -> list[dict]:
    rows = await pool.fetch(
        """
        SELECT * FROM hermes.novel_learning_candidates
        WHERE source_report_id = $1
        ORDER BY created_at DESC
        """,
        source_report_id,
    )
    return [_candidate(row) for row in rows]
