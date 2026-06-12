# Acceptance Record: Hermes DB WeChat Retrospective Topic Optimizer

**Workspace**: `hermes-db-wechat-retrospective-topic-optimizer` | **Date**: 2026-06-07 | **Updated**: 2026-06-08 | **Spec**: [spec.md](spec.md)

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| FR-001 performance upsert/list | 新增 `topic_performance` migration、contract validators、repository upsert/list、MCP tools；focused suite 覆盖幂等 upsert、filters、pagination 和 JSON serialization。 | `packages/hermes-db/migrations/versions/0005_wechat_retrospective_topic_optimizer.py`; `rtk uv run pytest tests/test_migration_sql.py tests/test_wechat_retrospective_contracts.py tests/test_wechat_retrospective_repo_sql.py tests/test_wechat_retrospective_tools.py tests/test_wechat_retrospective_schema_health.py -q` -> 70 passed | PASS |
| FR-002 reports create/get/list | 新增 report table、repository helpers 和 MCP tools；测试覆盖 create/get/list、not_found 和 schema drift mapping。 | `packages/hermes-db/src/hermes_db_mcp/tools/wechat_retrospective.py`; focused suite -> 70 passed | PASS |
| FR-003 suggestions create/list/review | 新增 suggestions table、batch create/list/review、review 状态校验；review tool 不允许写 `applied`。 | `packages/hermes-db/tests/test_wechat_retrospective_tools.py`; focused suite -> 70 passed | PASS |
| FR-004 learning candidates create/list/review | 新增 learning candidates table、batch create/list/review；审核只更新 candidate row，不应用 policy。 | `packages/hermes-db/src/hermes_db_mcp/repositories/wechat_retrospective_repo.py`; focused suite -> 70 passed | PASS |
| FR-005 approved ranking hints | `list_approved_topic_ranking_hints` 只返回 approved/applied 且未过期 suggestions，并支持 target filters。 | `packages/hermes-db/tests/test_wechat_retrospective_repo_sql.py`; `packages/hermes-db/tests/test_wechat_retrospective_tools.py`; focused suite -> 70 passed | PASS |
| FR-006 list pagination with total | Retrospective list tools 返回 `{items,total,limit,offset}`；repository 使用 count query。 | `packages/hermes-db/tests/test_wechat_retrospective_repo_sql.py`; `packages/hermes-db/tests/test_wechat_retrospective_tools.py`; focused suite -> 70 passed | PASS |
| FR-009/FR-010 health capability/schema drift gate | `health` 默认 `wechat_retrospective_topic_optimizer=false`；PG OK 时合并 schema inspector；inspector 检查四表 columns、PK/unique/check/FK constraints 和 indexes。 | `rtk uv run pytest tests/test_wechat_retrospective_schema_health.py tests/test_health.py -q` -> 10 passed | PASS |
| FR-011 structured errors | Tool 层映射 validation、FK not_found、schema_drift、invalid_transition 和 generic database_error。 | `packages/hermes-db/tests/test_wechat_retrospective_tools.py`; focused suite -> 70 passed | PASS |
| FR-012 downgrade safety | downgrade 按 learning candidates -> suggestions -> reports -> performance 删除 retrospective 表，不修改旧 feature 表。 | `packages/hermes-db/tests/test_migration_sql.py`; focused suite -> 70 passed | PASS |
| Existing capability regression | 旧 health、analytics、article、workflow、topic update tests 未被新 tool/module 破坏。 | `rtk uv run pytest tests/test_health.py tests/test_wechat_analytics_tools.py tests/test_wechat_article_tools.py tests/test_workflow_tools.py tests/test_tools_updates.py -q` -> 46 passed | PASS |
| Code quality | 全包 ruff 通过。 | `rtk uv run ruff check .` -> All checks passed | PASS |
| DB integration smoke | 本地 integration test 仍因无 `DATABASE_URL` clean skip；已用 NAS production MCP + real PG roundtrip 替代证明真实 DB 写读链路。 | `rtk uv run pytest tests/test_wechat_retrospective_integration.py -q` -> 1 skipped; deployed live smoke -> article/performance/report/suggestion/candidate ids all returned | PASS |
| Runtime MCP smoke | 本地-only MCP smoke 未执行，closeout 接受 deployed NAS `hermes-db-v0.2.15` runtime smoke 作为更接近最终运行环境的替代证据。 | T044 health smoke + T045 agents live smoke covered health capability and all retrospective tool calls | PASS |
| Deployed NAS health smoke | NAS `hermes-db-mcp` 已运行 `ghcr.io/north-sea/hermes-db-mcp:v0.2.15`，health 返回 schema revision `0005_wechat_retro_opt` 和 retrospective capability true。 | `rtk bash scripts/check-mcp-deploy.sh hermes-db-v0.2.15 nas deploy/mcp-services.json` -> `running=true`, `version=0.2.15`, `capabilities.wechat_retrospective_topic_optimizer=true`, `alembic=('0005_wechat_retro_opt',)` | PASS |
| Agents handoff smoke | agents production adapter 通过 retrospective 单测，并 against deployed MCP 完成 analytics -> article -> performance -> report -> suggestion approve -> approved ranking hint -> learning candidate。 | `rtk bun test packages/adapters/src/mcp/retrospective-tools.test.ts` from `/Users/yqg/personal/AI/agents` -> 6 pass; live smoke account `codex-retro-live-20260607170626`, approved hints `1`, candidate `98bf22a0-26b6-4bc9-96ef-755319e20cd9` | PASS |

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Migration、contracts、repository、MCP tools、health inspector、docs 和 regression tests 已完成。 |
| Workflow closure | PASS | 本地 unit/regression/ruff 通过；local-only smoke 由 deployed NAS production MCP + real PG smoke 替代。 |
| User-visible outcome | PASS | NAS capability 已为 true，agents adapter live smoke 已取回 approved ranking hint 和 learning candidate。 |

**Overall**: PASS

**替代证据说明**: 本地-only MCP smoke 因当前机器无 `DATABASE_URL`/本地容器未执行；最终判定采用 deployed NAS `v0.2.15` production MCP smoke 覆盖同一 runtime 行为，并额外证明真实部署镜像、Alembic revision 和 agents adapter handoff。

## Workflow Replay

- **输入摘要**: agents 侧将微信文章 analytics 结果转为 performance、report、suggestion、learning candidate payload。
- **最终 payload 摘要**: deployed live smoke 生成 article `af425208-bdc9-453d-af31-ed3633f5f272`、snapshot `90c212fe-4bb8-45f7-9e36-b4d4c9f8b1cb`、performance `c2aa7b3e-dbe0-40b8-848b-bfd4c15a9d2d`、report `5153b211-122c-414b-9b09-bb77c4ddf39f`、suggestion `76626d70-6ead-4d85-8777-c774cf142f83`、candidate `98bf22a0-26b6-4bc9-96ef-755319e20cd9`。
- **用户可见结果断言**: suggestion review status 为 `approved`，approved ranking hints 查询返回 `1` 条，learning candidate 成功创建，可被 agents 后续排序/策略链路读取。
- **Replay 类型**: deployed production MCP + real PG smoke。账号 `codex-retro-live-20260607170626`。

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | 不适用 | 本 feature 是 additive migration 和 additive MCP tools；未替换旧工具。 | 无 |
| 发布、提交、CI 或 follow-through | 已完成 | `hermes-db-v0.2.15` release run `27098123569` 成功；NAS health 显示 `version=0.2.15`、schema revision `0005_wechat_retro_opt`、capability true。失败的 `v0.2.13` 暴露 revision 长度问题，失败的 `v0.2.14` 暴露 NAS runner checkout 问题，均已在后续 commits 修复。 | 无 |
| 文档、阶段说明、模板或验收记录更新 | 已完成 | `tasks.md` 和本 acceptance 已补最终部署与 live smoke 证据。 | 如需提交，按 SDD commit plan 单独提交文档证据。 |
| ADR、架构债或演进触发信号 | 延后 | `applied` suggestion 和 `exported_to_policy` 仍为 future trace/export 状态。 | 后续如 agents 需要写回应用 trace，再新增 mark-applied/export tool。 |
| 知识同步或经验沉淀 | 延后 | Nowledge Mem 本地服务 `http://127.0.0.1:14242` 当前不可达；已在本 acceptance 留存最终证据。 | Mem 服务恢复后同步 `v0.2.15` 部署结论。 |

## Commit Result

| Field | Value |
|---|---|
| Status | release_submitted; closeout_docs_unsubmitted |
| Commit Hashes | `63363a6`, `9ef5517`, `42760b1` |
| Commit Messages | `feat(hermes-db): add wechat retrospective optimizer`; `fix(hermes-db): shorten retrospective migration revision`; `ci: avoid NAS checkout in MCP release preflight` |
| Included Files | release commits and tag `hermes-db-v0.2.15` have been pushed |
| Excluded / Remaining Files | current closeout evidence edits in `specs/hermes-db-wechat-retrospective-topic-optimizer/tasks.md` and `acceptance.md`; downstream agents adapter compatibility edits in `/Users/yqg/personal/AI/agents` remain in that repo worktree |
| Reason | SDD closeout 不自动新增提交；最终验收记录等待用户确认后再单独提交。 |

## Completion Record

- **最终结论**: PASS
- **完成依据**: 本地 focused suite 70 passed、existing regression 46 passed、health/schema 10 passed、全包 `rtk uv run pytest tests -q` -> 267 passed / 23 skipped、`rtk uv run ruff check .` passed；NAS deployed health smoke 通过；agents adapter live smoke 通过。
- **阻塞项**: 无。
- **延后项**: 可选提交 closeout docs；agents repo compatibility patch 需在 agents feature 自身收口；Nowledge Mem 服务恢复后同步记忆。
- **退役结论**: 不适用。
- **提交结论**: release commits/tag 已提交并推送；本次 closeout 文档未自动提交。
- **后续动作**: 无 hermes-db 部署阻塞；如需持久化验收记录，提交本 acceptance/tasks 更新。
