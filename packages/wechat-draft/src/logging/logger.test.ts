import test from 'node:test';
import assert from 'node:assert/strict';
import { createLogger, sanitizeLogUrl } from './logger.js';

test('sanitizeLogUrl redacts sensitive query parameters', () => {
  assert.equal(
    sanitizeLogUrl('/mcp?token=secret&ok=1&access_token=secret2'),
    '/mcp?token=%3Credacted%3E&ok=1&access_token=%3Credacted%3E'
  );
});

test('createLogger redacts authorization fields', () => {
  const lines: string[] = [];
  const logger = createLogger({
    stream: {
      write(line: string) {
        lines.push(line);
        return true;
      },
    },
  });

  logger.info({
    authorization: 'Bearer secret',
    req: {
      headers: {
        authorization: 'Bearer secret',
      },
    },
  });

  const record = JSON.parse(lines[0]);
  const serialized = JSON.stringify(record);
  assert.equal(serialized.includes('Bearer secret'), false);
  assert.equal(serialized.includes('<redacted>'), true);
});
