import type { DraftJob, DraftJobStatus } from '../schemas/tool-schemas.js';

export interface CreateOrGetJobInput {
  job: DraftJob;
  now?: Date;
}

export interface CreateOrGetJobResult {
  job: DraftJob;
  created: boolean;
}

export interface DraftJobStore {
  initialize(): Promise<void>;
  createOrGetJob(input: CreateOrGetJobInput): Promise<CreateOrGetJobResult>;
  saveJob(job: DraftJob): Promise<void>;
  getJobById(jobId: string): Promise<DraftJob | null>;
  getJobByArtifactId(artifactId: string): Promise<DraftJob | null>;
  checkIdempotency(idempotencyKey: string): Promise<DraftJob | null>;
}

export const TERMINAL_JOB_STATUSES: DraftJobStatus[] = [
  'saved',
  'failed',
  'invalid_artifact',
  'needs_operator_action',
];

export function generateIdempotencyKey(account: string, artifactId: string): string {
  return `${account}:${artifactId}`;
}
