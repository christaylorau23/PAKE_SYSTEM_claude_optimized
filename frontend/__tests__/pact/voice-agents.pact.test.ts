import { Pact } from '@pact-foundation/pact';
import { like, eachLike, regex } from '@pact-foundation/pact/dsl/matchers';
import axios from 'axios';

// Voice Agents API contract testing
describe('Voice Agents API Contract', () => {
  let provider: Pact;

  beforeAll(async () => {
    provider = new Pact({
      consumer: 'pake-frontend',
      provider: 'voice-agents-service',
      port: 8991,
      log: 'logs/pact.log',
      dir: 'pacts',
      logLevel: 'info',
    });

    await provider.setup();
  });

  afterAll(async () => {
    await provider.finalize();
  });

  afterEach(async () => {
    await provider.verify();
  });

  describe('GET /api/voice-agents', () => {
    it('should return a list of voice agents', async () => {
      // Arrange
      await provider.addInteraction({
        state: 'voice agents exist',
        uponReceiving: 'a request for voice agents',
        withRequest: {
          method: 'GET',
          path: '/api/voice-agents',
          headers: {
            Accept: 'application/json',
          },
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
          },
          body: {
            agents: eachLike({
              id: like('agent-123'),
              name: like('Customer Support Agent'),
              status: regex('active|inactive|training', 'active'),
              language: like('en-US'),
              voice: like('neural-female-1'),
              capabilities: eachLike('customer-support'),
              createdAt: regex(
                '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z',
                '2025-01-01T00:00:00Z'
              ),
              updatedAt: regex(
                '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z',
                '2025-01-01T00:00:00Z'
              ),
              metrics: {
                totalCalls: like(1542),
                successRate: like(0.95),
                avgResponseTime: like(1.2),
                satisfactionScore: like(4.7),
              },
            }),
            total: like(5),
            page: like(1),
            limit: like(10),
          },
        },
      });

      // Act
      const response = await axios.get(
        'http://localhost:8991/api/voice-agents'
      );

      // Assert
      expect(response.status).toBe(200);
      expect(response.data.agents).toBeInstanceOf(Array);
      expect(response.data.agents[0]).toHaveProperty('id');
      expect(response.data.agents[0]).toHaveProperty('name');
      expect(response.data.agents[0]).toHaveProperty('status');
      expect(response.data.agents[0]).toHaveProperty('metrics');
      expect(response.data.total).toBeGreaterThan(0);
    });
  });

  describe('POST /api/voice-agents', () => {
    it('should create a new voice agent', async () => {
      // Arrange
      const newAgent = {
        name: 'Sales Assistant Agent',
        language: 'en-US',
        voice: 'neural-male-1',
        capabilities: ['sales-support', 'lead-qualification'],
        configuration: {
          maxCallDuration: 1800,
          transferToHuman: true,
          knowledgeBase: 'sales-kb-v2',
        },
      };

      await provider.addInteraction({
        state: 'voice agent can be created',
        uponReceiving: 'a request to create a voice agent',
        withRequest: {
          method: 'POST',
          path: '/api/voice-agents',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
          body: newAgent,
        },
        willRespondWith: {
          status: 201,
          headers: {
            'Content-Type': 'application/json',
          },
          body: {
            id: like('agent-456'),
            ...newAgent,
            status: like('training'),
            createdAt: regex(
              '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z',
              '2025-01-01T00:00:00Z'
            ),
            updatedAt: regex(
              '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z',
              '2025-01-01T00:00:00Z'
            ),
            metrics: {
              totalCalls: like(0),
              successRate: like(0),
              avgResponseTime: like(0),
              satisfactionScore: like(0),
            },
          },
        },
      });

      // Act
      const response = await axios.post(
        'http://localhost:8991/api/voice-agents',
        newAgent
      );

      // Assert
      expect(response.status).toBe(201);
      expect(response.data).toHaveProperty('id');
      expect(response.data.name).toBe(newAgent.name);
      expect(response.data.status).toBe('training');
    });

    it('should return validation error for invalid agent data', async () => {
      // Arrange
      const invalidAgent = {
        name: '', // Invalid: empty name
        language: 'invalid-lang', // Invalid: unsupported language
      };

      await provider.addInteraction({
        state: 'voice agent validation fails',
        uponReceiving: 'a request to create an invalid voice agent',
        withRequest: {
          method: 'POST',
          path: '/api/voice-agents',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
          body: invalidAgent,
        },
        willRespondWith: {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
          },
          body: {
            error: like('Validation failed'),
            details: eachLike({
              field: like('name'),
              message: like('Name is required'),
              code: like('REQUIRED_FIELD'),
            }),
          },
        },
      });

      // Act & Assert
      try {
        await axios.post(
          'http://localhost:8991/api/voice-agents',
          invalidAgent
        );
        fail('Should have thrown an error');
      } catch (error) {
        expect(error.response.status).toBe(400);
        expect(error.response.data.error).toBe('Validation failed');
        expect(error.response.data.details).toBeInstanceOf(Array);
      }
    });
  });

  describe('GET /api/voice-agents/:id/conversations', () => {
    it('should return conversations for a specific agent', async () => {
      // Arrange
      const agentId = 'agent-123';

      await provider.addInteraction({
        state: 'voice agent has conversations',
        uponReceiving: 'a request for agent conversations',
        withRequest: {
          method: 'GET',
          path: `/api/voice-agents/${agentId}/conversations`,
          query: {
            limit: '20',
            offset: '0',
          },
          headers: {
            Accept: 'application/json',
          },
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
          },
          body: {
            conversations: eachLike({
              id: like('conv-789'),
              agentId: like(agentId),
              customerId: like('customer-456'),
              status: regex('active|completed|failed', 'completed'),
              duration: like(245),
              startTime: regex(
                '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z',
                '2025-01-01T10:00:00Z'
              ),
              endTime: regex(
                '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z',
                '2025-01-01T10:04:05Z'
              ),
              transcript: eachLike({
                timestamp: regex(
                  '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z',
                  '2025-01-01T10:00:00Z'
                ),
                speaker: regex('agent|customer', 'customer'),
                content: like('Hello, I need help with my order'),
                confidence: like(0.98),
              }),
              sentiment: {
                overall: regex('positive|neutral|negative', 'positive'),
                score: like(0.75),
              },
              outcome: {
                resolved: like(true),
                escalated: like(false),
                satisfaction: like(4.5),
              },
            }),
            total: like(150),
            limit: like(20),
            offset: like(0),
          },
        },
      });

      // Act
      const response = await axios.get(
        `http://localhost:8991/api/voice-agents/${agentId}/conversations?limit=20&offset=0`
      );

      // Assert
      expect(response.status).toBe(200);
      expect(response.data.conversations).toBeInstanceOf(Array);
      expect(response.data.conversations[0]).toHaveProperty('id');
      expect(response.data.conversations[0]).toHaveProperty('transcript');
      expect(response.data.conversations[0]).toHaveProperty('sentiment');
      expect(response.data.conversations[0]).toHaveProperty('outcome');
    });
  });

  describe('PUT /api/voice-agents/:id/status', () => {
    it('should update voice agent status', async () => {
      // Arrange
      const agentId = 'agent-123';
      const statusUpdate = { status: 'active' };

      await provider.addInteraction({
        state: 'voice agent exists and can be updated',
        uponReceiving: 'a request to update agent status',
        withRequest: {
          method: 'PUT',
          path: `/api/voice-agents/${agentId}/status`,
          headers: {
            'Content-Type': 'application/json',
            Accept: 'application/json',
          },
          body: statusUpdate,
        },
        willRespondWith: {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
          },
          body: {
            id: like(agentId),
            status: like('active'),
            updatedAt: regex(
              '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z',
              '2025-01-01T00:00:00Z'
            ),
          },
        },
      });

      // Act
      const response = await axios.put(
        `http://localhost:8991/api/voice-agents/${agentId}/status`,
        statusUpdate
      );

      // Assert
      expect(response.status).toBe(200);
      expect(response.data.status).toBe('active');
      expect(response.data).toHaveProperty('updatedAt');
    });
  });
});
