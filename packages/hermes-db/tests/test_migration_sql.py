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


def test_workflow_artifact_migration_contains_required_schema_changes():
    migration = Path(
        "migrations/versions/0002_wechat_workflow_artifacts.py"
    ).read_text()

    assert 'down_revision: Union[str, None] = "0001_topic_revisit"' in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.wechat_workflow_runs" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.workflow_artifacts" in migration
    assert "REFERENCES hermes.wechat_workflow_runs(run_id)" in migration
    assert "REFERENCES hermes.topics(id) ON DELETE SET NULL" in migration
    assert "chk_workflow_artifacts_content_present" in migration
    assert "uq_workflow_artifact_logical_version" in migration
    assert "uq_workflow_artifact_logical_hash" in migration
    assert "idx_workflow_artifacts_run_created" in migration
    assert "idx_workflow_artifacts_stage_name" in migration


def test_wechat_publication_ledger_migration_contains_required_schema_changes():
    migration = Path(
        "migrations/versions/0003_wechat_publication_ledger.py"
    ).read_text()

    assert 'down_revision: Union[str, None] = "0002_wechat_workflow_artifacts"' in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.wechat_articles" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.wechat_article_external_refs" in migration
    assert "REFERENCES hermes.wechat_workflow_runs(run_id)" in migration
    assert "REFERENCES hermes.workflow_artifacts(artifact_id)" in migration
    assert "uq_wechat_articles_account_idempotency" in migration
    assert "chk_wechat_articles_status" in migration
    assert "chk_wechat_articles_reference_for_published" in migration
    assert "uq_wechat_article_external_ref_active" in migration
    assert "uq_wechat_article_external_ref_article_active" in migration
    assert "idx_wechat_articles_account_status_created" in migration
    assert "idx_wechat_article_refs_type_value_active" in migration
