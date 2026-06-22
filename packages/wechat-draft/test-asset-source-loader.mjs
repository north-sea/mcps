/**
 * Manual test for AssetSourceLoader
 * Tests core functionality: local file, remote URL, size/format guards
 */

import { AssetSourceLoader } from './dist/wechat/AssetSourceLoader.js';
import { writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';

const TEST_DIR = './.test-assets';
const loader = new AssetSourceLoader();

// Test utilities
let testCount = 0;
let passCount = 0;

function assert(condition, message) {
  testCount++;
  if (condition) {
    passCount++;
    console.log(`✅ PASS: ${message}`);
  } else {
    console.error(`❌ FAIL: ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  }
}

async function assertThrows(fn, expectedCode, message) {
  testCount++;
  try {
    await fn();
    console.error(`❌ FAIL: ${message} (no error thrown)`);
  } catch (error) {
    if (error.code === expectedCode) {
      passCount++;
      console.log(`✅ PASS: ${message} (error code: ${expectedCode})`);
    } else {
      console.error(`❌ FAIL: ${message} (got error code: ${error.code}, expected: ${expectedCode})`);
      throw error;
    }
  }
}

// Setup test assets
function setup() {
  console.log('\n📦 Setting up test assets...\n');

  try {
    rmSync(TEST_DIR, { recursive: true, force: true });
  } catch {}

  mkdirSync(TEST_DIR, { recursive: true });

  // Create a small fake JPEG (valid size for both body and cover)
  const smallJpeg = Buffer.alloc(1024); // 1KB
  smallJpeg[0] = 0xFF;
  smallJpeg[1] = 0xD8;
  writeFileSync(join(TEST_DIR, 'small.jpg'), smallJpeg);

  // Create a 100KB fake JPEG (valid for body, too large for cover)
  const largeJpeg = Buffer.alloc(100 * 1024); // 100KB
  largeJpeg[0] = 0xFF;
  largeJpeg[1] = 0xD8;
  writeFileSync(join(TEST_DIR, 'large.jpg'), largeJpeg);

  // Create a 2MB fake JPEG (too large for both)
  const hugeJpeg = Buffer.alloc(2 * 1024 * 1024); // 2MB
  hugeJpeg[0] = 0xFF;
  hugeJpeg[1] = 0xD8;
  writeFileSync(join(TEST_DIR, 'huge.jpg'), hugeJpeg);

  // Create a fake PNG
  const fakePng = Buffer.alloc(1024);
  fakePng[0] = 0x89;
  fakePng[1] = 0x50;
  writeFileSync(join(TEST_DIR, 'small.png'), fakePng);
}

function cleanup() {
  console.log('\n🧹 Cleaning up test assets...\n');
  try {
    rmSync(TEST_DIR, { recursive: true, force: true });
  } catch {}
}

// Tests
async function testLocalPathBodyImage() {
  console.log('\n--- Test: Local Path - Body Image ---\n');

  const result = await loader.load({
    usage: 'body_image',
    source_type: 'local_path',
    source: join(TEST_DIR, 'small.jpg'),
  });

  assert(result.sizeBytes === 1024, 'Size should be 1024 bytes');
  assert(result.mimeType === 'image/jpeg', 'MIME should be image/jpeg');
  assert(result.filename === 'small.jpg', 'Filename should be small.jpg');
  assert(result.bytes instanceof Uint8Array, 'Bytes should be Uint8Array');
}

async function testLocalPathCoverImage() {
  console.log('\n--- Test: Local Path - Cover Image (within 64KB) ---\n');

  const result = await loader.load({
    usage: 'cover_image',
    source_type: 'local_path',
    source: join(TEST_DIR, 'small.jpg'),
  });

  assert(result.sizeBytes === 1024, 'Size should be 1024 bytes');
  assert(result.mimeType === 'image/jpeg', 'MIME should be image/jpeg');
}

async function testLocalPathCoverImageTooLarge() {
  console.log('\n--- Test: Local Path - Cover Image exceeds 64KB ---\n');

  await assertThrows(
    () => loader.load({
      usage: 'cover_image',
      source_type: 'local_path',
      source: join(TEST_DIR, 'large.jpg'),
    }),
    'ASSET_SIZE_EXCEEDED',
    'Should reject cover image > 64KB'
  );
}

async function testLocalPathBodyImageTooLarge() {
  console.log('\n--- Test: Local Path - Body Image exceeds 1MB ---\n');

  await assertThrows(
    () => loader.load({
      usage: 'body_image',
      source_type: 'local_path',
      source: join(TEST_DIR, 'huge.jpg'),
    }),
    'ASSET_SIZE_EXCEEDED',
    'Should reject body image > 1MB'
  );
}

async function testLocalPathPngForBodyImage() {
  console.log('\n--- Test: Local Path - PNG for Body Image ---\n');

  const result = await loader.load({
    usage: 'body_image',
    source_type: 'local_path',
    source: join(TEST_DIR, 'small.png'),
  });

  assert(result.mimeType === 'image/png', 'MIME should be image/png');
}

async function testLocalPathPngForCoverImageRejected() {
  console.log('\n--- Test: Local Path - PNG for Cover Image (should reject) ---\n');

  await assertThrows(
    () => loader.load({
      usage: 'cover_image',
      source_type: 'local_path',
      source: join(TEST_DIR, 'small.png'),
    }),
    'ASSET_FORMAT_UNSUPPORTED',
    'Should reject PNG for cover_image (WeChat thumb requires JPG)'
  );
}

async function testLocalPathNotFound() {
  console.log('\n--- Test: Local Path - File Not Found ---\n');

  await assertThrows(
    () => loader.load({
      usage: 'body_image',
      source_type: 'local_path',
      source: join(TEST_DIR, 'nonexistent.jpg'),
    }),
    'ASSET_FILE_NOT_READABLE',
    'Should reject nonexistent file'
  );
}

async function testRemoteUrlBasic() {
  console.log('\n--- Test: Remote URL - Basic fetch ---\n');

  // Use a real small image URL for this test
  const result = await loader.load({
    usage: 'body_image',
    source_type: 'remote_url',
    source: 'https://httpbin.org/image/jpeg',
  });

  assert(result.bytes.length > 0, 'Should fetch bytes from remote URL');
  assert(result.mimeType.includes('image'), 'MIME should be image type');
}

async function testRemoteUrlInvalidProtocol() {
  console.log('\n--- Test: Remote URL - Invalid protocol ---\n');

  await assertThrows(
    () => loader.load({
      usage: 'body_image',
      source_type: 'remote_url',
      source: 'ftp://example.com/image.jpg',
    }),
    'ASSET_SOURCE_INVALID',
    'Should reject non-http(s) protocol'
  );
}

async function testRemoteUrl404() {
  console.log('\n--- Test: Remote URL - 404 Not Found ---\n');

  await assertThrows(
    () => loader.load({
      usage: 'body_image',
      source_type: 'remote_url',
      source: 'https://httpbin.org/status/404',
    }),
    'ASSET_REMOTE_URL_FETCH_FAILED',
    'Should reject 404 response'
  );
}

// Run all tests
async function runTests() {
  console.log('🧪 AssetSourceLoader Test Suite\n');
  console.log('='.repeat(50));

  setup();

  try {
    await testLocalPathBodyImage();
    await testLocalPathCoverImage();
    await testLocalPathCoverImageTooLarge();
    await testLocalPathBodyImageTooLarge();
    await testLocalPathPngForBodyImage();
    await testLocalPathPngForCoverImageRejected();
    await testLocalPathNotFound();
    await testRemoteUrlBasic();
    await testRemoteUrlInvalidProtocol();
    await testRemoteUrl404();

    console.log('\n' + '='.repeat(50));
    console.log(`\n✅ All tests passed: ${passCount}/${testCount}\n`);
  } catch (error) {
    console.log('\n' + '='.repeat(50));
    console.error(`\n❌ Tests failed: ${passCount}/${testCount} passed\n`);
    console.error('Error:', error.message);
    process.exit(1);
  } finally {
    cleanup();
  }
}

runTests();
