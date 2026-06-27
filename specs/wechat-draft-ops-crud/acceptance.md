# Acceptance Record: WeChat Draft Ops CRUD

**Workspace**: `wechat-draft-ops-crud` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| FR-001 `wechat_list_drafts` MCP tool | Tool registered and listed by HTTP MCP smoke. | `createMcpServer.ts`; `HTTP MCP smoke calls list accounts and create draft through Streamable HTTP` | PASS |
| FR-002 list drafts schema | Input/output schema supports account, offset/count, include_content, summaries. | `tool-schemas.ts`; TypeScript build | PASS |
| FR-003 adapter client batchget | NAS-side client added `batchGetDrafts` for `/drafts/batchget`. | `WechatAdapterClient.ts` | PASS |
| FR-004 adapter error mapping | Service uses existing adapter error mapping path. Capability missing has structured error. | `WechatDraftService.listDrafts returns capability remediation when adapter lacks batchget` | PASS |
| FR-005 preserve local job status | `wechat_get_draft_status` unchanged; full suite still passes. | `pnpm --filter @mcps/wechat-draft test` 67/67 | PASS |
| FR-006 defer update/delete | No update/delete implementation added. | `verify-evidence.md` Diffusion Check | PASS |
| FR-007 future safety boundaries documented | spec/plan record destructive annotations and confirmation gate before update/delete. | `spec.md`, `plan.md` | PASS |

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Schema, adapter client, service, MCP registration, and tests are present. |
| Workflow closure | PASS | Operators/agents can inspect remote drafts through MCP before deciding next action. |
| User-visible outcome | PASS | Remote draft summaries are returned without full content by default; explicit content mode exists. |

**Overall**: PASS

## Workflow Replay

- **输入摘要**: `wechat_list_drafts(account="xiaban", offset=0, count=20, include_content=false)`.
- **最终 payload 摘要**: result includes `total_count`, `item_count`, `media_id`, title/author/digest/thumb summary; no full `content`.
- **用户可见结果断言**: Agent can inspect remote draft box without leaving MCP and without pulling full HTML by default.
- **Replay 类型**: fixture. No live WeChat batchget call in unit tests.

## Bugfix Closure

| Field | Value |
|---|---|
| Root Cause / Hypothesis | MCP could create drafts but not inspect remote draft box; operational CRUD feedback was bundled with higher-risk destructive actions. |
| Fix Mechanism | Implemented read-only `wechat_list_drafts` first and explicitly deferred update/delete. |
| Prevention Mechanism | Tests pin summary mode, content opt-in mode, capability missing, and MCP discovery. |
| Failed Attempts Summary | Avoided implementing update/delete without confirmation design. |
| Regression Guard | `pnpm --filter @mcps/wechat-draft build`; `pnpm --filter @mcps/wechat-draft test` 67/67; `git diff --check`. |
| Diffusion Check | No update/delete/schedule/group-send implementation added. |
| Remaining Risk | Live adapter batchget smoke remains a deployment follow-up. |

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | 不适用 | Local job status remains separate from remote draft list. | 无 |
| 发布、提交、CI 或 follow-through | 延后 | Local build/test/check pass; no commit/deploy requested. | 用户确认后提交/部署 |
| 文档、阶段说明、模板或验收记录更新 | 已完成 | spec/plan/tasks/evidence/acceptance written. | 无 |
| ADR、架构债或演进触发信号 | 已完成 | Update/delete require destructive annotations and confirmation before implementation. | Future feature |
| Knowledge Capture | 已完成 | Recorded below. | 无 |

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| decision | Read-Only First | Operational draft CRUD should start with remote list/detail before update/delete. It gives operators visibility without introducing destructive risk. | `plan.md` Scope Decision; tests | WeChat draft operations MCP | recorded-only | 无 |
| convention | Content Is Opt-In | Remote draft list omits full article content by default and only returns it when `include_content=true`. | `tool-schemas.ts`; `WechatDraftService.listDrafts` tests | MCP tools returning large remote content | recorded-only | 无 |
| follow-up | Destructive Draft Ops | Update/delete need adapter endpoints, destructive annotations, and explicit confirmation token/phrase before implementation. | `spec.md` US3; `acceptance.md` Remaining Risk | Future WeChat draft ops | follow-up | Design separate feature |

## Commit Result

| Field | Value |
|---|---|
| Status | not_submitted |
| Commit Hashes | 无 |
| Commit Messages | 无 |
| Included Files | 无 |
| Excluded / Remaining Files | Working tree contains roadmap-wide changes; no commit confirmation. |
| Reason | SDD closeout does not auto-submit commits. |

## Completion Record

- **最终结论**: PASS
- **完成依据**: Evidence Table 全部 PASS；wechat-draft build/test/diff-check PASS。
- **阻塞项**: 无。
- **延后项**: live batchget smoke、update/delete destructive design、commit/deploy。
- **退役结论**: 不退役本地 `wechat_get_draft_status`；它与远端草稿箱列表并存。
- **提交结论**: not_submitted。
- **后续动作**: roadmap 可进入整体 closeout，或另开 destructive draft update/delete feature。
