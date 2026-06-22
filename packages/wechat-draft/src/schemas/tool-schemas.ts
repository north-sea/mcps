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
 * - alternate write adapters
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
    adapter_id: z.string(),
    capabilities: z.array(z.string()).optional(),
  })),
});

export type ListAccountsInput = z.infer<typeof ListAccountsInputSchema>;
export type ListAccountsOutput = z.infer<typeof ListAccountsOutputSchema>;

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
    details: z.record(z.unknown()).optional(),
  }).optional(),
  created_at: z.string(),
});

export type CreateDraftInput = z.infer<typeof CreateDraftInputSchema>;
export type CreateDraftOutput = z.infer<typeof CreateDraftOutputSchema>;

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
  };
  created_at: string;
  updated_at: string;
}
