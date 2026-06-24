# Context Manifest: WeChat Canonical Article Artifact

**Workspace**: `wechat-canonical-article-artifact`  
**Created**: 2026-06-24  
**Status**: active

> 本文件记录实现和验证阶段必须读取的高信号上下文。它不是待修改源文件清单，也不替代实现阶段按需阅读代码。

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-canonical-article-artifact/spec.md` | 理解需求边界：Markdown 非 canonical、成熟工具库优先、微信草稿直适配优先 | implement | yes |
| `specs/wechat-canonical-article-artifact/plan.md` | 遵守 ADR、Producer-Consumer Matrix、模块边界和验证策略 | implement | yes |
| `specs/wechat-canonical-article-artifact/data-model.md` | 实现 `article_document` / `wechat_api_article` artifact shape 和 metadata | implement | yes |
| `specs/wechat-canonical-article-artifact/tasks.md` | 按任务依赖和验证点执行 | implement | yes |
| `packages/wechat-draft/docs/wechat-ready-artifact-example.md` | 现有 publish-ready artifact contract，draft MCP 只消费 `wechat_api_article` | implement | yes |
| `packages/wechat-draft/src/hermes/ArtifactValidator.ts` | 现有 ready artifact 校验边界，新增逻辑不得破坏 | implement | yes |
| `packages/wechat-draft/src/wechat/DraftPayloadBuilder.ts` | 草稿 payload 构造边界，确保不接收 `article_document` | implement | yes |
| `packages/wechat-draft/src/render/WechatStyleProfile.ts` | 复用月亮/微雨样式 profile，WeChat renderer 输出需使用这些 style | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-canonical-article-artifact/spec.md` | 验证 US1/US2/US3 与 FR 覆盖 | verify | yes |
| `specs/wechat-canonical-article-artifact/plan.md` | 检查架构漂移，尤其是是否绕过 WeChat renderer 或让 draft MCP 解析 Markdown | verify | yes |
| `specs/wechat-canonical-article-artifact/data-model.md` | 检查 artifact shape、metadata 和 parent/source refs 是否满足设计 | verify | yes |
| `specs/wechat-canonical-article-artifact/tasks.md` | 检查任务完成状态、依赖顺序和验证点 | verify | yes |
| `specs/wechat-draft-mcp/acceptance.md` | 回归确认 draft MCP 原有边界仍成立 | verify | yes |
| `specs/wechat-asset-upload/verify-evidence.md` | 回归确认图片上传/manifest 设计仍兼容 | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `https://github.com/ueberdosis/tiptap-docs/blob/main/src/content/editor/api/utilities/static-renderer.mdx` | Tiptap static renderer 支持 JSON -> HTML，可用于 preview/export 或对照测试 | plan / implement | yes |
| `https://github.com/ueberdosis/tiptap-docs/blob/main/src/content/guides/output-json-html.mdx` | Tiptap server-side HTML utility 说明无 editor instance 生成 HTML | plan / implement | yes |
| `https://prosemirror.net/docs/ref` | ProseMirror JSON serialization 和 DOM serialization 参考 | plan / implement | yes |
| `https://github.com/study8677/awesome-architecture/blob/main/tutorial/04-%E5%8D%81%E5%A4%A7%E6%A0%B8%E5%BF%83%E6%9E%B6%E6%9E%84%E6%A8%A1%E5%BC%8F.md` | Pipeline / Pipes-and-Filters 架构参考 | plan | yes |

---

## Rules

- 实现前必须先读 `tasks.md` 当前任务，不要把全部任务一次性混在一起改。
- `wechat_create_draft` 不得新增 Markdown 或 `article_document` 直收路径。
- Live smoke 只创建草稿，不自动发布。
- 若 implementation 证明 Tiptap 依赖应放在上游 `content-orchestrator-agent` 而不是 `wechat-draft`，必须回写 plan/tasks 后再继续。
