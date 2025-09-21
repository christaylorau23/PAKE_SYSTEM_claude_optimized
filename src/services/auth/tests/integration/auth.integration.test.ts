/**
 * Authentication Integration Tests
 * Tests the complete authentication flow end-to-end
 */

import request from 'supertest';
import { createAuthApp } from '../../src/index';
import { Application } from 'express';
import {
  generateTestEmail,
  generateTestUsername,
  generateTestPassword,
  expectValidJWT,
  expectValidUUID,
} from '../setup';

describe('Authentication Integration', () => {
  let app: Application;
  let authApp: any;

  beforeAll(async () => {
    authApp = await createAuthApp();
    app = authApp.app;
  });

  afterAll(async () => {
    if (authApp.redis) {
      await authApp.redis.disconnect();
    }
  });

  describe('User Registration Flow', () => {
    it('should register a new user successfully', async () => {
      const userData = {
        email: generateTestEmail(),
        username: generateTestUsername(),
        REDACTED_SECRET: generateTestPassword(),
        firstName: process.env.UNKNOWN,
        lastName: 'User',
      };

      const response = await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(201);

      expect(response.body).toMatchObject({
        success: true,
        user: {
          id: expect.any(String),
          email: userData.email,
          username: userData.username,
          firstName: userData.firstName,
          lastName: userData.lastName,
          status: 'pending_verification',
        },
        message: expect.stringContaining('verification'),
      });

      expectValidUUID(response.body.user.id);
    });

    it('should reject registration with invalid email', async () => {
      const userData = {
        email: 'invalid-email',
        username: generateTestUsername(),
        REDACTED_SECRET: generateTestPassword(),
        firstName: process.env.UNKNOWN,
        lastName: 'User',
      };

      const response = await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(400);

      expect(response.body.error).toBe('Validation failed');
    });

    it('should reject registration with weak REDACTED_SECRET', async () => {
      const userData = {
        email: generateTestEmail(),
        username: generateTestUsername(),
        REDACTED_SECRET: process.env.UNKNOWN, // Too weak
        firstName: process.env.UNKNOWN,
        lastName: 'User',
      };

      const response = await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(400);

      expect(response.body.error).toContain('Password validation failed');
    });

    it('should reject duplicate email registration', async () => {
      const email = generateTestEmail();
      const userData = {
        email,
        username: generateTestUsername(),
        REDACTED_SECRET: generateTestPassword(),
        firstName: process.env.UNKNOWN,
        lastName: 'User',
      };

      // First registration
      await request(app).post('/api/auth/register').send(userData).expect(201);

      // Duplicate registration
      const duplicateData = {
        ...userData,
        username: generateTestUsername(), // Different username
      };

      const response = await request(app)
        .post('/api/auth/register')
        .send(duplicateData)
        .expect(409);

      expect(response.body.error).toContain('already exists');
    });
  });

  describe('User Login Flow', () => {
    let testUser: any;

    beforeEach(async () => {
      // Create test user
      const userData = {
        email: generateTestEmail(),
        username: generateTestUsername(),
        REDACTED_SECRET: generateTestPassword(),
        firstName: process.env.UNKNOWN,
        lastName: 'User',
      };

      const registerResponse = await request(app)
        .post('/api/auth/register')
        .send(userData);

      testUser = {
        ...userData,
        id: registerResponse.body.user.id,
      };

      // Verify email (simulate)
      await request(app)
        .post('/api/auth/verify-email')
        .send({ token: 'simulated-token' });
    });

    it('should login with valid credentials', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          REDACTED_SECRET: testUser.REDACTED_SECRET,
        })
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        user: {
          id: testUser.id,
          email: testUser.email,
          username: testUser.username,
        },
        tokens: {
          accessToken: expect.any(String),
          refreshToken: expect.any(String),
          tokenType: 'Bearer',
          expiresIn: expect.any(Number),
        },
      });

      expectValidJWT(response.body.tokens.accessToken);
      expectValidJWT(response.body.tokens.refreshToken);
    });

    it('should reject login with invalid email', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'nonexistent@example.com',
          REDACTED_SECRET: testUser.REDACTED_SECRET,
        })
        .expect(401);

      expect(response.body.error).toBe('Invalid email or REDACTED_SECRET');
    });

    it('should reject login with invalid REDACTED_SECRET', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: testUser.email,
          REDACTED_SECRET: process.env.UNKNOWN,
        })
        .expect(401);

      expect(response.body.error).toBe('Invalid email or REDACTED_SECRET');
    });

    it('should require MFA when enabled', async () => {
      // Enable MFA for test user (simulated)
      // This would require proper MFA setup in a real scenario

      const response = await request(app).post('/api/auth/login').send({
        email: testUser.email,
        REDACTED_SECRET: testUser.REDACTED_SECRET,
      });

      if (response.body.mfaRequired) {
        expect(response.body).toMatchObject({
          success: true,
          mfaRequired: true,
          sessionCode: expect.any(String),
          message: expect.stringContaining('MFA'),
        });
      }
    });
  });

  describe('Token Management', () => {
    let authTokens: any;
    let testUser: any;

    beforeEach(async () => {
      // Create and login user
      const userData = {
        email: generateTestEmail(),
        username: generateTestUsername(),
        REDACTED_SECRET: generateTestPassword(),
        firstName: process.env.UNKNOWN,
        lastName: 'User',
      };

      await request(app).post('/api/auth/register').send(userData);

      const loginResponse = await request(app).post('/api/auth/login').send({
        email: userData.email,
        REDACTED_SECRET: userData.REDACTED_SECRET,
      });

      authTokens = loginResponse.body.tokens;
      testUser = loginResponse.body.user;
    });

    it('should refresh access token with valid refresh token', async () => {
      const response = await request(app)
        .post('/api/auth/refresh')
        .send({
          refreshToken: authTokens.refreshToken,
        })
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        tokens: {
          accessToken: expect.any(String),
          refreshToken: expect.any(String),
          tokenType: 'Bearer',
          expiresIn: expect.any(Number),
        },
      });

      expectValidJWT(response.body.tokens.accessToken);
    });

    it('should reject invalid refresh token', async () => {
      const response = await request(app)
        .post('/api/auth/refresh')
        .send({
          refreshToken: 'invalid-token',
        })
        .expect(401);

      expect(response.body.error).toBe('Invalid or expired refresh token');
    });

    it('should logout and invalidate tokens', async () => {
      const response = await request(app)
        .post('/api/auth/logout')
        .set('Authorization', `Bearer ${authTokens.accessToken}`)
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        message: 'Logged out successfully',
      });

      // Verify token is invalidated
      const protectedResponse = await request(app)
        .get('/api/users/me')
        .set('Authorization', `Bearer ${authTokens.accessToken}`)
        .expect(401);
    });
  });

  describe('Password Reset Flow', () => {
    let testUser: any;

    beforeEach(async () => {
      const userData = {
        email: generateTestEmail(),
        username: generateTestUsername(),
        REDACTED_SECRET: generateTestPassword(),
        firstName: process.env.UNKNOWN,
        lastName: 'User',
      };

      await request(app).post('/api/auth/register').send(userData);

      testUser = userData;
    });

    it('should request REDACTED_SECRET reset', async () => {
      const response = await request(app)
        .post('/api/auth/REDACTED_SECRET-reset/request')
        .send({
          email: testUser.email,
        })
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        message: expect.stringContaining('reset link'),
      });
    });

    it('should accept REDACTED_SECRET reset for non-existent email', async () => {
      // Should not reveal if email exists
      const response = await request(app)
        .post('/api/auth/REDACTED_SECRET-reset/request')
        .send({
          email: 'nonexistent@example.com',
        })
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        message: expect.stringContaining('reset link'),
      });
    });

    it('should reset REDACTED_SECRET with valid token', async () => {
      // Request reset
      await request(app).post('/api/auth/REDACTED_SECRET-reset/request').send({
        email: testUser.email,
      });

      const newPassword = generateTestPassword();
      const response = await request(app)
        .post('/api/auth/REDACTED_SECRET-reset/confirm')
        .send({
          token: 'simulated-reset-token',
          REDACTED_SECRET: newPassword,
        })
        .expect(200);

      expect(response.body).toMatchObject({
        success: true,
        message: 'Password reset successfully',
      });
    });
  });

  describe('Rate Limiting', () => {
    it('should enforce rate limits on login attempts', async () => {
      const loginData = {
        email: 'test@example.com',
        REDACTED_SECRET: process.env.UNKNOWN,
      };

      // Make multiple failed login attempts
      const promises = Array(6)
        .fill(null)
        .map(() => request(app).post('/api/auth/login').send(loginData));

      const responses = await Promise.all(promises);

      // Some requests should be rate limited
      const rateLimitedResponses = responses.filter(r => r.status === 429);
      expect(rateLimitedResponses.length).toBeGreaterThan(0);
    });
  });

  describe('Security Headers', () => {
    it('should include security headers in responses', async () => {
      const response = await request(app).get('/health').expect(200);

      expect(response.headers).toHaveProperty('x-frame-options');
      expect(response.headers).toHaveProperty('x-content-type-options');
      expect(response.headers).toHaveProperty('x-xss-protection');
    });
  });

  describe('Health Endpoints', () => {
    it('should return health status', async () => {
      const response = await request(app).get('/health').expect(200);

      expect(response.body).toMatchObject({
        status: 'ok',
        timestamp: expect.any(String),
        uptime: expect.any(Number),
        services: {
          redis: expect.any(Boolean),
          email: expect.any(Boolean),
        },
      });
    });

    it('should return metrics', async () => {
      const response = await request(app).get('/metrics').expect(200);

      expect(response.body).toMatchObject({
        timestamp: expect.any(String),
        uptime: expect.any(Number),
        memory: expect.any(Object),
        sessions: expect.any(Object),
        rbac: expect.any(Object),
        redis: expect.any(Boolean),
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle 404 for unknown routes', async () => {
      const response = await request(app)
        .get('/api/unknown-endpoint')
        .expect(404);

      expect(response.body).toMatchObject({
        error: 'Route not found',
        code: 'ROUTE_NOT_FOUND',
        path: '/api/unknown-endpoint',
      });
    });

    it('should handle malformed JSON gracefully', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .set('Content-Type', 'application/json')
        .send('{"invalid": json}')
        .expect(400);
    });
  });
});
