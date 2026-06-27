/**
 * Configuration Types for WeChat Draft MCP
 *
 * Mirrors data-model.md definitions:
 * - AccountConfig: WeChat account configuration
 * - EcsWechatAdapterConfig: ECS adapter connection config
 * - ApiCredentialConfig: Credential location and hints
 */

export interface AccountConfig {
  account_id: string;
  display_name: string;
  enabled: boolean;
  adapter_account_ref: string;
  metadata?: Record<string, unknown>;
}

export interface ApiCredentialConfig {
  account_id: string;
  credential_location: 'ecs_adapter';
  adapter_account_ref: string;
  appid_hint?: string;
  secret_source_hint?: string;
  ip_whitelist_note?: string;
}

export interface EcsWechatAdapterConfig {
  base_url: string;
  auth_ref: string;
  egress_public_ip: string;
  network_path: 'tailscale' | 'wireguard' | 'ssh_tunnel' | 'private_vpc' | 'other';
  timeout_ms: number;
  capabilities: string[];
  metadata?: Record<string, unknown>;
}

export interface HermesDbConfig {
  base_url: string;
  timeout_ms: number;
  auth_token?: string;
}

export interface ServiceConfig {
  accounts: AccountConfig[];
  wechat_adapter: EcsWechatAdapterConfig;
  credentials: ApiCredentialConfig[];
  hermes_db: HermesDbConfig;
  runtime_path?: string;
}
