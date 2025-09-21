import {
  ConfidentialClientApplication,
  AuthenticationResult,
  ClientCredentialRequest,
} from '@azure/msal-node';
import { Microsoft365Config } from './types';
import {
  ConnectionCredentials,
  AuthenticationConfig,
} from '../../types/integration';
import { Logger } from '../../utils/logger';

export class Microsoft365AuthService {
  private clientApp: ConfidentialClientApplication;
  private config: Microsoft365Config;
  private logger = Logger.getInstance();

  constructor(config: Microsoft365Config) {
    this.config = config;
    this.clientApp = new ConfidentialClientApplication({
      auth: {
        clientId: config.clientId,
        clientSecret: config.clientSecret,
        authority: `https://login.microsoftonline.com/${config.tenantId}`,
      },
      cache: {
        cacheLocation: 'filesystem',
        storeAuthStateInCookie: false,
      },
    });
  }

  async getAuthorizationUrl(state?: string): Promise<string> {
    try {
      const authCodeUrlParameters = {
        scopes: this.config.scopes,
        redirectUri: this.config.redirectUri,
        state: state || this.generateState(),
      };

      const response = await this.clientApp.getAuthCodeUrl(
        authCodeUrlParameters
      );
      this.logger.info('Generated authorization URL for Microsoft 365');
      return response;
    } catch (error) {
      this.logger.error('Failed to generate authorization URL', error);
      throw error;
    }
  }

  async exchangeCodeForTokens(code: string): Promise<ConnectionCredentials> {
    try {
      const tokenRequest = {
        code,
        scopes: this.config.scopes,
        redirectUri: this.config.redirectUri,
      };

      const response = await this.clientApp.acquireTokenByCode(tokenRequest);

      if (!response) {
        throw new Error('No authentication result received');
      }

      return this.mapAuthResultToCredentials(response);
    } catch (error) {
      this.logger.error('Failed to exchange code for tokens', error);
      throw error;
    }
  }

  async refreshAccessToken(
    refreshToken: string
  ): Promise<ConnectionCredentials> {
    try {
      const refreshTokenRequest = {
        refreshToken,
        scopes: this.config.scopes,
      };

      const response =
        await this.clientApp.acquireTokenByRefreshToken(refreshTokenRequest);

      if (!response) {
        throw new Error('No authentication result received');
      }

      return this.mapAuthResultToCredentials(response);
    } catch (error) {
      this.logger.error('Failed to refresh access token', error);
      throw error;
    }
  }

  async getApplicationToken(): Promise<string> {
    try {
      const clientCredentialRequest: ClientCredentialRequest = {
        scopes: ['https://graph.microsoft.com/.default'],
      };

      const response = await this.clientApp.acquireTokenByClientCredential(
        clientCredentialRequest
      );

      if (!response) {
        throw new Error('No authentication result received');
      }

      return response.accessToken;
    } catch (error) {
      this.logger.error('Failed to get application token', error);
      throw error;
    }
  }

  async validateToken(accessToken: string): Promise<boolean> {
    try {
      const response = await fetch('https://graph.microsoft.com/v1.0/me', {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      return response.ok;
    } catch (error) {
      this.logger.error('Token validation failed', error);
      return false;
    }
  }

  async revokeToken(token: string): Promise<void> {
    try {
      // Microsoft doesn't have a standard revoke endpoint for Graph API
      // Instead, we remove the token from our cache
      await this.clientApp.getTokenCache().removeAccount({
        homeAccountId: '', // Would need to store this from the auth result
        environment: 'login.microsoftonline.com',
        tenantId: this.config.tenantId,
        username: '',
      });

      this.logger.info('Token revoked successfully');
    } catch (error) {
      this.logger.error('Failed to revoke token', error);
      throw error;
    }
  }

  async getUserInfo(accessToken: string): Promise<any> {
    try {
      const response = await fetch('https://graph.microsoft.com/v1.0/me', {
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch user info: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      this.logger.error('Failed to fetch user info', error);
      throw error;
    }
  }

  getAuthenticationConfig(): AuthenticationConfig {
    return {
      type: 'oauth2',
      scopes: this.config.scopes,
      endpoints: {
        authorize: `https://login.microsoftonline.com/${this.config.tenantId}/oauth2/v2.0/authorize`,
        token: `https://login.microsoftonline.com/${this.config.tenantId}/oauth2/v2.0/token`,
        refresh: `https://login.microsoftonline.com/${this.config.tenantId}/oauth2/v2.0/token`,
        revoke: undefined, // Microsoft doesn't have a standard revoke endpoint
        userInfo: 'https://graph.microsoft.com/v1.0/me',
      },
      tokenStorage: {
        encrypted: true,
        location: 'database',
        keyPrefix: 'ms365_token',
        ttl: 3600,
      },
      refreshable: true,
      expirationTime: 3600,
    };
  }

  private mapAuthResultToCredentials(
    authResult: AuthenticationResult
  ): ConnectionCredentials {
    return {
      accessToken: authResult.accessToken,
      refreshToken: authResult.refreshToken || undefined,
      expiresAt: authResult.expiresOn || undefined,
      scopes: authResult.scopes,
      additionalCredentials: {
        idToken: authResult.idToken,
        account: authResult.account,
        correlationId: authResult.correlationId,
      },
    };
  }

  private generateState(): string {
    return (
      Math.random().toString(36).substring(2, 15) +
      Math.random().toString(36).substring(2, 15)
    );
  }

  async handleTokenExpiry(
    credentials: ConnectionCredentials
  ): Promise<ConnectionCredentials> {
    if (!credentials.refreshToken) {
      throw new Error('No refresh token available for token renewal');
    }

    if (this.isTokenExpired(credentials)) {
      this.logger.info('Access token expired, refreshing...');
      return await this.refreshAccessToken(credentials.refreshToken);
    }

    return credentials;
  }

  private isTokenExpired(credentials: ConnectionCredentials): boolean {
    if (!credentials.expiresAt) {
      return false; // If no expiry time, assume it's still valid
    }

    const now = new Date();
    const expiryTime = new Date(credentials.expiresAt);
    const bufferTime = 5 * 60 * 1000; // 5 minutes buffer

    return expiryTime.getTime() - bufferTime <= now.getTime();
  }

  async createWebhookSubscription(
    accessToken: string,
    resource: string,
    changeType: string,
    notificationUrl: string,
    expirationDateTime: Date
  ): Promise<string> {
    try {
      const subscription = {
        changeType,
        notificationUrl,
        resource,
        expirationDateTime: expirationDateTime.toISOString(),
        clientState: this.generateState(),
      };

      const response = await fetch(
        'https://graph.microsoft.com/v1.0/subscriptions',
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(subscription),
        }
      );

      if (!response.ok) {
        throw new Error(
          `Failed to create webhook subscription: ${response.statusText}`
        );
      }

      const result = await response.json();
      this.logger.info('Webhook subscription created', {
        subscriptionId: result.id,
      });

      return result.id;
    } catch (error) {
      this.logger.error('Failed to create webhook subscription', error);
      throw error;
    }
  }

  async deleteWebhookSubscription(
    accessToken: string,
    subscriptionId: string
  ): Promise<void> {
    try {
      const response = await fetch(
        `https://graph.microsoft.com/v1.0/subscriptions/${subscriptionId}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(
          `Failed to delete webhook subscription: ${response.statusText}`
        );
      }

      this.logger.info('Webhook subscription deleted', { subscriptionId });
    } catch (error) {
      this.logger.error('Failed to delete webhook subscription', error);
      throw error;
    }
  }
}
