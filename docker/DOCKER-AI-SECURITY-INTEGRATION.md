# Docker AI Security Integration Documentation

## Overview

This document details the Docker containerization and orchestration changes made to integrate AI-powered security monitoring into the PAKE system. The integration uses Docker Compose profiles to ensure the security monitoring stack is completely optional and does not affect production operations.

## Files Added/Modified

### New Files Created

#### 1. `docker-compose.override.yml` (Root Directory)
**Purpose**: Extends the base PAKE Docker Compose configuration with optional AI security services  
**Size**: 7,128 bytes  
**Location**: `/docker-compose.override.yml`

**Key Features**:
- Profile-based service deployment
- Complete ELK stack integration
- AI security monitor containerization
- Health check implementations
- Service dependency management

**Profiles Implemented**:
- `elk`: Elasticsearch, Logstash, Kibana, Filebeat only
- `ai-security`: AI security monitor only
- `security-monitoring`: AI monitor + basic ELK stack
- `full`: Complete security monitoring stack

**Services Added**:

##### Elasticsearch Service
```yaml
elasticsearch:
  image: elasticsearch:8.11.0
  container_name: pake_elasticsearch
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
    - "ES_JAVA_OPTS=-Xms512m -Xmx1g"
  ports:
    - "${ELASTICSEARCH_PORT:-9200}:9200"
  profiles: [elk, security-monitoring, full]
```

##### Logstash Service  
```yaml
logstash:
  image: logstash:8.11.0
  container_name: pake_logstash
  depends_on:
    elasticsearch: { condition: service_healthy }
  ports:
    - "5044:5044"  # Beats input
    - "9600:9600"  # API/Monitoring
```

##### Kibana Service
```yaml
kibana:
  image: kibana:8.11.0
  container_name: pake_kibana
  depends_on:
    elasticsearch: { condition: service_healthy }
  ports:
    - "5601:5601"
  environment:
    ELASTICSEARCH_HOSTS: http://elasticsearch:9200
```

##### Filebeat Service
```yaml
filebeat:
  image: elastic/filebeat:8.11.0
  container_name: pake_filebeat
  command: ["filebeat", "-e", "-strict.perms=false"]
  volumes:
    - ./logs:/logs:ro
    - /var/lib/docker/containers:/var/lib/docker/containers:ro
```

##### AI Security Monitor
```yaml
ai-security-monitor:
  build:
    context: ./docker
    dockerfile: Dockerfile.ai-security
  container_name: pake_ai_security_monitor
  ports:
    - "8080:8080"
  environment:
    LLM_PROVIDER: mock
    ELASTICSEARCH_HOST: elasticsearch
    MCP_INTEGRATION_ENABLED: "true"
```

##### Security Dashboard
```yaml
security-dashboard:
  image: nginx:alpine
  container_name: pake_security_dashboard
  ports:
    - "8090:80"
  volumes:
    - ./security-dashboard:/usr/share/nginx/html:ro
```

#### 2. `Dockerfile.ai-security` (Docker Directory)
**Purpose**: Container definition for AI Security Monitor service  
**Size**: 1,305 bytes  
**Location**: `/docker/Dockerfile.ai-security`

**Build Strategy**: Multi-stage build for optimized production image

**Base Image**: `python:3.11-slim`

**Key Build Steps**:
```dockerfile
# Stage 1: Dependencies
FROM python:3.11-slim as dependencies
WORKDIR /app
COPY requirements-ai-security.txt .
RUN pip install --no-cache-dir -r requirements-ai-security.txt

# Stage 2: Application
FROM python:3.11-slim
WORKDIR /app
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY ai-security-monitor.py .
COPY ai-security-config.yml ./config.yml

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080
CMD ["python", "ai-security-monitor.py"]
```

## Docker Network Configuration

### Network Architecture
- **Network Name**: `pake_network` (extends existing PAKE network)
- **Driver**: bridge
- **Subnet**: 172.20.0.0/16 (maintains existing configuration)

### Service Communication
- **Internal DNS**: Services communicate using container names
- **Elasticsearch**: `elasticsearch:9200` (internal)
- **MCP Server**: `mcp_server:8000` (existing)
- **Redis**: `redis:6379` (existing)
- **PostgreSQL**: `postgres:5432` (existing)

## Volume Management

### New Volumes Created
```yaml
volumes:
  elasticsearch_data:
    name: docker_elasticsearch_data
    driver: local
  filebeat_data:
    name: docker_filebeat_data
    driver: local
  ai_security_data:
    name: docker_ai_security_data
    driver: local
```

### Volume Mappings
- **Log Directory**: `./logs:/logs:ro` (shared across all services)
- **ELK Configs**: `./elk-config/*:/usr/share/*/config/*:ro`
- **Security Dashboard**: `./security-dashboard:/usr/share/nginx/html:ro`
- **Docker Socket**: `/var/run/docker.sock:/var/run/docker.sock:ro` (for Filebeat)

## Environment Variables

### AI Security Monitor Variables
```bash
# Core Configuration
API_HOST=0.0.0.0
API_PORT=8080
LOG_LEVEL=INFO

# AI/LLM Settings  
LLM_PROVIDER=mock
LLM_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=your_openai_key_here

# Elasticsearch Integration
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX_PATTERN=logs-*

# MCP Integration
MCP_INTEGRATION_ENABLED=true
MCP_HOST=mcp_server
MCP_PORT=8000

# Database Connections
DATABASE_URL=postgresql://pake_admin:process.env.SERVICE_PASSWORD || 'SECURE_PASSWORD_REQUIRED'@postgres:5432/pake_knowledge
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=process.env.REDIS_PASSWORD || 'SECURE_PASSWORD_REQUIRED'

# Security Settings
MIN_CONFIDENCE_THRESHOLD=0.3
ANALYSIS_INTERVAL=300
ALERT_RETENTION_DAYS=7
ENABLE_AUTO_BLOCKING=false
```

### ELK Stack Variables
```bash
# Elasticsearch
ES_JAVA_OPTS=-Xms512m -Xmx1g
discovery.type=single-node
xpack.security.enabled=false

# Logstash
LS_JAVA_OPTS=-Xmx512m -Xms256m

# Kibana
ELASTICSEARCH_HOSTS=http://elasticsearch:9200
SERVER_HOST=0.0.0.0
XPACK_SECURITY_ENABLED=false

# Filebeat
ELASTICSEARCH_HOST=elasticsearch:9200
KIBANA_HOST=kibana:5601
```

## Health Checks Implementation

### Elasticsearch Health Check
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
```

### Kibana Health Check
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:5601/api/status || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 5
```

### AI Security Monitor Health Check
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Service Dependencies

### Dependency Chain
```
AI Security Monitor → Elasticsearch (healthy) + MCP Server (started)
Security Dashboard → AI Security Monitor (healthy) + Kibana (healthy)  
Kibana → Elasticsearch (healthy)
Logstash → Elasticsearch (healthy)
Filebeat → Elasticsearch (healthy)
```

### Startup Order
1. **Core PAKE Services**: postgres, redis, mcp_server (existing)
2. **Elasticsearch**: Data storage foundation
3. **Logstash + Filebeat**: Log processing pipeline
4. **Kibana**: Visualization layer
5. **AI Security Monitor**: Analysis service
6. **Security Dashboard**: Web interface

## Deployment Commands

### Profile-Based Deployment
```bash
# Full security stack
docker compose -f docker/docker-compose.yml -f docker-compose.override.yml --profile full up -d

# ELK stack only
docker compose -f docker/docker-compose.yml -f docker-compose.override.yml --profile elk up -d

# AI security only
docker compose -f docker/docker-compose.yml -f docker-compose.override.yml --profile ai-security up -d

# Security monitoring (default)
docker compose -f docker/docker-compose.yml -f docker-compose.override.yml --profile security-monitoring up -d
```

### Management Commands
```bash
# View running services
docker compose ps

# View logs
docker compose logs ai-security-monitor
docker compose logs elasticsearch

# Stop services
docker compose --profile full down

# Update services
docker compose --profile full up -d --build
```

## Resource Allocation

### Memory Requirements
- **Elasticsearch**: 1GB (512MB min, 1GB max)
- **Logstash**: 512MB (256MB min, 512MB max)
- **Kibana**: 512MB default
- **AI Security Monitor**: 256MB typical
- **Filebeat**: 128MB typical
- **Security Dashboard**: 64MB typical

### CPU Requirements
- **Base Load**: ~10% per service
- **Peak Load**: ~25% during analysis
- **Elasticsearch**: CPU-intensive during indexing
- **AI Monitor**: CPU-intensive during pattern analysis

### Disk Requirements
- **Elasticsearch Data**: 1GB per day of logs (configurable retention)
- **Application Logs**: 100MB per day typical
- **Container Images**: ~2GB total download

## Security Considerations

### Development vs Production
- **Security Disabled**: XPack security disabled for development
- **Network Isolation**: Services isolated within Docker network
- **Read-Only Mounts**: Configuration files mounted read-only
- **User Privileges**: Containers run as non-root where possible

### Production Hardening Recommendations
- Enable XPack security for Elasticsearch
- Implement TLS/SSL certificates
- Use Docker secrets for sensitive data
- Implement container resource limits
- Enable audit logging
- Use dedicated service accounts

## Monitoring & Observability

### Health Monitoring
- All critical services have health checks
- Health check failures trigger container restarts
- Service status available via APIs

### Log Aggregation
- All container logs collected by Docker logging driver
- Application logs aggregated through Filebeat
- Structured logging with JSON format

### Metrics Collection
- Elasticsearch metrics via API
- Application metrics via Prometheus endpoints
- System metrics via Docker stats API

## Troubleshooting

### Common Issues
1. **Elasticsearch startup failure**: Check memory allocation
2. **Health check timeouts**: Verify service startup time
3. **Network connectivity**: Verify Docker network configuration
4. **Volume permissions**: Check bind mount permissions

### Debug Commands
```bash
# Check service status
docker compose ps

# View service logs  
docker compose logs [service_name]

# Test connectivity
docker compose exec ai-security-monitor curl elasticsearch:9200/_cluster/health

# Inspect containers
docker inspect pake_elasticsearch

# Check resource usage
docker stats
```

## Integration Testing

### Verification Steps
1. **Configuration Validation**: `docker compose config`
2. **Service Startup**: All services start without errors
3. **Health Checks**: All health checks pass
4. **Network Connectivity**: Services can communicate
5. **Data Flow**: Logs flow from Filebeat → Logstash → Elasticsearch
6. **API Accessibility**: All APIs respond correctly

### Test Commands
```bash
# Validate configuration
docker compose -f docker/docker-compose.yml -f docker-compose.override.yml --profile full config

# Test Elasticsearch
curl http://localhost:9200/_cluster/health

# Test AI Security API
curl http://localhost:8080/health

# Test Kibana
curl http://localhost:5601/api/status

# Test Security Dashboard
curl http://localhost:8090
```

This Docker integration provides a robust, scalable, and optional security monitoring platform that seamlessly extends the existing PAKE system infrastructure.