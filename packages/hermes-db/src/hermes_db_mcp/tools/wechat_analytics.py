from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import asyncpg
from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from hermes_db_mcp.contracts import (
    DEFAULT_WECHAT_ANALYTICS_LIMIT,
    error,
    validate_optional_uuid,
    validate_wechat_analytics_bulk_payload,
    validate_wechat_metric_query,
)
from hermes_db_mcp.repositories import wechat_analytics_repo
from hermes_db_mcp.server import AppContext, mcp


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(value)


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _serialize_value(value):
    if isinstance(value, (UUID, date, datetime)):
        return str(value)
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def _serialize_snapshot(row: dict, *, include_raw: bool = False) -> dict:
    result = {key: _serialize_value(value) for key, value in dict(row).items()}
    if not include_raw:
        result.pop("raw_json", None)
    return result


def _map_db_error(exc: Exception) -> dict:
    if isinstance(exc, asyncpg.ForeignKeyViolationError):
        constraint = getattr(exc, "constraint_name", "") or ""
        field = "article_id" if "article" in constraint else "reference"
        return error("not_found", field=field, details={"constraint": constraint})
    if isinstance(exc, asyncpg.UniqueViolationError):
        return error("conflict", details={"message": str(exc)})
    if isinstance(exc, (asyncpg.UndefinedTableError, asyncpg.UndefinedColumnError)):
        return error("schema_drift", details={"message": str(exc)})
    return error("database_error", details={"message": str(exc)})


def _article_lookup_fields(record: dict) -> dict:
    article_id = record.get("article_id")
    parsed_article_id = None
    if article_id:
        parsed_article_id = UUID(str(article_id))
    return {
        "article_id": parsed_article_id,
        "published_url": record.get("published_url"),
        "canonical_url": record.get("canonical_url"),
        "external_reference": record.get("external_reference"),
        "ref_type": record.get("ref_type"),
        "ref_value": record.get("ref_value"),
    }


def _snapshot_repo_row(record: dict, *, account: str, source: str, article_id: UUID) -> dict:
    row = dict(record)
    row["article_id"] = article_id
    row["account"] = account
    row["source"] = record.get("source") or source
    row["stat_date"] = _parse_date(record["stat_date"])
    row["collected_at"] = _parse_datetime(record.get("collected_at"))
    return row


def _channel_repo_row(record: dict, *, account: str, source: str, article_id: UUID) -> dict:
    row = dict(record)
    row["article_id"] = article_id
    row["account"] = account
    row["source"] = record.get("source") or source
    row["metric_date"] = _parse_date(record["metric_date"])
    return row


async def _resolve_record_article(pool, *, account: str, record: dict, index: int) -> tuple[UUID | None, dict | None]:
    resolution = await wechat_analytics_repo.resolve_article(
        pool,
        account=account,
        **_article_lookup_fields(record),
    )
    if resolution["status"] == "matched":
        return resolution["article"]["article_id"], None
    if resolution["status"] == "ambiguous":
        return None, {
            "index": index,
            "error": "ambiguous_article",
            "matches": [_serialize_value(item) for item in resolution.get("items", [])],
        }
    return None, {"index": index, "record": _serialize_value(record)}


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
)
async def bulk_upsert_wechat_article_metric_snapshots(
    account: str,
    source: str,
    records: list[dict],
    ctx: Context,
    dry_run: bool = False,
    channel_daily_metrics: list[dict] | None = None,
    audience_profiles: list[dict] | None = None,
    import_metadata: dict | None = None,
) -> dict:
    """批量导入公众号文章指标快照和渠道日明细。"""
    app: AppContext = ctx.request_context.lifespan_context

    validation_summary, validation_error = validate_wechat_analytics_bulk_payload(
        account=account,
        source=source,
        records=records,
        channel_daily_metrics=channel_daily_metrics,
        audience_profiles=audience_profiles,
        import_metadata=import_metadata,
    )
    if validation_error:
        return validation_error

    snapshot_rows = []
    channel_rows = []
    unmatched = []
    row_errors = []
    article_cache: dict[tuple, UUID] = {}

    try:
        for idx, record in enumerate(records):
            cache_key = tuple(sorted((key, str(value)) for key, value in _article_lookup_fields(record).items() if value))
            article_id = article_cache.get(cache_key)
            issue = None
            if article_id is None:
                article_id, issue = await _resolve_record_article(app.pool, account=account, record=record, index=idx)
                if article_id is not None:
                    article_cache[cache_key] = article_id
            if issue:
                if issue.get("error") == "ambiguous_article":
                    row_errors.append(issue)
                else:
                    unmatched.append(issue)
                continue
            snapshot_rows.append(
                _snapshot_repo_row(record, account=account, source=source, article_id=article_id)
            )

        for idx, record in enumerate(channel_daily_metrics or []):
            cache_key = tuple(sorted((key, str(value)) for key, value in _article_lookup_fields(record).items() if value))
            article_id = article_cache.get(cache_key)
            issue = None
            if article_id is None:
                article_id, issue = await _resolve_record_article(app.pool, account=account, record=record, index=idx)
                if article_id is not None:
                    article_cache[cache_key] = article_id
            if issue:
                if issue.get("error") == "ambiguous_article":
                    row_errors.append({"channel_index": idx, **issue})
                else:
                    unmatched.append({"channel_index": idx, **issue})
                continue
            channel_rows.append(
                _channel_repo_row(record, account=account, source=source, article_id=article_id)
            )
    except Exception as exc:
        return _map_db_error(exc)

    skipped = validation_summary["audience_profiles_skipped"]
    if validation_summary["skip_reasons"]:
        row_errors.append(
            {
                "error": "skipped",
                "reasons": validation_summary["skip_reasons"],
                "count": skipped,
            }
        )

    status = "completed"
    if unmatched or row_errors or skipped:
        status = "completed_with_errors"

    if dry_run:
        return {
            "import_run_id": None,
            "total_rows": len(records),
            "created": 0,
            "updated": 0,
            "skipped": skipped,
            "unmatched": unmatched,
            "errors": row_errors,
            "status": "dry_run",
        }

    try:
        result = await wechat_analytics_repo.run_import_transaction(
            app.pool,
            account=account,
            source=source,
            snapshot_rows=snapshot_rows,
            channel_rows=channel_rows,
            skipped=skipped,
            unmatched=unmatched,
            errors=row_errors,
            metadata=import_metadata or {},
        )
    except Exception as exc:
        return _map_db_error(exc)

    return {
        "import_run_id": _serialize_value(result["import_run_id"]),
        "total_rows": len(records),
        "created": result["created"],
        "updated": result["updated"],
        "skipped": skipped,
        "unmatched": unmatched,
        "errors": row_errors,
        "status": status,
    }


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
async def list_wechat_article_metric_snapshots(
    ctx: Context,
    account: str | None = None,
    article_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    window_label: str | None = None,
    limit: int = DEFAULT_WECHAT_ANALYTICS_LIMIT,
    offset: int = 0,
    include_raw: bool = False,
) -> dict:
    """按 account/article/date/window 查询公众号文章指标快照。"""
    app: AppContext = ctx.request_context.lifespan_context
    explicit_limit = limit != DEFAULT_WECHAT_ANALYTICS_LIMIT
    validation_error = validate_wechat_metric_query(
        account=account,
        article_id=article_id,
        date_from=date_from,
        date_to=date_to,
        window_label=window_label,
        limit=limit,
        offset=offset,
        include_raw=include_raw,
        explicit_limit=explicit_limit,
    )
    if validation_error:
        return validation_error
    parsed_article_id, article_error = validate_optional_uuid(article_id, "article_id")
    if article_error:
        return article_error

    try:
        rows = await wechat_analytics_repo.list_metric_snapshots(
            app.pool,
            account=account,
            article_id=parsed_article_id,
            date_from=_parse_date(date_from),
            date_to=_parse_date(date_to),
            window_label=window_label,
            limit=limit,
            offset=offset,
            include_raw=include_raw,
        )
    except Exception as exc:
        return _map_db_error(exc)
    return {
        "items": [_serialize_snapshot(row, include_raw=include_raw) for row in rows],
        "limit": limit,
        "offset": offset,
    }
