import {
  ErrorCode,
  createErrorResult,
  type ErrorResult,
} from '../schemas/index.js';

export function articleDocumentError(
  error: unknown,
  phase: string
): ErrorResult {
  const message = error instanceof Error ? error.message : 'Unknown article_document error';
  const context = mapArticleDocumentError(message, phase);
  return createErrorResult(ErrorCode.INVALID_INPUT, context.message, context.details, {
    next_action: context.next_action,
    remediation_hint: context.remediation_hint,
    retryable: false,
    current_phase: phase,
  });
}

function mapArticleDocumentError(
  message: string,
  phase: string
): {
  message: string;
  details?: Record<string, unknown>;
  next_action: string;
  remediation_hint: string;
} {
  if (message.startsWith('Missing prepared image asset')) {
    return {
      message,
      next_action: 'prepare_body_image_assets',
      remediation_hint: 'Upload or prepare one body image asset for each Markdown image, then retry import.',
    };
  }

  if (message.includes('cover.thumb_media_id is required')) {
    return {
      message: 'article_document cover.thumb_media_id is required for publish-ready artifact build',
      next_action: 'upload_cover_image',
      remediation_hint: 'Call wechat_upload_asset with usage=cover_image, then set cover.thumb_media_id before building.',
    };
  }

  if (message.includes('must use a WeChat image URL') || message.includes('Image asset is not ready')) {
    return {
      message,
      next_action: 'upload_body_images',
      remediation_hint: 'Call wechat_upload_asset with usage=body_image for each image and set assets.*.wechat_url.',
    };
  }

  if (message.includes('Unexpected token') || message.includes('JSON')) {
    return {
      message: 'Invalid article_document JSON string',
      next_action: 'fix_article_document_json',
      remediation_hint: 'Pass a valid article_document object, or a JSON string created with JSON.stringify(article).',
    };
  }

  if (message.includes('Invalid article_document') || message.includes('Unsupported article_document')) {
    return {
      message,
      next_action: 'fix_article_document',
      remediation_hint: 'Fix the reported article_document field or unsupported node/mark before retrying.',
    };
  }

  return {
    message,
    details: { phase },
    next_action: 'inspect_article_document_error',
    remediation_hint: 'Inspect the article_document input and retry with a valid canonical document.',
  };
}
