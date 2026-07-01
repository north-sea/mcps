"""add topic plan contracts

Revision ID: 0010_topic_plans
Revises: 0009_topic_candidates
Create Date: 2026-07-01
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0010_topic_plans"
down_revision: Union[str, None] = "0009_topic_candidates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.topic_plans (
            plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            candidate_id UUID NOT NULL REFERENCES hermes.topic_candidates(id) ON DELETE CASCADE,
            account_id TEXT NOT NULL,
            track_id TEXT,
            status TEXT NOT NULL,
            recommended_angle_index INTEGER,
            topic_angles JSONB NOT NULL DEFAULT '[]'::jsonb,
            outline_pack JSONB NOT NULL DEFAULT '{}'::jsonb,
            writing_brief JSONB NOT NULL DEFAULT '{}'::jsonb,
            image_brief JSONB NOT NULL DEFAULT '{}'::jsonb,
            evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
            llm_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            rejection_reason TEXT,
            topic_id UUID REFERENCES hermes.topics(id) ON DELETE SET NULL,
            source TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            consumed_at TIMESTAMPTZ,
            CONSTRAINT uq_topic_plans_candidate UNIQUE (candidate_id),
            CONSTRAINT chk_topic_plans_status
                CHECK (status IN ('planned', 'rejected', 'consumed', 'archived')),
            CONSTRAINT chk_topic_plans_planned_shape
                CHECK (
                    status <> 'planned'
                    OR (
                        recommended_angle_index IS NOT NULL
                        AND jsonb_typeof(topic_angles) = 'array'
                        AND jsonb_array_length(topic_angles) BETWEEN 3 AND 5
                        AND jsonb_typeof(outline_pack) = 'object'
                        AND jsonb_typeof(writing_brief) = 'object'
                        AND jsonb_typeof(image_brief) = 'object'
                    )
                ),
            CONSTRAINT chk_topic_plans_rejected_shape
                CHECK (
                    status <> 'rejected'
                    OR (
                        rejection_reason IS NOT NULL
                        AND btrim(rejection_reason) <> ''
                        AND jsonb_typeof(topic_angles) = 'array'
                        AND jsonb_typeof(outline_pack) = 'object'
                        AND jsonb_typeof(writing_brief) = 'object'
                        AND jsonb_typeof(image_brief) = 'object'
                    )
                )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_plans_account_status_created
        ON hermes.topic_plans(account_id, status, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_plans_account_track_status_created
        ON hermes.topic_plans(account_id, track_id, status, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_plans_candidate
        ON hermes.topic_plans(candidate_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_plans_topic_id
        ON hermes.topic_plans(topic_id)
        WHERE topic_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_plans_topic_id")
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_plans_candidate")
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_plans_account_track_status_created")
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_plans_account_status_created")
    op.execute("DROP TABLE IF EXISTS hermes.topic_plans")
