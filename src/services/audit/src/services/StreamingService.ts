/**
 * Real-time Audit Streaming Service
 * Provides real-time streaming of audit events to SIEM systems
 */

import { Kafka, Producer, Consumer } from 'kafkajs';
import { Client } from '@elastic/elasticsearch';
import Redis from 'redis';
import { createWriteStream } from 'fs';
import {
  AuditEvent,
  SIEMIntegration,
  SIEMType,
  SIEMConfig,
} from '../types/audit.types';
import { AuditConfig } from '../types/audit.types';
import { Logger } from '../utils/logger';

interface StreamingMetrics {
  eventsSent: number;
  errorsCount: number;
  lastSentAt: Date | null;
  avgLatency: number;
  successRate: number;
}

export class StreamingService {
  private readonly logger = new Logger('StreamingService');
  private readonly config: AuditConfig;
  private readonly integrations: Map<string, SIEMIntegration> = new Map();
  private readonly producers: Map<string, any> = new Map();
  private readonly metrics: Map<string, StreamingMetrics> = new Map();

  private kafka?: Kafka;
  private redis?: Redis;
  private elasticsearch?: Client;

  constructor(config: AuditConfig) {
    this.config = config;
  }

  /**
   * Initialize streaming service
   */
  async initialize(): Promise<void> {
    try {
      // Initialize Kafka
      if (this.config.streaming.kafka) {
        this.kafka = new Kafka({
          clientId: this.config.streaming.kafka.clientId,
          brokers: this.config.streaming.kafka.brokers,
        });
      }

      // Initialize Redis
      if (this.config.streaming.redis) {
        this.redis = Redis.createClient({
          host: this.config.streaming.redis.host,
          port: this.config.streaming.redis.port,
          REDACTED_SECRET: this.config.streaming.redis.REDACTED_SECRET,
        });

        this.redis.on('error', err => {
          this.logger.error('Redis connection error', { error: err.message });
        });

        await this.redis.connect();
      }

      this.logger.info('Streaming service initialized');
    } catch (error) {
      this.logger.error('Failed to initialize streaming service', {
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Add SIEM integration
   */
  async addIntegration(integration: SIEMIntegration): Promise<void> {
    try {
      this.integrations.set(integration.id, integration);

      // Initialize metrics
      this.metrics.set(integration.id, {
        eventsSent: 0,
        errorsCount: 0,
        lastSentAt: null,
        avgLatency: 0,
        successRate: 100,
      });

      // Initialize specific producer
      await this.initializeProducer(integration);

      this.logger.info('SIEM integration added', {
        integrationId: integration.id,
        type: integration.type,
      });
    } catch (error) {
      this.logger.error('Failed to add SIEM integration', {
        integrationId: integration.id,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Stream audit event to all active integrations
   */
  async streamEvent(event: AuditEvent): Promise<void> {
    const promises: Promise<void>[] = [];

    for (const [integrationId, integration] of this.integrations) {
      if (integration.enabled && integration.healthStatus !== 'failed') {
        promises.push(this.streamToIntegration(integration, event));
      }
    }

    try {
      await Promise.allSettled(promises);
    } catch (error) {
      this.logger.error('Error streaming events', {
        eventId: event.id,
        error: error.message,
      });
    }
  }

  /**
   * Stream batch of events
   */
  async streamBatch(events: AuditEvent[]): Promise<void> {
    const batchPromises: Promise<void>[] = [];

    for (const [integrationId, integration] of this.integrations) {
      if (integration.enabled && integration.healthStatus !== 'failed') {
        batchPromises.push(this.streamBatchToIntegration(integration, events));
      }
    }

    try {
      await Promise.allSettled(batchPromises);
    } catch (error) {
      this.logger.error('Error streaming event batch', {
        eventCount: events.length,
        error: error.message,
      });
    }
  }

  /**
   * Get streaming metrics for integration
   */
  getMetrics(integrationId: string): StreamingMetrics | null {
    return this.metrics.get(integrationId) || null;
  }

  /**
   * Get all streaming metrics
   */
  getAllMetrics(): Map<string, StreamingMetrics> {
    return new Map(this.metrics);
  }

  /**
   * Check health of all integrations
   */
  async checkHealth(): Promise<Map<string, 'healthy' | 'degraded' | 'failed'>> {
    const healthStatus = new Map<string, 'healthy' | 'degraded' | 'failed'>();

    for (const [integrationId, integration] of this.integrations) {
      try {
        const isHealthy = await this.checkIntegrationHealth(integration);
        healthStatus.set(integrationId, isHealthy ? 'healthy' : 'failed');

        // Update integration status
        integration.healthStatus = isHealthy ? 'healthy' : 'failed';
      } catch (error) {
        healthStatus.set(integrationId, 'failed');
        integration.healthStatus = 'failed';
        this.logger.warn('Integration health check failed', {
          integrationId,
          error: error.message,
        });
      }
    }

    return healthStatus;
  }

  /**
   * Initialize producer for specific integration
   */
  private async initializeProducer(
    integration: SIEMIntegration
  ): Promise<void> {
    switch (integration.type) {
      case SIEMType.KAFKA:
        if (this.kafka) {
          const producer = this.kafka.producer();
          await producer.connect();
          this.producers.set(integration.id, producer);
        }
        break;

      case SIEMType.ELASTICSEARCH:
        const esClient = new Client({
          node: integration.config.endpoint!,
          auth: {
            apiKey: integration.config.apiKey!,
          },
        });
        this.producers.set(integration.id, esClient);
        break;

      case SIEMType.SPLUNK:
        // Initialize Splunk HTTP Event Collector client
        const splunkConfig = {
          token: integration.config.token!,
          url: integration.config.endpoint!,
        };
        this.producers.set(integration.id, splunkConfig);
        break;

      case SIEMType.WEBHOOK:
        // No specific initialization needed for webhooks
        break;

      default:
        this.logger.warn('Unknown SIEM type', { type: integration.type });
    }
  }

  /**
   * Stream event to specific integration
   */
  private async streamToIntegration(
    integration: SIEMIntegration,
    event: AuditEvent
  ): Promise<void> {
    const startTime = Date.now();

    try {
      switch (integration.type) {
        case SIEMType.KAFKA:
          await this.streamToKafka(integration, event);
          break;

        case SIEMType.ELASTICSEARCH:
          await this.streamToElasticsearch(integration, event);
          break;

        case SIEMType.SPLUNK:
          await this.streamToSplunk(integration, event);
          break;

        case SIEMType.WEBHOOK:
          await this.streamToWebhook(integration, event);
          break;

        default:
          throw new Error(`Unsupported SIEM type: ${integration.type}`);
      }

      // Update metrics
      this.updateMetrics(integration.id, true, Date.now() - startTime);
    } catch (error) {
      this.updateMetrics(integration.id, false, Date.now() - startTime);
      this.logger.error('Failed to stream to integration', {
        integrationId: integration.id,
        type: integration.type,
        eventId: event.id,
        error: error.message,
      });
      throw error;
    }
  }

  /**
   * Stream batch to specific integration
   */
  private async streamBatchToIntegration(
    integration: SIEMIntegration,
    events: AuditEvent[]
  ): Promise<void> {
    const batchSize = integration.config.batchSize || 100;
    const batches = this.chunkArray(events, batchSize);

    for (const batch of batches) {
      await Promise.all(
        batch.map(event => this.streamToIntegration(integration, event))
      );

      // Rate limiting between batches
      if (integration.config.flushInterval) {
        await this.sleep(integration.config.flushInterval);
      }
    }
  }

  /**
   * Stream to Kafka
   */
  private async streamToKafka(
    integration: SIEMIntegration,
    event: AuditEvent
  ): Promise<void> {
    const producer = this.producers.get(integration.id) as Producer;

    if (!producer) {
      throw new Error('Kafka producer not initialized');
    }

    await producer.send({
      topic: integration.config.topic!,
      messages: [
        {
          key: event.id,
          value: JSON.stringify(event),
          headers: {
            'content-type': 'application/json',
            source: 'pake-audit',
          },
        },
      ],
    });
  }

  /**
   * Stream to Elasticsearch
   */
  private async streamToElasticsearch(
    integration: SIEMIntegration,
    event: AuditEvent
  ): Promise<void> {
    const client = this.producers.get(integration.id) as Client;

    if (!client) {
      throw new Error('Elasticsearch client not initialized');
    }

    await client.index({
      index: integration.config.index!,
      id: event.id,
      body: {
        ...event,
        '@timestamp': event.timestamp,
        source: 'pake-audit',
      },
    });
  }

  /**
   * Stream to Splunk
   */
  private async streamToSplunk(
    integration: SIEMIntegration,
    event: AuditEvent
  ): Promise<void> {
    const config = this.producers.get(integration.id);

    if (!config) {
      throw new Error('Splunk config not initialized');
    }

    const splunkEvent = {
      event: event,
      time: Math.floor(Date.parse(event.timestamp) / 1000),
      source: 'pake-audit',
      sourcetype: 'json',
      index: integration.config.index || 'main',
    };

    const response = await fetch(config.url, {
      method: 'POST',
      headers: {
        Authorization: `Splunk ${config.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(splunkEvent),
    });

    if (!response.ok) {
      throw new Error(`Splunk HTTP ${response.status}: ${response.statusText}`);
    }
  }

  /**
   * Stream to webhook
   */
  private async streamToWebhook(
    integration: SIEMIntegration,
    event: AuditEvent
  ): Promise<void> {
    const headers = {
      'Content-Type': 'application/json',
      ...integration.config.headers,
    };

    const response = await fetch(integration.config.webhookUrl!, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        event,
        source: 'pake-audit',
        timestamp: new Date().toISOString(),
      }),
    });

    if (!response.ok) {
      throw new Error(
        `Webhook HTTP ${response.status}: ${response.statusText}`
      );
    }
  }

  /**
   * Check integration health
   */
  private async checkIntegrationHealth(
    integration: SIEMIntegration
  ): Promise<boolean> {
    try {
      switch (integration.type) {
        case SIEMType.KAFKA:
          const producer = this.producers.get(integration.id) as Producer;
          return producer !== undefined;

        case SIEMType.ELASTICSEARCH:
          const client = this.producers.get(integration.id) as Client;
          if (client) {
            const response = await client.ping();
            return response.statusCode === 200;
          }
          return false;

        case SIEMType.WEBHOOK:
          const response = await fetch(integration.config.webhookUrl!, {
            method: 'HEAD',
            headers: integration.config.headers,
          });
          return response.ok;

        default:
          return true; // Assume healthy for unknown types
      }
    } catch (error) {
      return false;
    }
  }

  /**
   * Update metrics for integration
   */
  private updateMetrics(
    integrationId: string,
    success: boolean,
    latency: number
  ): void {
    const metrics = this.metrics.get(integrationId);

    if (metrics) {
      metrics.eventsSent++;
      metrics.lastSentAt = new Date();

      if (success) {
        // Update average latency using exponential moving average
        metrics.avgLatency = metrics.avgLatency * 0.9 + latency * 0.1;
      } else {
        metrics.errorsCount++;
      }

      // Calculate success rate (last 100 events)
      metrics.successRate =
        ((metrics.eventsSent - metrics.errorsCount) / metrics.eventsSent) * 100;
    }
  }

  /**
   * Utility function to chunk array
   */
  private chunkArray<T>(array: T[], size: number): T[][] {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  }

  /**
   * Utility function to sleep
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Remove integration
   */
  async removeIntegration(integrationId: string): Promise<void> {
    const integration = this.integrations.get(integrationId);

    if (!integration) {
      throw new Error(`Integration ${integrationId} not found`);
    }

    // Close producer connection
    const producer = this.producers.get(integrationId);
    if (producer && typeof producer.disconnect === 'function') {
      await producer.disconnect();
    }

    this.integrations.delete(integrationId);
    this.producers.delete(integrationId);
    this.metrics.delete(integrationId);

    this.logger.info('SIEM integration removed', { integrationId });
  }

  /**
   * Close all connections
   */
  async close(): Promise<void> {
    // Close all producers
    for (const [integrationId, producer] of this.producers) {
      try {
        if (producer && typeof producer.disconnect === 'function') {
          await producer.disconnect();
        }
      } catch (error) {
        this.logger.error('Error closing producer', {
          integrationId,
          error: error.message,
        });
      }
    }

    // Close Redis
    if (this.redis) {
      await this.redis.disconnect();
    }

    this.logger.info('Streaming service closed');
  }
}
