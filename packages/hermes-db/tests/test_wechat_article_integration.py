import pytest

from hermes_db_mcp.repositories import wechat_article_repo, workflow_repo


@pytest.mark.asyncio
async def test_wechat_article_roundtrip(db_pool):
    run_id = "pytest-wechat-article-run"
    draft_artifact_id = "pytest-wechat-article-draft"
    published_artifact_id = "pytest-wechat-article-final"
    publish_artifact_id = "pytest-wechat-article-publish"
    publication_key = "pytest-wechat-article-key"

    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            DELETE FROM hermes.wechat_article_external_refs
            WHERE article_id IN (
                SELECT article_id FROM hermes.wechat_articles
                WHERE account = 'pytest-account'
            )
            """
        )
        await conn.execute("DELETE FROM hermes.wechat_articles WHERE account = 'pytest-account'")
        await conn.execute(
            "DELETE FROM hermes.workflow_artifacts WHERE artifact_id = ANY($1::text[])",
            [draft_artifact_id, published_artifact_id, publish_artifact_id],
        )
        await conn.execute(
            "DELETE FROM hermes.wechat_workflow_runs WHERE run_id = $1",
            run_id,
        )

    try:
        await workflow_repo.upsert_run(
            db_pool,
            run_id=run_id,
            phase="publish",
            current_stage="publish",
            status="running",
            dry_run=False,
            metadata={"source": "pytest"},
        )
        for artifact_id, name in (
            (draft_artifact_id, "draft"),
            (published_artifact_id, "transformed-draft"),
            (publish_artifact_id, "publish-result"),
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

        article, created = await wechat_article_repo.upsert_article(
            db_pool,
            publication_idempotency_key=publication_key,
            account="pytest-account",
            run_id=run_id,
            draft_artifact_id=draft_artifact_id,
            published_artifact_id=published_artifact_id,
            publish_artifact_id=publish_artifact_id,
            status="published",
            published_url="https://mp.weixin.qq.com/s/pytest",
            publish_target="wechat-mp",
            metadata={"source": "pytest"},
        )

        assert created is True
        assert article["account"] == "pytest-account"

        article_again, created_again = await wechat_article_repo.upsert_article(
            db_pool,
            publication_idempotency_key=publication_key,
            account="pytest-account",
            run_id=run_id,
            status="published",
            published_url="https://mp.weixin.qq.com/s/pytest",
        )

        assert created_again is False
        assert article_again["article_id"] == article["article_id"]

        patched, refs = await wechat_article_repo.patch_article_refs_and_summary(
            db_pool,
            article_id=article["article_id"],
            refs=[
                {
                    "ref_type": "canonical_url",
                    "ref_value": "https://mp.weixin.qq.com/s/pytest",
                    "ref_source": "pytest",
                    "is_primary": True,
                }
            ],
            patch={"canonical_url": "https://mp.weixin.qq.com/s/pytest"},
        )

        assert patched["canonical_url"] == "https://mp.weixin.qq.com/s/pytest"
        assert refs[0]["ref_type"] == "canonical_url"

        listed = await wechat_article_repo.list_articles(db_pool, account="pytest-account")
        assert len(listed) == 1
        assert listed[0]["article_id"] == article["article_id"]

        detail = await wechat_article_repo.get_article(db_pool, article_id=article["article_id"])
        detail_refs = await wechat_article_repo.list_article_refs(
            db_pool,
            article_id=article["article_id"],
        )

        assert detail["published_artifact_id"] == published_artifact_id
        assert detail_refs[0]["ref_value"] == "https://mp.weixin.qq.com/s/pytest"
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                DELETE FROM hermes.wechat_article_external_refs
                WHERE article_id IN (
                    SELECT article_id FROM hermes.wechat_articles
                    WHERE account = 'pytest-account'
                )
                """
            )
            await conn.execute("DELETE FROM hermes.wechat_articles WHERE account = 'pytest-account'")
            await conn.execute(
                "DELETE FROM hermes.workflow_artifacts WHERE artifact_id = ANY($1::text[])",
                [draft_artifact_id, published_artifact_id, publish_artifact_id],
            )
            await conn.execute(
                "DELETE FROM hermes.wechat_workflow_runs WHERE run_id = $1",
                run_id,
            )
