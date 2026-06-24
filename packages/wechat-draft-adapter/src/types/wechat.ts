/**
 * WeChat API Types
 */

export interface AccessTokenResponse {
  access_token: string;
  expires_in: number;
}

export interface AccessTokenError {
  errcode: number;
  errmsg: string;
}

export interface DraftAddRequest {
  articles: Array<{
    title: string;
    author?: string;
    digest?: string;
    content: string;
    content_source_url?: string;
    thumb_media_id: string;
    need_open_comment?: 0 | 1;
    only_fans_can_comment?: 0 | 1;
  }>;
}

export interface DraftAddResponse {
  media_id: string;
}

export interface DraftBatchGetRequest {
  offset?: number;
  count?: number;
  no_content?: 0 | 1;
}

export interface DraftBatchGetResponse {
  total_count?: number;
  item_count?: number;
  item?: Array<{
    media_id: string;
    content?: {
      news_item?: Array<{
        title?: string;
        author?: string;
        digest?: string;
        content?: string;
        content_source_url?: string;
        thumb_media_id?: string;
      }>;
    };
    update_time?: number;
  }>;
}

export interface WechatApiError {
  errcode: number;
  errmsg: string;
}

export interface TokenState {
  token: string;
  expiresAt: number;
  acquiredAt: number;
}

export interface AccountCredential {
  appid: string;
  appsecret: string;
}

export type UploadAssetUsage = 'body_image' | 'cover_image';

export interface UploadImageResponse {
  url: string;
}

export interface AddMaterialResponse {
  media_id: string;
  url?: string;
}
