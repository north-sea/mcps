from uuid import uuid4

from hermes_db_mcp.contracts import (
    DEFAULT_WECHAT_ANALYTICS_LIMIT,
    WECHAT_ANALYTICS_SOURCES,
    validate_wechat_analytics_bulk_payload,
    validate_wechat_channel_metric,
    validate_wechat_metric_query,
    validate_wechat_metric_record,
)


def metric_record(**overrides):
    record = {
        "article_id": str(uuid4()),
        "stat_date": "2026-04-13",
        "window_label": "D+1",
        "read_user_count": 2682,
        "average_stay_seconds": 68.5,
        "completion_rate": 0.36,
        "missing_fields": [],
        "raw_json": {},
    }
    record.update(overrides)
    return record


def channel_metric(**overrides):
    record = {
        "article_id": str(uuid4()),
        "metric_date": "2026-04-13",
        "channel": "全部",
        "read_user_count": 2682,
        "share_user_count": 12,
        "raw_json": {},
    }
    record.update(overrides)
    return record


def test_wechat_analytics_sources_cover_expected_import_modes():
    assert {
        "manual_json",
        "manual_csv",
        "manual_xls",
        "wechat_api",
        "browser_automation",
        "manual_patch",
    }.issubset(WECHAT_ANALYTICS_SOURCES)


def test_validate_wechat_metric_record_accepts_valid_record():
    err = validate_wechat_metric_record(metric_record(), source="manual_json")

    assert err is None


def test_validate_wechat_metric_record_accepts_stable_url_reference():
    err = validate_wechat_metric_record(
        metric_record(article_id=None, canonical_url="https://mp.weixin.qq.com/s/abc"),
        source="manual_json",
    )

    assert err is None


def test_validate_wechat_metric_record_requires_article_resolution_fact():
    err = validate_wechat_metric_record(
        metric_record(article_id=None),
        source="manual_json",
    )

    assert err["error"] == "missing_required_field"
    assert err["field"] == "article_id"


def test_validate_wechat_metric_record_rejects_bad_date():
    err = validate_wechat_metric_record(
        metric_record(stat_date="2026-99-99"),
        source="manual_json",
    )

    assert err["error"] == "invalid_field"
    assert err["field"] == "stat_date"


def test_validate_wechat_metric_record_rejects_negative_count():
    err = validate_wechat_metric_record(
        metric_record(read_user_count=-1),
        source="manual_json",
    )

    assert err["error"] == "invalid_field"
    assert err["field"] == "read_user_count"


def test_validate_wechat_metric_record_rejects_completion_rate_outside_zero_one():
    err = validate_wechat_metric_record(
        metric_record(completion_rate=1.2),
        source="manual_json",
    )

    assert err["error"] == "invalid_field"
    assert err["field"] == "completion_rate"


def test_validate_wechat_metric_record_rejects_unknown_source():
    err = validate_wechat_metric_record(
        metric_record(),
        source="unknown",
    )

    assert err["error"] == "invalid_field"
    assert err["field"] == "source"


def test_validate_wechat_channel_metric_accepts_total_channel():
    err = validate_wechat_channel_metric(channel_metric(), source="manual_csv")

    assert err is None


def test_validate_wechat_channel_metric_rejects_bad_metric_date():
    err = validate_wechat_channel_metric(
        channel_metric(metric_date="bad"),
        source="manual_csv",
    )

    assert err["error"] == "invalid_field"
    assert err["field"] == "metric_date"


def test_validate_wechat_channel_metric_rejects_negative_count():
    err = validate_wechat_channel_metric(
        channel_metric(share_user_count=-1),
        source="manual_csv",
    )

    assert err["error"] == "invalid_field"
    assert err["field"] == "share_user_count"


def test_validate_wechat_analytics_bulk_payload_accepts_valid_payload():
    summary, err = validate_wechat_analytics_bulk_payload(
        account="acct",
        source="manual_json",
        records=[metric_record()],
        channel_daily_metrics=[channel_metric()],
        import_metadata={"filename": "sample.json"},
    )

    assert err is None
    assert summary["audience_profiles_skipped"] == 0


def test_validate_wechat_analytics_bulk_payload_rejects_empty_records():
    summary, err = validate_wechat_analytics_bulk_payload(
        account="acct",
        source="manual_json",
        records=[],
    )

    assert summary["audience_profiles_skipped"] == 0
    assert err["error"] == "missing_required_field"
    assert err["field"] == "records"


def test_validate_wechat_analytics_bulk_payload_marks_audience_profiles_skipped():
    summary, err = validate_wechat_analytics_bulk_payload(
        account="acct",
        source="manual_json",
        records=[metric_record()],
        audience_profiles=[{"dimension": "gender", "bucket": "male", "ratio": 0.5}],
    )

    assert err is None
    assert summary["audience_profiles_skipped"] == 1
    assert summary["skip_reasons"] == ["audience_profiles_not_supported_in_mvp"]


def test_validate_wechat_analytics_bulk_payload_prefixes_record_errors():
    _summary, err = validate_wechat_analytics_bulk_payload(
        account="acct",
        source="manual_json",
        records=[metric_record(completion_rate=2)],
    )

    assert err["error"] == "invalid_field"
    assert err["field"] == "records[0].completion_rate"


def test_validate_wechat_metric_query_requires_filter_or_explicit_limit():
    err = validate_wechat_metric_query(limit=DEFAULT_WECHAT_ANALYTICS_LIMIT)

    assert err["error"] == "invalid_filter"


def test_validate_wechat_metric_query_accepts_bounded_query():
    err = validate_wechat_metric_query(
        account="acct",
        article_id=str(uuid4()),
        date_from="2026-04-13",
        date_to="2026-04-20",
        window_label="D+1",
        include_raw=True,
    )

    assert err is None


def test_validate_wechat_metric_query_rejects_invalid_article_id():
    err = validate_wechat_metric_query(article_id="not-a-uuid")

    assert err["error"] == "invalid_uuid"
    assert err["field"] == "article_id"


def test_validate_wechat_metric_query_rejects_invalid_date_range():
    err = validate_wechat_metric_query(
        account="acct",
        date_from="2026-04-20",
        date_to="2026-04-13",
    )

    assert err["error"] == "invalid_filter"
    assert err["field"] == "date_from"


def test_validate_wechat_metric_query_rejects_unbounded_limit():
    err = validate_wechat_metric_query(account="acct", limit=10_000)

    assert err["error"] == "invalid_field"
    assert err["field"] == "limit"
