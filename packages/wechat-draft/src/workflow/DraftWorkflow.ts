/**
 * DraftWorkflow
 *
 * Orchestrates draft creation workflow:
 * queued → artifact_validation → adapter_check → payload_build →
 * draft_creating → ledger_update → saved/failed/invalid_artifact/needs_operator_action
 */

import { WorkflowArtifact, HermesDbClient } from '../hermes/HermesDbClient.js';
import { ArtifactValidator } from '../hermes/ArtifactValidator.js';
import { DraftPayloadBuilder } from '../wechat/DraftPayloadBuilder.js';
import {
  WechatAdapterClient,
  AdapterUnreachableError,
  AdapterAuthError,
  AdapterTimeoutError,
  AdapterTokenError,
  AdapterWeChatApiError,
} from '../wechat/WechatAdapterClient.js';
import { JobStore } from '../store/JobStore.js';
import { DraftJob, DraftJobStatus } from '../schemas/tool-schemas.js';
import { EcsWechatAdapterConfig } from '../config/types.js';
import { ErrorCode } from '../schemas/result-types.js';

export interface DraftWorkflowContext {
  account: string;
  artifactId: string;
  idempotencyKey: string;
  hermesDbClient: HermesDbClient;
  adapterConfig: EcsWechatAdapterConfig;
  jobStore: JobStore;
}

export class DraftWorkflow {
  private validator: ArtifactValidator;
  private payloadBuilder: DraftPayloadBuilder;

  constructor() {
    this.validator = new ArtifactValidator();
    this.payloadBuilder = new DraftPayloadBuilder();
  }

  /**
   * Execute draft creation workflow.
   * Returns final DraftJob with status saved/failed/invalid_artifact/needs_operator_action.
   */
  async execute(ctx: DraftWorkflowContext): Promise<DraftJob> {
    const jobId = this.generateJobId();
    let job: DraftJob = {
      job_id: jobId,
      status: 'queued',
      account: ctx.account,
      artifact_id: ctx.artifactId,
      idempotency_key: ctx.idempotencyKey,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    try {
      // Step 0: Check idempotency
      const existingJob = await ctx.jobStore.checkIdempotency(ctx.idempotencyKey);
      if (existingJob) {
        return existingJob;
      }

      // Save initial job
      await ctx.jobStore.saveJob(job);

      // Step 1: Artifact validation
      job = await this.updateJob(job, 'artifact_validation', ctx.jobStore);
      const artifact = await ctx.hermesDbClient.getArtifact(ctx.artifactId);
      if (!artifact) {
        return await this.failJob(job, 'invalid_artifact', ErrorCode.ARTIFACT_NOT_FOUND, 'Artifact not found', ctx.jobStore);
      }

      const validationResult = this.validator.validate(artifact);
      if (!validationResult.valid) {
        const errorMessage = validationResult.errors.map((e) => `${e.field}: ${e.issue}`).join('; ');
        return await this.failJob(job, 'invalid_artifact', ErrorCode.ARTIFACT_VALIDATION_FAILED, errorMessage, ctx.jobStore);
      }

      // Extract title for job metadata
      job.title = (artifact.metadata as any)?.title || 'Untitled';

      // Step 2: Adapter check
      job = await this.updateJob(job, 'adapter_check', ctx.jobStore);
      const adapterClient = new WechatAdapterClient(ctx.adapterConfig);

      try {
        await adapterClient.checkHealth();
      } catch (error) {
        if (error instanceof AdapterUnreachableError || error instanceof AdapterTimeoutError) {
          return await this.failJob(
            job,
            'needs_operator_action',
            ErrorCode.ADAPTER_UNREACHABLE,
            'Adapter unreachable. Check Tailscale/WireGuard/SSH tunnel.',
            ctx.jobStore
          );
        }
        if (error instanceof AdapterAuthError) {
          return await this.failJob(
            job,
            'needs_operator_action',
            ErrorCode.ADAPTER_AUTH_FAILED,
            'Adapter auth failed. Check ADAPTER_AUTH_TOKEN.',
            ctx.jobStore
          );
        }
        throw error;
      }

      // Step 3: Payload build
      job = await this.updateJob(job, 'payload_build', ctx.jobStore);
      const payloadResult = this.payloadBuilder.buildPayload(artifact);
      if (!payloadResult.success || !payloadResult.payload) {
        const errorMessage = payloadResult.errors?.map((e) => `${e.field}: ${e.issue}`).join('; ') || 'Payload build failed';
        return await this.failJob(job, 'invalid_artifact', ErrorCode.ARTIFACT_VALIDATION_FAILED, errorMessage, ctx.jobStore);
      }

      // Step 4: Draft creating
      job = await this.updateJob(job, 'draft_creating', ctx.jobStore);

      try {
        const response = await adapterClient.createDraft(ctx.account, payloadResult.payload);

        if (!response.success || !response.media_id) {
          return await this.failJob(
            job,
            'failed',
            ErrorCode.WECHAT_API_ERROR,
            'Draft creation failed: no media_id returned',
            ctx.jobStore
          );
        }

        // Success! Record media_id
        job.media_id = response.media_id;

        // Step 5: Ledger update
        job = await this.updateJob(job, 'ledger_update', ctx.jobStore);

        try {
          await ctx.hermesDbClient.upsertArticleLedger({
            account: ctx.account,
            run_id: artifact.run_id,
            status: 'drafted',
            draft_artifact_id: ctx.artifactId,
            title: job.title || 'Untitled',
            publication_idempotency_key: ctx.idempotencyKey,
            metadata: {
              wechat_media_id: job.media_id,
              draft_created_at: new Date().toISOString(),
            },
          });
        } catch (error) {
          // Ledger update failed, but draft was created successfully
          // Log error and continue to 'saved' status
          console.warn('Article ledger upsert failed (draft already created):', error);
          job.error = {
            code: ErrorCode.HERMES_DB_UPSERT_FAILED,
            message: `Draft created successfully (media_id: ${job.media_id}), but ledger update failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
          };
        }

        // Mark as saved
        job = await this.updateJob(job, 'saved', ctx.jobStore);

        return job;
      } catch (error) {
        // Classify adapter/WeChat errors
        if (error instanceof AdapterTokenError) {
          return await this.failJob(
            job,
            'needs_operator_action',
            ErrorCode.WECHAT_TOKEN_INVALID,
            `WeChat token error [${error.errcode}]: ${error.errmsg}. Check ECS adapter credentials.`,
            ctx.jobStore
          );
        }

        if (error instanceof AdapterWeChatApiError) {
          // Rate limit
          if (error.errcode === 45009) {
            return await this.failJob(
              job,
              'needs_operator_action',
              ErrorCode.WECHAT_RATE_LIMIT,
              `WeChat API rate limit [${error.errcode}]: ${error.errmsg}. Wait and retry later.`,
              ctx.jobStore
            );
          }

          // Permission
          if (error.errcode === 48001) {
            return await this.failJob(
              job,
              'needs_operator_action',
              ErrorCode.WECHAT_PERMISSION_DENIED,
              `WeChat permission denied [${error.errcode}]: ${error.errmsg}. Check account permissions.`,
              ctx.jobStore
            );
          }

          // Asset error
          if (error.errcode === 40007 || error.errcode === 40008) {
            return await this.failJob(
              job,
              'invalid_artifact',
              ErrorCode.WECHAT_ASSET_INVALID,
              `WeChat asset error [${error.errcode}]: ${error.errmsg}. Check thumb_media_id or content format.`,
              ctx.jobStore
            );
          }

          // Other WeChat API error
          return await this.failJob(
            job,
            'failed',
            ErrorCode.WECHAT_API_ERROR,
            `WeChat API error [${error.errcode}]: ${error.errmsg}`,
            ctx.jobStore
          );
        }

        if (error instanceof AdapterUnreachableError || error instanceof AdapterTimeoutError) {
          return await this.failJob(
            job,
            'needs_operator_action',
            ErrorCode.ADAPTER_UNREACHABLE,
            'Adapter unreachable during draft creation. Check network connectivity.',
            ctx.jobStore
          );
        }

        // Unknown error
        return await this.failJob(
          job,
          'failed',
          ErrorCode.INTERNAL_ERROR,
          error instanceof Error ? error.message : 'Unknown error during draft creation',
          ctx.jobStore
        );
      }
    } catch (error) {
      return await this.failJob(
        job,
        'failed',
        ErrorCode.INTERNAL_ERROR,
        error instanceof Error ? error.message : 'Unknown error',
        ctx.jobStore
      );
    }
  }

  /**
   * Update job status and save.
   */
  private async updateJob(job: DraftJob, status: DraftJobStatus, jobStore: JobStore): Promise<DraftJob> {
    const updatedJob: DraftJob = {
      ...job,
      status,
      updated_at: new Date().toISOString(),
    };
    await jobStore.saveJob(updatedJob);
    return updatedJob;
  }

  /**
   * Fail job with error and save.
   */
  private async failJob(
    job: DraftJob,
    status: DraftJobStatus,
    errorCode: string,
    errorMessage: string,
    jobStore: JobStore
  ): Promise<DraftJob> {
    const failedJob: DraftJob = {
      ...job,
      status,
      error: {
        code: errorCode,
        message: errorMessage,
      },
      updated_at: new Date().toISOString(),
    };
    await jobStore.saveJob(failedJob);
    return failedJob;
  }

  /**
   * Generate unique job ID.
   */
  private generateJobId(): string {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 9);
    return `job_${timestamp}_${random}`;
  }
}
