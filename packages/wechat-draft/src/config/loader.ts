/**
 * Configuration Loader
 *
 * Loads ServiceConfig from environment or config file.
 * MVP loads from inline config; production should use external YAML/JSON.
 */

import { ServiceConfig, AccountConfig, EcsWechatAdapterConfig } from './types.js';

export class ConfigLoader {
  private config: ServiceConfig | null = null;

  /**
   * Load configuration from environment or inline defaults.
   * MVP uses inline config; production should load from file/env.
   */
  load(): ServiceConfig {
    if (this.config) {
      return this.config;
    }

    // MVP: inline config example based on infrastructure-config.md
    // Production: load from process.env or config file
    this.config = this.getDefaultConfig();
    return this.config;
  }

  private getDefaultConfig(): ServiceConfig {
    const adapters: EcsWechatAdapterConfig[] = [
      {
        adapter_id: 'ali-wechat-egress',
        base_url: process.env.WECHAT_ADAPTER_BASE_URL || 'http://localhost:3000',
        auth_ref: process.env.WECHAT_ADAPTER_AUTH_REF || 'env:WECHAT_ADAPTER_AUTH_TOKEN',
        allowed_accounts: ['weiyuchengchun'],
        egress_public_ip: process.env.WECHAT_ECS_EGRESS_IP || '<REDACTED>',
        network_path: (process.env.WECHAT_ADAPTER_NETWORK_PATH as any) || 'tailscale',
        timeout_ms: 10000,
        capabilities: ['check_credentials', 'draft_add', 'draft_batchget'],
        metadata: {
          deployment_note: 'Ali ECS, systemd service wechat-adapter',
        },
      },
    ];

    const accounts: AccountConfig[] = [
      {
        account_id: 'weiyuchengchun',
        display_name: '微雨成春',
        enabled: true,
        adapter_account_ref: 'weiyuchengchun',
        adapter_id: 'ali-wechat-egress',
        metadata: {
          operator_note: 'MVP account for WeChat draft testing',
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
    ];

    return {
      accounts,
      adapters,
      credentials,
      hermes_db: {
        base_url: process.env.HERMES_DB_BASE_URL || 'http://nas.local:8765',
        timeout_ms: parseInt(process.env.HERMES_DB_TIMEOUT_MS || '10000', 10),
        auth_token: process.env.HERMES_DB_AUTH_TOKEN,
      },
      runtime_path: process.env.WECHAT_DRAFT_RUNTIME_PATH,
    };
  }

  getAccount(accountId: string): AccountConfig | undefined {
    const config = this.load();
    return config.accounts.find((a) => a.account_id === accountId);
  }

  getAdapter(adapterId: string): EcsWechatAdapterConfig | undefined {
    const config = this.load();
    return config.adapters.find((a) => a.adapter_id === adapterId);
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
