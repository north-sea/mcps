# Data Model: Hermes DB Topic Plan Contract

**Workspace**: `hermes-db-topic-plan-contract` | **Date**: 2026-07-01 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Entity Overview

| Entity | Storage | Purpose |
|---|---|---|
| TopicCandidate | `hermes.topic_candidates` | Existing raw candidate and source context |
| TopicPlan | `hermes.topic_plans` | New durable planning contract consumed by agents and article workflows |
| Topic | `hermes.topics` | Existing final topic entity optionally linked after consumption |

---

## Table: `hermes.topic_plans`

| Column | Type | Required | Notes |
|---|---|---|---|
| `plan_id` | `UUID` | yes | Primary key, default `gen_random_uuid()` |
| `candidate_id` | `UUID` | yes | Unique FK to `hermes.topic_candidates(id)` |
| `account_id` | `TEXT` | yes | Denormalized for listing and account scoping |
| `track_id` | `TEXT` | no | Candidate track when available |
| `status` | `TEXT` | yes | `planned`, `rejected`, `consumed`, `archived` |
| `recommended_angle_index` | `INTEGER` | no | Required for `planned`; null for `rejected` |
| `topic_angles` | `JSONB` | yes | Array; 3-5 items for `planned`, empty array allowed for `rejected` |
| `outline_pack` | `JSONB` | yes | Object; may be `{}` for `rejected` |
| `writing_brief` | `JSONB` | yes | Object; may be `{}` for `rejected` |
| `image_brief` | `JSONB` | yes | Object; may be `{}` for `rejected` |
| `evidence` | `JSONB` | yes | Object/array with planning evidence |
| `llm_metadata` | `JSONB` | yes | Object with provider/model/prompt/version metadata when available |
| `rejection_reason` | `TEXT` | no | Required for `rejected` |
| `topic_id` | `UUID` | no | Optional FK to `hermes.topics(id)` after consumption |
| `source` | `TEXT` | no | Producer/source marker, e.g. `wechat-agent` |
| `created_at` | `TIMESTAMPTZ` | yes | Default `now()` |
| `updated_at` | `TIMESTAMPTZ` | yes | Updated on upsert/status change |
| `consumed_at` | `TIMESTAMPTZ` | no | Set when status becomes `consumed` |

---

## Constraints

| Constraint | Rule | Reason |
|---|---|---|
| `topic_plans_pkey` | `PRIMARY KEY(plan_id)` | Stable tool identifier |
| `uq_topic_plans_candidate` | `UNIQUE(candidate_id)` | MVP one active plan per candidate |
| `fk_topic_plans_candidate` | `candidate_id REFERENCES hermes.topic_candidates(id) ON DELETE CASCADE` | Plan cannot outlive candidate context |
| `fk_topic_plans_topic` | `topic_id REFERENCES hermes.topics(id) ON DELETE SET NULL` | Preserve plan if final topic is removed |
| `chk_topic_plans_status` | status in allowed enum | Prevent invalid lifecycle values |
| `chk_topic_plans_planned_shape` | planned rows have angle index, non-empty angles, and handoff objects | Prevent unusable planned handoffs |
| `chk_topic_plans_rejected_shape` | rejected rows have rejection reason and may have empty handoff payloads | Preserve rejection evidence without fake plans |

SQL checks should validate coarse JSONB type/length only. Fine-grained LLM payload semantics stay in tool tests and agents-side contract tests.

---

## Indexes

| Index | Columns | Purpose |
|---|---|---|
| `idx_topic_plans_account_status_created` | `(account_id, status, created_at DESC)` | Main list filter |
| `idx_topic_plans_account_track_status_created` | `(account_id, track_id, status, created_at DESC)` | Track-scoped list filter |
| `idx_topic_plans_candidate` | `(candidate_id)` | Fast upsert/get by candidate |
| `idx_topic_plans_topic_id` | `(topic_id)` | Trace consumed plans to final topics |

---

## Status Lifecycle

```text
planned  -> consumed
planned  -> archived
rejected -> archived
consumed -> archived
archived -> terminal
```

MVP does not require a generic state-machine module update unless implementation reuses existing `state_machine.py`. Repository/tool tests must at least prevent unknown statuses.

---

## DTO: `TopicPlan`

```json
{
  "plan_id": "uuid",
  "candidate_id": "uuid",
  "account_id": "mp_account",
  "track_id": "daily-topic-radar",
  "status": "planned",
  "recommended_angle_index": 0,
  "topic_angles": [
    {
      "title": "angle title",
      "summary": "why this angle works",
      "score": 0.82
    }
  ],
  "outline_pack": {
    "title": "article title",
    "sections": []
  },
  "writing_brief": {
    "audience": "target reader",
    "tone": "calm",
    "constraints": []
  },
  "image_brief": {
    "cover": {},
    "inline": []
  },
  "evidence": {
    "candidate_signals": []
  },
  "llm_metadata": {
    "provider": "unknown",
    "model": "unknown"
  },
  "rejection_reason": null,
  "topic_id": null,
  "source": "wechat-agent",
  "created_at": "2026-07-01T00:00:00Z",
  "updated_at": "2026-07-01T00:00:00Z",
  "consumed_at": null
}
```

---

## Tool Payload Rules

### `upsert_topic_plan`

Required:

- `candidate_id`
- `account_id`
- `status`

Required when `status=planned`:

- `recommended_angle_index`
- `topic_angles` with 3-5 entries
- `outline_pack`
- `writing_brief`
- `image_brief`

Required when `status=rejected`:

- `rejection_reason`

Optional:

- `track_id`
- `evidence`
- `llm_metadata`
- `source`
- `mark_candidate_shortlisted`

### `list_topic_plans`

Filters:

- `account_id`
- `track_id`
- `status`
- `limit`
- `offset`

### `update_topic_plan_status`

Allowed statuses:

- `planned`
- `rejected`
- `consumed`
- `archived`

When status becomes `consumed`, `topic_id` may be supplied and `consumed_at` should be set.

---

## Compatibility Notes

- Existing `topic_candidates.raw_payload` remains source context, not plan storage.
- Existing candidate `adopt`, `reject`, `shortlist`, and `expire` tool semantics remain unchanged.
- `get_topic_candidate(include_raw=false)` must keep omitting `raw_payload` by default.
- `upsert_topic_plan(status=rejected)` must not automatically call candidate rejection.

---

## Validation Matrix

| Case | Expected Result |
|---|---|
| Planned payload with 3 angles and handoff objects | Created/updated `TopicPlan` |
| Planned payload with `mark_candidate_shortlisted=true` | Plan upsert and candidate shortlist commit together |
| Rejected payload with reason and empty arrays/objects | Created/updated rejected plan; candidate status unchanged |
| Duplicate candidate upsert | Same candidate plan updated, no duplicate row |
| Unknown status | Validation error, no DB write |
| `include_raw=false` candidate read | `raw_payload` absent |
| `include_raw=true` candidate read | `raw_payload` present |
