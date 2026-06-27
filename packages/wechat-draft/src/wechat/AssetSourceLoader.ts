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

import { readFile, realpath } from 'node:fs/promises';
import { basename, isAbsolute, relative, resolve, sep } from 'node:path';
import {
  AssetUsage,
  type AssetPreflightOutput,
  AssetSourceType,
} from '../schemas/tool-schemas.js';

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

export interface AssetSourceLoaderConfig {
  assetRoot?: string;
}

export interface AssetUsageConstraints {
  max_bytes: number;
  mime_types: string[];
  source_types: AssetSourceType[];
  wechat_api: string;
  media_type?: string;
}

export interface AssetSourceConstraints {
  assets: {
    body_image: AssetUsageConstraints;
    cover_image: AssetUsageConstraints;
    local_path: {
      enabled: boolean;
      accepted_path_prefixes: string[];
    };
    remote_url: {
      enabled: boolean;
      protocols: Array<'http' | 'https'>;
    };
  };
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
  private readonly assetRoot?: string;

  constructor(config: AssetSourceLoaderConfig = {}) {
    this.assetRoot =
      config.assetRoot ||
      process.env.WECHAT_DRAFT_ASSET_ROOT ||
      process.env.ASSET_ROOT ||
      undefined;
  }

  getConstraints(): AssetSourceConstraints {
    return getAssetSourceConstraints(this.assetRoot);
  }

  async preflight(input: AssetSourceInput): Promise<AssetPreflightOutput> {
    const constraints = getAssetUsageConstraints(input.usage);
    try {
      const loaded = await this.load(input);
      return this.toPreflightResult(input, constraints, {
        filename: loaded.filename,
        mimeType: loaded.mimeType,
        sizeBytes: loaded.sizeBytes,
      });
    } catch (error) {
      if (error instanceof AssetSourceError) {
        return this.toPreflightErrorResult(input, constraints, error);
      }
      return this.toPreflightErrorResult(
        input,
        constraints,
        new AssetSourceError(
          'Asset preflight failed',
          'ASSET_SOURCE_INVALID',
          { error: error instanceof Error ? error.message : String(error) }
        )
      );
    }
  }

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
      const safePath = await this.resolveLocalPath(path);
      const bytes = await readFile(safePath);
      const filename = explicitFilename || this.extractFilename(safePath);
      const mimeType = explicitMimeType || this.inferMimeFromFilename(filename);

      return {
        bytes: new Uint8Array(bytes),
        filename,
        mimeType,
      };
    } catch (error) {
      if (error instanceof AssetSourceError) {
        throw error;
      }

      throw new AssetSourceError(
        `Failed to read local file: ${path}`,
        'ASSET_FILE_NOT_READABLE',
        { path, error: error instanceof Error ? error.message : String(error) }
      );
    }
  }

  private async resolveLocalPath(path: string): Promise<string> {
    if (!this.assetRoot) {
      throw new AssetSourceError(
        'local_path requires WECHAT_DRAFT_ASSET_ROOT or ASSET_ROOT',
        'ASSET_SOURCE_INVALID',
        { source_type: 'local_path' }
      );
    }

    const rootPath = await realpath(this.assetRoot);
    const candidatePath = isAbsolute(path)
      ? resolve(path)
      : resolve(rootPath, path);
    const realCandidatePath = await realpath(candidatePath);

    if (!isPathInside(rootPath, realCandidatePath)) {
      throw new AssetSourceError(
        'local_path must resolve under ASSET_ROOT',
        'ASSET_SOURCE_INVALID',
        { source_type: 'local_path' }
      );
    }

    return realCandidatePath;
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
      const constraints = WECHAT_ASSET_USAGE_CONSTRAINTS.body_image;
      if (!constraints.mime_types.includes(normalizedMime)) {
        throw new AssetSourceError(
          `body_image requires jpg/jpeg/png, got: ${normalizedMime}`,
          'ASSET_FORMAT_UNSUPPORTED',
          { usage, mimeType: normalizedMime, allowed: constraints.mime_types }
        );
      }
      if (sizeBytes > constraints.max_bytes) {
        throw new AssetSourceError(
          `body_image size ${sizeBytes} bytes exceeds 1MB limit`,
          'ASSET_SIZE_EXCEEDED',
          { usage, sizeBytes, limit: constraints.max_bytes }
        );
      }
    } else if (usage === 'cover_image') {
      // cover_image: JPG only, max 64KB (WeChat thumb material requirement)
      const constraints = WECHAT_ASSET_USAGE_CONSTRAINTS.cover_image;
      if (!constraints.mime_types.includes(normalizedMime)) {
        throw new AssetSourceError(
          `cover_image requires jpg/jpeg (WeChat thumb material), got: ${normalizedMime}`,
          'ASSET_FORMAT_UNSUPPORTED',
          { usage, mimeType: normalizedMime, allowed: constraints.mime_types }
        );
      }
      if (sizeBytes > constraints.max_bytes) {
        throw new AssetSourceError(
          `cover_image size ${sizeBytes} bytes exceeds 64KB limit (WeChat thumb material)`,
          'ASSET_SIZE_EXCEEDED',
          { usage, sizeBytes, limit: constraints.max_bytes }
        );
      }
    }
  }

  private toPreflightResult(
    input: AssetSourceInput,
    constraints: AssetUsageConstraints,
    detected: { filename: string; mimeType: string; sizeBytes: number }
  ): AssetPreflightOutput {
    const issues = validateDetectedAsset(input.usage, detected.sizeBytes, detected.mimeType);
    return {
      valid: issues.length === 0,
      upload_ready: issues.length === 0,
      usage: input.usage,
      source_type: input.source_type,
      filename: detected.filename,
      mime_type: normalizeMime(detected.mimeType),
      size_bytes: detected.sizeBytes,
      constraints,
      source_diagnostics: this.sourceDiagnostics(input, true),
      issues,
      recommendations: recommendationFor(input.usage, issues, constraints),
    };
  }

  private toPreflightErrorResult(
    input: AssetSourceInput,
    constraints: AssetUsageConstraints,
    error: AssetSourceError
  ): AssetPreflightOutput {
    const detectedSize = numberDetail(error.details, 'sizeBytes') ?? numberDetail(error.details, 'size');
    const detectedMime = stringDetail(error.details, 'mimeType');
    const issues = [
      {
        code: error.code,
        message: error.message,
        severity: 'error' as const,
      },
    ];

    return {
      valid: false,
      upload_ready: false,
      usage: input.usage,
      source_type: input.source_type,
      filename: input.filename,
      mime_type: detectedMime ? normalizeMime(detectedMime) : input.mime_type,
      size_bytes: detectedSize,
      constraints,
      source_diagnostics: this.sourceDiagnostics(input, false, error),
      issues,
      recommendations: recommendationFor(input.usage, issues, constraints),
    };
  }

  private sourceDiagnostics(
    input: AssetSourceInput,
    ok: boolean,
    error?: AssetSourceError
  ): AssetPreflightOutput['source_diagnostics'] {
    if (input.source_type === 'local_path') {
      return {
        readable: ok,
        accepted_path_prefixes: this.assetRoot ? [this.assetRoot] : [],
      };
    }

    return {
      fetch_ok: ok,
      status: numberDetail(error?.details, 'status'),
      status_text: stringDetail(error?.details, 'statusText'),
      protocols: ['http', 'https'],
    };
  }

  private extractFilename(path: string): string {
    return basename(path) || 'unknown';
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

export function getAssetUsageConstraints(usage: AssetUsage): AssetUsageConstraints {
  const constraints = WECHAT_ASSET_USAGE_CONSTRAINTS[usage];
  return {
    ...constraints,
    mime_types: [...constraints.mime_types],
    source_types: [...constraints.source_types],
  };
}

const ASSET_SOURCE_TYPES: AssetSourceType[] = ['local_path', 'remote_url'];

const WECHAT_ASSET_USAGE_CONSTRAINTS: Record<AssetUsage, AssetUsageConstraints> = {
  body_image: {
    max_bytes: SIZE_LIMIT_BODY_IMAGE,
    mime_types: MIME_WHITELIST_BODY_IMAGE,
    source_types: ASSET_SOURCE_TYPES,
    wechat_api: '/cgi-bin/media/uploadimg',
  },
  cover_image: {
    max_bytes: SIZE_LIMIT_COVER_IMAGE,
    mime_types: MIME_WHITELIST_COVER_IMAGE,
    source_types: ASSET_SOURCE_TYPES,
    wechat_api: '/cgi-bin/material/add_material?type=thumb',
    media_type: 'thumb',
  },
};

export function getAssetSourceConstraints(assetRoot?: string): AssetSourceConstraints {
  return {
    assets: {
      body_image: {
        ...WECHAT_ASSET_USAGE_CONSTRAINTS.body_image,
        mime_types: [...WECHAT_ASSET_USAGE_CONSTRAINTS.body_image.mime_types],
        source_types: [...WECHAT_ASSET_USAGE_CONSTRAINTS.body_image.source_types],
      },
      cover_image: {
        ...WECHAT_ASSET_USAGE_CONSTRAINTS.cover_image,
        mime_types: [...WECHAT_ASSET_USAGE_CONSTRAINTS.cover_image.mime_types],
        source_types: [...WECHAT_ASSET_USAGE_CONSTRAINTS.cover_image.source_types],
      },
      local_path: {
        enabled: Boolean(assetRoot),
        accepted_path_prefixes: assetRoot ? [assetRoot] : [],
      },
      remote_url: {
        enabled: true,
        protocols: ['http', 'https'],
      },
    },
  };
}

function validateDetectedAsset(
  usage: AssetUsage,
  sizeBytes: number,
  mimeType: string
): AssetPreflightOutput['issues'] {
  const constraints = getAssetUsageConstraints(usage);
  const normalizedMime = normalizeMime(mimeType);
  const issues: AssetPreflightOutput['issues'] = [];

  if (!constraints.mime_types.includes(normalizedMime)) {
    issues.push({
      code: 'ASSET_FORMAT_UNSUPPORTED',
      message: `${usage} requires ${constraints.mime_types.join(', ')}, got: ${normalizedMime}`,
      severity: 'error',
    });
  }

  if (sizeBytes > constraints.max_bytes) {
    issues.push({
      code: 'ASSET_SIZE_EXCEEDED',
      message: `${usage} size ${sizeBytes} bytes exceeds ${constraints.max_bytes} byte limit`,
      severity: 'error',
    });
  }

  return issues;
}

function recommendationFor(
  usage: AssetUsage,
  issues: AssetPreflightOutput['issues'],
  constraints: AssetUsageConstraints
): AssetPreflightOutput['recommendations'] {
  if (issues.length === 0) {
    return [
      {
        action: 'none',
        reason: 'Asset already satisfies current WeChat constraints.',
        supported_in_mvp: true,
      },
    ];
  }

  return issues.map((issue) => {
    if (issue.code === 'ASSET_SIZE_EXCEEDED') {
      return {
        action: 'compress' as const,
        reason: `${usage} is too large. Compress or resize externally, then retry preflight/upload.`,
        target_max_bytes: constraints.max_bytes,
        target_mime_types: constraints.mime_types,
        supported_in_mvp: false,
      };
    }

    if (issue.code === 'ASSET_FORMAT_UNSUPPORTED') {
      return {
        action: 'convert_format' as const,
        reason: `${usage} uses an unsupported MIME type. Convert to one of the allowed formats.`,
        target_mime_types: constraints.mime_types,
        supported_in_mvp: false,
      };
    }

    if (issue.code === 'ASSET_SOURCE_INVALID' || issue.code === 'ASSET_FILE_NOT_READABLE') {
      return {
        action: 'use_accepted_path_or_remote_url' as const,
        reason: 'Use a local path under the accepted asset root, or provide a reachable remote_url.',
        supported_in_mvp: true,
      };
    }

    return {
      action: 'replace_asset' as const,
      reason: 'Replace the asset or fix the source before retrying.',
      supported_in_mvp: true,
    };
  });
}

function normalizeMime(value: string): string {
  return value.toLowerCase().split(';')[0].trim();
}

function numberDetail(details: Record<string, unknown> | undefined, key: string): number | undefined {
  const value = details?.[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function stringDetail(details: Record<string, unknown> | undefined, key: string): string | undefined {
  const value = details?.[key];
  return typeof value === 'string' ? value : undefined;
}

function isPathInside(rootPath: string, candidatePath: string): boolean {
  const relativePath = relative(rootPath, candidatePath);
  return (
    relativePath === '' ||
    (!relativePath.startsWith('..') && !isAbsolute(relativePath) && !relativePath.startsWith(sep))
  );
}
