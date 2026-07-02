# Acceptance Record: Topic Plan Feedback And Optimization

**Workspace**: `topic-plan-feedback-and-optimization` | **Date**: 2026-07-02 | **Spec**: [spec.md](spec.md)

---

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| FR-001..FR-003C feedback event entity, fields, dedupe, `event_at`, published lineage | Migration creates `hermes.topic_plan_feedback_events`; repo/tool tests cover insert, missing plan, invalid event, duplicate `dedupe_key`, invalid `event_at`, missing published lineage. | `packages/hermes-db/migrations/versions/0011_topic_plan_feedback.py`; `tests/test_topic_plan_feedback_repo_sql.py`; `tests/test_topic_plan_feedback_tools.py` | PASS |
| FR-004 `record_topic_plan_feedback` | MCP tool writes feedback events and returns serialized DTO with `event_id`, `plan_id`, `event_type`, `event_at`, `created_at`. | `packages/hermes-db/src/hermes_db_mcp/tools/topic_plan_feedback.py`; focused pytest 61 passed | PASS |
| FR-005 `list_topic_plan_feedback` | Repo/tool supports plan/account/track/event type filters, `event_at` window, optional created audit filters, pagination and stable timestamp serialization. | `tests/test_topic_plan_feedback_repo_sql.py`; `tests/test_topic_plan_feedback_tools.py` | PASS |
| FR-006 feedback report | Report returns planned/accepted/rejected/deferred/consumed/published counts, rates, reason tags and grouping arrays. | `get_topic_plan_feedback_report`; report fixture tests | PASS |
| FR-007 fixed precedence | Report chooses effective event by `published > written > accepted > deferred > rejected > archived`; same precedence uses `event_at DESC, created_at DESC`. | `test_get_topic_plan_feedback_report_applies_precedence_and_rates`; `test_get_topic_plan_feedback_report_uses_latest_for_same_precedence` | PASS |
| FR-008 sample warning | Report returns `sample_warning` and `min_sample_size`; low denominator test covers warning behavior. | `test_get_topic_plan_feedback_report_applies_precedence_and_rates`; tool report tests | PASS |
| FR-009 config snapshot grouping | Report reads `llm_metadata.config_snapshot`; missing snapshot maps to `unknown_config`; `by_source` comes from `topic_plans.source`. | `test_get_topic_plan_feedback_report_groups_config_and_unknown_config` | PASS |
| FR-010 canonical hash contract | Runtime hash generation remains a producer contract; report consumes existing snapshot hash values without reordering JSON. | [plan.md](plan.md) ADR-005; [data-model.md](data-model.md) PlanningConfigSnapshot | PASS |
| FR-011 sensitive filtering | Report DTO returns counts, hashes and group keys only; tests assert report surface rather than raw metadata payload. | `tests/test_topic_plan_feedback_repo_sql.py`; [verify-evidence.md](verify-evidence.md) | PASS |
| FR-012 health capability | `health.capabilities.topic_plan_feedback` is wired through schema inspector; P2 summary excluded from gate. | `tests/test_health.py`; `tests/test_topic_plan_feedback_schema_health.py` | PASS |

---

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Migration, schema inspector, repo, MCP tool module, registration and health capability exist and are covered by focused tests. |
| Workflow closure | PASS | Record -> list -> report -> health gate is covered by focused tests and `verify-evidence.md`. |
| User-visible outcome | PASS for P1 | Feedback report returns user-visible metrics, groupings and sample warnings. P2 optimization summary is explicitly deferred. |

**Overall**: CONDITIONAL PASS

**三维不一致说明**: P1 完成且可验收；US4/P2 `get_topic_plan_optimization_summary` 延后，不阻塞 P1 feedback/report contract，也不参与 `topic_plan_feedback` health gate。

---

## Workflow Replay

- **输入摘要**: 一个 `topic_plan` 先记录 `accepted`，另一个记录 `published`，部分 plan 带 `llm_metadata.config_snapshot`，部分缺失配置快照。
- **最终 payload 摘要**: Report fixture 返回 `planned_count`、`accepted_count`、`consumed_count`、`published_count`、rates、`reason_tag_counts`、`by_runtime_version`、`by_track_config_hash`、`unknown_config` 和 `sample_warning`。
- **用户可见结果断言**: 用户可查看采纳率、消费率、发布率、拒绝原因分布和配置分组表现；自动配置建议未在 P1 输出。
- **Replay 类型**: fixture。当前阶段未连接真实 MCP runtime 和生产数据库，使用 repo/tool focused tests 作为可重复证据。

---

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | 不适用 | 本 feature 新增 feedback/report 补充层，不替代 `topic_plans.status` 生命周期；旧路径需保留。 | 无 |
| 发布、提交、CI 或 follow-through | 执行中 | Focused tests 已通过；用户已确认“提交并部署”；本轮按 `hermes-db-v0.2.29` 发布。 | 提交后推送 release tag，等待 GitHub Actions / NAS deploy 结果。 |
| 文档、阶段说明、模板或验收记录更新 | 已完成 | `spec.md`、`plan.md`、`tasks.md`、`verify-evidence.md`、本 `acceptance.md` 已更新。 | 无 |
| ADR、架构债或演进触发信号 | 已完成 | ADR 保留在 `plan.md`；架构债为 Python-side MVP aggregation，数据量增长后升级索引/物化汇总。 | 观察 report latency 和数据量。 |
| Knowledge Capture | 已完成 | 下方 Knowledge Capture 表已记录 decision/pattern/follow-up。 | 无 |

---

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| decision | P1 health gate boundary | `topic_plan_feedback` health gate 只覆盖 P1 record/list/report，不要求 P2 optimization summary。这样 P1 可独立上线，P2 保持后续能力。 | [spec.md](spec.md) FR-012; [tasks.md](tasks.md) T014 | hermes-db feedback/report capabilities | recorded-only | 无 |
| pattern | Optional dedupe insert | feedback 写入允许 `dedupe_key` 可选；有 key 时用 partial unique index + `DO NOTHING` + fetch existing，保留 append-only 语义。 | [plan.md](plan.md) ADR-003; `topic_plan_feedback_repo.py` | append-only event write APIs | recorded-only | 无 |
| pattern | Fixture report replay | 用 repo/tool fixture replay 固定 denominator、precedence、`event_at`、`unknown_config` 和 grouping 口径，先钉业务语义再考虑 SQL 优化。 | [verify-evidence.md](verify-evidence.md); `tests/test_topic_plan_feedback_repo_sql.py` | analytical MCP report features | recorded-only | 无 |
| follow-up | P2 summary deferred | `get_topic_plan_optimization_summary` 未在本轮实现。后续应基于 report evidence 输出建议，不自动写 `topic_candidate_tracks`。 | [tasks.md](tasks.md) T014/T015 | topic plan optimization workflow | follow-up | 后续 feature 实现 P2 summary |

---

## Commit Result

| Field | Value |
|---|---|
| Status | confirmed_for_submission |
| Commit Hashes | 提交后由 git 生成，并在对话收尾记录 |
| Commit Messages | `feat(hermes-db): add topic plan feedback reporting` |
| Included Files | 见 [commit-plan.md](commit-plan.md) |
| Excluded / Remaining Files | 仓库存在其它 unrelated dirty/untracked files；本 feature 只建议提交 commit plan included files。 |
| Reason | 用户已确认“提交并部署”；本记录随提交计划一起提交，实际 hash 与部署结果在收尾消息记录。 |

---

## Completion Record

- **最终结论**: CONDITIONAL PASS
- **完成依据**: [verify-evidence.md](verify-evidence.md) 记录 focused suite `61 passed in 0.32s`；Evidence Table 覆盖 P1 FR-001..FR-012。
- **阻塞项**: 无。
- **延后项**: P2 `get_topic_plan_optimization_summary`。触发条件：需要基于 report 自动生成保守配置建议时启动后续 feature。
- **退役结论**: 不适用。现有 `topic_plans.status` 生命周期保留，feedback events 是补充审计和分析层。
- **提交结论**: confirmed_for_submission；按 [commit-plan.md](commit-plan.md) 执行 `feat(hermes-db): add topic plan feedback reporting`。
- **后续动作**: 推送 `hermes-db-v0.2.29` release tag，并等待 CI / NAS deploy。
