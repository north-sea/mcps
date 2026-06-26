import test from 'node:test';
import assert from 'node:assert/strict';
import type { HealthSnapshot } from '../service/index.js';
import { type HealthResponseWriter, getHealthHttpStatus, sendHealthResponse } from './health.js';

test('getHealthHttpStatus returns 503 only for local unhealthy status', () => {
  assert.equal(getHealthHttpStatus(makeSnapshot('ok')), 200);
  assert.equal(getHealthHttpStatus(makeSnapshot('degraded')), 200);
  assert.equal(getHealthHttpStatus(makeSnapshot('unhealthy')), 503);
});

test('sendHealthResponse writes JSON body for GET health', async () => {
  const response = createMockResponse();
  const snapshot = makeSnapshot('degraded');

  await sendHealthResponse(response, snapshot, true);

  assert.equal(response.statusCode, 200);
  assert.deepEqual(response.jsonBody, snapshot);
  assert.equal(response.ended, false);
});

test('sendHealthResponse ends without body for HEAD health', async () => {
  const response = createMockResponse();

  await sendHealthResponse(response, makeSnapshot('unhealthy'), false);

  assert.equal(response.statusCode, 503);
  assert.equal(response.jsonBody, undefined);
  assert.equal(response.ended, true);
});

function makeSnapshot(status: HealthSnapshot['status']): HealthSnapshot {
  return {
    status,
    version: '0.2.0',
    checks: {
      config_loaded: true,
      runtime_writable: status !== 'unhealthy',
      sqlite_ready: status !== 'unhealthy',
      adapter_reachable: status === 'ok',
      hermes_db_reachable: status === 'ok',
    },
  };
}

function createMockResponse(): HealthResponseWriter & {
  statusCode?: number;
  jsonBody?: unknown;
  ended: boolean;
} {
  return {
    ended: false,
    status(code: number) {
      this.statusCode = code;
      return this;
    },
    json(body: unknown) {
      this.jsonBody = body;
      return this;
    },
    end() {
      this.ended = true;
      return this;
    },
  };
}
