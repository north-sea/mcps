# Commit Plan: WeChat Canonical Article Artifact

**Feature**: `wechat-canonical-article-artifact`  
**Date**: 2026-06-24  
**Status**: ready for user review

## Include

Feature implementation:

- `packages/wechat-draft/package.json`
- `pnpm-lock.yaml`
- `packages/wechat-draft/src/render/ArticleDocumentTypes.ts`
- `packages/wechat-draft/src/render/TiptapExtensionAllowlist.ts`
- `packages/wechat-draft/src/render/ArticleDocumentValidator.ts`
- `packages/wechat-draft/src/render/WechatArticleDocumentRenderer.ts`
- `packages/wechat-draft/src/render/ArticleDocumentToWechatArtifactBuilder.ts`
- `packages/wechat-draft/src/render/MarkdownArticleImporter.ts`
- `packages/wechat-draft/src/render/MarkdownArticleExporter.ts`
- `packages/wechat-draft/src/render/index.ts`
- `packages/wechat-draft/test-article-document-renderer.mjs`
- `packages/wechat-draft/scripts/live-canonical-smoke.mjs`

Adapter batchget support:

- `packages/wechat-draft-adapter/src/types/wechat.ts`
- `packages/wechat-draft-adapter/src/wechat/WeChatApiClient.ts`
- `packages/wechat-draft-adapter/src/server.ts`

Docs and SDD artifacts:

- `docs/article-document-artifact-example.md`
- `packages/wechat-draft/docs/wechat-ready-artifact-example.md`
- `packages/wechat-draft/docs/canonical-article-artifact.md`
- `specs/.active`
- `specs/wechat-canonical-article-artifact/spec.md`
- `specs/wechat-canonical-article-artifact/plan.md`
- `specs/wechat-canonical-article-artifact/data-model.md`
- `specs/wechat-canonical-article-artifact/context-manifest.md`
- `specs/wechat-canonical-article-artifact/tasks.md`
- `specs/wechat-canonical-article-artifact/acceptance.md`
- `specs/wechat-canonical-article-artifact/commit-plan.md`

## Exclude / Needs User Decision

These files were dirty before or are not clearly owned by this feature:

- `packages/wechat-draft-adapter/DEPLOYMENT.md`
- `packages/wechat-draft-adapter/Dockerfile.simple`
- `packages/wechat-draft-adapter/package.json`
- `packages/wechat-draft/src/config/loader.ts`
- `packages/wechat-draft/src/hermes/HermesDbClient.ts`
- `packages/wechat-draft/src/store/JobStore.ts`
- `packages/wechat-draft/src/wechat/DraftPayloadBuilder.ts`
- `packages/wechat-draft/test-adapter-client-upload.mjs`
- `packages/wechat-draft/test-markdown-wechat-renderer.mjs`
- `specs/wechat-asset-upload/acceptance.md`
- `.pnpm-store/`
- `packages/wechat-draft-adapter/quick-deploy.sh`

## Suggested Commit Message

```text
Add canonical WeChat article artifact renderer
```

## Verification Before Commit

```bash
rtk pnpm --filter @mcps/wechat-draft build
rtk pnpm --filter @mcps/wechat-draft-adapter build
rtk node packages/wechat-draft/test-article-document-renderer.mjs
rtk node packages/wechat-draft/test-markdown-wechat-renderer.mjs
```
