import { Client } from '@microsoft/microsoft-graph-client';
import { AuthenticationProvider } from '@azure/msal-node';
import { BaseProvider } from '../base/BaseProvider';
import {
  IntegrationProvider,
  ConnectionCredentials,
  SyncOperation,
  IntegrationData,
  AuthType,
} from '../../types/integration';
import {
  Microsoft365Config,
  SharePointSite,
  OutlookMessage,
  TeamsChannel,
} from './types';
import { Logger } from '../../utils/logger';

export class Microsoft365Provider extends BaseProvider {
  private graphClient: Client | null = null;
  private config: Microsoft365Config;
  private logger = Logger.getInstance();

  constructor(config: Microsoft365Config) {
    super();
    this.config = config;
  }

  getProviderInfo(): IntegrationProvider {
    return {
      id: 'microsoft-365',
      name: 'Microsoft 365',
      category: 'productivity',
      type: 'api',
      version: '1.0.0',
      description: 'Complete Microsoft 365 integration with Graph API access',
      capabilities: {
        read: true,
        write: true,
        delete: true,
        subscribe: true,
        stream: true,
        batch: true,
        realtime: true,
        supportedOperations: [
          'sharepoint.sites.read',
          'sharepoint.files.read',
          'sharepoint.files.write',
          'outlook.mail.read',
          'outlook.mail.send',
          'outlook.calendar.read',
          'outlook.calendar.write',
          'teams.channels.read',
          'teams.messages.read',
          'teams.messages.write',
          'onedrive.files.read',
          'onedrive.files.write',
          'users.read',
          'groups.read',
        ],
        dataTypes: [
          'documents',
          'emails',
          'calendar_events',
          'chat_messages',
          'files',
          'users',
          'groups',
          'sites',
        ],
        maxBatchSize: 20,
        streamingTypes: ['teams.messages', 'outlook.mail'],
      },
      authentication: {
        type: 'oauth2' as AuthType,
        scopes: [
          'https://graph.microsoft.com/Sites.Read.All',
          'https://graph.microsoft.com/Sites.ReadWrite.All',
          'https://graph.microsoft.com/Files.ReadWrite.All',
          'https://graph.microsoft.com/Mail.Read',
          'https://graph.microsoft.com/Mail.Send',
          'https://graph.microsoft.com/Calendars.ReadWrite',
          'https://graph.microsoft.com/Team.ReadBasic.All',
          'https://graph.microsoft.com/ChannelMessage.Read.All',
          'https://graph.microsoft.com/User.Read.All',
          'https://graph.microsoft.com/Group.Read.All',
        ],
        endpoints: {
          authorize:
            'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
          token: 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
          refresh: 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
          userInfo: 'https://graph.microsoft.com/v1.0/me',
        },
        tokenStorage: {
          encrypted: true,
          location: 'database',
          keyPrefix: 'ms365_token',
        },
        refreshable: true,
        expirationTime: 3600,
      },
      rateLimit: {
        requestsPerSecond: 10,
        requestsPerMinute: 600,
        requestsPerHour: 10000,
        requestsPerDay: 100000,
        burstAllowance: 50,
        backoffStrategy: 'exponential',
        retryAttempts: 3,
      },
      webhook: {
        supportedEvents: [
          'mail.received',
          'calendar.created',
          'calendar.updated',
          'file.created',
          'file.modified',
          'teams.message.created',
        ],
        endpoint: '/webhooks/microsoft365',
        verificationMethod: 'hmac',
        maxRetries: 3,
        retryInterval: 5000,
      },
      isActive: true,
      metadata: {
        baseUrl: 'https://graph.microsoft.com/v1.0',
        apiVersion: 'v1.0',
        documentation: 'https://docs.microsoft.com/graph/api/overview',
        status: 'active',
        supportLevel: 'full',
        lastUpdated: new Date(),
        maintainer: 'PAKE System',
        tags: ['microsoft', 'office365', 'productivity', 'collaboration'],
      },
    };
  }

  async initialize(credentials: ConnectionCredentials): Promise<void> {
    try {
      const authProvider = this.createAuthProvider(credentials);
      this.graphClient = Client.initWithMiddleware({ authProvider });

      await this.testConnection();
      this.logger.info('Microsoft 365 provider initialized successfully');
    } catch (error) {
      this.logger.error('Failed to initialize Microsoft 365 provider', error);
      throw error;
    }
  }

  async testConnection(): Promise<boolean> {
    if (!this.graphClient) {
      throw new Error('Graph client not initialized');
    }

    try {
      await this.graphClient.api('/me').get();
      return true;
    } catch (error) {
      this.logger.error('Microsoft 365 connection test failed', error);
      return false;
    }
  }

  // SharePoint Operations
  async getSharePointSites(): Promise<SharePointSite[]> {
    if (!this.graphClient) throw new Error('Graph client not initialized');

    try {
      const response = await this.graphClient
        .api('/sites')
        .select(
          'id,displayName,webUrl,description,createdDateTime,lastModifiedDateTime'
        )
        .get();

      return response.value.map((site: any) => ({
        id: site.id,
        name: site.displayName,
        url: site.webUrl,
        description: site.description || '',
        createdAt: new Date(site.createdDateTime),
        modifiedAt: new Date(site.lastModifiedDateTime),
      }));
    } catch (error) {
      this.logger.error('Failed to fetch SharePoint sites', error);
      throw error;
    }
  }

  async getSharePointFiles(
    siteId: string,
    driveId?: string
  ): Promise<IntegrationData[]> {
    if (!this.graphClient) throw new Error('Graph client not initialized');

    try {
      const endpoint = driveId
        ? `/sites/${siteId}/drives/${driveId}/root/children`
        : `/sites/${siteId}/drive/root/children`;

      const response = await this.graphClient
        .api(endpoint)
        .select(
          'id,name,size,createdDateTime,lastModifiedDateTime,webUrl,file,folder'
        )
        .get();

      return response.value.map((item: any) => ({
        id: item.id,
        sourceId: item.id,
        sourceProvider: 'microsoft-365',
        entityType: 'file',
        data: {
          name: item.name,
          size: item.size,
          webUrl: item.webUrl,
          isFolder: !!item.folder,
          mimeType: item.file?.mimeType,
          downloadUrl: item['@microsoft.graph.downloadUrl'],
        },
        metadata: {
          sourceTimestamp: new Date(item.lastModifiedDateTime),
          hash: item.eTag || '',
          size: item.size || 0,
          mimeType: item.file?.mimeType,
        },
        syncStatus: 'synced',
        version: 1,
        lastSynced: new Date(),
      }));
    } catch (error) {
      this.logger.error('Failed to fetch SharePoint files', error);
      throw error;
    }
  }

  // Outlook Operations
  async getOutlookMessages(
    folderId = 'inbox',
    top = 50
  ): Promise<OutlookMessage[]> {
    if (!this.graphClient) throw new Error('Graph client not initialized');

    try {
      const response = await this.graphClient
        .api(`/me/mailFolders/${folderId}/messages`)
        .select(
          'id,subject,bodyPreview,from,receivedDateTime,isRead,importance,hasAttachments'
        )
        .top(top)
        .orderby('receivedDateTime desc')
        .get();

      return response.value.map((message: any) => ({
        id: message.id,
        subject: message.subject,
        bodyPreview: message.bodyPreview,
        from: message.from?.emailAddress,
        receivedDateTime: new Date(message.receivedDateTime),
        isRead: message.isRead,
        importance: message.importance,
        hasAttachments: message.hasAttachments,
      }));
    } catch (error) {
      this.logger.error('Failed to fetch Outlook messages', error);
      throw error;
    }
  }

  async sendOutlookMessage(
    to: string[],
    subject: string,
    body: string
  ): Promise<string> {
    if (!this.graphClient) throw new Error('Graph client not initialized');

    try {
      const message = {
        subject,
        body: {
          contentType: 'HTML',
          content: body,
        },
        toRecipients: to.map(email => ({
          emailAddress: { address: email },
        })),
      };

      const response = await this.graphClient
        .api('/me/sendMail')
        .post({ message });

      return response.id || 'sent';
    } catch (error) {
      this.logger.error('Failed to send Outlook message', error);
      throw error;
    }
  }

  // Teams Operations
  async getTeamsChannels(teamId: string): Promise<TeamsChannel[]> {
    if (!this.graphClient) throw new Error('Graph client not initialized');

    try {
      const response = await this.graphClient
        .api(`/teams/${teamId}/channels`)
        .select('id,displayName,description,createdDateTime,membershipType')
        .get();

      return response.value.map((channel: any) => ({
        id: channel.id,
        teamId,
        displayName: channel.displayName,
        description: channel.description || '',
        createdDateTime: new Date(channel.createdDateTime),
        membershipType: channel.membershipType,
      }));
    } catch (error) {
      this.logger.error('Failed to fetch Teams channels', error);
      throw error;
    }
  }

  async getTeamsMessages(
    teamId: string,
    channelId: string,
    top = 20
  ): Promise<IntegrationData[]> {
    if (!this.graphClient) throw new Error('Graph client not initialized');

    try {
      const response = await this.graphClient
        .api(`/teams/${teamId}/channels/${channelId}/messages`)
        .select('id,body,from,createdDateTime,importance,messageType')
        .top(top)
        .orderby('createdDateTime desc')
        .get();

      return response.value.map((message: any) => ({
        id: message.id,
        sourceId: message.id,
        sourceProvider: 'microsoft-365',
        entityType: 'teams_message',
        data: {
          body: message.body,
          from: message.from,
          messageType: message.messageType,
          importance: message.importance,
          teamId,
          channelId,
        },
        metadata: {
          sourceTimestamp: new Date(message.createdDateTime),
          hash: message.etag || '',
          size: JSON.stringify(message.body).length,
        },
        syncStatus: 'synced',
        version: 1,
        lastSynced: new Date(),
      }));
    } catch (error) {
      this.logger.error('Failed to fetch Teams messages', error);
      throw error;
    }
  }

  // Calendar Operations
  async getCalendarEvents(
    startTime?: Date,
    endTime?: Date
  ): Promise<IntegrationData[]> {
    if (!this.graphClient) throw new Error('Graph client not initialized');

    try {
      let query = this.graphClient
        .api('/me/events')
        .select(
          'id,subject,body,start,end,location,attendees,organizer,createdDateTime'
        );

      if (startTime && endTime) {
        query = query.filter(
          `start/dateTime ge '${startTime.toISOString()}' and end/dateTime le '${endTime.toISOString()}'`
        );
      }

      const response = await query.get();

      return response.value.map((event: any) => ({
        id: event.id,
        sourceId: event.id,
        sourceProvider: 'microsoft-365',
        entityType: 'calendar_event',
        data: {
          subject: event.subject,
          body: event.body,
          start: event.start,
          end: event.end,
          location: event.location,
          attendees: event.attendees,
          organizer: event.organizer,
        },
        metadata: {
          sourceTimestamp: new Date(event.createdDateTime),
          hash: event.id,
          size: JSON.stringify(event).length,
        },
        syncStatus: 'synced',
        version: 1,
        lastSynced: new Date(),
      }));
    } catch (error) {
      this.logger.error('Failed to fetch calendar events', error);
      throw error;
    }
  }

  // Batch Operations
  async executeBatchRequest(requests: any[]): Promise<any[]> {
    if (!this.graphClient) throw new Error('Graph client not initialized');

    try {
      const batchRequests = requests.map((req, index) => ({
        id: index.toString(),
        method: req.method || 'GET',
        url: req.url,
        body: req.body,
        headers: req.headers || {},
      }));

      const response = await this.graphClient
        .api('/$batch')
        .post({ requests: batchRequests });

      return response.responses;
    } catch (error) {
      this.logger.error('Failed to execute batch request', error);
      throw error;
    }
  }

  // Sync Operations
  async performSync(operation: SyncOperation): Promise<IntegrationData[]> {
    const { entityType, direction } = operation;
    let results: IntegrationData[] = [];

    try {
      switch (entityType) {
        case 'sharepoint_files': {
          const sites = await this.getSharePointSites();
          for (const site of sites.slice(0, 5)) {
            const files = await this.getSharePointFiles(site.id);
            results.push(...files);
          }
          break;
        }

        case 'outlook_messages': {
          const messages = await this.getOutlookMessages();
          results = messages.map(msg => ({
            id: msg.id,
            sourceId: msg.id,
            sourceProvider: 'microsoft-365',
            entityType: 'email',
            data: msg,
            metadata: {
              sourceTimestamp: msg.receivedDateTime,
              hash: msg.id,
              size: (msg.bodyPreview || '').length,
            },
            syncStatus: 'synced',
            version: 1,
            lastSynced: new Date(),
          }));
          break;
        }

        case 'calendar_events':
          results = await this.getCalendarEvents();
          break;

        default:
          throw new Error(`Unsupported entity type: ${entityType}`);
      }

      this.logger.info(`Synced ${results.length} ${entityType} records`);
      return results;
    } catch (error) {
      this.logger.error(`Sync failed for ${entityType}`, error);
      throw error;
    }
  }

  private createAuthProvider(
    credentials: ConnectionCredentials
  ): AuthenticationProvider {
    return {
      getAccessToken: async () => {
        if (!credentials.accessToken) {
          throw new Error('No access token available');
        }
        return credentials.accessToken;
      },
    };
  }

  async disconnect(): Promise<void> {
    this.graphClient = null;
    this.logger.info('Microsoft 365 provider disconnected');
  }
}
