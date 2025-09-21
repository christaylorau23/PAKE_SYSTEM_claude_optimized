export interface Microsoft365Config {
  clientId: string;
  clientSecret: string;
  tenantId: string;
  redirectUri: string;
  scopes: string[];
}

export interface SharePointSite {
  id: string;
  name: string;
  url: string;
  description: string;
  createdAt: Date;
  modifiedAt: Date;
}

export interface SharePointDocument {
  id: string;
  name: string;
  url: string;
  size: number;
  mimeType: string;
  createdAt: Date;
  modifiedAt: Date;
  author: string;
  downloadUrl?: string;
}

export interface OutlookMessage {
  id: string;
  subject: string;
  bodyPreview: string;
  from: {
    name: string;
    address: string;
  };
  receivedDateTime: Date;
  isRead: boolean;
  importance: 'low' | 'normal' | 'high';
  hasAttachments: boolean;
}

export interface OutlookCalendarEvent {
  id: string;
  subject: string;
  body: {
    contentType: string;
    content: string;
  };
  start: {
    dateTime: string;
    timeZone: string;
  };
  end: {
    dateTime: string;
    timeZone: string;
  };
  location: {
    displayName: string;
  };
  attendees: Array<{
    emailAddress: {
      name: string;
      address: string;
    };
    status: {
      response: string;
      time: string;
    };
  }>;
  organizer: {
    emailAddress: {
      name: string;
      address: string;
    };
  };
}

export interface TeamsChannel {
  id: string;
  teamId: string;
  displayName: string;
  description: string;
  createdDateTime: Date;
  membershipType: 'standard' | 'private';
}

export interface TeamsMessage {
  id: string;
  body: {
    contentType: string;
    content: string;
  };
  from: {
    user: {
      id: string;
      displayName: string;
      userIdentityType: string;
    };
  };
  createdDateTime: Date;
  importance: 'normal' | 'high' | 'urgent';
  messageType: 'message' | 'chatMessage' | 'typing';
}

export interface OneDriveItem {
  id: string;
  name: string;
  size: number;
  createdDateTime: Date;
  lastModifiedDateTime: Date;
  webUrl: string;
  downloadUrl?: string;
  file?: {
    mimeType: string;
    hashes: {
      quickXorHash?: string;
      sha1Hash?: string;
      sha256Hash?: string;
    };
  };
  folder?: {
    childCount: number;
  };
  createdBy: {
    user: {
      displayName: string;
      id: string;
    };
  };
  lastModifiedBy: {
    user: {
      displayName: string;
      id: string;
    };
  };
}

export interface Microsoft365User {
  id: string;
  displayName: string;
  mail: string;
  userPrincipalName: string;
  givenName: string;
  surname: string;
  jobTitle?: string;
  department?: string;
  officeLocation?: string;
  mobilePhone?: string;
  businessPhones: string[];
}

export interface Microsoft365Group {
  id: string;
  displayName: string;
  description?: string;
  mail?: string;
  mailNickname: string;
  createdDateTime: Date;
  groupTypes: string[];
  membershipRule?: string;
  membershipRuleProcessingState?: string;
  visibility: 'Private' | 'Public' | 'HiddenMembership';
}

export interface Microsoft365Subscription {
  id: string;
  resource: string;
  changeType: string;
  clientState?: string;
  notificationUrl: string;
  expirationDateTime: Date;
  applicationId: string;
  creatorId: string;
}

export interface Microsoft365WebhookNotification {
  subscriptionId: string;
  changeType: string;
  clientState?: string;
  resource: string;
  resourceData: {
    id: string;
    '@odata.type': string;
    '@odata.id': string;
  };
  subscriptionExpirationDateTime: Date;
  tenantId: string;
}

export interface GraphBatchRequest {
  id: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  url: string;
  headers?: Record<string, string>;
  body?: any;
}

export interface GraphBatchResponse {
  id: string;
  status: number;
  headers?: Record<string, string>;
  body: any;
}

export interface Microsoft365SyncOptions {
  entityTypes: (
    | 'files'
    | 'emails'
    | 'calendar'
    | 'teams'
    | 'users'
    | 'groups'
  )[];
  batchSize: number;
  maxRetries: number;
  syncMode: 'full' | 'incremental' | 'delta';
  filters?: {
    dateRange?: {
      start: Date;
      end: Date;
    };
    fileTypes?: string[];
    siteIds?: string[];
    teamIds?: string[];
  };
}

export interface Microsoft365Metrics {
  apiCalls: number;
  dataTransferred: number;
  rateLimitHits: number;
  errors: number;
  avgResponseTime: number;
  successRate: number;
  lastSyncTime?: Date;
  totalRecordsSynced: number;
}
