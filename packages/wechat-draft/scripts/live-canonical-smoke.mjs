#!/usr/bin/env node
/**
 * Live smoke for wechat-canonical-article-artifact.
 *
 * Side effects:
 * - Uploads one body image and one cover image to WeChat material APIs.
 * - Writes article_document and wechat_api_article artifacts to hermes-db.
 * - Creates one WeChat draft. It does not publish.
 */

import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  ARTICLE_DOCUMENT_SCHEMA_VERSION,
  ArticleDocumentToWechatArtifactBuilder,
} from '../dist/render/index.js';
import { DraftPayloadBuilder } from '../dist/wechat/index.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const MCP_SERVER_PATH = join(__dirname, '../dist/index.js');

const account = process.env.WECHAT_CANONICAL_SMOKE_ACCOUNT || 'yueliang';
const coverPath = process.env.WECHAT_CANONICAL_SMOKE_COVER || '/private/tmp/wechat-canonical-smoke-cover.jpg';
const bodyPath = process.env.WECHAT_CANONICAL_SMOKE_BODY || coverPath;
const adapterBaseUrl = process.env.WECHAT_ADAPTER_BASE_URL || 'http://100.117.14.128:3000';
const hermesBaseUrl = process.env.HERMES_DB_BASE_URL || 'http://100.113.231.101:8765';
const runId = `wechat-canonical-smoke-${new Date().toISOString().replace(/[:.]/g, '-')}`;
const sourceArtifactId = `${runId}-article-document`;

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

function textPreview(value) {
  return value.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim().slice(0, 240);
}

async function callHermesTool(name, args) {
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
  if (process.env.HERMES_DB_AUTH_TOKEN) {
    headers.Authorization = `Bearer ${process.env.HERMES_DB_AUTH_TOKEN}`;
  }

  const response = await fetch(`${hermesBaseUrl}/mcp`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: {
        name,
        arguments: args,
      },
    }),
  });

  const body = await response.text();
  if (!response.ok) {
    throw new Error(`hermes-db HTTP ${response.status}: ${body}`);
  }

  const parsed = JSON.parse(body);
  if (parsed.error) {
    throw new Error(`hermes-db JSON-RPC error: ${JSON.stringify(parsed.error)}`);
  }

  const text = parsed.result?.content?.[0]?.text;
  return text ? JSON.parse(text) : parsed.result;
}

async function callAdapter(path, body) {
  if (!process.env.WECHAT_ADAPTER_AUTH_TOKEN) {
    throw new Error('WECHAT_ADAPTER_AUTH_TOKEN is required for adapter calls');
  }

  const response = await fetch(`${adapterBaseUrl}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${process.env.WECHAT_ADAPTER_AUTH_TOKEN}`,
    },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok || data.success === false) {
    throw new Error(`adapter ${path} failed: ${JSON.stringify(data)}`);
  }
  return data;
}

function callMcpTool(toolName, params = {}) {
  return new Promise((resolve, reject) => {
    const mcp = spawn('node', [MCP_SERVER_PATH], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        WECHAT_ADAPTER_BASE_URL: adapterBaseUrl,
        WECHAT_DRAFT_RUNTIME_PATH: process.env.WECHAT_DRAFT_RUNTIME_PATH || '/tmp/wechat-draft-live-smoke',
      },
    });

    let stdout = '';
    let stderr = '';

    mcp.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    mcp.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    mcp.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`MCP exited with code ${code}: ${stderr}`));
        return;
      }

      try {
        const line = stdout
          .split(/\r?\n/)
          .map((item) => item.trim())
          .filter(Boolean)
          .find((item) => item.startsWith('{'));
        if (!line) {
          throw new Error(`No JSON-RPC response on stdout. stderr=${stderr}`);
        }
        const response = JSON.parse(line);
        if (response.error) {
          throw new Error(`MCP JSON-RPC error: ${JSON.stringify(response.error)}`);
        }
        const text = response.result?.content?.[0]?.text;
        resolve(text ? JSON.parse(text) : response.result);
      } catch (error) {
        reject(error);
      }
    });

    mcp.stdin.write(
      JSON.stringify({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'tools/call',
        params: {
          name: toolName,
          arguments: params,
        },
      }) + '\n'
    );
    mcp.stdin.end();
  });
}

async function main() {
  console.log(JSON.stringify({ step: 'start', account, adapterBaseUrl, hermesBaseUrl, runId }));

  const bodyUpload = await callMcpTool('wechat_upload_asset', {
    account,
    usage: 'body_image',
    source_type: 'local_path',
    source: bodyPath,
    filename: 'canonical-smoke-body.jpg',
    mime_type: 'image/jpeg',
  });
  if (!bodyUpload.success || !bodyUpload.data?.wechat_url) {
    throw new Error(`body image upload failed: ${JSON.stringify(bodyUpload)}`);
  }
  console.log(JSON.stringify({ step: 'body_uploaded', wechat_url: bodyUpload.data.wechat_url }));

  const coverUpload = await callMcpTool('wechat_upload_asset', {
    account,
    usage: 'cover_image',
    source_type: 'local_path',
    source: coverPath,
    filename: 'canonical-smoke-cover.jpg',
    mime_type: 'image/jpeg',
  });
  if (!coverUpload.success || !coverUpload.data?.thumb_media_id) {
    throw new Error(`cover image upload failed: ${JSON.stringify(coverUpload)}`);
  }
  console.log(JSON.stringify({ step: 'cover_uploaded', thumb_media_id: coverUpload.data.thumb_media_id }));

  const article = {
    schema_version: ARTICLE_DOCUMENT_SCHEMA_VERSION,
    title: `Canonical smoke ${new Date().toISOString()}`,
    digest: 'Canonical article_document live smoke. Safe to delete.',
    author: 'mcps',
    style_profile_id: 'yueliang.default',
    cover: {
      thumb_media_id: coverUpload.data.thumb_media_id,
    },
    assets: {
      smoke_body: {
        asset_ref: 'smoke_body',
        wechat_url: bodyUpload.data.wechat_url,
        alt: 'canonical smoke body image',
        ready: true,
      },
    },
    doc: {
      type: 'doc',
      content: [
        {
          type: 'heading',
          attrs: { level: 2 },
          content: [{ type: 'text', text: 'Canonical Article Smoke' }],
        },
        {
          type: 'paragraph',
          content: [
            { type: 'text', text: 'This draft was created by ' },
            { type: 'text', text: 'article_document.tiptap.v1', marks: [{ type: 'bold' }] },
            { type: 'text', text: ' live smoke.' },
          ],
        },
        {
          type: 'image',
          attrs: { asset_ref: 'smoke_body', alt: 'canonical smoke body image' },
        },
        { type: 'horizontalRule' },
      ],
    },
  };

  const sourceContentText = JSON.stringify(article);
  const sourceArtifact = {
    artifact_id: sourceArtifactId,
    run_id: runId,
    account,
    stage: 'drafted',
    type: 'article_document',
    name: 'canonical-smoke.article-document.json',
    content_hash: sha256(sourceContentText),
    content_size_bytes: Buffer.byteLength(sourceContentText, 'utf8'),
    content_preview: article.title,
    content_text: sourceContentText,
    metadata: {
      schema_version: ARTICLE_DOCUMENT_SCHEMA_VERSION,
      style_profile_id: article.style_profile_id,
      smoke: true,
    },
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  const readyArtifact = new ArticleDocumentToWechatArtifactBuilder().build({ source: sourceArtifact });
  readyArtifact.metadata = {
    ...readyArtifact.metadata,
    smoke: true,
  };
  readyArtifact.content_preview = textPreview(readyArtifact.content_text);

  let mediaId;
  let jobStatus;
  if (process.env.HERMES_DB_AUTH_TOKEN) {
    await callHermesTool('upsert_workflow_artifact', sourceArtifact);
    console.log(JSON.stringify({ step: 'source_artifact_upserted', artifact_id: sourceArtifact.artifact_id }));

    await callHermesTool('upsert_workflow_artifact', readyArtifact);
    console.log(JSON.stringify({ step: 'ready_artifact_upserted', artifact_id: readyArtifact.artifact_id }));

    const validation = await callMcpTool('wechat_validate_publish_artifact', {
      account,
      artifact_id: readyArtifact.artifact_id,
    });
    console.log(JSON.stringify({ step: 'artifact_validated', valid: validation.success, artifact_id: readyArtifact.artifact_id }));

    const draft = await callMcpTool('wechat_create_draft', {
      account,
      artifact_id: readyArtifact.artifact_id,
      idempotency_key: `${readyArtifact.artifact_id}:canonical-smoke`,
    });
    console.log(JSON.stringify({ step: 'draft_created', result: draft }));

    const jobId = draft.data?.job_id;
    const status = await callMcpTool('wechat_get_draft_status', {
      ...(jobId ? { job_id: jobId } : { artifact_id: readyArtifact.artifact_id }),
    });
    console.log(JSON.stringify({ step: 'draft_status', result: status }));
    mediaId = draft.data?.media_id || status.data?.media_id;
    jobStatus = status.data?.status;
  } else {
    console.log(JSON.stringify({ step: 'hermes_skipped', reason: 'HERMES_DB_AUTH_TOKEN not set; using direct adapter fallback' }));
    const payloadResult = new DraftPayloadBuilder().buildPayload(readyArtifact);
    if (!payloadResult.success || !payloadResult.payload) {
      throw new Error(`payload build failed: ${JSON.stringify(payloadResult.errors)}`);
    }
    const draft = await callAdapter(`/accounts/${encodeURIComponent(account)}/drafts`, payloadResult.payload);
    console.log(JSON.stringify({ step: 'draft_created_direct_adapter', result: draft }));
    mediaId = draft.media_id;
    jobStatus = 'adapter_saved';
  }

  const batchget = await callAdapter(`/accounts/${encodeURIComponent(account)}/drafts/batchget`, {
    offset: 0,
    count: 20,
    no_content: 0,
  });
  const item = (batchget.item || []).find((draft) => draft.media_id === mediaId);
  const articleContent = item?.content?.news_item?.[0]?.content || '';
  const batchgetChecks = {
    found: Boolean(item),
    hasCanonicalText: articleContent.includes('article_document.tiptap.v1'),
    noMarkdownResidue: !/(^|[^!])\*\*|##|!\[[^\]]*\]\(/.test(articleContent),
    hasWechatImage: /https?:\/\/mmbiz\.qpic\.cn\//.test(articleContent),
    contentLength: articleContent.length,
  };
  console.log(JSON.stringify({ step: 'draft_batchget', media_id: mediaId, checks: batchgetChecks }));
  if (
    !batchgetChecks.found ||
    !batchgetChecks.hasCanonicalText ||
    !batchgetChecks.noMarkdownResidue ||
    !batchgetChecks.hasWechatImage
  ) {
    throw new Error(`batchget verification failed: ${JSON.stringify(batchgetChecks)}`);
  }

  console.log(
    JSON.stringify({
      step: 'complete',
      artifact_id: readyArtifact.artifact_id,
      media_id: mediaId,
      job_status: jobStatus,
    })
  );
}

main().catch((error) => {
  console.error(JSON.stringify({ step: 'failed', message: error instanceof Error ? error.message : String(error) }));
  process.exit(1);
});
