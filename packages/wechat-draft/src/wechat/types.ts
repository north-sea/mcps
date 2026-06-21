/**
 * WeChat Types for NAS-side MCP
 *
 * Mirrors types from wechat-draft-adapter for payload construction.
 */

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

export interface DraftAddArticle {
  title: string;
  author?: string;
  digest?: string;
  content: string;
  content_source_url?: string;
  thumb_media_id: string;
  need_open_comment?: 0 | 1;
  only_fans_can_comment?: 0 | 1;
}
