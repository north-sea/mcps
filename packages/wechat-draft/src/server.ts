import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { ConfigLoader } from "./config/index.js";
import { HermesDbClient, ArtifactValidator } from "./hermes/index.js";
import { JobStore } from "./store/index.js";
import { DraftWorkflow } from "./workflow/index.js";
import { AssetSourceLoader } from "./wechat/AssetSourceLoader.js";
import { WechatAdapterClient } from "./wechat/WechatAdapterClient.js";
import {
  ListAccountsInputSchema,
  ListAccountsOutput,
  ValidateArtifactInputSchema,
  ValidateArtifactOutput,
  CreateDraftInputSchema,
  CreateDraftOutput,
  GetDraftStatusOutput,
  UploadAssetInputSchema,
  UploadAssetOutput,
  JobIdSchema,
  ArtifactIdSchema,
  ErrorCode,
  createSuccessResult,
  createErrorResult,
} from "./schemas/index.js";

export function createServer(): McpServer {
  const server = new McpServer({
    name: "WeChat Draft MCP Server",
    version: "0.1.0",
  });

  const configLoader = new ConfigLoader();
  const config = configLoader.load();
  const hermesDbClient = new HermesDbClient(
    config.hermes_db.base_url,
    config.hermes_db.timeout_ms,
    config.hermes_db.auth_token
  );
  const artifactValidator = new ArtifactValidator();
  const jobStore = new JobStore({ runtimePath: config.runtime_path });

  // Initialize job store (create directories)
  jobStore.initialize().catch((error) => {
    console.error('Failed to initialize job store:', error);
  });

  // ==========================================================================
  // Tool: wechat_list_accounts (read-only)
  // ==========================================================================
  server.tool(
    "wechat_list_accounts",
    "List available WeChat accounts. Returns enabled accounts by default.",
    {
      include_disabled: ListAccountsInputSchema.shape.include_disabled,
    },
    async ({ include_disabled }) => {
      try {
        const accounts = configLoader.getAllAccounts(include_disabled);
        const result: ListAccountsOutput = {
          accounts: accounts.map((acc) => {
            const adapter = configLoader.getAdapter(acc.adapter_id);
            return {
              account_id: acc.account_id,
              display_name: acc.display_name,
              enabled: acc.enabled,
              adapter_id: acc.adapter_id,
              capabilities: adapter?.capabilities,
            };
          }),
        };

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(createSuccessResult(result), null, 2),
            },
          ],
        };
      } catch (error) {
        const errorResult = createErrorResult(
          ErrorCode.INTERNAL_ERROR,
          error instanceof Error ? error.message : "Unknown error"
        );
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(errorResult, null, 2),
            },
          ],
        };
      }
    }
  );

  // ==========================================================================
  // Tool: wechat_validate_publish_artifact (read-only)
  // ==========================================================================
  server.tool(
    "wechat_validate_publish_artifact",
    "Validate that a hermes-db artifact is WeChat-ready before creating draft. Checks stage, type, publish_ready flag, and wechat_asset_manifest.",
    {
      account: ValidateArtifactInputSchema.shape.account,
      artifact_id: ValidateArtifactInputSchema.shape.artifact_id,
    },
    async ({ account, artifact_id }) => {
      try {
        // Check account exists and enabled
        const accountConfig = configLoader.getAccount(account);
        if (!accountConfig) {
          const errorResult = createErrorResult(
            ErrorCode.ACCOUNT_NOT_FOUND,
            `Account "${account}" not found`
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        if (!accountConfig.enabled) {
          const errorResult = createErrorResult(
            ErrorCode.ACCOUNT_DISABLED,
            `Account "${account}" is disabled`
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        // Get artifact from hermes-db
        const artifact = await hermesDbClient.getArtifact(artifact_id);
        if (!artifact) {
          const errorResult = createErrorResult(
            ErrorCode.ARTIFACT_NOT_FOUND,
            `Artifact "${artifact_id}" not found in hermes-db`
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        // Validate artifact is WeChat-ready
        const validationResult = artifactValidator.validate(artifact);

        const result: ValidateArtifactOutput = {
          valid: validationResult.valid,
          artifact_id,
          account,
          validation_errors: [
            ...validationResult.errors,
            ...validationResult.warnings,
          ],
          artifact_summary: {
            title: (artifact.metadata as any)?.title,
            stage: artifact.stage,
            type: artifact.type,
            publish_ready: (artifact.metadata as any)?.publish_ready,
            wechat_asset_ready: (artifact.metadata as any)?.wechat_asset_manifest?.ready,
          },
        };

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(createSuccessResult(result), null, 2),
            },
          ],
        };
      } catch (error) {
        const errorResult = createErrorResult(
          ErrorCode.INTERNAL_ERROR,
          error instanceof Error ? error.message : "Unknown error"
        );
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(errorResult, null, 2),
            },
          ],
        };
      }
    }
  );

  // ==========================================================================
  // Tool: wechat_create_draft (side-effecting)
  // ==========================================================================
  server.tool(
    "wechat_create_draft",
    "Create a WeChat draft from a hermes-db publish-ready artifact. This is a side-effecting operation that creates a draft in WeChat account's draft box.",
    {
      account: CreateDraftInputSchema.shape.account,
      artifact_id: CreateDraftInputSchema.shape.artifact_id,
      idempotency_key: CreateDraftInputSchema.shape.idempotency_key,
    },
    async ({ account, artifact_id, idempotency_key }) => {
      try {
        // Check account
        const accountConfig = configLoader.getAccount(account);
        if (!accountConfig) {
          const errorResult = createErrorResult(
            ErrorCode.ACCOUNT_NOT_FOUND,
            `Account "${account}" not found`
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        if (!accountConfig.enabled) {
          const errorResult = createErrorResult(
            ErrorCode.ACCOUNT_DISABLED,
            `Account "${account}" is disabled`
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        // Get adapter config
        const adapterConfig = configLoader.getAdapter(accountConfig.adapter_id);
        if (!adapterConfig) {
          const errorResult = createErrorResult(
            ErrorCode.ADAPTER_NOT_FOUND,
            `Adapter "${accountConfig.adapter_id}" not found`
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        // Generate idempotency key if not provided
        const finalIdempotencyKey = idempotency_key || JobStore.generateIdempotencyKey(account, artifact_id);

        // Execute draft workflow
        const workflow = new DraftWorkflow();
        const job = await workflow.execute({
          account,
          artifactId: artifact_id,
          idempotencyKey: finalIdempotencyKey,
          hermesDbClient,
          adapterConfig,
          jobStore,
        });

        // Build response
        const result: CreateDraftOutput = {
          job_id: job.job_id,
          status: job.status,
          account: job.account,
          artifact_id: job.artifact_id,
          title: job.title,
          media_id: job.media_id,
          error: job.error,
          created_at: job.created_at,
        };

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(createSuccessResult(result), null, 2),
            },
          ],
          isError: job.status !== 'saved',
        };
      } catch (error) {
        const errorResult = createErrorResult(
          ErrorCode.INTERNAL_ERROR,
          error instanceof Error ? error.message : "Unknown error"
        );
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(errorResult, null, 2),
            },
          ],
          isError: true,
        };
      }
    }
  );

  // ==========================================================================
  // Tool: wechat_get_draft_status (read-only)
  // ==========================================================================
  server.tool(
    "wechat_get_draft_status",
    "Get draft job status by job_id or artifact_id. Returns job metadata, current status, and media_id if available.",
    {
      job_id: JobIdSchema.optional(),
      artifact_id: ArtifactIdSchema.optional(),
    },
    async ({ job_id, artifact_id }) => {
      try {
        // Validate input
        if (!job_id && !artifact_id) {
          const errorResult = createErrorResult(
            ErrorCode.INVALID_INPUT,
            "Either job_id or artifact_id must be provided"
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        // Query job store
        let job = null;
        if (job_id) {
          job = await jobStore.getJobById(job_id);
        } else if (artifact_id) {
          job = await jobStore.getJobByArtifactId(artifact_id);
        }

        // Build result
        const result: GetDraftStatusOutput = job
          ? {
              found: true,
              job_id: job.job_id,
              status: job.status,
              account: job.account,
              artifact_id: job.artifact_id,
              title: job.title,
              media_id: job.media_id,
              error: job.error,
              created_at: job.created_at,
              updated_at: job.updated_at,
            }
          : { found: false };

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(createSuccessResult(result), null, 2),
            },
          ],
        };
      } catch (error) {
        const errorResult = createErrorResult(
          ErrorCode.INTERNAL_ERROR,
          error instanceof Error ? error.message : "Unknown error"
        );
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(errorResult, null, 2),
            },
          ],
        };
      }
    }
  );

  // ==========================================================================
  // Tool: wechat_upload_asset (side-effecting)
  // ==========================================================================
  server.tool(
    "wechat_upload_asset",
    "Upload image asset to WeChat material API. Supports body_image (returns wechat_url for inline content) and cover_image (returns thumb_media_id for draft cover). This is a side-effecting operation that uploads to WeChat's material system.",
    {
      account: UploadAssetInputSchema.shape.account,
      usage: UploadAssetInputSchema.shape.usage,
      source_type: UploadAssetInputSchema.shape.source_type,
      source: UploadAssetInputSchema.shape.source,
      filename: UploadAssetInputSchema.shape.filename,
      mime_type: UploadAssetInputSchema.shape.mime_type,
    },
    async ({ account, usage, source_type, source, filename, mime_type }) => {
      try {
        // Check account
        const accountConfig = configLoader.getAccount(account);
        if (!accountConfig) {
          const errorResult = createErrorResult(
            ErrorCode.ACCOUNT_NOT_FOUND,
            `Account "${account}" not found`
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        if (!accountConfig.enabled) {
          const errorResult = createErrorResult(
            ErrorCode.ACCOUNT_DISABLED,
            `Account "${account}" is disabled`
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        // Get adapter config
        const adapterConfig = configLoader.getAdapter(accountConfig.adapter_id);
        if (!adapterConfig) {
          const errorResult = createErrorResult(
            ErrorCode.ADAPTER_NOT_FOUND,
            `Adapter "${accountConfig.adapter_id}" not found`
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        // Check adapter capability
        if (!adapterConfig.capabilities.includes('asset_upload')) {
          const errorResult = createErrorResult(
            ErrorCode.ADAPTER_CAPABILITY_MISSING,
            `Adapter "${accountConfig.adapter_id}" does not support asset_upload capability`
          );
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(errorResult, null, 2),
              },
            ],
          };
        }

        // Load asset source (local_path or remote_url)
        const assetLoader = new AssetSourceLoader();
        const loadedAsset = await assetLoader.load({
          usage,
          source_type,
          source,
          filename,
          mime_type,
        });

        // Upload to adapter
        const adapterClient = new WechatAdapterClient(adapterConfig);
        const uploadResponse = await adapterClient.uploadAsset(account, {
          usage,
          bytes: loadedAsset.bytes,
          filename: loadedAsset.filename,
          mimeType: loadedAsset.mimeType,
        });

        // Build response
        const result: UploadAssetOutput = {
          account,
          usage,
          source_type,
          filename: loadedAsset.filename,
          mime_type: loadedAsset.mimeType,
          size_bytes: loadedAsset.sizeBytes,
          wechat_url: uploadResponse.wechat_url,
          thumb_media_id: uploadResponse.thumb_media_id,
          created_at: new Date().toISOString(),
        };

        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(createSuccessResult(result), null, 2),
            },
          ],
        };
      } catch (error) {
        // Map AssetSourceError to specific error codes
        if (error && typeof error === 'object' && 'code' in error && 'name' in error) {
          const typedError = error as any;

          // AssetSourceError - already has correct error codes
          if (typedError.name === 'AssetSourceError') {
            const errorResult = createErrorResult(
              typedError.code,
              typedError.message,
              typedError.details
            );
            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify(errorResult, null, 2),
                },
              ],
              isError: true,
            };
          }

          // AdapterError subclasses
          if (typedError.name?.startsWith('Adapter')) {
            // Map adapter error codes to MCP error codes
            let errorCode = typedError.code;

            // Map adapter_endpoint_not_found to capability_missing for asset upload
            if (typedError.code === 'adapter_endpoint_not_found') {
              errorCode = ErrorCode.ADAPTER_CAPABILITY_MISSING;
            }

            const errorResult = createErrorResult(
              errorCode,
              typedError.message,
              // Filter out sensitive details (don't include auth tokens, full URLs, etc.)
              typedError.details ? { account: typedError.details.account } : undefined
            );
            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify(errorResult, null, 2),
                },
              ],
              isError: true,
            };
          }
        }

        const errorResult = createErrorResult(
          ErrorCode.INTERNAL_ERROR,
          error instanceof Error ? error.message : "Unknown error"
        );
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(errorResult, null, 2),
            },
          ],
          isError: true,
        };
      }
    }
  );

  return server;
}
