import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import type { DraftJob } from '../schemas/tool-schemas.js';
import { SQLiteJobStore } from './SQLiteJobStore.js';

test('SQLiteJobStore initializes schema and persists job status updates', async () => {
  const { store, cleanup } = await createStore();

  try {
    const job = makeJob({ job_id: 'job_schema_1', idempotency_key: 'idem_schema' });
    const created = await store.createOrGetJob({ job });
    assert.equal(created.created, true);

    await store.saveJob({
      ...job,
      status: 'saved',
      media_id: 'draft_media_1',
      error: {
        code: 'ledger_warning',
        message: 'ledger update failed',
        details: { run_id: 'run_1' },
      },
      updated_at: '2026-01-01T00:01:00.000Z',
    });

    const byId = await store.getJobById(job.job_id);
    assert.equal(byId?.status, 'saved');
    assert.equal(byId?.media_id, 'draft_media_1');
    assert.deepEqual(byId?.error?.details, { run_id: 'run_1' });

    const byArtifact = await store.getJobByArtifactId(job.artifact_id);
    assert.equal(byArtifact?.job_id, job.job_id);

    const byIdempotency = await store.checkIdempotency(job.idempotency_key);
    assert.equal(byIdempotency?.job_id, job.job_id);
  } finally {
    store.close();
    await cleanup();
  }
});

test('SQLiteJobStore createOrGetJob returns existing rows for duplicate idempotency keys', async () => {
  const { store, cleanup } = await createStore();

  try {
    const firstJob = makeJob({ job_id: 'job_dup_1', idempotency_key: 'idem_dup' });
    const secondJob = makeJob({ job_id: 'job_dup_2', idempotency_key: 'idem_dup' });

    const results = await Promise.all([
      store.createOrGetJob({ job: firstJob }),
      store.createOrGetJob({ job: secondJob }),
    ]);

    assert.equal(results.filter((item) => item.created).length, 1);
    assert.equal(new Set(results.map((item) => item.job.job_id)).size, 1);
  } finally {
    store.close();
    await cleanup();
  }
});

test('SQLiteJobStore removes expired terminal jobs before reusing idempotency keys', async () => {
  const { store, cleanup } = await createStore();

  try {
    const oldNow = new Date('2026-01-01T00:00:00.000Z');
    const newNow = new Date('2026-01-09T00:00:00.000Z');
    const oldJob = makeJob({ job_id: 'job_expired_1', idempotency_key: 'idem_expired' });
    const newJob = makeJob({ job_id: 'job_expired_2', idempotency_key: 'idem_expired' });

    await store.createOrGetJob({ job: oldJob, now: oldNow });
    await store.saveJob({
      ...oldJob,
      status: 'failed',
      updated_at: '2026-01-01T00:01:00.000Z',
    });

    const result = await store.createOrGetJob({ job: newJob, now: newNow });

    assert.equal(result.created, true);
    assert.equal(result.job.job_id, newJob.job_id);
  } finally {
    store.close();
    await cleanup();
  }
});

test('SQLiteJobStore does not remove expired in-progress jobs', async () => {
  const { store, cleanup } = await createStore();

  try {
    const oldNow = new Date('2026-01-01T00:00:00.000Z');
    const newNow = new Date('2026-01-09T00:00:00.000Z');
    const oldJob = makeJob({ job_id: 'job_in_progress_1', idempotency_key: 'idem_busy' });
    const newJob = makeJob({ job_id: 'job_in_progress_2', idempotency_key: 'idem_busy' });

    await store.createOrGetJob({ job: oldJob, now: oldNow });
    const result = await store.createOrGetJob({ job: newJob, now: newNow });

    assert.equal(result.created, false);
    assert.equal(result.job.job_id, oldJob.job_id);
    assert.equal(result.job.status, 'queued');
  } finally {
    store.close();
    await cleanup();
  }
});

test('SQLiteJobStore uses DATABASE_PATH as the SQLite file location', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'wechat-draft-sqlite-env-test-'));
  const databasePath = join(dir, 'custom', 'jobs.db');
  const previousDatabasePath = process.env.DATABASE_PATH;
  const previousWechatDatabasePath = process.env.WECHAT_DRAFT_DATABASE_PATH;
  const previousRuntimePath = process.env.WECHAT_DRAFT_RUNTIME_PATH;

  delete process.env.WECHAT_DRAFT_DATABASE_PATH;
  delete process.env.WECHAT_DRAFT_RUNTIME_PATH;
  process.env.DATABASE_PATH = databasePath;

  const store = new SQLiteJobStore();

  try {
    assert.equal(store.getDatabasePath(), databasePath);
    assert.equal(store.getRuntimePath(), dirname(databasePath));

    await store.initialize();
    const result = await store.createOrGetJob({
      job: makeJob({ job_id: 'job_env_path_1', idempotency_key: 'idem_env_path' }),
    });

    assert.equal(result.created, true);
  } finally {
    store.close();
    restoreEnv('DATABASE_PATH', previousDatabasePath);
    restoreEnv('WECHAT_DRAFT_DATABASE_PATH', previousWechatDatabasePath);
    restoreEnv('WECHAT_DRAFT_RUNTIME_PATH', previousRuntimePath);
    await rm(dir, { recursive: true, force: true });
  }
});

async function createStore(): Promise<{
  store: SQLiteJobStore;
  cleanup: () => Promise<void>;
}> {
  const dir = await mkdtemp(join(tmpdir(), 'wechat-draft-sqlite-test-'));
  const store = new SQLiteJobStore({ databasePath: join(dir, 'jobs.db') });
  await store.initialize();

  return {
    store,
    cleanup: () => rm(dir, { recursive: true, force: true }),
  };
}

function makeJob(overrides: Partial<DraftJob> = {}): DraftJob {
  return {
    job_id: 'job_test_1',
    status: 'queued',
    account: 'xiaban',
    artifact_id: 'artifact_1',
    idempotency_key: 'xiaban:artifact_1',
    created_at: '2026-01-01T00:00:00.000Z',
    updated_at: '2026-01-01T00:00:00.000Z',
    ...overrides,
  };
}

function restoreEnv(name: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[name];
    return;
  }

  process.env[name] = value;
}
