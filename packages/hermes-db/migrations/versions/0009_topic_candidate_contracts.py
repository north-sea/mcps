"""add topic candidate contracts

Revision ID: 0009_topic_candidates
Revises: 0008_novel_planning
Create Date: 2026-06-29
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0009_topic_candidates"
down_revision: Union[str, None] = "0008_novel_planning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.topic_candidate_accounts (
            account_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT true,
            draft_target TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_candidate_accounts_enabled
        ON hermes.topic_candidate_accounts(enabled)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.topic_candidate_tracks (
            track_id TEXT NOT NULL,
            account_id TEXT NOT NULL REFERENCES hermes.topic_candidate_accounts(account_id),
            name TEXT NOT NULL,
            keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
            negative_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
            sources JSONB NOT NULL DEFAULT '[]'::jsonb,
            scoring_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
            daily_quota INTEGER,
            enabled BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (account_id, track_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_candidate_tracks_enabled
        ON hermes.topic_candidate_tracks(account_id, enabled)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.topic_candidates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id TEXT NOT NULL,
            track_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT,
            source_item_id TEXT,
            title TEXT NOT NULL,
            summary TEXT,
            hot_score NUMERIC,
            fit_score NUMERIC,
            novelty_score NUMERIC,
            status TEXT NOT NULL DEFAULT 'new',
            dedupe_key TEXT NOT NULL,
            captured_at TIMESTAMPTZ NOT NULL,
            raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            topic_id UUID REFERENCES hermes.topics(id),
            rejection_reason TEXT,
            adopted_at TIMESTAMPTZ,
            status_updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fk_topic_candidates_track
                FOREIGN KEY (account_id, track_id)
                REFERENCES hermes.topic_candidate_tracks(account_id, track_id),
            CONSTRAINT uq_topic_candidates_dedupe
                UNIQUE (account_id, track_id, dedupe_key),
            CONSTRAINT chk_topic_candidates_status
                CHECK (status IN ('new', 'shortlisted', 'adopted', 'rejected', 'expired')),
            CONSTRAINT chk_topic_candidates_source_identity
                CHECK (source_url IS NOT NULL OR source_item_id IS NOT NULL)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_candidates_pool
        ON hermes.topic_candidates(account_id, track_id, status, captured_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_candidates_source
        ON hermes.topic_candidates(source, captured_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_candidates_topic_id
        ON hermes.topic_candidates(topic_id)
        WHERE topic_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_candidates_topic_id")
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_candidates_source")
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_candidates_pool")
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_candidate_tracks_enabled")
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_candidate_accounts_enabled")
    op.execute("DROP TABLE IF EXISTS hermes.topic_candidates")
    op.execute("DROP TABLE IF EXISTS hermes.topic_candidate_tracks")
    op.execute("DROP TABLE IF EXISTS hermes.topic_candidate_accounts")
