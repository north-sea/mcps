"""add revisit_of and mother_theme to topics

Revision ID: 0001_topic_revisit
Revises:
Create Date: 2026-06-01
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0001_topic_revisit"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE hermes.topics
        ADD COLUMN IF NOT EXISTS revisit_of UUID
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_topics_revisit_of'
                  AND conrelid = 'hermes.topics'::regclass
            ) THEN
                RETURN;
            END IF;

            ALTER TABLE hermes.topics
            ADD CONSTRAINT fk_topics_revisit_of
            FOREIGN KEY (revisit_of)
            REFERENCES hermes.topics(id)
            ON DELETE SET NULL;
        END $$
        """
    )
    op.execute(
        """
        ALTER TABLE hermes.topics
        ADD COLUMN IF NOT EXISTS mother_theme TEXT
        """
    )
    op.execute(
        """
        ALTER TABLE hermes.topics
        DROP CONSTRAINT IF EXISTS chk_topics_revisit_of_not_self
        """
    )
    op.execute(
        """
        ALTER TABLE hermes.topics
        ADD CONSTRAINT chk_topics_revisit_of_not_self
        CHECK (revisit_of IS NULL OR revisit_of <> id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_topics_revisit_of
        ON hermes.topics(revisit_of)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS hermes.idx_topics_revisit_of")
    op.execute(
        """
        ALTER TABLE hermes.topics
        DROP CONSTRAINT IF EXISTS chk_topics_revisit_of_not_self
        """
    )
    op.execute(
        """
        ALTER TABLE hermes.topics
        DROP CONSTRAINT IF EXISTS fk_topics_revisit_of
        """
    )
    op.execute("ALTER TABLE hermes.topics DROP COLUMN IF EXISTS mother_theme")
    op.execute("ALTER TABLE hermes.topics DROP COLUMN IF EXISTS revisit_of")
