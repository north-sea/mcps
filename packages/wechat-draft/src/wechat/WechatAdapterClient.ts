/**
 * WechatAdapterClient
 *
 * NAS-side HTTP client for calling ECS WeChat adapter.
 * Handles auth, timeout, and error mapping.
 */

import { EcsWechatAdapterConfig } from '../config/types.js';
import { DraftAddRequest } from './types.js';

// ============================================================================
// Response Types
// ============================================================================

export interface AdapterHealthResponse {
  status: string;
  capabilities: string[];
  allowed_accounts: string[];
}

export interface AdapterCheckCredentialsResponse {
  success: boolean;
  account: string;
  token_valid?: boolean;
  expires_in?: number;
  error?: string;
  errcode?: number;
  errmsg?: string;
}

export interface AdapterCreateDraftResponse {
  success: boolean;
  account?: string;
  media_id?: string;
  error?: string;
  errcode?: number;
  errmsg?: string;
}

export interface AdapterUploadAssetResponse {
  success: boolean;
  account?: string;
  usage?: 'body_image' | 'cover_image';
  wechat_url?: string;        // body_image result
  thumb_media_id?: string;    // cover_image result
  error?: string;
  errcode?: number;
  errmsg?: string;
}

// ============================================================================
// Error Types
// ============================================================================

export class AdapterError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'AdapterError';
  }
}

export class AdapterUnreachableError extends AdapterError {
  constructor(baseUrl: string, cause: unknown) {
    super(
      `Adapter unreachable at ${baseUrl}: ${cause instanceof Error ? cause.message : 'Unknown error'}`,
      'adapter_unreachable',
      { baseUrl, cause: cause instanceof Error ? cause.message : String(cause) }
    );
    this.name = 'AdapterUnreachableError';
  }
}

export class AdapterAuthError extends AdapterError {
  constructor(message: string) {
    super(message, 'adapter_auth_failed');
    this.name = 'AdapterAuthError';
  }
}

export class AdapterTimeoutError extends AdapterError {
  constructor(timeoutMs: number) {
    super(`Adapter request timeout after ${timeoutMs}ms`, 'adapter_timeout', { timeoutMs });
    this.name = 'AdapterTimeoutError';
  }
}

export class AdapterAccountNotAllowedError extends AdapterError {
  constructor(account: string) {
    super(`Account "${account}" not allowed by adapter`, 'adapter_account_not_allowed', { account });
    this.name = 'AdapterAccountNotAllowedError';
  }
}

export class AdapterEndpointNotFoundError extends AdapterError {
  constructor(endpoint: string) {
    super(`Adapter endpoint not found: ${endpoint}`, 'adapter_endpoint_not_found', { endpoint });
    this.name = 'AdapterEndpointNotFoundError';
  }
}

export class AdapterInternalError extends AdapterError {
  constructor(message: string, details?: Record<string, unknown>) {
    super(message, 'adapter_internal_error', details);
    this.name = 'AdapterInternalError';
  }
}

export class AdapterTokenError extends AdapterError {
  constructor(
    public readonly account: string,
    public readonly errcode: number,
    public readonly errmsg: string
  ) {
    super(`WeChat token error for ${account}: [${errcode}] ${errmsg}`, 'wechat_token_error', {
      account,
      errcode,
      errmsg,
    });
    this.name = 'AdapterTokenError';
  }
}

export class AdapterWeChatApiError extends AdapterError {
  constructor(
    public readonly account: string,
    public readonly errcode: number,
    public readonly errmsg: string
  ) {
    super(`WeChat API error for ${account}: [${errcode}] ${errmsg}`, 'wechat_api_error', {
      account,
      errcode,
      errmsg,
    });
    this.name = 'AdapterWeChatApiError';
  }
}

// ============================================================================
// WechatAdapterClient
// ============================================================================

export class WechatAdapterClient {
  private baseUrl: string;
  private authToken: string;
  private timeoutMs: number;

  constructor(config: EcsWechatAdapterConfig) {
    this.baseUrl = config.base_url.replace(/\/$/, ''); // Remove trailing slash
    this.authToken = this.resolveAuthToken(config.auth_ref);
    this.timeoutMs = config.timeout_ms;
  }

  /**
   * Resolve auth token from auth_ref.
   * Supports:
   * - "env:VAR_NAME" -> read from process.env
   * - Direct string -> use as-is
   */
  private resolveAuthToken(authRef: string): string {
    if (authRef.startsWith('env:')) {
      const varName = authRef.substring(4);
      const token = process.env[varName];
      if (!token) {
        throw new Error(`Auth token environment variable not set: ${varName}`);
      }
      return token;
    }
    return authRef;
  }

  /**
   * Health check - verify adapter is reachable.
   */
  async checkHealth(): Promise<AdapterHealthResponse> {
    const url = `${this.baseUrl}/health`;
    const response = await this.fetch<AdapterHealthResponse>(url, {
      method: 'GET',
      requireAuth: false,
    });
    return response;
  }

  /**
   * Check credentials - AccessToken dry-run for account.
   */
  async checkCredentials(account: string): Promise<AdapterCheckCredentialsResponse> {
    const url = `${this.baseUrl}/accounts/${encodeURIComponent(account)}/check-credentials`;
    const response = await this.fetch<AdapterCheckCredentialsResponse>(url, {
      method: 'POST',
      requireAuth: true,
    });

    // Check for token error
    if (!response.success && response.error === 'token_error' && response.errcode && response.errmsg) {
      throw new AdapterTokenError(account, response.errcode, response.errmsg);
    }

    return response;
  }

  /**
   * Create draft - call adapter to create WeChat draft.
   */
  async createDraft(account: string, payload: DraftAddRequest): Promise<AdapterCreateDraftResponse> {
    const url = `${this.baseUrl}/accounts/${encodeURIComponent(account)}/drafts`;
    const response = await this.fetch<AdapterCreateDraftResponse>(url, {
      method: 'POST',
      requireAuth: true,
      body: payload,
    });

    // Check for errors
    if (!response.success) {
      // Token error
      if (response.error === 'token_error' && response.errcode && response.errmsg) {
        throw new AdapterTokenError(account, response.errcode, response.errmsg);
      }

      // WeChat API error
      if (response.error === 'wechat_api_error' && response.errcode && response.errmsg) {
        throw new AdapterWeChatApiError(account, response.errcode, response.errmsg);
      }

      // Other adapter error
      throw new AdapterInternalError(
        response.error || 'Draft creation failed',
        { account, response }
      );
    }

    return response;
  }

  /**
   * Upload asset - call adapter to upload image to WeChat material API.
   * Sends multipart/form-data with file bytes.
   */
  async uploadAsset(
    account: string,
    request: {
      usage: 'body_image' | 'cover_image';
      bytes: Uint8Array;
      filename: string;
      mimeType: string;
    }
  ): Promise<AdapterUploadAssetResponse> {
    const url = `${this.baseUrl}/accounts/${encodeURIComponent(account)}/assets`;

    // Build FormData
    const formData = new FormData();
    formData.append('usage', request.usage);

    // Create Blob from bytes and append as file
    const blob = new Blob([request.bytes], { type: request.mimeType });
    formData.append('media', blob, request.filename);

    // Optional: add filename and mime_type as separate fields if needed
    formData.append('filename', request.filename);
    formData.append('mime_type', request.mimeType);

    const response = await this.fetch<AdapterUploadAssetResponse>(url, {
      method: 'POST',
      requireAuth: true,
      customBody: formData,
    });

    // Check for errors
    if (!response.success) {
      // Token error
      if (response.error === 'token_error' && response.errcode && response.errmsg) {
        throw new AdapterTokenError(account, response.errcode, response.errmsg);
      }

      // WeChat API error (asset-specific: 40005, 40009, etc.)
      if (response.error === 'wechat_api_error' && response.errcode && response.errmsg) {
        throw new AdapterWeChatApiError(account, response.errcode, response.errmsg);
      }

      // Other adapter error
      throw new AdapterInternalError(
        response.error || 'Asset upload failed',
        { account, usage: request.usage, response }
      );
    }

    return response;
  }

  /**
   * Generic fetch with timeout, auth, and error handling.
   */
  private async fetch<T>(
    url: string,
    options: {
      method: 'GET' | 'POST';
      requireAuth: boolean;
      body?: unknown;
      customBody?: FormData;
    }
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const headers: Record<string, string> = {};

      // Only set Content-Type for JSON body; FormData sets its own
      if (!options.customBody) {
        headers['Content-Type'] = 'application/json';
      }

      if (options.requireAuth) {
        headers['Authorization'] = `Bearer ${this.authToken}`;
      }

      const response = await fetch(url, {
        method: options.method,
        headers,
        body: options.customBody
          ? options.customBody
          : options.body
            ? JSON.stringify(options.body)
            : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle HTTP errors
      if (response.status === 401) {
        throw new AdapterAuthError('Adapter authentication failed (401)');
      }

      if (response.status === 403) {
        const data = await response.json().catch(() => ({}));
        if ((data as any).error === 'account_not_allowed') {
          throw new AdapterAccountNotAllowedError((data as any).account || 'unknown');
        }
        throw new AdapterAuthError('Adapter forbidden (403)');
      }

      if (response.status === 404) {
        throw new AdapterEndpointNotFoundError(url);
      }

      if (response.status >= 500) {
        const text = await response.text().catch(() => 'Unknown error');
        throw new AdapterInternalError(`Adapter server error (${response.status})`, { text });
      }

      // Parse JSON response
      const data = await response.json();
      return data as T;
    } catch (error) {
      clearTimeout(timeoutId);

      // Timeout
      if (error instanceof Error && error.name === 'AbortError') {
        throw new AdapterTimeoutError(this.timeoutMs);
      }

      // Network errors (ECONNREFUSED, ENOTFOUND, etc.)
      if (error instanceof TypeError) {
        throw new AdapterUnreachableError(this.baseUrl, error);
      }

      // Re-throw adapter errors
      if (error instanceof AdapterError) {
        throw error;
      }

      // Unknown error
      throw new AdapterInternalError(
        error instanceof Error ? error.message : 'Unknown error',
        { originalError: String(error) }
      );
    }
  }
}
