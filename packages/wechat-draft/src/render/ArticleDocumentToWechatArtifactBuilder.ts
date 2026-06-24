import { createHash } from 'node:crypto';

import { WorkflowArtifact } from '../hermes/HermesDbClient.js';
import {
  ArticleDocumentEnvelope,
  WECHAT_API_ARTICLE_SCHEMA_VERSION,
} from './ArticleDocumentTypes.js';
import { ArticleDocumentValidator } from './ArticleDocumentValidator.js';
import { WechatArticleDocumentRenderer } from './WechatArticleDocumentRenderer.js';
import { getWechatStyleProfile } from './WechatStyleProfile.js';

export interface BuildWechatArticleArtifactInput {
  source: WorkflowArtifact;
  article?: ArticleDocumentEnvelope;
  style_profile_id?: string;
}

export class ArticleDocumentToWechatArtifactBuilder {
  private validator: ArticleDocumentValidator = new ArticleDocumentValidator();

  build(input: BuildWechatArticleArtifactInput): WorkflowArtifact {
    const article = input.article ?? this.parseArticleDocument(input.source);
    this.validator.assertValid(article);

    const styleProfileId =
      input.style_profile_id ||
      article.style_profile_id ||
      (typeof input.source.metadata.style_profile_id === 'string'
        ? input.source.metadata.style_profile_id
        : undefined) ||
      'yueliang.default';
    const renderer = new WechatArticleDocumentRenderer(getWechatStyleProfile(styleProfileId));
    const rendered = renderer.render({
      article,
      include_cover_image: false,
    });
    const coverThumbMediaId = article.cover?.thumb_media_id;

    if (!coverThumbMediaId) {
      throw new Error('article_document cover.thumb_media_id is required for wechat_api_article');
    }

    const contentHash = createHash('sha256').update(rendered.html).digest('hex');

    return {
      artifact_id: `${input.source.artifact_id}:wechat_api_article`,
      run_id: input.source.run_id,
      task_id: input.source.task_id,
      topic_id: input.source.topic_id,
      account: input.source.account,
      stage: 'publish_ready',
      type: 'wechat_api_article',
      name: `${article.title} - WeChat API Article`,
      content_hash: contentHash,
      content_size_bytes: Buffer.byteLength(rendered.html, 'utf8'),
      content_preview: this.toPreview(rendered.html),
      content_text: rendered.html,
      metadata: {
        title: article.title,
        digest: article.digest,
        author: article.author,
        content_source_url: article.content_source_url,
        publish_ready: true,
        schema_version: WECHAT_API_ARTICLE_SCHEMA_VERSION,
        style_profile_id: styleProfileId,
        source_article_document_artifact_id: input.source.artifact_id,
        source_article_document_schema_version: article.schema_version,
        source_markdown_artifact_id: article.source_markdown_artifact_id,
        parent_artifact_id: article.parent_artifact_id ?? input.source.artifact_id,
        cover: {
          thumb_media_id: coverThumbMediaId,
        },
        wechat_asset_manifest: {
          ready: true,
          cover_thumb_media_id: coverThumbMediaId,
          body_images: rendered.consumed_body_images.map((image) => ({
            wechat_url: image.wechat_url,
            position_hint: image.asset_ref,
          })),
        },
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  private parseArticleDocument(source: WorkflowArtifact): ArticleDocumentEnvelope {
    if (source.type !== 'article_document') {
      throw new Error(`Expected source artifact type article_document, got ${source.type}`);
    }

    if (!source.content_text) {
      throw new Error('article_document source must provide content_text JSON');
    }

    const parsed: unknown = JSON.parse(source.content_text);
    this.validator.assertValid(parsed);
    return parsed;
  }

  private toPreview(html: string): string {
    return html.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim().slice(0, 240);
  }
}
