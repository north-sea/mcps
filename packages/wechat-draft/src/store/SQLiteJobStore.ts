import Database from 'better-sqlite3';
import { promises as fs } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import type { DraftJob, DraftJobStatus } from '../schemas/tool-schemas.js';
import {
  type CreateOrGetJobInput,
  type CreateOrGetJobResult,
  type DraftJobStore,
  TERMINAL_JOB_STATUSES,
  generateIdempotencyKey,
} from './types.js';

const DEFAULT_RUNTIME_PATH = join(homedir(), '.wechat-draft');
const DEFAULT_DB_FILENAME = 'jobs.db';
const IDEMPOTENCY_WINDOW_DAYS = 7;

export interface SQLiteJobStoreConfig {
  runtimePath?: string;
  databasePath?: string;
}

interface JobRow {
  job_id: string;
  artifact_id: string;
  account: string;
  status: DraftJobStatus;
  media_id: string | null;
  idempotency_key: string;
  idempotency_expires_at: string;
  created_at: string;
  updated_at: string;
  error_code: string | null;
  error_message: string | null;
  error_details: string | null;
}

export class SQLiteJobStore implements DraftJobStore {
  private readonly runtimePath: string;
  private readonly databasePath: string;
  private db: Database.Database | null = null;

  constructor(config: SQLiteJobStoreConfig = {}) {
    const configuredDatabasePath =
      config.databasePath ||
      process.env.WECHAT_DRAFT_DATABASE_PATH ||
      process.env.DATABASE_PATH;

    this.runtimePath =
      config.runtimePath ||
      process.env.WECHAT_DRAFT_RUNTIME_PATH ||
      (configuredDatabasePath ? dirname(resolve(configuredDatabasePath)) : DEFAULT_RUNTIME_PATH);
    this.databasePath = configuredDatabasePath
      ? resolve(configuredDatabasePath)
      : join(this.runtimePath, DEFAULT_DB_FILENAME);
  }

  async initialize(): Promise<void> {
    await fs.mkdir(dirname(this.databasePath), { recursive: true });

    const db = new Database(this.databasePath);
    db.pragma('journal_mode = WAL');
    db.pragma('foreign_keys = ON');
    db.exec(`
      CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        artifact_id TEXT NOT NULL,
        account TEXT NOT NULL,
        status TEXT NOT NULL,
        media_id TEXT,
        idempotency_key TEXT NOT NULL,
        idempotency_expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        error_code TEXT,
        error_message TEXT,
        error_details TEXT,
        UNIQUE(account, idempotency_key)
      );

      CREATE INDEX IF NOT EXISTS idx_jobs_artifact_id
        ON jobs(artifact_id);

      CREATE INDEX IF NOT EXISTS idx_jobs_status
        ON jobs(status);

      CREATE INDEX IF NOT EXISTS idx_jobs_created_at
        ON jobs(created_at);

      CREATE INDEX IF NOT EXISTS idx_jobs_idempotency_expires_at
        ON jobs(idempotency_expires_at);
    `);

    this.db = db;
  }

  async createOrGetJob(input: CreateOrGetJobInput): Promise<CreateOrGetJobResult> {
    const db = this.requireDb();
    const now = input.now || new Date();
    const nowIso = now.toISOString();
    const expiresAt = addDays(now, IDEMPOTENCY_WINDOW_DAYS).toISOString();

    const transaction = db.transaction(() => {
      db.prepare(
        `DELETE FROM jobs
         WHERE idempotency_expires_at <= ?
           AND status IN (${TERMINAL_JOB_STATUSES.map(() => '?').join(', ')})`
      ).run(nowIso, ...TERMINAL_JOB_STATUSES);

      const insertResult = db.prepare(
        `INSERT OR IGNORE INTO jobs (
          job_id,
          artifact_id,
          account,
          status,
          media_id,
          idempotency_key,
          idempotency_expires_at,
          created_at,
          updated_at,
          error_code,
          error_message,
          error_details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      ).run(
        input.job.job_id,
        input.job.artifact_id,
        input.job.account,
        input.job.status,
        input.job.media_id ?? null,
        input.job.idempotency_key,
        expiresAt,
        input.job.created_at,
        input.job.updated_at,
        input.job.error?.code ?? null,
        input.job.error?.message ?? null,
        serializeDetails(input.job.error?.details)
      );

      const row = this.selectByIdempotency(input.job.account, input.job.idempotency_key);
      if (!row) {
        throw new Error('Failed to create or load draft job');
      }

      return {
        job: rowToJob(row),
        created: insertResult.changes === 1,
      };
    });

    return transaction();
  }

  async saveJob(job: DraftJob): Promise<void> {
    const db = this.requireDb();
    const existing = this.selectById(job.job_id);
    const expiresAt =
      existing?.idempotency_expires_at ||
      addDays(new Date(job.created_at), IDEMPOTENCY_WINDOW_DAYS).toISOString();

    db.prepare(
      `INSERT INTO jobs (
        job_id,
        artifact_id,
        account,
        status,
        media_id,
        idempotency_key,
        idempotency_expires_at,
        created_at,
        updated_at,
        error_code,
        error_message,
        error_details
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(job_id) DO UPDATE SET
        artifact_id = excluded.artifact_id,
        account = excluded.account,
        status = excluded.status,
        media_id = excluded.media_id,
        idempotency_key = excluded.idempotency_key,
        created_at = excluded.created_at,
        updated_at = excluded.updated_at,
        error_code = excluded.error_code,
        error_message = excluded.error_message,
        error_details = excluded.error_details`
    ).run(
      job.job_id,
      job.artifact_id,
      job.account,
      job.status,
      job.media_id ?? null,
      job.idempotency_key,
      expiresAt,
      job.created_at,
      job.updated_at,
      job.error?.code ?? null,
      job.error?.message ?? null,
      serializeDetails(job.error?.details)
    );
  }

  async getJobById(jobId: string): Promise<DraftJob | null> {
    const row = this.selectById(jobId);
    return row ? rowToJob(row) : null;
  }

  async getJobByArtifactId(artifactId: string): Promise<DraftJob | null> {
    const row = this.requireDb()
      .prepare(
        `SELECT *
         FROM jobs
         WHERE artifact_id = ?
         ORDER BY updated_at DESC
         LIMIT 1`
      )
      .get(artifactId) as JobRow | undefined;

    return row ? rowToJob(row) : null;
  }

  async checkIdempotency(idempotencyKey: string): Promise<DraftJob | null> {
    const row = this.requireDb()
      .prepare(
        `SELECT *
         FROM jobs
         WHERE idempotency_key = ?
           AND status = 'saved'
           AND idempotency_expires_at > ?
         ORDER BY updated_at DESC
         LIMIT 1`
      )
      .get(idempotencyKey, new Date().toISOString()) as JobRow | undefined;

    return row ? rowToJob(row) : null;
  }

  close(): void {
    this.db?.close();
    this.db = null;
  }

  checkHealth(): { ok: boolean; error?: string } {
    try {
      const db = this.requireDb();
      db.prepare('SELECT 1').get();
      db.prepare('BEGIN IMMEDIATE').run();
      db.prepare('ROLLBACK').run();
      return { ok: true };
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : 'Unknown SQLite health error',
      };
    }
  }

  getRuntimePath(): string {
    return this.runtimePath;
  }

  getDatabasePath(): string {
    return this.databasePath;
  }

  static generateIdempotencyKey = generateIdempotencyKey;

  private requireDb(): Database.Database {
    if (!this.db) {
      throw new Error('SQLiteJobStore is not initialized');
    }

    return this.db;
  }

  private selectById(jobId: string): JobRow | null {
    const row = this.requireDb()
      .prepare('SELECT * FROM jobs WHERE job_id = ?')
      .get(jobId) as JobRow | undefined;

    return row || null;
  }

  private selectByIdempotency(account: string, idempotencyKey: string): JobRow | null {
    const row = this.requireDb()
      .prepare('SELECT * FROM jobs WHERE account = ? AND idempotency_key = ?')
      .get(account, idempotencyKey) as JobRow | undefined;

    return row || null;
  }
}

function rowToJob(row: JobRow): DraftJob {
  return {
    job_id: row.job_id,
    artifact_id: row.artifact_id,
    account: row.account,
    status: row.status,
    media_id: row.media_id || undefined,
    idempotency_key: row.idempotency_key,
    error:
      row.error_code || row.error_message
        ? {
            code: row.error_code || 'unknown_error',
            message: row.error_message || 'Unknown error',
            details: parseDetails(row.error_details),
          }
        : undefined,
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

function serializeDetails(details: Record<string, unknown> | undefined): string | null {
  return details ? JSON.stringify(details) : null;
}

function parseDetails(details: string | null): Record<string, unknown> | undefined {
  if (!details) {
    return undefined;
  }

  try {
    return JSON.parse(details) as Record<string, unknown>;
  } catch {
    return { raw: details };
  }
}

function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setUTCDate(result.getUTCDate() + days);
  return result;
}
