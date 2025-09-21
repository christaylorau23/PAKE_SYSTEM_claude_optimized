/**
 * PAKE System - Queue Connector
 *
 * MCP-like connector for message queue operations supporting multiple
 * queue backends (Redis, RabbitMQ, SQS) with unified interface.
 */

import Redis from 'ioredis';
import amqp from 'amqplib';
import AWS from 'aws-sdk';
import { EventEmitter } from 'events';
import {
  Connector,
  ConnectorRequest,
  ConnectorRequestType,
  ResponseEnvelope,
  ResponseStatus,
  ConnectorConfig,
} from './Connector';

export interface QueueConfig extends ConnectorConfig {
  // Queue backend type
  backend: 'redis' | 'rabbitmq' | 'sqs';

  // Connection settings
  host?: string;
  port?: number;
  username?: string;
  REDACTED_SECRET?: string;

  // Redis specific
  redis?: {
    host: string;
    port: number;
    REDACTED_SECRET?: string;
    db?: number;
    keyPrefix?: string;
  };

  // RabbitMQ specific
  rabbitmq?: {
    url: string;
    exchange?: string;
    exchangeType?: string;
    durable?: boolean;
    autoDelete?: boolean;
  };

  // AWS SQS specific
  sqs?: {
    region: string;
    accessKeyId?: string;
    secretAccessKey?: string;
    queueUrlPrefix?: string;
  };

  // Message handling
  maxMessageSize: number;
  visibilityTimeout: number;
  messageRetention: number;
  deadLetterQueue?: string;

  // Consumer settings
  prefetchCount: number;
  batchSize: number;
  waitTimeSeconds: number;
}

export interface QueueMessage {
  id: string;
  body: any;
  attributes?: Record<string, any>;
  metadata: {
    timestamp: string;
    source: string;
    contentType?: string;
    encoding?: string;
    priority?: number;
    expiration?: string;
    correlationId?: string;
    replyTo?: string;
  };
}

export interface PublishResult {
  messageId: string;
  timestamp: string;
  queue: string;
  success: boolean;
}

export interface ConsumeResult {
  messages: QueueMessage[];
  hasMore: boolean;
  nextToken?: string;
}

/**
 * Universal queue connector supporting multiple backends
 */
export class QueueConnector extends Connector {
  private backend: 'redis' | 'rabbitmq' | 'sqs';
  private client: Redis | amqp.Connection | AWS.SQS | null = null;
  private channel: amqp.Channel | null = null;

  // Active consumers
  private consumers = new Map<string, EventEmitter>();
  private consumerTags = new Map<string, string>();

  constructor(name: string, config: Partial<QueueConfig> = {}) {
    const queueConfig: QueueConfig = {
      ...config,
      backend: config.backend || 'redis',
      maxMessageSize: config.maxMessageSize || 256 * 1024, // 256KB
      visibilityTimeout: config.visibilityTimeout || 30,
      messageRetention: config.messageRetention || 1209600, // 14 days
      prefetchCount: config.prefetchCount || 10,
      batchSize: config.batchSize || 10,
      waitTimeSeconds: config.waitTimeSeconds || 5,
    } as QueueConfig;

    super(name, queueConfig);

    this.backend = queueConfig.backend;

    this.logger.info('QueueConnector initialized', {
      backend: this.backend,
      maxMessageSize: queueConfig.maxMessageSize,
    });
  }

  /**
   * Fetch data using queue operations
   */
  async fetch<T = any>(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<T>> {
    this.validateRequest(request);
    const startTime = Date.now();

    try {
      switch (request.type) {
        case ConnectorRequestType.PUBLISH:
          return (await this.publishMessage(request)) as ResponseEnvelope<T>;

        case ConnectorRequestType.CONSUME:
          return (await this.consumeMessages(request)) as ResponseEnvelope<T>;

        case ConnectorRequestType.SUBSCRIBE:
          return (await this.subscribeToQueue(request)) as ResponseEnvelope<T>;

        case ConnectorRequestType.ACKNOWLEDGE:
          return (await this.acknowledgeMessage(
            request
          )) as ResponseEnvelope<T>;

        default:
          throw new Error(`Unsupported request type: ${request.type}`);
      }
    } catch (error) {
      const executionTime = Date.now() - startTime;
      return this.createErrorResponse(
        request,
        error as Error,
        this.mapErrorToStatus(error as Error),
        executionTime,
        this.isRetryableError(error as Error)
      );
    }
  }

  /**
   * Publish message to queue
   */
  private async publishMessage(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<PublishResult>> {
    const startTime = Date.now();
    const queueName = request.target;
    const message = request.parameters.message;

    this.validateMessageSize(message);

    this.logger.debug('Publishing message', {
      requestId: request.id,
      queue: queueName,
      messageSize: JSON.stringify(message).length,
    });

    let result: PublishResult;

    switch (this.backend) {
      case 'redis':
        result = await this.publishToRedis(
          queueName,
          message,
          request.parameters.options
        );
        break;

      case 'rabbitmq':
        result = await this.publishToRabbitMQ(
          queueName,
          message,
          request.parameters.options
        );
        break;

      case 'sqs':
        result = await this.publishToSQS(
          queueName,
          message,
          request.parameters.options
        );
        break;

      default:
        throw new Error(`Unsupported backend: ${this.backend}`);
    }

    const executionTime = Date.now() - startTime;

    this.logger.info('Message published', {
      requestId: request.id,
      messageId: result.messageId,
      queue: queueName,
      executionTime,
    });

    return this.createResponse(
      request,
      result,
      ResponseStatus.SUCCESS,
      executionTime,
      {
        recordCount: 1,
      }
    );
  }

  /**
   * Consume messages from queue
   */
  private async consumeMessages(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<ConsumeResult>> {
    const startTime = Date.now();
    const queueName = request.target;
    const options = request.parameters.options || {};

    this.logger.debug('Consuming messages', {
      requestId: request.id,
      queue: queueName,
      batchSize: options.batchSize || (this.config as QueueConfig).batchSize,
    });

    let result: ConsumeResult;

    switch (this.backend) {
      case 'redis':
        result = await this.consumeFromRedis(queueName, options);
        break;

      case 'rabbitmq':
        result = await this.consumeFromRabbitMQ(queueName, options);
        break;

      case 'sqs':
        result = await this.consumeFromSQS(queueName, options);
        break;

      default:
        throw new Error(`Unsupported backend: ${this.backend}`);
    }

    const executionTime = Date.now() - startTime;

    this.logger.debug('Messages consumed', {
      requestId: request.id,
      queue: queueName,
      messageCount: result.messages.length,
      hasMore: result.hasMore,
      executionTime,
    });

    return this.createResponse(
      request,
      result,
      ResponseStatus.SUCCESS,
      executionTime,
      {
        recordCount: result.messages.length,
        hasMore: result.hasMore,
        nextCursor: result.nextToken,
      }
    );
  }

  /**
   * Subscribe to queue for real-time message processing
   */
  private async subscribeToQueue(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<{ subscriptionId: string }>> {
    const startTime = Date.now();
    const queueName = request.target;
    const subscriptionId = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    this.logger.info('Creating subscription', {
      requestId: request.id,
      queue: queueName,
      subscriptionId,
    });

    const consumer = new EventEmitter();
    this.consumers.set(subscriptionId, consumer);

    switch (this.backend) {
      case 'redis':
        await this.subscribeToRedis(queueName, subscriptionId, consumer);
        break;

      case 'rabbitmq':
        await this.subscribeToRabbitMQ(queueName, subscriptionId, consumer);
        break;

      case 'sqs':
        await this.subscribeToSQS(queueName, subscriptionId, consumer);
        break;
    }

    const executionTime = Date.now() - startTime;

    return this.createResponse(
      request,
      { subscriptionId },
      ResponseStatus.SUCCESS,
      executionTime
    );
  }

  /**
   * Acknowledge message processing
   */
  private async acknowledgeMessage(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<{ acknowledged: boolean }>> {
    const startTime = Date.now();
    const messageId = request.parameters.messageId;
    const receiptHandle = request.parameters.receiptHandle;

    let acknowledged = false;

    switch (this.backend) {
      case 'redis':
        acknowledged = await this.acknowledgeRedisMessage(
          messageId,
          receiptHandle
        );
        break;

      case 'rabbitmq':
        acknowledged = await this.acknowledgeRabbitMQMessage(
          messageId,
          receiptHandle
        );
        break;

      case 'sqs':
        acknowledged = await this.acknowledgeSQSMessage(
          messageId,
          receiptHandle
        );
        break;
    }

    const executionTime = Date.now() - startTime;

    return this.createResponse(
      request,
      { acknowledged },
      ResponseStatus.SUCCESS,
      executionTime
    );
  }

  /**
   * Redis implementation methods
   */
  private async publishToRedis(
    queueName: string,
    message: any,
    options: any = {}
  ): Promise<PublishResult> {
    if (!this.client || !(this.client instanceof Redis)) {
      throw new Error('Redis client not initialized');
    }

    const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const queueMessage: QueueMessage = {
      id: messageId,
      body: message,
      attributes: options.attributes,
      metadata: {
        timestamp: new Date().toISOString(),
        source: this.name,
        contentType: options.contentType || 'application/json',
        priority: options.priority || 0,
        correlationId: options.correlationId,
      },
    };

    // Use Redis list for simple queue
    const serialized = JSON.stringify(queueMessage);
    await (this.client as Redis).lpush(queueName, serialized);

    return {
      messageId,
      timestamp: queueMessage.metadata.timestamp,
      queue: queueName,
      success: true,
    };
  }

  private async consumeFromRedis(
    queueName: string,
    options: any
  ): Promise<ConsumeResult> {
    if (!this.client || !(this.client instanceof Redis)) {
      throw new Error('Redis client not initialized');
    }

    const batchSize =
      options.batchSize || (this.config as QueueConfig).batchSize;
    const messages: QueueMessage[] = [];

    // Use blocking pop to wait for messages
    const waitTime =
      options.waitTime || (this.config as QueueConfig).waitTimeSeconds;

    for (let i = 0; i < batchSize; i++) {
      const result = await (this.client as Redis).brpop(queueName, waitTime);

      if (result) {
        const [, messageData] = result;
        try {
          const message: QueueMessage = JSON.parse(messageData);
          messages.push(message);
        } catch (error) {
          this.logger.warn('Failed to parse message from Redis', {
            error: (error as Error).message,
            messageData: messageData.substring(0, 100),
          });
        }
      } else {
        break; // No more messages
      }
    }

    return {
      messages,
      hasMore: messages.length === batchSize,
    };
  }

  private async subscribeToRedis(
    queueName: string,
    subscriptionId: string,
    consumer: EventEmitter
  ): Promise<void> {
    // Redis pub/sub for real-time notifications
    const subscriber = (this.client as Redis).duplicate();

    await subscriber.subscribe(queueName);

    subscriber.on('message', (channel, message) => {
      if (channel === queueName) {
        try {
          const queueMessage: QueueMessage = JSON.parse(message);
          consumer.emit('message', queueMessage);
        } catch (error) {
          consumer.emit('error', error);
        }
      }
    });

    this.consumerTags.set(subscriptionId, queueName);
  }

  private async acknowledgeRedisMessage(
    _messageId: string,
    _receiptHandle: string
  ): Promise<boolean> {
    // Redis doesn't have built-in acknowledgment, consider message processed
    return true;
  }

  /**
   * RabbitMQ implementation methods
   */
  private async publishToRabbitMQ(
    queueName: string,
    message: any,
    options: any = {}
  ): Promise<PublishResult> {
    if (!this.channel) {
      throw new Error('RabbitMQ channel not initialized');
    }

    const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const queueMessage: QueueMessage = {
      id: messageId,
      body: message,
      attributes: options.attributes,
      metadata: {
        timestamp: new Date().toISOString(),
        source: this.name,
        contentType: options.contentType || 'application/json',
        correlationId: options.correlationId,
      },
    };

    const buffer = Buffer.from(JSON.stringify(queueMessage));

    await this.channel.assertQueue(queueName, {
      durable: (this.config as QueueConfig).rabbitmq?.durable ?? true,
    });

    const published = this.channel.sendToQueue(queueName, buffer, {
      messageId,
      timestamp: Date.now(),
      persistent: true,
      priority: options.priority || 0,
      correlationId: options.correlationId,
    });

    return {
      messageId,
      timestamp: queueMessage.metadata.timestamp,
      queue: queueName,
      success: published,
    };
  }

  private async consumeFromRabbitMQ(
    queueName: string,
    options: any
  ): Promise<ConsumeResult> {
    if (!this.channel) {
      throw new Error('RabbitMQ channel not initialized');
    }

    await this.channel.assertQueue(queueName, { durable: true });
    await this.channel.prefetch(
      options.batchSize || (this.config as QueueConfig).prefetchCount
    );

    const messages: QueueMessage[] = [];
    const batchSize =
      options.batchSize || (this.config as QueueConfig).batchSize;

    for (let i = 0; i < batchSize; i++) {
      const msg = await this.channel.get(queueName, { noAck: false });

      if (msg) {
        try {
          const queueMessage: QueueMessage = JSON.parse(msg.content.toString());
          // Store delivery tag for acknowledgment
          queueMessage.attributes = {
            ...queueMessage.attributes,
            deliveryTag: msg.fields.deliveryTag,
          };
          messages.push(queueMessage);
        } catch (error) {
          this.logger.warn('Failed to parse message from RabbitMQ', {
            error: (error as Error).message,
          });
          // Reject invalid message
          this.channel.nack(msg, false, false);
        }
      } else {
        break; // No more messages
      }
    }

    return {
      messages,
      hasMore: messages.length === batchSize,
    };
  }

  private async subscribeToRabbitMQ(
    queueName: string,
    subscriptionId: string,
    consumer: EventEmitter
  ): Promise<void> {
    if (!this.channel) {
      throw new Error('RabbitMQ channel not initialized');
    }

    await this.channel.assertQueue(queueName, { durable: true });

    const consumerTag = await this.channel.consume(
      queueName,
      msg => {
        if (msg) {
          try {
            const queueMessage: QueueMessage = JSON.parse(
              msg.content.toString()
            );
            queueMessage.attributes = {
              ...queueMessage.attributes,
              deliveryTag: msg.fields.deliveryTag,
            };
            consumer.emit('message', queueMessage);
          } catch (error) {
            consumer.emit('error', error);
            this.channel?.nack(msg, false, false);
          }
        }
      },
      { noAck: false }
    );

    this.consumerTags.set(subscriptionId, consumerTag.consumerTag);
  }

  private async acknowledgeRabbitMQMessage(
    messageId: string,
    receiptHandle: string
  ): Promise<boolean> {
    if (!this.channel) {
      return false;
    }

    try {
      const deliveryTag = parseInt(receiptHandle);
      this.channel.ack({ fields: { deliveryTag } } as any);
      return true;
    } catch (error) {
      this.logger.error('Failed to acknowledge RabbitMQ message', {
        messageId,
        error: (error as Error).message,
      });
      return false;
    }
  }

  /**
   * AWS SQS implementation methods
   */
  private async publishToSQS(
    queueName: string,
    message: any,
    options: any = {}
  ): Promise<PublishResult> {
    if (!this.client || !(this.client instanceof AWS.SQS)) {
      throw new Error('SQS client not initialized');
    }

    const queueMessage: QueueMessage = {
      id: '', // SQS will assign ID
      body: message,
      attributes: options.attributes,
      metadata: {
        timestamp: new Date().toISOString(),
        source: this.name,
        contentType: options.contentType || 'application/json',
        correlationId: options.correlationId,
      },
    };

    const params: AWS.SQS.SendMessageRequest = {
      QueueUrl: queueName,
      MessageBody: JSON.stringify(queueMessage),
      MessageAttributes: options.messageAttributes || {},
    };

    if (options.delaySeconds) {
      params.DelaySeconds = options.delaySeconds;
    }

    const result = await (this.client as AWS.SQS).sendMessage(params).promise();

    return {
      messageId: result.MessageId || '',
      timestamp: queueMessage.metadata.timestamp,
      queue: queueName,
      success: !!result.MessageId,
    };
  }

  private async consumeFromSQS(
    queueName: string,
    options: any
  ): Promise<ConsumeResult> {
    if (!this.client || !(this.client instanceof AWS.SQS)) {
      throw new Error('SQS client not initialized');
    }

    const params: AWS.SQS.ReceiveMessageRequest = {
      QueueUrl: queueName,
      MaxNumberOfMessages: Math.min(
        options.batchSize || (this.config as QueueConfig).batchSize,
        10
      ),
      WaitTimeSeconds:
        options.waitTime || (this.config as QueueConfig).waitTimeSeconds,
      VisibilityTimeoutSeconds: (this.config as QueueConfig).visibilityTimeout,
      MessageAttributeNames: ['All'],
    };

    const result = await (this.client as AWS.SQS)
      .receiveMessage(params)
      .promise();
    const messages: QueueMessage[] = [];

    if (result.Messages) {
      for (const msg of result.Messages) {
        try {
          const queueMessage: QueueMessage = JSON.parse(msg.Body || '{}');
          queueMessage.id = msg.MessageId || '';
          queueMessage.attributes = {
            ...queueMessage.attributes,
            receiptHandle: msg.ReceiptHandle,
          };
          messages.push(queueMessage);
        } catch (error) {
          this.logger.warn('Failed to parse message from SQS', {
            messageId: msg.MessageId,
            error: (error as Error).message,
          });
        }
      }
    }

    return {
      messages,
      hasMore: messages.length === (params.MaxNumberOfMessages || 1),
    };
  }

  private async subscribeToSQS(
    queueName: string,
    subscriptionId: string,
    consumer: EventEmitter
  ): Promise<void> {
    // SQS long polling implementation
    const poll = async () => {
      try {
        const result = await this.consumeFromSQS(queueName, {
          batchSize: 1,
          waitTime: 20,
        });

        for (const message of result.messages) {
          consumer.emit('message', message);
        }

        // Continue polling if consumer is still active
        if (this.consumers.has(subscriptionId)) {
          setTimeout(poll, 100); // Small delay between polls
        }
      } catch (error) {
        consumer.emit('error', error);

        if (this.consumers.has(subscriptionId)) {
          setTimeout(poll, 5000); // Retry after error with longer delay
        }
      }
    };

    // Start polling
    poll();
    this.consumerTags.set(subscriptionId, 'sqs-polling');
  }

  private async acknowledgeSQSMessage(
    messageId: string,
    receiptHandle: string
  ): Promise<boolean> {
    if (!this.client || !(this.client instanceof AWS.SQS) || !receiptHandle) {
      return false;
    }

    try {
      await (this.client as AWS.SQS)
        .deleteMessage({
          QueueUrl: receiptHandle.split('|')[0], // Extract queue URL
          ReceiptHandle: receiptHandle,
        })
        .promise();

      return true;
    } catch (error) {
      this.logger.error('Failed to acknowledge SQS message', {
        messageId,
        error: (error as Error).message,
      });
      return false;
    }
  }

  /**
   * Utility methods
   */
  private validateMessageSize(message: any): void {
    const size = JSON.stringify(message).length;
    if (size > (this.config as QueueConfig).maxMessageSize) {
      throw new Error(
        `Message size ${size} exceeds limit ${(this.config as QueueConfig).maxMessageSize}`
      );
    }
  }

  private mapErrorToStatus(error: Error): ResponseStatus {
    const message = error.message.toLowerCase();

    if (message.includes('timeout')) {
      return ResponseStatus.TIMEOUT;
    }
    if (message.includes('connection') || message.includes('network')) {
      return ResponseStatus.SERVICE_UNAVAILABLE;
    }
    if (message.includes('unauthorized') || message.includes('access denied')) {
      return ResponseStatus.UNAUTHORIZED;
    }
    if (message.includes('forbidden')) {
      return ResponseStatus.FORBIDDEN;
    }
    if (message.includes('not found') || message.includes('does not exist')) {
      return ResponseStatus.NOT_FOUND;
    }

    return ResponseStatus.ERROR;
  }

  private isRetryableError(error: Error): boolean {
    const message = error.message.toLowerCase();

    return (
      message.includes('timeout') ||
      message.includes('connection') ||
      message.includes('network') ||
      message.includes('temporary')
    );
  }

  /**
   * Initialize connection based on backend
   */
  async connect(): Promise<void> {
    const config = this.config as QueueConfig;

    try {
      switch (this.backend) {
        case 'redis':
          this.client = new Redis(
            config.redis || {
              host: config.host || 'localhost',
              port: config.port || 6379,
              REDACTED_SECRET: config.REDACTED_SECRET,
            }
          );
          break;

        case 'rabbitmq':
          this.client = await amqp.connect(
            config.rabbitmq?.url ||
              `amqp://${config.username}:${config.REDACTED_SECRET}@${config.host || 'localhost'}:${config.port || 5672}`
          );
          this.channel = await (this.client as amqp.Connection).createChannel();
          break;

        case 'sqs':
          AWS.config.update(
            config.sqs || {
              region: 'us-east-1',
            }
          );
          this.client = new AWS.SQS();
          break;
      }

      this.isConnected = true;
      this.connectionHealth = 1.0;
      this.logger.info(`QueueConnector connected to ${this.backend}`);
    } catch (error) {
      this.isConnected = false;
      this.connectionHealth = 0.0;
      this.logger.error(`Failed to connect to ${this.backend}`, {
        error: (error as Error).message,
      });
      throw error;
    }
  }

  /**
   * Close connection
   */
  async disconnect(): Promise<void> {
    try {
      // Cancel all active consumers
      for (const [subscriptionId, consumer] of this.consumers) {
        consumer.removeAllListeners();

        const consumerTag = this.consumerTags.get(subscriptionId);
        if (this.backend === 'rabbitmq' && this.channel && consumerTag) {
          await this.channel.cancel(consumerTag);
        }
      }

      this.consumers.clear();
      this.consumerTags.clear();

      // Close connections
      if (this.client) {
        switch (this.backend) {
          case 'redis':
            (this.client as Redis).disconnect();
            break;

          case 'rabbitmq':
            if (this.channel) {
              await this.channel.close();
            }
            await (this.client as amqp.Connection).close();
            break;

          case 'sqs':
            // SQS client doesn't need explicit closing
            break;
        }
      }

      this.client = null;
      this.channel = null;
      this.isConnected = false;
      this.connectionHealth = 0.0;

      this.logger.info(`QueueConnector disconnected from ${this.backend}`);
    } catch (error) {
      this.logger.error('Error during disconnect', {
        error: (error as Error).message,
      });
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      switch (this.backend) {
        case 'redis':
          if (this.client && this.client instanceof Redis) {
            await (this.client as Redis).ping();
          }
          break;

        case 'rabbitmq':
          if (this.channel) {
            await this.channel.checkQueue('health-check-queue');
          }
          break;

        case 'sqs':
          if (this.client && this.client instanceof AWS.SQS) {
            await (this.client as AWS.SQS)
              .listQueues({ MaxResults: 1 })
              .promise();
          }
          break;
      }

      this.connectionHealth = 1.0;
      this.lastHealthCheck = Date.now();
      return true;
    } catch (error) {
      this.connectionHealth = 0.0;
      this.lastHealthCheck = Date.now();

      this.logger.warn(`Health check failed for ${this.backend}`, {
        error: (error as Error).message,
      });

      return false;
    }
  }

  /**
   * Get active consumer information
   */
  getConsumerStats(): {
    activeConsumers: number;
    consumerIds: string[];
    backend: string;
  } {
    return {
      activeConsumers: this.consumers.size,
      consumerIds: Array.from(this.consumers.keys()),
      backend: this.backend,
    };
  }
}
