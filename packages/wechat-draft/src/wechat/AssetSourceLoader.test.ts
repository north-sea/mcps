import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { AssetSourceError, AssetSourceLoader } from './AssetSourceLoader.js';

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
