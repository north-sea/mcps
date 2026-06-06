from datetime import date

import pytest

from hermes_db_mcp.repositories import (
    wechat_analytics_repo,
    wechat_article_repo,
    workflow_repo,
)


@pytest.mark.asyncio
async def test_wechat_analytics_roundtrip(db_pool):
    account = "pytest-analytics-account"
    run_id = "pytest-wechat-analytics-run"
    draft_artifact_id = "pytest-wechat-analytics-draft"
    published_artifact_id = "pytest-wechat-analytics-final"
    publication_key = "pytest-wechat-analytics-key"

    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM hermes.wechat_article_channel_daily_metrics
            WHERE account = $1
            """,
            account,
        )
        await conn.execute(
            """
            DELETE FROM hermes.wechat_article_metric_snapshots
            WHERE account = $1
            """,
            account,
        )
        await conn.execute("DELETE FROM hermes.analytics_import_runs WHERE account = $1", account)
        await conn.execute(
            """
            DELETE FROM hermes.wechat_article_external_refs
            WHERE article_id IN (
                SELECT article_id FROM hermes.wechat_articles
                WHERE account = $1
            )
            """,
            account,
        )
        await conn.execute("DELETE FROM hermes.wechat_articles WHERE account = $1", account)
        await conn.execute(
            "DELETE FROM hermes.workflow_artifacts WHERE artifact_id = ANY($1::text[])",
            [draft_artifact_id, published_artifact_id],
        )
        await conn.execute("DELETE FROM hermes.wechat_workflow_runs WHERE run_id = $1", run_id)

    try:
        await workflow_repo.upsert_run(
            db_pool,
            run_id=run_id,
            phase="publish",
            current_stage="analytics",
            status="completed",
            dry_run=False,
            metadata={"source": "pytest"},
        )
        for artifact_id, name in (
            (draft_artifact_id, "draft"),
            (published_artifact_id, "final"),
        ):
            await workflow_repo.upsert_artifact(
                db_pool,
                artifact_id=artifact_id,
                run_id=run_id,
                stage="publish",
                type=name,
                name=name,
                content_hash=f"sha256:{artifact_id}",
                content_size_bytes=7,
                content_preview="# Draft",
                content_text="# Draft",
                metadata={"source": "pytest"},
            )

        article, _created = await wechat_article_repo.upsert_article(
            db_pool,
            publication_idempotency_key=publication_key,
            account=account,
            run_id=run_id,
            draft_artifact_id=draft_artifact_id,
            published_artifact_id=published_artifact_id,
            status="published",
            published_url="https://mp.weixin.qq.com/s/pytest-analytics",
            metadata={"source": "pytest"},
        )

        snapshot = {
            "article_id": article["article_id"],
            "account": account,
            "stat_date": date(2026, 4, 13),
            "window_label": "D+1",
            "source": "manual_json",
            "read_user_count": 100,
            "completion_rate": 0.5,
            "missing_fields": [],
            "raw_json": {"row": 1},
        }
        channels = [
            {
                "article_id": article["article_id"],
                "account": account,
                "metric_date": date(2026, 4, 13),
                "channel": "全部",
                "source": "manual_json",
                "read_user_count": 100,
                "share_user_count": 2,
                "raw_json": {"channel": "全部"},
            },
            {
                "article_id": article["article_id"],
                "account": account,
                "metric_date": date(2026, 4, 13),
                "channel": "推荐",
                "source": "manual_json",
                "read_user_count": 80,
                "share_user_count": 1,
                "raw_json": {"channel": "推荐"},
            },
        ]

        first = await wechat_analytics_repo.run_import_transaction(
            db_pool,
            account=account,
            source="manual_json",
            snapshot_rows=[snapshot],
            channel_rows=channels,
            metadata={"source": "pytest"},
        )
        second = await wechat_analytics_repo.run_import_transaction(
            db_pool,
            account=account,
            source="manual_json",
            snapshot_rows=[{**snapshot, "read_user_count": 101}],
            channel_rows=channels,
            metadata={"source": "pytest-repeat"},
        )

        assert first["created"] == 1
        assert second["updated"] == 1

        rows = await wechat_analytics_repo.list_metric_snapshots(
            db_pool,
            account=account,
            article_id=article["article_id"],
            date_from=date(2026, 4, 13),
            date_to=date(2026, 4, 13),
            window_label="D+1",
            include_raw=True,
        )

        assert len(rows) == 1
        assert rows[0]["read_user_count"] == 101
        assert rows[0]["raw_json"] == {"row": 1}
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM hermes.wechat_article_channel_daily_metrics WHERE account = $1",
                account,
            )
            await conn.execute(
                "DELETE FROM hermes.wechat_article_metric_snapshots WHERE account = $1",
                account,
            )
            await conn.execute(
                "DELETE FROM hermes.analytics_import_runs WHERE account = $1",
                account,
            )
            await conn.execute(
                """
                DELETE FROM hermes.wechat_article_external_refs
                WHERE article_id IN (
                    SELECT article_id FROM hermes.wechat_articles
                    WHERE account = $1
                )
                """,
                account,
            )
            await conn.execute("DELETE FROM hermes.wechat_articles WHERE account = $1", account)
            await conn.execute(
                "DELETE FROM hermes.workflow_artifacts WHERE artifact_id = ANY($1::text[])",
                [draft_artifact_id, published_artifact_id],
            )
            await conn.execute("DELETE FROM hermes.wechat_workflow_runs WHERE run_id = $1", run_id)
