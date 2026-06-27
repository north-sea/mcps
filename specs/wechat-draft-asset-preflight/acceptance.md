# Acceptance Record: WeChat Draft Asset Preflight

**Workspace**: `wechat-draft-asset-preflight` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)

## Evidence Table

| Requirement | Evidence | Test or File | Verdict |
|---|---|---|---|
| FR-001 asset preflight | `AssetSourceLoader.preflight`, `WechatDraftService.preflightAsset`, and `wechat_preflight_asset` return source diagnostics, constraints, validation result, and recommendations. | `AssetSourceLoader.ts`; `WechatDraftService.ts`; `createMcpServer.ts`; tests | PASS |
| FR-002 local path diagnostics | Local preflight covers valid file, missing file/no readable source, accepted prefixes, and does not require adapter upload. | `AssetSourceLoader preflight returns accepted prefixes for local_path failures` | PASS |
| FR-003 remote diagnostics | Remote preflight handles HTTP failure status and protocols via mocked fetch. | `AssetSourceLoader preflights remote_url failures` | PASS |
| FR-004 transform recommendation | Oversized cover returns `compress` recommendation with target max bytes and `supported_in_mvp=false`. | `AssetSourceLoader preflight recommends transform for oversized cover` | PASS |
| FR-005 explicit transform boundary | No real compression dependency was added; docs and result mark recommendations only. | `package.json`; `verify-evidence.md`; docs | PASS |
| FR-006 upload preflight guard | `wechat_upload_asset(preflight=true)` skips adapter on invalid preflight and preserves existing upload behavior otherwise. | `WechatDraftService.uploadAsset preflight gate skips adapter on invalid asset`; existing upload tests | PASS |
| FR-007 conservative constraints | Body 1MB and cover 64KB/JPEG/thumb remain unchanged. | `AssetSourceLoader exposes constraints matching enforced guards`; source constants | PASS |
| FR-008 remediation/sanitization | Invalid preflight upload returns `next_action` and preflight details; local diagnostics expose accepted prefixes, not raw realpaths. | upload preflight tests; loader tests | PASS |

## Verdict Summary

| Dimension | Verdict | Notes |
|---|---|---|
| Component capability | PASS | Loader, schemas, service, MCP registration, upload gate, docs, and tests are implemented. |
| Workflow closure | PASS | Agent can preflight assets, receive recommendations, and optionally gate upload before adapter calls. |
| User-visible outcome | PASS | Tool responses expose pass/fail diagnostics and next actions without changing upload limits or silently compressing assets. |

**Overall**: PASS

## Workflow Replay

- **输入摘要**: local_path or remote_url image source with usage `body_image` or `cover_image`.
- **最终 payload 摘要**: `AssetPreflightOutput` with `valid`, `upload_ready`, constraints, diagnostics, issues, and recommendations; upload errors include preflight summary when gated.
- **用户可见结果断言**: Agent can know why an asset will fail and what to do before calling the WeChat adapter.
- **Replay 类型**: fixture/mock. No real WeChat upload is required for preflight.

## Bugfix Closure

| Field | Value |
|---|---|
| Root Cause / Hypothesis | Source loading and constraint validation were coupled to upload, so agents learned failures only through upload attempts. |
| Fix Mechanism | Added standalone preflight, shared constraints, transform recommendation, and upload preflight gate. |
| Prevention Mechanism | Tests cover local/remote diagnostics, oversized recommendations, upload adapter skip, and unchanged constraints. |
| Failed Attempts Summary | Real compression and constraint relaxation were rejected for MVP and recorded as deferred. |
| Regression Guard | `pnpm --filter @mcps/wechat-draft build`; `pnpm --filter @mcps/wechat-draft test`; `git diff --check`. |
| Diffusion Check | Docs point to preflight before upload; no image dependency added; constraints unchanged. |
| Remaining Risk | No real compression or dimension detection in MVP. Agents must transform externally and preflight again. |

## Closeout Checklist

| Item | Status | Evidence / Rationale | Next Step |
|---|---|---|---|
| 旧逻辑、旧路径、fallback 或临时兼容退役 | 已完成 | Upload-only discovery remains supported, but preflight path is now available and documented. | 无 |
| 发布、提交、CI 或 follow-through | 延后 | 未提交、未发布；用户尚未要求 commit。 | 需要提交时先做 commit plan。 |
| 文档、阶段说明、模板或验收记录更新 | 已完成 | Docs, verify evidence, tasks, acceptance, roadmap updated. | 无 |
| ADR、架构债或演进触发信号 | 已完成 | Real compression, dimension detection, cover channel switch remain deferred. | Future compression or publish-ready facade. |
| Knowledge Capture | 已完成 | 见下表；仅记录到本地 acceptance。 | 无 |

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|---|---|---|---|---|---|---|
| decision | Preflight first, no compression dependency | MVP adds diagnostics/recommendations without adding image processing dependencies. | `plan.md`; `package.json`; tests | WeChat draft asset flow | recorded-only | Add compression later if justified |
| convention | Upload preflight gate is opt-in | `wechat_upload_asset` keeps default behavior; `preflight=true` gates adapter upload. | service tests | WeChat upload tool | recorded-only | Future facade should use preflight by default internally |
| gotcha | Official constraints remain conservative | Body images stay 1MB uploadimg; cover stays 64KB JPEG thumb. | tests; docs | WeChat assets | recorded-only | Cover channel switch requires live evidence |

## Commit Result

| Field | Value |
|---|---|
| Status | not_submitted |
| Commit Hashes | 无 |
| Commit Messages | 无 |
| Included Files | 无 |
| Excluded / Remaining Files | 当前工作区仍有本 roadmap 多个 feature 的代码、测试、文档和 specs。 |
| Reason | SDD closeout 不自动提交；提交需要用户明确确认。 |

## Completion Record

- **最终结论**: PASS
- **完成依据**: FR-001 到 FR-008 均有测试或文件证据；三维 Verdict 全 PASS。
- **阻塞项**: 无。
- **延后项**: real compression, image dimension detection, cover image channel switch, publish-ready facade。
- **退役结论**: upload-only trial-and-error path 不再是唯一诊断方式；旧 upload 行为保留兼容。
- **提交结论**: not_submitted。
- **后续动作**: 回到 roadmap，启动 `wechat-draft-publish-ready-facade` 的 specify 阶段。
