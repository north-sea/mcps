from datetime import datetime

import asyncpg
from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.server import mcp, AppContext
from hermes_db_mcp.repositories import wechat_article_repo
from hermes_db_mcp.contracts import (
    DEFAULT_WECHAT_ARTICLE_LIMIT,
    derive_publication_idempotency_key,
    error,
    validate_optional_uuid,
    validate_wechat_article_payload,
    validate_wechat_article_query,
    validate_wechat_article_ref_payload,
)


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _serialize_article(row: dict) -> dict:
    result = dict(row)
    for key in ("article_id", "topic_id"):
        if result.get(key) is not None:
            result[key] = str(result[key])
    for key in ("published_at", "created_at", "updated_at"):
        if result.get(key) is not None:
            result[key] = str(result[key])
    return result


def _serialize_ref(row: dict) -> dict:
    result = dict(row)
    for key in ("ref_id", "article_id"):
        if result.get(key) is not None:
            result[key] = str(result[key])
    for key in ("superseded_at", "created_at", "updated_at"):
        if result.get(key) is not None:
            result[key] = str(result[key])
    return result


def _map_db_error(exc: Exception) -> dict:
    if isinstance(exc, asyncpg.ForeignKeyViolationError):
        constraint = getattr(exc, "constraint_name", "") or ""
        field = "reference"
        if "run_id" in constraint:
            field = "run_id"
        elif "draft_artifact_id" in constraint:
            field = "draft_artifact_id"
        elif "published_artifact_id" in constraint:
            field = "published_artifact_id"
        elif "publish_artifact_id" in constraint:
            field = "publish_artifact_id"
        elif "topic_id" in constraint:
            field = "topic_id"
        return error("not_found", field=field, details={"constraint": constraint})
    if isinstance(exc, asyncpg.UniqueViolationError):
        return error("conflict", details={"message": str(exc)})
    if isinstance(exc, (asyncpg.UndefinedTableError, asyncpg.UndefinedColumnError)):
        return error("schema_drift", details={"message": str(exc)})
    return error("database_error", details={"message": str(exc)})


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def upsert_wechat_article(
    account: str,
    run_id: str,
    status: str,
    ctx: Context,
    publication_idempotency_key: str | None = None,
    task_id: str | None = None,
    topic_id: str | None = None,
    draft_artifact_id: str | None = None,
    published_artifact_id: str | None = None,
    publish_artifact_id: str | None = None,
    dry_run: bool = False,
    title: str | None = None,
    published_url: str | None = None,
    canonical_url: str | None = None,
    publish_target: str | None = None,
    external_reference: str | None = None,
    external_refs: list[dict] | None = None,
    metadata: dict | None = None,
    published_at: str | None = None,
) -> dict:
    """创建或更新公众号 article ledger 主记录。"""
    app: AppContext = ctx.request_context.lifespan_context

    validation_error = validate_wechat_article_payload(
        account=account,
        run_id=run_id,
        status=status,
        topic_id=topic_id,
        draft_artifact_id=draft_artifact_id,
        published_artifact_id=published_artifact_id,
        publish_artifact_id=publish_artifact_id,
        published_url=published_url,
        canonical_url=canonical_url,
        external_reference=external_reference,
    )
    if validation_error:
        return validation_error
    ref_error = validate_wechat_article_ref_payload(refs=external_refs or [], patch=None) if external_refs else None
    if ref_error:
        return ref_error
    parsed_topic_id, topic_error = validate_optional_uuid(topic_id, "topic_id")
    if topic_error:
        return topic_error
    idempotency_key, key_error = derive_publication_idempotency_key(
        account=account,
        publication_idempotency_key=publication_idempotency_key,
        publish_target=publish_target,
        canonical_url=canonical_url,
        external_reference=external_reference,
        run_id=run_id,
        publish_artifact_id=publish_artifact_id,
        published_artifact_id=published_artifact_id,
    )
    if key_error:
        return key_error

    try:
        article, created = await wechat_article_repo.upsert_article(
            app.pool,
            publication_idempotency_key=idempotency_key,
            account=account,
            topic_id=parsed_topic_id,
            run_id=run_id,
            task_id=task_id,
            draft_artifact_id=draft_artifact_id,
            published_artifact_id=published_artifact_id,
            publish_artifact_id=publish_artifact_id,
            status=status,
            dry_run=dry_run,
            title=title,
            published_url=published_url,
            canonical_url=canonical_url,
            publish_target=publish_target,
            external_reference=external_reference,
            metadata=metadata,
            published_at=_parse_datetime(published_at),
        )
        if external_refs:
            patched_article, refs = await wechat_article_repo.patch_article_refs_and_summary(
                app.pool,
                article_id=article["article_id"],
                refs=external_refs,
                patch=None,
            )
            article = patched_article or article
        else:
            refs = []
    except ValueError as exc:
        if str(exc) == "external_ref_conflict":
            return error("conflict", field="external_ref")
        return error("invalid_field", details={"message": str(exc)})
    except Exception as exc:
        return _map_db_error(exc)

    return {
        **_serialize_article(article),
        "created": created,
        "external_refs": [_serialize_ref(row) for row in refs],
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_wechat_articles(
    ctx: Context,
    account: str | None = None,
    topic_id: str | None = None,
    run_id: str | None = None,
    status: str | None = None,
    publish_target: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = DEFAULT_WECHAT_ARTICLE_LIMIT,
    offset: int = 0,
) -> dict:
    """按 account/topic/run/status/date 查询公众号 article 摘要。"""
    app: AppContext = ctx.request_context.lifespan_context
    explicit_limit = limit != DEFAULT_WECHAT_ARTICLE_LIMIT
    validation_error = validate_wechat_article_query(
        account=account,
        topic_id=topic_id,
        run_id=run_id,
        status=status,
        publish_target=publish_target,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        explicit_limit=explicit_limit,
    )
    if validation_error:
        return validation_error
    parsed_topic_id, topic_error = validate_optional_uuid(topic_id, "topic_id")
    if topic_error:
        return topic_error

    try:
        rows = await wechat_article_repo.list_articles(
            app.pool,
            account=account,
            topic_id=parsed_topic_id,
            run_id=run_id,
            status=status,
            publish_target=publish_target,
            date_from=_parse_datetime(date_from),
            date_to=_parse_datetime(date_to),
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        return _map_db_error(exc)
    return {"items": [_serialize_article(row) for row in rows], "limit": limit, "offset": offset}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def get_wechat_article(article_id: str, ctx: Context) -> dict:
    """读取一条 article ledger 详情和外部引用列表，不返回 artifact 正文。"""
    app: AppContext = ctx.request_context.lifespan_context
    parsed_article_id, article_error = validate_optional_uuid(article_id, "article_id")
    if article_error or parsed_article_id is None:
        return article_error or error("missing_required_field", field="article_id")

    try:
        article = await wechat_article_repo.get_article(app.pool, article_id=parsed_article_id)
        if article is None:
            return error("not_found", field="article_id", details={"article_id": article_id})
        refs = await wechat_article_repo.list_article_refs(app.pool, article_id=parsed_article_id)
    except Exception as exc:
        return _map_db_error(exc)
    return {**_serialize_article(article), "external_refs": [_serialize_ref(row) for row in refs]}


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def update_wechat_article_external_refs(
    article_id: str,
    ctx: Context,
    refs: list[dict] | None = None,
    patch: dict | None = None,
) -> dict:
    """补写或修复 article 外部引用，并可 patch 少量 article 摘要字段。"""
    app: AppContext = ctx.request_context.lifespan_context
    parsed_article_id, article_error = validate_optional_uuid(article_id, "article_id")
    if article_error or parsed_article_id is None:
        return article_error or error("missing_required_field", field="article_id")
    validation_error = validate_wechat_article_ref_payload(refs=refs or [], patch=patch or {})
    if validation_error:
        return validation_error

    try:
        article, ref_rows = await wechat_article_repo.patch_article_refs_and_summary(
            app.pool,
            article_id=parsed_article_id,
            refs=refs,
            patch=patch,
        )
    except ValueError as exc:
        if str(exc) == "external_ref_conflict":
            return error("conflict", field="external_ref")
        return error("invalid_field", details={"message": str(exc)})
    except Exception as exc:
        return _map_db_error(exc)
    if article is None:
        return error("not_found", field="article_id", details={"article_id": article_id})
    return {
        **_serialize_article(article),
        "external_refs": [_serialize_ref(row) for row in ref_rows],
    }
