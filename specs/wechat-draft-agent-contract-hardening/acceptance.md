# Acceptance Record: WeChat Draft Agent Contract Hardening

**Workspace**: `wechat-draft-agent-contract-hardening` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| FR-001 account constraints discoverable | `wechat_list_accounts` output schema includes `constraints.assets`; service fills body/cover image limits, MIME, source types, local path prefix, and remote protocols from the same helper used by upload validation. | `packages/wechat-draft/src/schemas/tool-schemas.ts`; `packages/wechat-draft/src/wechat/AssetSourceLoader.ts`; `WechatDraftService.listAccounts returns account constraints`; `AssetSourceLoader exposes constraints matching enforced guards` | PASS |
| FR-002 public errors support remediation | WeChat and Hermes error envelopes keep old code/message fields and add optional `next_action`, `remediation_hint`, `retryable`, `current_phase`. Asset, adapter, workflow, conflict, and missing-run paths use those fields. | `packages/wechat-draft/src/schemas/result-types.ts`; `packages/hermes-db/src/hermes_db_mcp/contracts.py`; `errorMapping.test.ts`; `DraftWorkflow.test.ts`; `test_workflow_tools.py` | PASS |
| FR-003 `content_ref` only is recoverable | `DraftPayloadBuilder` no longer throws internal `T013 limitation`; workflow returns `next_action=re_upsert_inline_content_text` during payload build. | `DraftWorkflow returns actionable error for content_ref-only artifacts`; `verify-evidence.md` diffusion check | PASS |
| FR-004 artifact upsert outcome explicit | Hermes repo returns outcome metadata for created/idempotent paths; tool returns idempotency hit, skipped reason, hash context, structured conflict remediation, and missing run next action. | `workflow_repo.py`; `workflow_artifacts.py`; `test_workflow_repo_sql.py`; `test_workflow_tools.py` | PASS |
| FR-005 docs use real payload shape | Article document docs state `content_text` is a JSON string, include a real `upsert_workflow_artifact` payload shape, and document the shortest agent draft flow. | `docs/article-document-artifact-example.md` | PASS |
| FR-006 tests cover new contract fields | WeChat build/test pass with 44 tests; Hermes targeted workflow tests pass with 10 tests; additional integration command passed non-DB tests and skipped DB fixture tests. | `verify-evidence.md`; `pnpm --filter @mcps/wechat-draft test`; `uv run pytest ...` | PASS |

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Schema, service, workflow, asset loader, Hermes repo/tool, and docs implement the scoped contract changes. |
| Workflow closure | PASS | Agent can now preflight constraints, distinguish input-fixable vs retryable failures, understand idempotent skips, and recover missing workflow runs/conflicts without parsing internal strings. |
| User-visible outcome | PASS | The MCP responses expose actionable fields while preserving existing result shapes. No E2E facade or auto-compression was added, matching scope. |

**Overall**: PASS

## Workflow Replay

- **输入摘要**: Agent calls list accounts, uploads or validates assets, upserts publish-ready workflow artifacts, then calls create draft/status.
- **最终 payload 摘要**: Account responses include constraints; failures include `next_action` and `retryable`; artifact upsert success includes idempotency outcome; content-ref-only draft failure instructs inline `content_text` recovery.
- **用户可见结果断言**: Known failed paths now point to the next operation instead of leaking `T013`, raw FK details, or silent `created=false` semantics.
- **Replay 类型**: fixture/static。真实 WeChat 写操作未执行；本 feature 的完成条件是 contract hardening，不是 live draft publication.

## Bugfix Closure

| Field | Value |
|---|---|
| Root Cause / Hypothesis | Tool contracts exposed low-level implementation boundaries: hidden image guards, internal content_ref limitation, raw-ish DB constraint behavior, and silent artifact idempotency. |
| Fix Mechanism | Added discoverable constraints, optional remediation fields, structured Hermes upsert outcome, content_ref recovery errors, and executable docs. |
| Prevention Mechanism | Contract/unit tests cover constraints drift, remediation fields, idempotency outcome, conflict hash details, missing-run mapping, and no `T013` in user-facing content_ref failure. |
| Failed Attempts Summary | No code-level failed implementation path retained. Verification caught a brittle string conflict exception and old two-value test unpack; both were corrected before closeout. |
| Regression Guard | `pnpm --filter @mcps/wechat-draft build`; `pnpm --filter @mcps/wechat-draft test`; Hermes workflow pytest targets; `git diff --check`; diffusion `rg` recorded in `verify-evidence.md`. |
| Diffusion Check | Runtime WeChat paths no longer expose `content_ref is not yet supported` or `T013 limitation`; FK string remains only in mapper/schema-health/test contexts; `artifact_id_conflict` remains as public code with remediation. |
| Remaining Risk | JSON object/string ambiguity may still occur in some MCP client bindings; typed article document tools are next. Cover channel remains conservative `thumb`/64KB until live evidence proves an image-media alternative. |

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | 已完成 | Internal `T013 limitation` throw removed; Hermes conflict string parsing replaced by structured `ArtifactIdConflictError` with legacy fallback. | 无 |
| 发布、提交、CI 或 follow-through | 延后 | 本轮未提交、未发布；用户尚未要求 commit。 | 需要提交时先做 commit plan，只包含本 feature 相关 diff。 |
| 文档、阶段说明、模板或验收记录更新 | 已完成 | `docs/article-document-artifact-example.md`、`verify-evidence.md`、本 `acceptance.md` 已更新。 | 无 |
| ADR、架构债或演进触发信号 | 已完成 | E2E facade、auto-compress、cover channel switch、generic artifact versioning 均保留为 roadmap 后续项。 | 进入 `wechat-article-document-tools`。 |
| Knowledge Capture | 已完成 | 见下表；只记录到本地 acceptance。 | 无 |

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| decision | 保留低层工具，先硬化契约 | 当前 feature 不做一锤子 E2E facade；先让现有 tools 的约束、错误和 artifact outcome 对 agent 可恢复。 | `spec.md`; `plan.md`; `tasks.md` | WeChat draft MCP roadmap | recorded-only | 后续 facade 依赖本文契约 |
| convention | 错误响应使用 remediation fields | 新增错误上下文字段必须是 optional，并保留旧 `code/message/details` 可读性。 | `result-types.ts`; `contracts.py`; tests | WeChat draft MCP and Hermes workflow tools | recorded-only | 新工具沿用同一 envelope |
| gotcha | WeChat 图片限制不能混用接口 | 正文图继续按 `uploadimg` 1MB 处理；封面继续按 `thumb` 64KB，切 image 通道必须先 live 验证。 | `plan.md` Sources; `AssetSourceLoader.ts` | WeChat asset handling | recorded-only | `wechat-draft-asset-preflight` |
| follow-up | typed article document tools | `content_text` object/string 问题无法仅靠文档完全消除；下一步应暴露 document builder/render tools，由服务端处理 stringify/render。 | `docs/article-document-artifact-example.md`; `verify-evidence.md` | article document handoff | recorded-only | `wechat-article-document-tools` |

## Commit Result

| Field | Value |
|---|---|
| Status | not_submitted |
| Commit Hashes | 无 |
| Commit Messages | 无 |
| Included Files | 无 |
| Excluded / Remaining Files | 当前工作区仍有本 feature 代码、测试、文档、roadmap diff，以及若干与本 feature 无关或未确认归属的 untracked 文件。 |
| Reason | SDD closeout 不自动提交；提交需要用户明确确认和 commit plan。 |

## Completion Record

- **最终结论**: PASS
- **完成依据**: FR-001 到 FR-006 均有文件和测试证据；三维 Verdict 全 PASS；workflow replay 和 bugfix closure 已记录。
- **阻塞项**: 无。
- **延后项**: typed article document tools、asset preflight/compression、publish-ready facade、generic Hermes versioning/diff、cover channel live verification、draft CRUD。
- **退役结论**: 旧 internal `T013 limitation` 用户可见错误已退役；底层工具保留且契约增强。
- **提交结论**: not_submitted。
- **后续动作**: 回到 roadmap，启动 `wechat-article-document-tools` 的 specify 阶段。
