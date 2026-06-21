/**
 * Hermes-db Client
 *
 * Provides read access to workflow_artifacts and write access to wechat_articles ledger.
 * Connects to hermes-db MCP server via HTTP (FastAPI backend at nas.local:8765).
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
  private authToken?: string;

  constructor(baseUrl: string, timeoutMs: number = 10000, authToken?: string) {
    this.baseUrl = baseUrl;
    this.timeoutMs = timeoutMs;
    this.authToken = authToken;
  }

  /**
   * Call hermes-db MCP tool via HTTP POST.
   */
  private async callTool<T = any>(
    toolName: string,
    args: Record<string, any>
  ): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (this.authToken) {
        headers['Authorization'] = `Bearer ${this.authToken}`;
      }

      const response = await fetch(`${this.baseUrl}/mcp/tools/call`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          name: toolName,
          arguments: args,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new Error(
          `HTTP ${response.status}: ${response.statusText} - ${errorText}`
        );
      }

      const result = await response.json();

      // Check if result contains error
      if ((result as any)?.error) {
        throw new Error(`Tool error: ${(result as any).error.message || JSON.stringify((result as any).error)}`);
      }

      return (result as any)?.content?.[0]?.text ? JSON.parse((result as any).content[0].text) : result;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Hermes-db request timeout after ${this.timeoutMs}ms`);
      }

      throw error;
    }
  }

  /**
   * Get workflow artifact by artifact_id.
   * Returns artifact or null if not found.
   */
  async getArtifact(artifactId: string): Promise<WorkflowArtifact | null> {
    try {
      const result = await this.callTool<{ artifact: WorkflowArtifact | null }>(
        'mcp__hermes-db__get_workflow_artifact_content',
        { artifact_id: artifactId }
      );

      return result?.artifact || null;
    } catch (error) {
      // If artifact not found, return null instead of throwing
      if (error instanceof Error && error.message.includes('not found')) {
        return null;
      }

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
      await this.callTool(
        'mcp__hermes-db__upsert_wechat_article',
        {
          publication_idempotency_key: update.publication_idempotency_key,
          account: update.account,
          run_id: update.run_id,
          status: update.status,
          draft_artifact_id: update.draft_artifact_id,
          title: update.title,
          metadata: update.metadata,
        }
      );
    } catch (error) {
      // Log warning but don't throw - ledger update failure should not block draft creation
      console.warn(
        `[HermesDbClient] Failed to upsert article ledger: ${error instanceof Error ? error.message : 'Unknown error'}`,
        `Update: account=${update.account}, run_id=${update.run_id}, status=${update.status}`
      );
      // Rethrow so caller can decide whether to continue
      throw error;
    }
  }

  /**
   * Health check - verify hermes-db is reachable.
   */
  async health(): Promise<{ ok: boolean; error?: string }> {
    try {
      const result = await this.callTool<{ status?: string; ok?: boolean }>(
        'mcp__hermes-db__health',
        {}
      );

      const isOk = result?.ok === true || result?.status === 'ok' || result?.status === 'healthy';
      return { ok: isOk };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }
}
