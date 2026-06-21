/**
 * Hermes-db Client
 *
 * Provides read access to workflow_artifacts and write access to wechat_articles ledger.
 * MVP uses hermes-db MCP tools; production may use direct HTTP client.
 */

import { ErrorCode, createErrorResult, ErrorResult } from '../schemas/index.js';

// ============================================================================
// Types
// ============================================================================

export interface WorkflowArtifact {
  artifact_id: string;
  run_id: string;
  task_id?: string;
  topic_id?: string;
  account: string;
  stage: string;
  type: string;
  name: string;
  content_hash: string;
  content_size_bytes: number;
  content_preview?: string;
  content_text?: string;
  content_ref?: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WechatArticleLedger {
  account: string;
  run_id: string;
  status: string;
  draft_artifact_id: string;
  title: string;
  publication_idempotency_key: string;
  metadata: Record<string, unknown>;
  published_url?: string;
  created_at: string;
  updated_at: string;
}

export interface ArticleLedgerUpdate {
  account: string;
  run_id: string;
  status: 'drafted' | 'published' | 'failed';
  draft_artifact_id: string;
  title: string;
  publication_idempotency_key: string;
  metadata: Record<string, unknown>;
}

// ============================================================================
// HermesDbClient
// ============================================================================

export class HermesDbClient {
  private baseUrl: string;
  private timeoutMs: number;

  constructor(baseUrl: string, timeoutMs: number = 10000) {
    this.baseUrl = baseUrl;
    this.timeoutMs = timeoutMs;
  }

  /**
   * Get workflow artifact by artifact_id.
   * Returns artifact or null if not found.
   */
  async getArtifact(artifactId: string): Promise<WorkflowArtifact | null> {
    try {
      // TODO: Phase 2 - implement via hermes-db MCP or HTTP client
      // For now, return null (not found)
      return null;
    } catch (error) {
      throw new Error(
        `Failed to get artifact ${artifactId}: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  /**
   * Upsert wechat_articles ledger entry.
   * Returns success or throws error.
   */
  async upsertArticleLedger(update: ArticleLedgerUpdate): Promise<void> {
    try {
      // TODO: Phase 4 - implement via hermes-db MCP upsert_wechat_article
      // For MVP, we need to call the MCP tool via SDK or HTTP
      // Since we're in an MCP server, we can't directly call another MCP server's tool
      // Options:
      // 1. Use HTTP client to call hermes-db HTTP API (if exists)
      // 2. Use hermes-db MCP client (requires MCP client SDK)
      // 3. Direct database access (requires pg connection)
      //
      // For T017 MVP, we'll throw a descriptive error indicating the integration point
      // The actual implementation depends on the deployment architecture decision

      throw new Error(
        `Article ledger upsert requires hermes-db integration. ` +
        `Options: (1) HTTP API to hermes-db, (2) MCP client to hermes-db MCP, (3) Direct pg connection. ` +
        `Current update: account=${update.account}, run_id=${update.run_id}, status=${update.status}, ` +
        `draft_artifact_id=${update.draft_artifact_id}, media_id=${(update.metadata as any)?.wechat_media_id}`
      );
    } catch (error) {
      throw new Error(
        `Failed to upsert article ledger: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  /**
   * Health check - verify hermes-db is reachable.
   */
  async health(): Promise<{ ok: boolean; error?: string }> {
    try {
      // TODO: Phase 2 - implement via hermes-db MCP health tool
      // For now, return placeholder
      return { ok: false, error: 'Health check not yet implemented (Phase 2: T008)' };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }
}
