/**
 * Manual regression tests for ConfigLoader external account registry support.
 */

import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { ConfigLoader } from './dist/config/index.js';

let testCount = 0;
let passCount = 0;

function assert(condition, message) {
  testCount++;
  if (!condition) {
    console.error(`FAIL: ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  }
  passCount++;
  console.log(`PASS: ${message}`);
}

function assertThrows(fn, message, expectedText) {
  testCount++;
  try {
    fn();
  } catch (error) {
    const actual = error instanceof Error ? error.message : String(error);
    if (expectedText && !actual.includes(expectedText)) {
      console.error(`FAIL: ${message}: expected "${expectedText}", got "${actual}"`);
      throw error;
    }
    passCount++;
    console.log(`PASS: ${message}`);
    return;
  }
  throw new Error(`Assertion failed: ${message}`);
}

const originalEnv = {
  WECHAT_DRAFT_CONFIG_PATH: process.env.WECHAT_DRAFT_CONFIG_PATH,
  HERMES_DB_AUTH_TOKEN: process.env.HERMES_DB_AUTH_TOKEN,
  WECHAT_DRAFT_RUNTIME_PATH: process.env.WECHAT_DRAFT_RUNTIME_PATH,
};

const tempDir = mkdtempSync(join(tmpdir(), 'wechat-draft-config-test-'));

try {
  mkdirSync(join(tempDir, 'runtime'), { recursive: true });

  const configPath = join(tempDir, 'accounts.yaml');
  writeFileSync(
    configPath,
    `
accounts:
  - account_id: weiyuchengchun
    display_name: 微雨成春
    enabled: true
    adapter_account_ref: weiyuchengchun
    adapter_id: ali-wechat-egress
  - account_id: yueliang
    display_name: 月亮睡了我不睡
    enabled: true
    adapter_account_ref: yueliang
    adapter_id: ali-wechat-egress
  - account_id: xiaban
    display_name: 下班不躺平
    enabled: true
    adapter_account_ref: xiaban
    adapter_id: ali-wechat-egress
    metadata:
      style_profile_id: xiaban.default
adapters:
  - adapter_id: ali-wechat-egress
    base_url: http://127.0.0.1:3000
    auth_ref: env:WECHAT_ADAPTER_AUTH_TOKEN
    allowed_accounts:
      - weiyuchengchun
      - yueliang
      - xiaban
    egress_public_ip: <REDACTED>
    network_path: tailscale
    timeout_ms: 10000
    capabilities:
      - check_credentials
      - draft_add
      - draft_batchget
      - asset_upload
credentials:
  - account_id: xiaban
    credential_location: ecs_adapter
    adapter_account_ref: xiaban
    appid_hint: wx...xiaban
    secret_source_hint: ECS environment variable
hermes_db:
  base_url: http://127.0.0.1:8765
  timeout_ms: 5000
`
  );

  process.env.WECHAT_DRAFT_CONFIG_PATH = configPath;
  process.env.HERMES_DB_AUTH_TOKEN = 'redacted-test-token';
  process.env.WECHAT_DRAFT_RUNTIME_PATH = join(tempDir, 'runtime');

  const config = new ConfigLoader().load();
  assert(config.accounts.length === 3, 'external YAML config loads three accounts');
  assert(config.accounts.some((account) => account.account_id === 'xiaban'), 'external YAML config includes xiaban');
  assert(
    new ConfigLoader().getAccount('xiaban')?.display_name === '下班不躺平',
    'getAccount resolves xiaban from external config'
  );
  assert(
    config.adapters[0].allowed_accounts.includes('xiaban'),
    'external adapter allowed_accounts includes xiaban'
  );
  assert(config.hermes_db.auth_token === 'redacted-test-token', 'hermes auth token is injected from env only');
  assert(config.runtime_path === join(tempDir, 'runtime'), 'runtime path can be overridden by env');

  const invalidPath = join(tempDir, 'invalid-missing-allowed.yaml');
  writeFileSync(
    invalidPath,
    `
accounts:
  - account_id: xiaban
    display_name: 下班不躺平
    enabled: true
    adapter_account_ref: xiaban
    adapter_id: ali-wechat-egress
adapters:
  - adapter_id: ali-wechat-egress
    base_url: http://127.0.0.1:3000
    auth_ref: env:WECHAT_ADAPTER_AUTH_TOKEN
    allowed_accounts:
      - yueliang
hermes_db:
  base_url: http://127.0.0.1:8765
`
  );
  process.env.WECHAT_DRAFT_CONFIG_PATH = invalidPath;
  assertThrows(
    () => new ConfigLoader().load(),
    'enabled account missing from adapter allowed_accounts fails',
    'allowed_accounts must include "xiaban"'
  );

  const invalidIdPath = join(tempDir, 'invalid-account-id.yaml');
  writeFileSync(
    invalidIdPath,
    `
accounts:
  - account_id: Xiaban
    display_name: 下班不躺平
    enabled: true
    adapter_account_ref: xiaban
    adapter_id: ali-wechat-egress
adapters:
  - adapter_id: ali-wechat-egress
    base_url: http://127.0.0.1:3000
    auth_ref: env:WECHAT_ADAPTER_AUTH_TOKEN
    allowed_accounts:
      - xiaban
hermes_db:
  base_url: http://127.0.0.1:8765
`
  );
  process.env.WECHAT_DRAFT_CONFIG_PATH = invalidIdPath;
  assertThrows(
    () => new ConfigLoader().load(),
    'invalid uppercase account id fails',
    'lowercase ASCII'
  );

  delete process.env.WECHAT_DRAFT_CONFIG_PATH;
  delete process.env.HERMES_DB_AUTH_TOKEN;
  delete process.env.WECHAT_DRAFT_RUNTIME_PATH;
  const fallback = new ConfigLoader().load();
  assert(
    fallback.accounts.some((account) => account.account_id === 'xiaban'),
    'inline fallback includes xiaban without external config'
  );
} finally {
  if (originalEnv.WECHAT_DRAFT_CONFIG_PATH === undefined) {
    delete process.env.WECHAT_DRAFT_CONFIG_PATH;
  } else {
    process.env.WECHAT_DRAFT_CONFIG_PATH = originalEnv.WECHAT_DRAFT_CONFIG_PATH;
  }
  if (originalEnv.HERMES_DB_AUTH_TOKEN === undefined) {
    delete process.env.HERMES_DB_AUTH_TOKEN;
  } else {
    process.env.HERMES_DB_AUTH_TOKEN = originalEnv.HERMES_DB_AUTH_TOKEN;
  }
  if (originalEnv.WECHAT_DRAFT_RUNTIME_PATH === undefined) {
    delete process.env.WECHAT_DRAFT_RUNTIME_PATH;
  } else {
    process.env.WECHAT_DRAFT_RUNTIME_PATH = originalEnv.WECHAT_DRAFT_RUNTIME_PATH;
  }
  rmSync(tempDir, { recursive: true, force: true });
}

console.log(`\n${passCount}/${testCount} tests passed`);
