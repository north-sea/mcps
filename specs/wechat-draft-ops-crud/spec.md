# Spec: WeChat Draft Ops CRUD

**Workspace**: `wechat-draft-ops-crud`
**Date**: 2026-06-27
**Roadmap**: `wechat-draft-agent-experience-roadmap`
**Status**: draft

## Feature Traits

| Trait | 是否命中 | 依据 |
|---|---|---|
| external-side-effects | ✅ | update/delete 会修改微信草稿箱；首个 slice 应以 read-only 为主。 |
| user-visible-output | ✅ | 返回草稿列表、media_id、标题、更新时间、内容摘要。 |
| multi-stage-workflow | ✅ | 运营校对通常是 list/detail -> inspect -> update/delete。 |
| destructive-action | ✅ | delete/update 需要工具 annotation、确认令牌和恢复说明。 |
| bugfix-loop-breaker | ✅ | 复盘指出“看历史草稿、改草稿、删草稿”缺失，但不能一次性无保护实现破坏性操作。 |

## Problem

The WeChat draft publication path can create drafts, but operators and agents cannot inspect existing WeChat drafts through the MCP. The ECS adapter already exposes `POST /accounts/:account/drafts/batchget` and advertises `draft_batchget`, while `wechat-draft` MCP currently exposes only local job status.

Update/delete are operationally useful but higher risk. They should not be implemented until the read-only inventory path is stable and destructive tool semantics are designed.

## Goals

- Expose a read-only MCP tool for listing WeChat drafts from the adapter batchget endpoint.
- Normalize returned draft summaries for agent/operator inspection without dumping full HTML by default.
- Make account capabilities reflect whether draft batchget is available.
- Define safe boundaries for future update/delete tools, including destructive annotations and operator confirmation.

## Non-Goals

- No update/delete implementation in the first slice.
- No scheduling, group-send, publish, or mass-send.
- No automatic cleanup of remote drafts.
- No live WeChat API call in unit tests.
- No attempt to generate `preview_url` unless the upstream API/adapter provides a verified URL.

## User Stories

### User Story 1 - List Existing Drafts (P1)

As an operator or agent, I want to list recent WeChat drafts for an account, so that I can confirm what was created and avoid duplicate publication work.

**Acceptance Scenarios**

1. **US1-1 list summaries**
   - Given account `xiaban` supports `draft_batchget`
   - When calling `wechat_list_drafts(account, offset=0, count=20, include_content=false)`
   - Then MCP returns `total_count`, `item_count`, and items with `media_id`, `update_time`, `title`, `author`, `digest`, and `thumb_media_id`.

2. **US1-2 no full content by default**
   - Given draft contains HTML content
   - When `include_content=false`
   - Then response omits full `content` and returns bounded `content_preview` only if available.

3. **US1-3 include content explicitly**
   - Given caller sets `include_content=true`
   - Then MCP may return full article content, subject to response-size guard.

### User Story 2 - Capability And Errors (P1)

As an agent, I want clear errors and capability discovery, so that I do not call unsupported operations blindly.

**Acceptance Scenarios**

1. **US2-1 unsupported capability**
   - If adapter/account lacks `draft_batchget`, tool returns `adapter_capability_missing` with next action.

2. **US2-2 adapter errors**
   - Token/API/timeout failures map to existing remediation envelope without leaking tokens.

### User Story 3 - Future Update/Delete Safety (P2)

As the owner, I want update/delete to be designed with explicit protection before implementation, so that destructive draft operations cannot be triggered accidentally.

**Acceptance Scenarios**

1. **US3-1 destructive annotations**
   - Future delete/update tools must set destructive annotations and require confirmation input.

2. **US3-2 delete confirmation**
   - Delete must require account, media_id, and a confirmation phrase or token derived from media_id.

3. **US3-3 update source of truth**
   - Update should consume a publish-ready artifact or article-document version, not ad hoc HTML.

## Requirements

### Functional Requirements

- **FR-001**: Add `wechat_list_drafts` MCP tool backed by adapter `draft_batchget`.
- **FR-002**: Add schema for list draft input/output with bounded count/offset and `include_content` option.
- **FR-003**: Add adapter client method for batchget if not already present in NAS-side client.
- **FR-004**: Map adapter batchget errors into existing remediation envelope.
- **FR-005**: Preserve existing `wechat_get_draft_status` local job status semantics.
- **FR-006**: Do not add update/delete tools until destructive confirmation design is complete.
- **FR-007**: Document future update/delete boundaries in this feature.

### Non-Functional Requirements

- **NFR-001**: `wechat_list_drafts` must be read-only.
- **NFR-002**: Unit tests use fake adapter responses.
- **NFR-003**: Response content must be bounded by default.
- **NFR-004**: Existing create-draft and facade tests must continue to pass.

## Existing Design Facts

- `packages/wechat-draft-adapter` already exposes `POST /accounts/:account/drafts/batchget`.
- Adapter capability defaults include `draft_batchget`.
- `packages/wechat-draft/src/wechat/WechatAdapterClient.ts` currently wraps create draft and upload asset, but not batchget.
- `wechat-draft` MCP currently has local `wechat_get_draft_status`, not remote draft list.

## Out Of Scope

- `wechat_update_draft`
- `wechat_delete_draft`
- `wechat_schedule_publish`
- `wechat_mass_send`
- unverified `preview_url`

## Success Criteria

- Agent can list remote WeChat drafts without leaving MCP.
- Full content is not returned unless explicitly requested.
- Unsupported adapter capability produces actionable error.
- Roadmap has a clear next gate for update/delete rather than accidental implementation.
