# PAKE System - Maintenance & Operations Guide

## Overview

This comprehensive guide provides detailed procedures for maintaining and operating the PAKE System in production environments. It covers monitoring, maintenance, troubleshooting, and long-term health management.

## Table of Contents

1. [System Monitoring](#system-monitoring)
2. [Health Monitoring](#health-monitoring)
3. [Logging and Observability](#logging-and-observability)
4. [Maintenance Tasks](#maintenance-tasks)
5. [Troubleshooting](#troubleshooting)
6. [Performance Optimization](#performance-optimization)
7. [Backup and Recovery](#backup-and-recovery)
8. [Security Operations](#security-operations)
9. [Capacity Planning](#capacity-planning)
10. [Incident Response](#incident-response)

## System Monitoring

### Health Monitoring Framework

The PAKE System includes a comprehensive health monitoring framework that tracks:

- **System Metrics**: CPU, memory, disk, network usage
- **Service Health**: Database, Redis, API gateway, ingestion services
- **Application Metrics**: Response times, error rates, throughput
- **Security Metrics**: Failed logins, suspicious activities, vulnerabilities

#### Health Check Endpoints

```bash
# System health check
curl http://localhost:8000/health

# Detailed health report
curl http://localhost:8000/health/detailed

# Service-specific health checks
curl http://localhost:8000/health/database
curl http://localhost:8000/health/redis
curl http://localhost:8000/health/api-gateway
```

#### Health Monitoring Commands

```bash
# Start health monitoring
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def start_monitoring():
    health_monitor = HealthMonitoringSystem()
    await health_monitor.start_monitoring(interval_seconds=60)

asyncio.run(start_monitoring())
"

# Generate health report
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def generate_report():
    health_monitor = HealthMonitoringSystem()
    report = await health_monitor.generate_health_report()
    print(f'System Status: {report.overall_status.value}')
    print(f'Uptime: {report.uptime_seconds / 3600:.1f} hours')
    print(f'Alerts: {len(report.alerts)}')

asyncio.run(generate_report())
"
```

### Performance Monitoring

#### Key Performance Indicators (KPIs)

| Metric | Target | Warning | Critical | Action |
|--------|--------|---------|----------|--------|
| API Response Time | < 200ms | > 500ms | > 1000ms | Scale up/optimize |
| Database Query Time | < 100ms | > 300ms | > 500ms | Optimize queries |
| Memory Usage | < 70% | > 80% | > 95% | Scale up memory |
| CPU Usage | < 60% | > 80% | > 95% | Scale up CPU |
| Disk Usage | < 70% | > 80% | > 95% | Clean up/expand |
| Error Rate | < 1% | > 2% | > 5% | Investigate errors |

#### Performance Monitoring Commands

```bash
# Monitor system performance
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def monitor_performance():
    health_monitor = HealthMonitoringSystem()
    metrics = await health_monitor.collect_system_metrics()
    
    for metric in metrics:
        print(f'{metric.metric_name}: {metric.value} {metric.unit} ({metric.status.value})')

asyncio.run(monitor_performance())
"

# Get performance trends
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def get_trends():
    health_monitor = HealthMonitoringSystem()
    trends = await health_monitor.get_health_trends(days=7)
    print(f'Health Score: {trends[\"summary\"][\"health_score\"]:.1f}')
    print(f'Trend: {trends[\"trends\"][\"trend\"]}')

asyncio.run(get_trends())
"
```

## Logging and Observability

### Structured Logging

The PAKE System uses structured logging with multiple outputs:

- **Application Logs**: `logs/application.log`
- **Error Logs**: `logs/errors.log`
- **Audit Logs**: `logs/audit.log`
- **Performance Logs**: `logs/performance.log`
- **Security Logs**: `logs/security/security.log`

#### Logging Commands

```bash
# View real-time logs
tail -f logs/application.log

# View error logs
tail -f logs/errors.log

# View audit logs
tail -f logs/audit.log

# Search logs
grep "ERROR" logs/application.log
grep "security_event" logs/security/security.log
```

#### Log Analysis

```bash
# Analyze log patterns
python -c "
from monitoring.logging_framework import LoggingFramework
import asyncio

async def analyze_logs():
    logging_framework = LoggingFramework()
    report = await logging_framework.generate_log_report(days=7)
    
    print(f'Total Events: {report[\"summary\"][\"total_audit_events\"]}')
    print(f'Unique Users: {report[\"summary\"][\"unique_users\"]}')
    print(f'Top Events: {report[\"event_breakdown\"]}')

asyncio.run(analyze_logs())
"
```

### Distributed Tracing

The system supports distributed tracing for request flow analysis:

```bash
# Start tracing (requires Jaeger)
export JAEGER_AGENT_HOST=localhost
export JAEGER_AGENT_PORT=14268

# View traces in Jaeger UI
open http://localhost:16686
```

## Maintenance Tasks

### Automated Maintenance

The PAKE System includes automated maintenance tasks:

| Task | Schedule | Description | Timeout |
|------|----------|-------------|---------|
| Log Cleanup | Daily 2 AM | Clean old log files | 15 min |
| Database Backup | Daily 1 AM | Create database backup | 60 min |
| Cache Cleanup | Every 6 hours | Clear expired cache | 10 min |
| Security Scan | Weekly Sunday 3 AM | Vulnerability scan | 45 min |
| Capacity Check | Every 4 hours | Check system capacity | 5 min |
| Performance Optimization | Weekly Sunday 4 AM | System optimization | 30 min |

#### Maintenance Commands

```bash
# Run specific maintenance task
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def run_maintenance():
    health_monitor = HealthMonitoringSystem()
    success = await health_monitor.run_maintenance_task('log_cleanup')
    print(f'Maintenance task result: {success}')

asyncio.run(run_maintenance())
"

# Run all scheduled maintenance
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def run_scheduled():
    health_monitor = HealthMonitoringSystem()
    await health_monitor.run_scheduled_maintenance()
    print('Scheduled maintenance completed')

asyncio.run(run_scheduled())
"
```

### Manual Maintenance Tasks

#### Database Maintenance

```bash
# Database optimization
python -c "
import asyncio
from services.database.connection_manager import DatabaseConnectionManager

async def optimize_database():
    db_manager = DatabaseConnectionManager()
    await db_manager.connect()
    
    # Run VACUUM ANALYZE
    await db_manager.execute_query('VACUUM ANALYZE;')
    
    # Check database size
    result = await db_manager.fetch_one('SELECT pg_size_pretty(pg_database_size(current_database()));')
    print(f'Database size: {result[0]}')
    
    await db_manager.disconnect()

asyncio.run(optimize_database())
"
```

#### Cache Maintenance

```bash
# Clear cache
python -c "
import asyncio
from services.caching.redis_cache_strategy import RedisCacheStrategy

async def clear_cache():
    cache = RedisCacheStrategy('redis://localhost:6379')
    await cache.start()
    
    # Clear all cache
    await cache.clear_all()
    print('Cache cleared')
    
    await cache.stop()

asyncio.run(clear_cache())
"
```

## Troubleshooting

### Common Issues and Solutions

#### High Memory Usage

**Symptoms**: System slow, memory usage > 90%

**Diagnosis**:
```bash
# Check memory usage
python -c "
import psutil
memory = psutil.virtual_memory()
print(f'Memory usage: {memory.percent:.1f}%')
print(f'Available: {memory.available / (1024**3):.1f} GB')
"

# Check for memory leaks
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def check_memory():
    health_monitor = HealthMonitoringSystem()
    metrics = await health_monitor.collect_system_metrics()
    
    memory_metric = next((m for m in metrics if m.metric_name == 'memory_usage_percent'), None)
    if memory_metric:
        print(f'Memory status: {memory_metric.status.value}')
        if memory_metric.status.value != 'healthy':
            print('Memory usage is high - consider scaling up or investigating memory leaks')

asyncio.run(check_memory())
"
```

**Solutions**:
1. Scale up memory allocation
2. Investigate memory leaks in application code
3. Optimize data structures and algorithms
4. Clear unused cache entries

#### Database Performance Issues

**Symptoms**: Slow queries, high database CPU usage

**Diagnosis**:
```bash
# Check database performance
python -c "
import asyncio
from services.database.connection_manager import DatabaseConnectionManager

async def check_db_performance():
    db_manager = DatabaseConnectionManager()
    await db_manager.connect()
    
    # Check active connections
    result = await db_manager.fetch_one('SELECT count(*) FROM pg_stat_activity;')
    print(f'Active connections: {result[0]}')
    
    # Check slow queries
    result = await db_manager.fetch_all('''
        SELECT query, mean_time, calls 
        FROM pg_stat_statements 
        ORDER BY mean_time DESC 
        LIMIT 5;
    ''')
    
    print('Slowest queries:')
    for row in result:
        print(f'  {row[0][:50]}... - {row[1]:.2f}ms avg, {row[2]} calls')
    
    await db_manager.disconnect()

asyncio.run(check_db_performance())
"
```

**Solutions**:
1. Optimize slow queries
2. Add database indexes
3. Scale up database resources
4. Implement query caching

#### API Gateway Issues

**Symptoms**: High response times, connection errors

**Diagnosis**:
```bash
# Check API gateway health
curl -v http://localhost:8000/health

# Check API performance
python -c "
import asyncio
import aiohttp
import time

async def check_api_performance():
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8000/health') as response:
            duration = (time.time() - start_time) * 1000
            print(f'API response time: {duration:.2f}ms')
            print(f'Status: {response.status}')

asyncio.run(check_api_performance())
"
```

**Solutions**:
1. Scale up API gateway instances
2. Implement load balancing
3. Optimize API endpoints
4. Add caching layers

### Error Investigation

#### Application Errors

```bash
# Analyze error patterns
python -c "
from monitoring.logging_framework import LoggingFramework
import asyncio

async def analyze_errors():
    logging_framework = LoggingFramework()
    
    # Get recent errors
    audit_logs = await logging_framework.get_audit_logs(
        start_date=datetime.now(UTC) - timedelta(hours=24)
    )
    
    error_logs = [log for log in audit_logs if log.result == 'failure']
    print(f'Errors in last 24h: {len(error_logs)}')
    
    # Group by error type
    error_types = {}
    for log in error_logs:
        error_types[log.event_type] = error_types.get(log.event_type, 0) + 1
    
    print('Error breakdown:')
    for error_type, count in error_types.items():
        print(f'  {error_type}: {count}')

asyncio.run(analyze_errors())
"
```

#### Security Incidents

```bash
# Check security incidents
python -c "
from security.security_monitoring import SecurityMonitoringSystem
import asyncio

async def check_security():
    security_monitor = SecurityMonitoringSystem()
    
    # Get open incidents
    open_incidents = await security_monitor.get_open_incidents()
    print(f'Open security incidents: {len(open_incidents)}')
    
    for incident in open_incidents:
        print(f'  {incident.incident_id}: {incident.title} ({incident.threat_level.value})')
    
    # Get incident metrics
    metrics = await security_monitor.get_incident_metrics(days=7)
    print(f'Incidents in last 7 days: {metrics[\"summary\"][\"total_incidents\"]}')

asyncio.run(check_security())
"
```

## Performance Optimization

### Application Optimization

#### Code Optimization

```bash
# Profile application performance
python -c "
import cProfile
import pstats
from services.ingestion.orchestrator import IngestionOrchestrator

def profile_ingestion():
    orchestrator = IngestionOrchestrator()
    # Profile ingestion process
    cProfile.run('orchestrator.execute_plan(test_plan)', 'profile_output.prof')
    
    # Analyze results
    p = pstats.Stats('profile_output.prof')
    p.sort_stats('cumulative').print_stats(10)

profile_ingestion()
"
```

#### Database Optimization

```bash
# Analyze database performance
python -c "
import asyncio
from services.database.connection_manager import DatabaseConnectionManager

async def analyze_db_performance():
    db_manager = DatabaseConnectionManager()
    await db_manager.connect()
    
    # Check table sizes
    result = await db_manager.fetch_all('''
        SELECT schemaname, tablename, 
               pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
    ''')
    
    print('Table sizes:')
    for row in result:
        print(f'  {row[1]}: {row[2]}')
    
    # Check index usage
    result = await db_manager.fetch_all('''
        SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
        FROM pg_stat_user_indexes 
        ORDER BY idx_scan DESC 
        LIMIT 10;
    ''')
    
    print('Index usage:')
    for row in result:
        print(f'  {row[2]}: {row[3]} scans')
    
    await db_manager.disconnect()

asyncio.run(analyze_db_performance())
"
```

### Infrastructure Optimization

#### Resource Scaling

```bash
# Check resource utilization
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def check_resources():
    health_monitor = HealthMonitoringSystem()
    metrics = await health_monitor.collect_system_metrics()
    
    # Check CPU usage
    cpu_metric = next((m for m in metrics if m.metric_name == 'cpu_usage_percent'), None)
    if cpu_metric and cpu_metric.value > 80:
        print('CPU usage is high - consider scaling up')
    
    # Check memory usage
    memory_metric = next((m for m in metrics if m.metric_name == 'memory_usage_percent'), None)
    if memory_metric and memory_metric.value > 80:
        print('Memory usage is high - consider scaling up')
    
    # Check disk usage
    disk_metric = next((m for m in metrics if m.metric_name == 'disk_usage_percent'), None)
    if disk_metric and disk_metric.value > 80:
        print('Disk usage is high - consider expanding storage')

asyncio.run(check_resources())
"
```

## Backup and Recovery

### Automated Backups

The system includes automated backup procedures:

```bash
# Run backup task
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def run_backup():
    health_monitor = HealthMonitoringSystem()
    success = await health_monitor.run_maintenance_task('database_backup')
    
    if success:
        print('Backup completed successfully')
    else:
        print('Backup failed - check logs')

asyncio.run(run_backup())
"
```

### Manual Backup Procedures

#### Database Backup

```bash
# Create database backup
pg_dump -h localhost -U postgres -d pake_system > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database backup
psql -h localhost -U postgres -d pake_system < backup_20240115_120000.sql
```

#### Configuration Backup

```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    .env \
    config/ \
    security/ \
    monitoring/

# Backup secrets (if using local storage)
tar -czf secrets_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    secrets/ \
    --exclude='*.log'
```

## Security Operations

### Security Monitoring

```bash
# Check security status
python -c "
from security.security_monitoring import SecurityMonitoringSystem
import asyncio

async def check_security():
    security_monitor = SecurityMonitoringSystem()
    
    # Generate security report
    report = await security_monitor.generate_security_report(days=7)
    
    print(f'Security Events: {report[\"summary\"][\"total_security_events\"]}')
    print(f'Critical Events: {report[\"summary\"][\"critical_events\"]}')
    print(f'Open Incidents: {report[\"summary\"][\"open_incidents\"]}')
    
    if report['recommendations']:
        print('Recommendations:')
        for rec in report['recommendations']:
            print(f'  - {rec}')

asyncio.run(check_security())
"
```

### Vulnerability Management

```bash
# Run vulnerability scan
python -c "
from security.security_hardening_framework import SecurityHardeningFramework
import asyncio

async def scan_vulnerabilities():
    security_framework = SecurityHardeningFramework()
    scan_results = await security_framework.scan_dependencies()
    
    print(f'Total Vulnerabilities: {scan_results[\"summary\"][\"total_vulnerabilities\"]}')
    print(f'Critical: {scan_results[\"summary\"][\"critical\"]}')
    print(f'High: {scan_results[\"summary\"][\"high\"]}')
    print(f'Medium: {scan_results[\"summary\"][\"medium\"]}')

asyncio.run(scan_vulnerabilities())
"
```

## Capacity Planning

### Resource Monitoring

```bash
# Analyze capacity trends
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def analyze_capacity():
    health_monitor = HealthMonitoringSystem()
    trends = await health_monitor.get_health_trends(days=30)
    
    print(f'Health Score Trend: {trends[\"trends\"][\"trend\"]}')
    print(f'Average Uptime: {trends[\"summary\"][\"average_uptime_hours\"]:.1f} hours')
    
    # Check for capacity issues
    if trends['trends']['trend'] == 'declining':
        print('System health is declining - consider capacity planning')

asyncio.run(analyze_capacity())
"
```

### Scaling Recommendations

Based on monitoring data, the system provides scaling recommendations:

- **CPU Scaling**: When CPU usage consistently > 80%
- **Memory Scaling**: When memory usage consistently > 80%
- **Storage Scaling**: When disk usage > 80%
- **Database Scaling**: When query times increase significantly

## Incident Response

### Incident Classification

| Severity | Response Time | Escalation | Examples |
|----------|---------------|------------|----------|
| Critical | Immediate | On-call team | System down, data breach |
| High | 1 hour | Team lead | Performance degradation |
| Medium | 4 hours | Regular team | Minor issues |
| Low | 24 hours | Next business day | Cosmetic issues |

### Incident Response Procedures

#### 1. Detection and Alerting

```bash
# Check for active incidents
python -c "
from security.security_monitoring import SecurityMonitoringSystem
import asyncio

async def check_incidents():
    security_monitor = SecurityMonitoringSystem()
    open_incidents = await security_monitor.get_open_incidents()
    
    if open_incidents:
        print('Active incidents:')
        for incident in open_incidents:
            print(f'  {incident.incident_id}: {incident.title} ({incident.threat_level.value})')
    else:
        print('No active incidents')

asyncio.run(check_incidents())
"
```

#### 2. Investigation and Containment

```bash
# Investigate system health
python -c "
from monitoring.health_monitoring import HealthMonitoringSystem
import asyncio

async def investigate():
    health_monitor = HealthMonitoringSystem()
    report = await health_monitor.generate_health_report()
    
    print(f'System Status: {report.overall_status.value}')
    print(f'Active Alerts: {len(report.alerts)}')
    
    if report.alerts:
        print('Alerts:')
        for alert in report.alerts:
            print(f'  - {alert}')
    
    if report.recommendations:
        print('Recommendations:')
        for rec in report.recommendations:
            print(f'  - {rec}')

asyncio.run(investigate())
"
```

#### 3. Resolution and Recovery

```bash
# Update incident status
python -c "
from security.security_monitoring import SecurityMonitoringSystem
import asyncio

async def resolve_incident():
    security_monitor = SecurityMonitoringSystem()
    
    # Update incident status (example)
    # success = await security_monitor.update_incident_status(
    #     incident_id='inc_1234567890_abcd',
    #     status=IncidentStatus.RESOLVED,
    #     notes='Issue resolved by restarting service'
    # )
    
    print('Incident resolution procedures completed')

asyncio.run(resolve_incident())
"
```

## Quick Reference

### Daily Operations Checklist

- [ ] Check system health status
- [ ] Review security alerts
- [ ] Monitor performance metrics
- [ ] Check backup status
- [ ] Review error logs
- [ ] Verify service availability

### Weekly Operations Checklist

- [ ] Review security incidents
- [ ] Analyze performance trends
- [ ] Check capacity utilization
- [ ] Review maintenance tasks
- [ ] Update documentation
- [ ] Plan capacity scaling

### Monthly Operations Checklist

- [ ] Security audit review
- [ ] Performance optimization review
- [ ] Capacity planning assessment
- [ ] Backup and recovery testing
- [ ] Incident response review
- [ ] System architecture review

### Emergency Procedures

#### System Down

1. **Immediate Response**
   ```bash
   # Check system status
   curl http://localhost:8000/health
   
   # Check service status
   systemctl status pake-system
   
   # Check logs
   tail -f logs/errors.log
   ```

2. **Recovery Steps**
   ```bash
   # Restart services
   systemctl restart pake-system
   
   # Check database connectivity
   python -c "from services.database.connection_manager import DatabaseConnectionManager; print('DB OK')"
   
   # Verify system health
   python -c "from monitoring.health_monitoring import HealthMonitoringSystem; print('Health OK')"
   ```

#### Security Incident

1. **Immediate Response**
   ```bash
   # Check security incidents
   python -c "from security.security_monitoring import SecurityMonitoringSystem; print('Security OK')"
   
   # Review security logs
   tail -f logs/security/security.log
   ```

2. **Containment**
   - Isolate affected systems
   - Preserve evidence
   - Notify security team

3. **Recovery**
   - Apply security patches
   - Update access controls
   - Monitor for recurrence

## Conclusion

This comprehensive maintenance and operations guide provides the procedures and tools necessary to maintain the PAKE System in production. Regular use of these procedures ensures system reliability, security, and performance.

The guide emphasizes:
- **Proactive Monitoring**: Early detection of issues
- **Automated Maintenance**: Reduced manual intervention
- **Comprehensive Logging**: Full observability
- **Security Operations**: Continuous security monitoring
- **Incident Response**: Structured response procedures

Regular review and updates of this guide ensure that operational procedures remain effective and current with system evolution.
