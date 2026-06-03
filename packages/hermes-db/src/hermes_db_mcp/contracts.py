"""
Topic 写接口契约、常量、校验 helper 和结构化结果模型。

本模块定义:
- 字段白名单和可清空字段集合
- priority/resonance 合法值
- 结构化成功结果和错误模型
- 通用校验 helper
"""

from typing import TypedDict, NotRequired
from uuid import UUID


# ============================================================================
# Constants - Field Whitelists
# ============================================================================

# 可通过单条更新接口编辑的字段
EDITABLE_TOPIC_FIELDS = frozenset(
    [
        "title",
        "angle",
        "priority",
        "column_name",
        "resonance",
        "content",
        "revisit_of",
        "mother_theme",
    ]
)

# 可通过批量更新接口编辑的运营字段(不触发 embedding)
BULK_TOPIC_FIELDS = frozenset(
    [
        "priority",
        "resonance",
        "column_name",
    ]
)

# 可通过 clear_fields 清空的 nullable 字段
CLEARABLE_TOPIC_FIELDS = frozenset(
    [
        "angle",
        "column_name",
        "resonance",
        "content",
        "revisit_of",
        "mother_theme",
    ]
)

# Priority 合法值
VALID_PRIORITIES = frozenset(["A", "B", "C"])

# Resonance 合法值
VALID_RESONANCES = frozenset(["高", "中", "低"])

# 批量更新上限
MAX_BATCH_SIZE = 100
MAX_WORKFLOW_INLINE_CONTENT_BYTES = 256 * 1024
DEFAULT_WORKFLOW_ARTIFACT_LIMIT = 50
MAX_WORKFLOW_ARTIFACT_LIMIT = 200
DEFAULT_WECHAT_ARTICLE_LIMIT = 50
MAX_WECHAT_ARTICLE_LIMIT = 200
MAX_WECHAT_ARTICLE_REF_LENGTH = 2048

WECHAT_ARTICLE_STATUSES = frozenset(
    [
        "drafted",
        "published",
        "published_missing_url",
        "publish_reference_missing",
        "archived",
    ]
)

WECHAT_ARTICLE_REF_TYPES = frozenset(
    [
        "published_url",
        "canonical_url",
        "wechat_msg_id",
        "wechat_biz_mid_idx_sn",
        "youmind_ref",
        "publish_target_ref",
        "manual_repair",
        "external_reference",
    ]
)

WECHAT_ARTICLE_PATCH_FIELDS = frozenset(
    [
        "published_url",
        "canonical_url",
        "external_reference",
        "status",
        "published_at",
        "metadata",
    ]
)


# ============================================================================
# Structured Result Models
# ============================================================================


class TopicUpdateResult(TypedDict):
    """单条 topic 更新成功结果"""

    id: str
    updated_fields: list[str]
    embedding_regenerated: bool
    embedding_pending: NotRequired[bool]
    updated_at: str


class BatchTopicUpdateResult(TypedDict):
    """批量 topic 更新成功结果"""

    requested_count: int
    unique_count: int
    matched: int
    updated: int
    updated_fields: list[str]
    not_found_ids: list[str]


class TopicListResult(TypedDict):
    """Topic 列表结果"""

    items: list[dict]
    total: int


class RevisitChainItem(TypedDict):
    """revisit_of 祖先链条目"""

    id: str
    title: str
    status: str
    created_at: str
    published_url: str | None


class RevisitChainResult(TypedDict):
    """revisit_of 祖先链查询结果"""

    items: list[RevisitChainItem]
    truncated: bool


class ToolError(TypedDict):
    """工具错误结果"""

    error: str
    message: NotRequired[str]
    field: NotRequired[str]
    details: NotRequired[dict]


# ============================================================================
# Error Codes
# ============================================================================

ERROR_CODES = {
    # 输入校验错误
    "missing_required_field": "缺少必填字段",
    "invalid_field": "字段值不合法",
    "field_too_long": "字段超长",
    "invalid_uuid": "UUID 格式错误",
    "no_fields_to_update": "未提供任何可更新字段",
    "invalid_clear_field": "不可清空的字段",
    "batch_size_exceeded": "批量更新超限",
    "empty_ids": "批量 ids 为空",
    # 数据状态错误
    "not_found": "记录不存在",
    "invalid_revisit_of_self": "revisit_of 不能指向自身",
    "revisit_target_not_found": "revisit_of 指向的 topic 不存在",
    "invalid_transition": "状态流转不合法",
    # 系统错误
    "embedding_unavailable": "embedding 服务不可用",
    "database_error": "数据库错误",
    # workflow persistence
    "content_too_large": "正文超过 inline 存储上限",
    "content_missing": "content_text 和 content_ref 至少需要一个",
    "artifact_id_conflict": "artifact_id 已存在但内容 hash 不一致",
    "schema_drift": "数据库 schema 未满足工具要求",
    "invalid_filter": "查询过滤条件不合法",
    # wechat article ledger
    "conflict": "记录冲突",
}


# ============================================================================
# Validation Helpers
# ============================================================================


def validate_priority(priority: str | None) -> ToolError | None:
    """校验 priority 字段"""
    if priority is not None and priority not in VALID_PRIORITIES:
        return {
            "error": "invalid_field",
            "field": "priority",
            "message": f"priority 必须是 {', '.join(VALID_PRIORITIES)} 之一",
            "details": {"valid_values": list(VALID_PRIORITIES)},
        }
    return None


def validate_resonance(resonance: str | None) -> ToolError | None:
    """校验 resonance 字段"""
    if resonance is not None and resonance not in VALID_RESONANCES:
        return {
            "error": "invalid_field",
            "field": "resonance",
            "message": f"resonance 必须是 {', '.join(VALID_RESONANCES)} 之一",
            "details": {"valid_values": list(VALID_RESONANCES)},
        }
    return None


def validate_title(title: str | None) -> ToolError | None:
    """校验 title 字段"""
    if title is not None:
        if not title or not title.strip():
            return {
                "error": "invalid_field",
                "field": "title",
                "message": "title 不能为空",
            }
        if len(title) > 200:
            return {
                "error": "field_too_long",
                "field": "title",
                "message": "title 超过 200 字符",
                "details": {"max_length": 200, "actual_length": len(title)},
            }
    return None


def validate_clear_fields(clear_fields: list[str] | None) -> ToolError | None:
    """校验 clear_fields 参数"""
    if clear_fields:
        invalid = set(clear_fields) - CLEARABLE_TOPIC_FIELDS
        if invalid:
            return {
                "error": "invalid_clear_field",
                "message": f"以下字段不可清空: {', '.join(invalid)}",
                "details": {
                    "invalid_fields": list(invalid),
                    "clearable_fields": list(CLEARABLE_TOPIC_FIELDS),
                },
            }
    return None


def validate_batch_ids(ids: list[str]) -> tuple[list[UUID], ToolError | None]:
    """
    校验批量 ids 参数

    Returns:
        (parsed_uuids, error)
        - 成功: (去重后的 UUID 列表, None)
        - 失败: ([], ToolError)
    """
    if not ids:
        return [], {
            "error": "empty_ids",
            "message": "批量 ids 不能为空",
        }

    if len(ids) > MAX_BATCH_SIZE:
        return [], {
            "error": "batch_size_exceeded",
            "message": f"批量更新超限,最多 {MAX_BATCH_SIZE} 条",
            "details": {
                "max_size": MAX_BATCH_SIZE,
                "requested": len(ids),
            },
        }

    # 解析并去重
    parsed = []
    seen = set()
    for id_str in ids:
        try:
            uuid_obj = UUID(id_str)
            if uuid_obj not in seen:
                parsed.append(uuid_obj)
                seen.add(uuid_obj)
        except (ValueError, AttributeError):
            return [], {
                "error": "invalid_uuid",
                "message": f"非法 UUID: {id_str}",
                "field": "ids",
            }

    return parsed, None


def validate_pagination(limit: int, offset: int) -> ToolError | None:
    """校验分页参数"""
    if limit < 1 or limit > 100:
        return {
            "error": "invalid_field",
            "field": "limit",
            "message": "limit 必须在 1-100 之间",
            "details": {"min": 1, "max": 100, "actual": limit},
        }
    if offset < 0:
        return {
            "error": "invalid_field",
            "field": "offset",
            "message": "offset 不能为负数",
            "details": {"actual": offset},
        }
    return None


def validate_required_text(value: str | None, field: str) -> ToolError | None:
    if value is None or not str(value).strip():
        return error("missing_required_field", field=field)
    return None


def validate_optional_uuid(value: str | None, field: str) -> tuple[UUID | None, ToolError | None]:
    if value is None:
        return None, None
    try:
        return UUID(value), None
    except (ValueError, AttributeError):
        return None, error("invalid_uuid", field=field, details={"value": value})


def validate_workflow_run_payload(
    *,
    run_id: str | None,
    phase: str | None,
    status: str | None,
) -> ToolError | None:
    for field, value in (
        ("run_id", run_id),
        ("phase", phase),
        ("status", status),
    ):
        err = validate_required_text(value, field)
        if err:
            return err
    return None


def validate_finish_workflow_run_payload(
    *,
    run_id: str | None,
    phase: str | None,
    status: str | None,
) -> ToolError | None:
    return validate_workflow_run_payload(run_id=run_id, phase=phase, status=status)


def validate_workflow_artifact_payload(
    *,
    run_id: str | None,
    stage: str | None,
    type: str | None,
    name: str | None,
    content_hash: str | None,
    content_size_bytes: int | None,
    content_text: str | None,
    content_ref: str | None,
    topic_id: str | None = None,
    parent_artifact_id: str | None = None,
) -> ToolError | None:
    for field, value in (
        ("run_id", run_id),
        ("stage", stage),
        ("type", type),
        ("name", name),
        ("content_hash", content_hash),
    ):
        err = validate_required_text(value, field)
        if err:
            return err

    if content_size_bytes is None or content_size_bytes < 0:
        return error(
            "invalid_field",
            field="content_size_bytes",
            details={"actual": content_size_bytes},
        )
    if content_text is None and content_ref is None:
        return error("content_missing")
    if content_text is not None:
        size = len(content_text.encode("utf-8"))
        if size > MAX_WORKFLOW_INLINE_CONTENT_BYTES:
            return error(
                "content_too_large",
                field="content_text",
                details={
                    "max_bytes": MAX_WORKFLOW_INLINE_CONTENT_BYTES,
                    "actual_bytes": size,
                },
            )
        if "\x00" in content_text:
            return error("invalid_field", field="content_text")

    _, topic_err = validate_optional_uuid(topic_id, "topic_id")
    if topic_err:
        return topic_err
    if parent_artifact_id is not None and not parent_artifact_id.strip():
        return error("invalid_field", field="parent_artifact_id")
    return None


def validate_workflow_artifact_query(
    *,
    run_id: str | None = None,
    topic_id: str | None = None,
    account: str | None = None,
    type: str | None = None,
    stage: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = DEFAULT_WORKFLOW_ARTIFACT_LIMIT,
    offset: int = 0,
    explicit_limit: bool = False,
) -> ToolError | None:
    filters = [run_id, topic_id, account, type, stage, date_from, date_to]
    if not any(value is not None for value in filters) and not explicit_limit:
        return error("invalid_filter", details={"reason": "filter_or_explicit_limit_required"})
    if limit < 1 or limit > MAX_WORKFLOW_ARTIFACT_LIMIT:
        return error(
            "invalid_field",
            field="limit",
            details={"min": 1, "max": MAX_WORKFLOW_ARTIFACT_LIMIT, "actual": limit},
        )
    if offset < 0:
        return error("invalid_field", field="offset", details={"actual": offset})
    _, topic_err = validate_optional_uuid(topic_id, "topic_id")
    return topic_err


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def derive_publication_idempotency_key(
    *,
    account: str | None,
    publication_idempotency_key: str | None = None,
    publish_target: str | None = None,
    canonical_url: str | None = None,
    external_reference: str | None = None,
    run_id: str | None = None,
    publish_artifact_id: str | None = None,
    published_artifact_id: str | None = None,
) -> tuple[str | None, ToolError | None]:
    explicit_key = _clean_text(publication_idempotency_key)
    if explicit_key:
        return explicit_key, None

    account = _clean_text(account)
    if not account:
        return None, error("missing_required_field", field="account")

    publish_target = _clean_text(publish_target) or "default"
    canonical_url = _clean_text(canonical_url)
    external_reference = _clean_text(external_reference)
    run_id = _clean_text(run_id)
    publish_artifact_id = _clean_text(publish_artifact_id)
    published_artifact_id = _clean_text(published_artifact_id)

    if canonical_url:
        return f"{account}:{publish_target}:canonical_url:{canonical_url}", None
    if external_reference:
        return f"{account}:{publish_target}:external_reference:{external_reference}", None
    if run_id and publish_artifact_id:
        return f"{account}:run:{run_id}:publish_artifact:{publish_artifact_id}", None
    if run_id and published_artifact_id:
        return f"{account}:run:{run_id}:published_artifact:{published_artifact_id}", None
    return None, error("missing_required_field", field="publication_idempotency_key")


def validate_wechat_article_payload(
    *,
    account: str | None,
    run_id: str | None,
    status: str | None,
    topic_id: str | None = None,
    draft_artifact_id: str | None = None,
    published_artifact_id: str | None = None,
    publish_artifact_id: str | None = None,
    published_url: str | None = None,
    canonical_url: str | None = None,
    external_reference: str | None = None,
) -> ToolError | None:
    for field, value in (
        ("account", account),
        ("run_id", run_id),
        ("status", status),
    ):
        err = validate_required_text(value, field)
        if err:
            return err

    if status not in WECHAT_ARTICLE_STATUSES:
        return error(
            "invalid_field",
            field="status",
            details={"valid_values": sorted(WECHAT_ARTICLE_STATUSES), "actual": status},
        )

    for field, value in (
        ("topic_id", topic_id),
    ):
        _, uuid_err = validate_optional_uuid(value, field)
        if uuid_err:
            return uuid_err

    for field, value in (
        ("draft_artifact_id", draft_artifact_id),
        ("published_artifact_id", published_artifact_id),
        ("publish_artifact_id", publish_artifact_id),
    ):
        if value is not None and not str(value).strip():
            return error("invalid_field", field=field)

    refs = [
        _clean_text(published_url),
        _clean_text(canonical_url),
        _clean_text(external_reference),
    ]
    if status == "published" and not any(refs):
        return error(
            "invalid_field",
            field="published_url",
            details={"reason": "published_requires_url_or_reference"},
        )
    if status == "published_missing_url" and not _clean_text(external_reference):
        return error(
            "invalid_field",
            field="external_reference",
            details={"reason": "published_missing_url_requires_reference"},
        )
    return None


def validate_wechat_article_query(
    *,
    account: str | None = None,
    topic_id: str | None = None,
    run_id: str | None = None,
    status: str | None = None,
    publish_target: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = DEFAULT_WECHAT_ARTICLE_LIMIT,
    offset: int = 0,
    explicit_limit: bool = False,
) -> ToolError | None:
    filters = [account, topic_id, run_id, status, publish_target, date_from, date_to]
    if not any(value is not None for value in filters) and not explicit_limit:
        return error("invalid_filter", details={"reason": "filter_or_explicit_limit_required"})
    if status is not None and status not in WECHAT_ARTICLE_STATUSES:
        return error(
            "invalid_field",
            field="status",
            details={"valid_values": sorted(WECHAT_ARTICLE_STATUSES), "actual": status},
        )
    if limit < 1 or limit > MAX_WECHAT_ARTICLE_LIMIT:
        return error(
            "invalid_field",
            field="limit",
            details={"min": 1, "max": MAX_WECHAT_ARTICLE_LIMIT, "actual": limit},
        )
    if offset < 0:
        return error("invalid_field", field="offset", details={"actual": offset})
    _, topic_err = validate_optional_uuid(topic_id, "topic_id")
    return topic_err


def validate_wechat_article_ref_payload(
    *,
    refs: list[dict] | None = None,
    patch: dict | None = None,
) -> ToolError | None:
    refs = refs or []
    patch = patch or {}
    if not refs and not patch:
        return error("missing_required_field", field="refs")

    invalid_patch_fields = set(patch) - WECHAT_ARTICLE_PATCH_FIELDS
    if invalid_patch_fields:
        return error(
            "invalid_field",
            field="patch",
            details={"invalid_fields": sorted(invalid_patch_fields)},
        )
    if "status" in patch and patch["status"] not in WECHAT_ARTICLE_STATUSES:
        return error(
            "invalid_field",
            field="status",
            details={"valid_values": sorted(WECHAT_ARTICLE_STATUSES), "actual": patch["status"]},
        )

    for idx, ref in enumerate(refs):
        ref_type = ref.get("ref_type")
        ref_value = _clean_text(ref.get("ref_value"))
        if ref_type not in WECHAT_ARTICLE_REF_TYPES:
            return error(
                "invalid_field",
                field=f"refs[{idx}].ref_type",
                details={"valid_values": sorted(WECHAT_ARTICLE_REF_TYPES), "actual": ref_type},
            )
        if not ref_value:
            return error("missing_required_field", field=f"refs[{idx}].ref_value")
        if len(ref_value) > MAX_WECHAT_ARTICLE_REF_LENGTH:
            return error(
                "field_too_long",
                field=f"refs[{idx}].ref_value",
                details={
                    "max_length": MAX_WECHAT_ARTICLE_REF_LENGTH,
                    "actual_length": len(ref_value),
                },
            )
    return None


def error(
    code: str, field: str | None = None, details: dict | None = None
) -> ToolError:
    """
    构造标准错误结果

    Args:
        code: 错误码,必须在 ERROR_CODES 中
        field: 可选,关联字段名
        details: 可选,额外错误详情
    """
    result: ToolError = {
        "error": code,
        "message": ERROR_CODES.get(code, "未知错误"),
    }
    if field:
        result["field"] = field
    if details:
        result["details"] = details
    return result
