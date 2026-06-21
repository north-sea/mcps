/**
 * JobStore
 *
 * Local JSONL-based storage for draft job status.
 * Supports append-only writes, query by job_id or artifact_id, and idempotency checks.
 */

import { promises as fs } from 'fs';
import { join, dirname } from 'path';
import { DraftJob } from '../schemas/tool-schemas.js';
import { homedir } from 'os';

const DEFAULT_RUNTIME_PATH = join(homedir(), '.wechat-draft');
const JOBS_SUBDIR = 'jobs';
const IDEMPOTENCY_LOOKBACK_DAYS = 7;

export interface JobStoreConfig {
  runtimePath?: string;
}

export class JobStore {
  private runtimePath: string;
  private jobsDir: string;

  constructor(config?: JobStoreConfig) {
    this.runtimePath = config?.runtimePath || process.env.WECHAT_DRAFT_RUNTIME_PATH || DEFAULT_RUNTIME_PATH;
    this.jobsDir = join(this.runtimePath, JOBS_SUBDIR);
  }

  /**
   * Initialize store (create directories if needed).
   */
  async initialize(): Promise<void> {
    await fs.mkdir(this.jobsDir, { recursive: true });
  }

  /**
   * Save job to JSONL (append-only).
   */
  async saveJob(job: DraftJob): Promise<void> {
    const filePath = this.getJobFilePath(new Date(job.created_at));
    const line = JSON.stringify(job) + '\n';

    // Ensure directory exists
    await fs.mkdir(dirname(filePath), { recursive: true });

    // Append to file
    await fs.appendFile(filePath, line, 'utf-8');
  }

  /**
   * Get job by job_id (searches recent days).
   */
  async getJobById(jobId: string, lookbackDays: number = 7): Promise<DraftJob | null> {
    const files = await this.getRecentJobFiles(lookbackDays);

    for (const file of files) {
      const jobs = await this.readJobsFromFile(file);
      const found = jobs.find((j) => j.job_id === jobId);
      if (found) {
        return found;
      }
    }

    return null;
  }

  /**
   * Get jobs by artifact_id (searches recent days, returns latest).
   */
  async getJobByArtifactId(artifactId: string, lookbackDays: number = 7): Promise<DraftJob | null> {
    const files = await this.getRecentJobFiles(lookbackDays);
    let latestJob: DraftJob | null = null;

    for (const file of files) {
      const jobs = await this.readJobsFromFile(file);
      for (const job of jobs) {
        if (job.artifact_id === artifactId) {
          if (!latestJob || new Date(job.created_at) > new Date(latestJob.created_at)) {
            latestJob = job;
          }
        }
      }
    }

    return latestJob;
  }

  /**
   * Check idempotency: return existing saved job if idempotency_key matches.
   */
  async checkIdempotency(idempotencyKey: string, lookbackDays: number = IDEMPOTENCY_LOOKBACK_DAYS): Promise<DraftJob | null> {
    const files = await this.getRecentJobFiles(lookbackDays);

    for (const file of files) {
      const jobs = await this.readJobsFromFile(file);
      const found = jobs.find((j) => j.idempotency_key === idempotencyKey && j.status === 'saved');
      if (found) {
        return found;
      }
    }

    return null;
  }

  /**
   * Get job file path for a given date.
   */
  private getJobFilePath(date: Date): string {
    const dateStr = this.formatDate(date);
    return join(this.jobsDir, `${dateStr}.jsonl`);
  }

  /**
   * Get recent job files (sorted newest first).
   */
  private async getRecentJobFiles(days: number): Promise<string[]> {
    const files: string[] = [];
    const today = new Date();

    for (let i = 0; i < days; i++) {
      const date = new Date(today);
      date.setDate(date.getDate() - i);
      const filePath = this.getJobFilePath(date);

      try {
        await fs.access(filePath);
        files.push(filePath);
      } catch {
        // File doesn't exist, skip
      }
    }

    return files;
  }

  /**
   * Read all jobs from a JSONL file.
   */
  private async readJobsFromFile(filePath: string): Promise<DraftJob[]> {
    try {
      const content = await fs.readFile(filePath, 'utf-8');
      const lines = content.trim().split('\n').filter((line) => line.length > 0);

      return lines.map((line) => {
        try {
          return JSON.parse(line) as DraftJob;
        } catch {
          // Skip invalid lines
          return null;
        }
      }).filter((job): job is DraftJob => job !== null);
    } catch (error) {
      // File read error (e.g., permission denied)
      return [];
    }
  }

  /**
   * Format date as YYYY-MM-DD.
   */
  private formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  /**
   * Generate default idempotency key from account and artifact_id.
   */
  static generateIdempotencyKey(account: string, artifactId: string): string {
    return `${account}:${artifactId}`;
  }
}
