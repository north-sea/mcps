"""add novel retrospective contracts

Revision ID: 0009_novel_retrospective
Revises: 0008_novel_planning
Create Date: 2026-07-07
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0009_novel_retrospective"
down_revision: Union[str, None] = "0008_novel_planning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_retrospective_reports (
            report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            batch_label TEXT NOT NULL,
            mode VARCHAR(20) NOT NULL,
            start_chapter INTEGER NOT NULL,
            end_chapter INTEGER NOT NULL,
            scoring_version TEXT NOT NULL,
            diagnosis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            llm_narrative TEXT,
            confidence VARCHAR(10) NOT NULL,
            warnings TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            review_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_novel_retrospective_reports_mode
                CHECK (mode IN ('batch', 'volume')),
            CONSTRAINT chk_novel_retrospective_reports_chapter_range
                CHECK (start_chapter > 0 AND end_chapter >= start_chapter),
            CONSTRAINT chk_novel_retrospective_reports_confidence
                CHECK (confidence IN ('high', 'low')),
            CONSTRAINT chk_novel_retrospective_reports_review_status
                CHECK (review_status IN ('pending', 'approved', 'rejected'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_retrospective_reports_book_created
        ON hermes.novel_retrospective_reports(book_slug, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_retrospective_reports_book_range
        ON hermes.novel_retrospective_reports(book_slug, start_chapter, end_chapter)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_retrospective_reports_review_status
        ON hermes.novel_retrospective_reports(review_status, created_at DESC)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_retrospective_alerts (
            alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            report_id UUID NOT NULL REFERENCES hermes.novel_retrospective_reports(report_id) ON DELETE CASCADE,
            alert_type VARCHAR(50) NOT NULL,
            severity VARCHAR(10) NOT NULL,
            description TEXT NOT NULL,
            evidence_refs TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            suggested_action TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_novel_retrospective_alerts_type
                CHECK (alert_type IN ('high_similarity', 'character_single_reaction', 'foreshadowing_expired', 'emotional_debt_overdue')),
            CONSTRAINT chk_novel_retrospective_alerts_severity
                CHECK (severity IN ('red', 'yellow', 'green'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_retrospective_alerts_report
        ON hermes.novel_retrospective_alerts(report_id, created_at)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_correction_constraints (
            constraint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            source_report_id UUID NOT NULL REFERENCES hermes.novel_retrospective_reports(report_id) ON DELETE CASCADE,
            alert_type TEXT NOT NULL,
            description TEXT NOT NULL,
            target_chapters VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_novel_correction_constraints_target
                CHECK (target_chapters IN ('next', 'remaining')),
            CONSTRAINT chk_novel_correction_constraints_status
                CHECK (status IN ('pending', 'approved', 'rejected', 'expired'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_correction_constraints_book_status
        ON hermes.novel_correction_constraints(book_slug, status, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_correction_constraints_report
        ON hermes.novel_correction_constraints(source_report_id)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_handoff_packages (
            package_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            snapshot_chapter INTEGER NOT NULL,
            context_version INTEGER NOT NULL,
            progress_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            character_states_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            recent_changes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            remaining_tasks TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            disabled_templates TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            stage_reminders TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_novel_handoff_packages_snapshot
                CHECK (snapshot_chapter > 0),
            CONSTRAINT chk_novel_handoff_packages_context_version
                CHECK (context_version > 0)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_handoff_packages_book_created
        ON hermes.novel_handoff_packages(book_slug, created_at DESC)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_character_states (
            state_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            character_name TEXT NOT NULL,
            last_chapter INTEGER NOT NULL,
            location TEXT NOT NULL,
            relationships_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            emotional_state TEXT NOT NULL,
            goals TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            conflicts TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            arc_progress TEXT NOT NULL,
            dialogue_style TEXT NOT NULL,
            personality_traits TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_novel_character_states_last_chapter
                CHECK (last_chapter > 0),
            CONSTRAINT uq_novel_character_states_book_character_chapter
                UNIQUE(book_slug, character_name, last_chapter)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_character_states_book_character
        ON hermes.novel_character_states(book_slug, character_name)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_character_states_book_chapter
        ON hermes.novel_character_states(book_slug, last_chapter DESC)
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_learning_candidates (
            candidate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_report_id UUID NOT NULL REFERENCES hermes.novel_retrospective_reports(report_id) ON DELETE CASCADE,
            scope TEXT NOT NULL,
            trigger_conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
            proposed_action TEXT NOT NULL,
            evidence_refs TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            confidence VARCHAR(10) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_novel_learning_candidates_confidence
                CHECK (confidence IN ('high', 'medium', 'low')),
            CONSTRAINT chk_novel_learning_candidates_status
                CHECK (status IN ('pending', 'approved', 'rejected'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_learning_candidates_source_report
        ON hermes.novel_learning_candidates(source_report_id, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_learning_candidates_source_report")
    op.execute("DROP TABLE IF EXISTS hermes.novel_learning_candidates")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_character_states_book_chapter")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_character_states_book_character")
    op.execute("DROP TABLE IF EXISTS hermes.novel_character_states")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_handoff_packages_book_created")
    op.execute("DROP TABLE IF EXISTS hermes.novel_handoff_packages")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_correction_constraints_report")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_correction_constraints_book_status")
    op.execute("DROP TABLE IF EXISTS hermes.novel_correction_constraints")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_retrospective_alerts_report")
    op.execute("DROP TABLE IF EXISTS hermes.novel_retrospective_alerts")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_retrospective_reports_review_status")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_retrospective_reports_book_range")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_retrospective_reports_book_created")
    op.execute("DROP TABLE IF EXISTS hermes.novel_retrospective_reports")
