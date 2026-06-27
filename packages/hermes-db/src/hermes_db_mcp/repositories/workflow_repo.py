from __future__ import annotations

from datetime import datetime
import json
from uuid import UUID, uuid4

import asyncpg


RUN_COLUMNS = """
    run_id, task_id, topic_id, account, input_text, intent, phase,
    current_stage, status, dry_run, summary, failure_reason, missing_inputs,
    next_action, metadata, started_at, completed_at, created_at, updated_at
"""

ARTIFACT_SUMMARY_COLUMNS = """
    artifact_id, run_id, task_id, topic_id, account, stage, type, name,
    version, parent_artifact_id, content_hash, content_size_bytes,
    content_preview, content_ref, metadata, created_at, updated_at
"""


def _row(row: asyncpg.Record | None) -> dict | None:
    return dict(row) if row else None


def _jsonb(value) -> str:
    return json.dumps(value, ensure_ascii=False)


class ArtifactIdConflictError(ValueError):
    def __init__(self, *, existing_content_hash: str, provided_content_hash: str):
        super().__init__("artifact_id_conflict")
        self.existing_content_hash = existing_content_hash
        self.provided_content_hash = provided_content_hash


async def upsert_run(
    pool: asyncpg.Pool,
    *,
    run_id: str,
    task_id: str | None = None,
    topic_id: UUID | None = None,
    account: str | None = None,
    input_text: str | None = None,
    intent: str | None = None,
    phase: str,
    current_stage: str | None = None,
    status: str,
    dry_run: bool = False,
    metadata: dict | None = None,
    started_at: datetime | None = None,
) -> dict:
    sql = f"""
        INSERT INTO hermes.wechat_workflow_runs (
            run_id, task_id, topic_id, account, input_text, intent, phase,
            current_stage, status, dry_run, metadata, started_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (run_id) DO UPDATE SET
            task_id = EXCLUDED.task_id,
            topic_id = EXCLUDED.topic_id,
            account = EXCLUDED.account,
            input_text = EXCLUDED.input_text,
            intent = EXCLUDED.intent,
            phase = EXCLUDED.phase,
            current_stage = EXCLUDED.current_stage,
            status = EXCLUDED.status,
            dry_run = EXCLUDED.dry_run,
            metadata = EXCLUDED.metadata,
            started_at = COALESCE(hermes.wechat_workflow_runs.started_at, EXCLUDED.started_at),
            updated_at = now()
        RETURNING {RUN_COLUMNS}, (xmax = 0) AS created
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            sql,
            run_id,
            task_id,
            topic_id,
            account,
            input_text,
            intent,
            phase,
            current_stage,
            status,
            dry_run,
            _jsonb(metadata or {}),
            started_at,
        )
    return dict(row)


async def finish_run(
    pool: asyncpg.Pool,
    *,
    run_id: str,
    phase: str,
    status: str,
    current_stage: str | None = None,
    summary: str | None = None,
    failure_reason: str | None = None,
    missing_inputs: list | None = None,
    next_action: str | None = None,
    completed_at: datetime | None = None,
) -> dict | None:
    sql = f"""
        UPDATE hermes.wechat_workflow_runs
        SET phase = $2,
            current_stage = $3,
            status = $4,
            summary = $5,
            failure_reason = $6,
            missing_inputs = $7,
            next_action = $8,
            completed_at = $9,
            updated_at = now()
        WHERE run_id = $1
        RETURNING {RUN_COLUMNS}
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            sql,
            run_id,
            phase,
            current_stage,
            status,
            summary,
            failure_reason,
            _jsonb(missing_inputs or []),
            next_action,
            completed_at,
        )
    return _row(row)


async def upsert_artifact(
    pool: asyncpg.Pool,
    *,
    run_id: str,
    stage: str,
    type: str,
    name: str,
    content_hash: str,
    content_size_bytes: int,
    artifact_id: str | None = None,
    task_id: str | None = None,
    topic_id: UUID | None = None,
    account: str | None = None,
    parent_artifact_id: str | None = None,
    content_preview: str | None = None,
    content_text: str | None = None,
    content_ref: str | None = None,
    metadata: dict | None = None,
) -> tuple[dict, bool, dict]:
    artifact_id = artifact_id or str(uuid4())
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtext($1))",
                f"{run_id}:{stage}:{name}",
            )
            existing_by_id = await conn.fetchrow(
                """
                SELECT artifact_id, content_hash
                FROM hermes.workflow_artifacts
                WHERE artifact_id = $1
                """,
                artifact_id,
            )
            if existing_by_id and existing_by_id["content_hash"] != content_hash:
                raise ArtifactIdConflictError(
                    existing_content_hash=existing_by_id["content_hash"],
                    provided_content_hash=content_hash,
                )
            if existing_by_id:
                row = await conn.fetchrow(
                    f"SELECT {ARTIFACT_SUMMARY_COLUMNS} FROM hermes.workflow_artifacts WHERE artifact_id = $1",
                    artifact_id,
                )
                return dict(row), False, {
                    "idempotency_hit": True,
                    "skipped_update_reason": "artifact_id_content_hash_match",
                    "existing_content_hash": existing_by_id["content_hash"],
                    "provided_content_hash": content_hash,
                }

            existing_by_hash = await conn.fetchrow(
                f"""
                SELECT {ARTIFACT_SUMMARY_COLUMNS}
                FROM hermes.workflow_artifacts
                WHERE run_id = $1 AND stage = $2 AND name = $3 AND content_hash = $4
                """,
                run_id,
                stage,
                name,
                content_hash,
            )
            if existing_by_hash:
                return dict(existing_by_hash), False, {
                    "idempotency_hit": True,
                    "skipped_update_reason": "run_stage_name_content_hash_match",
                    "existing_content_hash": existing_by_hash["content_hash"],
                    "provided_content_hash": content_hash,
                }

            version = await conn.fetchval(
                """
                SELECT COALESCE(max(version), 0) + 1
                FROM hermes.workflow_artifacts
                WHERE run_id = $1 AND stage = $2 AND name = $3
                """,
                run_id,
                stage,
                name,
            )
            row = await conn.fetchrow(
                f"""
                INSERT INTO hermes.workflow_artifacts (
                    artifact_id, run_id, task_id, topic_id, account, stage, type, name,
                    version, parent_artifact_id, content_hash, content_size_bytes,
                    content_preview, content_text, content_ref, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING {ARTIFACT_SUMMARY_COLUMNS}
                """,
                artifact_id,
                run_id,
                task_id,
                topic_id,
                account,
                stage,
                type,
                name,
                version,
                parent_artifact_id,
                content_hash,
                content_size_bytes,
                content_preview,
                content_text,
                content_ref,
                _jsonb(metadata or {}),
            )
    return dict(row), True, {
        "idempotency_hit": False,
        "provided_content_hash": content_hash,
    }


async def list_artifacts(
    pool: asyncpg.Pool,
    *,
    run_id: str | None = None,
    topic_id: UUID | None = None,
    account: str | None = None,
    type: str | None = None,
    stage: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = []
    params: list = []
    idx = 1
    for column, value in (
        ("run_id", run_id),
        ("topic_id", topic_id),
        ("account", account),
        ("type", type),
        ("stage", stage),
    ):
        if value is not None:
            conditions.append(f"{column} = ${idx}")
            params.append(value)
            idx += 1
    if date_from is not None:
        conditions.append(f"created_at >= ${idx}")
        params.append(date_from)
        idx += 1
    if date_to is not None:
        conditions.append(f"created_at <= ${idx}")
        params.append(date_to)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"""
        SELECT {ARTIFACT_SUMMARY_COLUMNS}
        FROM hermes.workflow_artifacts
        {where}
        ORDER BY created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *(params + [limit, offset]))
    return [dict(row) for row in rows]


async def get_artifact(pool: asyncpg.Pool, *, artifact_id: str) -> dict | None:
    sql = f"""
        SELECT {ARTIFACT_SUMMARY_COLUMNS}, content_text
        FROM hermes.workflow_artifacts
        WHERE artifact_id = $1
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, artifact_id)
    return _row(row)


async def list_artifact_versions(
    pool: asyncpg.Pool,
    *,
    artifact_id: str | None = None,
    run_id: str | None = None,
    stage: str | None = None,
    name: str | None = None,
    order: str = "asc",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], dict | None]:
    selector = await resolve_artifact_family(
        pool,
        artifact_id=artifact_id,
        run_id=run_id,
        stage=stage,
        name=name,
    )
    if selector is None:
        return [], None

    direction = "DESC" if order == "desc" else "ASC"
    sql = f"""
        SELECT {ARTIFACT_SUMMARY_COLUMNS}
        FROM hermes.workflow_artifacts
        WHERE run_id = $1 AND stage = $2 AND name = $3
        ORDER BY version {direction}, created_at {direction}
        LIMIT $4 OFFSET $5
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            sql,
            selector["run_id"],
            selector["stage"],
            selector["name"],
            limit,
            offset,
        )
    return [dict(row) for row in rows], selector


async def get_latest_artifact_version(
    pool: asyncpg.Pool,
    *,
    artifact_id: str | None = None,
    run_id: str | None = None,
    stage: str | None = None,
    name: str | None = None,
) -> tuple[dict | None, dict | None]:
    versions, selector = await list_artifact_versions(
        pool,
        artifact_id=artifact_id,
        run_id=run_id,
        stage=stage,
        name=name,
        order="desc",
        limit=1,
        offset=0,
    )
    return (versions[0] if versions else None), selector


async def resolve_artifact_family(
    pool: asyncpg.Pool,
    *,
    artifact_id: str | None = None,
    run_id: str | None = None,
    stage: str | None = None,
    name: str | None = None,
) -> dict | None:
    if artifact_id:
        artifact = await get_artifact(pool, artifact_id=artifact_id)
        if artifact is None:
            return None
        return {
            "artifact_id": artifact["artifact_id"],
            "run_id": artifact["run_id"],
            "stage": artifact["stage"],
            "name": artifact["name"],
        }

    if run_id and stage and name:
        return {
            "artifact_id": None,
            "run_id": run_id,
            "stage": stage,
            "name": name,
        }

    return None
