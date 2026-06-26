import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { createMcpServer } from './mcp/index.js';
import { WechatDraftService } from './service/index.js';

export { createMcpServer };

export async function createServer(): Promise<McpServer> {
  const service = await WechatDraftService.create();
  return createMcpServer(service);
}
