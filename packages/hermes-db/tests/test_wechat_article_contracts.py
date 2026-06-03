from uuid import uuid4

from hermes_db_mcp.contracts import (
    DEFAULT_WECHAT_ARTICLE_LIMIT,
    derive_publication_idempotency_key,
    validate_wechat_article_payload,
    validate_wechat_article_query,
    validate_wechat_article_ref_payload,
)


def test_derive_publication_idempotency_key_prefers_explicit_key():
    key, err = derive_publication_idempotency_key(
        account="acct",
        publication_idempotency_key=" explicit ",
        canonical_url="https://example.com/a",
    )

    assert err is None
    assert key == "explicit"


def test_derive_publication_idempotency_key_uses_canonical_url_first():
    key, err = derive_publication_idempotency_key(
        account="acct",
        publish_target="wechat-mp",
        canonical_url="https://mp.weixin.qq.com/s/abc",
        external_reference="ref-1",
        run_id="run-1",
        publish_artifact_id="artifact-pub",
    )

    assert err is None
    assert key == "acct:wechat-mp:canonical_url:https://mp.weixin.qq.com/s/abc"


def test_derive_publication_idempotency_key_requires_a_stable_fact():
    key, err = derive_publication_idempotency_key(account="acct", run_id="run-1")

    assert key is None
    assert err["error"] == "missing_required_field"
    assert err["field"] == "publication_idempotency_key"


def test_validate_wechat_article_payload_accepts_published_with_reference():
    err = validate_wechat_article_payload(
        account="acct",
        run_id="run-1",
        status="published",
        topic_id=str(uuid4()),
        published_url="https://mp.weixin.qq.com/s/abc",
    )

    assert err is None


def test_validate_wechat_article_payload_rejects_published_without_reference():
    err = validate_wechat_article_payload(
        account="acct",
        run_id="run-1",
        status="published",
    )

    assert err["error"] == "invalid_field"
    assert err["field"] == "published_url"


def test_validate_wechat_article_payload_rejects_invalid_status():
    err = validate_wechat_article_payload(
        account="acct",
        run_id="run-1",
        status="unknown",
    )

    assert err["error"] == "invalid_field"
    assert err["field"] == "status"


def test_validate_wechat_article_query_requires_filter_or_explicit_limit():
    err = validate_wechat_article_query(limit=DEFAULT_WECHAT_ARTICLE_LIMIT)

    assert err["error"] == "invalid_filter"


def test_validate_wechat_article_query_accepts_explicit_bounded_limit():
    err = validate_wechat_article_query(limit=50, explicit_limit=True)

    assert err is None


def test_validate_wechat_article_query_rejects_invalid_topic_id():
    err = validate_wechat_article_query(topic_id="not-a-uuid")

    assert err["error"] == "invalid_uuid"
    assert err["field"] == "topic_id"


def test_validate_wechat_article_ref_payload_accepts_refs_and_patch():
    err = validate_wechat_article_ref_payload(
        refs=[
            {
                "ref_type": "canonical_url",
                "ref_value": "https://mp.weixin.qq.com/s/abc",
            }
        ],
        patch={"status": "published"},
    )

    assert err is None


def test_validate_wechat_article_ref_payload_rejects_empty_payload():
    err = validate_wechat_article_ref_payload(refs=[], patch={})

    assert err["error"] == "missing_required_field"
    assert err["field"] == "refs"


def test_validate_wechat_article_ref_payload_rejects_invalid_ref_type():
    err = validate_wechat_article_ref_payload(
        refs=[{"ref_type": "bad", "ref_value": "value"}],
    )

    assert err["error"] == "invalid_field"
    assert err["field"] == "refs[0].ref_type"
