import {
  type ErrorCodeType,
  type ErrorContext,
  type Result,
  ErrorCode,
  createErrorResult,
} from '../schemas/index.js';

interface OperationalErrorLike {
  name?: string;
  code?: string;
  message?: string;
  details?: Record<string, unknown>;
}

export function mapOperationalErrorToResult<T>(error: unknown): Result<T> | null {
  if (!isOperationalErrorLike(error)) {
    return null;
  }

  if (error.name === 'AssetSourceError') {
    return createErrorResult(
      normalizeAssetErrorCode(error.code),
      error.message || 'Asset source error',
      sanitizeAssetDetails(error.details),
      getAssetErrorContext(error.code)
    );
  }

  if (error.name?.startsWith('Adapter')) {
    return createErrorResult(
      normalizeAdapterErrorCode(error.code),
      error.message || 'Adapter error',
      sanitizeAdapterDetails(error.details),
      getAdapterErrorContext(error.code)
    );
  }

  return null;
}

export function normalizeAssetErrorCode(code: string | undefined): ErrorCodeType {
  const map: Record<string, ErrorCodeType> = {
    ASSET_SOURCE_INVALID: ErrorCode.ASSET_SOURCE_INVALID,
    ASSET_FILE_NOT_READABLE: ErrorCode.ASSET_FILE_NOT_READABLE,
    ASSET_REMOTE_URL_FETCH_FAILED: ErrorCode.ASSET_REMOTE_URL_FETCH_FAILED,
    ASSET_SIZE_EXCEEDED: ErrorCode.ASSET_SIZE_EXCEEDED,
    ASSET_FORMAT_UNSUPPORTED: ErrorCode.ASSET_FORMAT_UNSUPPORTED,
  };

  return code ? map[code] || ErrorCode.INTERNAL_ERROR : ErrorCode.INTERNAL_ERROR;
}

export function normalizeAdapterErrorCode(code: string | undefined): ErrorCodeType {
  const map: Record<string, ErrorCodeType> = {
    adapter_unreachable: ErrorCode.ADAPTER_UNREACHABLE,
    adapter_auth_failed: ErrorCode.ADAPTER_AUTH_FAILED,
    adapter_timeout: ErrorCode.ADAPTER_TIMEOUT,
    adapter_endpoint_not_found: ErrorCode.ADAPTER_CAPABILITY_MISSING,
    adapter_account_not_allowed: ErrorCode.ADAPTER_AUTH_FAILED,
    adapter_internal_error: ErrorCode.WECHAT_API_ERROR,
    wechat_token_error: ErrorCode.WECHAT_TOKEN_INVALID,
    wechat_api_error: ErrorCode.WECHAT_API_ERROR,
  };

  return code ? map[code] || ErrorCode.WECHAT_API_ERROR : ErrorCode.WECHAT_API_ERROR;
}

function sanitizeAdapterDetails(
  details: Record<string, unknown> | undefined
): Record<string, unknown> | undefined {
  return details?.account ? { account: details.account } : undefined;
}

function sanitizeAssetDetails(
  details: Record<string, unknown> | undefined
): Record<string, unknown> | undefined {
  if (!details) {
    return undefined;
  }

  const allowedKeys = [
    'usage',
    'source_type',
    'sizeBytes',
    'size',
    'limit',
    'mimeType',
    'allowed',
    'status',
    'statusText',
  ];
  const sanitized: Record<string, unknown> = {};
  for (const key of allowedKeys) {
    if (key in details) {
      sanitized[key] = details[key];
    }
  }

  return Object.keys(sanitized).length > 0 ? sanitized : undefined;
}

function getAssetErrorContext(code: string | undefined): ErrorContext {
  switch (normalizeAssetErrorCode(code)) {
    case ErrorCode.ASSET_SIZE_EXCEEDED:
      return {
        next_action: 'resize_or_compress_asset',
        remediation_hint: 'Use wechat_list_accounts to inspect image size constraints, then retry with a smaller image.',
        retryable: false,
        current_phase: 'asset_preflight',
      };
    case ErrorCode.ASSET_FORMAT_UNSUPPORTED:
      return {
        next_action: 'convert_asset_format',
        remediation_hint: 'Use one of the MIME types returned by wechat_list_accounts for this asset usage.',
        retryable: false,
        current_phase: 'asset_preflight',
      };
    case ErrorCode.ASSET_SOURCE_INVALID:
    case ErrorCode.ASSET_FILE_NOT_READABLE:
      return {
        next_action: 'fix_asset_source',
        remediation_hint: 'For local_path, use a path under the accepted prefixes returned by wechat_list_accounts, or use remote_url.',
        retryable: false,
        current_phase: 'asset_loading',
      };
    case ErrorCode.ASSET_REMOTE_URL_FETCH_FAILED:
      return {
        next_action: 'retry_or_replace_remote_url',
        remediation_hint: 'Verify the remote image URL is reachable from the MCP runtime, or upload from local_path.',
        retryable: true,
        current_phase: 'asset_loading',
      };
    default:
      return {
        next_action: 'inspect_asset_error',
        retryable: false,
        current_phase: 'asset_loading',
      };
  }
}

function getAdapterErrorContext(code: string | undefined): ErrorContext {
  switch (normalizeAdapterErrorCode(code)) {
    case ErrorCode.ADAPTER_UNREACHABLE:
    case ErrorCode.ADAPTER_TIMEOUT:
      return {
        next_action: 'check_adapter_connectivity',
        remediation_hint: 'Check the ECS adapter endpoint, network path, and health status before retrying.',
        retryable: true,
        current_phase: 'adapter_call',
      };
    case ErrorCode.ADAPTER_AUTH_FAILED:
      return {
        next_action: 'check_adapter_credentials',
        remediation_hint: 'Verify adapter auth configuration and token references.',
        retryable: false,
        current_phase: 'adapter_call',
      };
    case ErrorCode.ADAPTER_CAPABILITY_MISSING:
      return {
        next_action: 'check_adapter_capabilities',
        remediation_hint: 'Call wechat_list_accounts and ensure the selected account/adapter supports the requested capability.',
        retryable: false,
        current_phase: 'adapter_call',
      };
    default:
      return {
        next_action: 'inspect_adapter_error',
        retryable: false,
        current_phase: 'adapter_call',
      };
  }
}

function isOperationalErrorLike(error: unknown): error is OperationalErrorLike {
  return Boolean(
    error &&
      typeof error === 'object' &&
      'name' in error &&
      'code' in error
  );
}
