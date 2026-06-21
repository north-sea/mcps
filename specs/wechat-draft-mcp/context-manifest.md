# Context Manifest: WeChat Draft MCP

**Workspace**: `wechat-draft-mcp`
**Created**: 2026-06-21
**Last Updated**: 2026-06-21
**Status**: active (Phase 2 完成，Phase 3 进行中)

## Phase Progress

- **Phase 0**: ✅ 完成（T001a/T001d 配置固化，T001b 移到 Phase 3）
- **Phase 1**: ✅ 完成（T005/T006/T007 MCP 骨架与工具契约）
- **Phase 2**: ✅ 完成（T008-T010 Hermes-db Artifact 契约）
- **Phase 3**: 🔄 进行中（T011-T013a ECS Adapter、API Client、Token）
- **Phase 4**: ⏳ 待开始（T014-T018 草稿写入闭环）
- **Phase 5**: ⏳ 待开始（T019-T022 验证与收口）

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-mcp/spec.md` | Defines user stories, safety boundaries, P1 requirements, and out-of-scope publish behavior. | implement | yes |
| `specs/wechat-draft-mcp/plan.md` | Defines architecture decisions, official API module boundaries, ECS adapter boundary, WeChat-ready artifact contract, and verification path. | implement | yes |
| `specs/wechat-draft-mcp/tasks.md` | Defines execution order, smoke-test gates, slices, artifact/credential dependencies, and verification requirements. | implement | yes |
| `specs/wechat-draft-mcp/data-model.md` | Defines AccountConfig, ECS adapter config, API credentials, AccessTokenState, PublishReadyArtifact, WechatAssetManifest, DraftJob, ArticleLedgerUpdate, adapter/WeChat API errors, and state transitions. | implement | yes |
| `specs/wechat-draft-mcp/official-api-research.md` | Records official WeChat API evidence for AccessToken, draft/add, draft/batchget, and draft payload asset constraints. | implement | yes |
| `specs/wechat-draft-mcp/smoke-evidence.md` | Records still-valid hermes-db artifact/ledger readiness. | implement | no |

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-draft-mcp/spec.md` | Verify P1 scenarios, safety boundaries, and non-goals. | verify | yes |
| `specs/wechat-draft-mcp/plan.md` | Check architecture drift, ADR compliance, and quality attributes. | verify | yes |
| `specs/wechat-draft-mcp/tasks.md` | Check task completion, skipped tasks, and evidence coverage. | verify | yes |
| `specs/wechat-draft-mcp/data-model.md` | Verify status transitions, WeChat-ready artifact contract, ECS adapter config, and article ledger update match the modeled entities. | verify | yes |
| `specs/wechat-draft-mcp/official-api-research.md` | Verify implementation matches current official API paths, payload constraints, and source links. | verify | yes |
| `specs/wechat-draft-mcp/smoke-evidence.md` | Verify hermes-db artifact/ledger readiness evidence. | verify | no |

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `specs/wechat-draft-mcp/official-api-research.md` | Records the current API-only decision and official source evidence. | plan / implement / verify | yes |
| Ali ECS adapter decision | User selected option A: NAS MCP calls a minimal Ali ECS WeChat API adapter; WeChat IP whitelist uses ECS public IP/EIP, not NAS home IP or Tailscale IP. | plan / implement / verify | yes |
| WeChat-ready asset decision | User confirmed `wechat_create_draft` should not download/upload images; MCP only accepts artifacts whose body image URLs and cover `thumb_media_id` are already prepared for WeChat. | plan / implement / verify | yes |
| `https://developers.weixin.qq.com/doc/subscription/api/base/api_getaccesstoken.html` | Official AccessToken source. | plan / implement / verify | yes |
| `https://developers.weixin.qq.com/doc/service/api/draftbox/draftmanage/api_draft_add.html` | Official add-draft source. | plan / implement / verify | yes |
| `https://developers.weixin.qq.com/doc/service/api/draftbox/draftmanage/api_draft_batchget.html` | Official draft-list source. | plan / verify | yes |
| `https://developers.weixin.qq.com/doc/service/api/material/permanent/api_uploadimage.html` | Official article-image upload source. | plan / verify | yes |
| `https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial.html` | Official permanent-material upload source. | plan / verify | yes |

## Rules

- Required local context must exist before implementation or verification.
- Do not use this manifest as a source-file edit list; implementation still needs local code inspection.
- Do not introduce `.trellis/`, Trellis CLI, hook-based task injection, automatic commits, or external knowledge sync from this manifest.
