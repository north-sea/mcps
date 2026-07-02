# Data Model: Topic Plan Feedback And Optimization

**Workspace**: `topic-plan-feedback-and-optimization` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Entity Overview

| Entity | Storage | Purpose |
|---|---|---|
| TopicPlan | `hermes.topic_plans` | Existing durable planning handoff and denominator for report |
| TopicPlanFeedbackEvent | `hermes.topic_plan_feedback_events` | New append-only feedback/lifecycle event log |
| PlanningConfigSnapshot | `hermes.topic_plans.llm_metadata.config_snapshot` | Stable runtime/config attribution for report grouping |
| Topic / Publication lineage | `hermes.topics` and metadata fields | Proof for written/published events |

---

## Table: `hermes.topic_plan_feedback_events`

| Column | Type | Required | Notes |
|---|---|---|---|
| `event_id` | `UUID` | yes | Primary key, default `gen_random_uuid()` |
| `plan_id` | `UUID` | yes | FK to `hermes.topic_plans(plan_id)` |
| `account_id` | `TEXT` | yes | Denormalized from plan for report filters |
| `track_id` | `TEXT` | no | Denormalized from plan |
| `event_type` | `TEXT` | yes | `accepted`, `rejected`, `deferred`, `archived`, `written`, `published`, `score_adjusted` |
| `dedupe_key` | `TEXT` | no | Optional idempotency key from UI/agent/client |
| `reason_tags` | `JSONB` | yes | Array of normalized reason tags, default `[]` |
| `note` | `TEXT` | no | Human-readable note |
| `decided_by` | `TEXT` | no | Actor marker, e.g. `user`, `hermes`, `codex`, `writing-agent` |
| `topic_id` | `UUID` | no | Optional FK to `hermes.topics(id)` |
| `metadata` | `JSONB` | yes | Object for publication lineage and extra evidence, default `{}` |
| `event_at` | `TIMESTAMPTZ` | yes | Actual event time; default `now()` |
| `created_at` | `TIMESTAMPTZ` | yes | DB write time; default `now()` |

---

## Constraints

| Constraint | Rule | Reason |
|---|---|---|
| `topic_plan_feedback_events_pkey` | `PRIMARY KEY(event_id)` | Stable tool identifier |
| `fk_topic_plan_feedback_events_plan` | `plan_id REFERENCES hermes.topic_plans(plan_id) ON DELETE CASCADE` | Feedback cannot outlive plan |
| `fk_topic_plan_feedback_events_topic` | `topic_id REFERENCES hermes.topics(id) ON DELETE SET NULL` | Preserve feedback if topic is removed |
| `chk_topic_plan_feedback_event_type` | event type in allowed set | Prevent invalid report values |
| `chk_topic_plan_feedback_reason_tags_array` | `jsonb_typeof(reason_tags) = 'array'` | Keep reason aggregation predictable |
| `chk_topic_plan_feedback_metadata_object` | `jsonb_typeof(metadata) = 'object'` | Keep metadata access predictable |

Tool-level validation must additionally enforce:

- `published` requires at least one lineage value: `topic_id`, `metadata.publication_id`, or `metadata.publication_idempotency_key`.
- `event_at` must parse as timestamp if supplied.
- `reason_tags` must be an array of non-empty strings.

---

## Indexes

| Index | Columns | Purpose |
|---|---|---|
| `idx_topic_plan_feedback_plan_event_at` | `(plan_id, event_at DESC)` | Read plan event history |
| `idx_topic_plan_feedback_account_track_event_at` | `(account_id, track_id, event_at DESC)` | Account/track report window |
| `idx_topic_plan_feedback_account_event_type_event_at` | `(account_id, event_type, event_at DESC)` | Reason/event type summaries |
| `uq_topic_plan_feedback_dedupe` | `(plan_id, event_type, dedupe_key) WHERE dedupe_key IS NOT NULL` | Idempotent client retries |
| `idx_topic_plan_feedback_topic_id` | `(topic_id) WHERE topic_id IS NOT NULL` | Trace written/published events |

---

## Event Precedence

Report-level effective event per plan uses:

```text
published > written > accepted > deferred > rejected > archived
```

Rules:

- Keep raw events append-only.
- Count a plan once per metric bucket after precedence is applied.
- When multiple events have the same precedence, choose `event_at DESC, created_at DESC`.
- Preserve reason tag distribution from rejected/deferred events, even if a later event wins lifecycle precedence.
- `score_adjusted` is an analysis/support event and must not override lifecycle precedence.

---

## PlanningConfigSnapshot

Stored under `hermes.topic_plans.llm_metadata.config_snapshot`.

```json
{
  "runtime_name": "wechat-topic-planner",
  "runtime_version": "2026-07-01",
  "planner_version": "v1",
  "account_config_hash": "sha256:...",
  "track_config_hash": "sha256:...",
  "scoring_profile_hash": "sha256:..."
}
```

Rules:

- Missing snapshot maps to `unknown_config`.
- Report returns hashes and summary fields only.
- Hash generation must use canonical JSON serialization when implemented in this repo.
- Do not return full prompts, secret-bearing runtime config, Authorization headers, API keys, or raw payload.

---

## DTO: `TopicPlanFeedbackEvent`

```json
{
  "event_id": "uuid",
  "plan_id": "uuid",
  "account_id": "mp_account",
  "track_id": "daily-topic-radar",
  "event_type": "accepted",
  "dedupe_key": "ui-click-123",
  "reason_tags": ["worth-writing"],
  "note": null,
  "decided_by": "user",
  "topic_id": null,
  "metadata": {},
  "event_at": "2026-07-01T10:00:00Z",
  "created_at": "2026-07-01T10:00:02Z"
}
```

---

## DTO: `TopicPlanFeedbackReport`

```json
{
  "account_id": "mp_account",
  "track_id": "daily-topic-radar",
  "window_days": 30,
  "planned_count": 20,
  "accepted_count": 8,
  "rejected_count": 5,
  "deferred_count": 2,
  "consumed_count": 4,
  "published_count": 3,
  "acceptance_rate": 0.4,
  "consume_rate": 0.2,
  "publish_rate": 0.15,
  "reason_tag_counts": {
    "too-generic": 3,
    "off-brand": 2
  },
  "by_source": [],
  "by_runtime_version": [],
  "by_track_config_hash": [],
  "sample_warning": false,
  "min_sample_size": 5
}
```

Metric rules:

- `planned_count`: number of matching `topic_plans` in the report scope.
- `accepted_count`: plans whose effective event is `accepted`, `written`, or `published`.
- `consumed_count`: plans with `topic_plans.status='consumed'` or effective event `written`/`published`.
- `published_count`: plans with effective event `published`.
- `by_source`: grouped by `topic_plans.source`, not by a feedback-event column.
- Rates use `planned_count` as denominator; return `null` when denominator is zero.
- `sample_warning=true` when `planned_count < min_sample_size`.

---

## DTO: `TopicPlanOptimizationSummary` (P2 Optional)

```json
{
  "account_id": "mp_account",
  "track_id": "daily-topic-radar",
  "sample_warning": false,
  "suggestions": [
    {
      "type": "negative_keyword",
      "summary": "too-generic rejection is high; consider adding narrower negative keywords",
      "evidence_plan_ids": ["uuid-1", "uuid-2"],
      "reason_tags": ["too-generic"]
    }
  ]
}
```

Rules:

- Never modifies `topic_candidate_tracks`.
- Do not generate strong recommendations when `sample_warning=true`.
- Each suggestion must include evidence plan ids or reason tags.

---

## Relationships

```text
TopicPlan 1:N TopicPlanFeedbackEvent
TopicPlan N:1 TopicCandidate
TopicPlanFeedbackEvent N:1 Topic (optional)
TopicPlan 1:1 PlanningConfigSnapshot via llm_metadata.config_snapshot
```

---

## Migration Notes

- Alembic revision should follow `0010_topic_plans`.
- Downgrade drops indexes before table.
- Existing `topic_plans` rows are not backfilled.
- Old rows without config snapshot are reported as `unknown_config`.
- Existing `topic_plans.status` lifecycle is not replaced by feedback events.
