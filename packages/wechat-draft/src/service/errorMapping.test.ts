import test from 'node:test';
import assert from 'node:assert/strict';
import { ErrorCode } from '../schemas/index.js';
import {
  mapOperationalErrorToResult,
  normalizeAdapterErrorCode,
  normalizeAssetErrorCode,
} from './errorMapping.js';

test('normalizeAssetErrorCode maps AssetSourceError codes to public MCP codes', () => {
  assert.equal(normalizeAssetErrorCode('ASSET_SIZE_EXCEEDED'), ErrorCode.ASSET_SIZE_EXCEEDED);
  assert.equal(
    normalizeAssetErrorCode('ASSET_REMOTE_URL_FETCH_FAILED'),
    ErrorCode.ASSET_REMOTE_URL_FETCH_FAILED
  );
  assert.equal(normalizeAssetErrorCode('UNKNOWN_ASSET_CODE'), ErrorCode.INTERNAL_ERROR);
});

test('normalizeAdapterErrorCode maps adapter implementation codes to public MCP codes', () => {
  assert.equal(normalizeAdapterErrorCode('adapter_timeout'), ErrorCode.ADAPTER_TIMEOUT);
  assert.equal(
    normalizeAdapterErrorCode('adapter_endpoint_not_found'),
    ErrorCode.ADAPTER_CAPABILITY_MISSING
  );
  assert.equal(normalizeAdapterErrorCode('wechat_token_error'), ErrorCode.WECHAT_TOKEN_INVALID);
  assert.equal(normalizeAdapterErrorCode('unknown_adapter_code'), ErrorCode.WECHAT_API_ERROR);
});

test('mapOperationalErrorToResult sanitizes adapter details', () => {
  const result = mapOperationalErrorToResult({
    name: 'AdapterInternalError',
    code: 'adapter_internal_error',
    message: 'Adapter failed',
    details: {
      account: 'xiaban',
      url: 'http://adapter.local/secret',
      token: 'secret',
    },
  });

  assert.deepEqual(result, {
    success: false,
    error: {
      code: ErrorCode.WECHAT_API_ERROR,
      message: 'Adapter failed',
      details: {
        account: 'xiaban',
      },
      next_action: 'inspect_adapter_error',
      retryable: false,
      current_phase: 'adapter_call',
    },
  });
});

test('mapOperationalErrorToResult adds remediation for asset size failures and redacts source', () => {
  const result = mapOperationalErrorToResult({
    name: 'AssetSourceError',
    code: 'ASSET_SIZE_EXCEEDED',
    message: 'cover_image size exceeds limit',
    details: {
      usage: 'cover_image',
      sizeBytes: 65537,
      limit: 65536,
      path: '/private/tmp/secret/cover.jpg',
    },
  });

  assert.deepEqual(result, {
    success: false,
    error: {
      code: ErrorCode.ASSET_SIZE_EXCEEDED,
      message: 'cover_image size exceeds limit',
      details: {
        usage: 'cover_image',
        sizeBytes: 65537,
        limit: 65536,
      },
      next_action: 'resize_or_compress_asset',
      remediation_hint: 'Use wechat_list_accounts to inspect image size constraints, then retry with a smaller image.',
      retryable: false,
      current_phase: 'asset_preflight',
    },
  });
});
