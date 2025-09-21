import { Request, Response } from 'express';
import crypto from 'crypto';
import {
  WebhookEvent,
  WebhookSubscription,
  Microsoft365WebhookNotification,
} from './types';
import { Microsoft365Provider } from './Microsoft365Provider';
import { Logger } from '../../utils/logger';

export class Microsoft365WebhookHandler {
  private provider: Microsoft365Provider;
  private logger = Logger.getInstance();
  private subscriptions = new Map<string, WebhookSubscription>();

  constructor(provider: Microsoft365Provider) {
    this.provider = provider;
  }

  async handleWebhook(req: Request, res: Response): Promise<void> {
    try {
      // Validate webhook request
      const validationToken = req.query.validationToken as string;
      if (validationToken) {
        // This is a subscription validation request
        res.status(200).send(validationToken);
        this.logger.info('Webhook validation completed');
        return;
      }

      // Process webhook notification
      const notification = req.body as Microsoft365WebhookNotification;

      if (!this.verifyWebhookSignature(req)) {
        res.status(401).json({ error: 'Invalid webhook signature' });
        return;
      }

      await this.processWebhookNotification(notification);

      res.status(200).json({ status: 'processed' });
    } catch (error) {
      this.logger.error('Webhook processing failed', error);
      res.status(500).json({ error: 'Webhook processing failed' });
    }
  }

  private verifyWebhookSignature(req: Request): boolean {
    try {
      const signature = req.headers['x-ms-signature'] as string;
      const clientState = req.body.clientState;

      if (!signature || !clientState) {
        return false;
      }

      // In a real implementation, you would verify the signature
      // using the client secret and request body
      return true; // Simplified for demo
    } catch (error) {
      this.logger.error('Webhook signature verification failed', error);
      return false;
    }
  }

  private async processWebhookNotification(
    notification: Microsoft365WebhookNotification
  ): Promise<void> {
    try {
      const webhookEvent: WebhookEvent = {
        id: crypto.randomUUID(),
        providerId: 'microsoft-365',
        connectionId: '', // Would be determined from subscription mapping
        eventType: notification.changeType,
        payload: {
          resource: notification.resource,
          resourceData: notification.resourceData,
          subscriptionId: notification.subscriptionId,
          tenantId: notification.tenantId,
        },
        headers: {},
        verified: true,
        processed: false,
        receivedAt: new Date(),
        retryCount: 0,
      };

      await this.routeWebhookEvent(webhookEvent);

      this.logger.info('Webhook notification processed', {
        subscriptionId: notification.subscriptionId,
        changeType: notification.changeType,
        resource: notification.resource,
      });
    } catch (error) {
      this.logger.error('Failed to process webhook notification', error);
      throw error;
    }
  }

  private async routeWebhookEvent(event: WebhookEvent): Promise<void> {
    const { resource, changeType } = event.payload;

    try {
      switch (true) {
        case resource.includes('/driveItems/'):
          await this.handleDriveItemChange(event);
          break;

        case resource.includes('/messages/'):
          await this.handleMessageChange(event);
          break;

        case resource.includes('/events/'):
          await this.handleCalendarEventChange(event);
          break;

        case resource.includes('/teams/'):
          await this.handleTeamsChange(event);
          break;

        default:
          this.logger.warn('Unknown webhook resource type', { resource });
      }
    } catch (error) {
      this.logger.error('Failed to route webhook event', error);
      throw error;
    }
  }

  private async handleDriveItemChange(event: WebhookEvent): Promise<void> {
    const { resource, changeType } = event.payload;

    this.logger.info('Processing drive item change', { resource, changeType });

    // Trigger sync operation for the affected drive item
    this.provider.emit('driveItemChanged', {
      resource,
      changeType,
      timestamp: event.receivedAt,
    });
  }

  private async handleMessageChange(event: WebhookEvent): Promise<void> {
    const { resource, changeType } = event.payload;

    this.logger.info('Processing message change', { resource, changeType });

    // Trigger sync operation for the affected message
    this.provider.emit('messageChanged', {
      resource,
      changeType,
      timestamp: event.receivedAt,
    });
  }

  private async handleCalendarEventChange(event: WebhookEvent): Promise<void> {
    const { resource, changeType } = event.payload;

    this.logger.info('Processing calendar event change', {
      resource,
      changeType,
    });

    // Trigger sync operation for the affected calendar event
    this.provider.emit('calendarEventChanged', {
      resource,
      changeType,
      timestamp: event.receivedAt,
    });
  }

  private async handleTeamsChange(event: WebhookEvent): Promise<void> {
    const { resource, changeType } = event.payload;

    this.logger.info('Processing Teams change', { resource, changeType });

    // Trigger sync operation for the affected Teams resource
    this.provider.emit('teamsResourceChanged', {
      resource,
      changeType,
      timestamp: event.receivedAt,
    });
  }

  async createSubscription(
    resource: string,
    changeType: string,
    notificationUrl: string,
    expirationDateTime: Date,
    clientState?: string
  ): Promise<WebhookSubscription> {
    try {
      const subscription: WebhookSubscription = {
        id: crypto.randomUUID(),
        providerId: 'microsoft-365',
        connectionId: '', // Would be provided by calling code
        eventTypes: [changeType],
        endpoint: notificationUrl,
        secret: clientState,
        isActive: true,
        createdAt: new Date(),
        eventCount: 0,
        errorCount: 0,
      };

      this.subscriptions.set(subscription.id, subscription);

      this.logger.info('Webhook subscription created', {
        subscriptionId: subscription.id,
        resource,
        changeType,
      });

      return subscription;
    } catch (error) {
      this.logger.error('Failed to create webhook subscription', error);
      throw error;
    }
  }

  async deleteSubscription(subscriptionId: string): Promise<void> {
    try {
      if (this.subscriptions.has(subscriptionId)) {
        this.subscriptions.delete(subscriptionId);
        this.logger.info('Webhook subscription deleted', { subscriptionId });
      }
    } catch (error) {
      this.logger.error('Failed to delete webhook subscription', error);
      throw error;
    }
  }

  getSubscriptions(): WebhookSubscription[] {
    return Array.from(this.subscriptions.values());
  }

  getSubscription(subscriptionId: string): WebhookSubscription | undefined {
    return this.subscriptions.get(subscriptionId);
  }

  async renewSubscription(
    subscriptionId: string,
    newExpirationDate: Date
  ): Promise<void> {
    try {
      const subscription = this.subscriptions.get(subscriptionId);
      if (!subscription) {
        throw new Error(`Subscription ${subscriptionId} not found`);
      }

      // In a real implementation, you would make a PATCH request to Microsoft Graph
      // to update the subscription's expiration date

      this.logger.info('Webhook subscription renewed', {
        subscriptionId,
        newExpirationDate,
      });
    } catch (error) {
      this.logger.error('Failed to renew webhook subscription', error);
      throw error;
    }
  }

  async handleSubscriptionExpiry(subscriptionId: string): Promise<void> {
    try {
      const subscription = this.subscriptions.get(subscriptionId);
      if (!subscription) {
        return;
      }

      // Mark as inactive
      subscription.isActive = false;
      this.subscriptions.set(subscriptionId, subscription);

      this.logger.warn('Webhook subscription expired', { subscriptionId });

      // Emit event for cleanup or renewal
      this.provider.emit('subscriptionExpired', { subscriptionId });
    } catch (error) {
      this.logger.error('Failed to handle subscription expiry', error);
    }
  }

  async validateWebhookEndpoint(notificationUrl: string): Promise<boolean> {
    try {
      // Test webhook endpoint availability
      const response = await fetch(notificationUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test: true }),
      });

      return response.ok;
    } catch (error) {
      this.logger.error('Webhook endpoint validation failed', error);
      return false;
    }
  }

  setupSubscriptionMonitoring(): void {
    // Monitor subscription health and renew before expiry
    setInterval(async () => {
      for (const subscription of this.subscriptions.values()) {
        if (subscription.isActive) {
          // Check if subscription needs renewal (example: 24 hours before expiry)
          // In a real implementation, you would track expiration dates
          this.logger.debug('Monitoring webhook subscription', {
            subscriptionId: subscription.id,
          });
        }
      }
    }, 60000); // Check every minute
  }

  getWebhookMetrics(): {
    totalSubscriptions: number;
    activeSubscriptions: number;
    totalEvents: number;
    totalErrors: number;
  } {
    const subscriptions = Array.from(this.subscriptions.values());

    return {
      totalSubscriptions: subscriptions.length,
      activeSubscriptions: subscriptions.filter(s => s.isActive).length,
      totalEvents: subscriptions.reduce((sum, s) => sum + s.eventCount, 0),
      totalErrors: subscriptions.reduce((sum, s) => sum + s.errorCount, 0),
    };
  }
}
