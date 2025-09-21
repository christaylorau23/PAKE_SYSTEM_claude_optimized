#!/usr/bin/env node
/**
 * Test script for PAKE+ Obsidian Bridge API
 * Tests all major endpoints and functionality
 */

const axios = require('axios');
const { v4: uuidv4 } = require('uuid');

const API_BASE = process.env.API_BASE || 'http://localhost:3000';
const TEST_TIMEOUT = 10000;

class APITester {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.testResults = [];
    this.createdNotes = [];
  }

  async runTest(name, testFunction) {
    console.log(`\n🧪 Testing: ${name}`);
    try {
      const startTime = Date.now();
      await testFunction();
      const duration = Date.now() - startTime;
      console.log(`✅ PASSED: ${name} (${duration}ms)`);
      this.testResults.push({ name, status: 'PASSED', duration });
    } catch (error) {
      console.log(`❌ FAILED: ${name}`);
      console.log(`   Error: ${error.message}`);
      this.testResults.push({ name, status: 'FAILED', error: error.message });
    }
  }

  async testHealthCheck() {
    const response = await axios.get(`${this.baseUrl}/health`, {
      timeout: TEST_TIMEOUT,
    });

    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    if (!response.data.status || response.data.status !== 'healthy') {
      throw new Error('Health check returned unhealthy status');
    }

    console.log(`   Health check response:`, response.data);
  }

  async testCreateNote() {
    const testNote = {
      title: 'API Test Note',
      content: `# API Test Note

This is a test note created via the PAKE+ API.

## Test Details
- Created: ${new Date().toISOString()}
- Purpose: API functionality verification
- Test UUID: ${uuidv4()}

## Content Validation
This note contains structured content to test:
- Markdown formatting
- Multiple paragraphs
- List items
- Headers

This should be processed correctly by the confidence scoring engine.`,
      type: 'note',
      source_uri: 'local://api-test',
      tags: ['test', 'api', 'automated'],
      confidence_score: 0.7,
      human_notes: 'Created by automated API test suite',
    };

    const response = await axios.post(`${this.baseUrl}/api/notes`, testNote, {
      timeout: TEST_TIMEOUT,
    });

    if (response.status !== 201) {
      throw new Error(`Expected status 201, got ${response.status}`);
    }

    if (!response.data.success || !response.data.pake_id) {
      throw new Error('Create note response missing required fields');
    }

    this.createdNotes.push(response.data.pake_id);
    console.log(`   Created note with PAKE ID: ${response.data.pake_id}`);
    console.log(`   File path: ${response.data.filepath}`);

    return response.data.pake_id;
  }

  async testGetNote(pakeId) {
    const response = await axios.get(`${this.baseUrl}/api/notes/${pakeId}`, {
      timeout: TEST_TIMEOUT,
    });

    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    const note = response.data;
    if (!note.pake_id || !note.content) {
      throw new Error('Get note response missing required fields');
    }

    if (note.pake_id !== pakeId) {
      throw new Error(
        `PAKE ID mismatch: expected ${pakeId}, got ${note.pake_id}`
      );
    }

    console.log(`   Retrieved note: ${note.content.split('\n')[0]}`);
    return note;
  }

  async testUpdateNote(pakeId) {
    const updates = {
      confidence_score: 0.85,
      human_notes: 'Updated by API test - verification added',
      tags: ['test', 'api', 'automated', 'updated'],
    };

    const response = await axios.patch(
      `${this.baseUrl}/api/notes/${pakeId}`,
      updates,
      {
        timeout: TEST_TIMEOUT,
      }
    );

    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    if (!response.data.success) {
      throw new Error('Update note response indicates failure');
    }

    console.log(
      `   Updated fields: ${response.data.updated_fields.join(', ')}`
    );
  }

  async testVerifyNote(pakeId) {
    const verificationData = {
      verification_status: 'verified',
      human_notes: 'Verified via API test - all checks passed',
    };

    const response = await axios.patch(
      `${this.baseUrl}/api/notes/${pakeId}/verify`,
      verificationData,
      {
        timeout: TEST_TIMEOUT,
      }
    );

    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    if (response.data.verification_status !== 'verified') {
      throw new Error('Verification did not succeed');
    }

    console.log(`   Verification status: ${response.data.verification_status}`);
  }

  async testSearchNotes() {
    const searchQuery = {
      query: 'API test',
      filters: {
        semantic: true,
        min_confidence: 0.5,
      },
      limit: 10,
    };

    const response = await axios.post(
      `${this.baseUrl}/api/search`,
      searchQuery,
      {
        timeout: TEST_TIMEOUT,
      }
    );

    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    if (!Array.isArray(response.data)) {
      throw new Error('Search response should be an array');
    }

    console.log(`   Found ${response.data.length} matching notes`);

    // Verify our test note appears in results
    const testNoteFound = response.data.some(note =>
      this.createdNotes.includes(note.pake_id)
    );

    if (!testNoteFound && response.data.length > 0) {
      console.log(`   Warning: Test note not found in search results`);
    } else if (testNoteFound) {
      console.log(`   ✓ Test note found in search results`);
    }
  }

  async testConfidenceQuery() {
    const threshold = 0.6;
    const response = await axios.get(
      `${this.baseUrl}/api/notes/confidence/${threshold}?limit=5`,
      {
        timeout: TEST_TIMEOUT,
      }
    );

    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    if (!response.data.notes || !Array.isArray(response.data.notes)) {
      throw new Error('Confidence query response missing notes array');
    }

    // Verify all returned notes meet the threshold
    const allAboveThreshold = response.data.notes.every(
      note => note.confidence_score >= threshold
    );

    if (!allAboveThreshold) {
      throw new Error('Some returned notes below confidence threshold');
    }

    console.log(
      `   Found ${response.data.count} notes with confidence >= ${threshold}`
    );
  }

  async testListNotes() {
    const params = {
      page: 1,
      limit: 5,
      sort_by: 'modified',
      order: 'desc',
    };

    const queryString = new URLSearchParams(params).toString();
    const response = await axios.get(
      `${this.baseUrl}/api/notes?${queryString}`,
      {
        timeout: TEST_TIMEOUT,
      }
    );

    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    if (!response.data.notes || !response.data.pagination) {
      throw new Error('List notes response missing required fields');
    }

    console.log(
      `   Listed ${response.data.notes.length} notes (page 1 of ${response.data.pagination.pages})`
    );
    console.log(`   Total notes: ${response.data.pagination.total}`);
  }

  async testCreateConnection() {
    if (this.createdNotes.length < 2) {
      // Create a second note for connection testing
      const secondNote = {
        title: 'API Connection Test Note',
        content:
          '# Connection Test\n\nThis note tests connection functionality.',
        type: 'note',
        source_uri: 'local://api-connection-test',
        tags: ['test', 'connection'],
      };

      const response = await axios.post(
        `${this.baseUrl}/api/notes`,
        secondNote
      );
      this.createdNotes.push(response.data.pake_id);
    }

    const connectionData = {
      source_id: this.createdNotes[0],
      target_id: this.createdNotes[1],
      connection_type: 'relates_to',
    };

    const response = await axios.post(
      `${this.baseUrl}/api/connections`,
      connectionData,
      {
        timeout: TEST_TIMEOUT,
      }
    );

    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    if (!response.data.success) {
      throw new Error('Connection creation failed');
    }

    console.log(
      `   Created connection: ${connectionData.source_id} -> ${connectionData.target_id}`
    );
  }

  async testStatistics() {
    const response = await axios.get(`${this.baseUrl}/api/stats`, {
      timeout: TEST_TIMEOUT,
    });

    if (response.status !== 200) {
      throw new Error(`Expected status 200, got ${response.status}`);
    }

    const stats = response.data;
    if (typeof stats.total_notes !== 'number' || !stats.by_type) {
      throw new Error('Statistics response missing required fields');
    }

    console.log(`   Vault contains ${stats.total_notes} total notes`);
    console.log(
      `   Average confidence: ${stats.avg_confidence?.toFixed(3) || 'N/A'}`
    );
    console.log(`   Types: ${Object.keys(stats.by_type).join(', ')}`);
  }

  async testErrorHandling() {
    // Test 404 for non-existent note
    try {
      await axios.get(`${this.baseUrl}/api/notes/non-existent-id`);
      throw new Error('Expected 404 for non-existent note');
    } catch (error) {
      if (error.response?.status !== 404) {
        throw new Error(
          `Expected 404, got ${error.response?.status || 'no response'}`
        );
      }
    }

    // Test validation error for missing required fields
    try {
      await axios.post(`${this.baseUrl}/api/notes`, {
        title: 'Missing Content',
      });
      throw new Error('Expected 400 for missing content');
    } catch (error) {
      if (error.response?.status !== 400) {
        throw new Error(
          `Expected 400, got ${error.response?.status || 'no response'}`
        );
      }
    }

    console.log(`   ✓ Error handling working correctly`);
  }

  async runAllTests() {
    console.log('🚀 Starting PAKE+ API Test Suite');
    console.log(`📡 Testing API at: ${this.baseUrl}`);

    try {
      await this.runTest('Health Check', () => this.testHealthCheck());

      let testNoteId;
      await this.runTest('Create Note', async () => {
        testNoteId = await this.testCreateNote();
      });

      if (testNoteId) {
        await this.runTest('Get Note', () => this.testGetNote(testNoteId));
        await this.runTest('Update Note', () =>
          this.testUpdateNote(testNoteId)
        );
        await this.runTest('Verify Note', () =>
          this.testVerifyNote(testNoteId)
        );
      }

      await this.runTest('Search Notes', () => this.testSearchNotes());
      await this.runTest('Confidence Query', () => this.testConfidenceQuery());
      await this.runTest('List Notes', () => this.testListNotes());
      await this.runTest('Create Connection', () =>
        this.testCreateConnection()
      );
      await this.runTest('Statistics', () => this.testStatistics());
      await this.runTest('Error Handling', () => this.testErrorHandling());
    } catch (error) {
      console.log(`\n💥 Test suite failed with error: ${error.message}`);
    }

    this.printSummary();
  }

  printSummary() {
    console.log('\n📊 Test Summary');
    console.log('================');

    const passed = this.testResults.filter(r => r.status === 'PASSED').length;
    const failed = this.testResults.filter(r => r.status === 'FAILED').length;
    const total = this.testResults.length;

    console.log(`Total Tests: ${total}`);
    console.log(`Passed: ${passed} ✅`);
    console.log(`Failed: ${failed} ❌`);
    console.log(`Success Rate: ${((passed / total) * 100).toFixed(1)}%`);

    if (failed > 0) {
      console.log('\n❌ Failed Tests:');
      this.testResults
        .filter(r => r.status === 'FAILED')
        .forEach(test => {
          console.log(`   • ${test.name}: ${test.error}`);
        });
    }

    if (this.createdNotes.length > 0) {
      console.log(`\n📝 Created test notes (PAKE IDs):`);
      this.createdNotes.forEach(id => console.log(`   • ${id}`));
      console.log('   These can be found in your vault for manual inspection.');
    }

    console.log('\n🎯 Test suite completed!');
  }
}

// Run tests if called directly
if (require.main === module) {
  const tester = new APITester(API_BASE);
  tester.runAllTests().catch(error => {
    console.error('Test suite failed:', error);
    process.exit(1);
  });
}

module.exports = APITester;
