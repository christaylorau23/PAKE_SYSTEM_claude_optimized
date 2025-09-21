# PAKE System - Voice Agents Service

Enterprise-grade voice agent service with Vapi.ai integration, advanced error handling, and real-time conversation management.

## Overview

The Voice Agents Service provides sophisticated voice AI capabilities including:

- **Vapi.ai Integration**: Seamless voice assistant creation and call management
- **Advanced Error Handling**: Circuit breaker patterns with automatic failover
- **Real-time Conversations**: Context-aware dialogue with memory persistence
- **Knowledge Integration**: Dynamic knowledge vault searches for contextual responses
- **Quality Monitoring**: Comprehensive voice quality tracking and optimization
- **Enterprise Security**: Rate limiting, input validation, and secure communication

## Quick Start

### Prerequisites

- Node.js 18+
- Docker & Docker Compose
- Redis (for conversation persistence)
- Vapi.ai API key

### Environment Setup

1. Copy environment template:

```bash
cp .env.example .env
```

2. Configure required variables in `.env`:

```bash
# Vapi.ai Configuration
VAPI_API_KEY=your_vapi_api_key_here
DEFAULT_VOICE_ID=en-US-Standard-A
DEFAULT_KNOWLEDGE_BASE_ID=default

# Service Configuration
VOICE_AGENT_PORT=9000
REDIS_URL=redis://localhost:6379
NODE_ENV=production
LOG_LEVEL=info
```

### Development

```bash
# Install dependencies
npm install

# Start development server
npm run start:dev

# With Docker (recommended)
docker-compose -f docker-compose.dev.yml up -d
```

### Production Deployment

```bash
# Build images
./scripts/build.sh

# Deploy services
./scripts/deploy.sh

# Or with Docker Compose
docker-compose up -d
```

## API Endpoints

### Voice Assistant Management

- `POST /api/v1/assistants` - Create voice assistant
- `GET /api/v1/assistants` - List assistants

### Voice Call Management

- `POST /api/v1/calls` - Initiate voice call
- `GET /api/v1/calls/:callId` - Get call status
- `PATCH /api/v1/calls/:callId` - Update call context
- `DELETE /api/v1/calls/:callId` - End voice call

### Knowledge Integration

- `POST /api/v1/knowledge/search` - Search knowledge base

### Conversation Management

- `GET /api/v1/conversations/:sessionId` - Get conversation context
- `POST /api/v1/conversations/:sessionId/messages` - Add message
- `DELETE /api/v1/conversations/:sessionId` - End conversation

### Monitoring

- `GET /health` - Health check
- `GET /ready` - Readiness check
- `GET /metrics` - Service metrics
- `GET /status` - Service status

## Architecture

### Core Components

- **VapiVoiceAgent**: Main integration with Vapi.ai API
- **CircuitBreaker**: Advanced error handling and automatic failover
- **ConversationManager**: Session and context management
- **KnowledgeConnector**: Real-time knowledge vault integration
- **VoiceMonitor**: Quality tracking and performance monitoring

### Error Handling

The service implements sophisticated error handling including:

- Circuit breaker patterns for external API failures
- Automatic retry mechanisms with exponential backoff
- Fallback providers for voice generation
- Graceful degradation of non-critical features

### Conversation Management

- **Session Persistence**: Redis-backed conversation storage
- **Context Compression**: Intelligent context reduction for large histories
- **User Preferences**: Personalized voice settings and styles
- **Multi-turn Dialogue**: Advanced conversation flow management

## Configuration

### Environment Variables

| Variable           | Description          | Default                |
| ------------------ | -------------------- | ---------------------- |
| `VAPI_API_KEY`     | Vapi.ai API key      | Required               |
| `VOICE_AGENT_PORT` | Service port         | 9000                   |
| `REDIS_URL`        | Redis connection URL | redis://localhost:6379 |
| `LOG_LEVEL`        | Logging level        | info                   |
| `NODE_ENV`         | Environment          | development            |

### Voice Quality Settings

| Variable                  | Description             | Default    |
| ------------------------- | ----------------------- | ---------- |
| `VOICE_RESPONSE_TIMEOUT`  | Response timeout (ms)   | 5000       |
| `VOICE_STREAMING_LATENCY` | Streaming latency level | 3          |
| `VOICE_QUALITY_THRESHOLD` | Quality threshold       | 0.8        |
| `FALLBACK_PROVIDER`       | Fallback voice provider | elevenlabs |

### Circuit Breaker Settings

| Variable                            | Description             | Default |
| ----------------------------------- | ----------------------- | ------- |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | Failure count threshold | 5       |
| `CIRCUIT_BREAKER_RESET_TIMEOUT`     | Reset timeout (ms)      | 60000   |
| `CIRCUIT_BREAKER_MONITOR_WINDOW`    | Monitoring window (ms)  | 60000   |

## Monitoring & Observability

### Metrics

The service exposes comprehensive metrics including:

- **Voice Quality**: Audio quality scores, latency measurements
- **API Performance**: Request/response times, error rates
- **Conversation Flow**: Session durations, message counts
- **Resource Usage**: Memory, CPU, Redis utilization

### Health Checks

- **Health Endpoint**: Basic service health (`/health`)
- **Readiness Check**: Dependency readiness (`/ready`)
- **Deep Health**: Component-level health checks

### Logging

Structured logging with configurable levels:

- **Console Logging**: Development-friendly output
- **File Logging**: Production log files with rotation
- **Structured JSON**: Machine-readable log format

## Development

### Scripts

```bash
npm run build          # Build TypeScript
npm run start          # Start production server
npm run start:dev      # Start development server
npm run start:watch    # Start with hot reload
npm run test           # Run tests
npm run test:coverage  # Run tests with coverage
npm run lint           # Lint code
npm run format         # Format code
```

### Docker Commands

```bash
# Build images
./scripts/build.sh --prod    # Production only
./scripts/build.sh --dev     # Development only
./scripts/build.sh           # Both images

# Deploy
./scripts/deploy.sh          # Production deployment
./scripts/deploy.sh --dev    # Development deployment
```

## Security

- **Input Validation**: Joi schemas for all API inputs
- **Rate Limiting**: Configurable request limits
- **CORS Protection**: Strict origin policies
- **Helmet Security**: Security headers and CSP
- **Authentication**: API key validation

## Performance

- **Connection Pooling**: Optimized HTTP client configuration
- **Response Caching**: Intelligent caching for knowledge queries
- **Memory Management**: Efficient conversation context handling
- **Load Balancing**: Ready for horizontal scaling

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Check Redis server status
   - Verify connection string in environment

2. **Vapi.ai API Errors**
   - Validate API key configuration
   - Check rate limits and quotas

3. **High Memory Usage**
   - Review conversation TTL settings
   - Monitor Redis memory usage

### Debug Mode

Enable debug logging:

```bash
LOG_LEVEL=debug npm run start:dev
```

## Support

For technical support and feature requests, please refer to the PAKE System documentation or contact the development team.

## License

MIT License - see LICENSE file for details.
