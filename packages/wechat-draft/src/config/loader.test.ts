import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

import { ConfigLoader } from './loader.js';

test('ConfigLoader overlays runtime endpoint env vars on external YAML config', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'wechat-draft-config-'));
  const configPath = join(dir, 'accounts.yaml');
  await writeFile(configPath, makeConfigYaml(), 'utf8');

  const previous = {
    WECHAT_DRAFT_CONFIG_PATH: process.env.WECHAT_DRAFT_CONFIG_PATH,
    WECHAT_ADAPTER_BASE_URL: process.env.WECHAT_ADAPTER_BASE_URL,
    WECHAT_ADAPTER_AUTH_REF: process.env.WECHAT_ADAPTER_AUTH_REF,
    HERMES_DB_BASE_URL: process.env.HERMES_DB_BASE_URL,
  };

  process.env.WECHAT_DRAFT_CONFIG_PATH = configPath;
  process.env.WECHAT_ADAPTER_BASE_URL = 'http://adapter.runtime:3000';
  process.env.WECHAT_ADAPTER_AUTH_REF = 'env:RUNTIME_ADAPTER_TOKEN';
  process.env.HERMES_DB_BASE_URL = 'http://hermes.runtime:8080';

  try {
    const loader = new ConfigLoader();
    const config = loader.load();

    assert.equal(config.wechat_adapter.base_url, 'http://adapter.runtime:3000');
    assert.equal(config.wechat_adapter.auth_ref, 'env:RUNTIME_ADAPTER_TOKEN');
    assert.equal(config.hermes_db.base_url, 'http://hermes.runtime:8080');
  } finally {
    restoreEnv(previous);
    await rm(dir, { recursive: true, force: true });
  }
});

function restoreEnv(values: Record<string, string | undefined>): void {
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = value;
    }
  }
}

function makeConfigYaml(): string {
  return `
accounts:
  - account_id: xiaban
    display_name: 下班不躺平
    enabled: true
    adapter_account_ref: xiaban

wechat_adapter:
  base_url: http://adapter.file:3000
  auth_ref: env:FILE_ADAPTER_TOKEN
  capabilities:
    - check_credentials
    - draft_add
    - draft_batchget
    - asset_upload

credentials:
  - account_id: xiaban
    credential_location: ecs_adapter
    adapter_account_ref: xiaban

hermes_db:
  base_url: http://hermes.file:8080
  timeout_ms: 10000
`;
}
