#!/usr/bin/env node
/**
 * Test HermesDbClient integration with hermes-db MCP
 */

import { HermesDbClient } from './dist/hermes/HermesDbClient.js';

// Read auth token from environment
const authToken = process.env.HERMES_DB_AUTH_TOKEN;
if (!authToken) {
  console.error('❌ HERMES_DB_AUTH_TOKEN not set');
  console.error('Usage: HERMES_DB_AUTH_TOKEN=your_token node test-hermes-client.mjs');
  process.exit(1);
}

const baseUrl = process.env.HERMES_DB_BASE_URL || 'http://nas.local:8765';

const client = new HermesDbClient(baseUrl, 10000, authToken);

console.log('Testing HermesDbClient...');
console.log(`Base URL: ${baseUrl}\n`);

async function runTests() {
  // Test 1: Health check
  console.log('1. Health check:');
  try {
    const health = await client.health();
    console.log('✅ Result:', JSON.stringify(health, null, 2));
  } catch (error) {
    console.log('❌ Error:', error.message);
  }

  // Test 2: Get artifact (non-existent)
  console.log('\n2. Get artifact (non-existent):');
  try {
    const artifact = await client.getArtifact('test_artifact_not_exist');
    console.log('✅ Result:', artifact === null ? 'null (as expected)' : JSON.stringify(artifact, null, 2));
  } catch (error) {
    console.log('❌ Error:', error.message);
  }

  // Test 3: Get artifact (try with a real artifact_id if you have one)
  const testArtifactId = process.env.TEST_ARTIFACT_ID;
  if (testArtifactId) {
    console.log(`\n3. Get artifact (${testArtifactId}):`);
    try {
      const artifact = await client.getArtifact(testArtifactId);
      if (artifact) {
        console.log('✅ Found artifact:');
        console.log(`   - artifact_id: ${artifact.artifact_id}`);
        console.log(`   - run_id: ${artifact.run_id}`);
        console.log(`   - stage: ${artifact.stage}`);
        console.log(`   - type: ${artifact.type}`);
        console.log(`   - title: ${artifact.metadata?.title || 'N/A'}`);
      } else {
        console.log('✅ Result: null (artifact not found)');
      }
    } catch (error) {
      console.log('❌ Error:', error.message);
    }
  } else {
    console.log('\n3. Get artifact (skipped - set TEST_ARTIFACT_ID to test)');
  }

  console.log('\nTests complete.');
}

runTests().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
