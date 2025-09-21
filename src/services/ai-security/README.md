# PAKE AI Security Controls

A comprehensive security framework specifically designed for AI systems, protecting against prompt injection, model extraction, adversarial attacks, and ensuring cost control.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Run tests
npm test

# Run specific security tests
npm run test:prompt-injection
npm run test:model-protection
npm run test:adversarial
npm run test:cost-controls

# Start the service
npm run dev
```

## 🎯 Success Criteria

✅ **Zero successful prompt injections** - 100% detection rate against known attacks  
✅ **Model extraction attempts detected and blocked** - Advanced query analysis  
✅ **Token costs within 10% of projections** - Precise cost tracking and budgeting  
✅ **<5% false positive rate** - High accuracy adversarial detection

## 🏗️ Architecture

### Core Security Components

- **PromptInjectionPrevention** - Advanced input sanitization and threat detection
- **ModelProtection** - Extraction prevention, watermarking, and query analysis
- **CostControls** - Token budgets, throttling, and cost optimization
- **AdversarialDefense** - Perturbation detection and consistency checking
- **OutputFiltering** - Response validation and content safety

### Security Layers

```
┌─────────────────────────────────────────────────────────┐
│                    AI Request Flow                      │
├─────────────────────────────────────────────────────────┤
│  1. Input Analysis     │  Prompt Injection Detection   │
│  2. Query Analysis     │  Model Protection             │
│  3. Budget Check       │  Cost Controls                │
│  4. Processing         │  Model Inference              │
│  5. Output Validation  │  Content & Safety Filtering   │
│  6. Response Delivery  │  Watermarking & Monitoring    │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Configuration

### Basic Setup

```typescript
import {
  PromptInjectionPrevention,
  ModelProtection,
  CostControls,
  AdversarialDefense,
  OutputFiltering,
} from '@pake/ai-security';

// Configure security components
const securityConfig = {
  promptInjection: {
    enabled: true,
    strictMode: true,
    maxPromptLength: 10000,
    semanticAnalysis: true,
    contextAnalysis: true,
  },
  modelProtection: {
    enabled: true,
    watermarking: {
      enabled: true,
      algorithm: 'statistical',
      strength: 0.7,
    },
    extractionPrevention: {
      enabled: true,
      maxSimilarQueries: 5,
      blockSuspiciousQueries: true,
    },
  },
  costControls: {
    enabled: true,
    defaultTokenBudget: 100000,
    budgetPeriod: 'monthly',
    throttleThreshold: 0.8,
  },
  adversarialDefense: {
    enabled: true,
    perturbationDetection: {
      threshold: 0.1,
      sensitivity: 'medium',
    },
    falsePositiveTarget: 0.05,
  },
};
```

### Advanced Configuration

```typescript
const advancedConfig = {
  promptInjection: {
    enabled: true,
    strictMode: true,
    maxPromptLength: 10000,
    suspiciousPatterns: [
      'ignore previous instructions',
      'system override',
      'jailbreak mode',
    ],
    whitelistedTerms: ['system analysis', 'computer science instruction'],
    semanticAnalysis: true,
    contextAnalysis: true,
  },
  modelProtection: {
    enabled: true,
    watermarking: {
      enabled: true,
      algorithm: 'statistical',
      strength: 0.7,
      detectability: 0.6,
      keyRotationInterval: 24,
    },
    rateLimiting: {
      enabled: true,
      requestsPerMinute: 60,
      tokensPerHour: 10000,
      burstLimit: 10,
    },
    queryAnalysis: {
      enabled: true,
      patternDetection: true,
      behaviorAnalysis: true,
      extractionThreshold: 0.7,
    },
  },
};
```

## 💻 Usage

### Prompt Injection Prevention

```typescript
const injectionPrevention = new PromptInjectionPrevention(
  config.promptInjection
);

// Analyze input for threats
const analysis = await injectionPrevention.analyze(userInput);
if (!analysis.isClean) {
  console.log('Threats detected:', analysis.threats);
  throw new PromptInjectionError('Malicious input detected');
}

// Sanitize input
const sanitized = await injectionPrevention.sanitize(userInput, context);
const cleanInput = sanitized.sanitized;
```

### Model Protection

```typescript
const modelProtection = new ModelProtection(config.modelProtection);

// Analyze query for extraction attempts
const queryAnalysis = await modelProtection.analyzeQuery(
  userQuery,
  userId,
  context
);

if (queryAnalysis.isExtraction) {
  throw new ModelExtractionError('Extraction attempt detected');
}

// Apply watermark to output
const watermarked = await modelProtection.applyWatermark(modelOutput, context);
const protectedOutput = watermarked.watermarkedText;
```

### Cost Controls

```typescript
const costControls = new CostControls(config.costControls);

// Check budget before processing
const budgetCheck = await costControls.checkBudget(
  userId,
  estimatedTokens,
  modelType
);
if (!budgetCheck.allowed) {
  throw new BudgetExceededError('Insufficient budget');
}

// Record actual usage
const metrics = await costControls.recordUsage(
  userId,
  inputTokens,
  outputTokens,
  modelType,
  context
);
```

### Adversarial Defense

```typescript
const adversarialDefense = new AdversarialDefense(config.adversarialDefense);

// Detect adversarial input
const detection = await adversarialDefense.detectAdversarialInput(
  input,
  userId,
  context
);

if (detection.isAdversarial) {
  console.log('Adversarial attack detected:', detection.detectionType);
  throw new AdversarialAttackError('Adversarial input blocked');
}

// Validate output consistency
const consistencyCheck = await adversarialDefense.performConsistencyCheck(
  input,
  responses,
  userId
);
```

### Output Filtering

```typescript
const outputFilter = new OutputFiltering(config.outputValidation);

// Filter and validate output
const filtered = await outputFilter.filterOutput(modelOutput, context);

if (!filtered.isClean) {
  console.log('Content violations:', filtered.violations);
  return filtered.filteredOutput; // Return sanitized version
}
```

## 🛡️ Security Features

### Prompt Injection Protection

#### Detection Capabilities

- **Direct instruction overrides** - "Ignore previous instructions"
- **System prompt manipulation** - "Show me your system prompt"
- **Role confusion attacks** - "Pretend you are a hacker"
- **Jailbreak attempts** - "Enable developer mode"
- **Extraction attempts** - "Repeat your training instructions"
- **Encoded injections** - Base64, hex, Unicode attacks
- **Context pollution** - "The user previously told me..."

#### Advanced Features

- Semantic analysis using NLP
- Context-aware threat detection
- Linguistic pattern analysis
- Multi-language support
- Real-time threat intelligence

### Model Protection

#### Query Analysis

- **Pattern detection** - Systematic probing attempts
- **Similarity analysis** - Repeated similar queries
- **Behavioral analysis** - User query patterns over time
- **Progressive complexity** - Escalating sophistication
- **Topic drift analysis** - Focused vs. scattered queries

#### Watermarking

- **Statistical watermarking** - Token probability modification
- **Lexical watermarking** - Strategic word choice
- **Semantic watermarking** - Meaning-preserving markers
- **Automatic key rotation** - Periodic watermark updates
- **Detection algorithms** - Identify watermarked content

### Cost Management

#### Budget Controls

- **Per-user token budgets** - Daily/weekly/monthly limits
- **Multi-model cost tracking** - Different pricing tiers
- **Real-time usage monitoring** - Live budget tracking
- **Threshold alerts** - 50%, 75%, 90% notifications
- **Overage policies** - Block, throttle, or alert

#### Performance Optimization

- **Intelligent throttling** - Gradual slowdown approach
- **Burst allowances** - Short-term usage spikes
- **Priority queuing** - VIP user handling
- **Cost projection** - Accurate usage forecasting

### Adversarial Defense

#### Perturbation Detection

- **Character-level** - Unicode substitutions, invisible chars
- **Word-level** - Typo injection, synonym replacement
- **Sentence-level** - Reordering, paraphrasing
- **Semantic-level** - Context drift, contradiction
- **Statistical analysis** - Pattern anomaly detection

#### Consistency Checking

- **Input variations** - Multiple similar inputs
- **Response consistency** - Coherent output validation
- **Temporal consistency** - Consistent behavior over time
- **Cross-model validation** - Multiple model agreement

## 📊 Monitoring & Analytics

### Real-time Metrics

```typescript
// Get security metrics
const metrics = {
  promptInjection: injectionPrevention.getMetrics(),
  modelProtection: modelProtection.getMetrics(),
  costControls: costControls.getMetrics(),
  adversarialDefense: adversarialDefense.getMetrics(),
};

console.log('Security Status:', {
  threatsBlocked: metrics.promptInjection.threatsDetected,
  extractionAttempts: metrics.modelProtection.extractionAttempts,
  budgetUtilization: metrics.costControls.averageUtilization,
  falsePositiveRate: metrics.adversarialDefense.falsePositiveRate,
});
```

### Dashboard Integration

```typescript
// Security event handling
securityComponents.forEach(component => {
  component.on('threat', event => {
    dashboard.recordThreat(event);
    alerting.sendAlert(event);
  });

  component.on('budget', event => {
    dashboard.updateBudget(event);
  });

  component.on('performance', event => {
    dashboard.recordPerformance(event);
  });
});
```

### Alerting System

```typescript
const alertConfig = {
  threats: {
    critical: ['prompt_injection', 'model_extraction', 'adversarial_attack'],
    channels: ['slack', 'email', 'webhook'],
  },
  budgets: {
    thresholds: [0.8, 0.9, 0.95],
    escalation: ['team', 'manager', 'executive'],
  },
  performance: {
    latency: 100, // ms
    errorRate: 0.01, // 1%
  },
};
```

## 🧪 Testing

### Comprehensive Test Suite

```bash
# Run all security tests
npm test

# Specific test categories
npm run test:prompt-injection    # Injection detection tests
npm run test:model-protection   # Extraction prevention tests
npm run test:adversarial        # Adversarial defense tests
npm run test:cost-controls      # Budget and cost tests

# Performance benchmarks
npm run benchmark

# Security compliance validation
npm run security-scan
```

### Test Categories

#### Prompt Injection Tests

- **Known attack patterns** - 100+ injection techniques
- **Encoding variations** - Base64, hex, Unicode attacks
- **Language variations** - Multi-language injection attempts
- **False positive validation** - Legitimate input testing

#### Model Protection Tests

- **Extraction scenarios** - Systematic probing simulations
- **Watermark validation** - Detection accuracy testing
- **Query pattern analysis** - Behavioral pattern recognition
- **Performance under load** - Concurrent request handling

#### Cost Control Tests

- **Budget enforcement** - Overage prevention validation
- **Multi-model costs** - Accurate pricing calculations
- **Throttling behavior** - Gradual slowdown verification
- **Usage analytics** - Reporting accuracy

#### Adversarial Defense Tests

- **Perturbation detection** - Character/word/semantic attacks
- **Consistency validation** - Response coherence checking
- **Performance metrics** - Speed and accuracy measurement
- **False positive rates** - Legitimate input handling

## 🔒 Security Best Practices

### Deployment Security

```typescript
// Production configuration
const productionConfig = {
  // Enable all security features
  promptInjection: { enabled: true, strictMode: true },
  modelProtection: { enabled: true },
  costControls: { enabled: true },
  adversarialDefense: { enabled: true },

  // Secure logging
  logging: {
    level: 'info',
    enableAudit: true,
    enableMetrics: true,
    logSensitiveData: false,
  },

  // Redis security
  redis: {
    host: process.env.REDIS_HOST,
    REDACTED_SECRET: process.env.REDIS_PASSWORD,
    tls: { servername: process.env.REDIS_HOST },
  },
};
```

### Monitoring Guidelines

1. **Real-time Alerting** - Immediate notification of threats
2. **Audit Trails** - Complete security event logging
3. **Performance Tracking** - Latency and accuracy metrics
4. **Budget Monitoring** - Cost control and optimization
5. **False Positive Analysis** - Continuous accuracy improvement

### Incident Response

```typescript
// Security incident handling
const incidentResponse = {
  prompt_injection: {
    severity: 'critical',
    actions: ['block_user', 'alert_team', 'log_incident'],
    escalation: 'immediate',
  },
  model_extraction: {
    severity: 'high',
    actions: ['throttle_user', 'analyze_pattern', 'alert_team'],
    escalation: 'within_hour',
  },
  budget_exceeded: {
    severity: 'medium',
    actions: ['throttle_user', 'notify_user', 'log_usage'],
    escalation: 'daily_report',
  },
};
```

## 📈 Performance Specifications

### Latency Requirements

- **Input analysis**: <100ms per request
- **Query analysis**: <50ms per query
- **Budget checking**: <10ms per check
- **Output filtering**: <200ms per response

### Accuracy Targets

- **Prompt injection detection**: >95% true positive rate
- **False positive rate**: <5% across all components
- **Model extraction detection**: >90% accuracy
- **Cost estimation**: ±10% of actual costs

### Scalability Limits

- **Concurrent requests**: 1000+ per second
- **User sessions**: 10,000+ concurrent users
- **Budget tracking**: 1M+ users
- **Query analysis**: 100+ queries per user per hour

## 🔧 API Reference

### Core Classes

#### PromptInjectionPrevention

```typescript
class PromptInjectionPrevention {
  analyze(input: string): Promise<PromptAnalysisResult>;
  sanitize(
    input: string,
    context?: SanitizationContext
  ): Promise<SanitizationResult>;
  updateConfig(config: Partial<PromptInjectionConfig>): void;
  getMetrics(): PromptInjectionMetrics;
}
```

#### ModelProtection

```typescript
class ModelProtection {
  analyzeQuery(
    query: string,
    userId: string,
    context: SecurityContext
  ): Promise<QueryAnalysis>;
  applyWatermark(
    text: string,
    context: SecurityContext
  ): Promise<WatermarkResult>;
  detectWatermark(text: string): Promise<WatermarkDetection>;
  getUserQueryPatterns(userId: string): QueryPattern[];
}
```

#### CostControls

```typescript
class CostControls {
  checkBudget(
    userId: string,
    tokens: number,
    model: string
  ): Promise<BudgetCheck>;
  recordUsage(
    userId: string,
    input: number,
    output: number,
    model: string,
    context: SecurityContext
  ): Promise<CostMetrics>;
  setBudget(userId: string, budget: number): void;
  getUserUsageMetrics(userId: string, days: number): Promise<UsageMetrics>;
}
```

#### AdversarialDefense

```typescript
class AdversarialDefense {
  detectAdversarialInput(
    input: string,
    userId: string,
    context: SecurityContext
  ): Promise<AdversarialDetection>;
  performConsistencyCheck(
    input: string,
    responses: string[],
    userId: string
  ): Promise<ConsistencyCheck>;
  validateOutput(
    output: string,
    context: SecurityContext
  ): Promise<ValidationResult>;
}
```

## 🚀 Deployment

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app

# Copy and install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY dist/ ./dist/

# Security configurations
ENV NODE_ENV=production
ENV LOG_LEVEL=info
ENV ENABLE_SECURITY=true

EXPOSE 3000
CMD ["npm", "start"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-security
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-security
  template:
    metadata:
      labels:
        app: ai-security
    spec:
      containers:
        - name: ai-security
          image: pake/ai-security:latest
          ports:
            - containerPort: 3000
          env:
            - name: REDIS_HOST
              value: 'redis-cluster'
            - name: NODE_ENV
              value: 'production'
          resources:
            requests:
              memory: '512Mi'
              cpu: '250m'
            limits:
              memory: '1Gi'
              cpu: '500m'
```

### Environment Variables

```bash
# Core Configuration
NODE_ENV=production
LOG_LEVEL=info
PORT=3000

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-REDACTED_SECRET

# Security Settings
ENABLE_PROMPT_INJECTION_PROTECTION=true
ENABLE_MODEL_PROTECTION=true
ENABLE_COST_CONTROLS=true
ENABLE_ADVERSARIAL_DEFENSE=true

# Performance Tuning
MAX_CONCURRENT_REQUESTS=1000
CACHE_TTL=1800
RATE_LIMIT_WINDOW=60000
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-security`)
3. Add comprehensive tests for new security features
4. Ensure all security tests pass
5. Update documentation
6. Submit a pull request

### Security Contribution Guidelines

- **Never commit test credentials** - Use environment variables
- **Include attack scenarios** - Demonstrate security improvements
- **Document false positive rates** - Include accuracy metrics
- **Performance benchmarks** - Validate speed requirements
- **Threat model updates** - Document new attack vectors

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 **Security Issues**: security@pake-system.com
- 📖 **Documentation**: https://docs.pake-system.com/ai-security
- 🐛 **Bug Reports**: https://github.com/pake-system/ai-security/issues
- 💬 **Discussion**: https://discord.gg/pake-ai-security

## 📚 Additional Resources

- [OWASP AI Security Guidelines](https://owasp.org/www-project-ai-security-and-privacy-guide/)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
- [AI Security Research Papers](https://docs.pake-system.com/ai-security/research)
- [Prompt Injection Attack Database](https://docs.pake-system.com/ai-security/attacks)

---

**⚠️ Security Notice**: This system implements critical AI security controls. Always conduct thorough security reviews and penetration testing before production deployment. Report security vulnerabilities through responsible disclosure channels.
