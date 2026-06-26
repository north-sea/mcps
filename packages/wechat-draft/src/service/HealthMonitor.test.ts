import test from 'node:test';
import assert from 'node:assert/strict';
import { HealthMonitor, sanitizeHealthError } from './HealthMonitor.js';

test('HealthMonitor returns ok when local checks and cached external checks are healthy', async () => {
  const monitor = createMonitor({
    runtimeOk: true,
    sqliteOk: true,
    adapterOk: true,
    hermesOk: true,
  });

  const snapshot = await monitor.getSnapshot();

  assert.equal(snapshot.status, 'ok');
  assert.equal(snapshot.version, '0.2.0');
  assert.equal(snapshot.checks.config_loaded, true);
  assert.equal(snapshot.checks.runtime_writable, true);
  assert.equal(snapshot.checks.sqlite_ready, true);
  assert.equal(snapshot.checks.adapter_reachable, true);
  assert.equal(snapshot.checks.hermes_db_reachable, true);
});

test('HealthMonitor returns degraded when only external dependencies are unhealthy', async () => {
  const monitor = createMonitor({
    runtimeOk: true,
    sqliteOk: true,
    adapterOk: false,
    hermesOk: true,
    adapterError: 'Adapter failed at http://adapter.local/path?token=secret',
  });

  const snapshot = await monitor.getSnapshot();

  assert.equal(snapshot.status, 'degraded');
  assert.equal(snapshot.checks.adapter_reachable, false);
  assert.equal(
    snapshot.checks.errors?.adapter_reachable,
    'Adapter failed at http://adapter.local/path'
  );
});

test('HealthMonitor returns unhealthy when local runtime or sqlite checks fail', async () => {
  const runtimeFailure = await createMonitor({
    runtimeOk: false,
    sqliteOk: true,
    adapterOk: true,
    hermesOk: true,
    runtimeError: 'EACCES: permission denied',
  }).getSnapshot();
  const sqliteFailure = await createMonitor({
    runtimeOk: true,
    sqliteOk: false,
    adapterOk: true,
    hermesOk: true,
    sqliteError: 'database is locked',
  }).getSnapshot();

  assert.equal(runtimeFailure.status, 'unhealthy');
  assert.equal(runtimeFailure.checks.runtime_writable, false);
  assert.equal(sqliteFailure.status, 'unhealthy');
  assert.equal(sqliteFailure.checks.sqlite_ready, false);
});

test('HealthMonitor getSnapshot does not run external probes', async () => {
  let adapterProbeCalls = 0;
  let hermesProbeCalls = 0;
  const monitor = new HealthMonitor({
    runtimePath: '/tmp/runtime',
    runtimeWritableCheck: async () => ({ ok: true }),
    sqliteCheck: () => ({ ok: true }),
    adapterProbe: async () => {
      adapterProbeCalls += 1;
      return { ok: true };
    },
    hermesDbProbe: async () => {
      hermesProbeCalls += 1;
      return { ok: true };
    },
    initialExternalChecks: {
      adapter: { ok: true },
      hermesDb: { ok: true },
    },
  });

  await monitor.getSnapshot();

  assert.equal(adapterProbeCalls, 0);
  assert.equal(hermesProbeCalls, 0);
});

test('HealthMonitor refreshExternalChecks updates cached dependency status', async () => {
  const monitor = new HealthMonitor({
    runtimePath: '/tmp/runtime',
    runtimeWritableCheck: async () => ({ ok: true }),
    sqliteCheck: () => ({ ok: true }),
    adapterProbe: async () => ({ ok: true }),
    hermesDbProbe: async () => ({ ok: false, error: 'Hermes down' }),
  });

  await monitor.refreshExternalChecks();
  const snapshot = await monitor.getSnapshot();

  assert.equal(snapshot.status, 'degraded');
  assert.equal(snapshot.checks.adapter_reachable, true);
  assert.equal(snapshot.checks.hermes_db_reachable, false);
  assert.equal(snapshot.checks.errors?.hermes_db_reachable, 'Hermes down');
});

test('sanitizeHealthError redacts bearer tokens, query secrets, and long messages', () => {
  const sanitized = sanitizeHealthError(
    'Bearer abc.def http://svc.local/path?token=secret&ok=1 '.repeat(10),
    120
  );

  assert.equal(sanitized.includes('abc.def'), false);
  assert.equal(sanitized.includes('token=secret'), false);
  assert.equal(sanitized.includes('Bearer <redacted>'), true);
  assert.equal(sanitized.length <= 123, true);
});

function createMonitor(options: {
  runtimeOk: boolean;
  sqliteOk: boolean;
  adapterOk: boolean;
  hermesOk: boolean;
  runtimeError?: string;
  sqliteError?: string;
  adapterError?: string;
  hermesError?: string;
}): HealthMonitor {
  return new HealthMonitor({
    runtimePath: '/tmp/runtime',
    runtimeWritableCheck: async () => ({
      ok: options.runtimeOk,
      error: options.runtimeError,
    }),
    sqliteCheck: () => ({
      ok: options.sqliteOk,
      error: options.sqliteError,
    }),
    initialExternalChecks: {
      adapter: {
        ok: options.adapterOk,
        error: options.adapterError,
      },
      hermesDb: {
        ok: options.hermesOk,
        error: options.hermesError,
      },
    },
  });
}
