# Implementation Plan: Hermes DB Topic Plan Contract

**Workspace**: `hermes-db-topic-plan-contract` | **Date**: 2026-07-01 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/hermes-db-topic-plan-contract/spec.md`

---

## Summary

Add a first-class `hermes.topic_plans` contract to hermes-db so WeChat topic planning can persist LLM-produced plans separately from raw topic candidates. The implementation should follow the existing topic candidate pattern: Alembic migration, repository functions, MCP tool wrappers, schema health inspection, and focused unit/SQL tests.

只有一个合理实现方向：复用当前 hermes-db 的 `topic_candidates` repo/tool/schema/health 风格。引入独立服务、workflow artifact 主存储或 agents-side shadow storage 都会破坏 spec 中的 MCP contract owner 边界。

---

## Architecture Overview

```text
agents/wechat-agent
  produces planning payload
        |
        v
hermes-db MCP tools
  upsert_topic_plan
  list_topic_plans
  get_topic_plan
  update_topic_plan_status
  get_topic_candidate(include_raw)
        |
        v
repository layer
  topic_plan_repo.py
  topic_candidate_repo.py extension
        |
        v
Postgres schema hermes
  topic_candidates
  topic_plans
```

The write path is intentionally synchronous and transactional. `upsert_topic_plan` owns the `topic_plans` insert/update and, when requested, the candidate `shortlisted` transition in the same database transaction. Candidate rejection remains owned by the existing `reject_topic_candidate` flow.

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| WeChat topic planning runtime | `TopicPlanInput` payload | `upsert_topic_plan` MCP tool | Tool test verifies planned and rejected payload validation plus repository call shape |
| `topic_plan_repo.upsert_topic_plan` | `TopicPlan` row / DTO | `list_topic_plans`, `get_topic_plan` | Repo SQL tests verify created/updated idempotency and returned fields |
| `upsert_topic_plan(mark_candidate_shortlisted=true)` | Candidate status transition | Existing candidate adoption/inbox workflow | Repo SQL test verifies same transaction updates candidate only for `status=planned` |
| `get_topic_candidate(include_raw=true)` | Candidate raw payload | WeChat planning runtime | Tool/repo tests verify `raw_payload` is present only when requested |
| Schema migration | `hermes.topic_plans` table, constraints, indexes | Health tool and repository queries | Migration text test and schema inspection test verify required objects |
| `update_topic_plan_status` | Consumed/rejected/archived lifecycle state | Article/topic creation or cleanup workflow | Tool/repo tests verify `previous_status`, `status`, and optional `topic_id` return |

**孤儿 artifact 处理**: `llm_metadata` and `evidence` are stored for traceability even if no current tool filters on them. They are not orphan workflow artifacts because they travel inside the consumed `TopicPlan` DTO.

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 原子性 | Plan upsert and candidate shortlist either both commit or both fail | Use one repository transaction for `upsert_topic_plan` and candidate update | Fake transaction test plus SQL shape assertion |
| 幂等性 | One active plan per candidate in MVP | Unique constraint on `candidate_id`; upsert by `candidate_id` | Duplicate upsert repo test returns `updated` instead of duplicate |
| 可恢复 | Invalid LLM/schema payload creates no side effect | Validate tool inputs before repository write | Tool validation tests for planned/rejected payloads |
| 可观测 | agents can gate on `health.capabilities.topic_plans` | Add schema inspector and health capability flag | `test_health.py` and topic plan schema health tests |
| 兼容性 | Existing topic candidate flows remain unchanged | Extend candidate raw read only; do not alter reject/adopt semantics | Existing topic candidate tests plus new include_raw regression |
| 查询性能 | Account/track/status listing has bounded indexes | Add account/status/created and account/track/status/created indexes | Migration text test and schema inspector |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001: `topic_plans` is first-class storage | Plan lifecycle must outlive candidate raw payload and be queryable by MCP | A: new table; B: embed in `topic_candidates.raw_payload`; C: workflow artifact only | Choose A | Adds migration/repo/tool surface | Existing `topic_candidates` and workflow artifact separation in repo |
| ADR-002: one plan per candidate for MVP | Spec requires MVP default one active plan per candidate | A: unique `candidate_id`; B: multiple plan versions | Choose A | No version history yet | Spec FR-002 |
| ADR-003: status controls handoff semantics | Planned/rejected/consumed/archived need deterministic behavior | A: constrained text enum; B: free-form status | Choose A | Migration required for new statuses | Existing status check constraints pattern |
| ADR-004: same transaction for plan write and shortlist | Avoid plan written but candidate not visible to downstream consumer | A: repository transaction; B: two MCP calls | Choose A | Repository implementation slightly larger | Spec NFR-001 |
| ADR-005: health capability is schema-based | agents need a write gate before using tools | A: inspect DB schema; B: static config flag | Choose A | More schema inspector tests | Existing health capability pattern |

---

## Key Design Decisions

### Decision 1: Follow the topic candidate module shape

- **背景**: hermes-db already has `topic_candidate_repo.py`, `tools/topic_candidates.py`, migration tests, and schema health inspection.
- **选项**:
  - A: Add `topic_plan_repo.py` and `tools/topic_plans.py` beside candidate modules.
  - B: Fold all plan behavior into `topic_candidate_repo.py`.
- **结论**: Choose A, with a minimal extension to `topic_candidate_repo.get_candidate(include_raw)`.
- **影响**: Keeps candidate lifecycle and plan lifecycle readable while preserving the existing candidate API.
- **来源**: Existing local files under `packages/hermes-db/src/hermes_db_mcp/`.

### Decision 2: Keep DTOs as plain dictionaries at the MCP boundary

- **背景**: Existing hermes-db MCP tools return dict envelopes and repository rows without introducing a separate DTO framework.
- **选项**:
  - A: Continue dict-based DTO normalization.
  - B: Add Pydantic models for this feature only.
- **结论**: Choose A. Validate required fields in tool/repo helpers and keep dependencies unchanged.
- **影响**: Less schema duplication now; more care needed in tests to pin field names.
- **来源**: Existing topic candidate and workflow tool style.

### Decision 3: Do not auto-reject candidates from rejected plans

- **背景**: Rejected plans may represent one planning attempt, while candidate rejection is a stronger workflow decision.
- **选项**:
  - A: `upsert_topic_plan(status=rejected)` only stores plan rejection.
  - B: Also call candidate rejection.
- **结论**: Choose A; existing `reject_topic_candidate` remains the deterministic candidate status tool.
- **影响**: Callers must invoke candidate rejection explicitly when they want candidate state to change.
- **来源**: Spec FR-008.

---

## Module Design

### Module: Migration `0010_topic_plan_contracts`

**YAGNI stop**: Layer 3, database-native constraints and indexes are enough.

**职责**: Create `hermes.topic_plans` with constraints, foreign keys, JSONB payload fields, timestamps, and listing indexes.

**改动概述**:

- Add migration under `packages/hermes-db/migrations/versions/`.
- Down revision should follow `0009_topic_candidates`.
- Add migration text assertions to `tests/test_migration_sql.py`.

**关键行为**:

```text
CREATE TABLE IF NOT EXISTS hermes.topic_plans (
  plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES hermes.topic_candidates(id) ON DELETE CASCADE,
  account_id TEXT NOT NULL,
  track_id TEXT,
  status TEXT NOT NULL,
  recommended_angle_index INTEGER,
  topic_angles JSONB NOT NULL,
  outline_pack JSONB NOT NULL,
  writing_brief JSONB NOT NULL,
  image_brief JSONB NOT NULL,
  evidence JSONB NOT NULL,
  llm_metadata JSONB NOT NULL,
  rejection_reason TEXT,
  topic_id UUID REFERENCES hermes.topics(id) ON DELETE SET NULL,
  source TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  consumed_at TIMESTAMPTZ
)
```

**注意事项**:

- `topic_angles`, handoff fields, `evidence`, and `llm_metadata` should default to JSON arrays/objects at the repository/tool boundary, not via hidden Python globals.
- Use check constraints for status and planned/rejected shape.
- Add `uq_topic_plans_candidate` on `candidate_id`.

### Module: Repository `topic_plan_repo.py`

**YAGNI stop**: Layer 5, small async functions using existing asyncpg pool style are enough.

**职责**: Own all SQL for topic plan lifecycle.

**改动概述**:

- `upsert_topic_plan(pool, payload, mark_candidate_shortlisted=False)`.
- `list_topic_plans(pool, account_id=None, track_id=None, status=None, limit=20, offset=0)`.
- `get_topic_plan(pool, plan_id)`.
- `update_topic_plan_status(pool, plan_id, status, topic_id=None)`.

**关键行为**:

```text
upsert:
  validate planned/rejected shape
  begin transaction
  INSERT ... ON CONFLICT(candidate_id) DO UPDATE
  if mark_candidate_shortlisted and status == planned:
      UPDATE hermes.topic_candidates SET status = 'shortlisted'
      only if transition from new/shortlisted is valid
  return {upserted, item}

status update:
  fetch current row
  update status/topic_id/consumed_at as needed
  return previous_status + item
```

**注意事项**:

- Keep SQL parameterized.
- Do not generate duplicate plans for repeated `candidate_id`.
- Use helper normalization for JSONB fields and timestamps.

### Module: Candidate Raw Read Extension

**YAGNI stop**: Layer 5, extend the existing function instead of adding a new abstraction.

**职责**: Let planning callers fetch candidate raw context only when they ask for it.

**改动概述**:

- Extend `topic_candidate_repo.get_candidate(pool, candidate_id, include_raw=False)`.
- Add MCP tool wrapper `get_topic_candidate(candidate_id, include_raw=False)` if absent from the public tool surface.
- Preserve existing list behavior that omits `raw_payload` unless requested.

**注意事项**:

- Default response must not leak raw payload into existing callers.
- Tests should assert both include and exclude behavior.

### Module: MCP Tools `topic_plans.py`

**YAGNI stop**: Layer 5, plain FastMCP tool functions match the repo.

**职责**: Expose plan lifecycle operations to agents through hermes-db MCP.

**改动概述**:

- Add `tools/topic_plans.py`.
- Register the module in `server.register_tools()`.
- Follow existing envelope/error style from topic candidate tools.

**关键接口**:

```text
upsert_topic_plan(candidate_id, account_id, track_id?, status,
                  recommended_angle_index?, topic_angles,
                  outline_pack, writing_brief, image_brief,
                  evidence?, llm_metadata?, rejection_reason?,
                  mark_candidate_shortlisted?)

list_topic_plans(account_id?, track_id?, status?, limit?, offset?)

get_topic_plan(plan_id)

update_topic_plan_status(plan_id, status, topic_id?)
```

**注意事项**:

- Reject `mark_candidate_shortlisted=true` unless `status=planned`.
- Return validation errors before repository writes.
- Keep result envelopes stable enough for agents smoke tests.

### Module: Schema Health

**YAGNI stop**: Layer 3, introspect database metadata like existing schema checks.

**职责**: Add `topic_plans` capability to health.

**改动概述**:

- Add `inspect_topic_plan_schema(pool)` in `services/schema.py`.
- Merge it into `tools/health.py` capabilities.
- Test complete and incomplete schema responses.

**注意事项**:

- Capability should return false if required table, columns, constraints, or indexes are missing.
- Health should not attempt writes.

---

## Data Model

Detailed data model is in [data-model.md](data-model.md).

Core entity:

- `hermes.topic_plans`: first-class plan lifecycle table keyed by `plan_id`, unique by `candidate_id` for MVP.

Core statuses:

- `planned`
- `rejected`
- `consumed`
- `archived`

---

## Project Structure

```text
packages/hermes-db/
├── migrations/versions/0010_topic_plan_contracts.py
├── src/hermes_db_mcp/
│   ├── repositories/topic_plan_repo.py
│   ├── repositories/topic_candidate_repo.py
│   ├── services/schema.py
│   ├── tools/topic_plans.py
│   ├── tools/topic_candidates.py
│   ├── tools/health.py
│   └── server.py
└── tests/
    ├── test_migration_sql.py
    ├── test_topic_plan_repo_sql.py
    ├── test_topic_plan_tools.py
    ├── test_topic_plan_schema_health.py
    └── test_topic_candidate_tools.py
```

---

## Risks and Tradeoffs

- **Schema shape risk**: Over-constraining planned/rejected JSON shape in SQL can make future LLM payloads brittle. Mitigation: SQL checks should enforce coarse shape only; tool tests enforce contract fields.
- **State coupling risk**: Candidate status and plan status can drift if callers bypass `upsert_topic_plan`. Mitigation: shortlist coupling only exists in one transactional repo path; no implicit reject side effects.
- **DTO drift risk**: agents may depend on field names before implementation stabilizes. Mitigation: pin response shape in tool tests and verify with an agents smoke after hermes-db tests pass.
- **Migration ordering risk**: revision id length and down revision must match current Alembic chain. Mitigation: extend existing migration SQL tests.

---

## Evolution Path

- **MVP**: One plan per candidate, no version history, no partial plan revisions, no automatic candidate rejection.
- **成长期**: Add plan versioning only after agents need compare/regenerate workflows.
- **成熟期**: Add analytics on plan quality and adoption outcomes after `topic_id` linkage has enough data.

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。No event bus, no plan version table, no separate service.
- 是否引用了外部模式但没有适配检查：否。This plan uses existing repository/migration/tool patterns from the repo.
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。New statuses are listed here and in data-model; no queue/cache/dependency added.

---

## Verification Strategy

1. Migration text test verifies revision id, down revision, table, constraints, and indexes.
2. Schema health tests verify `inspect_topic_plan_schema` returns true only when required objects exist.
3. Repository SQL tests verify upsert create/update idempotency, planned shortlist transaction behavior, rejected behavior, listing filters, get by id, and lifecycle updates.
4. Tool tests verify validation, error envelopes, include_raw behavior, and repository call contracts.
5. Existing topic candidate tests remain green to prove compatibility.
6. Optional integration smoke can run after implementation with a local or test Postgres if available.

Recommended focused command set:

```bash
cd packages/hermes-db
rtk uv run pytest \
  tests/test_migration_sql.py \
  tests/test_topic_candidate_repo_sql.py \
  tests/test_topic_candidate_tools.py \
  tests/test_topic_plan_repo_sql.py \
  tests/test_topic_plan_tools.py \
  tests/test_topic_plan_schema_health.py \
  tests/test_health.py
```

---

## Stage Readiness

- 是否需要 `data-model.md`：需要。This feature adds a new persisted entity, lifecycle statuses, foreign keys, indexes, and DTO shape.
- 下一步建议：`tasks`
- 阻塞项：无。The remaining implementation details are task-level, not spec/plan blockers.

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | 必须 | 当前文件 |
| data-model.md | 需要 | 新表、状态、DTO、索引 |
| tasks.md | 后续阶段生成 | 下一步拆 execution slices |
| acceptance.md | 后续阶段生成 | 最终验收记录 |

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| Topic candidate module style | UNVERIFIED | Local repo pattern: `topic_candidate_repo.py`, `tools/topic_candidates.py`, `services/schema.py`, `tests/test_topic_candidate_*` |
| Migration test style | UNVERIFIED | Local repo pattern: `tests/test_migration_sql.py` |
| Health capability style | UNVERIFIED | Local repo pattern: `tools/health.py` and `tests/test_health.py` |
