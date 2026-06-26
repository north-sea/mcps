import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import type { WechatDraftService } from '../service/index.js';
import type { AppLogger } from '../logging/index.js';
import { SERVICE_VERSION } from '../version.js';
import {
  CreateDraftInputSchema,
  GetDraftStatusInputSchema,
  ListAccountsInputSchema,
  UploadAssetInputSchema,
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

  return server;
}

function toolLogContext(toolName: string, options: CreateMcpServerOptions) {
  return {
    toolName,
    logger: options.logger,
    requestId: options.requestId,
  };
}
