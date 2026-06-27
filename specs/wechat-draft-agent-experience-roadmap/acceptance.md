# Acceptance Record: WeChat Draft Agent Experience Roadmap

**Workspace**: `wechat-draft-agent-experience-roadmap` | **Date**: 2026-06-27 | **Roadmap**: [roadmap.md](roadmap.md)

## Evidence Table

| Roadmap Objective | Evidence | Test or File | Verdict |
|---|---|---|---|
| Agent-facing constraints and remediation | `wechat-draft-agent-contract-hardening` completed with constraints, remediation fields, artifact upsert context. | `specs/wechat-draft-agent-contract-hardening/acceptance.md` | PASS |
| Deterministic article document tools | Markdown import, article validation, render/preview, publish-ready build tools completed. | `specs/wechat-article-document-tools/acceptance.md` | PASS |
| Asset preflight and diagnostics | Account constraints, local path diagnostics, explicit preflight gate completed. | `specs/wechat-draft-asset-preflight/acceptance.md` | PASS |
| One-call draft facade | `wechat_create_draft_facade` completed for existing publish-ready artifact and article-document modes. | `specs/wechat-draft-publish-ready-facade/acceptance.md`; 64/64 tests | PASS |
| Artifact lifecycle recovery | Hermes explicit artifact version/list/latest/diff tools completed; no `force_update`. | `specs/hermes-artifact-versioning-and-diff/acceptance.md`; Hermes pytest 19/19 + 14 passed/1 skipped | PASS |
| Remote draft visibility | Read-only `wechat_list_drafts` completed; update/delete deferred behind destructive gate. | `specs/wechat-draft-ops-crud/acceptance.md`; 67/67 tests | PASS |
| Boundary with note-skill migration | Roadmap kept writing generation, skill migration, Library/Memory routing, and prompt/model work out of scope. | `roadmap.md` Boundary section | PASS |

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | WeChat draft MCP and Hermes workflow tools now cover the planned agent-facing contract surface. |
| Workflow closure | PASS | A prepared article can be validated, rendered, built, persisted, drafted, inspected, and recovered through explicit version tools. |
| User-visible outcome | PASS | Agents get clearer constraints, one-call facade, phase traces, draft listing, and artifact diff/version recovery. |

**Overall**: PASS

## Verification Summary

| Area | Latest Evidence | Result |
|---|---|---|
| WeChat draft package | `pnpm --filter @mcps/wechat-draft build`; `pnpm --filter @mcps/wechat-draft test` | PASS, 67/67 tests |
| Hermes workflow artifacts | `uv run pytest tests/test_workflow_repo_sql.py tests/test_workflow_tools.py` from `packages/hermes-db` | PASS, 19/19 tests |
| Hermes workflow contracts/schema | `uv run pytest tests/test_workflow_contracts.py tests/test_workflow_schema_health.py tests/test_workflow_integration.py tests/test_migration_sql.py` | PASS, 14 passed, 1 skipped |
| Diff hygiene | `git diff --check` | PASS |

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | 不适用 | Low-level tools remain deliberate recovery/debug paths. | 无 |
| 发布、提交、CI 或 follow-through | 延后 | Local checks pass; no commit/deploy requested. | 用户确认后提交和部署 |
| 文档、阶段说明、模板或验收记录更新 | 已完成 | Roadmap and each feature have acceptance records. | 无 |
| ADR、架构债或演进触发信号 | 已完成 | Deferred destructive update/delete, schedule/group-send, cover channel switch, live smoke are recorded. | Future features |
| Knowledge Capture | 已完成 | Roadmap-level decisions recorded below; feature-level knowledge captured in each acceptance. | 无 |

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| pattern | Layered MCP Roadmap | Fix agent experience by hardening contracts first, then deterministic builders, then facade, then recovery and ops. This avoids pushing orchestration complexity back to agents. | `roadmap.md`; feature acceptance records | WeChat draft MCP roadmap planning | recorded-only | 无 |
| decision | No WeChat Force Update | Artifact mutation belongs in Hermes lifecycle tools, not as a WeChat facade `force_update`. Explicit versions preserve audit and recovery semantics. | `hermes-artifact-versioning-and-diff/acceptance.md` | Hermes workflow artifact writes | recorded-only | 无 |
| decision | Destructive Ops Split | Remote draft list is safe to ship as read-only; update/delete require a separate feature with destructive annotations and operator confirmation. | `wechat-draft-ops-crud/acceptance.md` | WeChat draft operations | recorded-only | Design future destructive draft ops |
| follow-up | Live Smoke And Deploy | Local tests prove contracts, not live WeChat adapter behavior after deployment. | Verification Summary | Release process | follow-up | Run live smoke with explicit operator approval |

## Commit Result

| Field | Value |
|---|---|
| Status | commit_plan_ready |
| Commit Hashes | 无 |
| Commit Messages | 无 |
| Included Files | 无 |
| Excluded / Remaining Files | Working tree includes roadmap-wide source/spec changes plus unrelated untracked runtime/docs such as `.pnpm-store/`, `DEPLOYMENT_SUMMARY.md`, `NAS_DEPLOYMENT_GUIDE.md`. Commit plan: `specs/wechat-draft-agent-experience-roadmap/commit-plan.md`. |
| Reason | SDD does not auto-commit. Commit plan is ready and needs user confirmation/file decisions. |

## Completion Record

- **最终结论**: PASS
- **完成依据**: All roadmap feature rows are `done`; latest WeChat and Hermes verification commands pass; `git diff --check` passes.
- **阻塞项**: 无。
- **延后项**: live WeChat smoke、commit/deploy、destructive draft update/delete、schedule/group-send、cover channel switch。
- **退役结论**: 不退役低层工具；它们作为恢复和调试入口保留。
- **提交结论**: commit_plan_ready; 等待用户确认批次和 excluded/needs-decision 文件。
- **后续动作**: 用户确认后执行分批 commit/deploy；另开 destructive draft ops feature if needed.
