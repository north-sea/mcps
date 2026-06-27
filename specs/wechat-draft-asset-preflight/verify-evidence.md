# Verify Evidence: WeChat Draft Asset Preflight

**Workspace**: `wechat-draft-asset-preflight`
**Created**: 2026-06-27
**Status**: pass

---

## Baseline / Failed Behavior

| Case | Before Behavior | Evidence Source | After Guard |
|---|---|---|---|
| No standalone preflight | Asset loading/validation only happens through `wechat_upload_asset` and `AssetSourceLoader.load`. | `createMcpServer.ts`, `AssetSourceLoader.ts` before this feature | Add `wechat_preflight_asset` and service/loader preflight path. |
| Opaque local path diagnostics | No asset root, missing file, and path escape are upload-time errors. | Existing `AssetSourceLoader.test.ts` | Return accepted prefixes and actionable reason. |
| Manual compression retries | Oversized assets only fail validation; no transform recommendation is returned. | Existing cover size test | Return recommendation, without real compression in MVP. |
| No image processing dependency | Package has no `sharp`/`jimp` dependency. | `packages/wechat-draft/package.json` | Keep MVP recommendation-only. |

---

## Failed Attempt Ledger

| Time | Attempt | Result | Decision |
|---|---|---|---|
| 2026-06-27 | Considered real compression in this feature. | Rejected for MVP: no image dependency, Docker/runtime implications. | Return transform recommendations only. |
| 2026-06-27 | Considered changing WeChat limits for better operator UX. | Rejected: body 1MB and cover thumb 64KB remain official/current path constraints. | Keep constraints unchanged. |

---

## Verification Runs

| Time | Command | Result | Notes |
|---|---|---|---|
| 2026-06-27 | `pnpm --filter @mcps/wechat-draft build` | PASS | TypeScript build passed after schemas, loader preflight, service gate, MCP registration, docs, and tests. |
| 2026-06-27 | `pnpm --filter @mcps/wechat-draft test` | PASS | 58 tests passed, including loader preflight tests, service preflight/upload-gate tests, and MCP tool discovery. |
| 2026-06-27 | `git diff --check` | PASS | No whitespace errors. |

---

## Diffusion Check

Findings:

- `wechat_preflight_asset` is registered as a side-effect-free MCP tool.
- `wechat_upload_asset(preflight=true)` runs preflight before adapter upload and skips the adapter on invalid assets.
- Preflight diagnostics include accepted local path prefixes rather than raw resolved paths.
- Body image and cover image constraints remain unchanged: body image max 1MB; cover image max 64KB JPEG/thumb.
- No image processing dependency was added to `packages/wechat-draft/package.json`.
- Docs now recommend `wechat_preflight_asset` before upload and explicitly state real compression is not implemented in this feature.

---

## Remaining Risk

- This feature intentionally does not compress images. It provides recommendations and diagnostics; actual transform output remains a future feature.
- Dimension detection remains omitted in MVP because no image metadata dependency was introduced.
