# Verify Evidence: WeChat Article Document Tools

**Workspace**: `wechat-article-document-tools`
**Created**: 2026-06-27
**Status**: pass

---

## Baseline / Failed Behavior

| Case | Before Behavior | Evidence Source | After Guard |
|---|---|---|---|
| No MCP article document tools | `createMcpServer.ts` only registers accounts, upload asset, validate publish artifact, create draft, get draft status. | `rg` over `packages/wechat-draft/src/mcp/createMcpServer.ts` before this feature. | Add import/validate/render/build article document tools. |
| Library-level conversion not discoverable | Importer, validator, renderer, exporter, and builder exist under `src/render`, but no MCP registration. | `packages/wechat-draft/src/render/*` | Wrap existing modules through service methods and MCP tools. |
| No render module tests | `find packages/wechat-draft/src/render -name '*.test.ts'` returned no files. | pre-implementation check | Add service/render/tool contract tests. |
| Agent hand-roll risk | Docs explain canonical artifact shape and string persistence, but do not provide tool calls for constructing/rendering it. | `docs/article-document-artifact-example.md` | Update docs to tool-first flow. |

---

## Failed Attempt Ledger

| Time | Attempt | Result | Decision |
|---|---|---|---|
| 2026-06-27 | Considered one mega E2E draft tool for article document -> draft. | Rejected. It overlaps `wechat-draft-publish-ready-facade` and asset preflight roadmap features. | Use four side-effect-free tools. |
| 2026-06-27 | Considered implementing a new Markdown/Tiptap converter in MCP layer. | Rejected. Existing render modules already provide importer/validator/renderer/builder. | Thin service façade only. |

---

## Verification Runs

| Time | Command | Result | Notes |
|---|---|---|---|
| 2026-06-27 | `pnpm --filter @mcps/wechat-draft build` | PASS | TypeScript build passed after article-document schemas, service methods, MCP registration, docs, and tests. |
| 2026-06-27 | `pnpm --filter @mcps/wechat-draft test` | PASS | 51 tests passed, including 7 article-document service tests and HTTP MCP tool discovery coverage. |
| 2026-06-27 | `git diff --check` | PASS | No whitespace errors. |

---

## Diffusion Check

Command:

```bash
rg -n "wechat_import_article_markdown|wechat_validate_article_document|wechat_render_article_document|wechat_build_publish_ready_artifact|next_action|remediation_hint" packages/wechat-draft/src/service packages/wechat-draft/src/mcp packages/wechat-draft/src/schemas docs/article-document-artifact-example.md specs/wechat-article-document-tools
```

Findings:

- New MCP tools are registered in `createMcpServer.ts` and covered by HTTP MCP `listTools` smoke assertions.
- Article-document service errors route through `articleDocumentError` or `normalizeArticleDocumentInput`, returning `next_action`, `remediation_hint`, `retryable=false`, and `current_phase`.
- Tests assert recovery actions for missing Markdown image assets, invalid JSON, missing body `wechat_url`, and missing cover `thumb_media_id`.
- Docs now show a tool-first import -> validate -> render -> build -> hermes upsert -> create draft flow.

---

## Remaining Risk

- Existing markdown importer is intentionally small and may not support full Markdown. This feature should expose its deterministic subset rather than expanding parsing scope without tests.
- Tools are side-effect-free; agents must still call hermes upsert and `wechat_create_draft` explicitly until the later publish-ready facade feature.
