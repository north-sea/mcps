import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { AssetSourceError, AssetSourceLoader, getAssetSourceConstraints } from './AssetSourceLoader.js';

test('AssetSourceLoader exposes constraints matching enforced guards', () => {
  const constraints = getAssetSourceConstraints('/assets');

  assert.equal(constraints.assets.body_image.max_bytes, 1024 * 1024);
  assert.deepEqual(constraints.assets.body_image.mime_types, ['image/jpeg', 'image/jpg', 'image/png']);
  assert.equal(constraints.assets.body_image.wechat_api, '/cgi-bin/media/uploadimg');
  assert.equal(constraints.assets.cover_image.max_bytes, 64 * 1024);
  assert.deepEqual(constraints.assets.cover_image.mime_types, ['image/jpeg', 'image/jpg']);
  assert.equal(constraints.assets.cover_image.media_type, 'thumb');
  assert.deepEqual(constraints.assets.local_path.accepted_path_prefixes, ['/assets']);
  assert.equal(constraints.assets.remote_url.enabled, true);
});

test('AssetSourceLoader loads local_path only under asset root', async () => {
  const { dir, cleanup } = await createTempDir();

  try {
    const filePath = join(dir, 'image.png');
    await writeFile(filePath, Buffer.from([1, 2, 3]));

    const loader = new AssetSourceLoader({ assetRoot: dir });
    const asset = await loader.load({
      usage: 'body_image',
      source_type: 'local_path',
      source: 'image.png',
    });

    assert.equal(asset.filename, 'image.png');
    assert.equal(asset.mimeType, 'image/png');
    assert.equal(asset.sizeBytes, 3);
  } finally {
    await cleanup();
  }
});

test('AssetSourceLoader preflights valid local assets', async () => {
  const { dir, cleanup } = await createTempDir();

  try {
    await writeFile(join(dir, 'image.png'), Buffer.from([1, 2, 3]));
    const loader = new AssetSourceLoader({ assetRoot: dir });

    const preflight = await loader.preflight({
      usage: 'body_image',
      source_type: 'local_path',
      source: 'image.png',
    });

    assert.equal(preflight.valid, true);
    assert.equal(preflight.upload_ready, true);
    assert.equal(preflight.filename, 'image.png');
    assert.equal(preflight.mime_type, 'image/png');
    assert.equal(preflight.size_bytes, 3);
    assert.deepEqual(preflight.issues, []);
    assert.equal(preflight.recommendations[0]?.action, 'none');
  } finally {
    await cleanup();
  }
});

test('AssetSourceLoader preflight returns accepted prefixes for local_path failures', async () => {
  const { dir, cleanup } = await createTempDir();

  try {
    const loader = new AssetSourceLoader({ assetRoot: dir });
    const preflight = await loader.preflight({
      usage: 'body_image',
      source_type: 'local_path',
      source: 'missing.png',
    });

    assert.equal(preflight.valid, false);
    assert.equal(preflight.upload_ready, false);
    assert.equal(preflight.source_diagnostics.readable, false);
    assert.deepEqual(preflight.source_diagnostics.accepted_path_prefixes, [dir]);
    assert.equal(preflight.recommendations[0]?.action, 'use_accepted_path_or_remote_url');
  } finally {
    await cleanup();
  }
});

test('AssetSourceLoader rejects local_path without asset root', async () => {
  const loader = new AssetSourceLoader({ assetRoot: '' });

  await assert.rejects(
    () =>
      loader.load({
        usage: 'body_image',
        source_type: 'local_path',
        source: '/tmp/image.png',
      }),
    (error) => isAssetError(error, 'ASSET_SOURCE_INVALID')
  );
});

test('AssetSourceLoader rejects local_path escapes from asset root', async () => {
  const { dir, cleanup } = await createTempDir();
  const { dir: outsideDir, cleanup: cleanupOutside } = await createTempDir();

  try {
    const outsideFile = join(outsideDir, 'escape.png');
    await writeFile(outsideFile, Buffer.from([1, 2, 3]));

    const loader = new AssetSourceLoader({ assetRoot: dir });

    await assert.rejects(
      () =>
        loader.load({
          usage: 'body_image',
          source_type: 'local_path',
          source: outsideFile,
        }),
      (error) => isAssetError(error, 'ASSET_SOURCE_INVALID')
    );
  } finally {
    await cleanup();
    await cleanupOutside();
  }
});

test('AssetSourceLoader loads remote_url over http(s)', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(Buffer.from([1, 2, 3]), {
      status: 200,
      headers: {
        'content-type': 'image/jpeg',
        'content-length': '3',
      },
    });

  try {
    const loader = new AssetSourceLoader();
    const asset = await loader.load({
      usage: 'cover_image',
      source_type: 'remote_url',
      source: 'https://example.com/cover.jpg',
    });

    assert.equal(asset.filename, 'cover.jpg');
    assert.equal(asset.mimeType, 'image/jpeg');
    assert.equal(asset.sizeBytes, 3);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('AssetSourceLoader preflights remote_url failures', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response('not found', {
      status: 404,
      statusText: 'Not Found',
    });

  try {
    const loader = new AssetSourceLoader();
    const preflight = await loader.preflight({
      usage: 'body_image',
      source_type: 'remote_url',
      source: 'https://example.com/missing.png',
    });

    assert.equal(preflight.valid, false);
    assert.equal(preflight.source_diagnostics.fetch_ok, false);
    assert.equal(preflight.source_diagnostics.status, 404);
    assert.equal(preflight.source_diagnostics.status_text, 'Not Found');
    assert.equal(preflight.recommendations[0]?.action, 'replace_asset');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('AssetSourceLoader enforces mime and cover size guards', async () => {
  const { dir, cleanup } = await createTempDir();

  try {
    const gifPath = join(dir, 'image.gif');
    const largeCoverPath = join(dir, 'large.jpg');
    await writeFile(gifPath, Buffer.from([1, 2, 3]));
    await writeFile(largeCoverPath, Buffer.alloc(64 * 1024 + 1));

    const loader = new AssetSourceLoader({ assetRoot: dir });

    await assert.rejects(
      () =>
        loader.load({
          usage: 'body_image',
          source_type: 'local_path',
          source: gifPath,
        }),
      (error) => isAssetError(error, 'ASSET_FORMAT_UNSUPPORTED')
    );

    await assert.rejects(
      () =>
        loader.load({
          usage: 'cover_image',
          source_type: 'local_path',
          source: largeCoverPath,
        }),
      (error) => isAssetError(error, 'ASSET_SIZE_EXCEEDED')
    );
  } finally {
    await cleanup();
  }
});

test('AssetSourceLoader preflight recommends transform for oversized cover', async () => {
  const { dir, cleanup } = await createTempDir();

  try {
    await writeFile(join(dir, 'large.jpg'), Buffer.alloc(64 * 1024 + 1));
    const loader = new AssetSourceLoader({ assetRoot: dir });

    const preflight = await loader.preflight({
      usage: 'cover_image',
      source_type: 'local_path',
      source: 'large.jpg',
    });

    assert.equal(preflight.valid, false);
    assert.equal(preflight.issues[0]?.code, 'ASSET_SIZE_EXCEEDED');
    assert.equal(preflight.recommendations[0]?.action, 'compress');
    assert.equal(preflight.recommendations[0]?.target_max_bytes, 64 * 1024);
    assert.equal(preflight.recommendations[0]?.supported_in_mvp, false);
  } finally {
    await cleanup();
  }
});

async function createTempDir(): Promise<{
  dir: string;
  cleanup: () => Promise<void>;
}> {
  const dir = await mkdtemp(join(tmpdir(), 'wechat-draft-assets-'));
  return {
    dir,
    cleanup: () => rm(dir, { recursive: true, force: true }),
  };
}

function isAssetError(error: unknown, code: string): boolean {
  return error instanceof AssetSourceError && error.code === code;
}
