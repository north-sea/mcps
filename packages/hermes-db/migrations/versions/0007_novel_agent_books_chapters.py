"""add novel agent books and chapters

Revision ID: 0007_novel_agent_books
Revises: 0006_agent_self_evolution
Create Date: 2026-06-14
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0007_novel_agent_books"
down_revision: Union[str, None] = "0006_agent_self_evolution"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. novel_books
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_books (
            book_slug TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT,
            total_chapters INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_books_created_at
        ON hermes.novel_books(created_at DESC)
        """
    )

    # 2. novel_chapters
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_chapters (
            chapter_id TEXT PRIMARY KEY,
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            chapter_number INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            word_count INTEGER NOT NULL,
            split_source TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_novel_chapters_book_number UNIQUE (book_slug, chapter_number)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_chapters_book_slug
        ON hermes.novel_chapters(book_slug, chapter_number)
        """
    )

    # 3. novel_chapter_analyses
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_chapter_analyses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chapter_id TEXT NOT NULL REFERENCES hermes.novel_chapters(chapter_id) ON DELETE CASCADE,
            summary TEXT NOT NULL,
            plot_points TEXT[] NOT NULL DEFAULT '{}',
            characters TEXT[] NOT NULL DEFAULT '{}',
            conflicts TEXT[] NOT NULL DEFAULT '{}',
            hooks TEXT[] NOT NULL DEFAULT '{}',
            dialogue_samples_by_dimension JSONB NOT NULL DEFAULT '{}'::jsonb,
            style_signals JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_novel_chapter_analyses_chapter UNIQUE (chapter_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_chapter_analyses_chapter_id
        ON hermes.novel_chapter_analyses(chapter_id)
        """
    )

    # 4. novel_style_profiles
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_style_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            version INTEGER NOT NULL,
            active BOOLEAN NOT NULL DEFAULT true,
            summary JSONB NOT NULL,
            dimensions JSONB NOT NULL,
            prompt_template TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_novel_style_profiles_book_version UNIQUE (book_slug, version),
            CONSTRAINT chk_novel_style_profiles_version_positive CHECK (version > 0)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_style_profiles_book_active
        ON hermes.novel_style_profiles(book_slug, active)
        WHERE active = true
        """
    )

    # 5. novel_style_anchors
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_style_anchors (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            style_profile_id UUID NOT NULL REFERENCES hermes.novel_style_profiles(id) ON DELETE CASCADE,
            dimension TEXT NOT NULL,
            text TEXT NOT NULL,
            chapter_id TEXT NOT NULL REFERENCES hermes.novel_chapters(chapter_id) ON DELETE CASCADE,
            line_range INTEGER[] NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_style_anchors_profile
        ON hermes.novel_style_anchors(style_profile_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_style_anchors_chapter
        ON hermes.novel_style_anchors(chapter_id)
        """
    )

    # 6. novel_validation_reports
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_validation_reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            is_valid BOOLEAN NOT NULL,
            total_chapters INTEGER NOT NULL,
            warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
            errors JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_validation_reports_book_created
        ON hermes.novel_validation_reports(book_slug, created_at DESC)
        """
    )

    # 7. novel_analysis_runs
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_analysis_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            started_at TIMESTAMPTZ NOT NULL,
            completed_at TIMESTAMPTZ,
            stage TEXT NOT NULL,
            chapters_status JSONB NOT NULL DEFAULT '[]'::jsonb,
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_analysis_runs_book_started
        ON hermes.novel_analysis_runs(book_slug, started_at DESC)
        """
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key dependencies)
    op.execute("DROP TABLE IF EXISTS hermes.novel_analysis_runs CASCADE")
    op.execute("DROP TABLE IF EXISTS hermes.novel_validation_reports CASCADE")
    op.execute("DROP TABLE IF EXISTS hermes.novel_style_anchors CASCADE")
    op.execute("DROP TABLE IF EXISTS hermes.novel_style_profiles CASCADE")
    op.execute("DROP TABLE IF EXISTS hermes.novel_chapter_analyses CASCADE")
    op.execute("DROP TABLE IF EXISTS hermes.novel_chapters CASCADE")
    op.execute("DROP TABLE IF EXISTS hermes.novel_books CASCADE")

