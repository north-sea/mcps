/**
 * AssetSourceLoader
 *
 * Materializes image sources (local_path or remote_url) into controlled
 * file bytes, with size and format guards enforced per AssetUsage.
 *
 * - local_path: reads from MCP runtime filesystem
 * - remote_url: fetches over http(s) with size/type guards
 * - No base64 support in MVP
 *
 * Size limits:
 * - body_image: jpg/jpeg/png, max 1MB
 * - cover_image: jpg/jpeg only, max 64KB (WeChat thumb material requirement)
 */

import { readFile } from 'node:fs/promises';
import { AssetUsage, AssetSourceType } from '../schemas/tool-schemas.js';

// ============================================================================
// Constants
// ============================================================================

const SIZE_LIMIT_BODY_IMAGE = 1 * 1024 * 1024; // 1MB
const SIZE_LIMIT_COVER_IMAGE = 64 * 1024;      // 64KB

const MIME_WHITELIST_BODY_IMAGE = ['image/jpeg', 'image/jpg', 'image/png'];
const MIME_WHITELIST_COVER_IMAGE = ['image/jpeg', 'image/jpg'];

const EXTENSION_TO_MIME: Record<string, string> = {
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
};

// ============================================================================
// Types
// ============================================================================

export interface AssetSourceInput {
  usage: AssetUsage;
  source_type: AssetSourceType;
  source: string;
  filename?: string;
  mime_type?: string;
}

export interface LoadedAsset {
  bytes: Uint8Array;
  filename: string;
  mimeType: string;
  sizeBytes: number;
}

export class AssetSourceError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'AssetSourceError';
  }
}

// ============================================================================
// Loader
// ============================================================================

export class AssetSourceLoader {
  async load(input: AssetSourceInput): Promise<LoadedAsset> {
    const { usage, source_type, source, filename, mime_type } = input;

    let bytes: Uint8Array;
    let inferredFilename: string;
    let inferredMimeType: string;

    // Load bytes based on source_type
    if (source_type === 'local_path') {
      const result = await this.loadLocalPath(source, filename, mime_type);
      bytes = result.bytes;
      inferredFilename = result.filename;
      inferredMimeType = result.mimeType;
    } else if (source_type === 'remote_url') {
      const result = await this.loadRemoteUrl(source, filename, mime_type);
      bytes = result.bytes;
      inferredFilename = result.filename;
      inferredMimeType = result.mimeType;
    } else {
      throw new AssetSourceError(
        `Unsupported source_type: ${source_type}`,
        'ASSET_SOURCE_INVALID',
        { source_type }
      );
    }

    const sizeBytes = bytes.length;

    // Apply size and format guards per usage
    this.validateAssetConstraints(usage, sizeBytes, inferredMimeType);

    return {
      bytes,
      filename: inferredFilename,
      mimeType: inferredMimeType,
      sizeBytes,
    };
  }

  private async loadLocalPath(
    path: string,
    explicitFilename?: string,
    explicitMimeType?: string
  ): Promise<{ bytes: Uint8Array; filename: string; mimeType: string }> {
    try {
      const bytes = await readFile(path);
      const filename = explicitFilename || this.extractFilename(path);
      const mimeType = explicitMimeType || this.inferMimeFromFilename(filename);

      return {
        bytes: new Uint8Array(bytes),
        filename,
        mimeType,
      };
    } catch (error) {
      throw new AssetSourceError(
        `Failed to read local file: ${path}`,
        'ASSET_FILE_NOT_READABLE',
        { path, error: error instanceof Error ? error.message : String(error) }
      );
    }
  }

  private async loadRemoteUrl(
    url: string,
    explicitFilename?: string,
    explicitMimeType?: string
  ): Promise<{ bytes: Uint8Array; filename: string; mimeType: string }> {
    // Only allow http(s)
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      throw new AssetSourceError(
        'Remote URL must use http or https protocol',
        'ASSET_SOURCE_INVALID',
        { url }
      );
    }

    try {
      const response = await fetch(url);

      if (!response.ok) {
        throw new AssetSourceError(
          `Remote URL fetch failed: ${response.status} ${response.statusText}`,
          'ASSET_REMOTE_URL_FETCH_FAILED',
          { url, status: response.status, statusText: response.statusText }
        );
      }

      // Check Content-Length if available
      const contentLength = response.headers.get('content-length');
      if (contentLength) {
        const size = parseInt(contentLength, 10);
        // Use the larger limit as a pre-check; specific usage check happens later
        if (size > SIZE_LIMIT_BODY_IMAGE) {
          throw new AssetSourceError(
            `Remote image size ${size} bytes exceeds maximum limit`,
            'ASSET_SIZE_EXCEEDED',
            { url, size, limit: SIZE_LIMIT_BODY_IMAGE }
          );
        }
      }

      // Check Content-Type if available
      const contentType = response.headers.get('content-type');
      const mimeType = explicitMimeType || contentType || 'application/octet-stream';

      // Read body
      const arrayBuffer = await response.arrayBuffer();
      const bytes = new Uint8Array(arrayBuffer);

      // Extract filename from URL or use default
      const filename = explicitFilename || this.extractFilenameFromUrl(url) || 'image';

      return {
        bytes,
        filename,
        mimeType,
      };
    } catch (error) {
      if (error instanceof AssetSourceError) {
        throw error;
      }
      throw new AssetSourceError(
        `Failed to fetch remote URL: ${url}`,
        'ASSET_REMOTE_URL_FETCH_FAILED',
        { url, error: error instanceof Error ? error.message : String(error) }
      );
    }
  }

  private validateAssetConstraints(
    usage: AssetUsage,
    sizeBytes: number,
    mimeType: string
  ): void {
    const normalizedMime = mimeType.toLowerCase().split(';')[0].trim();

    if (usage === 'body_image') {
      // body_image: jpg/jpeg/png, max 1MB
      if (!MIME_WHITELIST_BODY_IMAGE.includes(normalizedMime)) {
        throw new AssetSourceError(
          `body_image requires jpg/jpeg/png, got: ${normalizedMime}`,
          'ASSET_FORMAT_UNSUPPORTED',
          { usage, mimeType: normalizedMime, allowed: MIME_WHITELIST_BODY_IMAGE }
        );
      }
      if (sizeBytes > SIZE_LIMIT_BODY_IMAGE) {
        throw new AssetSourceError(
          `body_image size ${sizeBytes} bytes exceeds 1MB limit`,
          'ASSET_SIZE_EXCEEDED',
          { usage, sizeBytes, limit: SIZE_LIMIT_BODY_IMAGE }
        );
      }
    } else if (usage === 'cover_image') {
      // cover_image: JPG only, max 64KB (WeChat thumb material requirement)
      if (!MIME_WHITELIST_COVER_IMAGE.includes(normalizedMime)) {
        throw new AssetSourceError(
          `cover_image requires jpg/jpeg (WeChat thumb material), got: ${normalizedMime}`,
          'ASSET_FORMAT_UNSUPPORTED',
          { usage, mimeType: normalizedMime, allowed: MIME_WHITELIST_COVER_IMAGE }
        );
      }
      if (sizeBytes > SIZE_LIMIT_COVER_IMAGE) {
        throw new AssetSourceError(
          `cover_image size ${sizeBytes} bytes exceeds 64KB limit (WeChat thumb material)`,
          'ASSET_SIZE_EXCEEDED',
          { usage, sizeBytes, limit: SIZE_LIMIT_COVER_IMAGE }
        );
      }
    }
  }

  private extractFilename(path: string): string {
    const parts = path.split('/');
    return parts[parts.length - 1] || 'unknown';
  }

  private extractFilenameFromUrl(url: string): string | null {
    try {
      const urlObj = new URL(url);
      const pathname = urlObj.pathname;
      const parts = pathname.split('/');
      const filename = parts[parts.length - 1];
      return filename || null;
    } catch {
      return null;
    }
  }

  private inferMimeFromFilename(filename: string): string {
    const lowerFilename = filename.toLowerCase();
    for (const [ext, mime] of Object.entries(EXTENSION_TO_MIME)) {
      if (lowerFilename.endsWith(ext)) {
        return mime;
      }
    }
    return 'application/octet-stream';
  }
}
