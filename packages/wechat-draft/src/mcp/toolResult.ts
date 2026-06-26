import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import type { Result } from '../schemas/index.js';

export function toMcpToolResult<T>(
  result: Result<T>,
  options: { isError?: boolean } = {}
): CallToolResult {
  return {
    content: [
      {
        type: 'text',
        text: JSON.stringify(result, null, 2),
      },
    ],
    isError: options.isError ?? !result.success,
  };
}
