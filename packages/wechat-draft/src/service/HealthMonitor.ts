import { promises as fs } from 'node:fs';
import { join } from 'node:path';
import { SERVICE_VERSION } from '../version.js';

export type HealthStatus = 'ok' | 'degraded' | 'unhealthy';

export interface HealthCheckResult {
  ok: boolean | null;
  error?: string;
  checked_at?: string;
}

export interface HealthSnapshot {
  status: HealthStatus;
  version: string;
  checks: {
    config_loaded: boolean;
    runtime_writable: boolean;
    sqlite_ready: boolean;
    adapter_reachable: boolean | null;
    hermes_db_reachable: boolean | null;
    runtime_path?: string;
    errors?: Record<string, string>;
  };
}

export interface HealthMonitorOptions {
  version?: string;
  runtimePath: string;
  configLoaded?: boolean;
  probeIntervalMs?: number;
  runtimeWritableCheck?: () => Promise<HealthCheckResult>;
  sqliteCheck: () => HealthCheckResult | Promise<HealthCheckResult>;
  adapterProbe?: () => Promise<HealthCheckResult>;
  hermesDbProbe?: () => Promise<HealthCheckResult>;
  initialExternalChecks?: {
    adapter?: HealthCheckResult;
    hermesDb?: HealthCheckResult;
  };
}

const DEFAULT_PROBE_INTERVAL_MS = 30_000;

export class HealthMonitor {
  private readonly version: string;
  private readonly runtimePath: string;
  private readonly configLoaded: boolean;
  private readonly probeIntervalMs: number;
  private readonly runtimeWritableCheck: () => Promise<HealthCheckResult>;
  private readonly sqliteCheck: () => HealthCheckResult | Promise<HealthCheckResult>;
  private readonly adapterProbe?: () => Promise<HealthCheckResult>;
  private readonly hermesDbProbe?: () => Promise<HealthCheckResult>;
  private interval: NodeJS.Timeout | null = null;
  private adapterCheck: HealthCheckResult;
  private hermesDbCheck: HealthCheckResult;

  constructor(options: HealthMonitorOptions) {
    this.version = options.version || SERVICE_VERSION;
    this.runtimePath = options.runtimePath;
    this.configLoaded = options.configLoaded ?? true;
    this.probeIntervalMs = options.probeIntervalMs || DEFAULT_PROBE_INTERVAL_MS;
    this.runtimeWritableCheck =
      options.runtimeWritableCheck || (() => checkRuntimeWritable(this.runtimePath));
    this.sqliteCheck = options.sqliteCheck;
    this.adapterProbe = options.adapterProbe;
    this.hermesDbProbe = options.hermesDbProbe;
    this.adapterCheck = options.initialExternalChecks?.adapter || { ok: null };
    this.hermesDbCheck = options.initialExternalChecks?.hermesDb || { ok: null };
  }

  start(): void {
    void this.refreshExternalChecks();

    if (this.interval) {
      return;
    }

    this.interval = setInterval(() => {
      void this.refreshExternalChecks();
    }, this.probeIntervalMs);
    this.interval.unref?.();
  }

  stop(): void {
    if (!this.interval) {
      return;
    }

    clearInterval(this.interval);
    this.interval = null;
  }

  async refreshExternalChecks(): Promise<void> {
    const [adapter, hermesDb] = await Promise.all([
      runProbe(this.adapterProbe),
      runProbe(this.hermesDbProbe),
    ]);

    this.adapterCheck = adapter;
    this.hermesDbCheck = hermesDb;
  }

  async getSnapshot(): Promise<HealthSnapshot> {
    const runtime = await this.runtimeWritableCheck();
    const sqlite = await this.sqliteCheck();
    const errors = collectErrors({
      runtime_writable: runtime,
      sqlite_ready: sqlite,
      adapter_reachable: this.adapterCheck,
      hermes_db_reachable: this.hermesDbCheck,
    });
    const localOk = this.configLoaded && runtime.ok === true && sqlite.ok === true;
    const externalOk =
      this.adapterCheck.ok === true && this.hermesDbCheck.ok === true;

    return {
      status: !localOk ? 'unhealthy' : externalOk ? 'ok' : 'degraded',
      version: this.version,
      checks: {
        config_loaded: this.configLoaded,
        runtime_writable: runtime.ok === true,
        sqlite_ready: sqlite.ok === true,
        adapter_reachable: this.adapterCheck.ok,
        hermes_db_reachable: this.hermesDbCheck.ok,
        runtime_path: this.runtimePath,
        ...(Object.keys(errors).length > 0 ? { errors } : {}),
      },
    };
  }
}

export async function checkRuntimeWritable(runtimePath: string): Promise<HealthCheckResult> {
  const probePath = join(runtimePath, `.healthcheck-${process.pid}-${Date.now()}`);

  try {
    await fs.writeFile(probePath, 'ok', 'utf8');
    await fs.unlink(probePath);
    return { ok: true };
  } catch (error) {
    return {
      ok: false,
      error: sanitizeHealthError(
        error instanceof Error ? error.message : 'Unknown runtime health error'
      ),
    };
  }
}

export function sanitizeHealthError(value: string, maxLength: number = 200): string {
  const redacted = value
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, 'Bearer <redacted>')
    .replace(/([?&](?:token|access_token|auth|authorization|key|secret)=)[^&\s]+/gi, '$1<redacted>')
    .replace(/https?:\/\/[^\s]+/gi, (match) => {
      try {
        const url = new URL(match);
        url.username = '';
        url.password = '';
        url.search = '';
        return url.toString();
      } catch {
        return '<redacted-url>';
      }
    });

  return redacted.length > maxLength ? `${redacted.slice(0, maxLength)}...` : redacted;
}

async function runProbe(
  probe: (() => Promise<HealthCheckResult>) | undefined
): Promise<HealthCheckResult> {
  if (!probe) {
    return { ok: null };
  }

  try {
    const result = await probe();
    return {
      ok: result.ok,
      checked_at: new Date().toISOString(),
      ...(result.error ? { error: sanitizeHealthError(result.error) } : {}),
    };
  } catch (error) {
    return {
      ok: false,
      checked_at: new Date().toISOString(),
      error: sanitizeHealthError(error instanceof Error ? error.message : 'Unknown probe error'),
    };
  }
}

function collectErrors(checks: Record<string, HealthCheckResult>): Record<string, string> {
  const errors: Record<string, string> = {};

  for (const [name, result] of Object.entries(checks)) {
    if (result.error) {
      errors[name] = sanitizeHealthError(result.error);
    }
  }

  return errors;
}
