import {
  type ErrorCodeType,
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
      error.details
    );
  }

  if (error.name?.startsWith('Adapter')) {
    return createErrorResult(
      normalizeAdapterErrorCode(error.code),
      error.message || 'Adapter error',
      sanitizeAdapterDetails(error.details)
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

function isOperationalErrorLike(error: unknown): error is OperationalErrorLike {
  return Boolean(
    error &&
      typeof error === 'object' &&
      'name' in error &&
      'code' in error
  );
}
