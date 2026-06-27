import test from 'node:test';
import assert from 'node:assert/strict';
import { ErrorCode, createErrorResult, createSuccessResult } from '../schemas/index.js';
import { toMcpToolResult } from './toolResult.js';

test('toMcpToolResult wraps success result as text JSON', () => {
  const mcpResult = toMcpToolResult(createSuccessResult({ account: 'xiaban' }));

  assert.equal(mcpResult.isError, false);
  assert.equal(mcpResult.content[0].type, 'text');
  assert.deepEqual(JSON.parse(getTextContent(mcpResult)), {
    success: true,
    data: {
      account: 'xiaban',
    },
  });
});

test('toMcpToolResult marks error results as MCP errors', () => {
  const mcpResult = toMcpToolResult(
    createErrorResult(ErrorCode.ACCOUNT_NOT_FOUND, 'Account not found', undefined, {
      next_action: 'choose_enabled_account',
      remediation_hint: 'Call wechat_list_accounts and retry with an enabled account.',
      retryable: false,
      current_phase: 'account_resolution',
    })
  );

  assert.equal(mcpResult.isError, true);
  assert.deepEqual(JSON.parse(getTextContent(mcpResult)), {
    success: false,
    error: {
      code: ErrorCode.ACCOUNT_NOT_FOUND,
      message: 'Account not found',
      next_action: 'choose_enabled_account',
      remediation_hint: 'Call wechat_list_accounts and retry with an enabled account.',
      retryable: false,
      current_phase: 'account_resolution',
    },
  });
});

test('toMcpToolResult supports explicit isError override for non-saved draft jobs', () => {
  const mcpResult = toMcpToolResult(
    createSuccessResult({
      job_id: 'job_1',
      status: 'needs_operator_action',
    }),
    { isError: true }
  );

  assert.equal(mcpResult.isError, true);
  assert.equal(JSON.parse(getTextContent(mcpResult)).success, true);
});

function getTextContent(result: ReturnType<typeof toMcpToolResult>): string {
  const firstContent = result.content[0];
  assert.equal(firstContent.type, 'text');
  return firstContent.text;
}
