# PAKE System - Comprehensive Audit Service

A production-ready, enterprise-grade audit logging system providing tamper-proof audit trails, real-time SIEM streaming, compliance reporting, and advanced analytics for the PAKE ecosystem.

## 🚀 Features

### Core Capabilities

- **Tamper-Proof Audit Trails** - Cryptographic signatures and chain integrity verification
- **Multi-Tier Storage** - Hot (PostgreSQL), Warm (S3), Cold (Glacier) storage tiers
- **Real-Time SIEM Streaming** - Kafka, Elasticsearch, Splunk, webhook integrations
- **Compliance Reporting** - SOC2, HIPAA, GDPR, PCI-DSS automated reports
- **Data Retention Policies** - Automated archival with configurable retention rules
- **Advanced Analytics** - Anomaly detection and suspicious pattern recognition
- **High Performance** - <1ms overhead, zero lost events, 100% operation coverage

### Security Features

- **HMAC-SHA256 Signatures** - Every audit event cryptographically signed
- **Chain Integrity Verification** - Detect tampering across audit chains
- **Data Encryption** - AES-256-GCM encryption for sensitive audit data
- **Access Controls** - Role-based access to audit data and reports
- **Integrity Reporting** - Automated tamper detection and alerting

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Middleware Integration](#middleware-integration)
- [Compliance Reporting](#compliance-reporting)
- [Analytics & Monitoring](#analytics--monitoring)
- [Security](#security)
- [Performance](#performance)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ and npm 8+
- PostgreSQL 13+ (for hot storage)
- AWS Account (for S3/Glacier storage)
- Redis 6+ (for caching and sessions)
- Kafka (optional, for real-time streaming)

### Installation

```bash
# Clone and install dependencies
git clone <repository-url>
cd services/audit
npm install

# Build the service
npm run build
```

### Basic Usage

```typescript
import {
  CryptographicAuditService,
  AuditStorageService,
  StreamingService,
  AuditConfig,
} from '@pake/audit';

// Configure the audit system
const config: AuditConfig = {
  database: {
    host: 'localhost',
    port: 5432,
    name: 'audit_db',
    user: 'audit_user',
    REDACTED_SECRET: 'secure_database_REDACTED_SECRET',
    ssl: true,
    maxConnections: 20,
  },
  security: {
    signingKey: process.env.AUDIT_SIGNING_KEY,
    encryptionKey: process.env.AUDIT_ENCRYPTION_KEY,
    algorithm: 'aes-256-gcm',
  },
  storage: {
    s3: {
      region: 'us-west-2',
      bucket: 'company-audit-logs',
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
    },
  },
};

// Initialize services
const cryptoService = new CryptographicAuditService(
  config.security.signingKey,
  config.security.encryptionKey
);

const storageService = new AuditStorageService(config);
await storageService.initialize();

const streamingService = new StreamingService(config);
await streamingService.initialize();

// Log an audit event
const auditEvent = {
  id: 'event-001',
  timestamp: new Date().toISOString(),
  actor: {
    id: 'user-123',
    type: 'user',
    ip: '192.168.1.100',
  },
  action: {
    type: 'create',
    resource: 'document',
    resourceId: 'doc-456',
    result: 'success',
  },
  context: {
    environment: 'production',
    application: 'document-service',
    version: '2.1.0',
  },
  version: '1.0.0',
};

// Sign, store, and stream the event
const signedEvent = await cryptoService.signAuditEvent(auditEvent);
await storageService.storeEvent(signedEvent);
await streamingService.streamEvent(signedEvent);
```

## ⚙️ Configuration

### Environment Variables

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pake_audit
DB_USER=audit_user
DB_PASSWORD=secure_REDACTED_SECRET
DB_SSL=true
DB_MAX_CONNECTIONS=50

# Security Configuration
AUDIT_SIGNING_KEY=your-hmac-signing-key-here
AUDIT_ENCRYPTION_KEY=64-character-hex-encryption-key

# AWS Configuration
AWS_REGION=us-west-2
AWS_S3_BUCKET=company-audit-storage
AWS_GLACIER_VAULT=company-audit-archive
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Streaming Configuration
KAFKA_BROKERS=localhost:9092,localhost:9093
KAFKA_TOPIC=audit-events
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_REDACTED_SECRET

# Service Configuration
LOG_LEVEL=info
NODE_ENV=production
PORT=3002
```

### Configuration File

Create `config/audit.json`:

```json
{
  \"retention\": {
    \"hotStorageDays\": 30,
    \"warmStorageDays\": 90,
    \"coldStorageYears\": 7
  },
  \"compliance\": {
    \"enabled\": true,
    \"reports\": [\"soc2\", \"hipaa\", \"gdpr\"],
    \"alerting\": true,
    \"automatedReporting\": {
      \"soc2\": { \"schedule\": \"0 0 1 * *\" },
      \"gdpr\": { \"schedule\": \"0 0 1 */3 *\" }
    }
  },
  \"analytics\": {
    \"anomalyDetection\": true,
    \"behaviorProfiling\": true,
    \"alertThresholds\": {
      \"suspiciousActivity\": 70,
      \"criticalAlert\": 90
    }
  },
  \"performance\": {
    \"batchSize\": 1000,
    \"flushInterval\": 5000,
    \"maxRetries\": 3
  }
}
```

## 📡 API Reference

### Core Audit API

#### POST /api/audit/events

Log a single audit event.

```javascript
// Request
POST /api/audit/events
Content-Type: application/json

{
  \"id\": \"evt-123\",
  \"timestamp\": \"2024-01-15T10:30:00.000Z\",
  \"actor\": {
    \"id\": \"user-456\",
    \"type\": \"user\",
    \"ip\": \"192.168.1.100\",
    \"session\": \"sess-789\"
  },
  \"action\": {
    \"type\": \"update\",
    \"resource\": \"user_profile\",
    \"resourceId\": \"profile-123\",
    \"result\": \"success\",
    \"duration\": 150
  },
  \"context\": {
    \"requestId\": \"req-abc-123\",
    \"environment\": \"production\",
    \"application\": \"user-service\",
    \"version\": \"2.1.0\"
  },
  \"version\": \"1.0.0\"
}

// Response
{
  \"success\": true,
  \"eventId\": \"evt-123\",
  \"signature\": \"a1b2c3d4e5f6...\",
  \"stored\": true,
  \"streamed\": true
}
```

#### POST /api/audit/events/batch

Log multiple audit events efficiently.

```javascript
// Request
POST /api/audit/events/batch
Content-Type: application/json

{
  \"events\": [...], // Array of audit events
  \"batchId\": \"batch-456\"
}

// Response
{
  \"success\": true,
  \"batchId\": \"batch-456\",
  \"eventsProcessed\": 25,
  \"checksum\": \"batch-checksum-hash\"
}
```

#### GET /api/audit/events

Query audit events with filters.

```javascript
// Request
GET /api/audit/events?startTime=2024-01-01T00:00:00Z&endTime=2024-01-02T00:00:00Z&actorId=user-123&limit=100

// Response
{
  \"events\": [...],
  \"total\": 1250,
  \"page\": 1,
  \"hasMore\": true
}
```

### Compliance API

#### POST /api/compliance/reports/generate

Generate compliance reports.

```javascript
// Request
POST /api/compliance/reports/generate
Content-Type: application/json

{
  \"type\": \"soc2\",
  \"startDate\": \"2024-01-01T00:00:00Z\",
  \"endDate\": \"2024-01-31T23:59:59Z\",
  \"generatedBy\": \"compliance-officer\"
}

// Response
{
  \"reportId\": \"rpt-soc2-2024-01\",
  \"type\": \"soc2\",
  \"summary\": {
    \"totalEvents\": 125000,
    \"successfulActions\": 123500,
    \"failedActions\": 1500,
    \"securityIncidents\": 5
  },
  \"downloadUrl\": \"/api/compliance/reports/rpt-soc2-2024-01/download\"
}
```

#### GET /api/compliance/violations

Get compliance violations.

```javascript
// Response
{
  \"violations\": [
    {
      \"id\": \"viol-001\",
      \"type\": \"access_denied\",
      \"severity\": \"high\",
      \"timestamp\": \"2024-01-15T14:30:00Z\",
      \"description\": \"Unauthorized access attempt to sensitive resource\",
      \"event\": {...}
    }
  ]
}
```

### Analytics API

#### GET /api/analytics/dashboard

Get analytics dashboard data.

```javascript
// Response
{
  \"period\": {
    \"start\": \"2024-01-01T00:00:00Z\",
    \"end\": \"2024-01-07T23:59:59Z\"
  },
  \"metrics\": {
    \"totalEvents\": 75000,
    \"eventsPerHour\": [120, 150, 180, ...],
    \"errorRate\": 2.1,
    \"securityIncidents\": 3
  },
  \"trends\": {
    \"dailyVolume\": [...],
    \"topUsers\": [...],
    \"topResources\": [...]
  },
  \"alerts\": [...]
}
```

#### POST /api/analytics/detect

Run anomaly detection on events.

```javascript
// Request
POST /api/analytics/detect
{
  \"eventIds\": [\"evt-1\", \"evt-2\", \"evt-3\"],
  \"analysisType\": \"behavioral\"
}

// Response
{
  \"anomalies\": [
    {
      \"eventId\": \"evt-2\",
      \"score\": 85,
      \"reasons\": [\"Unusual time access\", \"New IP address\"],
      \"severity\": \"high\"
    }
  ]
}
```

## 🔧 Middleware Integration

### Express.js Integration

```typescript
import express from 'express';
import { createAuditMiddleware } from '@pake/audit';

const app = express();

// Setup audit middleware
app.use(
  createAuditMiddleware(cryptoService, storageService, streamingService, {
    excludePaths: ['/health', '/metrics'],
    includeRequestBody: true,
    includeResponseBody: false,
    sensitiveFields: ['REDACTED_SECRET', 'token', 'ssn', 'creditCard'],
    maxBodySize: 10000,
    asyncLogging: true,
  })
);

// Your application routes
app.get('/api/users', (req, res) => {
  // This request will be automatically audited
  res.json({ users: [] });
});
```

### FastAPI Integration (Python)

```python
from fastapi import FastAPI
from audit_integration import AuditMiddleware, AuditLogger

app = FastAPI()

# Setup audit logging
audit_logger = AuditLogger(
    audit_service_url=\"http://localhost:3002\",
    service_name=\"python-api\"
)

app.add_middleware(
    AuditMiddleware,
    audit_logger=audit_logger,
    exclude_paths=[\"/health\", \"/docs\"],
    include_request_body=True
)

@app.get(\"/api/data\")
async def get_data():
    # This request will be automatically audited
    return {\"data\": \"example\"}

# Manual audit logging
@app.post(\"/api/sensitive\")
async def sensitive_operation(request: Request):
    result = perform_sensitive_operation()

    # Log custom audit event
    await audit_logger.log_user_action(
        user_id=\"user-123\",
        action_type=\"export\",
        resource=\"sensitive_data\",
        result=\"success\" if result else \"failure\",
        request=request,
        metadata={\"recordCount\": 150, \"format\": \"csv\"}
    )

    return {\"success\": result}
```

## 📊 Compliance Reporting

### Automated Report Generation

```typescript
import { ComplianceReportingService } from '@pake/audit';

const complianceService = new ComplianceReportingService(
  storageService,
  cryptoService
);

// Generate SOC2 report
const soc2Report = await complianceService.generateSOC2Report(
  new Date('2024-01-01'),
  new Date('2024-01-31'),
  'compliance-officer@company.com'
);

console.log('SOC2 Report Generated:', {
  reportId: soc2Report.id,
  totalEvents: soc2Report.summary.totalEvents,
  securityIncidents: soc2Report.summary.securityIncidents,
  integrityVerified: await complianceService.verifyReport(soc2Report),
});

// Schedule automated reports
const scheduleReports = () => {
  // Monthly SOC2 reports
  cron.schedule('0 0 1 * *', async () => {
    const lastMonth = getLastMonthRange();
    await complianceService.generateSOC2Report(
      lastMonth.start,
      lastMonth.end,
      'system-automated'
    );
  });

  // Quarterly GDPR reports
  cron.schedule('0 0 1 */3 *', async () => {
    const lastQuarter = getLastQuarterRange();
    await complianceService.generateGDPRReport(
      lastQuarter.start,
      lastQuarter.end,
      'system-automated'
    );
  });
};
```

### Custom Compliance Checks

```typescript
// Define custom compliance rules
const customComplianceRules = [
  {
    name: 'Data Export Monitoring',
    description: 'Monitor all data export operations',
    condition: event => event.action.type === 'export',
    severity: 'medium',
    action: 'log_and_alert',
  },
  {
    name: 'Administrative Access',
    description: 'Track administrative privilege usage',
    condition: event => event.action.resource.includes('admin'),
    severity: 'high',
    action: 'immediate_alert',
  },
];

// Apply rules during report generation
const violations = await complianceService.getComplianceViolations(
  ComplianceReportType.CUSTOM,
  startDate,
  endDate
);
```

## 📈 Analytics & Monitoring

### Real-Time Monitoring Dashboard

```typescript
import { AuditAnalyticsService } from '@pake/audit';

const analyticsService = new AuditAnalyticsService(storageService);

// Get real-time metrics
const dashboard = async () => {
  const analytics = await analyticsService.generateAnalytics(
    new Date(Date.now() - 24 * 60 * 60 * 1000), // Last 24 hours
    new Date()
  );

  return {
    eventVolume: analytics.metrics.totalEvents,
    errorRate: analytics.metrics.errorRate,
    securityAlerts: analytics.metrics.securityIncidents,
    topUsers: analytics.metrics.topActors.slice(0, 10),
    anomalousActivity: analytics.anomalies.filter(a => a.severity === 'high'),
  };
};

// Setup alerting
analyticsService.onAlert = async alert => {
  if (alert.severity === 'critical') {
    await sendSlackAlert(alert);
    await sendEmailAlert(alert);
  }

  await logAlert(alert);
};
```

### Anomaly Detection

```typescript
// Configure detection rules
const anomalyRules = [
  {
    name: 'Rapid Failed Logins',
    pattern: {
      action: 'login',
      result: 'failure',
      timeWindow: 15, // minutes
      threshold: 5,
    },
    severity: 'high',
    response: 'block_ip',
  },
  {
    name: 'Unusual Data Access Volume',
    pattern: {
      action: 'read',
      resource: 'sensitive_data',
      volumeThreshold: 100, // events per hour
      timeWindow: 60,
    },
    severity: 'medium',
    response: 'flag_for_review',
  },
];

// Monitor for patterns
const monitorAnomalies = async () => {
  const recentEvents = await storageService.queryEvents({
    startTime: new Date(Date.now() - 60 * 60 * 1000), // Last hour
    limit: 10000,
  });

  const suspiciousPatterns =
    await analyticsService.detectSuspiciousPatterns(recentEvents);

  for (const pattern of suspiciousPatterns) {
    console.log(`🚨 Suspicious pattern detected: ${pattern.title}`);
    console.log(`   Severity: ${pattern.severity}`);
    console.log(`   Events: ${pattern.events.length}`);

    if (pattern.severity === 'critical') {
      await handleCriticalAlert(pattern);
    }
  }
};
```

## 🔒 Security

### Cryptographic Integrity

```typescript
// Verify audit chain integrity
const verifyAuditChain = async (events: AuditEvent[]) => {
  const integrityReport = await cryptoService.generateIntegrityReport(events);

  if (integrityReport.summary.integrityStatus === 'compromised') {
    console.error('🚨 AUDIT CHAIN COMPROMISED!');
    console.error('Issues found:', integrityReport.summary.issues);

    // Take immediate action
    await alertSecurityTeam(integrityReport);
    await freezeAuditChain();
    await investigateTampering(integrityReport);
  } else {
    console.log('✅ Audit chain integrity verified');
  }

  return integrityReport;
};

// Encrypt sensitive audit data
const handleSensitiveEvent = async (event: AuditEvent) => {
  if (containsSensitiveData(event)) {
    // Encrypt sensitive fields
    const sensitiveData = extractSensitiveData(event);
    const encrypted = cryptoService.encryptSensitiveData(sensitiveData);

    // Replace sensitive data with encrypted version
    event.action.metadata = {
      ...event.action.metadata,
      sensitiveData: encrypted,
      encrypted: true,
    };
  }

  return event;
};
```

### Access Control

```typescript
// Implement audit log access controls
const auditAccessControl = (req, res, next) => {
  const userRoles = req.user.roles;
  const requestedResource = req.params.resource;

  // Define access rules
  const accessRules = {
    audit_viewer: ['read'],
    audit_analyst: ['read', 'analyze'],
    audit_admin: ['read', 'analyze', 'export', 'configure'],
    compliance_officer: ['read', 'analyze', 'export', 'report'],
  };

  const allowedActions = userRoles.flatMap(role => accessRules[role] || []);

  if (!allowedActions.includes(req.method.toLowerCase())) {
    return res.status(403).json({ error: 'Insufficient permissions' });
  }

  // Log access attempt
  auditLogger.logUserAction(
    req.user.id,
    'access_audit_data',
    requestedResource,
    'success'
  );

  next();
};
```

## ⚡ Performance

### Optimization Configuration

```typescript
// High-performance configuration
const performanceConfig = {
  // Batch processing
  batchSize: 1000,
  flushInterval: 5000, // 5 seconds
  maxBatchAge: 30000, // 30 seconds

  // Connection pooling
  database: {
    maxConnections: 50,
    idleTimeout: 30000,
    connectionTimeout: 5000,
  },

  // Caching
  cache: {
    enabled: true,
    ttl: 300, // 5 minutes
    maxSize: 10000,
  },

  // Streaming
  streaming: {
    bufferSize: 1000,
    flushOnExit: true,
    compressionLevel: 6,
  },
};

// Performance monitoring
const performanceMonitor = {
  // Track latency
  trackLatency: (operation, duration) => {
    metrics.histogram(`audit.${operation}.duration`, duration);

    if (duration > 1000) {
      // Over 1 second
      console.warn(`Slow audit operation: ${operation} took ${duration}ms`);
    }
  },

  // Track throughput
  trackThroughput: eventCount => {
    metrics.increment('audit.events.processed', eventCount);
    metrics.gauge('audit.events.rate', eventCount / 60); // Per minute
  },

  // Track errors
  trackError: (operation, error) => {
    metrics.increment(`audit.${operation}.errors`);
    console.error(`Audit error in ${operation}:`, error);
  },
};
```

### Scaling Strategies

```typescript
// Horizontal scaling with sharding
const setupSharding = config => {
  const shards = [];

  for (let i = 0; i < config.shardCount; i++) {
    shards.push(
      new AuditStorageService({
        ...config,
        database: {
          ...config.database,
          name: `${config.database.name}_shard_${i}`,
        },
      })
    );
  }

  // Route events to shards based on actor ID
  const getShardForEvent = event => {
    const hash = hashString(event.actor.id);
    return shards[hash % shards.length];
  };

  return { shards, getShardForEvent };
};

// Load balancing
const loadBalancer = {
  services: [...auditServices],
  currentIndex: 0,

  getNextService() {
    const service = this.services[this.currentIndex];
    this.currentIndex = (this.currentIndex + 1) % this.services.length;
    return service;
  },
};
```

## 🧪 Testing

### Running Tests

```bash
# Install dependencies
npm install

# Run unit tests
npm run test:unit

# Run integration tests
npm run test:integration

# Run all tests with coverage
npm run test:coverage

# Run performance tests
npm run test:performance

# Run specific test files
npm test -- --testPathPattern=CryptographicAuditService
```

### Test Configuration

```javascript
// jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  setupFilesAfterEnv: ['<rootDir>/tests/setup.ts'],
  collectCoverageFrom: ['src/**/*.ts', '!src/**/*.d.ts', '!src/**/*.test.ts'],
  coverageThreshold: {
    global: {
      branches: 85,
      functions: 85,
      lines: 85,
      statements: 85,
    },
  },
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  testTimeout: 30000,
};
```

### Writing Tests

```typescript
// Example test file
describe('AuditStorageService', () => {
  let storageService: AuditStorageService;

  beforeEach(async () => {
    storageService = new AuditStorageService(testConfig);
    await storageService.initialize();
  });

  afterEach(async () => {
    await storageService.close();
  });

  it('should store and retrieve audit events', async () => {
    const testEvent = createTestAuditEvent({
      actor: { id: 'test-user', type: 'user' },
      action: { type: 'create', resource: 'document', result: 'success' },
    });

    await storageService.storeEvent(testEvent);

    const retrieved = await storageService.queryEvents({
      actorId: 'test-user',
      limit: 1,
    });

    expect(retrieved).toHaveLength(1);
    expect(retrieved[0]).toBeValidAuditEvent();
    expect(retrieved[0].id).toBe(testEvent.id);
  });

  it('should handle high-volume event storage', async () => {
    const events = createTestAuditEvents(1000);
    const batch = await cryptoService.createSignedBatch(events);

    const startTime = Date.now();
    await storageService.storeBatch(batch);
    const duration = Date.now() - startTime;

    expect(duration).toBeLessThan(5000); // Should complete in under 5 seconds
  });
});
```

## 🚀 Deployment

### Docker Deployment

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY dist/ ./dist/
COPY config/ ./config/

EXPOSE 3002

CMD [\"node\", \"dist/index.js\"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  audit-service:
    build: .
    ports:
      - \"3002:3002\"
    environment:
      - NODE_ENV=production
      - DB_HOST=postgres
      - REDIS_HOST=redis
      - KAFKA_BROKERS=kafka:9092
    depends_on:
      - postgres
      - redis
      - kafka
    volumes:
      - ./logs:/app/logs

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: pake_audit
      POSTGRES_USER: audit_user
      POSTGRES_PASSWORD: secure_REDACTED_SECRET
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass redis_REDACTED_SECRET

  kafka:
    image: confluentinc/cp-kafka:latest
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

volumes:
  postgres_data:
```

### Kubernetes Deployment

```yaml
# k8s/audit-service.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: audit-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: audit-service
  template:
    metadata:
      labels:
        app: audit-service
    spec:
      containers:
        - name: audit-service
          image: pake/audit-service:latest
          ports:
            - containerPort: 3002
          env:
            - name: NODE_ENV
              value: production
            - name: DB_HOST
              valueFrom:
                configMapKeyRef:
                  name: audit-config
                  key: db.host
          resources:
            requests:
              memory: \"256Mi\"
              cpu: \"250m\"
            limits:
              memory: \"1Gi\"
              cpu: \"500m\"
          livenessProbe:
            httpGet:
              path: /health
              port: 3002
            initialDelaySeconds: 30
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: audit-service
spec:
  selector:
    app: audit-service
  ports:
    - port: 3002
      targetPort: 3002
  type: ClusterIP
```

### Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL/TLS certificates installed
- [ ] Monitoring and alerting configured
- [ ] Log aggregation setup
- [ ] Backup procedures tested
- [ ] Security scanning completed
- [ ] Performance testing passed
- [ ] Documentation updated
- [ ] Team training completed

## 🔧 Troubleshooting

### Common Issues

#### High Memory Usage

```bash
# Check memory usage
npm run check-memory

# Enable memory profiling
NODE_OPTIONS=\"--max-old-space-size=4096 --inspect\" npm start

# Optimize configuration
{
  \"performance\": {
    \"batchSize\": 500,        # Reduce batch size
    \"flushInterval\": 10000,  # Increase flush interval
    \"maxCacheSize\": 5000     # Reduce cache size
  }
}
```

#### Database Connection Issues

```bash
# Test database connectivity
npm run test-db

# Check connection pool
SELECT * FROM pg_stat_activity WHERE application_name = 'audit-service';

# Reset connections
npm run db-reset-connections
```

#### High Latency

```bash
# Enable performance monitoring
DEBUG=audit:performance npm start

# Check slow queries
npm run analyze-slow-queries

# Optimize database
npm run db-analyze-performance
```

### Debug Mode

```bash
# Enable debug logging
DEBUG=audit:* LOG_LEVEL=debug npm start

# Enable SQL query logging
DB_DEBUG=true npm start

# Monitor real-time metrics
npm run monitor
```

### Health Checks

```bash
# Basic health check
curl http://localhost:3002/health

# Detailed health check
curl http://localhost:3002/health/detailed

# Database health
curl http://localhost:3002/health/database

# Dependencies health
curl http://localhost:3002/health/dependencies
```

## 📚 Additional Resources

- [API Documentation](./docs/api.md)
- [Architecture Overview](./docs/architecture.md)
- [Security Guidelines](./docs/security.md)
- [Performance Tuning](./docs/performance.md)
- [Compliance Guides](./docs/compliance/)
- [Integration Examples](./examples/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Ensure all tests pass
5. Update documentation
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Email**: support@pake-system.com
- **Documentation**: https://docs.pake-system.com/audit
- **Issues**: https://github.com/pake-system/audit/issues
- **Slack**: #audit-support

---

**PAKE Audit Service** - Securing your digital operations with enterprise-grade audit logging.
