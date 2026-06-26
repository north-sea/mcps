import test from 'node:test';
import assert from 'node:assert/strict';
import { ErrorCode, createErrorResult, createSuccessResult } from '../schemas/index.js';
import { createLogger } from '../logging/index.js';
import { toMcpToolResult } from './toolResult.js';
import { runLoggedTool, summarizeMcpToolResult } from './toolLogging.js';

test('summarizeMcpToolResult extracts success, job, and error metadata', () => {
  assert.deepEqual(
    summarizeMcpToolResult(
      toMcpToolResult(
        createSuccessResult({
          job_id: 'job_1',
          status: 'saved',
        })
      )
    ),
    {
      success: true,
      job_id: 'job_1',
      job_status: 'saved',
    }
  );

  assert.deepEqual(
    summarizeMcpToolResult(
      toMcpToolResult(createErrorResult(ErrorCode.ACCOUNT_NOT_FOUND, 'missing'))
    ),
    {
      success: false,
      error_code: ErrorCode.ACCOUNT_NOT_FOUND,
    }
  );
});

test('runLoggedTool writes tool correlation metadata without arguments', async () => {
  const lines: string[] = [];
  const logger = createLogger({
    stream: {
      write(line: string) {
        lines.push(line);
        return true;
      },
    },
  });

  await runLoggedTool(
    {
      toolName: 'wechat_create_draft',
      requestId: 'req_1',
      logger,
    },
    () =>
      toMcpToolResult(
        createSuccessResult({
          job_id: 'job_1',
          status: 'saved',
        })
      )
  );

  const record = JSON.parse(lines[0]);
  assert.equal(record.event, 'mcp_tool_call');
  assert.equal(record.request_id, 'req_1');
  assert.equal(record.tool_name, 'wechat_create_draft');
  assert.equal(record.job_id, 'job_1');
  assert.equal(record.job_status, 'saved');
  assert.equal('arguments' in record, false);
  assert.equal(typeof record.duration_ms, 'number');
});
