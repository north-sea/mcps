from pathlib import Path


def test_topic_revisit_migration_contains_required_schema_changes():
    migration = Path(
        "migrations/versions/0001_add_revisit_of_mother_theme.py"
    ).read_text()

    assert "ADD COLUMN IF NOT EXISTS revisit_of UUID" in migration
    assert "pg_constraint" in migration
    assert "ADD CONSTRAINT fk_topics_revisit_of" in migration
    assert "REFERENCES hermes.topics(id)" in migration
    assert "ON DELETE SET NULL" in migration
    assert "ADD COLUMN IF NOT EXISTS mother_theme TEXT" in migration
    assert "chk_topics_revisit_of_not_self" in migration
    assert "CHECK (revisit_of IS NULL OR revisit_of <> id)" in migration
    assert "CREATE INDEX IF NOT EXISTS idx_topics_revisit_of" in migration
