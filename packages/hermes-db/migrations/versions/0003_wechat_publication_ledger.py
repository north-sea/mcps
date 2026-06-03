"""add wechat publication ledger

Revision ID: 0003_wechat_publication_ledger
Revises: 0002_wechat_workflow_artifacts
Create Date: 2026-06-03
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0003_wechat_publication_ledger"
down_revision: Union[str, None] = "0002_wechat_workflow_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.wechat_articles (
            article_id UUID PRIMARY KEY,
            publication_idempotency_key TEXT NOT NULL,
            account TEXT NOT NULL,
            topic_id UUID REFERENCES hermes.topics(id) ON DELETE SET NULL,
            run_id TEXT NOT NULL REFERENCES hermes.wechat_workflow_runs(run_id),
            task_id TEXT,
            draft_artifact_id TEXT REFERENCES hermes.workflow_artifacts(artifact_id),
            published_artifact_id TEXT REFERENCES hermes.workflow_artifacts(artifact_id),
            publish_artifact_id TEXT REFERENCES hermes.workflow_artifacts(artifact_id),
            status TEXT NOT NULL,
            dry_run BOOLEAN NOT NULL DEFAULT false,
            title TEXT,
            published_url TEXT,
            canonical_url TEXT,
            publish_target TEXT,
            external_reference TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            published_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_wechat_articles_account_idempotency
                UNIQUE (account, publication_idempotency_key),
            CONSTRAINT chk_wechat_articles_status
                CHECK (status IN (
                    'drafted',
                    'published',
                    'published_missing_url',
                    'publish_reference_missing',
                    'archived'
                )),
            CONSTRAINT chk_wechat_articles_reference_for_published
                CHECK (
                    status <> 'published'
                    OR published_url IS NOT NULL
                    OR canonical_url IS NOT NULL
                    OR external_reference IS NOT NULL
                )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_articles_account_created
        ON hermes.wechat_articles(account, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_articles_account_status_created
        ON hermes.wechat_articles(account, status, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_articles_topic_created
        ON hermes.wechat_articles(topic_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_articles_run_id
        ON hermes.wechat_articles(run_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_articles_task_id
        ON hermes.wechat_articles(task_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_articles_published_url
        ON hermes.wechat_articles(published_url)
        WHERE published_url IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_articles_canonical_url
        ON hermes.wechat_articles(canonical_url)
        WHERE canonical_url IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_articles_publish_target_created
        ON hermes.wechat_articles(publish_target, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_articles_published_at
        ON hermes.wechat_articles(published_at DESC)
        WHERE published_at IS NOT NULL
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.wechat_article_external_refs (
            ref_id UUID PRIMARY KEY,
            article_id UUID NOT NULL REFERENCES hermes.wechat_articles(article_id) ON DELETE CASCADE,
            ref_type TEXT NOT NULL,
            ref_value TEXT NOT NULL,
            ref_source TEXT,
            is_primary BOOLEAN NOT NULL DEFAULT false,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            superseded_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_wechat_article_external_refs_type
                CHECK (ref_type IN (
                    'published_url',
                    'canonical_url',
                    'wechat_msg_id',
                    'wechat_biz_mid_idx_sn',
                    'youmind_ref',
                    'publish_target_ref',
                    'manual_repair',
                    'external_reference'
                )),
            CONSTRAINT chk_wechat_article_external_refs_value_nonempty
                CHECK (length(trim(ref_value)) > 0)
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_wechat_article_external_ref_active
        ON hermes.wechat_article_external_refs(ref_type, ref_value)
        WHERE superseded_at IS NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_wechat_article_external_ref_article_active
        ON hermes.wechat_article_external_refs(article_id, ref_type, ref_value)
        WHERE superseded_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_refs_article_created
        ON hermes.wechat_article_external_refs(article_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_refs_type_value_active
        ON hermes.wechat_article_external_refs(ref_type, ref_value)
        WHERE superseded_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_article_refs_primary
        ON hermes.wechat_article_external_refs(article_id, ref_type, is_primary)
        WHERE superseded_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_refs_primary")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_refs_type_value_active")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_article_refs_article_created")
    op.execute("DROP INDEX IF EXISTS hermes.uq_wechat_article_external_ref_article_active")
    op.execute("DROP INDEX IF EXISTS hermes.uq_wechat_article_external_ref_active")
    op.execute("DROP TABLE IF EXISTS hermes.wechat_article_external_refs")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_articles_published_at")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_articles_publish_target_created")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_articles_canonical_url")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_articles_published_url")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_articles_task_id")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_articles_run_id")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_articles_topic_created")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_articles_account_status_created")
    op.execute("DROP INDEX IF EXISTS hermes.idx_wechat_articles_account_created")
    op.execute("DROP TABLE IF EXISTS hermes.wechat_articles")
