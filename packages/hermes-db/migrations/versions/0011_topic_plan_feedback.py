"""add topic plan feedback events

Revision ID: 0011_topic_plan_feedback
Revises: 0010_topic_plans
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0011_topic_plan_feedback"
down_revision: Union[str, None] = "0010_topic_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.topic_plan_feedback_events (
            event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            plan_id UUID NOT NULL,
            account_id TEXT NOT NULL,
            track_id TEXT,
            event_type TEXT NOT NULL,
            dedupe_key TEXT,
            reason_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            note TEXT,
            decided_by TEXT,
            topic_id UUID,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            event_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fk_topic_plan_feedback_events_plan
                FOREIGN KEY (plan_id)
                REFERENCES hermes.topic_plans(plan_id)
                ON DELETE CASCADE,
            CONSTRAINT fk_topic_plan_feedback_events_topic
                FOREIGN KEY (topic_id)
                REFERENCES hermes.topics(id)
                ON DELETE SET NULL,
            CONSTRAINT chk_topic_plan_feedback_event_type
                CHECK (
                    event_type IN (
                        'accepted',
                        'rejected',
                        'deferred',
                        'archived',
                        'written',
                        'published',
                        'score_adjusted'
                    )
                ),
            CONSTRAINT chk_topic_plan_feedback_reason_tags_array
                CHECK (jsonb_typeof(reason_tags) = 'array'),
            CONSTRAINT chk_topic_plan_feedback_metadata_object
                CHECK (jsonb_typeof(metadata) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_plan_feedback_plan_event_at
        ON hermes.topic_plan_feedback_events(plan_id, event_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_plan_feedback_account_track_event_at
        ON hermes.topic_plan_feedback_events(account_id, track_id, event_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_plan_feedback_account_event_type_event_at
        ON hermes.topic_plan_feedback_events(account_id, event_type, event_at DESC)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_topic_plan_feedback_dedupe
        ON hermes.topic_plan_feedback_events(plan_id, event_type, dedupe_key)
        WHERE dedupe_key IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topic_plan_feedback_topic_id
        ON hermes.topic_plan_feedback_events(topic_id)
        WHERE topic_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_plan_feedback_topic_id")
    op.execute("DROP INDEX IF EXISTS hermes.uq_topic_plan_feedback_dedupe")
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_plan_feedback_account_event_type_event_at")
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_plan_feedback_account_track_event_at")
    op.execute("DROP INDEX IF EXISTS hermes.idx_topic_plan_feedback_plan_event_at")
    op.execute("DROP TABLE IF EXISTS hermes.topic_plan_feedback_events")
