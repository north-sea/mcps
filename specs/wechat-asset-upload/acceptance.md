# Acceptance Record: WeChat Asset Upload Tool

**Workspace**: `wechat-asset-upload`  
**Feature**: 微信素材上传工具  
**Completed**: 2026-06-22  
**Closeout Status**: Implementation Complete, Live Smoke Pending

---

## Feature Traits Review

| Trait | 命中 | 验收要求 | 完成状态 |
|---|---|---|---|
| `multi-stage-workflow` | ✅ | Producer-Consumer Matrix 验证 | ✅ Verified |
| `external-side-effects` | ✅ | 副作用边界清晰，可回滚或补偿 | ✅ Documented |
| `artifact-handoff` | ✅ | 输出格式符合下游消费契约 | ✅ Verified |
| `user-visible-output` | ✅ | 最终用户可见输出验证 | ⚠️ Pending Live Smoke |
| `prior-closure-failure` | ✅ | 端到端能力补齐 | ✅ Verified |

---

## Three-Dimensional Verdict

### 1. Component Verdict: ✅ PASS

**范围**: 单元级别功能正确性

**验证证据**:
- ✅ `AssetSourceLoader`: 15/15 单元测试通过
  - 本地文件读取（成功/失败/不可读）
  - 远程 URL 下载（成功/404/非 HTTP(S)/超限）
  - body_image 和 cover_image 大小/格式限制
  - MIME 推断和校验
- ✅ `WechatAdapterClient`: 3/3 单元测试通过
  - multipart 请求构建
  - 404 映射为 endpoint_not_found
  - uploadAsset 方法存在性
- ✅ TypeScript 编译通过（wechat-draft + wechat-draft-adapter）
- ✅ Schema 验证通过（zod schema 类型推断正确）

**Verdict**: Component 层面功能完整，单元测试覆盖核心路径和边界条件。

---

### 2. Workflow Verdict: ✅ PASS (with noted limitations)

**范围**: 端到端流程集成

**验证证据**:
- ✅ MCP tool 注册：`wechat_upload_asset` 已注册，schema 正确暴露
- ✅ Account + Adapter 校验：复用现有校验逻辑，capability 检查正确
- ✅ AssetSourceLoader → WechatAdapterClient 集成：错误正确传播
- ✅ Adapter → WeChatApiClient 集成：usage 路由正确，两个微信 API 都已实现
- ✅ 错误映射：AssetSourceError、AdapterError、WeChatApiError 正确映射到 MCP 错误码
- ✅ 敏感信息保护：错误响应不包含 token、secret、图片内容
- ✅ 契约稳定性：`wechat_create_draft` 未引入隐式上传逻辑
- ✅ Producer-Consumer Matrix：
  - `wechat_upload_asset usage=body_image` 产出 `wechat_url`，可用于正文 `<img src="...">`
  - `wechat_upload_asset usage=cover_image` 产出 `thumb_media_id`，可用于草稿 `thumb_media_id` 字段
  - `wechat_create_draft` 消费 `wechat_asset_manifest`，检查正文 URL 和封面 media_id

**已知限制**:
- ⚠️ **未执行 live smoke test**：没有真实微信账号、ECS adapter 和 IP 白名单环境，未能端到端测试真实微信 API 调用
- ⚠️ **Adapter 部署未验证**：ECS adapter 新增 `/assets` endpoint 尚未部署到生产环境

**Verdict**: Workflow 层面逻辑正确，本地集成验证通过；真实微信 API 调用待 live smoke 确认。

---

### 3. User-visible Outcome Verdict: ⚠️ PENDING

**范围**: 最终用户可见的外部副作用

**验证证据**:
- ⚠️ **Live smoke test pending**: 以下验证待执行
  - [ ] 上传小于 1MB 的 jpg/png，确认返回 `https://mmbiz.qpic.cn/...` URL
  - [ ] 上传小于 64KB 的 JPG，确认返回 `thumb_media_id`
  - [ ] 使用返回的 `wechat_url` 创建草稿，确认图片在草稿预览中正确显示
  - [ ] 使用返回的 `thumb_media_id` 创建草稿，确认封面在草稿预览中正确显示
  - [ ] 验证超限图片返回明确错误（body_image >1MB, cover_image >64KB）
  - [ ] 验证格式错误返回明确错误（cover_image 传入 PNG）

**Verdict**: User-visible outcome 待 live smoke 确认。本地实现完整，但真实微信素材库副作用未验证。

---

## Residual Risks

### High Priority

1. **Live Smoke Test 缺失**
   - **风险**: 真实微信 API 行为可能与文档不一致（格式要求、大小限制、返回字段）
   - **影响**: 首次生产使用可能遇到未预期错误
   - **缓解**: 
     - 已实现完整错误映射，微信 API 错误会正确传播
     - 已记录官方文档链接和约束
     - 建议首次使用时用测试账号验证

2. **Adapter 部署版本错位**
   - **风险**: NAS MCP 配置 `asset_upload` capability，但 ECS adapter 尚未部署新版本
   - **影响**: 调用 `wechat_upload_asset` 会返回 404 -> `adapter_capability_missing`
   - **缓解**: 
     - 404 正确映射为 capability missing 错误
     - 错误消息明确提示升级 adapter
     - 建议同步部署 MCP 和 adapter

### Medium Priority

3. **封面图片 64KB 限制严格**
   - **风险**: 大部分常规封面图会超过 64KB 限制
   - **影响**: 用户需要预先压缩封面图
   - **缓解**:
     - 文档明确说明 64KB 限制和 JPG only 要求
     - 错误消息清晰（`asset_size_exceeded`, `asset_format_unsupported`）
     - 未来可考虑自动压缩（超出 MVP 范围）

4. **远程 URL 下载无域名白名单**
   - **风险**: MCP 可能下载恶意或超大远程图片
   - **影响**: DoS、SSRF 风险（已部分缓解）
   - **缓解**:
     - 只允许 http/https 协议
     - 预检查 Content-Length
     - 最大 1MB 限制
     - 未来可考虑域名白名单（超出 MVP 范围）

### Low Priority

5. **Multipart 依赖引入**
   - **风险**: 增加了 `multer` 依赖（原 plan 希望零依赖）
   - **影响**: 供应链复杂度轻微增加
   - **缓解**:
     - `multer` 是成熟且广泛使用的 npm 包
     - 已在 plan.md 中记录引入原因（Express 不原生支持 multipart）

6. **上传结果不持久化**
   - **风险**: 上传成功后 MCP 崩溃，结果丢失
   - **影响**: 需要重新上传
   - **缓解**:
     - 微信素材上传是幂等的（重复上传同一图片返回新 URL/media_id）
     - 调用方负责把结果写入 artifact metadata
     - 未来可考虑 upload job store（超出 MVP 范围）

---

## Functional Requirements Coverage

| FR-ID | 要求 | 状态 | 证据 |
|-------|------|------|------|
| FR-001 | 在现有 MCP 中新增 tool | ✅ | `wechat_upload_asset` 已注册 |
| FR-002 | 支持 body_image 和 cover_image | ✅ | AssetUsageSchema enum |
| FR-003 | body_image 返回 wechat_url | ✅ | UploadAssetOutputSchema |
| FR-004 | cover_image 返回 thumb_media_id | ✅ | UploadAssetOutputSchema |
| FR-005 | 复用现有账号和 adapter | ✅ | ConfigLoader.getAccount/getAdapter |
| FR-006 | 通过 ECS adapter 调用微信 API | ✅ | WechatAdapterClient.uploadAsset |
| FR-007 | Adapter 复用 AccessToken 机制 | ✅ | TokenManager.getToken |
| FR-008 | 按 usage 路由到对应微信 API | ✅ | uploadBodyImage / uploadCoverImage |
| FR-009 | 返回结构化结果 | ✅ | UploadAssetOutput |
| FR-010 | Adapter capability 检查 | ✅ | `asset_upload` capability |
| FR-011 | 不自动扫描文章 | ✅ | Code review confirmed |
| FR-012 | 不泄露敏感信息 | ✅ | 错误响应过滤 token/secret |
| FR-013 | 支持本地路径和远程 URL | ✅ | AssetSourceLoader |
| FR-014 | MVP 不支持 base64 | ✅ | AssetSourceTypeSchema 不包含 base64 |

**Coverage**: 14/14 (100%)

---

## Non-Functional Requirements Coverage

| NFR-ID | 要求 | 状态 | 证据 |
|--------|------|------|------|
| NFR-001 | 安全边界保守 | ✅ | Token/secret 只在 ECS adapter |
| NFR-002 | 返回内容短小可操作 | ✅ | UploadAssetOutput 紧凑 |
| NFR-003 | 错误可区分 | ✅ | 5 个专用错误码 + WeChatApiError mapping |
| NFR-004 | 不改变 create_draft 契约 | ✅ | Code review confirmed |

**Coverage**: 4/4 (100%)

---

## Producer-Consumer Matrix Verification

| Producer | Artifact | Consumer | Verified |
|---|---|---|---|
| `wechat_upload_asset usage=body_image` | `wechat_url` | 正文 `<img src="...">` | ✅ Local |
| `wechat_upload_asset usage=cover_image` | `thumb_media_id` | 草稿 `thumb_media_id` 字段 | ✅ Local |
| ECS adapter `/assets` | `AdapterUploadAssetResponse` | MCP response formatter | ✅ Local |

**Note**: "✅ Local" 表示本地代码和单元测试验证通过；真实微信 API 端到端验证待 live smoke。

---

## Documentation

| 文档 | 状态 | 位置 |
|------|------|------|
| MCP Tool 文档 | ✅ | `packages/wechat-draft/README.md` |
| Adapter Endpoint 文档 | ✅ | `packages/wechat-draft-adapter/README.md` |
| 工作流程示例 | ✅ | `packages/wechat-draft/README.md` |
| 错误处理指南 | ✅ | 两个 README 都包含 |
| 素材约束说明 | ✅ | 两个 README 都包含 |
| 微信官方文档链接 | ✅ | 两个 README 都包含 |

---

## Completion Checklist

- [x] FR-001 ~ FR-014 全部实现
- [x] NFR-001 ~ NFR-004 全部满足
- [x] T001 ~ T011 全部完成
- [x] Component 单元测试通过（18/18）
- [x] TypeScript 编译通过
- [x] 错误映射完整
- [x] 敏感信息保护验证
- [x] 契约稳定性验证
- [x] 文档完整
- [ ] Live smoke test（待执行）
- [ ] ECS adapter 生产部署（待执行）

---

## Closeout Checklist

执行日期：2026-06-22

| # | Checklist Item | Status | Evidence / Reason |
|---|---------------|--------|-------------------|
| 1 | 旧逻辑、旧路径、fallback 退役检查 | ✅ 已完成 | 本次为新增能力，无旧逻辑需退役 |
| 2 | 发布、提交、CI、follow-through 事项 | ⏳ 待确认 | 需要部署 ECS adapter 新版本（operational concern） |
| 3 | SDD structure validation | ✅ 已完成 | 所有必需文件存在，tasks 12/12 完成 |
| 4 | 相关文档更新 | ✅ 已完成 | MCP 和 Adapter README 已完整重写 |
| 5 | 关键架构决策保留 | ✅ 已完成 | ADR-001~004 已记录在 plan.md |
| 6 | 架构债、临时兼容、演进触发信号 | ✅ 已完成 | 6 个 residual risks 已记录，无架构债 |
| 7 | Knowledge Capture Gate | ✅ 已完成 | 见下方 Knowledge Capture 表格 |
| 8 | Roadmap 状态同步 | ❌ 不适用 | 本 feature 不属于 roadmap |
| 9 | Workflow replay (multi-stage + user-visible) | ⚠️ 部分完成 | 本地验证完整，live smoke pending |
| 10 | Bugfix closure | ❌ 不适用 | 本 feature 不命中 bugfix-loop-breaker trait |
| 11 | Commit plan | ⏳ 待生成 | 存在相关 diff，需生成 commit plan |

**阻塞项**: 无  
**延后项**: 
- ECS adapter 生产部署（operational，不阻塞 feature completion）
- Live smoke test（已记录为 residual risk）

---

## Knowledge Capture

| Type | Title | Summary | Evidence | Scope | Sync Status | Follow-up |
|------|-------|---------|----------|-------|-------------|-----------|
| decision | 单 tool + usage 枚举统一端点 | 避免创建 upload_body_image 和 upload_cover_image 两个 tool，用 usage 参数路由。简化 agent 调用和文档。 | plan.md ADR-001 | 所有具有多种用途的资源上传场景 | recorded-only | 无 |
| decision | MCP 统一物化图片字节 | 本地路径和远程 URL 都由 MCP 的 AssetSourceLoader 处理，adapter 只接收 bytes。避免 adapter 承担 SSRF 风险。 | plan.md ADR-002 | 需要上传外部资源的 MCP tool | recorded-only | 无 |
| pattern | AssetSourceLoader 模式 | 统一 local_path 和 remote_url 两种来源，返回 bytes + metadata。可复用于其他需要多源输入的场景。 | packages/wechat-draft/src/wechat/AssetSourceLoader.ts | 任何需要从多个来源加载资源的场景 | recorded-only | 可考虑抽取为通用 utility |
| convention | 素材约束前置检查 | 在 MCP 层面就检查大小和格式限制（body_image 1MB/jpg/png, cover_image 64KB/JPG），避免无效请求到达微信 API。 | AssetSourceLoader.ts:validateAssetConstraints | 所有需要预检查的外部 API 调用 | recorded-only | 无 |
| anti-pattern | 避免 adapter 直接下载远程 URL | 远程 URL 下载放在 adapter 会导致 SSRF 风险和网络策略复杂化。应由 MCP 控制下载源。 | plan.md ADR-002, Security Boundary | 所有涉及远程资源的 adapter | recorded-only | 无 |
| gotcha | 微信封面素材严格限制 | 封面图片必须是永久 thumb 素材（type=thumb），JPG 格式且 64KB 以下。超出限制会导致草稿创建失败。 | 微信官方文档, README.md | 微信公众号封面上传 | recorded-only | 文档已明确说明，需要用户提前压缩 |
| follow-up | Live smoke test 待执行 | 真实微信 API 行为验证待执行，包括素材上传、URL 可用性、封面显示。 | acceptance.md Residual Risks | 本 feature | recorded-only | 建议首次使用时在测试账号验证 |
| follow-up | ECS adapter 生产部署 | 新版本 adapter 包含 /assets endpoint 和 asset_upload capability，需要同步部署。 | acceptance.md Residual Risks | 本 feature | recorded-only | 部署后验证 /health 返回 asset_upload |

---

1. **Adapter 部署**：
   - 先部署 ECS adapter 新版本到生产环境
   - 验证 `/health` 返回 `asset_upload` capability
   - 验证 systemd 服务正常重启

2. **Live Smoke Test**：
   - 准备测试图片：
     - body_image: 500KB jpg/png
     - cover_image: 50KB jpg
   - 使用测试账号调用 `wechat_upload_asset`
   - 验证返回的 URL/media_id 可用于草稿创建
   - 在微信公众平台后台确认素材已上传

3. **生产使用**：
   - 先用测试账号验证端到端流程
   - 确认错误处理符合预期
   - 记录任何与文档不一致的行为
   - 更新 acceptance.md 记录 live smoke 结果

---

## Final Verdict

**Implementation**: ✅ COMPLETE  
**Local Verification**: ✅ PASS  
**Production Readiness**: ⚠️ PENDING (Live Smoke + Adapter Deployment)

**Recommendation**: Feature 实现完整且质量合格，可以进入 live smoke 和生产部署阶段。建议按 "Recommendations for First Use" 章节执行后续验证。

---

## Completion Record

**Feature Status**: ✅ COMPLETED  
**Completion Date**: 2026-06-22

**Git Commits**:
- `70a91ba` - feat(wechat-draft): add asset upload foundation
- `1904b57` - feat(wechat-draft): integrate asset upload tool
- `29d8dd9` - docs(wechat-draft): add asset upload documentation

**Branch**: main  
**Total Changes**: 23 files changed, 3794 insertions(+), 95 deletions(-)

**Deliverables**:
- ✅ MCP Tool: `wechat_upload_asset`
- ✅ Adapter Endpoint: `POST /accounts/:account/assets`
- ✅ Unit Tests: 18/18 passed
- ✅ Documentation: Complete (MCP + Adapter README)
- ✅ SDD Artifacts: 7 files

**Not Pushed**: Commits are local only. Use `git push` to publish.
