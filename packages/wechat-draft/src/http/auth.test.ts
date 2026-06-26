import test from 'node:test';
import assert from 'node:assert/strict';
import {
  extractBearerToken,
  isBearerAuthorized,
  isHostAllowed,
  isOriginAllowed,
} from './auth.js';

test('extractBearerToken parses bearer tokens only', () => {
  assert.equal(extractBearerToken('Bearer secret'), 'secret');
  assert.equal(extractBearerToken('bearer secret'), 'secret');
  assert.equal(extractBearerToken('Basic secret'), null);
  assert.equal(extractBearerToken(undefined), null);
});

test('isBearerAuthorized supports required and empty auth token modes', () => {
  assert.equal(isBearerAuthorized('Bearer secret', 'secret'), true);
  assert.equal(isBearerAuthorized('Bearer wrong', 'secret'), false);
  assert.equal(isBearerAuthorized(undefined, 'secret'), false);
  assert.equal(isBearerAuthorized(undefined, undefined), true);
  assert.equal(isBearerAuthorized(undefined, ''), true);
});

test('isHostAllowed matches exact hosts and hostnames without ports', () => {
  assert.equal(isHostAllowed('127.0.0.1:3001', ['127.0.0.1']), true);
  assert.equal(isHostAllowed('wechat-draft-mcp:3001', ['wechat-draft-mcp']), true);
  assert.equal(isHostAllowed('nas.local:3001', ['nas.local:3001']), true);
  assert.equal(isHostAllowed('evil.example', ['127.0.0.1']), false);
  assert.equal(isHostAllowed(undefined, ['127.0.0.1']), false);
  assert.equal(isHostAllowed('evil.example', []), true);
});

test('isOriginAllowed requires exact origins only when configured', () => {
  assert.equal(isOriginAllowed('http://nas.local:3001', ['http://nas.local:3001']), true);
  assert.equal(isOriginAllowed('http://evil.example', ['http://nas.local:3001']), false);
  assert.equal(isOriginAllowed(undefined, ['http://nas.local:3001']), true);
  assert.equal(isOriginAllowed('http://evil.example', []), true);
});
