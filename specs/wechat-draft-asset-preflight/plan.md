# Implementation Plan: WeChat Draft Asset Preflight

**Workspace**: `wechat-draft-asset-preflight` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/wechat-draft-asset-preflight/spec.md`

---

## Summary

Add a side-effect-light asset preflight layer that probes local/remote image sources, reports constraint fit, returns transform recommendations, and makes upload rejections more actionable. This MVP will not implement real image compression because `@mcps/wechat-draft` currently has no image processing dependency; adding `sharp` or similar is a heavier packaging/runtime decision and should be deferred until the preflight contract is proven.

---

## Architecture Overview

```text
Agent
  -> wechat_preflight_asset
    -> AssetSourceLoader probe/preflight path
      -> local path diagnostics / remote fetch diagnostics
      -> shared WeChat constraints
      -> transform recommendation
  -> optional wechat_upload_asset(preflight=true)
    -> same preflight diagnostics before adapter upload
    -> existing adapter upload only if preflight passes
```

Preflight and upload use the same source loading and constraints. Upload remains the only WeChat side-effecting path. Preflight does not upload, write hermes-db, or create drafts.

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| `wechat_preflight_asset` | `AssetPreflightResult` | Agent, `wechat_upload_asset`, article-document tools | Tests assert pass/fail diagnostics and upload-ready metadata. |
| `wechat_preflight_asset` | `TransformRecommendation` | Agent/operator and future compression feature | Tests assert oversized cover/body produce recommendations without changing source files. |
| `wechat_upload_asset(preflight=true)` | Preflight summary embedded in success/error response | Agent and article document asset metadata construction | Upload tests assert adapter is not called on preflight failure and error details include constraints. |

**孤儿 artifact 处理**: Transform recommendation is a diagnostic output, not a durable artifact. Real transformed assets are deferred until compression implementation is explicitly added.

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 可恢复性 | Every rejected asset includes next action and constraint diagnostics | Shared preflight result and error mapper | Unit tests for size, MIME, path, remote fetch failures |
| 安全性 | No sensitive full path/token/header leakage | Return accepted prefixes and source type, not raw private absolute paths | Sanitization assertions |
| 一致性 | Preflight and upload use same constraints | Extract helper from `AssetSourceLoader` | Constraints drift tests |
| 成本 | Avoid unnecessary heavy image processing dependency | No `sharp`/`jimp` in MVP | package diff review |
| 可演进性 | Future compression/facade can consume preflight output | Typed result includes recommendations and upload-ready metadata | Schema tests |

---

## Bugfix Strategy

| Field | Value |
|---|---|
| Observed Behavior | Agents learn image size/MIME/path failures only after upload attempts, and local path failures can look like raw filesystem errors. |
| Expected Behavior | Agents can preflight assets and receive actionable diagnostics before upload. |
| Reproduction Status | reproducible with existing `AssetSourceLoader` tests for large cover, unsupported MIME, no asset root, path escape, remote fetch. |
| Root Cause Hypothesis | Source loading and constraint validation are coupled to upload materialization; there is no read-only diagnostic surface. |
| Fix Boundary | Add preflight/probe API/tool and reuse its diagnostics in upload failures; do not implement real compression or change WeChat limits. |
| Failed Attempt Handling | If preflight and upload diagnostics drift, add shared helper and a regression test before closeout. |
| Regression Guard Strategy | Tests for local path, remote URL, MIME, size, recommendation output, upload preflight gate, and no adapter call on preflight failure. |
| Diffusion Check Strategy | Search asset error paths for raw `path`, `url`, `realpath`, and unstructured `AssetSourceError` leakage. |
| Verification Path | `pnpm --filter @mcps/wechat-draft build`; `pnpm --filter @mcps/wechat-draft test`; `git diff --check`. |

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001 no real compression in MVP | No image dependency exists; adding native image processing affects Docker/runtime | A: recommendation only; B: add sharp; C: hand-roll compression | Choose A | Operators still need external compression for now | local package.json |
| ADR-002 independent preflight tool plus upload flag | Agents need dry-run, upload needs better diagnostics | A: separate tool only; B: upload flag only; C: both | Choose C | Slightly larger API surface | local tool contract |
| ADR-003 keep official constraints | Prior review found body 10MB claim incorrect for `uploadimg` | A: keep current 1MB/64KB; B: relax limits | Choose A | HD cover remains constrained until verified | prior official-doc verification in roadmap |
| ADR-004 local path diagnostics by prefix, not raw path | Raw paths can leak host/container details | A: return accepted prefixes/status; B: return full realpath | Choose A | Less low-level debugging detail | contract-hardening security rule |

---

## Module Design

### Module: AssetSourceLoader Preflight

**职责**: Probe a source and validate it against usage constraints without requiring adapter upload.

**改动概述**:

- Add `preflight(input)` method returning `AssetPreflightResult`.
- Internally reuse local/remote loading where feasible, but catch `AssetSourceError` and convert to diagnostics.
- Add constraint helper for `usage` to avoid duplicating size/MIME logic.
- Include source diagnostics:
  - `source_type`
  - `readable` / `fetch_ok`
  - sanitized `accepted_path_prefixes`
  - status/statusText for remote
  - detected filename/MIME/size
  - pass/fail reasons
  - recommendation.

**YAGNI stop**: Layer 5/6. Reuse existing loader/fetch/readFile; no image dimension parser if it requires new binary parsing dependency. Dimensions can be optional/unknown.

### Module: Tool Schemas

**职责**: Define preflight input/output and optional upload preflight flag.

**改动概述**:

- Add `PreflightAssetInputSchema`, `PreflightAssetOutputSchema`.
- Add optional `preflight` or `preflight_only` flag to `UploadAssetInputSchema`.
- Output should be stable enough for agents:
  - `valid`
  - `diagnostics`
  - `constraints`
  - `recommendations`
  - `upload_ready`.

**YAGNI stop**: Layer 4, zod schemas already used.

### Module: WechatDraftService

**职责**: Expose `preflightAsset` and make `uploadAsset` use preflight diagnostics on demand and on failure.

**改动概述**:

- Add `preflightAsset(input): Promise<Result<PreflightAssetOutput>>`.
- In `uploadAsset`, if `preflight=true`, run preflight before adapter upload; if invalid, return preflight-style error and do not call adapter.
- On existing upload failures, include sanitized preflight details where possible.

**YAGNI stop**: Layer 5/6. No new workflow state.

### Module: MCP Registration

**职责**: Register `wechat_preflight_asset`.

**改动概述**:

- Add read-only/non-destructive tool description.
- Use existing result helper and logging.
- Keep `wechat_upload_asset` as existing side-effecting tool.

**YAGNI stop**: Layer 3/4, reuse current MCP registration pattern.

### Module: Tests And Docs

**职责**: Prove diagnostics and guard behavior.

**改动概述**:

- Extend `AssetSourceLoader.test.ts` for preflight pass/fail cases.
- Extend `WechatDraftService.uploadAsset.test.ts` for `preflight=true` and no adapter call on invalid source.
- Add HTTP/MCP tool discovery assertion for `wechat_preflight_asset`.
- Update docs to recommend preflight before upload.

**YAGNI stop**: Layer 4, current node test runner.

---

## Risks and Tradeoffs

- Without real compression, the feature does not fully solve image preparation. It does remove guesswork and creates a typed contract for a later transform implementation.
- Remote preflight may need to download images when content-length is missing. The plan should cap reads using existing upload limits where possible.
- Local path diagnostics must be useful without leaking private paths. Returning accepted prefixes and source type is the intended compromise.
- Dimension detection is optional in MVP; adding it without a library would risk fragile binary parsing.

---

## Evolution Path

- **MVP**: Probe/preflight, recommendations, upload preflight gate, better diagnostics.
- **成长期**: Add explicit compression with a justified dependency and runtime output path.
- **成熟期**: Publish-ready facade uses preflight + compression + upload as one internal asset preparation pipeline.

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。No image processing pipeline or queue.
- 是否引用了外部模式但没有适配检查：否。Plan is local-code driven.
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。No durable state or new dependency in MVP.
- 是否重复实现 article-document tools：否。This only produces asset metadata/diagnostics for those tools.

---

## Verification Strategy

- `pnpm --filter @mcps/wechat-draft build`
- `pnpm --filter @mcps/wechat-draft test`
- Test cases:
  - local valid body/cover preflight passes.
  - local no asset root/path escape/missing file returns accepted prefixes and next action.
  - remote invalid protocol/fetch status/content type/oversize returns structured diagnostics.
  - oversized body/cover returns transform recommendation.
  - `wechat_upload_asset(preflight=true)` skips adapter on invalid preflight.
  - existing upload behavior remains compatible without preflight flag.
  - MCP listTools includes `wechat_preflight_asset`.
- Diffusion:
  - Search for raw path/url leakage in asset error details.
  - Confirm body and cover constraints remain unchanged.

---

## Stage Readiness

- 是否需要 `data-model.md`: 不需要。No durable storage or entity relationship changes.
- 下一步建议：`tasks`
- 阻塞项：无。Compression is explicitly deferred to a later feature unless user changes scope.

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| Existing constraints and loader | local code | `packages/wechat-draft/src/wechat/AssetSourceLoader.ts` |
| No image dependency | local package | `packages/wechat-draft/package.json` |
| Official WeChat constraints | local roadmap evidence | `wechat-draft-agent-contract-hardening` planning notes |
