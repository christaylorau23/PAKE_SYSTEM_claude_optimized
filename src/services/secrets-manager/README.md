# PAKE Secrets Management & Encryption Service

A comprehensive zero-trust secrets management system with HashiCorp Vault integration, automatic rotation, and enterprise-grade security features.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Start development Vault server
npm run vault:dev

# Initialize Vault engines
npm run vault:init

# Run tests
npm test

# Start the service
npm run dev
```

## 📋 Success Criteria

✅ **Zero secrets in code/environment variables** - All secrets fetched at runtime via SDK  
✅ **Automated rotation for all credentials** - Configurable rotation schedules  
✅ **<10ms decryption overhead** - High-performance encryption/decryption  
✅ **100% encryption coverage** - All sensitive data encrypted at rest  
✅ **Disaster recovery tested** - Break-glass procedures and backup/restore

## 🏗️ Architecture

### Core Components

- **VaultService** - HashiCorp Vault integration
- **SecretsManagerSDK** - Application integration layer
- **EncryptionService** - AES-256-GCM encryption at rest
- **RotationService** - Automated key/secret rotation
- **HSMService** - Hardware Security Module support
- **MTLSService** - Mutual TLS for encryption in transit
- **BreakGlassService** - Emergency access procedures

### Security Features

- **Zero-Trust Architecture** - No secrets in environment variables
- **Field-Level Encryption** - Granular PII data protection
- **Hardware Security Module** - HSM-backed key operations
- **Mutual TLS** - Certificate-based authentication
- **Audit Logging** - Comprehensive security event tracking
- **Break-Glass Access** - Emergency procedures with approval workflows

## 🔧 Configuration

### Environment Setup

```typescript
import { SecretsManagerSDK } from '@pake/secrets-manager';

const sdk = new SecretsManagerSDK({
  vault: {
    endpoint: 'https://vault.example.com:8200',
    engines: {
      kv: { name: 'secret', version: 2, path: 'secret/' },
      transit: { name: 'transit', path: 'transit/' },
      pki: { name: 'pki', path: 'pki/' },
    },
    auth: { method: 'token', token: 'your-token' },
  },
  cache: {
    ttl: 300, // 5 minutes
    maxSize: 1000,
    encryptCached: true,
  },
});

await sdk.initialize();
```

### Vault Configuration

```bash
# Enable required engines
vault auth enable -path=auth/kubernetes kubernetes
vault secrets enable -path=secret -version=2 kv
vault secrets enable transit
vault secrets enable pki
vault secrets enable database
```

## 💻 Usage

### Basic Secret Operations

```typescript
// Store a secret
await sdk.storeSecret('myapp/database', {
  host: 'localhost',
  username: 'admin',
  REDACTED_SECRET: 'secure_database_REDACTED_SECRET',
});

// Retrieve a secret
const secret = await sdk.getSecret('myapp/database');
console.log(secret.value); // { host: 'localhost', username: 'admin', REDACTED_SECRET: 'secure_database_REDACTED_SECRET' }

// Delete a secret
await sdk.deleteSecret('myapp/database');
```

### Typed Secret Accessors

```typescript
// Database credentials
const dbCreds = await sdk.getDatabaseCredentials('myapp/postgres');
// Returns: { host, port, username, REDACTED_SECRET, database }

// API key
const apiKey = await sdk.getAPIKey('myapp/external-service');
// Returns: string

// Certificate with private key
const cert = await sdk.getCertificate('myapp/tls-cert');
// Returns: { certificate, privateKey, caChain }
```

### Secret Injection

```typescript
const secrets = new Map([
  ['DATABASE_URL', { path: 'myapp/db', field: 'url' }],
  ['API_KEY', { path: 'myapp/api' }],
  ['JWT_SECRET', { path: 'myapp/jwt', field: 'secret' }],
]);

const context = await sdk.injectSecrets(secrets);
// Returns: { DATABASE_URL: '...', API_KEY: '...', JWT_SECRET: '...' }
```

## 🔐 Encryption

### Data Encryption

```typescript
import { EncryptionService } from '@pake/secrets-manager';

const encryption = new EncryptionService(config);
await encryption.initialize();

// Encrypt data
const encrypted = await encryption.encryptData('sensitive information');
// Returns: { ciphertext, keyId, algorithm, iv, authTag }

// Decrypt data
const decrypted = await encryption.decryptData(encrypted);
// Returns: 'sensitive information'
```

### Field-Level Encryption

```typescript
const userData = {
  name: 'John Doe',
  email: 'john@example.com',
  ssn: '123-45-6789',
};

const fieldsToEncrypt = [
  { fieldName: 'email', algorithm: 'aes-256-gcm', keyId: 'pii-key' },
  { fieldName: 'ssn', algorithm: 'aes-256-gcm', keyId: 'pii-key' },
];

const encrypted = await encryption.encryptFields(userData, fieldsToEncrypt);
// Returns: { name: 'John Doe', email: {...encrypted}, ssn: {...encrypted} }
```

## 🔄 Key Rotation

### Automatic Rotation

```typescript
import { RotationService } from '@pake/secrets-manager';

const rotation = new RotationService(vaultService, encryptionService);

// Set rotation policy
await rotation.setRotationPolicy({
  secretPath: 'myapp/database',
  schedule: { type: 'fixed', intervalDays: 30 },
  strategy: 'gradual', // immediate, gradual, blue-green, canary
  notifications: {
    beforeRotation: ['admin@example.com'],
    afterRotation: ['admin@example.com'],
  },
});

// Manual rotation
const result = await rotation.rotateNow('myapp/database', 'database-REDACTED_SECRET');
```

### Rotation Strategies

- **Immediate** - Replace secret immediately
- **Gradual** - Phase in new secret over time
- **Blue-Green** - Switch between two versions
- **Canary** - Test new secret with subset of traffic

## 🏥 Hardware Security Module

### HSM Configuration

```typescript
const hsmConfig = {
  enabled: true,
  provider: 'AWS-CloudHSM', // or 'SoftHSM', 'Thales', 'Utimaco'
  config: {
    library: '/opt/cloudhsm/lib/libcloudhsm_pkcs11.so',
    slot: 0,
    pin: process.env.HSM_PIN,
  },
};

const hsm = new HSMService(hsmConfig);
await hsm.initialize();

// Generate HSM-backed key
const keyInfo = await hsm.generateKey('myapp-key', 'aes', 256);
```

## 🚨 Break-Glass Procedures

### Emergency Access

```typescript
import { BreakGlassService } from '@pake/secrets-manager';

const breakGlass = new BreakGlassService(vaultService, encryptionService);

// Initiate emergency procedure
const sessionId = await breakGlass.initiateBreakGlass({
  procedureName: 'critical-system-access',
  initiator: {
    userId: 'admin-user',
    role: 'system-admin',
    location: 'data-center',
  },
  justification: 'Critical system failure requiring immediate access',
  requiredSecrets: ['/critical/database-REDACTED_SECRET'],
  actions: ['secret.reveal'],
  expiration: new Date(Date.now() + 3600000), // 1 hour
});

// Execute emergency action (after approvals)
const result = await breakGlass.executeEmergencyAction(
  sessionId,
  'secret.reveal',
  { secretPath: '/critical/database-REDACTED_SECRET' }
);
```

## 🔒 Mutual TLS

### mTLS Configuration

```typescript
import { MTLSService } from '@pake/secrets-manager';

const mtls = new MTLSService({
  certificates: {
    ca: '/path/to/ca.crt',
    cert: '/path/to/server.crt',
    key: '/path/to/server.key',
  },
  validation: {
    verifyChain: true,
    allowSelfSigned: false,
  },
});

// Create secure server
const context = await mtls.createContext('api-server');
const server = mtls.createMTLSServer('api-server', {
  port: 8443,
  requestCert: true,
});
```

## 📊 Monitoring & Observability

### Metrics

The service exposes Prometheus metrics:

- `secrets_operations_total` - Total secret operations
- `secrets_operation_duration_seconds` - Operation latency
- `secrets_cache_hit_ratio` - Cache performance
- `secrets_rotation_total` - Rotation events
- `secrets_error_total` - Error counts

### Health Checks

```typescript
// Service health
const health = await sdk.getHealth();
// Returns: { status: 'healthy', vault: {...}, encryption: {...} }

// Vault health
const vaultHealth = await vaultService.getHealth();
// Returns: { initialized: true, sealed: false, version: '1.15.2' }
```

## 🧪 Testing

### Test Suites

```bash
# Unit tests
npm run test:unit

# Integration tests
npm run test:integration

# Performance tests
npm run test:performance

# Security compliance tests
npm run test:security

# Full test suite with coverage
npm run test:coverage
```

### Test Categories

- **Unit Tests** - Individual service testing
- **Integration Tests** - End-to-end workflow testing
- **Performance Tests** - Latency and throughput validation
- **Security Tests** - Compliance and vulnerability testing

## 📚 API Reference

### SecretsManagerSDK

| Method                    | Description         | Parameters                   | Returns                        |
| ------------------------- | ------------------- | ---------------------------- | ------------------------------ |
| `initialize()`            | Initialize SDK      | -                            | `Promise<void>`                |
| `getSecret(path)`         | Retrieve secret     | `string \| SecretRequest`    | `Promise<Secret \| null>`      |
| `storeSecret(path, data)` | Store secret        | `string, any`                | `Promise<boolean>`             |
| `deleteSecret(path)`      | Delete secret       | `string`                     | `Promise<boolean>`             |
| `injectSecrets(map)`      | Inject into context | `Map<string, SecretMapping>` | `Promise<Record<string, any>>` |

### EncryptionService

| Method                          | Description           | Parameters                  | Returns                     |
| ------------------------------- | --------------------- | --------------------------- | --------------------------- |
| `encryptData(data, keyId?)`     | Encrypt data          | `string \| Buffer, string?` | `Promise<EncryptionResult>` |
| `decryptData(result)`           | Decrypt data          | `EncryptionResult`          | `Promise<string>`           |
| `encryptFields(obj, fields)`    | Encrypt object fields | `object, FieldConfig[]`     | `Promise<object>`           |
| `generateKey(label, algorithm)` | Generate new key      | `string, string`            | `Promise<KeyInfo>`          |

## 🔧 Configuration Reference

### SDK Configuration

```typescript
interface SDKConfig {
  vault: VaultConfig;
  cache?: CacheConfig;
  retry?: RetryConfig;
  validation?: ValidationConfig;
}
```

### Encryption Configuration

```typescript
interface EncryptionConfig {
  algorithms: {
    symmetric: string; // 'aes-256-gcm'
    asymmetric: string; // 'rsa-4096'
    hash: string; // 'sha256'
    kdf: string; // 'argon2id'
  };
  keys: {
    masterKeyId: string;
    keyDerivationParams: {
      memory: number; // 64 * 1024
      iterations: number; // 3
      parallelism: number; // 4
    };
  };
  fieldLevel: FieldLevelConfig;
  hsm: HSMConfig;
}
```

## 🚀 Deployment

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY dist/ ./dist/
EXPOSE 3000
CMD ["npm", "start"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secrets-manager
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: secrets-manager
          image: pake/secrets-manager:latest
          env:
            - name: VAULT_ADDR
              value: 'https://vault.internal:8200'
            - name: NODE_ENV
              value: 'production'
```

## 🔐 Security Best Practices

### Development

- Never commit secrets to version control
- Use development Vault server for testing
- Rotate development tokens regularly
- Enable audit logging in all environments

### Production

- Use HSM-backed keys for critical operations
- Implement network segmentation
- Enable comprehensive monitoring
- Regular security audits and penetration testing
- Maintain offline backup of Vault data

### Compliance

- **PCI DSS** - Card data field-level encryption
- **GDPR** - Personal data encryption and right to be forgotten
- **HIPAA** - Healthcare data protection
- **SOC 2** - Security controls and audit trails

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: security@pake-system.com
- 📖 Documentation: https://docs.pake-system.com/secrets
- 🐛 Issues: https://github.com/pake-system/secrets-manager/issues
- 💬 Discord: https://discord.gg/pake-system

---

**⚠️ Security Notice**: This service handles sensitive cryptographic operations. Always follow security best practices and conduct thorough security reviews before production deployment.
