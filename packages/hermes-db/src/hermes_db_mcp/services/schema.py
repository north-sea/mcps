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


async def inspect_wechat_analytics_ingestion_schema(pool: asyncpg.Pool) -> dict[str, bool]:
    import_columns = await _fetch_column_names(pool, "hermes", "analytics_import_runs")
    snapshot_columns = await _fetch_column_names(pool, "hermes", "wechat_article_metric_snapshots")
    channel_columns = await _fetch_column_names(
        pool,
        "hermes",
        "wechat_article_channel_daily_metrics",
    )
    import_constraints = await _fetch_constraint_names(
        pool,
        (
            "analytics_import_runs_pkey",
            "chk_analytics_import_runs_status",
            "chk_analytics_import_runs_counts_nonnegative",
        ),
        table_name="analytics_import_runs",
    )
    snapshot_constraints = await _fetch_constraint_names(
        pool,
        (
            "wechat_article_metric_snapshots_pkey",
            "wechat_article_metric_snapshots_article_id_fkey",
            "wechat_article_metric_snapshots_import_run_id_fkey",
            "uq_wechat_article_metric_snapshot_identity",
            "chk_wechat_article_metric_snapshot_counts_nonnegative",
            "chk_wechat_article_metric_snapshot_completion_rate",
        ),
        table_name="wechat_article_metric_snapshots",
    )
    channel_constraints = await _fetch_constraint_names(
        pool,
        (
            "wechat_article_channel_daily_metrics_pkey",
            "wechat_article_channel_daily_metrics_article_id_fkey",
            "wechat_article_channel_daily_metrics_import_run_id_fkey",
            "uq_wechat_article_channel_daily_identity",
            "chk_wechat_article_channel_daily_counts_nonnegative",
        ),
        table_name="wechat_article_channel_daily_metrics",
    )
    indexes = await _fetch_index_names(
        pool,
        "hermes",
        (
            "idx_analytics_import_runs_account_created",
            "idx_analytics_import_runs_source_created",
            "idx_analytics_import_runs_status_created",
            "idx_wechat_article_metric_snapshots_account_stat",
            "idx_wechat_article_metric_snapshots_article_stat",
            "idx_wechat_article_metric_snapshots_window_stat",
            "idx_wechat_article_metric_snapshots_source_stat",
            "idx_wechat_article_metric_snapshots_import_run",
            "idx_wechat_article_channel_daily_account_date",
            "idx_wechat_article_channel_daily_article_date",
            "idx_wechat_article_channel_daily_channel_date",
            "idx_wechat_article_channel_daily_import_run",
        ),
    )

    import_required = {
        "import_run_id",
        "account",
        "source",
        "status",
        "total_rows",
        "created",
        "updated",
        "skipped",
        "unmatched",
        "errors",
        "metadata",
        "created_at",
        "updated_at",
    }
    snapshot_required = {
        "snapshot_id",
        "article_id",
        "account",
        "stat_date",
        "window_label",
        "source",
        "read_user_count",
        "average_stay_seconds",
        "completion_rate",
        "new_follow_user_count",
        "share_user_count",
        "wow_user_count",
        "like_user_count",
        "favorite_user_count",
        "reward_cents",
        "comment_count",
        "delivered_user_count",
        "account_message_read_user_count",
        "first_share_user_count",
        "total_share_user_count",
        "share_generated_read_user_count",
        "missing_fields",
        "raw_json",
        "import_run_id",
        "collected_at",
        "created_at",
        "updated_at",
    }
    channel_required = {
        "metric_id",
        "article_id",
        "account",
        "metric_date",
        "channel",
        "source",
        "read_user_count",
        "share_user_count",
        "raw_json",
        "import_run_id",
        "created_at",
        "updated_at",
    }

    return {
        "wechat_analytics_ingestion": import_required.issubset(import_columns)
        and snapshot_required.issubset(snapshot_columns)
        and channel_required.issubset(channel_columns)
        and {
            "chk_analytics_import_runs_status",
            "chk_analytics_import_runs_counts_nonnegative",
        }.issubset(import_constraints)
        and {
            "wechat_article_metric_snapshots_article_id_fkey",
            "wechat_article_metric_snapshots_import_run_id_fkey",
            "uq_wechat_article_metric_snapshot_identity",
            "chk_wechat_article_metric_snapshot_counts_nonnegative",
            "chk_wechat_article_metric_snapshot_completion_rate",
        }.issubset(snapshot_constraints)
        and {
            "wechat_article_channel_daily_metrics_article_id_fkey",
            "wechat_article_channel_daily_metrics_import_run_id_fkey",
            "uq_wechat_article_channel_daily_identity",
            "chk_wechat_article_channel_daily_counts_nonnegative",
        }.issubset(channel_constraints)
        and {
            "idx_analytics_import_runs_account_created",
            "idx_analytics_import_runs_source_created",
            "idx_analytics_import_runs_status_created",
            "idx_wechat_article_metric_snapshots_account_stat",
            "idx_wechat_article_metric_snapshots_article_stat",
            "idx_wechat_article_metric_snapshots_window_stat",
            "idx_wechat_article_metric_snapshots_source_stat",
            "idx_wechat_article_metric_snapshots_import_run",
            "idx_wechat_article_channel_daily_account_date",
            "idx_wechat_article_channel_daily_article_date",
            "idx_wechat_article_channel_daily_channel_date",
            "idx_wechat_article_channel_daily_import_run",
        }.issubset(indexes),
    }
