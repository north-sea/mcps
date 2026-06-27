# Implementation Plan: WeChat Draft Agent Contract Hardening

**Workspace**: `wechat-draft-agent-contract-hardening` | **Date**: 2026-06-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/wechat-draft-agent-contract-hardening/spec.md`

---

## Summary

Harden the existing WeChat draft MCP and hermes-db workflow artifact contracts by adding discoverable constraints, actionable remediation fields, explicit idempotency/conflict outcomes, and corrected content handoff documentation. The plan uses backward-compatible extension of current result schemas and repositories; it does not introduce new tool versions, E2E draft facades, image compression, or generic artifact versioning.

---

## Architecture Overview

The change stays inside the current MCP/tool boundary:

```text
Agent
  -> wechat_list_accounts
       -> WechatDraftService
       -> AccountConfig + AssetSourceLoader static constraints
       <- account capabilities + constraints

Agent
  -> wechat_upload_asset / wechat_validate_publish_artifact / wechat_create_draft
       -> Result/Error envelope with remediation fields
       -> DraftWorkflow phase-aware failures
       -> DraftPayloadBuilder content_text/content_ref guard
       <- success or actionable error

Agent
  -> hermes upsert_workflow_artifact
       -> workflow_repo.upsert_artifact
       <- created / idempotency_hit / conflict context
```

No storage migration is planned. The DB already stores workflow runs and artifacts; this feature changes what the tools return and how errors are mapped, not the durable schema.

---

## Architecture Reference

| 参考模式 / 模板 | 来源 URL | 适配点 | 不适配点 | 当前阶段 |
|-----------------|----------|--------|----------|----------|
| Pipe-and-filter / staged workflow | https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md | 当前 draft flow 已是 validate -> payload build -> adapter -> ledger 的阶段链，phase-aware errors 能直接贴合。 | 不引入消息队列、异步 orchestrator 或 workflow engine。 | MVP hardening |
| API gateway style error envelope | UNVERIFIED | 统一错误外壳便于 agent 恢复和上层调用。 | 不做独立 gateway，不新增 transport 层。 | MVP hardening |

---

## Producer-Consumer Matrix

| Producer | Artifact | Consumer | Consumption Proof |
|---|---|---|---|
| `WechatDraftService.listAccounts` | `AccountConstraints` | Agent preflight before upload/create draft | Contract/unit test asserts constraints match `AssetSourceLoader` enforced limits. |
| `AssetSourceLoader` / adapter error mapping | `ToolErrorEnvelope` with remediation fields | Agent retry/recovery loop | Tests assert asset size/path/mime/auth failures include `next_action`, `remediation_hint`, and `retryable`. |
| `DraftPayloadBuilder.extractContent` | content contract failure | `DraftWorkflow` / `wechat_create_draft` response | Test with content-ref-only artifact returns public remediation, not `T013`. |
| `workflow_repo.upsert_artifact` | `ArtifactUpsertOutcome` | hermes MCP tool caller | Repository/tool tests assert created, idempotency hit, and conflict cases expose hash/context. |
| docs canonical example | executable tool-call shape | Agents and maintainers | Documentation test or static review verifies `content_text` string/object boundary is explicit. |

**孤儿 artifact 处理**: `ArtifactUpsertOutcome` must be consumed by the hermes MCP tool response in the same feature. If versioning is needed beyond the outcome fields, it is handed off to `hermes-artifact-versioning-and-diff`.

---

## Quality Attribute Targets

| 属性 | 目标 | 设计影响 | 验证方式 |
|------|------|----------|----------|
| 可恢复性 | Common failures include next action and retryability | Extend existing error helpers rather than returning raw messages | Error contract tests |
| 一致性 | Exposed constraints match enforced validators | Define constraints from shared constants/helpers, not duplicated prose | Unit test drift checks |
| 向后兼容 | Existing callers can still read `success/data` and `error/code/message/details` | New fields are optional additions | Existing tests remain passing |
| 安全性 | Errors do not leak tokens, full private paths, or raw SQL | Preserve current sanitization and add tests for new details | Redaction/error mapping tests |
| 可演进性 | Later document tools and publish-ready facade reuse the same contracts | Keep field names generic but minimal | Plan/tasks check no second error schema appears |

---

## Bugfix Strategy

| Field | Value |
|---|---|
| Observed Behavior | Agents learned hidden constraints through repeated failures: JSON `content_text` shape confusion, content-ref-only draft failure, silent artifact idempotency hit, raw FK/conflict errors, and internal `T013` wording. |
| Expected Behavior | Agents can discover constraints before write calls and recover from common failures using structured remediation fields. |
| Reproduction Status | reproducible for code-level cases: content-ref-only path, asset size/mime/path guards, artifact id/hash conflict, idempotency hit. JSON parsing root cause is partially unknown and must be narrowed in implementation. |
| Root Cause Hypothesis | Tool contracts expose implementation details and omit state transition context; examples also blur string-vs-object boundaries. Hermes artifact upsert currently optimizes for idempotent persistence but does not report skipped update semantics. |
| Fix Boundary | Extend contracts, errors, tests, and docs. Do not add E2E facade, compression, draft CRUD, generic versioning, or note skill migration. |
| Failed Attempt Handling | If a failing case remains ambiguous, add it to the feature tests or docs with explicit "unsupported/unknown" status before further edits. Do not paper over by adding broad `force_update`. |
| Regression Guard Strategy | Unit/contract tests for account constraints, error envelope fields, content-ref-only validation, upsert idempotency hit, artifact conflict, and doc example shape. |
| Diffusion Check Strategy | Check all WeChat MCP tool responses and hermes workflow artifact tools for raw internal errors or non-actionable messages. |
| Verification Path | Before/after proof: old cases return raw/non-actionable messages; new cases return stable code + remediation fields while existing build/test still pass. |

---

## Capacity / Scale Notes

- **规模假设**: Human/agent-triggered draft preparation, low QPS.
- **读写特征**: Read-heavy preflight plus low-volume writes to hermes-db and WeChat adapter.
- **失败代价**: Wrong or unclear failures cause repeated external calls, polluted artifact history, and operator time loss.
- **YAGNI**: No queue, cache, version graph, DSL, or full workflow engine. Use existing schemas, repositories, and tests.

---

## Lightweight ADR

| 决策 | 背景 | 候选 | 结论 | 代价 | 来源 |
|------|------|------|------|------|------|
| ADR-001: Extend existing result envelopes | Existing MCP tools already return structured result/error objects. | A: optional fields on current envelope; B: v2 tools; C: docs-only. | Choose A. It is compatible and fixes agent recoverability without tool churn. | Field names must stay disciplined and documented. | UNVERIFIED |
| ADR-002: Do not implement `force_update` | Artifact upsert conflicts are currently ambiguous, but blind overwrite weakens audit semantics. | A: raw `force_update`; B: explicit outcome + later versioning; C: always new artifact id. | Choose B. This feature reports context and remediation; versioning is conditional follow-up. | Some agents still need one extra call to create a new version/id. | UNVERIFIED |
| ADR-003: Keep WeChat media limits conservative | WeChat docs distinguish permanent image, thumb, and content image APIs. | A: expose current enforced limits; B: relax body image to permanent image limit; C: switch cover channel now. | Choose A. Body `uploadimg` remains <1MB; cover thumb remains 64KB until live proof supports another channel. | Operator-friendly image handling waits for asset preflight/compression feature. | WeChat official docs listed in Sources |

---

## Key Design Decisions

### Decision 1: Add optional remediation fields to existing errors

- **背景**: Existing WeChat result types already have `error.code/message/details`; hermes ToolError has `error/message/field/details`.
- **选项**:
  - A: Add optional `next_action`, `remediation_hint`, `retryable`, `current_phase` to the existing envelope.
  - B: Add new `*_v2` tool outputs.
  - C: Keep outputs unchanged and improve docs only.
- **结论**: Choose A. It provides value to agents with minimal client breakage.
- **影响**: Update schema definitions and helpers first, then migrate specific error sites.
- **来源**: UNVERIFIED.

### Decision 2: Generate account constraints from code-owned constants/helpers

- **背景**: Hidden image/path limits caused avoidable retries.
- **选项**:
  - A: Export a constraints helper from `AssetSourceLoader` or adjacent module and use it in both validation and `listAccounts`.
  - B: Duplicate constraints in `WechatDraftService.listAccounts`.
- **结论**: Choose A. It prevents drift.
- **影响**: May require moving size/MIME constants from private file scope to a typed helper.
- **来源**: WeChat official docs for media limits; current `AssetSourceLoader` guards.

### Decision 3: Treat content-ref-only as unsupported-but-actionable

- **背景**: `DraftPayloadBuilder` currently throws an internal `T013` message.
- **选项**:
  - A: Add content_ref dereference now.
  - B: Keep unsupported, but validate and return remediation.
- **结论**: Choose B. Dereference belongs to a later content/document feature.
- **影响**: `wechat_validate_publish_artifact` and/or `create_draft` must catch and map the condition into public remediation.
- **来源**: current code; spec out-of-scope.

### Decision 4: Report hermes upsert outcomes without changing storage semantics

- **背景**: Same hash currently short-circuits, same id/different hash raises `artifact_id_conflict`.
- **选项**:
  - A: Keep repository return shape and infer in tool.
  - B: Return explicit repository outcome enum/data.
  - C: Add overwrite mode.
- **结论**: Choose B if implementation impact stays small; otherwise A with equivalent tool-level context. Do not choose C in this feature.
- **影响**: Tests must cover created, idempotency hit, and conflict.
- **来源**: current `workflow_repo.upsert_artifact`.

---

## Module Design

### Module: WeChat Account Constraints

**职责**: Expose current account/tool input constraints through `wechat_list_accounts`.

**改动概述**:

- Add a typed `constraints` object to `ListAccountsOutputSchema`.
- Move or export current asset limits/MIME/source semantics from `AssetSourceLoader` into a shared helper.
- Include account-neutral constraints for body image, cover image, content HTML, and local path source support.

**关键接口 / 行为**:

```text
account.constraints.body_image = {
  max_bytes: 1048576,
  mime_types: ["image/jpeg", "image/png"],
  source_types: ["remote_url", "local_path"],
}

account.constraints.cover_image = {
  max_bytes: 65536,
  mime_types: ["image/jpeg"],
  media_type: "thumb",
}
```

**YAGNI stop**: Layer 4/6. Reuse existing validation constants and zod schemas; do not add runtime policy storage or account-specific override until needed.

**注意事项**:

- Body image must stay aligned with WeChat `media/uploadimg` <1MB.
- Permanent `image` 10M does not imply body image limit.
- Cover channel remains `thumb` until live proof supports a different path.

### Module: WeChat Error Envelope

**职责**: Add actionable context to WeChat MCP errors while preserving existing result shape.

**改动概述**:

- Extend `ErrorResultSchema` and `createErrorResult` with optional fields.
- Add small helpers for common remediation patterns instead of hardcoding strings everywhere.
- Map asset, adapter, artifact validation, and workflow phase failures.

**关键接口 / 行为**:

```text
error = {
  code,
  message,
  details?,
  next_action?,
  remediation_hint?,
  retryable?,
  current_phase?,
}
```

**YAGNI stop**: Layer 6. A small helper is enough; no separate error class hierarchy or registry unless tests show repetition.

**注意事项**:

- Continue sanitizing adapter details.
- Do not expose raw SQL, private local paths, auth headers, or internal ticket names.

### Module: Content Contract Guard

**职责**: Make `content_text` / `content_ref` behavior explicit and recoverable.

**改动概述**:

- Replace `T013` throw text with a public error type or error mapping.
- Ensure validate/create draft returns a consistent response for content-ref-only artifacts.
- Update examples so `content_text` string-vs-object boundary is explicit.

**YAGNI stop**: Layer 1/6. Do not implement content_ref dereference in this feature; the need is to expose the unsupported state clearly.

### Module: Hermes Artifact Upsert Outcome

**职责**: Report idempotency and conflict semantics to agents.

**改动概述**:

- Adjust `workflow_repo.upsert_artifact` or tool wrapper to produce outcome metadata.
- For same hash: return `idempotency_hit=true` and `skipped_update_reason`.
- For same artifact id/different hash: return error with existing/provided hash summary and remediation.
- Keep storage immutable; do not add `force_update`.

**关键接口 / 行为**:

```text
{
  artifact_id,
  created,
  idempotency_hit?,
  skipped_update_reason?,
  existing_content_hash?,
  provided_content_hash?,
}
```

**YAGNI stop**: Layer 3/6. Preserve existing database uniqueness/hash semantics; only expose the state already available.

### Module: Documentation And Contract Tests

**职责**: Prevent future agent-facing contract drift.

**改动概述**:

- Update canonical article artifact docs and happy path examples.
- Add tests for constraints, remediation fields, and upsert outcomes.
- Add diffusion checks across WeChat MCP tools and hermes workflow artifact tools.

**YAGNI stop**: Layer 5/6. Static docs plus focused tests are sufficient; no doc generator or schema publication pipeline.

---

## Data Model

No durable database schema change. The plan introduces API/tool contract structures only:

- `AccountConstraints`
- `ToolErrorEnvelope` optional fields
- `ArtifactUpsertOutcome`

These are specified in schemas/tool contracts and tests. A separate `data-model.md` is not needed unless implementation discovers a durable storage change.

---

## Project Structure

```text
packages/wechat-draft/src/schemas/result-types.ts
packages/wechat-draft/src/schemas/tool-schemas.ts
packages/wechat-draft/src/service/WechatDraftService.ts
packages/wechat-draft/src/service/errorMapping.ts
packages/wechat-draft/src/wechat/AssetSourceLoader.ts
packages/wechat-draft/src/wechat/DraftPayloadBuilder.ts
packages/wechat-draft/src/workflow/DraftWorkflow.ts
packages/hermes-db/src/hermes_db_mcp/contracts.py
packages/hermes-db/src/hermes_db_mcp/repositories/workflow_repo.py
packages/hermes-db/src/hermes_db_mcp/tools/workflow_artifacts.py
docs/article-document-artifact-example.md
specs/wechat-draft-agent-contract-hardening/tasks.md
```

---

## Risks and Tradeoffs

- **Response compatibility**: Optional fields should be safe, but some strict clients may snapshot exact response shapes. Mitigation: keep existing required fields unchanged and update tests intentionally.
- **Hermes scope creep**: Artifact versioning is tempting but outside this feature. Mitigation: only expose existing state and remediation.
- **Constraint drift**: Duplicated constants would recreate the same problem. Mitigation: derive list output from validation helper/constants.
- **Unconfirmed WeChat cover behavior**: Do not switch media channel in this feature.
- **JSON parsing root cause**: If the root is outside this repo, docs and typed future tools may be the short-term mitigation.

---

## Evolution Path

- **MVP**: Optional remediation fields, constraints output, explicit upsert outcomes, doc fixes.
- **成长期**: `wechat-article-document-tools` exposes typed build/render/preview tools to remove manual JSON string handling.
- **成熟期**: `wechat-draft-publish-ready-facade` composes validated publish-ready inputs into one draft creation flow; generic artifact versioning moves to hermes-db if needed.

---

## Anti-Pattern Check

- 是否把成熟期架构套到了 MVP：否。No workflow engine, no queue, no version graph.
- 是否引用了外部模式但没有适配检查：否。Architecture references are used only as framing.
- 是否新增未记录的状态、依赖、缓存、队列或失败模式：否。New fields describe existing states/failures.
- 是否重复实现 `note-skill-migration-roadmap` 能力：否。This plan excludes skill migration, agents ownership, writing generation, and Library/Memory routing.

---

## Verification Strategy

1. Run existing baseline:
   - `pnpm --filter @mcps/wechat-draft build`
   - `pnpm --filter @mcps/wechat-draft test`
   - relevant hermes-db Python tests through existing project command after tasks identify the exact target.
2. Add/verify WeChat tests:
   - `wechat_list_accounts` returns constraints matching asset validators.
   - `wechat_upload_asset` size/mime/path failures include remediation fields.
   - `wechat_create_draft` content-ref-only artifact returns actionable error without `T013`.
   - Existing HTTP MCP smoke still passes.
3. Add/verify hermes-db tests:
   - `upsert_workflow_artifact` created path.
   - Same hash idempotency hit includes skipped reason.
   - Same artifact id/different hash returns conflict context and remediation.
   - Missing workflow run maps to a next action instead of raw FK detail where the tool can catch it.
4. Documentation check:
   - Canonical examples distinguish JSON object for readability from actual string payloads.
   - Happy path includes constraints preflight and common recovery actions.

---

## Stage Readiness

- 是否需要 `data-model.md`: 不需要。没有 durable schema/storage change；API contract structures are covered in this `plan.md` and implementation schemas.
- 下一步建议：`tasks`
- 阻塞项（如有）：无。Implementation can proceed once tasks are sliced by contract area.

---

## Design Artifacts

| 产物 | 是否需要 | 说明 |
|------|---------|------|
| plan.md | 必须 | 本文件 |
| data-model.md | 不需要 | 不改变持久实体、关系或存储 schema |
| tasks.md | 后续阶段生成 | 需要按 vertical slice 拆出 WeChat constraints/error、hermes upsert outcome、docs/tests |
| acceptance.md | 后续阶段生成 | 因 traits 命中，closeout 需要三维 Verdict 和 bugfix closure |

---

## Sources

| 决策 | 来源 URL | 备注 |
|------|---------|------|
| WeChat permanent material image/thumb limits | https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial.html | Re-fetched 2026-06-27. Image 10M; thumb 64KB JPG; content images use uploadimg. |
| WeChat content image limit | https://developers.weixin.qq.com/doc/service/api/material/permanent/api_uploadimage.html | Re-fetched 2026-06-27. `uploadimg` supports jpg/png under 1MB. |
| WeChat draft add fields | https://developers.weixin.qq.com/doc/service/api/draftbox/draftmanage/api_draft_add.html | Re-fetched 2026-06-27. News article uses `thumb_media_id`; content constraints documented. |
| Architecture quality gate | /Users/yqg/.agents/skills/sdd/references/architecture-quality-gate.md | Used for lightweight ADR and quality attribute checks. |
| YAGNI ladder | /Users/yqg/.agents/skills/sdd/references/yagni-ladder.md | Used to avoid E2E facade/versioning scope creep. |
