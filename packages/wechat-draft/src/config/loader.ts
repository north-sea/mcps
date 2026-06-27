/**
 * Configuration Loader
 *
 * Loads ServiceConfig from environment or config file.
 * Production can use external YAML/JSON with inline fallback for local dev.
 */

import { existsSync, readFileSync } from 'node:fs';
import { dirname, extname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseYaml } from 'yaml';
import { z } from 'zod';

import { ServiceConfig, AccountConfig, EcsWechatAdapterConfig } from './types.js';

const ACCOUNT_ID_PATTERN = /^[a-z][a-z0-9_]*$/;
const DEFAULT_CONFIG_PATH = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '../../config/accounts.yaml'
);

const metadataSchema = z.record(z.string(), z.unknown()).optional();
const accountIdSchema = z
  .string()
  .regex(ACCOUNT_ID_PATTERN, 'must be lowercase ASCII and env-safe: ^[a-z][a-z0-9_]*$');

const accountConfigSchema = z
  .object({
    account_id: accountIdSchema,
    display_name: z.string().min(1),
    enabled: z.boolean().default(true),
    adapter_account_ref: accountIdSchema.optional(),
    metadata: metadataSchema,
  })
  .strict()
  .transform((account) => ({
    ...account,
    adapter_account_ref: account.adapter_account_ref || account.account_id,
  }));

const adapterConfigSchema = z
  .object({
    base_url: z.string().min(1),
    auth_ref: z
      .string()
      .min(1)
      .refine(
        (value) => value.startsWith('env:'),
        'must reference env:VAR; raw auth tokens are not allowed'
      ),
    egress_public_ip: z.string().default('<REDACTED>'),
    network_path: z
      .enum(['tailscale', 'wireguard', 'ssh_tunnel', 'private_vpc', 'other'])
      .default('tailscale'),
    timeout_ms: z.coerce.number().int().positive().default(10000),
    capabilities: z.array(z.string().min(1)).default([
      'check_credentials',
      'draft_add',
      'draft_batchget',
      'asset_upload',
    ]),
    metadata: metadataSchema,
  })
  .strict();

const credentialConfigSchema = z
  .object({
    account_id: accountIdSchema,
    credential_location: z.literal('ecs_adapter'),
    adapter_account_ref: accountIdSchema,
    appid_hint: z.string().optional(),
    secret_source_hint: z.string().optional(),
    ip_whitelist_note: z.string().optional(),
  })
  .strict();

const hermesDbConfigSchema = z
  .object({
    base_url: z.string().min(1).default('http://100.113.231.101:8765'),
    timeout_ms: z.coerce.number().int().positive().default(10000),
  })
  .strict();

const serviceConfigFileSchema = z
  .object({
    accounts: z.array(accountConfigSchema).min(1),
    wechat_adapter: adapterConfigSchema,
    credentials: z.array(credentialConfigSchema).default([]),
    hermes_db: hermesDbConfigSchema
      .optional()
      .default({ base_url: 'http://100.113.231.101:8765', timeout_ms: 10000 }),
    runtime_path: z.string().optional(),
  })
  .strict();

export class ConfigLoader {
  private config: ServiceConfig | null = null;

  /**
   * Load configuration from external file or inline defaults.
   *
   * Priority:
   * 1. WECHAT_DRAFT_CONFIG_PATH
   * 2. packages/wechat-draft/config/accounts.yaml if present next to dist
   * 3. Inline safe fallback
   */
  load(): ServiceConfig {
    if (this.config) {
      return this.config;
    }

    const configPath = this.resolveConfigPath();
    this.config = configPath ? this.loadFromFile(configPath) : this.getDefaultConfig();
    return this.config;
  }

  private resolveConfigPath(): string | null {
    if (process.env.WECHAT_DRAFT_CONFIG_PATH) {
      return resolve(process.env.WECHAT_DRAFT_CONFIG_PATH);
    }

    return existsSync(DEFAULT_CONFIG_PATH) ? DEFAULT_CONFIG_PATH : null;
  }

  private loadFromFile(configPath: string): ServiceConfig {
    if (!existsSync(configPath)) {
      throw new Error(`WeChat Draft config file not found: ${configPath}`);
    }

    let rawConfig: unknown;
    try {
      const content = readFileSync(configPath, 'utf8');
      const extension = extname(configPath).toLowerCase();
      rawConfig = extension === '.json' ? JSON.parse(content) : parseYaml(content);
    } catch (error) {
      throw new Error(
        `Failed to parse WeChat Draft config ${configPath}: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }

    const parsed = serviceConfigFileSchema.safeParse(rawConfig);
    if (!parsed.success) {
      const issues = parsed.error.issues
        .map((issue) => `${issue.path.join('.') || '<root>'}: ${issue.message}`)
        .join('; ');
      throw new Error(`Invalid WeChat Draft config ${configPath}: ${issues}`);
    }

    const config: ServiceConfig = {
      accounts: parsed.data.accounts,
      wechat_adapter: {
        ...parsed.data.wechat_adapter,
        base_url: process.env.WECHAT_ADAPTER_BASE_URL || parsed.data.wechat_adapter.base_url,
        auth_ref: process.env.WECHAT_ADAPTER_AUTH_REF || parsed.data.wechat_adapter.auth_ref,
      },
      credentials: parsed.data.credentials,
      hermes_db: {
        ...parsed.data.hermes_db,
        base_url: process.env.HERMES_DB_BASE_URL || parsed.data.hermes_db.base_url,
        auth_token: process.env.HERMES_DB_AUTH_TOKEN,
      },
      runtime_path: process.env.WECHAT_DRAFT_RUNTIME_PATH || parsed.data.runtime_path,
    };

    return this.validateConfig(config, configPath);
  }

  private getDefaultConfig(): ServiceConfig {
    const wechatAdapter: EcsWechatAdapterConfig = {
      base_url: process.env.WECHAT_ADAPTER_BASE_URL || 'http://localhost:3000',
      auth_ref: process.env.WECHAT_ADAPTER_AUTH_REF || 'env:WECHAT_ADAPTER_AUTH_TOKEN',
      egress_public_ip: process.env.WECHAT_ECS_EGRESS_IP || '<REDACTED>',
      network_path: (process.env.WECHAT_ADAPTER_NETWORK_PATH as any) || 'tailscale',
      timeout_ms: 10000,
      capabilities: ['check_credentials', 'draft_add', 'draft_batchget', 'asset_upload'],
      metadata: {
        deployment_note: 'Ali ECS, systemd service wechat-adapter',
      },
    };

    const accounts: AccountConfig[] = [
      {
        account_id: 'weiyuchengchun',
        display_name: '微雨成春',
        enabled: true,
        adapter_account_ref: 'weiyuchengchun',
        metadata: {
          operator_note: 'MVP account for WeChat draft testing',
        },
      },
      {
        account_id: 'yueliang',
        display_name: '月亮睡了我不睡',
        enabled: true,
        adapter_account_ref: 'yueliang',
        metadata: {
          operator_note: 'Moon Sleeping account for WeChat draft testing',
        },
      },
      {
        account_id: 'xiaban',
        display_name: '下班不躺平',
        enabled: true,
        adapter_account_ref: 'xiaban',
        metadata: {
          operator_note: 'Xiaban account for multi-account production smoke',
          style_profile_id: 'xiaban.default',
        },
      },
    ];

    const credentials = [
      {
        account_id: 'weiyuchengchun',
        credential_location: 'ecs_adapter' as const,
        adapter_account_ref: 'weiyuchengchun',
        appid_hint: 'wx...abc123',
        secret_source_hint: 'ECS environment variable',
        ip_whitelist_note: 'ECS egress IP configured in WeChat console',
      },
      {
        account_id: 'yueliang',
        credential_location: 'ecs_adapter' as const,
        adapter_account_ref: 'yueliang',
        appid_hint: 'wx...yueliang',
        secret_source_hint: 'ECS environment variable',
        ip_whitelist_note: 'ECS egress IP configured in WeChat console',
      },
      {
        account_id: 'xiaban',
        credential_location: 'ecs_adapter' as const,
        adapter_account_ref: 'xiaban',
        appid_hint: 'wx...xiaban',
        secret_source_hint: 'ECS environment variable',
        ip_whitelist_note: 'ECS egress IP configured in WeChat console',
      },
    ];

    return this.validateConfig({
      accounts,
      wechat_adapter: wechatAdapter,
      credentials,
      hermes_db: {
        base_url: process.env.HERMES_DB_BASE_URL || 'http://100.113.231.101:8765',
        timeout_ms: parseInt(process.env.HERMES_DB_TIMEOUT_MS || '10000', 10),
        auth_token: process.env.HERMES_DB_AUTH_TOKEN,
      },
      runtime_path: process.env.WECHAT_DRAFT_RUNTIME_PATH,
    }, 'inline fallback');
  }

  private validateConfig(config: ServiceConfig, source: string): ServiceConfig {
    const accountIds = new Set<string>();
    for (const account of config.accounts) {
      if (accountIds.has(account.account_id)) {
        throw new Error(`Invalid WeChat Draft config ${source}: duplicate account_id "${account.account_id}"`);
      }
      accountIds.add(account.account_id);
    }

    for (const account of config.accounts) {
      if (!account.adapter_account_ref) {
        throw new Error(
          `Invalid WeChat Draft config ${source}: account "${account.account_id}" must define adapter_account_ref`
        );
      }
    }

    for (const credential of config.credentials) {
      const account = config.accounts.find((item) => item.account_id === credential.account_id);
      if (!account) {
        throw new Error(
          `Invalid WeChat Draft config ${source}: credential references missing account "${credential.account_id}"`
        );
      }

      if (account.adapter_account_ref !== credential.adapter_account_ref) {
        throw new Error(
          `Invalid WeChat Draft config ${source}: credential adapter_account_ref for "${credential.account_id}" must match account adapter_account_ref`
        );
      }
    }

    return config;
  }

  getAccount(accountId: string): AccountConfig | undefined {
    const config = this.load();
    return config.accounts.find((a) => a.account_id === accountId);
  }

  getWechatAdapter(): EcsWechatAdapterConfig {
    return this.load().wechat_adapter;
  }

  getEnabledAccounts(): AccountConfig[] {
    const config = this.load();
    return config.accounts.filter((a) => a.enabled);
  }

  getAllAccounts(includeDisabled: boolean = false): AccountConfig[] {
    const config = this.load();
    return includeDisabled ? config.accounts : this.getEnabledAccounts();
  }
}
