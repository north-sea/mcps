# Tasks: WeChat Draft Asset Preflight

**Workspace**: `wechat-draft-asset-preflight` | **Date**: 2026-06-27
**Input**: `specs/wechat-draft-asset-preflight/spec.md` + `plan.md`
**Prerequisites**: spec.md, plan.md

---

## 执行原则

- 先做 probe/preflight 和 diagnostics，不引入真实压缩依赖。
- preflight 和 upload 必须共享约束，不允许 advice 和 enforcement 漂移。
- `wechat_upload_asset` 默认行为保持兼容；`preflight=true` 才启用上传前 gate。
- 不放宽正文 1MB、封面 64KB/JPEG/thumb 限制。
- 不创建草稿、不写 hermes-db、不构造 article document。

---

## Phase 1: Baseline And Contract

**目标**: 固定失败基线和 preflight result 契约。

- [x] T001 [Bugfix] 记录 before evidence 和 failed-attempt ledger
  - scope: `specs/wechat-draft-asset-preflight/verify-evidence.md`
  - slice: 证明当前只有 upload-time loading/validation，没有 dry-run preflight；路径/远程/大小失败需通过 upload 路径触发。
  - blocked_by: none
  - maps_to: Bugfix Context / US1 / US3
  - verify: evidence 记录 current tools、loader behavior、no image dependency、deferred compression decision。

- [x] T002 [Foundation] 定义 preflight schemas and upload flag
  - scope: `tool-schemas.ts`, exported types
  - slice: `wechat_preflight_asset` 有 typed input/output；`wechat_upload_asset` 可接受 backward-compatible `preflight?: boolean`。
  - blocked_by: T001
  - maps_to: FR-001 / FR-006 / ADR-002
  - verify: TypeScript build and schema tests/usage compile.

---

## Phase 2: AssetSourceLoader Preflight Slice

**目标**: 在不调用 adapter 的情况下探测 source 并返回诊断。

- [x] T003 [US1] 实现 local_path preflight diagnostics
  - scope: `AssetSourceLoader.ts`, tests
  - slice: valid local file returns filename/MIME/size/constraints/pass；no asset root、missing file、path escape return accepted prefixes and actionable reason without raw private path.
  - blocked_by: T002
  - maps_to: US1 / FR-001 / FR-002 / NFR-003
  - verify: `AssetSourceLoader.test` covers valid local, no root, missing file, path escape.

- [x] T004 [US1] 实现 remote_url preflight diagnostics
  - scope: `AssetSourceLoader.ts`, tests
  - slice: remote URL returns fetch status/content-type/content-length/size/pass; invalid protocol and HTTP failure are classified.
  - blocked_by: T002
  - maps_to: US1 / FR-001 / FR-003 / NFR-004
  - verify: mocked fetch tests cover success, invalid protocol, HTTP failure, unsupported MIME/oversize.

- [x] T005 [US2/US4] 实现 transform recommendation
  - scope: `AssetSourceLoader.ts`, tests
  - slice: oversized or unsupported assets return recommendation such as compress/resize/convert, while explicitly stating compression is not performed in MVP and constraints remain unchanged.
  - blocked_by: T003, T004
  - maps_to: US2 / US4 / FR-004 / FR-007 / ADR-001 / ADR-003
  - verify: tests assert oversized cover/body produce recommendation and package dependencies remain unchanged.

---

## Phase 3: Service And MCP Tool Slice

**目标**: agent 可以直接调用 preflight tool，并在 upload 中复用 preflight gate。

- [x] T006 [US1] 增加 `WechatDraftService.preflightAsset`
  - scope: `WechatDraftService.ts`, service tests
  - slice: service wraps loader preflight and returns `Result<PreflightAssetOutput>` with remediation envelope for unexpected failures.
  - blocked_by: T005
  - maps_to: FR-001 / FR-008
  - verify: service tests assert success and failure shapes.

- [x] T007 [US1] 注册 `wechat_preflight_asset` MCP tool
  - scope: `createMcpServer.ts`, HTTP MCP smoke
  - slice: MCP `listTools` exposes preflight tool; tool is described as side-effect-free and non-uploading.
  - blocked_by: T006
  - maps_to: US1 / FR-001
  - verify: HTTP MCP smoke asserts tool name exists.

- [x] T008 [US3] 为 `wechat_upload_asset(preflight=true)` 增加 preflight gate
  - scope: `WechatDraftService.uploadAsset`, upload tests
  - slice: if preflight fails, adapter is not called and response includes preflight diagnostics; without flag, existing behavior stays compatible.
  - blocked_by: T006
  - maps_to: US3 / FR-006 / backward compatibility
  - verify: upload tests assert no adapter call on invalid preflight and existing upload tests still pass.

---

## Phase 4: Docs, Diffusion, Verify

**目标**: 文档和证据收口。

- [x] T009 [Docs] 更新 asset/document flow docs
  - scope: `docs/article-document-artifact-example.md` or package docs
  - slice: docs recommend preflight before upload, explain no real compression in MVP, and retain official limits.
  - blocked_by: T007, T008
  - maps_to: US4 / FR-007
  - verify: static review confirms docs mention preflight and deferred compression.

- [x] T010 [Bugfix] 执行 diffusion check
  - scope: asset error paths, docs, `verify-evidence.md`
  - slice: no raw path/url leakage or unstructured asset errors remain in affected preflight/upload paths; deferred compression/channel-switch are recorded.
  - blocked_by: T009
  - maps_to: Bugfix Loop Breaker / NFR-003
  - verify: `rg` findings recorded; unresolved items have roadmap owner.

- [x] T011 [Verify] 运行 build/test and whitespace checks
  - scope: `packages/wechat-draft`, `verify-evidence.md`
  - slice: component and contract tests produce fresh evidence.
  - blocked_by: T010
  - maps_to: Verification Strategy / FR-001..FR-008
  - verify: record `pnpm --filter @mcps/wechat-draft build`, `pnpm --filter @mcps/wechat-draft test`, `git diff --check`.

- [x] T012 [Closeout Prep] 准备 acceptance and roadmap update
  - scope: `acceptance.md`, roadmap
  - slice: closeout can judge PASS/PARTIAL/FAIL and next roadmap feature.
  - blocked_by: T011
  - maps_to: Acceptance Gate / Knowledge Capture
  - verify: evidence table, bugfix closure, remaining risks, and deferred compression are ready.

---

## 依赖与顺序

- 关键路径：T001 -> T002 -> T003/T004 -> T005 -> T006 -> T007/T008 -> T009 -> T010 -> T011 -> T012。
- T003 和 T004 可并行。
- T007 和 T008 可在 T006 后并行。
- T009 必须等 tool/API 名称稳定后再写。

---

## 覆盖检查

| 场景 / 需求 | 对应任务 |
|-------------|----------|
| US1 probe local/remote asset | T002, T003, T004, T006, T007 |
| US2 transform recommendation | T005 |
| US3 upload preflight guard | T008 |
| US4 preserve official constraints | T005, T009, T010 |
| Bugfix loop breaker | T001, T010, T011, T012 |

| 架构决策 / 质量属性 | 对应任务 | 验证任务 |
|----------------------|----------|----------|
| ADR-001 no real compression | T005, T009 | T010, T011 |
| ADR-002 preflight tool + upload flag | T002, T007, T008 | T011 |
| ADR-003 keep constraints | T005, T009 | T011 |
| ADR-004 sanitized local diagnostics | T003, T010 | T011 |
| 可恢复性 | T003-T008 | T011 |
| 安全性 | T003, T004, T010 | T011 |
| 一致性 | T002, T005, T008 | T011 |

---

## Context Manifest

已生成 `context-manifest.md`。本 feature 命中多项 traits，且涉及 upload/preflight 边界和安全诊断，必须保留实现与验证上下文。

---

## Stage Readiness

- 推荐下一步：`verify`
- 阻塞项：无。
- 原因：12/12 tasks 已完成；build PASS，test 58/58 PASS，文档已更新，diffusion check 待验收记录收口。
