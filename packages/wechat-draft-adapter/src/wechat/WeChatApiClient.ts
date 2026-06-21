/**
 * WeChatApiClient
 *
 * Calls WeChat official API with token management and error handling.
 * MVP scope: draft/add only.
 */

import { TokenManager, TokenError } from './TokenManager.js';
import { DraftAddRequest, DraftAddResponse, WechatApiError } from '../types/wechat.js';

const WECHAT_DRAFT_ADD_API = 'https://api.weixin.qq.com/cgi-bin/draft/add';

export class WeChatApiClient {
  constructor(private tokenManager: TokenManager) {}

  /**
   * Create draft via WeChat draft/add API.
   * Automatically retries once on token error.
   */
  async createDraft(account: string, request: DraftAddRequest): Promise<DraftAddResponse> {
    try {
      return await this.callDraftAdd(account, request);
    } catch (error) {
      // Retry once on token error
      if (error instanceof WeChatApiError && error.isTokenError()) {
        this.tokenManager.clearToken(account);
        return await this.callDraftAdd(account, request);
      }
      throw error;
    }
  }

  /**
   * Call draft/add API with current token.
   */
  private async callDraftAdd(account: string, request: DraftAddRequest): Promise<DraftAddResponse> {
    const token = await this.tokenManager.getToken(account);
    const url = `${WECHAT_DRAFT_ADD_API}?access_token=${token}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    const data: unknown = await response.json();

    // Check for error
    if (typeof data === 'object' && data !== null && 'errcode' in data && (data as any).errcode !== 0) {
      const error = data as WechatApiError;
      throw new WeChatApiError(error.errcode, error.errmsg, account);
    }

    return data as DraftAddResponse;
  }
}

/**
 * WeChatApiError - WeChat API errors
 */
export class WeChatApiError extends Error {
  constructor(
    public readonly errcode: number,
    public readonly errmsg: string,
    public readonly account: string
  ) {
    super(`WeChat API error for ${account}: [${errcode}] ${errmsg}`);
    this.name = 'WeChatApiError';
  }

  isTokenError(): boolean {
    // 40001: invalid credential
    // 40014: invalid access_token
    // 42001: access_token expired
    return this.errcode === 40001 || this.errcode === 40014 || this.errcode === 42001;
  }

  isRateLimitError(): boolean {
    return this.errcode === 45009; // API freq out of limit
  }

  isPermissionError(): boolean {
    return this.errcode === 48001; // api unauthorized
  }

  isAssetError(): boolean {
    // 40007: invalid media_id
    // 40008: invalid message type
    return this.errcode === 40007 || this.errcode === 40008;
  }
}
