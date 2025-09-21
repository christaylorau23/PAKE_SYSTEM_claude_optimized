/**
 * HashiCorp Vault Service
 * Comprehensive Vault integration with all engines and authentication methods
 */

import vault from 'node-vault';
import { EventEmitter } from 'events';
import {
  VaultConfig,
  VaultAuthMethod,
  VaultEngineType,
  Secret,
  SecretMetadata,
  EncryptedSecret,
  EncryptionKey,
  Certificate,
  CertificateConfig,
  RotationPolicy,
  SecretEvent,
  SecretEventType,
} from '../types/secrets.types';
import { Logger } from '../utils/logger';

interface VaultToken {
  token: string;
  renewable: boolean;
  ttl: number;
  policies: string[];
  metadata: Record<string, any>;
  expiresAt: Date;
}

interface DatabaseCredentials {
  username: string;
  REDACTED_SECRET: string;
  ttl: number;
  leaseId: string;
}

export class VaultService extends EventEmitter {
  private readonly logger = new Logger('VaultService');
  private vaultClient: any;
  private config: VaultConfig;
  private currentToken: VaultToken | null = null;
  private tokenRenewalTimer: NodeJS.Timeout | null = null;
  private isInitialized = false;
  private healthCheck: NodeJS.Timeout | null = null;

  constructor(config: VaultConfig) {
    super();
    this.config = config;
  }

  /**
   * Initialize Vault service
   */
  async initialize(): Promise<void> {
    try {
      // Configure Vault client
      this.vaultClient = vault({
        endpoint: this.config.endpoint,
        namespace: this.config.namespace,
        requestOptions: {
          timeout: this.config.timeout || 30000,
          rejectUnauthorized: !this.config.tlsConfig?.insecure,
        },
      });

      // Setup TLS if configured
      if (this.config.tlsConfig?.enabled) {
        await this.configureTLS();
      }

      // Authenticate with Vault
      await this.authenticate();

      // Setup engines
      await this.initializeEngines();

      // Start token renewal process
      this.startTokenRenewal();

      // Start health monitoring
      this.startHealthCheck();

      this.isInitialized = true;
      this.logger.info('Vault service initialized successfully', {
        endpoint: this.config.endpoint,
        authMethod: this.config.authMethod,
        engines: this.config.engines.length,
      });
    } catch (error) {
      this.logger.error('Failed to initialize Vault service', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Authenticate with Vault
   */
  private async authenticate(): Promise<void> {
    try {
      let authResponse: any;

      switch (this.config.authMethod) {
        case VaultAuthMethod.TOKEN:
          if (!this.config.token) {
            throw new Error('Token required for token authentication');
          }
          this.vaultClient.token = this.config.token;
          authResponse = await this.vaultClient.tokenLookupSelf();
          break;

        case VaultAuthMethod.APPROLE:
          if (!this.config.roleId || !this.config.secretId) {
            throw new Error(
              'Role ID and Secret ID required for AppRole authentication'
            );
          }
          authResponse = await this.vaultClient.approleLogin({
            role_id: this.config.roleId,
            secret_id: this.config.secretId,
          });
          this.vaultClient.token = authResponse.auth.client_token;
          break;

        case VaultAuthMethod.KUBERNETES: {
          const jwt = await this.getServiceAccountToken();
          authResponse = await this.vaultClient.kubernetesLogin({
            role: this.config.kubernetesRole,
            jwt: jwt,
          });
          this.vaultClient.token = authResponse.auth.client_token;
          break;
        }

        case VaultAuthMethod.AWS_IAM:
          authResponse = await this.vaultClient.awsIamLogin({
            role: this.config.awsRole,
            iam_http_request_method: 'POST',
            iam_request_url: 'https://sts.amazonaws.com/',
            iam_request_body: 'Action=GetCallerIdentity&Version=2011-06-15',
            iam_request_headers: await this.getAWSHeaders(),
          });
          this.vaultClient.token = authResponse.auth.client_token;
          break;

        default:
          throw new Error(
            `Unsupported authentication method: ${this.config.authMethod}`
          );
      }

      // Store token information
      this.currentToken = {
        token: this.vaultClient.token,
        renewable: authResponse.auth?.renewable || false,
        ttl:
          authResponse.auth?.lease_duration || authResponse.data?.ttl || 3600,
        policies:
          authResponse.auth?.policies || authResponse.data?.policies || [],
        metadata:
          authResponse.auth?.metadata || authResponse.data?.metadata || {},
        expiresAt: new Date(
          Date.now() + (authResponse.auth?.lease_duration || 3600) * 1000
        ),
      };

      this.logger.info('Successfully authenticated with Vault', {
        authMethod: this.config.authMethod,
        policies: this.currentToken.policies,
        ttl: this.currentToken.ttl,
        renewable: this.currentToken.renewable,
      });
    } catch (error) {
      this.logger.error('Vault authentication failed', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Initialize Vault engines
   */
  private async initializeEngines(): Promise<void> {
    for (const engineConfig of this.config.engines) {
      try {
        await this.enableEngine(
          engineConfig.type,
          engineConfig.path,
          engineConfig.config
        );
        this.logger.debug('Engine initialized', {
          type: engineConfig.type,
          path: engineConfig.path,
        });
      } catch (error) {
        // Engine might already exist
        this.logger.warn('Failed to enable engine (might already exist)', {
          type: engineConfig.type,
          path: engineConfig.path,
          error: error.message,
        });
      }
    }
  }

  /**
   * Enable a Vault engine
   */
  private async enableEngine(
    type: VaultEngineType,
    path: string,
    config?: any
  ): Promise<void> {
    const mountConfig: any = {
      type: type,
      description: `PAKE ${type} engine`,
      config: {
        default_lease_ttl: '24h',
        max_lease_ttl: '720h',
        ...config,
      },
    };

    await this.vaultClient.mount({
      mount_point: path,
      type: type,
      config: mountConfig,
    });
  }

  /**
   * Store a secret in KV store
   */
  async storeSecret(
    path: string,
    secret: Record<string, any>,
    metadata?: Partial<SecretMetadata>
  ): Promise<void> {
    try {
      this.ensureInitialized();

      const secretWithMetadata = {
        data: secret,
        metadata: {
          created_by: 'pake-system',
          created_at: new Date().toISOString(),
          ...metadata,
        },
      };

      await this.vaultClient.write(`secret/data/${path}`, secretWithMetadata);

      // Emit event
      this.emit('secretStored', {
        id: `secret-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.SECRET_WRITE,
        secretId: path,
        actor: 'vault-service',
        source: 'vault',
        success: true,
      } as SecretEvent);

      this.logger.info('Secret stored successfully', { path });
    } catch (error) {
      this.logger.error('Failed to store secret', {
        path,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Retrieve a secret from KV store
   */
  async getSecret(path: string): Promise<Secret | null> {
    try {
      this.ensureInitialized();

      const response = await this.vaultClient.read(`secret/data/${path}`);

      if (!response || !response.data) {
        return null;
      }

      // Emit event
      this.emit('secretAccessed', {
        id: `secret-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.SECRET_READ,
        secretId: path,
        actor: 'vault-service',
        source: 'vault',
        success: true,
      } as SecretEvent);

      return {
        metadata: {
          id: path,
          name: path,
          version: response.data.metadata?.version || 1,
          createdAt: response.data.metadata?.created_time,
          updatedAt: response.data.metadata?.updated_time,
          tags: response.data.metadata?.custom_metadata || {},
          classification: response.data.metadata?.classification || 'internal',
          environment: response.data.metadata?.environment || 'unknown',
          application: response.data.metadata?.application || 'unknown',
          owner: response.data.metadata?.created_by || 'unknown',
          accessCount: 0,
        } as SecretMetadata,
        value: response.data.data,
        encrypted: false,
      };
    } catch (error) {
      this.logger.error('Failed to retrieve secret', {
        path,
        error: error.message,
      });

      // Emit failed access event
      this.emit('secretAccessFailed', {
        id: `secret-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.SECRET_READ,
        secretId: path,
        actor: 'vault-service',
        source: 'vault',
        success: false,
        error: error.message,
      } as SecretEvent);

      return null;
    }
  }

  /**
   * Delete a secret from KV store
   */
  async deleteSecret(path: string): Promise<void> {
    try {
      this.ensureInitialized();

      await this.vaultClient.delete(`secret/data/${path}`);

      // Emit event
      this.emit('secretDeleted', {
        id: `secret-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.SECRET_DELETE,
        secretId: path,
        actor: 'vault-service',
        source: 'vault',
        success: true,
      } as SecretEvent);

      this.logger.info('Secret deleted successfully', { path });
    } catch (error) {
      this.logger.error('Failed to delete secret', {
        path,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * List secrets in a path
   */
  async listSecrets(path: string = ''): Promise<string[]> {
    try {
      this.ensureInitialized();

      const response = await this.vaultClient.list(`secret/metadata/${path}`);
      return response?.data?.keys || [];
    } catch (error) {
      this.logger.error('Failed to list secrets', {
        path,
        error: error.message,
      });
      return [];
    }
  }

  /**
   * Encrypt data using Transit engine
   */
  async encryptData(
    keyName: string,
    plaintext: string,
    context?: Record<string, string>
  ): Promise<string> {
    try {
      this.ensureInitialized();

      const payload: any = {
        plaintext: Buffer.from(plaintext).toString('base64'),
      };

      if (context) {
        payload.context = Buffer.from(JSON.stringify(context)).toString(
          'base64'
        );
      }

      const response = await this.vaultClient.write(
        `transit/encrypt/${keyName}`,
        payload
      );

      // Emit event
      this.emit('dataEncrypted', {
        id: `encrypt-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.ENCRYPT,
        secretId: keyName,
        actor: 'vault-service',
        source: 'transit',
        success: true,
        metadata: { contextProvided: !!context },
      } as SecretEvent);

      return response.data.ciphertext;
    } catch (error) {
      this.logger.error('Failed to encrypt data', {
        keyName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Decrypt data using Transit engine
   */
  async decryptData(
    keyName: string,
    ciphertext: string,
    context?: Record<string, string>
  ): Promise<string> {
    try {
      this.ensureInitialized();

      const payload: any = {
        ciphertext: ciphertext,
      };

      if (context) {
        payload.context = Buffer.from(JSON.stringify(context)).toString(
          'base64'
        );
      }

      const response = await this.vaultClient.write(
        `transit/decrypt/${keyName}`,
        payload
      );

      // Emit event
      this.emit('dataDecrypted', {
        id: `decrypt-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.DECRYPT,
        secretId: keyName,
        actor: 'vault-service',
        source: 'transit',
        success: true,
        metadata: { contextProvided: !!context },
      } as SecretEvent);

      return Buffer.from(response.data.plaintext, 'base64').toString();
    } catch (error) {
      this.logger.error('Failed to decrypt data', {
        keyName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Create encryption key in Transit engine
   */
  async createTransitKey(
    keyName: string,
    keyType: string = 'aes256-gcm96'
  ): Promise<void> {
    try {
      this.ensureInitialized();

      await this.vaultClient.write(`transit/keys/${keyName}`, {
        type: keyType,
        exportable: false,
        allow_plaintext_backup: false,
      });

      // Emit event
      this.emit('keyCreated', {
        id: `key-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.KEY_GENERATE,
        secretId: keyName,
        actor: 'vault-service',
        source: 'transit',
        success: true,
        metadata: { keyType },
      } as SecretEvent);

      this.logger.info('Transit key created', { keyName, keyType });
    } catch (error) {
      this.logger.error('Failed to create transit key', {
        keyName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Rotate encryption key in Transit engine
   */
  async rotateTransitKey(keyName: string): Promise<void> {
    try {
      this.ensureInitialized();

      await this.vaultClient.write(`transit/keys/${keyName}/rotate`, {});

      // Emit event
      this.emit('keyRotated', {
        id: `rotate-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.KEY_ROTATE,
        secretId: keyName,
        actor: 'vault-service',
        source: 'transit',
        success: true,
      } as SecretEvent);

      this.logger.info('Transit key rotated', { keyName });
    } catch (error) {
      this.logger.error('Failed to rotate transit key', {
        keyName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Generate dynamic database credentials
   */
  async getDatabaseCredentials(roleName: string): Promise<DatabaseCredentials> {
    try {
      this.ensureInitialized();

      const response = await this.vaultClient.read(
        `database/creds/${roleName}`
      );

      return {
        username: response.data.username,
        REDACTED_SECRET: response.data.REDACTED_SECRET,
        ttl: response.lease_duration,
        leaseId: response.lease_id,
      };
    } catch (error) {
      this.logger.error('Failed to get database credentials', {
        roleName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Configure database connection
   */
  async configureDatabaseConnection(name: string, config: any): Promise<void> {
    try {
      this.ensureInitialized();

      await this.vaultClient.write(`database/config/${name}`, {
        plugin_name: config.plugin_name,
        connection_url: config.connection_url,
        allowed_roles: config.allowed_roles,
        username: config.username,
        REDACTED_SECRET: config.REDACTED_SECRET,
      });

      this.logger.info('Database connection configured', { name });
    } catch (error) {
      this.logger.error('Failed to configure database connection', {
        name,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Create database role
   */
  async createDatabaseRole(name: string, config: any): Promise<void> {
    try {
      this.ensureInitialized();

      await this.vaultClient.write(`database/roles/${name}`, {
        db_name: config.db_name,
        creation_statements: config.creation_statements,
        default_ttl: config.default_ttl || '24h',
        max_ttl: config.max_ttl || '72h',
      });

      this.logger.info('Database role created', { name });
    } catch (error) {
      this.logger.error('Failed to create database role', {
        name,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Issue certificate using PKI engine
   */
  async issueCertificate(
    role: string,
    config: CertificateConfig
  ): Promise<Certificate> {
    try {
      this.ensureInitialized();

      const response = await this.vaultClient.write(`pki/issue/${role}`, {
        common_name: config.commonName,
        alt_names: config.alternativeNames?.map(an => an.value).join(','),
        ip_sans: config.alternativeNames
          ?.filter(an => an.type === 'ip')
          .map(an => an.value)
          .join(','),
        ttl: `${config.validityDays}d`,
        format: 'pem',
      });

      const certificate: Certificate = {
        id: `cert-${Date.now()}`,
        certificate: response.data.certificate,
        privateKey: response.data.private_key,
        certificateChain: response.data.ca_chain,
        serialNumber: response.data.serial_number,
        issuer: response.data.issuing_ca,
        subject: config.commonName,
        notBefore: new Date().toISOString(),
        notAfter: new Date(
          Date.now() + config.validityDays * 24 * 60 * 60 * 1000
        ).toISOString(),
        keyUsage: ['digital_signature', 'key_encipherment'],
        extendedKeyUsage: ['server_auth'],
        subjectAlternativeNames: config.alternativeNames || [],
        fingerprint: this.calculateFingerprint(response.data.certificate),
        status: 'active',
        metadata: {
          purpose: 'server_auth',
          autoRenew: false,
          renewalThreshold: 30,
          ocspUrls: [],
          crlUrls: [],
        },
      };

      // Emit event
      this.emit('certificateIssued', {
        id: `cert-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.CERTIFICATE_ISSUE,
        secretId: certificate.id,
        actor: 'vault-service',
        source: 'pki',
        success: true,
        metadata: { commonName: config.commonName, role },
      } as SecretEvent);

      this.logger.info('Certificate issued', {
        commonName: config.commonName,
        serialNumber: certificate.serialNumber,
      });
      return certificate;
    } catch (error) {
      this.logger.error('Failed to issue certificate', {
        commonName: config.commonName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Revoke certificate
   */
  async revokeCertificate(serialNumber: string): Promise<void> {
    try {
      this.ensureInitialized();

      await this.vaultClient.write('pki/revoke', {
        serial_number: serialNumber,
      });

      this.logger.info('Certificate revoked', { serialNumber });
    } catch (error) {
      this.logger.error('Failed to revoke certificate', {
        serialNumber,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Sign data using Transit engine
   */
  async signData(
    keyName: string,
    data: string,
    algorithm: string = 'sha2-256'
  ): Promise<string> {
    try {
      this.ensureInitialized();

      const response = await this.vaultClient.write(
        `transit/sign/${keyName}/${algorithm}`,
        {
          input: Buffer.from(data).toString('base64'),
        }
      );

      // Emit event
      this.emit('dataSignatureed', {
        id: `sign-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.SIGN,
        secretId: keyName,
        actor: 'vault-service',
        source: 'transit',
        success: true,
        metadata: { algorithm },
      } as SecretEvent);

      return response.data.signature;
    } catch (error) {
      this.logger.error('Failed to sign data', {
        keyName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Verify signature using Transit engine
   */
  async verifySignature(
    keyName: string,
    data: string,
    signature: string,
    algorithm: string = 'sha2-256'
  ): Promise<boolean> {
    try {
      this.ensureInitialized();

      const response = await this.vaultClient.write(
        `transit/verify/${keyName}/${algorithm}`,
        {
          input: Buffer.from(data).toString('base64'),
          signature: signature,
        }
      );

      // Emit event
      this.emit('signatureVerified', {
        id: `verify-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: SecretEventType.VERIFY,
        secretId: keyName,
        actor: 'vault-service',
        source: 'transit',
        success: true,
        metadata: { algorithm, valid: response.data.valid },
      } as SecretEvent);

      return response.data.valid;
    } catch (error) {
      this.logger.error('Failed to verify signature', {
        keyName,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get Vault health status
   */
  async getHealth(): Promise<any> {
    try {
      return await this.vaultClient.health();
    } catch (error) {
      this.logger.error('Failed to get Vault health', { error: error.message });
      throw error;
    }
  }

  /**
   * Renew current token
   */
  async renewToken(): Promise<void> {
    if (!this.currentToken || !this.currentToken.renewable) {
      this.logger.debug('Token not renewable, skipping renewal');
      return;
    }

    try {
      const response = await this.vaultClient.tokenRenewSelf();

      this.currentToken.ttl = response.auth.lease_duration;
      this.currentToken.expiresAt = new Date(
        Date.now() + response.auth.lease_duration * 1000
      );

      this.logger.debug('Token renewed successfully', {
        newTtl: this.currentToken.ttl,
        expiresAt: this.currentToken.expiresAt,
      });
    } catch (error) {
      this.logger.error('Failed to renew token', { error: error.message });
      // Re-authenticate if renewal fails
      await this.authenticate();
    }
  }

  /**
   * Start automatic token renewal
   */
  private startTokenRenewal(): void {
    if (!this.currentToken || !this.currentToken.renewable) {
      return;
    }

    const renewalInterval =
      (this.currentToken.ttl - this.config.tokenRenewalBuffer) * 1000;

    this.tokenRenewalTimer = setInterval(async () => {
      try {
        await this.renewToken();
      } catch (error) {
        this.logger.error('Token renewal failed', { error: error.message });
        this.emit('tokenRenewalFailed', error);
      }
    }, renewalInterval);

    this.logger.debug('Token renewal scheduled', {
      intervalMs: renewalInterval,
    });
  }

  /**
   * Start health check monitoring
   */
  private startHealthCheck(): void {
    this.healthCheck = setInterval(async () => {
      try {
        await this.getHealth();
        this.emit('healthCheck', { status: 'healthy' });
      } catch (error) {
        this.logger.warn('Vault health check failed', { error: error.message });
        this.emit('healthCheck', { status: 'unhealthy', error: error.message });
      }
    }, 60000); // Check every minute
  }

  /**
   * Configure TLS settings
   */
  private async configureTLS(): Promise<void> {
    const tlsConfig = this.config.tlsConfig!;

    // Implementation would configure TLS certificates and validation
    this.logger.debug('TLS configuration applied', {
      enabled: tlsConfig.enabled,
      insecure: tlsConfig.insecure,
    });
  }

  /**
   * Get Kubernetes service account token
   */
  private async getServiceAccountToken(): Promise<string> {
    const fs = await import('fs');
    return await fs.promises.readFile(
      '/var/run/secrets/kubernetes.io/serviceaccount/token',
      'utf8'
    );
  }

  /**
   * Get AWS IAM headers for authentication
   */
  private async getAWSHeaders(): Promise<Record<string, string>> {
    // Implementation would generate AWS SigV4 headers
    return {
      'X-Amz-Date': new Date().toISOString().replace(/[:\-]|\.\d{3}/g, ''),
      Authorization: 'AWS4-HMAC-SHA256 ...', // Actual SigV4 signature
    };
  }

  /**
   * Calculate certificate fingerprint
   */
  private calculateFingerprint(certificate: string): string {
    const crypto = await import('crypto');
    const cert = certificate.replace(
      /-----BEGIN CERTIFICATE-----|\-----END CERTIFICATE-----|\n/g,
      ''
    );
    return crypto
      .createHash('sha256')
      .update(Buffer.from(cert, 'base64'))
      .digest('hex');
  }

  /**
   * Ensure service is initialized
   */
  private ensureInitialized(): void {
    if (!this.isInitialized) {
      throw new Error(
        'Vault service not initialized. Call initialize() first.'
      );
    }
  }

  /**
   * Close Vault service
   */
  async close(): Promise<void> {
    if (this.tokenRenewalTimer) {
      clearInterval(this.tokenRenewalTimer);
      this.tokenRenewalTimer = null;
    }

    if (this.healthCheck) {
      clearInterval(this.healthCheck);
      this.healthCheck = null;
    }

    this.isInitialized = false;
    this.logger.info('Vault service closed');
  }
}
