"""add novel planning tables and fields

Revision ID: 0008_novel_planning
Revises: 0007_novel_agent_books
Create Date: 2026-06-16
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0008_novel_planning"
down_revision: Union[str, None] = "0007_novel_agent_books"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 扩展现有表：novel_books (context_version)
    op.execute(
        """
        ALTER TABLE hermes.novel_books
        ADD COLUMN IF NOT EXISTS context_version INTEGER NOT NULL DEFAULT 1
        """
    )

    # 2. 扩展现有表：novel_chapters (context_version, residue)
    op.execute(
        """
        ALTER TABLE hermes.novel_chapters
        ADD COLUMN IF NOT EXISTS context_version INTEGER
        """
    )
    op.execute(
        """
        ALTER TABLE hermes.novel_chapters
        ADD COLUMN IF NOT EXISTS residue JSONB
        """
    )

    # 3. 创建新表：novel_worldbuilding
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_worldbuilding (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            rules TEXT NOT NULL,
            history TEXT NOT NULL,
            magic_system TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(book_slug)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_worldbuilding_book
        ON hermes.novel_worldbuilding(book_slug)
        """
    )

    # 4. 创建新表：novel_characters
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_characters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            personality TEXT NOT NULL,
            secondary_interpretation TEXT,
            behavior_prohibitions TEXT[],
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(book_slug, name)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_characters_book
        ON hermes.novel_characters(book_slug)
        """
    )

    # 5. 创建新表：novel_foreshadowing
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_foreshadowing (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            title TEXT NOT NULL,
            plant_chapter INTEGER NOT NULL,
            reminder_chapter INTEGER,
            payoff_chapter INTEGER NOT NULL,
            priority VARCHAR(10) NOT NULL CHECK (priority IN ('high', 'medium', 'low')),
            status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'resolved')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(book_slug, title)
        )
        """
    )
    # 关键性能优化索引：支持活跃伏笔过滤查询
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_foreshadowing_book_status_payoff
        ON hermes.novel_foreshadowing(book_slug, status, payoff_chapter)
        """
    )

    # 6. 创建新表：novel_volume_outlines
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_volume_outlines (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            volume_number INTEGER NOT NULL,
            goal TEXT NOT NULL,
            start_chapter INTEGER NOT NULL,
            end_chapter INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(book_slug, volume_number)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_volume_outlines_book
        ON hermes.novel_volume_outlines(book_slug)
        """
    )

    # 7. 创建新表：novel_human_reviews
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_human_reviews (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            stage VARCHAR(50) NOT NULL CHECK (stage IN ('concept', 'outline', 'volume', 'chapter')),
            target_id UUID,
            status VARCHAR(20) NOT NULL CHECK (status IN ('pending_review', 'approved', 'rejected')),
            reviewer_notes TEXT,
            feedback JSONB,
            approved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_human_reviews_book_stage
        ON hermes.novel_human_reviews(book_slug, stage)
        """
    )

    # 8. 创建新表：novel_context_change_log
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS hermes.novel_context_change_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            book_slug TEXT NOT NULL REFERENCES hermes.novel_books(book_slug) ON DELETE CASCADE,
            old_version INTEGER NOT NULL,
            new_version INTEGER NOT NULL,
            changed_scope VARCHAR(50) NOT NULL CHECK (changed_scope IN ('book_outline', 'volume_outline', 'characters', 'foreshadowing')),
            change_summary TEXT,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_context_change_log_book
        ON hermes.novel_context_change_log(book_slug, changed_at DESC)
        """
    )

    # 9. 创建章节查询性能优化索引
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_novel_chapters_book_number
        ON hermes.novel_chapters(book_slug, chapter_number)
        """
    )


def downgrade() -> None:
    # 删除索引
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_chapters_book_number")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_context_change_log_book")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_human_reviews_book_stage")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_volume_outlines_book")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_foreshadowing_book_status_payoff")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_characters_book")
    op.execute("DROP INDEX IF EXISTS hermes.idx_novel_worldbuilding_book")

    # 删除新表
    op.execute("DROP TABLE IF EXISTS hermes.novel_context_change_log")
    op.execute("DROP TABLE IF EXISTS hermes.novel_human_reviews")
    op.execute("DROP TABLE IF EXISTS hermes.novel_volume_outlines")
    op.execute("DROP TABLE IF EXISTS hermes.novel_foreshadowing")
    op.execute("DROP TABLE IF EXISTS hermes.novel_characters")
    op.execute("DROP TABLE IF EXISTS hermes.novel_worldbuilding")

    # 移除扩展字段
    op.execute("ALTER TABLE hermes.novel_chapters DROP COLUMN IF EXISTS residue")
    op.execute("ALTER TABLE hermes.novel_chapters DROP COLUMN IF EXISTS context_version")
    op.execute("ALTER TABLE hermes.novel_books DROP COLUMN IF EXISTS context_version")

