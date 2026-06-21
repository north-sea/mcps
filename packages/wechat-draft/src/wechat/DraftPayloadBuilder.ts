/**
 * DraftPayloadBuilder
 *
 * Builds WeChat draft/add payload from validated workflow artifact.
 * Enforces WeChat asset ready contract before constructing payload.
 */

import { WorkflowArtifact } from '../hermes/HermesDbClient.js';
import { ArtifactValidator, ArtifactMetadata } from '../hermes/ArtifactValidator.js';
import { DraftAddRequest } from './types.js';

export interface BuildPayloadResult {
  success: boolean;
  payload?: DraftAddRequest;
  errors?: Array<{
    field: string;
    issue: string;
  }>;
}

export class DraftPayloadBuilder {
  private validator: ArtifactValidator;

  constructor() {
    this.validator = new ArtifactValidator();
  }

  /**
   * Build draft/add payload from artifact.
   * Returns success=false if artifact is not WeChat-ready.
   */
  buildPayload(artifact: WorkflowArtifact): BuildPayloadResult {
    // Validate artifact first
    const validationResult = this.validator.validate(artifact);
    if (!validationResult.valid) {
      return {
        success: false,
        errors: validationResult.errors.map((e) => ({
          field: e.field,
          issue: e.issue,
        })),
      };
    }

    const metadata = artifact.metadata as ArtifactMetadata;

    // Extract content
    const content = this.extractContent(artifact);
    if (!content) {
      return {
        success: false,
        errors: [
          {
            field: 'content',
            issue: 'Content is empty or missing',
          },
        ],
      };
    }

    // Extract thumb_media_id
    const thumbMediaId =
      metadata.cover?.thumb_media_id ||
      metadata.wechat_asset_manifest?.cover_thumb_media_id;

    if (!thumbMediaId) {
      return {
        success: false,
        errors: [
          {
            field: 'thumb_media_id',
            issue: 'Cover thumb_media_id is missing',
          },
        ],
      };
    }

    // Check content for non-WeChat image URLs (second line of defense)
    const invalidImages = this.findInvalidImageUrls(content);
    if (invalidImages.length > 0) {
      return {
        success: false,
        errors: [
          {
            field: 'content',
            issue: `Content contains non-WeChat image URLs: ${invalidImages.slice(0, 3).join(', ')}`,
          },
        ],
      };
    }

    // Extract comment settings (MVP default: comments disabled)
    const commentSettings = (metadata as any).comment_settings || {};
    const needOpenComment = commentSettings.enabled ? 1 : 0;
    const onlyFansCanComment = commentSettings.only_fans ? 1 : 0;

    // Build payload
    const payload: DraftAddRequest = {
      articles: [
        {
          title: metadata.title || 'Untitled',
          author: metadata.author,
          digest: metadata.digest,
          content,
          content_source_url: metadata.content_source_url,
          thumb_media_id: thumbMediaId,
          need_open_comment: needOpenComment as 0 | 1,
          only_fans_can_comment: onlyFansCanComment as 0 | 1,
        },
      ],
    };

    return {
      success: true,
      payload,
    };
  }

  /**
   * Extract content from artifact (content_text preferred over content_ref).
   */
  private extractContent(artifact: WorkflowArtifact): string | null {
    if (artifact.content_text) {
      return artifact.content_text;
    }

    // TODO: support content_ref (e.g., S3 URL or file path)
    // For MVP, only content_text is supported
    if (artifact.content_ref) {
      throw new Error(
        'content_ref is not yet supported; artifact must provide content_text (T013 limitation)'
      );
    }

    return null;
  }

  /**
   * Find non-WeChat image URLs in content (second line of defense).
   * WeChat image URLs should start with https://mmbiz.qpic.cn/
   */
  private findInvalidImageUrls(content: string): string[] {
    const invalidUrls: string[] = [];

    // Match image tags with src attribute
    const imgRegex = /<img[^>]+src=["']([^"']+)["'][^>]*>/gi;
    let match;

    while ((match = imgRegex.exec(content)) !== null) {
      const url = match[1];
      if (!this.isWechatImageUrl(url)) {
        invalidUrls.push(url);
      }
    }

    return invalidUrls;
  }

  /**
   * Check if URL is a valid WeChat image URL.
   */
  private isWechatImageUrl(url: string): boolean {
    return url.startsWith('https://mmbiz.qpic.cn/');
  }
}
