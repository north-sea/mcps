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
    },
  });
});
