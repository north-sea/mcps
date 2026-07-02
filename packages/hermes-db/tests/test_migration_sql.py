import re
from pathlib import Path

# Postgres alembic_version.version_num is varchar(32); a revision id longer than
# this fails at `UPDATE alembic_version` during deploy (after build + image push),
# which we have hit twice. Guard it here so CI fails in the test phase instead.
ALEMBIC_VERSION_NUM_MAX_LEN = 32

_REVISION_RE = re.compile(r'^revision: str = "(?P<rev>[^"]+)"', re.MULTILINE)


def test_all_migration_revision_ids_fit_alembic_version_column():
    versions_dir = Path("migrations/versions")
    migrations = sorted(versions_dir.glob("[0-9]*.py"))
    assert migrations, "expected at least one migration under migrations/versions"

    offenders = []
    for migration in migrations:
        match = _REVISION_RE.search(migration.read_text())
        assert match, f"could not find revision id in {migration.name}"
        rev = match.group("rev")
        if len(rev) > ALEMBIC_VERSION_NUM_MAX_LEN:
            offenders.append((migration.name, rev, len(rev)))

    assert not offenders, (
        "revision ids exceed alembic_version varchar(32) limit and will fail "
        f"at deploy time: {offenders}"
    )


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


def test_wechat_analytics_ingestion_migration_contains_required_schema_changes():
    migration = Path(
        "migrations/versions/0004_wechat_analytics_ingestion.py"
    ).read_text()

    assert 'down_revision: Union[str, None] = "0003_wechat_publication_ledger"' in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.analytics_import_runs" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.wechat_article_metric_snapshots" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.wechat_article_channel_daily_metrics" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.wechat_article_audience_profiles" not in migration
    assert "REFERENCES hermes.wechat_articles(article_id) ON DELETE CASCADE" in migration
    assert "REFERENCES hermes.analytics_import_runs(import_run_id) ON DELETE SET NULL" in migration
    assert "chk_analytics_import_runs_status" in migration
    assert "chk_analytics_import_runs_counts_nonnegative" in migration
    assert "uq_wechat_article_metric_snapshot_identity" in migration
    assert "chk_wechat_article_metric_snapshot_counts_nonnegative" in migration
    assert "chk_wechat_article_metric_snapshot_completion_rate" in migration
    assert "uq_wechat_article_channel_daily_identity" in migration
    assert "chk_wechat_article_channel_daily_counts_nonnegative" in migration
    assert "idx_analytics_import_runs_account_created" in migration
    assert "idx_wechat_article_metric_snapshots_account_stat" in migration
    assert "idx_wechat_article_metric_snapshots_article_stat" in migration
    assert "idx_wechat_article_metric_snapshots_source_stat" in migration
    assert "idx_wechat_article_channel_daily_account_date" in migration
    assert "idx_wechat_article_channel_daily_article_date" in migration
    assert "DROP TABLE IF EXISTS hermes.wechat_article_channel_daily_metrics" in migration
    assert "DROP TABLE IF EXISTS hermes.wechat_article_metric_snapshots" in migration
    assert "DROP TABLE IF EXISTS hermes.analytics_import_runs" in migration


def test_wechat_retrospective_topic_optimizer_migration_contains_required_schema_changes():
    migration = Path(
        "migrations/versions/0005_wechat_retrospective_topic_optimizer.py"
    ).read_text()

    assert 'revision: str = "0005_wechat_retro_opt"' in migration
    assert 'down_revision: Union[str, None] = "0004_wechat_analytics_ingestion"' in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.topic_performance" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.wechat_retrospective_reports" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.topic_optimization_suggestions" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.learning_candidates" in migration
    assert "REFERENCES hermes.wechat_articles(article_id) ON DELETE CASCADE" in migration
    assert "REFERENCES hermes.topics(id) ON DELETE SET NULL" in migration
    assert "REFERENCES hermes.wechat_articles(article_id) ON DELETE SET NULL" in migration
    assert (
        "REFERENCES hermes.wechat_retrospective_reports(report_id) ON DELETE CASCADE"
        in migration
    )
    assert "uq_topic_performance_identity" in migration
    assert "chk_topic_performance_scores_range" in migration
    assert "chk_topic_performance_confidence_range" in migration
    assert "chk_wechat_retrospective_reports_type" in migration
    assert "chk_wechat_retrospective_reports_generation_mode" in migration
    assert "chk_wechat_retrospective_reports_status" in migration
    assert "chk_wechat_retrospective_reports_period" in migration
    assert "chk_topic_optimization_suggestions_type" in migration
    assert "chk_topic_optimization_suggestions_target_kind" in migration
    assert "chk_topic_optimization_suggestions_review_status" in migration
    assert "chk_topic_optimization_suggestions_target_ref" in migration
    assert "chk_learning_candidates_type" in migration
    assert "chk_learning_candidates_status" in migration
    assert "idx_topic_performance_account_stat" in migration
    assert "idx_topic_performance_article_stat" in migration
    assert "idx_topic_performance_topic_stat" in migration
    assert "idx_wechat_retrospective_reports_account_period" in migration
    assert "idx_wechat_retrospective_reports_account_type_created" in migration
    assert "idx_topic_optimization_suggestions_account_status_target" in migration
    assert "idx_topic_optimization_suggestions_approved_hints" in migration
    assert "idx_learning_candidates_account_status_type" in migration
    assert "idx_learning_candidates_source_report" in migration
    assert "DROP TABLE IF EXISTS hermes.learning_candidates" in migration
    assert "DROP TABLE IF EXISTS hermes.topic_optimization_suggestions" in migration
    assert "DROP TABLE IF EXISTS hermes.wechat_retrospective_reports" in migration
    assert "DROP TABLE IF EXISTS hermes.topic_performance" in migration


def test_agent_self_evolution_foundation_migration_contains_required_schema_changes():
    migration = Path(
        "migrations/versions/0006_agent_self_evolution_foundation.py"
    ).read_text()

    assert 'revision: str = "0006_agent_self_evolution"' in migration
    assert 'down_revision: Union[str, None] = "0005_wechat_retro_opt"' in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.agent_policies" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.policy_applications" in migration
    assert (
        "REFERENCES hermes.learning_candidates(candidate_id) ON DELETE SET NULL"
        in migration
    )
    assert (
        "REFERENCES hermes.agent_policies(policy_version_id) ON DELETE RESTRICT"
        in migration
    )
    assert "uq_agent_policies_policy_version" in migration
    assert "uq_agent_policies_source_candidate" in migration
    assert "chk_agent_policies_version_positive" in migration
    assert "chk_agent_policies_status" in migration
    assert "chk_agent_policies_policy_type" in migration
    assert "chk_agent_policies_effective_range" in migration
    assert "chk_agent_policies_scope_json_object" in migration
    assert "chk_agent_policies_task_types_json_array" in migration
    assert "chk_policy_applications_version_positive" in migration
    assert "chk_policy_applications_status" in migration
    assert "chk_policy_applications_error_summary_json_object" in migration
    assert "idx_agent_policies_active_lookup" in migration
    assert "idx_agent_policies_source_candidate" in migration
    assert "idx_agent_policies_policy_id" in migration
    assert "idx_agent_policies_scope_gin" in migration
    assert "idx_agent_policies_trigger_conditions_gin" in migration
    assert "idx_policy_applications_run" in migration
    assert "idx_policy_applications_policy" in migration
    assert "idx_policy_applications_policy_version" in migration
    assert "idx_policy_applications_domain_task" in migration
    assert "DROP TABLE IF EXISTS hermes.policy_applications" in migration
    assert "DROP TABLE IF EXISTS hermes.agent_policies" in migration
    assert migration.index("DROP TABLE IF EXISTS hermes.policy_applications") < migration.index(
        "DROP TABLE IF EXISTS hermes.agent_policies"
    )


def test_topic_candidate_contracts_migration_contains_required_schema_changes():
    migration = Path(
        "migrations/versions/0009_topic_candidate_contracts.py"
    ).read_text()

    assert 'revision: str = "0009_topic_candidates"' in migration
    assert 'down_revision: Union[str, None] = "0008_novel_planning"' in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.topic_candidate_accounts" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.topic_candidate_tracks" in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.topic_candidates" in migration
    assert "REFERENCES hermes.topic_candidate_accounts(account_id)" in migration
    assert "REFERENCES hermes.topic_candidate_tracks(account_id, track_id)" in migration
    assert "REFERENCES hermes.topics(id)" in migration
    assert "CONSTRAINT uq_topic_candidates_dedupe" in migration
    assert "UNIQUE (account_id, track_id, dedupe_key)" in migration
    assert "CONSTRAINT chk_topic_candidates_status" in migration
    assert "CONSTRAINT chk_topic_candidates_source_identity" in migration
    assert "idx_topic_candidate_accounts_enabled" in migration
    assert "idx_topic_candidate_tracks_enabled" in migration
    assert "idx_topic_candidates_pool" in migration
    assert "idx_topic_candidates_source" in migration
    assert "idx_topic_candidates_topic_id" in migration
    assert "DROP TABLE IF EXISTS hermes.topic_candidates" in migration
    assert "DROP TABLE IF EXISTS hermes.topic_candidate_tracks" in migration
    assert "DROP TABLE IF EXISTS hermes.topic_candidate_accounts" in migration


def test_topic_plan_contracts_migration_contains_required_schema_changes():
    migration = Path("migrations/versions/0010_topic_plan_contracts.py").read_text()

    assert 'revision: str = "0010_topic_plans"' in migration
    assert 'down_revision: Union[str, None] = "0009_topic_candidates"' in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.topic_plans" in migration
    assert "candidate_id UUID NOT NULL REFERENCES hermes.topic_candidates(id) ON DELETE CASCADE" in migration
    assert "topic_id UUID REFERENCES hermes.topics(id) ON DELETE SET NULL" in migration
    assert "CONSTRAINT uq_topic_plans_candidate UNIQUE (candidate_id)" in migration
    assert "CONSTRAINT chk_topic_plans_status" in migration
    assert "CHECK (status IN ('planned', 'rejected', 'consumed', 'archived'))" in migration
    assert "CONSTRAINT chk_topic_plans_planned_shape" in migration
    assert "jsonb_array_length(topic_angles) BETWEEN 3 AND 5" in migration
    assert "CONSTRAINT chk_topic_plans_rejected_shape" in migration
    assert "idx_topic_plans_account_status_created" in migration
    assert "idx_topic_plans_account_track_status_created" in migration
    assert "idx_topic_plans_candidate" in migration
    assert "idx_topic_plans_topic_id" in migration
    assert "DROP TABLE IF EXISTS hermes.topic_plans" in migration


def test_topic_plan_feedback_migration_contains_required_schema_changes():
    migration = Path("migrations/versions/0011_topic_plan_feedback.py").read_text()

    assert 'revision: str = "0011_topic_plan_feedback"' in migration
    assert 'down_revision: Union[str, None] = "0010_topic_plans"' in migration
    assert "CREATE TABLE IF NOT EXISTS hermes.topic_plan_feedback_events" in migration
    assert "event_id UUID PRIMARY KEY DEFAULT gen_random_uuid()" in migration
    assert "plan_id UUID NOT NULL" in migration
    assert "CONSTRAINT fk_topic_plan_feedback_events_plan" in migration
    assert "REFERENCES hermes.topic_plans(plan_id)" in migration
    assert "ON DELETE CASCADE" in migration
    assert "CONSTRAINT fk_topic_plan_feedback_events_topic" in migration
    assert "REFERENCES hermes.topics(id)" in migration
    assert "ON DELETE SET NULL" in migration
    assert "CONSTRAINT chk_topic_plan_feedback_event_type" in migration
    assert "'accepted'" in migration
    assert "'published'" in migration
    assert "'score_adjusted'" in migration
    assert "CONSTRAINT chk_topic_plan_feedback_reason_tags_array" in migration
    assert "CHECK (jsonb_typeof(reason_tags) = 'array')" in migration
    assert "CONSTRAINT chk_topic_plan_feedback_metadata_object" in migration
    assert "CHECK (jsonb_typeof(metadata) = 'object')" in migration
    assert "idx_topic_plan_feedback_plan_event_at" in migration
    assert "idx_topic_plan_feedback_account_track_event_at" in migration
    assert "idx_topic_plan_feedback_account_event_type_event_at" in migration
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_topic_plan_feedback_dedupe" in migration
    assert "ON hermes.topic_plan_feedback_events(plan_id, event_type, dedupe_key)" in migration
    assert "WHERE dedupe_key IS NOT NULL" in migration
    assert "idx_topic_plan_feedback_topic_id" in migration
    assert "DROP TABLE IF EXISTS hermes.topic_plan_feedback_events" in migration
