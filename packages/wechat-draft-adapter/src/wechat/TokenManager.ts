/**
 * TokenManager
 *
 * Manages WeChat AccessToken lifecycle:
 * - Fetch and cache token
 * - Refresh before expiry (safety margin: 300s)
 * - Serialize refresh per account
 * - Redact token in logs
 */

import { AccessTokenResponse, AccessTokenError, TokenState, AccountCredential } from '../types/wechat.js';

const WECHAT_TOKEN_API = 'https://api.weixin.qq.com/cgi-bin/token';
const TOKEN_SAFETY_MARGIN_MS = 300_000; // 5 minutes

export class TokenManager {
  private tokens: Map<string, TokenState> = new Map();
  private refreshing: Map<string, Promise<string>> = new Map();

  constructor(private credentials: Map<string, AccountCredential>) {}

  /**
   * Get valid AccessToken for account.
   * Returns cached token if valid, otherwise refreshes.
   */
  async getToken(account: string): Promise<string> {
    // Check cache
    const cached = this.tokens.get(account);
    if (cached && this.isTokenValid(cached)) {
      return cached.token;
    }

    // Serialize refresh
    const refreshing = this.refreshing.get(account);
    if (refreshing) {
      return refreshing;
    }

    // Start refresh
    const refreshPromise = this.refreshToken(account);
    this.refreshing.set(account, refreshPromise);

    try {
      const token = await refreshPromise;
      return token;
    } finally {
      this.refreshing.delete(account);
    }
  }

  /**
   * Force refresh token for account.
   */
  async refreshToken(account: string): Promise<string> {
    const credential = this.credentials.get(account);
    if (!credential) {
      throw new Error(`Credential not found for account: ${account}`);
    }

    const url = new URL(WECHAT_TOKEN_API);
    url.searchParams.set('grant_type', 'client_credential');
    url.searchParams.set('appid', credential.appid);
    url.searchParams.set('secret', credential.appsecret);

    const response = await fetch(url.toString());
    const data: unknown = await response.json();

    // Check for error
    if (typeof data === 'object' && data !== null && 'errcode' in data && (data as any).errcode !== 0) {
      const error = data as AccessTokenError;
      throw new TokenError(error.errcode, error.errmsg, account);
    }

    const tokenResponse = data as AccessTokenResponse;
    const now = Date.now();
    const expiresAt = now + tokenResponse.expires_in * 1000;

    // Cache token
    this.tokens.set(account, {
      token: tokenResponse.access_token,
      expiresAt,
      acquiredAt: now,
    });

    return tokenResponse.access_token;
  }

  /**
   * Check if cached token is still valid (with safety margin).
   */
  private isTokenValid(state: TokenState): boolean {
    return Date.now() < state.expiresAt - TOKEN_SAFETY_MARGIN_MS;
  }

  /**
   * Clear cached token for account (e.g., after auth error).
   */
  clearToken(account: string): void {
    this.tokens.delete(account);
  }

  /**
   * Get redacted token metadata (for logs/diagnostics).
   */
  getTokenMetadata(account: string): {
    hasCached: boolean;
    isValid: boolean;
    expiresIn?: number;
  } {
    const cached = this.tokens.get(account);
    if (!cached) {
      return { hasCached: false, isValid: false };
    }

    const isValid = this.isTokenValid(cached);
    const expiresIn = Math.max(0, Math.floor((cached.expiresAt - Date.now()) / 1000));

    return { hasCached: true, isValid, expiresIn };
  }
}

/**
 * TokenError - WeChat token API errors
 */
export class TokenError extends Error {
  constructor(
    public readonly errcode: number,
    public readonly errmsg: string,
    public readonly account: string
  ) {
    super(`WeChat token error for ${account}: [${errcode}] ${errmsg}`);
    this.name = 'TokenError';
  }

  isInvalidCredential(): boolean {
    return this.errcode === 40001 || this.errcode === 40013;
  }

  isIpWhitelistError(): boolean {
    return this.errcode === 40164;
  }

  isSecretFrozen(): boolean {
    return this.errcode === 40125;
  }
}
