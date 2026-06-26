import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import type { AppLogger } from '../logging/index.js';

export interface ToolLogContext {
  toolName: string;
  logger?: AppLogger;
  requestId?: string;
}

export interface ToolResultLogSummary {
  success?: boolean;
  error_code?: string;
  job_id?: string;
  job_status?: string;
}

export async function runLoggedTool(
  context: ToolLogContext,
  handler: () => CallToolResult | Promise<CallToolResult>
): Promise<CallToolResult> {
  const startedAt = performance.now();

  try {
    const result = await handler();
    context.logger?.info(
      {
        event: 'mcp_tool_call',
        request_id: context.requestId,
        tool_name: context.toolName,
        duration_ms: elapsedMs(startedAt),
        mcp_is_error: result.isError === true,
        ...summarizeMcpToolResult(result),
      },
      'MCP tool call completed'
    );
    return result;
  } catch (error) {
    context.logger?.error(
      {
        event: 'mcp_tool_call',
        request_id: context.requestId,
        tool_name: context.toolName,
        duration_ms: elapsedMs(startedAt),
        error: error instanceof Error ? { name: error.name, message: error.message } : String(error),
      },
      'MCP tool call failed'
    );
    throw error;
  }
}

export function summarizeMcpToolResult(result: CallToolResult): ToolResultLogSummary {
  const text = result.content.find(isTextContent)?.text;
  if (!text) {
    return {};
  }

  try {
    const parsed = JSON.parse(text) as {
      success?: boolean;
      data?: {
        job_id?: string;
        status?: string;
      };
      error?: {
        code?: string;
      };
    };

    return omitUndefined({
      success: parsed.success,
      error_code: parsed.error?.code,
      job_id: parsed.data?.job_id,
      job_status: parsed.data?.status,
    });
  } catch {
    return {};
  }
}

function isTextContent(
  content: CallToolResult['content'][number]
): content is Extract<CallToolResult['content'][number], { type: 'text' }> {
  return content.type === 'text';
}

function elapsedMs(startedAt: number): number {
  return Math.round((performance.now() - startedAt) * 100) / 100;
}

function omitUndefined<T extends Record<string, unknown>>(value: T): T {
  return Object.fromEntries(
    Object.entries(value).filter(([, item]) => item !== undefined)
  ) as T;
}
