/**
 * Unified MCP Result Types
 *
 * All MCP tools return structured results with consistent error handling.
 * Side-effecting tools (wechat_create_draft) are explicitly marked.
 */

import { z } from 'zod';

// ============================================================================
// Success Result
// ============================================================================

export const SuccessResultSchema = z.object({
  success: z.literal(true),
  data: z.unknown(),
});

export type SuccessResult<T = unknown> = {
  success: true;
  data: T;
};

// ============================================================================
// Error Result
// ============================================================================

export const ErrorResultSchema = z.object({
  success: z.literal(false),
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.string(), z.unknown()).optional(),
  }),
});

export type ErrorResult = {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
};

// ============================================================================
// Result Union
// ============================================================================

export type Result<T = unknown> = SuccessResult<T> | ErrorResult;

// ============================================================================
// Error Codes
// ============================================================================

export const ErrorCode = {
  // Config errors
  ACCOUNT_NOT_FOUND: 'account_not_found',
  ACCOUNT_DISABLED: 'account_disabled',
  ADAPTER_NOT_FOUND: 'adapter_not_found',

  // Artifact errors
  ARTIFACT_NOT_FOUND: 'artifact_not_found',
  ARTIFACT_INVALID_STAGE: 'artifact_invalid_stage',
  ARTIFACT_INVALID_TYPE: 'artifact_invalid_type',
  ARTIFACT_NOT_PUBLISH_READY: 'artifact_not_publish_ready',
  ARTIFACT_WECHAT_ASSETS_NOT_READY: 'artifact_wechat_assets_not_ready',
  ARTIFACT_VALIDATION_FAILED: 'artifact_validation_failed',

  // Adapter errors
  ADAPTER_UNREACHABLE: 'adapter_unreachable',
  ADAPTER_AUTH_FAILED: 'adapter_auth_failed',
  ADAPTER_CAPABILITY_MISSING: 'adapter_capability_missing',
  ADAPTER_TIMEOUT: 'adapter_timeout',

  // WeChat API errors
  WECHAT_TOKEN_INVALID: 'wechat_token_invalid',
  WECHAT_TOKEN_EXPIRED: 'wechat_token_expired',
  WECHAT_IP_WHITELIST_ERROR: 'wechat_ip_whitelist_error',
  WECHAT_RATE_LIMIT: 'wechat_rate_limit',
  WECHAT_PERMISSION_DENIED: 'wechat_permission_denied',
  WECHAT_ASSET_INVALID: 'wechat_asset_invalid',
  WECHAT_API_ERROR: 'wechat_api_error',

  // Asset upload specific errors
  ASSET_SOURCE_INVALID: 'asset_source_invalid',
  ASSET_FILE_NOT_READABLE: 'asset_file_not_readable',
  ASSET_REMOTE_URL_FETCH_FAILED: 'asset_remote_url_fetch_failed',
  ASSET_SIZE_EXCEEDED: 'asset_size_exceeded',
  ASSET_FORMAT_UNSUPPORTED: 'asset_format_unsupported',

  // Job errors
  JOB_NOT_FOUND: 'job_not_found',
  JOB_ALREADY_EXISTS: 'job_already_exists',

  // Hermes-db errors
  HERMES_DB_UNREACHABLE: 'hermes_db_unreachable',
  HERMES_DB_QUERY_FAILED: 'hermes_db_query_failed',
  HERMES_DB_UPSERT_FAILED: 'hermes_db_upsert_failed',

  // Internal errors
  INTERNAL_ERROR: 'internal_error',
  INVALID_INPUT: 'invalid_input',
} as const;

export type ErrorCodeType = typeof ErrorCode[keyof typeof ErrorCode];

// ============================================================================
// Helper Functions
// ============================================================================

export function createSuccessResult<T>(data: T): SuccessResult<T> {
  return { success: true, data };
}

export function createErrorResult(
  code: ErrorCodeType,
  message: string,
  details?: Record<string, unknown>
): ErrorResult {
  return {
    success: false,
    error: { code, message, details },
  };
}
