# Context Manifest: WeChat Article Document Tools

**Workspace**: `wechat-article-document-tools`
**Created**: 2026-06-27
**Status**: active

---

## Implement Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-article-document-tools/spec.md` | Defines tool boundaries, user stories, out-of-scope items, and side-effect restrictions. | implement | yes |
| `specs/wechat-article-document-tools/plan.md` | Defines ADRs, module boundaries, Producer-Consumer Matrix, and verification strategy. | implement | yes |
| `specs/wechat-article-document-tools/tasks.md` | Defines vertical slices, dependencies, and task-level verification. | implement | yes |
| `specs/wechat-draft-agent-experience-roadmap/roadmap.md` | Keeps this feature inside the larger WeChat draft agent experience roadmap and non-duplication rules. | implement | yes |
| `specs/wechat-draft-agent-contract-hardening/acceptance.md` | Establishes existing remediation envelope and constraints contract that new tools must reuse. | implement | yes |
| `docs/article-document-artifact-example.md` | Current article_document persistence and happy-path docs that must become tool-first. | implement | yes |

---

## Check Context

| File / Source | Reason | Phase | Required |
|---|---|---|---|
| `specs/wechat-article-document-tools/spec.md` | Verify FR-001..FR-007, out-of-scope boundaries, and trait-driven acceptance. | verify | yes |
| `specs/wechat-article-document-tools/plan.md` | Check architecture drift, ADR compliance, and no hidden side effects. | verify | yes |
| `specs/wechat-article-document-tools/tasks.md` | Confirm every task is completed with evidence. | verify | yes |
| `specs/wechat-article-document-tools/verify-evidence.md` | Expected evidence ledger for before/after, tests, diffusion, and remaining risks. | verify | yes |
| `specs/wechat-draft-agent-experience-roadmap/roadmap.md` | Confirm roadmap status and next feature recommendation after closeout. | verify | yes |

---

## Research Context

| File / Source | Reason | Phase | Verified |
|---|---|---|---|
| `packages/wechat-draft/src/render/MarkdownArticleImporter.ts` | Existing markdown -> article_document importer to wrap; do not duplicate. | plan / implement / verify | yes |
| `packages/wechat-draft/src/render/ArticleDocumentValidator.ts` | Existing validation logic to expose through tool. | plan / implement / verify | yes |
| `packages/wechat-draft/src/render/WechatArticleDocumentRenderer.ts` | Existing HTML renderer to expose through preview/render tool. | plan / implement / verify | yes |
| `packages/wechat-draft/src/render/MarkdownArticleExporter.ts` | Existing non-canonical preview/export helper. | plan / implement / verify | yes |
| `packages/wechat-draft/src/render/ArticleDocumentToWechatArtifactBuilder.ts` | Existing publish-ready artifact builder to wrap. | plan / implement / verify | yes |
| `packages/wechat-draft/src/mcp/createMcpServer.ts` | Current tool registration pattern and logging/result helper usage. | plan / implement / verify | yes |
| `packages/wechat-draft/src/schemas/result-types.ts` | Existing Result and remediation envelope. | plan / implement / verify | yes |
| `packages/wechat-draft/src/schemas/tool-schemas.ts` | Current MCP tool schemas and output conventions. | plan / implement / verify | yes |
| `packages/wechat-draft/src/service/WechatDraftService.ts` | Service façade where new article-document methods should live. | plan / implement / verify | yes |

---

## Rules

- Do not add a second markdown/Tiptap/HTML implementation in MCP service code.
- Do not call WeChat API, hermes-db, image upload, compression, or draft creation from these tools.
- Treat `article_document` as canonical; Markdown and HTML preview are derived formats.
- If a tool accepts JSON string for compatibility, normalize immediately and report object/string errors through the remediation envelope.
