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
        'Accept': 'application/json',
      };

      if (this.authToken) {
        headers['Authorization'] = `Bearer ${this.authToken}`;
      }

      const response = await fetch(`${this.baseUrl}/mcp`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: Date.now(),
          method: 'tools/call',
          params: {
            name: toolName,
            arguments: args,
          },
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

      // Check JSON-RPC error
      if ((result as any)?.error) {
        throw new Error(`JSON-RPC error: ${(result as any).error.message || JSON.stringify((result as any).error)}`);
      }

      // Extract content from JSON-RPC result
      const content = (result as any)?.result?.content;
      if (content && Array.isArray(content) && content[0]?.text) {
        return JSON.parse(content[0].text) as T;
      }

      return result as T;
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
      const result = await this.callTool<WorkflowArtifact | { error?: string; message?: string }>(
        'get_workflow_artifact_content',
        { artifact_id: artifactId }
      );

      // Check if result is an error response
      if (result && typeof result === 'object' && 'error' in result) {
        if ((result as any).error === 'not_found') {
          return null;
        }
        throw new Error((result as any).message || 'Unknown error from hermes-db');
      }

      return result as WorkflowArtifact || null;
    } catch (error) {
      // If artifact not found, return null instead of throwing
      if (error instanceof Error && (error.message.includes('not found') || error.message.includes('does not exist') || error.message.includes('不存在'))) {
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
        'upsert_wechat_article',
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
      const result = await this.callTool<{ pg?: string; redis?: string; embedding?: string }>(
        'health',
        {}
      );

      const isOk = result?.pg === 'ok' && result?.redis === 'ok';
      return { ok: isOk };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }
}
