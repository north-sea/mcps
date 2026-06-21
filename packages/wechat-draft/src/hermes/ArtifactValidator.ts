/**
 * Artifact Validator
 *
 * Validates that a workflow_artifact is WeChat-ready before creating draft.
 * Checks stage, type, publish_ready flag, and wechat_asset_manifest.
 */

import { WorkflowArtifact } from './HermesDbClient.js';
import { ErrorCode } from '../schemas/index.js';

export interface ValidationError {
  field: string;
  issue: string;
  severity: 'error' | 'warning';
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

export interface WechatAssetManifest {
  ready: boolean;
  body_images?: Array<{
    wechat_url: string;
    position_hint?: string;
  }>;
  cover_thumb_media_id?: string;
  asset_warnings?: string[];
}

export interface ArtifactMetadata {
  publish_ready?: boolean;
  title?: string;
  digest?: string;
  author?: string;
  content_source_url?: string;
  cover?: {
    thumb_media_id?: string;
  };
  style_profile_id?: string;
  style_version?: string;
  wechat_asset_manifest?: WechatAssetManifest;
  format?: string;
}

// ============================================================================
// ArtifactValidator
// ============================================================================

export class ArtifactValidator {
  /**
   * Validate that artifact is WeChat-ready.
   *
   * Required checks:
   * - stage === 'publish_ready'
   * - type === 'wechat_api_article'
   * - metadata.publish_ready === true
   * - metadata.wechat_asset_manifest.ready === true
   * - metadata.cover.thumb_media_id exists
   * - body_images all use WeChat URLs (mmbiz.qpic.cn)
   */
  validate(artifact: WorkflowArtifact): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationError[] = [];

    // Check stage
    if (artifact.stage !== 'publish_ready') {
      errors.push({
        field: 'stage',
        issue: `Expected 'publish_ready', got '${artifact.stage}'`,
        severity: 'error',
      });
    }

    // Check type
    if (artifact.type !== 'wechat_api_article') {
      errors.push({
        field: 'type',
        issue: `Expected 'wechat_api_article', got '${artifact.type}'`,
        severity: 'error',
      });
    }

    // Parse metadata
    const metadata = artifact.metadata as ArtifactMetadata;

    // Check publish_ready flag
    if (!metadata.publish_ready) {
      errors.push({
        field: 'metadata.publish_ready',
        issue: 'publish_ready flag is false or missing',
        severity: 'error',
      });
    }

    // Check title
    if (!metadata.title) {
      errors.push({
        field: 'metadata.title',
        issue: 'Title is required',
        severity: 'error',
      });
    }

    // Check wechat_asset_manifest
    const assetManifest = metadata.wechat_asset_manifest;
    if (!assetManifest) {
      errors.push({
        field: 'metadata.wechat_asset_manifest',
        issue: 'wechat_asset_manifest is missing',
        severity: 'error',
      });
    } else {
      // Check ready flag
      if (!assetManifest.ready) {
        errors.push({
          field: 'metadata.wechat_asset_manifest.ready',
          issue: 'wechat_asset_manifest.ready is false',
          severity: 'error',
        });
      }

      // Check cover thumb_media_id
      if (!metadata.cover?.thumb_media_id && !assetManifest.cover_thumb_media_id) {
        errors.push({
          field: 'metadata.cover.thumb_media_id',
          issue: 'Cover thumb_media_id is missing',
          severity: 'error',
        });
      }

      // Check body images use WeChat URLs
      if (assetManifest.body_images) {
        for (const img of assetManifest.body_images) {
          if (!this.isWechatImageUrl(img.wechat_url)) {
            errors.push({
              field: 'metadata.wechat_asset_manifest.body_images',
              issue: `Invalid WeChat image URL: ${img.wechat_url}`,
              severity: 'error',
            });
          }
        }
      }

      // Collect asset warnings
      if (assetManifest.asset_warnings && assetManifest.asset_warnings.length > 0) {
        for (const warning of assetManifest.asset_warnings) {
          warnings.push({
            field: 'metadata.wechat_asset_manifest.asset_warnings',
            issue: warning,
            severity: 'warning',
          });
        }
      }
    }

    // Check content exists
    if (!artifact.content_text && !artifact.content_ref) {
      errors.push({
        field: 'content',
        issue: 'Neither content_text nor content_ref is provided',
        severity: 'error',
      });
    }

    return {
      valid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Check if URL is a valid WeChat image URL.
   * WeChat image URLs typically start with https://mmbiz.qpic.cn/
   */
  private isWechatImageUrl(url: string): boolean {
    return url.startsWith('https://mmbiz.qpic.cn/');
  }
}
