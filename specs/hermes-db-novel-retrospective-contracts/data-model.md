# Data Model: Hermes-DB Novel Retrospective Contracts

**Workspace**: `hermes-db-novel-retrospective-contracts`  
**Date**: 2026-07-07  
**Migration**: `0009_novel_retrospective_contracts.py`

## Tables

### `hermes.novel_retrospective_reports`

| Column | Type | Notes |
|---|---|---|
| `report_id` | UUID PK | generated |
| `book_slug` | TEXT FK | references `hermes.novel_books(book_slug)` |
| `batch_label` | TEXT | e.g. `ch_001-003`, `volume_01` |
| `mode` | VARCHAR(20) | `batch` or `volume` |
| `start_chapter` / `end_chapter` | INTEGER | positive range |
| `scoring_version` | TEXT | detector/scoring version |
| `diagnosis_json` | JSONB | deterministic findings payload |
| `llm_narrative` | TEXT nullable | render text, not source of truth |
| `confidence` | VARCHAR(10) | `high` or `low` |
| `warnings` | TEXT[] | non-blocking warnings |
| `review_status` | VARCHAR(20) | `pending`, `approved`, `rejected` |
| `created_at` / `updated_at` | TIMESTAMPTZ | default now |

Indexes:

- `idx_novel_retrospective_reports_book_created`
- `idx_novel_retrospective_reports_book_range`
- `idx_novel_retrospective_reports_review_status`

### `hermes.novel_retrospective_alerts`

| Column | Type | Notes |
|---|---|---|
| `alert_id` | UUID PK | generated |
| `report_id` | UUID FK | cascade on report delete |
| `alert_type` | VARCHAR(50) | high similarity, character reaction, foreshadowing, emotional debt |
| `severity` | VARCHAR(10) | `red`, `yellow`, `green` |
| `description` | TEXT | human-readable alert |
| `evidence_refs` | TEXT[] | chapter/span refs |
| `suggested_action` | TEXT nullable | optional runtime suggestion |
| `created_at` | TIMESTAMPTZ | default now |

Index: `idx_novel_retrospective_alerts_report`.

### `hermes.novel_correction_constraints`

| Column | Type | Notes |
|---|---|---|
| `constraint_id` | UUID PK | generated |
| `book_slug` | TEXT FK | references book |
| `source_report_id` | UUID FK | references report |
| `alert_type` | TEXT | source alert category |
| `description` | TEXT | approved correction instruction |
| `target_chapters` | VARCHAR(20) | `next` or `remaining` |
| `status` | VARCHAR(20) | `pending`, `approved`, `rejected`, `expired` |
| `expires_at` | TIMESTAMPTZ nullable | optional |
| `created_at` / `updated_at` | TIMESTAMPTZ | default now |

Indexes:

- `idx_novel_correction_constraints_book_status`
- `idx_novel_correction_constraints_report`

### `hermes.novel_handoff_packages`

| Column | Type | Notes |
|---|---|---|
| `package_id` | UUID PK | generated |
| `book_slug` | TEXT FK | references book |
| `snapshot_chapter` | INTEGER | latest completed chapter in package |
| `context_version` | INTEGER | book context version |
| `progress_json` | JSONB | compact progress object |
| `character_states_json` | JSONB | embedded snapshot array |
| `recent_changes` | TEXT[] | summary bullets |
| `remaining_tasks` | TEXT[] | pending bullets |
| `disabled_templates` | TEXT[] | guardrail list |
| `stage_reminders` | TEXT[] | continuation reminders |
| `created_at` | TIMESTAMPTZ | default now |

Index: `idx_novel_handoff_packages_book_created`.

### `hermes.novel_character_states`

| Column | Type | Notes |
|---|---|---|
| `state_id` | UUID PK | generated |
| `book_slug` | TEXT FK | references book |
| `character_name` | TEXT | logical character key |
| `last_chapter` | INTEGER | snapshot chapter |
| `location` | TEXT | current known location |
| `relationships_json` | JSONB | compact relationship map |
| `emotional_state` | TEXT | current state |
| `goals` / `conflicts` / `personality_traits` | TEXT[] | compact arrays |
| `arc_progress` | TEXT | arc summary |
| `dialogue_style` | TEXT | compact style note |
| `created_at` / `updated_at` | TIMESTAMPTZ | default now |

Unique key:

- `uq_novel_character_states_book_character_chapter` on `(book_slug, character_name, last_chapter)`

Indexes:

- `idx_novel_character_states_book_character`
- `idx_novel_character_states_book_chapter`

### `hermes.novel_learning_candidates`

| Column | Type | Notes |
|---|---|---|
| `candidate_id` | UUID PK | generated |
| `source_report_id` | UUID FK | references report |
| `scope` | TEXT | domain/scope |
| `trigger_conditions` | JSONB | when to apply |
| `proposed_action` | TEXT | compact proposed change |
| `evidence_refs` | TEXT[] | source refs |
| `confidence` | VARCHAR(10) | `high`, `medium`, `low` |
| `status` | VARCHAR(20) | `pending`, `approved`, `rejected` |
| `created_at` / `updated_at` | TIMESTAMPTZ | default now |

Index: `idx_novel_learning_candidates_source_report`.

## Tool Contract

Tool names must match agents adapter:

- `create_novel_retrospective_report`
- `get_novel_retrospective_report`
- `list_novel_retrospective_reports`
- `update_novel_retrospective_report_review_status`
- `create_novel_retrospective_alert`
- `list_novel_retrospective_alerts`
- `create_novel_correction_constraint`
- `get_novel_correction_constraint`
- `list_novel_correction_constraints`
- `update_novel_correction_constraint_status`
- `create_novel_handoff_package`
- `get_novel_handoff_package`
- `get_latest_novel_handoff_package`
- `upsert_novel_character_state`
- `get_novel_character_state`
- `list_novel_character_states`
- `create_novel_learning_candidate`
- `list_novel_learning_candidates`
- `health_novel_retrospective`
