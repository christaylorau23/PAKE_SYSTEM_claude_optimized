# Agent Runtime System

A scalable, provider-based agent execution system with feature flags and JSON schema validation.

## Overview

The Agent Runtime provides a standardized interface for executing AI agent tasks across different providers while maintaining type safety, observability, and configuration flexibility.

## Key Features

- **Provider Interface**: Pluggable agent providers (NullProvider, LLMProvider, etc.)
- **Feature Flags**: Environment-driven configuration with runtime overrides
- **JSON Schemas**: Contract validation for agent I/O and trend records
- **Type Safety**: Full TypeScript support with strict typing
- **Observability**: Built-in metrics, logging, and health checks
- **Testing**: Comprehensive unit and contract test coverage

## Architecture

```
Agent Runtime
├── Providers (AgentProvider interface)
│   ├── NullProvider (deterministic stubbed results)
│   └── [Future: LLMProvider, LocalProvider, etc.]
├── Feature Flags (environment-driven configuration)
├── JSON Schemas (contract validation)
└── Runtime Management (orchestration, metrics, health)
```

## Quick Start

```typescript
import { defaultAgentRuntime, agent, AgentTaskType } from '@pake/agent-runtime';

// Analyze sentiment using default runtime
const result = await agent.analyzeSentiment('This product is amazing!', { provider: 'null' });

console.log(result.output.sentiment); // { score: 0.8, label: 'positive', ... }

// Create custom runtime
const customRuntime = new AgentRuntime({
  defaultProvider: 'null',
  maxConcurrentTasks: 5,
});

await customRuntime.executeTask({
  id: 'custom_task',
  type: AgentTaskType.ENTITY_EXTRACTION,
  input: { content: 'John Smith works at Microsoft.' },
  config: { timeout: 30000 },
  metadata: { source: 'api', createdAt: new Date().toISOString() },
});
```

## Feature Flags

Configure behavior via environment variables:

```bash
# Core system flags
FEATURE_AGENT_RUNTIME_ENABLED=true
FEATURE_NULL_PROVIDER_ENABLED=true
FEATURE_CONCURRENT_TASK_LIMIT=10
FEATURE_TASK_TIMEOUT_MS=30000

# Performance flags
FEATURE_ENABLE_RESULT_CACHING=false
FEATURE_CACHE_TTL_SECONDS=3600

# Observability flags
FEATURE_ENABLE_METRICS_COLLECTION=true
FEATURE_ENABLE_DETAILED_LOGGING=false

# Rollout flags
FEATURE_ROLLOUT_PERCENTAGE=100
```

Access flags programmatically:

```typescript
import { flags, agentRuntimeFlags } from '@pake/agent-runtime';

// Convenience functions
const isEnabled = flags.isAgentRuntimeEnabled();
const taskLimit = flags.getConcurrentTaskLimit();

// Direct flag access
const customFlag = agentRuntimeFlags.getValue('CUSTOM_FLAG', { userId: 'user123' });

// Runtime overrides
agentRuntimeFlags.setOverride('TASK_TIMEOUT_MS', 60000);
```

## Providers

### NullProvider

Deterministic stubbed provider for testing and development:

```typescript
import { NullProvider } from '@pake/agent-runtime';

const provider = new NullProvider({
  timeout: 10000,
  concurrency: 5,
});

// Always returns consistent, predictable results
const result = await provider.run(task);
```

**Features:**

- Deterministic outputs based on task ID hashing
- Simulated processing delays (50-150ms)
- All agent capabilities supported
- Perfect for unit testing and development

### Custom Providers

Implement the `AgentProvider` interface:

```typescript
import { AgentProvider, AgentTask, AgentResult } from '@pake/agent-runtime';

class CustomProvider implements AgentProvider {
  readonly name = 'CustomProvider';
  readonly version = '1.0.0';
  readonly capabilities = [
    /* ... */
  ];

  async run(task: AgentTask): Promise<AgentResult> {
    // Your implementation here
  }

  async healthCheck(): Promise<boolean> {
    return true;
  }

  async dispose(): Promise<void> {
    // Cleanup resources
  }
}
```

## JSON Schemas

Three core schemas define the contract:

### AgentTask Schema

Validates task input structure:

```json
{
  "id": "task_001",
  "type": "sentiment_analysis",
  "input": {
    "content": "Analyze this text",
    "data": { "language": "en" }
  },
  "config": {
    "timeout": 30000,
    "priority": 5
  },
  "metadata": {
    "source": "api",
    "createdAt": "2024-01-01T12:00:00Z"
  }
}
```

### AgentResult Schema

Validates execution output:

```json
{
  "taskId": "task_001",
  "status": "success",
  "output": {
    "sentiment": {
      "score": 0.8,
      "label": "positive",
      "confidence": 0.95
    }
  },
  "metadata": {
    "provider": "NullProvider",
    "duration": 150,
    "confidence": 0.9
  }
}
```

### TrendRecord Schema

Comprehensive trend analysis structure aligned with compendium schema.

## Development

### Setup

```bash
# Install dependencies
npm install

# Build TypeScript
npm run build

# Run tests
npm test

# Run with coverage
npm run test:coverage

# Lint and format
npm run lint
npm run format
```

### Testing

```bash
# Unit tests
npm run test:unit

# Contract tests
npm run test:contract

# Schema validation
npm run validate-schemas

# Full CI pipeline
npm run ci
```

### Project Structure

```
services/agent-runtime/
├── src/
│   ├── providers/
│   │   ├── AgentProvider.ts      # Core interface
│   │   └── NullProvider.ts       # Reference implementation
│   ├── schemas/
│   │   ├── AgentTask.json        # Task validation schema
│   │   ├── AgentResult.json      # Result validation schema
│   │   └── TrendRecord.json      # Trend analysis schema
│   ├── types/
│   │   └── index.ts              # TypeScript definitions
│   └── index.ts                  # Main exports
├── ../config/
│   └── FeatureFlags.ts           # Feature flag system
├── tests/
│   ├── unit/                     # Unit test suite
│   ├── contract/                 # Contract test suite
│   └── setup.ts                  # Test configuration
├── package.json                  # Dependencies and scripts
├── tsconfig.json                 # TypeScript configuration
└── README.md                     # This file
```

## Architecture Guarantees

1. **Provider Interface Compliance**: All providers implement the same contract, ensuring consistent behavior and easy swapping.

2. **Schema-Driven Validation**: JSON schemas enforce data contracts at runtime, preventing invalid inputs/outputs from propagating.

3. **Feature Flag Isolation**: Environment-driven configuration prevents production impact while enabling gradual rollouts and A/B testing.

## Contributing

1. Follow TypeScript strict mode requirements
2. Maintain 80%+ test coverage
3. Update JSON schemas for breaking changes
4. Add feature flags for new functionality
5. Document provider implementations

## License

MIT License - See LICENSE file for details.
