"""add wechat analytics ingestion

Revision ID: 0004_wechat_analytics_ingestion
Revises: 0003_wechat_publication_ledger
Create Date: 2026-06-06
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0004_wechat_analytics_ingestion"
down_revision: Union[str, None] = "0003_wechat_publication_ledger"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.analytics_import_runs (
            import_run_id UUID PRIMARY KEY,
            account TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            total_rows INTEGER NOT NULL DEFAULT 0,
            created INTEGER NOT NULL DEFAULT 0,
            updated INTEGER NOT NULL DEFAULT 0,
            skipped INTEGER NOT NULL DEFAULT 0,
            unmatched JSONB NOT NULL DEFAULT '[]'::jsonb,
            errors JSONB NOT NULL DEFAULT '[]'::jsonb,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_analytics_import_runs_status
                CHECK (status IN (
                    'completed',
                    'completed_with_errors',
                    'failed'
                )),
            CONSTRAINT chk_analytics_import_runs_counts_nonnegative
                CHECK (
                    total_rows >= 0
                    AND created >= 0
                    AND updated >= 0
                    AND skipped >= 0
                )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_analytics_import_runs_account_created
        ON hermes.analytics_import_runs(account, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_analytics_import_runs_source_created
        ON hermes.analytics_import_runs(source, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_analytics_import_runs_status_created
        ON hermes.analytics_import_runs(status, created_at DESC)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.wechat_article_metric_snapshots (
            snapshot_id UUID PRIMARY KEY,
            article_id UUID NOT NULL REFERENCES hermes.wechat_articles(article_id) ON DELETE CASCADE,
            account TEXT NOT NULL,
            stat_date DATE NOT NULL,
            window_label TEXT NOT NULL,
            source TEXT NOT NULL,
            read_user_count INTEGER,
            average_stay_seconds DOUBLE PRECISION,
            completion_rate DOUBLE PRECISION,
            new_follow_user_count INTEGER,
            share_user_count INTEGER,
            wow_user_count INTEGER,
            like_user_count INTEGER,
            favorite_user_count INTEGER,
            reward_cents INTEGER,
            comment_count INTEGER,
            delivered_user_count INTEGER,
            account_message_read_user_count INTEGER,
            first_share_user_count INTEGER,
            total_share_user_count INTEGER,
            share_generated_read_user_count INTEGER,
            missing_fields TEXT[] NOT NULL DEFAULT ARRAY[]::text[],
            raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            import_run_id UUID REFERENCES hermes.analytics_import_runs(import_run_id) ON DELETE SET NULL,
            collected_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_wechat_article_metric_snapshot_identity
                UNIQUE (article_id, stat_date, window_label, source),
            CONSTRAINT chk_wechat_article_metric_snapshot_counts_nonnegative
                CHECK (
                    (read_user_count IS NULL OR read_user_count >= 0)
                    AND (average_stay_seconds IS NULL OR average_stay_seconds >= 0)
                    AND (new_follow_user_count IS NULL OR new_follow_user_count >= 0)
                    AND (share_user_count IS NULL OR share_user_count >= 0)
                    AND (wow_user_count IS NULL OR wow_user_count >= 0)
                    AND (like_user_count IS NULL OR like_user_count >= 0)
                    AND (favorite_user_count IS NULL OR favorite_user_count >= 0)
                    AND (reward_cents IS NULL OR reward_cents >= 0)
                    AND (comment_count IS NULL OR comment_count >= 0)
                    AND (delivered_user_count IS NULL OR delivered_user_count >= 0)
                    AND (
                        account_message_read_user_count IS NULL
                        OR account_message_read_user_count >= 0
                    )
                    AND (first_share_user_count IS NULL OR first_share_user_count >= 0)
                    AND (total_share_user_count IS NULL OR total_share_user_count >= 0)
                    AND (
                        share_generated_read_user_count IS NULL
                        OR share_generated_read_user_count >= 0
                    )
                ),
            CONSTRAINT chk_wechat_article_metric_snapshot_completion_rate
                CHECK (
                    completion_rate IS NULL
                    OR (completion_rate >= 0 AND completion_rate <= 1)
                )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_metric_snapshots_account_stat
        ON hermes.wechat_article_metric_snapshots(account, stat_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_metric_snapshots_article_stat
        ON hermes.wechat_article_metric_snapshots(article_id, stat_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_metric_snapshots_window_stat
        ON hermes.wechat_article_metric_snapshots(window_label, stat_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_metric_snapshots_source_stat
        ON hermes.wechat_article_metric_snapshots(source, stat_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_metric_snapshots_import_run
        ON hermes.wechat_article_metric_snapshots(import_run_id)
        WHERE import_run_id IS NOT NULL
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.wechat_article_channel_daily_metrics (
            metric_id UUID PRIMARY KEY,
            article_id UUID NOT NULL REFERENCES hermes.wechat_articles(article_id) ON DELETE CASCADE,
            account TEXT NOT NULL,
            metric_date DATE NOT NULL,
            channel TEXT NOT NULL,
            source TEXT NOT NULL,
            read_user_count INTEGER,
            share_user_count INTEGER,
            raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            import_run_id UUID REFERENCES hermes.analytics_import_runs(import_run_id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_wechat_article_channel_daily_identity
                UNIQUE (article_id, metric_date, channel, source),
            CONSTRAINT chk_wechat_article_channel_daily_counts_nonnegative
                CHECK (
                    (read_user_count IS NULL OR read_user_count >= 0)
                    AND (share_user_count IS NULL OR share_user_count >= 0)
                )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_channel_daily_account_date
        ON hermes.wechat_article_channel_daily_metrics(account, metric_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_channel_daily_article_date
        ON hermes.wechat_article_channel_daily_metrics(article_id, metric_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_channel_daily_channel_date
        ON hermes.wechat_article_channel_daily_metrics(channel, metric_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_channel_daily_import_run
        ON hermes.wechat_article_channel_daily_metrics(import_run_id)
        WHERE import_run_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_channel_daily_import_run")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_channel_daily_channel_date")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_channel_daily_article_date")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_channel_daily_account_date")
    op.execute("DROP TABLE IF EXISTS hermes.wechat_article_channel_daily_metrics")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_metric_snapshots_import_run")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_metric_snapshots_source_stat")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_metric_snapshots_window_stat")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_metric_snapshots_article_stat")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_metric_snapshots_account_stat")
    op.execute("DROP TABLE IF EXISTS hermes.wechat_article_metric_snapshots")
    op.execute("DROP INDEX IF EXISTS hermes.idx_analytics_import_runs_status_created")
    op.execute("DROP INDEX IF EXISTS hermes.idx_analytics_import_runs_source_created")
    op.execute("DROP INDEX IF EXISTS hermes.idx_analytics_import_runs_account_created")
    op.execute("DROP TABLE IF EXISTS hermes.analytics_import_runs")
