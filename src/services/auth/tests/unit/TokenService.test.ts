/**
 * Token Service Unit Tests
 * Tests JWT token generation, validation, and management
 */

import { TokenService } from '../../src/services/TokenService';
import { RedisService } from '../../src/services/RedisService';
import { authConfig } from '../../src/config/auth.config';
import { createMockRedis, createMockUser, expectValidJWT } from '../setup';
import jwt from 'jsonwebtoken';

describe('TokenService', () => {
  let tokenService: TokenService;
  let mockRedis: jest.Mocked<RedisService>;

  beforeEach(() => {
    mockRedis = createMockRedis();
    tokenService = new TokenService(mockRedis);
  });

  describe('generateTokens', () => {
    it('should generate valid access and refresh tokens', async () => {
      const user = createMockUser();
      const sessionId = 'session-123';

      const tokens = await tokenService.generateTokens(user, sessionId);

      expect(tokens).toEqual({
        accessToken: expect.any(String),
        refreshToken: expect.any(String),
        tokenType: 'Bearer',
        expiresIn: expect.any(Number),
        scope: 'read write',
      });

      expectValidJWT(tokens.accessToken);
      expectValidJWT(tokens.refreshToken);
    });

    it('should include correct payload in access token', async () => {
      const user = createMockUser({
        roles: [{ name: process.env.UNKNOWN }],
        permissions: [{ resource: 'users', action: 'read' }],
      });
      const sessionId = 'session-123';

      const tokens = await tokenService.generateTokens(user, sessionId, true);

      const decoded = jwt.decode(tokens.accessToken) as any;
      expect(decoded).toMatchObject({
        sub: user.id,
        email: user.email,
        username: user.username,
        roles: ['admin'],
        permissions: ['users:read'],
        sessionId,
        mfaVerified: true,
        iss: authConfig.jwt.issuer,
        aud: authConfig.jwt.audience,
      });
    });

    it('should store refresh token in Redis', async () => {
      const user = createMockUser();
      const sessionId = 'session-123';

      await tokenService.generateTokens(user, sessionId);

      expect(mockRedis.setex).toHaveBeenCalledWith(
        expect.stringMatching(/^refresh_token:/),
        expect.any(Number),
        expect.stringContaining(user.id)
      );
    });
  });

  describe('verifyToken', () => {
    it('should verify valid token', async () => {
      const user = createMockUser();
      const sessionId = 'session-123';
      mockRedis.exists.mockResolvedValue(1); // Session active

      const tokens = await tokenService.generateTokens(user, sessionId);
      const payload = await tokenService.verifyToken(tokens.accessToken);

      expect(payload).toMatchObject({
        sub: user.id,
        email: user.email,
        sessionId,
      });
    });

    it('should reject token if session inactive', async () => {
      const user = createMockUser();
      const sessionId = 'session-123';
      mockRedis.exists.mockResolvedValue(0); // Session inactive

      const tokens = await tokenService.generateTokens(user, sessionId);
      const payload = await tokenService.verifyToken(tokens.accessToken);

      expect(payload).toBeNull();
    });

    it('should reject expired token', async () => {
      // Create token with expired timestamp
      const expiredToken = jwt.sign(
        {
          sub: 'user-123',
          exp: Math.floor(Date.now() / 1000) - 3600, // 1 hour ago
          iss: authConfig.jwt.issuer,
          aud: authConfig.jwt.audience,
        },
        authConfig.jwt.secret
      );

      const payload = await tokenService.verifyToken(expiredToken);
      expect(payload).toBeNull();
    });

    it('should reject token with invalid signature', async () => {
      const invalidToken = jwt.sign({ sub: 'user-123' }, 'wrong-secret');

      const payload = await tokenService.verifyToken(invalidToken);
      expect(payload).toBeNull();
    });
  });

  describe('refreshToken', () => {
    it('should refresh valid refresh token', async () => {
      const user = createMockUser();
      const sessionId = 'session-123';

      // Mock stored refresh token data
      mockRedis.get
        .mockResolvedValueOnce(
          JSON.stringify({
            userId: user.id,
            sessionId,
          })
        )
        .mockResolvedValueOnce(
          JSON.stringify({
            email: user.email,
            username: user.username,
            roles: [],
            permissions: [],
          })
        );

      const originalTokens = await tokenService.generateTokens(user, sessionId);
      const newTokens = await tokenService.refreshToken(
        originalTokens.refreshToken
      );

      expect(newTokens).toEqual({
        accessToken: expect.any(String),
        refreshToken: originalTokens.refreshToken, // Same refresh token
        tokenType: 'Bearer',
        expiresIn: expect.any(Number),
        scope: 'read write',
      });

      expectValidJWT(newTokens!.accessToken);
    });

    it('should reject refresh token not in store', async () => {
      const user = createMockUser();
      const sessionId = 'session-123';
      mockRedis.get.mockResolvedValue(null); // Token not in store

      const tokens = await tokenService.generateTokens(user, sessionId);
      const result = await tokenService.refreshToken(tokens.refreshToken);

      expect(result).toBeNull();
    });

    it('should reject refresh token with inactive session', async () => {
      const user = createMockUser();
      const sessionId = 'session-123';

      mockRedis.get
        .mockResolvedValueOnce(
          JSON.stringify({
            userId: user.id,
            sessionId,
          })
        )
        .mockResolvedValueOnce(null); // Session not found

      const tokens = await tokenService.generateTokens(user, sessionId);
      const result = await tokenService.refreshToken(tokens.refreshToken);

      expect(result).toBeNull();
    });
  });

  describe('revokeRefreshToken', () => {
    it('should revoke valid refresh token', async () => {
      const user = createMockUser();
      const sessionId = 'session-123';
      mockRedis.del.mockResolvedValue(1);

      const tokens = await tokenService.generateTokens(user, sessionId);
      const result = await tokenService.revokeRefreshToken(tokens.refreshToken);

      expect(result).toBe(true);
      expect(mockRedis.del).toHaveBeenCalledWith(
        expect.stringMatching(/^refresh_token:/)
      );
    });

    it('should handle non-existent refresh token', async () => {
      const user = createMockUser();
      const sessionId = 'session-123';
      mockRedis.del.mockResolvedValue(0);

      const tokens = await tokenService.generateTokens(user, sessionId);
      const result = await tokenService.revokeRefreshToken(tokens.refreshToken);

      expect(result).toBe(false);
    });
  });

  describe('revokeAllUserTokens', () => {
    it('should revoke all tokens for user', async () => {
      const userId = 'user-123';

      mockRedis.keys.mockResolvedValue([
        'refresh_token:token1',
        'refresh_token:token2',
      ]);
      mockRedis.get
        .mockResolvedValueOnce(JSON.stringify({ userId }))
        .mockResolvedValueOnce(JSON.stringify({ userId }));
      mockRedis.del.mockResolvedValue(1);

      const result = await tokenService.revokeAllUserTokens(userId);

      expect(result).toBe(2);
      expect(mockRedis.del).toHaveBeenCalledTimes(2);
    });
  });

  describe('cleanupExpiredTokens', () => {
    it('should clean up expired tokens', async () => {
      mockRedis.keys.mockResolvedValue([
        'refresh_token:expired1',
        'refresh_token:expired2',
      ]);
      mockRedis.ttl.mockResolvedValue(-1); // Expired
      mockRedis.del.mockResolvedValue(1);

      const result = await tokenService.cleanupExpiredTokens();

      expect(result).toBe(2);
      expect(mockRedis.del).toHaveBeenCalledTimes(2);
    });

    it('should not clean up active tokens', async () => {
      mockRedis.keys.mockResolvedValue(['refresh_token:active']);
      mockRedis.ttl.mockResolvedValue(3600); // 1 hour remaining

      const result = await tokenService.cleanupExpiredTokens();

      expect(result).toBe(0);
      expect(mockRedis.del).not.toHaveBeenCalled();
    });
  });

  describe('isTokenExpired', () => {
    it('should detect expired token', () => {
      const expiredToken = jwt.sign(
        { exp: Math.floor(Date.now() / 1000) - 3600 },
        'secret'
      );

      const result = tokenService.isTokenExpired(expiredToken);
      expect(result).toBe(true);
    });

    it('should detect valid token', () => {
      const validToken = jwt.sign(
        { exp: Math.floor(Date.now() / 1000) + 3600 },
        'secret'
      );

      const result = tokenService.isTokenExpired(validToken);
      expect(result).toBe(false);
    });

    it('should handle invalid token', () => {
      const result = tokenService.isTokenExpired('invalid-token');
      expect(result).toBe(true);
    });
  });

  describe('edge cases', () => {
    it('should handle Redis errors gracefully', async () => {
      mockRedis.setex.mockRejectedValue(new Error('Redis error'));
      const user = createMockUser();

      await expect(
        tokenService.generateTokens(user, 'session-123')
      ).rejects.toThrow('Redis error');
    });

    it('should handle malformed JWT gracefully', async () => {
      const payload = await tokenService.verifyToken('not.a.jwt');
      expect(payload).toBeNull();
    });
  });
});
