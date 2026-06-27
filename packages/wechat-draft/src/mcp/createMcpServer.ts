import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { WechatDraftService } from '../service/index.js';
import type { AppLogger } from '../logging/index.js';
import { SERVICE_VERSION } from '../version.js';
import {
  BuildPublishReadyArtifactInputSchema,
  CreateDraftFacadeInputSchema,
  CreateDraftInputSchema,
  GetDraftStatusInputSchema,
  ImportArticleMarkdownInputSchema,
  ListDraftsInputSchema,
  ListAccountsInputSchema,
  AssetPreflightInputSchema,
  RenderArticleDocumentInputSchema,
  UploadAssetInputSchema,
  ValidateArticleDocumentInputSchema,
  ValidateArtifactInputSchema,
} from '../schemas/index.js';
import { toMcpToolResult } from './toolResult.js';
import { runLoggedTool } from './toolLogging.js';

export interface CreateMcpServerOptions {
  logger?: AppLogger;
  requestId?: string;
}

export function createMcpServer(
  service: WechatDraftService,
  options: CreateMcpServerOptions = {}
): McpServer {
  const server = new McpServer({
    name: 'WeChat Draft MCP Server',
    version: SERVICE_VERSION,
  });

  server.registerTool(
    'wechat_list_accounts',
    {
      description: 'List available WeChat accounts. Returns enabled accounts by default.',
      inputSchema: ListAccountsInputSchema,
    },
    async (input) =>
      runLoggedTool(toolLogContext('wechat_list_accounts', options), () =>
        toMcpToolResult(service.listAccounts(input))
      )
  );

  server.registerTool(
    'wechat_validate_publish_artifact',
    {
      description:
        'Validate that a hermes-db artifact is WeChat-ready before creating draft.',
      inputSchema: ValidateArtifactInputSchema,
    },
    async (input) =>
      runLoggedTool(toolLogContext('wechat_validate_publish_artifact', options), async () =>
        toMcpToolResult(await service.validatePublishArtifact(input))
      )
  );

  server.registerTool(
    'wechat_import_article_markdown',
    {
      description:
        'Side-effect-free: convert Markdown plus prepared image metadata into canonical article_document. Does not upload assets or create drafts.',
      inputSchema: ImportArticleMarkdownInputSchema,
    },
    async (input) =>
      runLoggedTool(toolLogContext('wechat_import_article_markdown', options), () =>
        toMcpToolResult(service.importArticleMarkdown(input))
      )
  );

  server.registerTool(
    'wechat_validate_article_document',
    {
      description:
        'Side-effect-free: validate article_document object or JSON string before rendering/building.',
      inputSchema: ValidateArticleDocumentInputSchema,
    },
    async (input) =>
      runLoggedTool(toolLogContext('wechat_validate_article_document', options), () =>
        toMcpToolResult(service.validateArticleDocument(input))
      )
  );

  server.registerTool(
    'wechat_render_article_document',
    {
      description:
        'Side-effect-free: render article_document to HTML or Markdown preview. Does not write hermes-db or create drafts.',
      inputSchema: RenderArticleDocumentInputSchema,
    },
    async (input) =>
      runLoggedTool(toolLogContext('wechat_render_article_document', options), () =>
        toMcpToolResult(service.renderArticleDocument(input))
      )
  );

  server.registerTool(
    'wechat_build_publish_ready_artifact',
    {
      description:
        'Side-effect-free: build a hermes upsert payload for a publish_ready wechat_api_article artifact. Does not upsert or create drafts.',
      inputSchema: BuildPublishReadyArtifactInputSchema,
    },
    async (input) =>
      runLoggedTool(toolLogContext('wechat_build_publish_ready_artifact', options), () =>
        toMcpToolResult(service.buildPublishReadyArtifact(input))
      )
  );

  server.registerTool(
    'wechat_create_draft',
    {
      description:
        "Create a WeChat draft from a hermes-db publish-ready artifact. This creates a draft in the account's draft box.",
      inputSchema: CreateDraftInputSchema,
    },
    async (input) => runLoggedTool(toolLogContext('wechat_create_draft', options), async () => {
      const result = await service.createDraft(input);
      const isError = !result.success || result.data.status !== 'saved';
      return toMcpToolResult(result, { isError });
    })
  );

  server.registerTool(
    'wechat_create_draft_facade',
    {
      description:
        'Create a WeChat draft through an agent-facing facade. Can validate an existing publish_ready artifact or build/upsert one from article_document before draft creation. This may write Hermes workflow records and create a WeChat draft.',
      inputSchema: CreateDraftFacadeInputSchema,
    },
    async (input) => runLoggedTool(toolLogContext('wechat_create_draft_facade', options), async () => {
      const result = await service.createDraftFacade(input);
      const isError = !result.success || result.data.draft?.status !== 'saved';
      return toMcpToolResult(result, { isError });
    })
  );

  server.registerTool(
    'wechat_list_drafts',
    {
      description:
        'Read-only: list remote WeChat drafts via adapter draft_batchget. Omits full content by default; set include_content=true explicitly to inspect article HTML.',
      inputSchema: ListDraftsInputSchema,
    },
    async (input) =>
      runLoggedTool(toolLogContext('wechat_list_drafts', options), async () =>
        toMcpToolResult(await service.listDrafts(input))
      )
  );

  server.registerTool(
    'wechat_get_draft_status',
    {
      description:
        'Get draft job status by job_id or artifact_id. Returns job metadata and media_id if available.',
      inputSchema: GetDraftStatusInputSchema,
    },
    async (input) =>
      runLoggedTool(toolLogContext('wechat_get_draft_status', options), async () =>
        toMcpToolResult(await service.getDraftStatus(input))
      )
  );

  server.registerTool(
    'wechat_upload_asset',
    {
      description:
        "Upload image asset to WeChat material API. body_image returns wechat_url; cover_image returns thumb_media_id.",
      inputSchema: UploadAssetInputSchema,
    },
    async (input) =>
      runLoggedTool(toolLogContext('wechat_upload_asset', options), async () =>
        toMcpToolResult(await service.uploadAsset(input))
      )
  );

  server.registerTool(
    'wechat_preflight_asset',
    {
      description:
        'Side-effect-free: probe a local_path or remote_url image against WeChat asset constraints before upload. Does not upload or compress.',
      inputSchema: AssetPreflightInputSchema,
    },
    async (input) =>
      runLoggedTool(toolLogContext('wechat_preflight_asset', options), async () =>
        toMcpToolResult(await service.preflightAsset(input))
      )
  );

  return server;
}

function toolLogContext(toolName: string, options: CreateMcpServerOptions) {
  return {
    toolName,
    logger: options.logger,
    requestId: options.requestId,
  };
}
