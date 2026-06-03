from __future__ import annotations

from collections.abc import Iterable

import asyncpg


async def _fetch_column_names(pool: asyncpg.Pool, table_schema: str, table_name: str) -> set[str]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = $1 AND table_name = $2
            """,
            table_schema,
            table_name,
        )
    return {row["column_name"] for row in rows}


async def _fetch_constraint_names(
    pool: asyncpg.Pool,
    constraint_names: Iterable[str],
    table_schema: str = "hermes",
    table_name: str = "topics",
) -> set[str]:
    wanted = list(constraint_names)
    if not wanted:
        return set()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT conname
            FROM pg_constraint
            WHERE connamespace = $1::regnamespace
              AND conrelid = $2::regclass
              AND conname = ANY($3::text[])
            """,
            table_schema,
            f"{table_schema}.{table_name}",
            wanted,
        )
    return {row["conname"] for row in rows}


async def inspect_topic_schema(pool: asyncpg.Pool) -> dict[str, bool]:
    columns = await _fetch_column_names(pool, "hermes", "topics")
    constraints = await _fetch_constraint_names(
        pool,
        (
            "fk_topics_revisit_of",
            "chk_topics_revisit_of_not_self",
        ),
    )

    return {
        "topic_bucket": "embedding" in columns,
        "topic_revisit_of": {"revisit_of", "mother_theme"}.issubset(columns)
        and "fk_topics_revisit_of" in constraints
        and "chk_topics_revisit_of_not_self" in constraints,
        "list_revisit_chain": "revisit_of" in columns,
    }


async def _fetch_index_names(
    pool: asyncpg.Pool,
    table_schema: str,
    index_names: Iterable[str],
) -> set[str]:
    wanted = list(index_names)
    if not wanted:
        return set()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = $1
              AND indexname = ANY($2::text[])
            """,
            table_schema,
            wanted,
        )
    return {row["indexname"] for row in rows}


async def inspect_workflow_schema(pool: asyncpg.Pool) -> dict[str, bool]:
    run_columns = await _fetch_column_names(pool, "hermes", "wechat_workflow_runs")
    artifact_columns = await _fetch_column_names(pool, "hermes", "workflow_artifacts")
    artifact_constraints = await _fetch_constraint_names(
        pool,
        (
            "workflow_artifacts_pkey",
            "workflow_artifacts_run_id_fkey",
            "workflow_artifacts_parent_artifact_id_fkey",
            "chk_workflow_artifacts_content_present",
            "chk_workflow_artifacts_version_positive",
            "chk_workflow_artifacts_content_size_nonnegative",
            "uq_workflow_artifact_logical_version",
            "uq_workflow_artifact_logical_hash",
        ),
        table_name="workflow_artifacts",
    )
    indexes = await _fetch_index_names(
        pool,
        "hermes",
        (
            "idx_wechat_workflow_runs_topic_created",
            "idx_wechat_workflow_runs_account_created",
            "idx_workflow_artifacts_run_created",
            "idx_workflow_artifacts_topic_created",
            "idx_workflow_artifacts_account_created",
            "idx_workflow_artifacts_type_created",
            "idx_workflow_artifacts_stage_name",
        ),
    )

    run_required = {
        "run_id",
        "task_id",
        "topic_id",
        "account",
        "phase",
        "current_stage",
        "status",
        "dry_run",
        "metadata",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    }
    artifact_required = {
        "artifact_id",
        "run_id",
        "stage",
        "type",
        "name",
        "version",
        "parent_artifact_id",
        "content_hash",
        "content_size_bytes",
        "content_preview",
        "content_text",
        "content_ref",
        "metadata",
        "created_at",
        "updated_at",
    }

    return {
        "workflow_runs": run_required.issubset(run_columns),
        "workflow_artifacts": artifact_required.issubset(artifact_columns)
        and {
            "workflow_artifacts_run_id_fkey",
            "workflow_artifacts_parent_artifact_id_fkey",
            "chk_workflow_artifacts_content_present",
            "chk_workflow_artifacts_version_positive",
            "chk_workflow_artifacts_content_size_nonnegative",
            "uq_workflow_artifact_logical_version",
            "uq_workflow_artifact_logical_hash",
        }.issubset(artifact_constraints)
        and {
            "idx_workflow_artifacts_run_created",
            "idx_workflow_artifacts_topic_created",
            "idx_workflow_artifacts_account_created",
            "idx_workflow_artifacts_type_created",
            "idx_workflow_artifacts_stage_name",
        }.issubset(indexes),
    }


async def inspect_wechat_publication_ledger_schema(pool: asyncpg.Pool) -> dict[str, bool]:
    article_columns = await _fetch_column_names(pool, "hermes", "wechat_articles")
    ref_columns = await _fetch_column_names(pool, "hermes", "wechat_article_external_refs")
    article_constraints = await _fetch_constraint_names(
        pool,
        (
            "wechat_articles_pkey",
            "uq_wechat_articles_account_idempotency",
            "chk_wechat_articles_status",
            "chk_wechat_articles_reference_for_published",
        ),
        table_name="wechat_articles",
    )
    ref_constraints = await _fetch_constraint_names(
        pool,
        (
            "wechat_article_external_refs_pkey",
            "chk_wechat_article_external_refs_type",
            "chk_wechat_article_external_refs_value_nonempty",
        ),
        table_name="wechat_article_external_refs",
    )
    indexes = await _fetch_index_names(
        pool,
        "hermes",
        (
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
        ),
    )

    article_required = {
        "article_id",
        "publication_idempotency_key",
        "account",
        "topic_id",
        "run_id",
        "task_id",
        "draft_artifact_id",
        "published_artifact_id",
        "publish_artifact_id",
        "status",
        "dry_run",
        "title",
        "published_url",
        "canonical_url",
        "publish_target",
        "external_reference",
        "metadata",
        "published_at",
        "created_at",
        "updated_at",
    }
    ref_required = {
        "ref_id",
        "article_id",
        "ref_type",
        "ref_value",
        "ref_source",
        "is_primary",
        "metadata",
        "superseded_at",
        "created_at",
        "updated_at",
    }

    return {
        "wechat_publication_ledger": article_required.issubset(article_columns)
        and ref_required.issubset(ref_columns)
        and {
            "uq_wechat_articles_account_idempotency",
            "chk_wechat_articles_status",
            "chk_wechat_articles_reference_for_published",
        }.issubset(article_constraints)
        and {
            "chk_wechat_article_external_refs_type",
            "chk_wechat_article_external_refs_value_nonempty",
        }.issubset(ref_constraints)
        and {
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
        }.issubset(indexes),
    }
