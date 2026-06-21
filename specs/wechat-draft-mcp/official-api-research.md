# Official API Research: WeChat Draft MCP

**Workspace**: `wechat-draft-mcp`  
**Date**: 2026-06-21  
**Decision**: Official WeChat API is the only MVP draft-writing path.

## Findings

| Area | Official evidence | Implication |
|---|---|---|
| AccessToken | `GET https://api.weixin.qq.com/cgi-bin/token?appid=AppID&secret=AppSecret&grant_type=client_credential`; token response includes `access_token` and `expires_in`; token is currently 7200 seconds; errors include invalid credential, invalid appid, invalid secret, IP whitelist mismatch, frozen AppSecret. | Add `TokenManager` inside the Ali ECS adapter; redact token/secret; handle ECS IP whitelist and frozen secret as operator actions. |
| Draft add | `POST https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN`; response includes `media_id`; supported for 公众号 and 服务号. | `wechat_create_draft` should call `draft/add` and use `media_id` as draft locator. |
| Draft batchget | `POST https://api.weixin.qq.com/cgi-bin/draft/batchget?access_token=ACCESS_TOKEN`; request uses `offset`, `count`, `no_content`; response items include `media_id`, `content`, `update_time`, and draft `url` in news item. | Optional read-only locator/status enhancement. Not required for first create-draft success path. |
| Body image upload | `POST https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=ACCESS_TOKEN`; form field `media`; returns image `url`; **supports jpg/png, < 1MB**; uploaded images do not count against permanent material image limit. | Explains why `wechat_create_draft` must require WeChat-hosted body image URLs. Uploading images is outside MVP draft creation. |
| Permanent material | `POST https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=ACCESS_TOKEN&type=TYPE`; form field `media`; returns `media_id`; image material also returns `url`; **permanent material supports image/thumb types, < 2MB, jpg/png/gif**. | Explains why `wechat_create_draft` must require an existing permanent `thumb_media_id`. Uploading materials is outside MVP draft creation. |

## Draft Add Payload Constraints

MVP focuses on `article_type=news`.

Required / important fields:

- `articles[]`
- `article_type`: optional, defaults to `news`
- `title`: required, max 32 Chinese characters per docs
- `author`: optional, max 16 Chinese characters per docs
- `digest`: optional, max 128 Chinese characters per docs
- `content`: required, supports HTML tags, strips JS, must be less than 20,000 chars and less than 1MB; image URLs must come from WeChat upload-image API
- `content_source_url`: optional read-original URL
- `thumb_media_id`: required for `news`; must be permanent MediaID
- `need_open_comment`: optional, default 0
- `only_fans_can_comment`: optional, default 0

## Design Impact

- `wechat-draft-mcp` should not build alternate write adapters.
- `wechat_check_session` becomes `wechat_check_api_credentials`.
- `PublishReadyArtifact.type` should become `wechat_api_article`.
- Input artifact for `wechat_create_draft` must already contain WeChat-hosted body image URLs and permanent cover `thumb_media_id`; non-WeChat image URLs are invalid input.
- `wechat_asset_manifest` should record the WeChat-ready refs consumed by the draft workflow.
- Returned draft locator should be `media_id`.
- Risk model centers on credential/token/IP whitelist/API errors.

## Verification Notes

- `media/uploadimg` and `material/add_material` are not required for MVP `wechat_create_draft`.
- Live smoke must prove a WeChat-ready artifact results in a `draft/add` payload containing only WeChat image URLs / `thumb_media_id`.

## GitHub SDK Scan

**Date**: 2026-06-21

| Candidate | Ecosystem | Evidence | Evaluation |
|---|---|---|---|
| `binarywang/WxJava` | Java | Mature Apache-2.0 SDK; draft service wraps `addDraft`, `getDraft`, `updateDraft`, `delDraft`, `listDraft`, and `countDraft`. | Good behavior reference for endpoint coverage and response shape; not reusable as a TypeScript dependency. |
| `JeffreySu/WeiXinMPSDK` | .NET | Mature Apache-2.0 SDK with broad official-account coverage. | Useful as ecosystem evidence that draft APIs are stable; not relevant for Node runtime. |
| `silenceper/wechat` | Go | Mature Apache-2.0 Go SDK; docs expose official-account draft operations including `AddDraft`. | Good cross-check for API naming; not reusable in TypeScript MCP. |
| `ArtisanCloud/PowerWeChat` | Go | Maintained MIT SDK; `officialAccount/publish/client.go` wraps draft APIs and also publish/delete APIs. | Good reference for separating draft and publish surfaces; do not mirror its broader publish methods in MVP. |
| `fastwego/offiaccount` | Go | Apache-2.0 thin wrapper for `/cgi-bin/draft/add`, `/get`, `/delete`, `/update`, `/count`, `/batchget`. | Confirms a thin HTTP client is sufficient; not a dependency candidate. |
| `bao-io/wx-oa-sdk` | TypeScript | MIT package `wx-oa-sdk@0.2.2`; `src/draft.ts` and types cover draft add/get/delete/update/count/batchget. Small project, low adoption. | Best TypeScript reference for payload types, but not mature enough to add as a runtime dependency. |
| `BobGod/wechat-publisher-mcp` | JavaScript MCP | Implements AccessToken cache, material upload, draft creation, then `freepublish/submit`; logs verbose publish flow. | Not suitable for this feature because MVP must draft-only and must not publish. Useful only as negative evidence for safety boundaries. |

**Decision**: do not introduce a third-party WeChat SDK dependency for MVP. Implement a small ECS-adapter-local `WeChatApiClient` with typed request/response schemas, token refresh, error mapping, and an explicit MVP allowlist containing only `token`, `draft/add`, and optional `draft/batchget`. `media/uploadimg` and `material/add_material` are payload-constraint references, not part of `wechat_create_draft`. The NAS-side MCP calls the adapter rather than calling WeChat directly. Use mature SDKs only as reference implementations and regression-check sources.

## Sources

- AccessToken: https://developers.weixin.qq.com/doc/subscription/api/base/api_getaccesstoken.html
- Draft guide: https://developers.weixin.qq.com/doc/service/guide/product/draft.html
- Add draft: https://developers.weixin.qq.com/doc/service/api/draftbox/draftmanage/api_draft_add.html
- Batch get draft: https://developers.weixin.qq.com/doc/service/api/draftbox/draftmanage/api_draft_batchget.html
- Upload article image: https://developers.weixin.qq.com/doc/service/api/material/permanent/api_uploadimage.html
- Add permanent material: https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial.html
- WxJava draft service: https://github.com/binarywang/WxJava/blob/develop/weixin-java-mp/src/main/java/me/chanjar/weixin/mp/api/WxMpDraftService.java
- WxJava draft implementation: https://github.com/binarywang/WxJava/blob/develop/weixin-java-mp/src/main/java/me/chanjar/weixin/mp/api/impl/WxMpDraftServiceImpl.java
- PowerWeChat official account publish client: https://github.com/ArtisanCloud/PowerWeChat/blob/release/3.4.0/src/officialAccount/publish/client.go
- FastWeGo draft wrapper: https://github.com/fastwego/offiaccount/blob/master/apis/draft/draft.go
- TypeScript `wx-oa-sdk` draft API: https://github.com/bao-io/wx-oa-sdk/blob/main/src/draft.ts
- TypeScript `wx-oa-sdk` draft types: https://github.com/bao-io/wx-oa-sdk/blob/main/src/types/draft.ts
- WeChat publisher MCP implementation: https://github.com/BobGod/wechat-publisher-mcp/blob/main/src/services/WeChatAPI.js
