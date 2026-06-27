/**
 * MCP Tool Schemas for WeChat Draft Service
 *
 * MVP scope:
 * - wechat_list_accounts: read-only, list enabled accounts
 * - wechat_validate_publish_artifact: read-only, validate artifact before creating draft
 * - wechat_create_draft: side-effecting, create WeChat draft from hermes-db artifact
 * - wechat_get_draft_status: read-only, query draft job status
 * - wechat_upload_asset: side-effecting, upload image asset to WeChat (body image or cover thumbnail)
 *
 * Out of scope for MVP:
 * - publish/mass-send/update/delete tools
 * - alternate write backends
 * - preview tools
 */

import { z } from 'zod';

// ============================================================================
// Common Schemas
// ============================================================================

export const AccountIdSchema = z.string()
  .min(1)
  .describe('WeChat account identifier, e.g. "yueliang"');

export const ArtifactIdSchema = z.string()
  .min(1)
  .describe('Hermes-db workflow artifact ID');

export const JobIdSchema = z.string()
  .regex(/^job_[a-zA-Z0-9_-]+$/)
  .describe('Draft job identifier');

// ============================================================================
// Tool: wechat_list_accounts
// ============================================================================

export const AssetUsageConstraintsSchema = z.object({
  max_bytes: z.number().int().positive(),
  mime_types: z.array(z.string()).min(1),
  source_types: z.array(z.enum(['local_path', 'remote_url'])).min(1),
  wechat_api: z.string(),
  media_type: z.string().optional(),
});

export const AccountConstraintsSchema = z.object({
  assets: z.object({
    body_image: AssetUsageConstraintsSchema,
    cover_image: AssetUsageConstraintsSchema,
    local_path: z.object({
      enabled: z.boolean(),
      accepted_path_prefixes: z.array(z.string()),
    }),
    remote_url: z.object({
      enabled: z.boolean(),
      protocols: z.array(z.enum(['http', 'https'])),
    }),
  }),
});

export const ListAccountsInputSchema = z.object({
  include_disabled: z.boolean()
    .optional()
    .default(false)
    .describe('Include disabled accounts in the result'),
});

export const ListAccountsOutputSchema = z.object({
  accounts: z.array(z.object({
    account_id: z.string(),
    display_name: z.string(),
    enabled: z.boolean(),
    capabilities: z.array(z.string()).optional(),
    constraints: AccountConstraintsSchema.optional(),
  })),
});

export type ListAccountsInput = z.infer<typeof ListAccountsInputSchema>;
export type ListAccountsOutput = z.infer<typeof ListAccountsOutputSchema>;
export type AccountConstraints = z.infer<typeof AccountConstraintsSchema>;

// ============================================================================
// Tool: wechat_validate_publish_artifact
// ============================================================================

export const ValidateArtifactInputSchema = z.object({
  account: AccountIdSchema,
  artifact_id: ArtifactIdSchema,
});

export const ValidateArtifactOutputSchema = z.object({
  valid: z.boolean(),
  artifact_id: z.string(),
  account: z.string(),
  validation_errors: z.array(z.object({
    field: z.string(),
    issue: z.string(),
    severity: z.enum(['error', 'warning']),
  })),
  artifact_summary: z.object({
    title: z.string().optional(),
    stage: z.string().optional(),
    type: z.string().optional(),
    publish_ready: z.boolean().optional(),
    wechat_asset_ready: z.boolean().optional(),
  }).optional(),
});

export type ValidateArtifactInput = z.infer<typeof ValidateArtifactInputSchema>;
export type ValidateArtifactOutput = z.infer<typeof ValidateArtifactOutputSchema>;

// ============================================================================
// Tool: wechat_create_draft
// ============================================================================

export const CreateDraftInputSchema = z.object({
  account: AccountIdSchema,
  artifact_id: ArtifactIdSchema,
  idempotency_key: z.string()
    .optional()
    .describe('Optional idempotency key; defaults to account+artifact_id hash'),
});

export const CreateDraftOutputSchema = z.object({
  job_id: JobIdSchema,
  status: z.enum([
    'queued',
    'artifact_validation',
    'adapter_check',
    'payload_build',
    'draft_creating',
    'ledger_update',
    'saved',
    'failed',
    'invalid_artifact',
    'needs_operator_action',
  ]),
  account: z.string(),
  artifact_id: z.string(),
  title: z.string().optional(),
  media_id: z.string().optional(),
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.string(), z.unknown()).optional(),
    next_action: z.string().optional(),
    remediation_hint: z.string().optional(),
    retryable: z.boolean().optional(),
    current_phase: z.string().optional(),
  }).optional(),
  created_at: z.string(),
});

export type CreateDraftInput = z.infer<typeof CreateDraftInputSchema>;
export type CreateDraftOutput = z.infer<typeof CreateDraftOutputSchema>;

// ============================================================================
// Tool: wechat_list_drafts
// ============================================================================

export const ListDraftsInputSchema = z.object({
  account: AccountIdSchema,
  offset: z.number().int().min(0).optional().default(0),
  count: z.number().int().min(1).max(50).optional().default(20),
  include_content: z.boolean()
    .optional()
    .default(false)
    .describe('Return full draft article HTML content. Defaults to false to keep MCP responses bounded.'),
});

export const DraftListItemSchema = z.object({
  media_id: z.string(),
  update_time: z.number().optional(),
  title: z.string().optional(),
  author: z.string().optional(),
  digest: z.string().optional(),
  thumb_media_id: z.string().optional(),
  content_source_url: z.string().optional(),
  content_preview: z.string().optional(),
  content: z.string().optional(),
});

export const ListDraftsOutputSchema = z.object({
  account: z.string(),
  total_count: z.number().int().nonnegative().optional(),
  item_count: z.number().int().nonnegative().optional(),
  offset: z.number().int().nonnegative(),
  count: z.number().int().positive(),
  include_content: z.boolean(),
  items: z.array(DraftListItemSchema),
});

export type ListDraftsInput = z.infer<typeof ListDraftsInputSchema>;
export type ListDraftsOutput = z.infer<typeof ListDraftsOutputSchema>;

// ============================================================================
// Tool: wechat_get_draft_status
// ============================================================================

export const GetDraftStatusInputSchema = z.object({
  job_id: JobIdSchema.optional(),
  artifact_id: ArtifactIdSchema.optional(),
}).refine(
  (data) => data.job_id || data.artifact_id,
  { message: 'Either job_id or artifact_id must be provided' }
);

export const GetDraftStatusOutputSchema = z.object({
  found: z.boolean(),
  job_id: JobIdSchema.optional(),
  status: z.string().optional(),
  account: z.string().optional(),
  artifact_id: z.string().optional(),
  title: z.string().optional(),
  media_id: z.string().optional(),
  error: z.object({
    code: z.string(),
    message: z.string(),
  }).optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});

export type GetDraftStatusInput = z.infer<typeof GetDraftStatusInputSchema>;
export type GetDraftStatusOutput = z.infer<typeof GetDraftStatusOutputSchema>;

// ============================================================================
// Tool: wechat_upload_asset
// ============================================================================

/**
 * Image usage. Drives which WeChat material API the adapter calls and which
 * core reference field the result carries:
 * - body_image  -> /cgi-bin/media/uploadimg -> wechat_url
 * - cover_image -> /cgi-bin/material/add_material?type=thumb -> thumb_media_id
 */
export const AssetUsageSchema = z.enum(['body_image', 'cover_image'])
  .describe('Image usage: body_image returns an inline content URL, cover_image returns a permanent thumb media_id');

/**
 * Image source kind. base64 is intentionally excluded from MVP.
 */
export const AssetSourceTypeSchema = z.enum(['local_path', 'remote_url'])
  .describe('Image source kind: local_path reads a file from the MCP runtime, remote_url fetches over http(s)');

export const UploadAssetInputSchema = z.object({
  account: AccountIdSchema,
  usage: AssetUsageSchema,
  source_type: AssetSourceTypeSchema,
  source: z.string()
    .min(1)
    .describe('Local file path (source_type=local_path) or http(s) image URL (source_type=remote_url)'),
  filename: z.string()
    .min(1)
    .optional()
    .describe('Optional original filename, used for mime/extension inference'),
  mime_type: z.string()
    .min(1)
    .optional()
    .describe('Optional explicit mime type, e.g. "image/jpeg"'),
  preflight: z.boolean()
    .optional()
    .describe('Run preflight before adapter upload and skip upload if the asset is invalid'),
});

export const UploadAssetOutputSchema = z.object({
  account: z.string(),
  usage: AssetUsageSchema,
  source_type: AssetSourceTypeSchema,
  filename: z.string().optional(),
  mime_type: z.string().optional(),
  size_bytes: z.number().int().nonnegative().optional(),
  // Exactly one of the following is populated, selected by `usage`:
  wechat_url: z.string().optional()
    .describe('Inline content image URL (usage=body_image)'),
  thumb_media_id: z.string().optional()
    .describe('Permanent thumbnail material id (usage=cover_image)'),
  created_at: z.string(),
});

export type UploadAssetInput = z.infer<typeof UploadAssetInputSchema>;
export type UploadAssetOutput = z.infer<typeof UploadAssetOutputSchema>;
export type AssetUsage = z.infer<typeof AssetUsageSchema>;
export type AssetSourceType = z.infer<typeof AssetSourceTypeSchema>;

export const AssetPreflightInputSchema = z.object({
  usage: AssetUsageSchema,
  source_type: AssetSourceTypeSchema,
  source: z.string().min(1),
  filename: z.string().min(1).optional(),
  mime_type: z.string().min(1).optional(),
});

export const AssetPreflightIssueSchema = z.object({
  code: z.string(),
  message: z.string(),
  severity: z.enum(['error', 'warning']),
});

export const AssetTransformRecommendationSchema = z.object({
  action: z.enum(['none', 'compress', 'convert_format', 'use_accepted_path_or_remote_url', 'replace_asset']),
  reason: z.string(),
  target_max_bytes: z.number().int().positive().optional(),
  target_mime_types: z.array(z.string()).optional(),
  supported_in_mvp: z.boolean(),
});

export const AssetPreflightOutputSchema = z.object({
  valid: z.boolean(),
  upload_ready: z.boolean(),
  usage: AssetUsageSchema,
  source_type: AssetSourceTypeSchema,
  filename: z.string().optional(),
  mime_type: z.string().optional(),
  size_bytes: z.number().int().nonnegative().optional(),
  constraints: AssetUsageConstraintsSchema,
  source_diagnostics: z.object({
    readable: z.boolean().optional(),
    fetch_ok: z.boolean().optional(),
    status: z.number().int().optional(),
    status_text: z.string().optional(),
    accepted_path_prefixes: z.array(z.string()).optional(),
    protocols: z.array(z.enum(['http', 'https'])).optional(),
  }),
  issues: z.array(AssetPreflightIssueSchema),
  recommendations: z.array(AssetTransformRecommendationSchema),
});

export type AssetPreflightInput = z.infer<typeof AssetPreflightInputSchema>;
export type AssetPreflightOutput = z.infer<typeof AssetPreflightOutputSchema>;

// ============================================================================
// Tools: article_document import / validate / render / build
// ============================================================================

export const ArticleDocumentAssetSchema = z.object({
  asset_ref: z.string().min(1),
  wechat_url: z.string().optional(),
  alt: z.string().optional(),
  width: z.number().int().positive().optional(),
  height: z.number().int().positive().optional(),
  ready: z.boolean().optional(),
});

export const ArticleDocumentCoverSchema = z.object({
  asset_ref: z.string().min(1).optional(),
  thumb_media_id: z.string().min(1).optional(),
  alt: z.string().optional(),
});

export const ArticleDocumentSchema = z.object({
  schema_version: z.string(),
  title: z.string(),
  digest: z.string().optional(),
  author: z.string().optional(),
  style_profile_id: z.string().optional(),
  content_source_url: z.string().optional(),
  doc: z.unknown(),
  assets: z.record(z.string(), ArticleDocumentAssetSchema).optional(),
  cover: ArticleDocumentCoverSchema.optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  source_markdown_artifact_id: z.string().optional(),
  parent_artifact_id: z.string().optional(),
});

export const ArticleDocumentInputSchema = z.union([
  ArticleDocumentSchema,
  z.string().min(1),
]).describe('article_document object or JSON string');

export const ImportArticleMarkdownInputSchema = z.object({
  markdown: z.string().min(1),
  title: z.string().optional(),
  digest: z.string().optional(),
  author: z.string().optional(),
  style_profile_id: z.string().optional(),
  content_source_url: z.string().optional(),
  cover: ArticleDocumentCoverSchema.optional(),
  body_images: z.array(ArticleDocumentAssetSchema).optional(),
  source_markdown_artifact_id: z.string().optional(),
  parent_artifact_id: z.string().optional(),
  return_content_text: z.boolean().optional().default(false)
    .describe('Also return JSON.stringify(article_document) for hermes content_text persistence'),
});

export const ImportArticleMarkdownOutputSchema = z.object({
  article: ArticleDocumentSchema,
  content_text: z.string().optional(),
  validation: z.object({
    valid: z.boolean(),
    errors: z.array(z.object({
      field: z.string(),
      issue: z.string(),
    })),
  }),
});

export const ValidateArticleDocumentInputSchema = z.object({
  article: ArticleDocumentInputSchema,
  return_normalized: z.boolean().optional().default(false),
});

export const ValidateArticleDocumentOutputSchema = z.object({
  valid: z.boolean(),
  schema_version: z.string().optional(),
  errors: z.array(z.object({
    field: z.string(),
    issue: z.string(),
  })),
  article: ArticleDocumentSchema.optional(),
});

export const RenderArticleDocumentInputSchema = z.object({
  article: ArticleDocumentInputSchema,
  style_profile_id: z.string().optional(),
  include_cover_image: z.boolean().optional().default(false),
  output_format: z.enum(['html', 'markdown']).optional().default('html'),
});

export const RenderArticleDocumentOutputSchema = z.object({
  output_format: z.enum(['html', 'markdown']),
  html: z.string().optional(),
  markdown: z.string().optional(),
  content_hash: z.string(),
  content_size_bytes: z.number().int().nonnegative(),
  preview_text: z.string(),
  consumed_body_images: z.array(z.object({
    asset_ref: z.string(),
    wechat_url: z.string(),
  })),
  warnings: z.array(z.string()),
});

export const BuildPublishReadyArtifactInputSchema = z.object({
  article: ArticleDocumentInputSchema,
  artifact_id: z.string().min(1),
  run_id: z.string().min(1),
  account: z.string().min(1),
  task_id: z.string().optional(),
  topic_id: z.string().optional(),
  source_artifact_id: z.string().optional(),
  style_profile_id: z.string().optional(),
});

export const BuildPublishReadyArtifactOutputSchema = z.object({
  upsert_payload: z.object({
    artifact_id: z.string(),
    run_id: z.string(),
    task_id: z.string().optional(),
    topic_id: z.string().optional(),
    account: z.string(),
    stage: z.literal('publish_ready'),
    type: z.literal('wechat_api_article'),
    name: z.string(),
    content_hash: z.string(),
    content_size_bytes: z.number().int().nonnegative(),
    content_preview: z.string().optional(),
    content_text: z.string(),
    metadata: z.record(z.string(), z.unknown()),
  }),
});

export type ArticleDocumentInput = z.infer<typeof ArticleDocumentInputSchema>;
export type ImportArticleMarkdownInput = z.infer<typeof ImportArticleMarkdownInputSchema>;
export type ImportArticleMarkdownOutput = z.infer<typeof ImportArticleMarkdownOutputSchema>;
export type ValidateArticleDocumentInput = z.infer<typeof ValidateArticleDocumentInputSchema>;
export type ValidateArticleDocumentOutput = z.infer<typeof ValidateArticleDocumentOutputSchema>;
export type RenderArticleDocumentInputTool = z.infer<typeof RenderArticleDocumentInputSchema>;
export type RenderArticleDocumentOutputTool = z.infer<typeof RenderArticleDocumentOutputSchema>;
export type BuildPublishReadyArtifactInput = z.infer<typeof BuildPublishReadyArtifactInputSchema>;
export type BuildPublishReadyArtifactOutput = z.infer<typeof BuildPublishReadyArtifactOutputSchema>;

export const FacadePhaseSchema = z.object({
  phase: z.enum([
    'input_validation',
    'asset_preflight',
    'artifact_build',
    'workflow_run_upsert',
    'artifact_upsert',
    'publish_validation',
    'draft_create',
  ]),
  status: z.enum(['skipped', 'running', 'succeeded', 'failed']),
  artifact_id: z.string().optional(),
  message: z.string().optional(),
});

const FacadeCommonInputSchema = z.object({
  account: AccountIdSchema,
  idempotency_key: z.string().optional(),
});

const PublishReadyArtifactFacadeInputSchema = FacadeCommonInputSchema.extend({
  source_type: z.literal('publish_ready_artifact'),
  artifact_id: ArtifactIdSchema,
});

const ArticleDocumentFacadeInputSchema = FacadeCommonInputSchema.extend({
  source_type: z.literal('article_document'),
  article: ArticleDocumentInputSchema,
  run_id: z.string().min(1),
  publish_artifact_id: ArtifactIdSchema,
  task_id: z.string().optional(),
  topic_id: z.string().optional(),
  source_artifact_id: z.string().optional(),
  style_profile_id: z.string().optional(),
});

export const CreateDraftFacadeInputSchema = z.discriminatedUnion('source_type', [
  PublishReadyArtifactFacadeInputSchema,
  ArticleDocumentFacadeInputSchema,
]);

export const CreateDraftFacadeOutputSchema = z.object({
  account: z.string(),
  source_type: z.enum(['publish_ready_artifact', 'article_document']),
  idempotency_key: z.string(),
  publish_artifact_id: z.string(),
  current_phase: z.string(),
  completed_phases: z.array(z.string()),
  phase_trace: z.array(FacadePhaseSchema),
  validation_summary: ValidateArtifactOutputSchema.optional(),
  upsert_outcome: z.record(z.string(), z.unknown()).optional(),
  draft: CreateDraftOutputSchema.optional(),
});

export type FacadePhase = z.infer<typeof FacadePhaseSchema>;
export type CreateDraftFacadeInput = z.infer<typeof CreateDraftFacadeInputSchema>;
export type CreateDraftFacadeOutput = z.infer<typeof CreateDraftFacadeOutputSchema>;

// ============================================================================
// Result Types (Internal)
// ============================================================================

export type DraftJobStatus =
  | 'queued'
  | 'artifact_validation'
  | 'adapter_check'
  | 'payload_build'
  | 'draft_creating'
  | 'ledger_update'
  | 'saved'
  | 'failed'
  | 'invalid_artifact'
  | 'needs_operator_action';

export interface DraftJob {
  job_id: string;
  status: DraftJobStatus;
  account: string;
  artifact_id: string;
  title?: string;
  idempotency_key: string;
  media_id?: string;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    next_action?: string;
    remediation_hint?: string;
    retryable?: boolean;
    current_phase?: string;
  };
  created_at: string;
  updated_at: string;
}
