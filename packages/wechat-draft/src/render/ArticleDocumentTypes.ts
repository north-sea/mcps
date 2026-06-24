export const ARTICLE_DOCUMENT_SCHEMA_VERSION = 'article_document.tiptap.v1';
export const WECHAT_API_ARTICLE_SCHEMA_VERSION = 'wechat_api_article.v1';

export type ArticleDocumentSchemaVersion = typeof ARTICLE_DOCUMENT_SCHEMA_VERSION;

export interface ArticleDocumentAsset {
  asset_ref: string;
  wechat_url?: string;
  alt?: string;
  width?: number;
  height?: number;
  ready?: boolean;
}

export interface ArticleDocumentCover {
  asset_ref?: string;
  thumb_media_id?: string;
  alt?: string;
}

export interface ArticleDocumentMetadata {
  title: string;
  digest?: string;
  author?: string;
  content_source_url?: string;
  style_profile_id?: string;
  source_markdown_artifact_id?: string;
  parent_artifact_id?: string;
}

export interface ArticleDocumentEnvelope {
  schema_version: ArticleDocumentSchemaVersion;
  title: string;
  digest?: string;
  author?: string;
  style_profile_id?: string;
  content_source_url?: string;
  doc: unknown;
  assets?: Record<string, ArticleDocumentAsset>;
  cover?: ArticleDocumentCover;
  metadata?: Record<string, unknown>;
  source_markdown_artifact_id?: string;
  parent_artifact_id?: string;
}

export interface ArticleDocumentValidationIssue {
  field: string;
  issue: string;
}

export interface ArticleDocumentValidationResult {
  valid: boolean;
  errors: ArticleDocumentValidationIssue[];
}

export interface RenderArticleDocumentInput {
  article: ArticleDocumentEnvelope;
  assets?: Record<string, ArticleDocumentAsset>;
  include_cover_image?: boolean;
}

export interface RenderArticleDocumentOutput {
  html: string;
  consumed_body_images: Array<{
    asset_ref: string;
    wechat_url: string;
  }>;
}
