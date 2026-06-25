/**
 * Manual regression tests for production smoke support fixes.
 */

import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { HermesDbClient } from './dist/hermes/index.js';
import { JobStore } from './dist/store/index.js';

let testCount = 0;
let passCount = 0;

function assert(condition, message) {
  testCount++;
  if (!condition) {
    console.error(`FAIL: ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  }
  passCount++;
  console.log(`PASS: ${message}`);
}

const runtimePath = mkdtempSync(join(tmpdir(), 'wechat-draft-jobstore-test-'));

try {
  const jobStore = new JobStore({ runtimePath });
  await jobStore.initialize();

  const createdAt = '2026-06-25T00:00:00.000Z';
  const olderJob = {
    job_id: 'job-regression-1',
    status: 'queued',
    account: 'xiaban',
    artifact_id: 'artifact-regression-1',
    idempotency_key: 'xiaban:artifact-regression-1',
    created_at: createdAt,
    updated_at: '2026-06-25T00:00:01.000Z',
  };
  const newerJob = {
    ...olderJob,
    status: 'saved',
    media_id: 'mock-media-id',
    updated_at: '2026-06-25T00:00:03.000Z',
  };

  await jobStore.saveJob(olderJob);
  await jobStore.saveJob(newerJob);

  const byJobId = await jobStore.getJobById('job-regression-1');
  assert(byJobId?.status === 'saved', 'JobStore getJobById returns latest updated_at state');
  assert(byJobId?.media_id === 'mock-media-id', 'JobStore latest state preserves media_id');

  const byArtifactId = await jobStore.getJobByArtifactId('artifact-regression-1');
  assert(byArtifactId?.status === 'saved', 'JobStore getJobByArtifactId returns latest updated_at state');

  const artifact = {
    artifact_id: 'artifact-regression-1',
    run_id: 'run-regression-1',
    account: 'xiaban',
    stage: 'publish_ready',
    type: 'wechat_api_article',
    name: 'regression artifact',
    content_hash: 'hash',
    content_size_bytes: 12,
    content_text: '<p>ok</p>',
    metadata: JSON.stringify({
      publish_ready: true,
      style_profile_id: 'xiaban.default',
    }),
    created_at: createdAt,
    updated_at: '2026-06-25T00:00:00.000Z',
  };

  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async () => ({
      ok: true,
      json: async () => ({
        jsonrpc: '2.0',
        id: 1,
        result: {
          content: [
            {
              type: 'text',
              text: JSON.stringify(artifact),
            },
          ],
        },
      }),
    });

    const client = new HermesDbClient('http://127.0.0.1:8765', 1000);
    const loaded = await client.getArtifact('artifact-regression-1');
    assert(loaded?.metadata.publish_ready === true, 'HermesDbClient parses string metadata as object');
    assert(
      loaded?.metadata.style_profile_id === 'xiaban.default',
      'HermesDbClient preserves parsed style_profile_id metadata'
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
} finally {
  rmSync(runtimePath, { recursive: true, force: true });
}

console.log(`\n${passCount}/${testCount} tests passed`);
