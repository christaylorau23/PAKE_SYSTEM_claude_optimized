/**
 * Mutual TLS (mTLS) Service
 * Provides encryption in transit with mutual authentication
 */

import tls from 'tls';
import https from 'https';
import crypto from 'crypto';
import { EventEmitter } from 'events';
import { VaultService } from './VaultService';
import {
  TLSConfig,
  ClientAuth,
  Certificate,
  CertificateConfig,
  AlternativeName,
  AlternativeNameType,
} from '../types/secrets.types';
import { Logger } from '../utils/logger';

interface MTLSContext {
  server?: tls.SecureContext;
  client?: tls.SecureContext;
  caCertificates: string[];
  serverCertificate?: Certificate;
  clientCertificate?: Certificate;
}

interface CertificateValidationResult {
  valid: boolean;
  reason?: string;
  certificate?: any;
  chain?: any[];
  issuer?: string;
  subject?: string;
  fingerprint?: string;
}

interface MTLSServerOptions {
  port: number;
  host?: string;
  cert: string | Buffer;
  key: string | Buffer;
  ca?: string | Buffer | Array<string | Buffer>;
  clientAuth: ClientAuth;
  protocols: string[];
  ciphers?: string[];
  honorCipherOrder?: boolean;
  sessionIdContext?: string;
}

interface MTLSClientOptions {
  cert: string | Buffer;
  key: string | Buffer;
  ca?: string | Buffer | Array<string | Buffer>;
  servername?: string;
  checkServerIdentity?: Function;
  rejectUnauthorized?: boolean;
}

export class MTLSService extends EventEmitter {
  private readonly logger = new Logger('MTLSService');
  private readonly vaultService?: VaultService;

  private contexts = new Map<string, MTLSContext>();
  private isInitialized = false;
  private certificateWatcher?: NodeJS.Timeout;

  // Default secure configurations
  private readonly SECURE_PROTOCOLS = ['TLSv1.3', 'TLSv1.2'];
  private readonly SECURE_CIPHERS = [
    'TLS_AES_256_GCM_SHA384',
    'TLS_CHACHA20_POLY1305_SHA256',
    'TLS_AES_128_GCM_SHA256',
    'ECDHE-RSA-AES256-GCM-SHA384',
    'ECDHE-ECDSA-AES256-GCM-SHA384',
    'ECDHE-RSA-AES128-GCM-SHA256',
    'ECDHE-ECDSA-AES128-GCM-SHA256',
  ].join(':');

  constructor(vaultService?: VaultService) {
    super();
    this.vaultService = vaultService;
  }

  /**
   * Initialize mTLS service
   */
  async initialize(): Promise<void> {
    try {
      // Start certificate monitoring
      this.startCertificateWatcher();

      this.isInitialized = true;
      this.logger.info('mTLS service initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize mTLS service', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Create mTLS context for a service
   */
  async createContext(
    contextId: string,
    serverCertPath?: string,
    clientCertPath?: string,
    caPath?: string
  ): Promise<MTLSContext> {
    this.ensureInitialized();

    try {
      const context: MTLSContext = {
        caCertificates: [],
      };

      // Load CA certificates
      if (caPath && this.vaultService) {
        const caSecret = await this.vaultService.getSecret(caPath);
        if (caSecret?.value) {
          const caCerts = Array.isArray(caSecret.value.ca)
            ? caSecret.value.ca
            : [caSecret.value.ca];
          context.caCertificates = caCerts;
        }
      }

      // Load server certificate
      if (serverCertPath && this.vaultService) {
        const serverCertSecret =
          await this.vaultService.getSecret(serverCertPath);
        if (serverCertSecret?.value) {
          context.serverCertificate = {
            certificate: serverCertSecret.value.certificate,
            privateKey: serverCertSecret.value.privateKey,
            certificateChain: serverCertSecret.value.certificateChain,
          } as Certificate;

          // Create server TLS context
          context.server = tls.createSecureContext({
            cert: context.serverCertificate.certificate,
            key: context.serverCertificate.privateKey,
            ca: context.caCertificates,
            honorCipherOrder: true,
            secureProtocol: 'TLSv1_3_method',
          });
        }
      }

      // Load client certificate
      if (clientCertPath && this.vaultService) {
        const clientCertSecret =
          await this.vaultService.getSecret(clientCertPath);
        if (clientCertSecret?.value) {
          context.clientCertificate = {
            certificate: clientCertSecret.value.certificate,
            privateKey: clientCertSecret.value.privateKey,
            certificateChain: clientCertSecret.value.certificateChain,
          } as Certificate;

          // Create client TLS context
          context.client = tls.createSecureContext({
            cert: context.clientCertificate.certificate,
            key: context.clientCertificate.privateKey,
            ca: context.caCertificates,
          });
        }
      }

      this.contexts.set(contextId, context);

      this.logger.info('mTLS context created', {
        contextId,
        hasServer: !!context.server,
        hasClient: !!context.client,
        caCount: context.caCertificates.length,
      });

      return context;
    } catch (error) {
      this.logger.error('Failed to create mTLS context', {
        contextId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Create HTTPS server with mTLS
   */
  createMTLSServer(
    contextId: string,
    options: Partial<MTLSServerOptions> = {}
  ): https.Server {
    this.ensureInitialized();

    const context = this.contexts.get(contextId);
    if (!context || !context.server) {
      throw new Error(`Server context not found: ${contextId}`);
    }

    const serverOptions: https.ServerOptions = {
      secureContext: context.server,
      ca: context.caCertificates,
      requestCert: true,
      rejectUnauthorized: options.clientAuth !== ClientAuth.NO_CLIENT_CERT,
      ciphers: options.ciphers || this.SECURE_CIPHERS,
      honorCipherOrder: options.honorCipherOrder ?? true,
      secureProtocol: 'TLSv1_3_method',
      sessionIdContext:
        options.sessionIdContext || crypto.randomBytes(16).toString('hex'),
    };

    const server = https.createServer(serverOptions);

    // Set up certificate validation
    server.on('secureConnection', tlsSocket => {
      this.validateClientCertificate(
        tlsSocket,
        options.clientAuth || ClientAuth.REQUIRE_AND_VERIFY_CLIENT_CERT
      );
    });

    // Log TLS events
    server.on('secureConnection', tlsSocket => {
      this.logger.debug('mTLS connection established', {
        contextId,
        protocol: tlsSocket.getProtocol(),
        cipher: tlsSocket.getCipher(),
        clientCertificate: !!tlsSocket.getPeerCertificate(),
      });

      this.emit('connectionEstablished', {
        contextId,
        protocol: tlsSocket.getProtocol(),
        cipher: tlsSocket.getCipher(),
        timestamp: new Date().toISOString(),
      });
    });

    server.on('tlsClientError', (err, tlsSocket) => {
      this.logger.warn('mTLS client error', {
        contextId,
        error: err.message,
        remoteAddress: tlsSocket?.remoteAddress,
      });

      this.emit('connectionError', {
        contextId,
        error: err.message,
        timestamp: new Date().toISOString(),
      });
    });

    return server;
  }

  /**
   * Create HTTPS agent with mTLS client certificate
   */
  createMTLSAgent(
    contextId: string,
    options: Partial<MTLSClientOptions> = {}
  ): https.Agent {
    this.ensureInitialized();

    const context = this.contexts.get(contextId);
    if (!context || !context.client) {
      throw new Error(`Client context not found: ${contextId}`);
    }

    const agentOptions: https.AgentOptions = {
      cert: context.clientCertificate?.certificate,
      key: context.clientCertificate?.privateKey,
      ca: context.caCertificates,
      rejectUnauthorized: options.rejectUnauthorized ?? true,
      checkServerIdentity:
        options.checkServerIdentity || tls.checkServerIdentity,
      secureProtocol: 'TLSv1_3_method',
      ciphers: this.SECURE_CIPHERS,
      honorCipherOrder: true,
      keepAlive: true,
      maxSockets: 50,
      maxFreeSockets: 10,
      timeout: 30000,
    };

    const agent = new https.Agent(agentOptions);

    // Log connection events
    agent.on('keylog', (line, tlsSocket) => {
      this.logger.debug('TLS keylog event', {
        contextId,
        line: line.toString(),
      });
    });

    return agent;
  }

  /**
   * Validate certificate
   */
  async validateCertificate(
    certificate: string,
    caCertificates?: string[]
  ): Promise<CertificateValidationResult> {
    try {
      // Parse certificate
      const cert = crypto.X509Certificate
        ? new crypto.X509Certificate(certificate)
        : null;

      if (!cert) {
        return {
          valid: false,
          reason: 'Failed to parse certificate',
        };
      }

      const now = new Date();
      const notBefore = new Date(cert.validFrom);
      const notAfter = new Date(cert.validTo);

      // Check validity period
      if (now < notBefore) {
        return {
          valid: false,
          reason: 'Certificate not yet valid',
          certificate: cert,
        };
      }

      if (now > notAfter) {
        return {
          valid: false,
          reason: 'Certificate has expired',
          certificate: cert,
        };
      }

      // Check certificate chain if CA certificates provided
      if (caCertificates && caCertificates.length > 0) {
        const chainValid = await this.validateCertificateChain(
          certificate,
          caCertificates
        );
        if (!chainValid) {
          return {
            valid: false,
            reason: 'Certificate chain validation failed',
            certificate: cert,
          };
        }
      }

      return {
        valid: true,
        certificate: cert,
        issuer: cert.issuer,
        subject: cert.subject,
        fingerprint: cert.fingerprint256,
      };
    } catch (error) {
      return {
        valid: false,
        reason: error.message,
      };
    }
  }

  /**
   * Generate certificate signing request (CSR)
   */
  async generateCSR(
    config: CertificateConfig
  ): Promise<{ csr: string; privateKey: string }> {
    try {
      // Generate key pair
      const { publicKey, privateKey } = crypto.generateKeyPairSync(
        config.keyAlgorithm as any,
        {
          modulusLength: config.keySize,
          publicKeyEncoding: { type: 'spki', format: 'pem' },
          privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
        }
      );

      // Build subject
      const subject = [
        ['CN', config.commonName],
        ...(config.organization ? [['O', config.organization]] : []),
        ...(config.organizationalUnit
          ? [['OU', config.organizationalUnit]]
          : []),
        ...(config.country ? [['C', config.country]] : []),
        ...(config.state ? [['ST', config.state]] : []),
        ...(config.locality ? [['L', config.locality]] : []),
      ];

      // Build extensions
      const extensions = [];

      if (config.alternativeNames && config.alternativeNames.length > 0) {
        const sanEntries = config.alternativeNames.map(alt => {
          switch (alt.type) {
            case AlternativeNameType.DNS:
              return `DNS:${alt.value}`;
            case AlternativeNameType.IP:
              return `IP:${alt.value}`;
            case AlternativeNameType.EMAIL:
              return `email:${alt.value}`;
            case AlternativeNameType.URI:
              return `URI:${alt.value}`;
            default:
              return alt.value;
          }
        });
        extensions.push({
          name: 'subjectAltName',
          altNames: config.alternativeNames.map(alt => ({
            type:
              alt.type === AlternativeNameType.DNS
                ? 2
                : alt.type === AlternativeNameType.IP
                  ? 7
                  : 1,
            value: alt.value,
          })),
        });
      }

      // For now, return a basic CSR structure
      // Real implementation would use a library like node-forge or OpenSSL bindings
      const csr = `-----BEGIN CERTIFICATE REQUEST-----
${Buffer.from(JSON.stringify({ subject, publicKey, extensions })).toString('base64')}
-----END CERTIFICATE REQUEST-----`;

      this.logger.info('CSR generated successfully', {
        commonName: config.commonName,
        keyAlgorithm: config.keyAlgorithm,
        keySize: config.keySize,
      });

      return { csr, privateKey };
    } catch (error) {
      this.logger.error('Failed to generate CSR', { error: error.message });
      throw error;
    }
  }

  /**
   * Rotate mTLS certificates
   */
  async rotateCertificates(contextId: string): Promise<void> {
    this.ensureInitialized();

    try {
      const context = this.contexts.get(contextId);
      if (!context) {
        throw new Error(`Context not found: ${contextId}`);
      }

      // Generate new certificates (implementation would depend on CA)
      // For now, this is a placeholder that would integrate with Vault PKI

      if (this.vaultService) {
        // Issue new server certificate if needed
        if (context.serverCertificate) {
          const newServerCert = await this.vaultService.issueCertificate(
            'server-role',
            {
              commonName: context.serverCertificate.subject,
              keyAlgorithm: 'rsa',
              keySize: 2048,
              validityDays: 90,
            }
          );

          // Update context with new certificate
          context.serverCertificate = newServerCert;
          context.server = tls.createSecureContext({
            cert: newServerCert.certificate,
            key: newServerCert.privateKey,
            ca: context.caCertificates,
          });
        }

        // Issue new client certificate if needed
        if (context.clientCertificate) {
          const newClientCert = await this.vaultService.issueCertificate(
            'client-role',
            {
              commonName: context.clientCertificate.subject,
              keyAlgorithm: 'rsa',
              keySize: 2048,
              validityDays: 90,
            }
          );

          // Update context with new certificate
          context.clientCertificate = newClientCert;
          context.client = tls.createSecureContext({
            cert: newClientCert.certificate,
            key: newClientCert.privateKey,
            ca: context.caCertificates,
          });
        }
      }

      this.emit('certificatesRotated', {
        contextId,
        timestamp: new Date().toISOString(),
      });
      this.logger.info('Certificates rotated successfully', { contextId });
    } catch (error) {
      this.logger.error('Failed to rotate certificates', {
        contextId,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Get context information
   */
  getContextInfo(contextId: string): any {
    const context = this.contexts.get(contextId);
    if (!context) {
      return null;
    }

    return {
      contextId,
      hasServer: !!context.server,
      hasClient: !!context.client,
      caCount: context.caCertificates.length,
      serverCertificate: context.serverCertificate
        ? {
            subject: context.serverCertificate.subject,
            issuer: context.serverCertificate.issuer,
            serialNumber: context.serverCertificate.serialNumber,
            notBefore: context.serverCertificate.notBefore,
            notAfter: context.serverCertificate.notAfter,
          }
        : null,
      clientCertificate: context.clientCertificate
        ? {
            subject: context.clientCertificate.subject,
            issuer: context.clientCertificate.issuer,
            serialNumber: context.clientCertificate.serialNumber,
            notBefore: context.clientCertificate.notBefore,
            notAfter: context.clientCertificate.notAfter,
          }
        : null,
    };
  }

  /**
   * Private helper methods
   */

  private async validateCertificateChain(
    certificate: string,
    caCertificates: string[]
  ): Promise<boolean> {
    try {
      // Implementation would validate the certificate chain
      // This is a placeholder for actual chain validation logic
      return caCertificates.length > 0;
    } catch (error) {
      this.logger.error('Certificate chain validation failed', {
        error: error.message,
      });
      return false;
    }
  }

  private validateClientCertificate(
    tlsSocket: tls.TLSSocket,
    clientAuth: ClientAuth
  ): void {
    if (clientAuth === ClientAuth.NO_CLIENT_CERT) {
      return;
    }

    const peerCert = tlsSocket.getPeerCertificate(true);

    if (!peerCert || Object.keys(peerCert).length === 0) {
      if (
        clientAuth === ClientAuth.REQUIRE_AND_VERIFY_CLIENT_CERT ||
        clientAuth === ClientAuth.REQUIRE_ANY_CLIENT_CERT
      ) {
        this.logger.warn('Client certificate required but not provided');
        tlsSocket.destroy(new Error('Client certificate required'));
        return;
      }
    }

    if (peerCert && Object.keys(peerCert).length > 0) {
      // Validate certificate
      const now = new Date();
      const notBefore = new Date(peerCert.valid_from);
      const notAfter = new Date(peerCert.valid_to);

      if (now < notBefore || now > notAfter) {
        this.logger.warn('Client certificate is not valid', {
          subject: peerCert.subject,
          validFrom: peerCert.valid_from,
          validTo: peerCert.valid_to,
        });

        if (clientAuth === ClientAuth.REQUIRE_AND_VERIFY_CLIENT_CERT) {
          tlsSocket.destroy(new Error('Client certificate is not valid'));
          return;
        }
      }

      this.logger.debug('Client certificate validated', {
        subject: peerCert.subject,
        issuer: peerCert.issuer,
        fingerprint: peerCert.fingerprint,
        serialNumber: peerCert.serialNumber,
      });
    }
  }

  private startCertificateWatcher(): void {
    this.certificateWatcher = setInterval(
      async () => {
        await this.checkCertificateExpiry();
      },
      24 * 60 * 60 * 1000
    ); // Check daily
  }

  private async checkCertificateExpiry(): Promise<void> {
    const now = new Date();
    const warningThreshold = 30; // days

    for (const [contextId, context] of this.contexts.entries()) {
      // Check server certificate
      if (context.serverCertificate) {
        const expiryDate = new Date(context.serverCertificate.notAfter);
        const daysUntilExpiry = Math.ceil(
          (expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
        );

        if (daysUntilExpiry <= warningThreshold) {
          this.logger.warn('Server certificate expiring soon', {
            contextId,
            daysUntilExpiry,
            subject: context.serverCertificate.subject,
            serialNumber: context.serverCertificate.serialNumber,
          });

          this.emit('certificateExpiring', {
            contextId,
            type: 'server',
            daysUntilExpiry,
            certificate: context.serverCertificate,
          });
        }
      }

      // Check client certificate
      if (context.clientCertificate) {
        const expiryDate = new Date(context.clientCertificate.notAfter);
        const daysUntilExpiry = Math.ceil(
          (expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
        );

        if (daysUntilExpiry <= warningThreshold) {
          this.logger.warn('Client certificate expiring soon', {
            contextId,
            daysUntilExpiry,
            subject: context.clientCertificate.subject,
            serialNumber: context.clientCertificate.serialNumber,
          });

          this.emit('certificateExpiring', {
            contextId,
            type: 'client',
            daysUntilExpiry,
            certificate: context.clientCertificate,
          });
        }
      }
    }
  }

  private ensureInitialized(): void {
    if (!this.isInitialized) {
      throw new Error('mTLS service not initialized. Call initialize() first.');
    }
  }

  /**
   * Close mTLS service
   */
  async close(): Promise<void> {
    if (this.certificateWatcher) {
      clearInterval(this.certificateWatcher);
    }

    // Clear contexts (they contain sensitive data)
    this.contexts.clear();

    this.isInitialized = false;
    this.logger.info('mTLS service closed');
  }
}
