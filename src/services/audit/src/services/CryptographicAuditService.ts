/**
 * Cryptographic Audit Service
 * Provides tamper-proof audit logging with cryptographic signatures
 */

import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import { AuditEvent, AuditEventBatch } from '../types/audit.types';
import { Logger } from '../utils/logger';

export class CryptographicAuditService {
  private readonly logger = new Logger('CryptographicAuditService');
  private readonly signingKey: string;
  private readonly encryptionKey: Buffer;
  private readonly algorithm = 'aes-256-gcm';
  private readonly hashAlgorithm = 'sha256';

  // Chain variables for tamper detection
  private lastEventHash: string | null = null;
  private chainIntegrityHash: string | null = null;

  constructor(signingKey: string, encryptionKey: string) {
    this.signingKey = signingKey;
    this.encryptionKey = Buffer.from(encryptionKey, 'hex');

    if (this.encryptionKey.length !== 32) {
      throw new Error('Encryption key must be 32 bytes (64 hex characters)');
    }

    this.initializeChain();
  }

  /**
   * Initialize the audit chain
   */
  private initializeChain(): void {
    // Genesis block for the audit chain
    const genesisData = {
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      system: 'PAKE-Audit',
      type: 'genesis',
    };

    this.lastEventHash = this.calculateHash(JSON.stringify(genesisData));
    this.chainIntegrityHash = this.lastEventHash;

    this.logger.info('Audit chain initialized', {
      genesisHash: this.lastEventHash.substring(0, 16) + '...',
    });
  }

  /**
   * Sign and secure an audit event
   */
  async signAuditEvent(
    event: Omit<AuditEvent, 'signature'>
  ): Promise<AuditEvent> {
    try {
      // Create event with previous hash for chaining
      const eventWithChain = {
        ...event,
        previousHash: this.lastEventHash,
        chainIntegrity: this.chainIntegrityHash,
      };

      // Calculate event hash
      const eventData = this.normalizeEventData(eventWithChain);
      const eventHash = this.calculateHash(eventData);

      // Create digital signature
      const signature = this.createDigitalSignature(eventData);

      // Update chain state
      this.lastEventHash = eventHash;
      this.chainIntegrityHash = this.calculateHash(
        `${this.chainIntegrityHash}:${eventHash}`
      );

      const signedEvent: AuditEvent = {
        ...event,
        signature: signature,
      };

      this.logger.debug('Audit event signed', {
        eventId: event.id,
        hash: eventHash.substring(0, 16) + '...',
      });

      return signedEvent;
    } catch (error) {
      this.logger.error('Failed to sign audit event', {
        eventId: event.id,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Verify the integrity of an audit event
   */
  async verifyAuditEvent(
    event: AuditEvent,
    previousHash?: string
  ): Promise<boolean> {
    try {
      if (!event.signature) {
        return false;
      }

      // Reconstruct event data for verification
      const { signature, ...eventWithoutSignature } = event;
      const eventWithChain = {
        ...eventWithoutSignature,
        previousHash: previousHash || null,
        chainIntegrity: this.chainIntegrityHash,
      };

      const eventData = this.normalizeEventData(eventWithChain);

      // Verify digital signature
      return this.verifyDigitalSignature(eventData, signature);
    } catch (error) {
      this.logger.error('Failed to verify audit event', {
        eventId: event.id,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Create a signed batch of events
   */
  async createSignedBatch(events: AuditEvent[]): Promise<AuditEventBatch> {
    try {
      const batchId = uuidv4();
      const timestamp = new Date().toISOString();

      // Calculate batch checksum
      const batchData = {
        batchId,
        timestamp,
        eventCount: events.length,
        events: events.map(e => e.id),
      };

      const checksum = this.calculateHash(JSON.stringify(batchData));

      // Create batch signature
      const batchSignature = this.createDigitalSignature(
        JSON.stringify(batchData)
      );

      const batch: AuditEventBatch = {
        events,
        batchId,
        timestamp,
        checksum: `${checksum}:${batchSignature}`,
      };

      this.logger.info('Signed audit batch created', {
        batchId,
        eventCount: events.length,
        checksum: checksum.substring(0, 16) + '...',
      });

      return batch;
    } catch (error) {
      this.logger.error('Failed to create signed batch', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Verify batch integrity
   */
  async verifyBatch(batch: AuditEventBatch): Promise<boolean> {
    try {
      const [checksum, signature] = batch.checksum.split(':');

      const batchData = {
        batchId: batch.batchId,
        timestamp: batch.timestamp,
        eventCount: batch.events.length,
        events: batch.events.map(e => e.id),
      };

      const calculatedChecksum = this.calculateHash(JSON.stringify(batchData));
      const checksumValid = calculatedChecksum === checksum;

      const signatureValid = this.verifyDigitalSignature(
        JSON.stringify(batchData),
        signature
      );

      return checksumValid && signatureValid;
    } catch (error) {
      this.logger.error('Failed to verify batch', {
        batchId: batch.batchId,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Encrypt sensitive audit data
   */
  encryptSensitiveData(data: any): string {
    try {
      const iv = crypto.randomBytes(16);
      const cipher = crypto.createCipher(this.algorithm, this.encryptionKey, {
        iv,
      });

      let encrypted = cipher.update(JSON.stringify(data), 'utf8', 'hex');
      encrypted += cipher.final('hex');

      const authTag = cipher.getAuthTag();

      return `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`;
    } catch (error) {
      this.logger.error('Failed to encrypt sensitive data', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Decrypt sensitive audit data
   */
  decryptSensitiveData(encryptedData: string): any {
    try {
      const [ivHex, authTagHex, encrypted] = encryptedData.split(':');

      const iv = Buffer.from(ivHex, 'hex');
      const authTag = Buffer.from(authTagHex, 'hex');

      const decipher = crypto.createDecipher(
        this.algorithm,
        this.encryptionKey,
        { iv }
      );
      decipher.setAuthTag(authTag);

      let decrypted = decipher.update(encrypted, 'hex', 'utf8');
      decrypted += decipher.final('utf8');

      return JSON.parse(decrypted);
    } catch (error) {
      this.logger.error('Failed to decrypt sensitive data', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Generate tamper-evident seal for a collection of events
   */
  generateTamperSeal(events: AuditEvent[]): string {
    const sealData = {
      eventCount: events.length,
      firstEventId: events[0]?.id,
      lastEventId: events[events.length - 1]?.id,
      firstTimestamp: events[0]?.timestamp,
      lastTimestamp: events[events.length - 1]?.timestamp,
      combinedHash: this.calculateHash(events.map(e => e.signature).join('')),
    };

    const seal = this.calculateHash(JSON.stringify(sealData));
    const signature = this.createDigitalSignature(seal);

    return `${seal}:${signature}`;
  }

  /**
   * Verify tamper-evident seal
   */
  verifyTamperSeal(events: AuditEvent[], seal: string): boolean {
    try {
      const generatedSeal = this.generateTamperSeal(events);
      return generatedSeal === seal;
    } catch (error) {
      this.logger.error('Failed to verify tamper seal', {
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Detect chain tampering
   */
  detectChainTampering(
    events: AuditEvent[]
  ): Array<{ eventId: string; issue: string }> {
    const issues: Array<{ eventId: string; issue: string }> = [];

    if (events.length === 0) {
      return issues;
    }

    // Check temporal ordering
    for (let i = 1; i < events.length; i++) {
      const prevEvent = events[i - 1];
      const currEvent = events[i];

      if (new Date(currEvent.timestamp) < new Date(prevEvent.timestamp)) {
        issues.push({
          eventId: currEvent.id,
          issue:
            'Temporal ordering violation - event timestamp is before previous event',
        });
      }
    }

    // Check signature validity
    for (const event of events) {
      if (!event.signature) {
        issues.push({
          eventId: event.id,
          issue: 'Missing cryptographic signature',
        });
        continue;
      }

      // Note: Full chain verification would require previous hashes
      // This is a simplified check
      try {
        const isValid = this.verifyAuditEvent(event);
        if (!isValid) {
          issues.push({
            eventId: event.id,
            issue: 'Invalid cryptographic signature',
          });
        }
      } catch (error) {
        issues.push({
          eventId: event.id,
          issue: `Signature verification error: ${error.message}`,
        });
      }
    }

    // Check for duplicate event IDs
    const eventIds = new Set();
    for (const event of events) {
      if (eventIds.has(event.id)) {
        issues.push({
          eventId: event.id,
          issue: 'Duplicate event ID detected',
        });
      }
      eventIds.add(event.id);
    }

    return issues;
  }

  /**
   * Normalize event data for consistent hashing
   */
  private normalizeEventData(event: any): string {
    // Create a normalized representation of the event
    const normalized = {
      id: event.id,
      timestamp: event.timestamp,
      actor: {
        id: event.actor.id,
        type: event.actor.type,
        ip: event.actor.ip || null,
        session: event.actor.session || null,
      },
      action: {
        type: event.action.type,
        resource: event.action.resource,
        resourceId: event.action.resourceId || null,
        result: event.action.result,
      },
      context: event.context,
      version: event.version,
      previousHash: event.previousHash || null,
    };

    return JSON.stringify(normalized, Object.keys(normalized).sort());
  }

  /**
   * Calculate cryptographic hash
   */
  private calculateHash(data: string): string {
    return crypto.createHash(this.hashAlgorithm).update(data).digest('hex');
  }

  /**
   * Create digital signature using HMAC
   */
  private createDigitalSignature(data: string): string {
    return crypto
      .createHmac(this.hashAlgorithm, this.signingKey)
      .update(data)
      .digest('hex');
  }

  /**
   * Verify digital signature
   */
  private verifyDigitalSignature(data: string, signature: string): boolean {
    const calculatedSignature = this.createDigitalSignature(data);
    return crypto.timingSafeEqual(
      Buffer.from(calculatedSignature, 'hex'),
      Buffer.from(signature, 'hex')
    );
  }

  /**
   * Generate audit report with integrity proof
   */
  async generateIntegrityReport(events: AuditEvent[]): Promise<{
    summary: {
      totalEvents: number;
      integrityStatus: 'verified' | 'compromised' | 'unknown';
      issues: Array<{ eventId: string; issue: string }>;
    };
    proof: {
      tamperSeal: string;
      chainHash: string;
      generatedAt: string;
      signature: string;
    };
  }> {
    const issues = this.detectChainTampering(events);
    const tamperSeal = events.length > 0 ? this.generateTamperSeal(events) : '';
    const chainHash = this.calculateHash(events.map(e => e.id).join(':'));

    const report = {
      summary: {
        totalEvents: events.length,
        integrityStatus:
          issues.length === 0 ? 'verified' : ('compromised' as const),
        issues,
      },
      proof: {
        tamperSeal,
        chainHash,
        generatedAt: new Date().toISOString(),
        signature: '',
      },
    };

    // Sign the report itself
    report.proof.signature = this.createDigitalSignature(
      JSON.stringify(report.summary) +
        report.proof.chainHash +
        report.proof.generatedAt
    );

    return report;
  }

  /**
   * Get current chain state for monitoring
   */
  getChainState(): {
    lastEventHash: string | null;
    chainIntegrityHash: string | null;
    initialized: boolean;
  } {
    return {
      lastEventHash: this.lastEventHash,
      chainIntegrityHash: this.chainIntegrityHash,
      initialized: this.lastEventHash !== null,
    };
  }
}
