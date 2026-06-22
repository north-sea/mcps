/**
 * WeChatApiClient
 *
 * Calls WeChat official API with token management and error handling.
 * MVP scope: draft/add only.
 */

import { TokenManager, TokenError } from './TokenManager.js';
import { DraftAddRequest, DraftAddResponse, WechatApiError, UploadImageResponse, AddMaterialResponse } from '../types/wechat.js';

const WECHAT_DRAFT_ADD_API = 'https://api.weixin.qq.com/cgi-bin/draft/add';
const WECHAT_UPLOAD_IMAGE_API = 'https://api.weixin.qq.com/cgi-bin/media/uploadimg';
const WECHAT_ADD_MATERIAL_API = 'https://api.weixin.qq.com/cgi-bin/material/add_material';

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

  /**
   * Upload body image via WeChat uploadimg API.
   * Returns a WeChat CDN URL suitable for inline content.
   * Automatically retries once on token error.
   */
  async uploadBodyImage(account: string, fileBuffer: Buffer, filename: string): Promise<UploadImageResponse> {
    try {
      return await this.callUploadImage(account, fileBuffer, filename);
    } catch (error) {
      // Retry once on token error
      if (error instanceof WeChatApiError && error.isTokenError()) {
        this.tokenManager.clearToken(account);
        return await this.callUploadImage(account, fileBuffer, filename);
      }
      throw error;
    }
  }

  /**
   * Upload cover image via WeChat add_material API with type=thumb.
   * Returns a permanent thumb media_id for draft cover.
   * Automatically retries once on token error.
   */
  async uploadCoverImage(account: string, fileBuffer: Buffer, filename: string): Promise<AddMaterialResponse> {
    try {
      return await this.callAddMaterial(account, fileBuffer, filename, 'thumb');
    } catch (error) {
      // Retry once on token error
      if (error instanceof WeChatApiError && error.isTokenError()) {
        this.tokenManager.clearToken(account);
        return await this.callAddMaterial(account, fileBuffer, filename, 'thumb');
      }
      throw error;
    }
  }

  /**
   * Call uploadimg API with current token.
   */
  private async callUploadImage(account: string, fileBuffer: Buffer, filename: string): Promise<UploadImageResponse> {
    const token = await this.tokenManager.getToken(account);
    const url = `${WECHAT_UPLOAD_IMAGE_API}?access_token=${token}`;

    // Build FormData
    const formData = new FormData();
    const blob = new Blob([fileBuffer], { type: 'image/jpeg' });
    formData.append('media', blob, filename);

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    const data: unknown = await response.json();

    // Check for error
    if (typeof data === 'object' && data !== null && 'errcode' in data && (data as any).errcode !== 0) {
      const error = data as WechatApiError;
      throw new WeChatApiError(error.errcode, error.errmsg, account);
    }

    return data as UploadImageResponse;
  }

  /**
   * Call add_material API with current token.
   */
  private async callAddMaterial(
    account: string,
    fileBuffer: Buffer,
    filename: string,
    type: 'thumb' | 'image'
  ): Promise<AddMaterialResponse> {
    const token = await this.tokenManager.getToken(account);
    const url = `${WECHAT_ADD_MATERIAL_API}?access_token=${token}&type=${type}`;

    // Build FormData
    const formData = new FormData();
    const blob = new Blob([fileBuffer], { type: 'image/jpeg' });
    formData.append('media', blob, filename);

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    const data: unknown = await response.json();

    // Check for error
    if (typeof data === 'object' && data !== null && 'errcode' in data && (data as any).errcode !== 0) {
      const error = data as WechatApiError;
      throw new WeChatApiError(error.errcode, error.errmsg, account);
    }

    return data as AddMaterialResponse;
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
    // 40005: invalid file type
    // 40007: invalid media_id
    // 40008: invalid message type
    // 40009: invalid image file size
    return this.errcode === 40005 || this.errcode === 40007 || this.errcode === 40008 || this.errcode === 40009;
  }
}
