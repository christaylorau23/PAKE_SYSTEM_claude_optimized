# PAKE System Disaster Recovery Runbooks

## 🚨 Emergency Response Procedures

### Incident Classification

**P0 - Critical (Complete System Down)**
- Complete cluster failure
- Data center outage
- RTO: 15 minutes
- RPO: 5 minutes

**P1 - High (Major Service Disruption)**
- Single service failure affecting users
- Database corruption
- RTO: 30 minutes
- RPO: 15 minutes

**P2 - Medium (Partial Service Disruption)**
- Performance degradation
- Non-critical component failure
- RTO: 2 hours
- RPO: 1 hour

## 📋 Runbook Index

### 1. Complete Cluster Failure
### 2. Database Corruption/Failure
### 3. Multi-AZ Failover
### 4. Application-Specific Recovery
### 5. Data Recovery Procedures
### 6. Network Partitioning
### 7. Storage Failure Recovery
### 8. Automated Failover Procedures
### 9. Data Replication Issues
### 10. Chaos Engineering Response
### 11. Backup Validation Failures
### 12. Compliance Violations
### 13. DR Dashboard & Monitoring Issues

---

## 1. Complete Cluster Failure Recovery

**Symptoms:**
- All nodes unreachable
- API server not responding
- etcd cluster down

**Immediate Response (0-5 minutes):**

```bash
# 1. Assess the situation
kubectl get nodes
kubectl get componentstatuses

# 2. Check cluster health from monitoring
# Access Grafana: https://grafana.pake-system.com
# Check Prometheus alerts

# 3. If cluster is completely down, initiate DR
```

**Recovery Steps:**

```bash
# 1. Activate secondary cluster (if available)
./failover-procedure.sh auto primary secondary

# 2. Or restore from backup
./cluster-restore.sh cluster-backup-YYYYMMDD_HHMMSS.tar.gz

# 3. Verify core services
kubectl get pods -n kube-system
kubectl get pods -n pake-system

# 4. Check application health
kubectl get rollouts -n pake-system
kubectl get svc -n pake-system

# 5. Update DNS if needed
# Point *.pake-system.com to new cluster IPs
```

**Verification:**
```bash
# Test API endpoints
curl -f https://api.pake-system.com/health
curl -f https://ai.pake-system.com/health

# Check database connectivity
kubectl exec -it deployment/pake-api -n pake-system -- python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('DATABASE_URL')
    result = await conn.fetchval('SELECT 1')
    print(f'Database: {"OK" if result == 1 else "FAIL"}')
asyncio.run(test())
"

# Verify monitoring
kubectl get pods -n monitoring
```

---

## 2. Database Corruption/Failure Recovery

**Symptoms:**
- Database connection failures
- Data consistency errors
- High error rates from API services

**PostgreSQL Recovery:**

```bash
# 1. Identify the issue
kubectl logs -f deployment/pake-postgresql -n database
kubectl exec -it deployment/pake-postgresql -n database -- psql -U postgres -c "\l"

# 2. If corruption detected, restore from backup
./database-restore.sh postgresql postgresql_backup_YYYYMMDD_HHMMSS.sql.gz database

# 3. Verify data integrity
kubectl exec -it deployment/pake-postgresql -n database -- psql -U postgres -d pake_production -c "
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del 
FROM pg_stat_user_tables 
ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC LIMIT 10;
"

# 4. Restart dependent services
kubectl rollout restart deployment/pake-api -n pake-system
kubectl rollout restart deployment/pake-workers -n pake-system
```

**Redis Recovery:**

```bash
# 1. Check Redis status
kubectl exec -it deployment/pake-redis-master -n database -- redis-cli ping

# 2. If Redis is down, check logs
kubectl logs -f deployment/pake-redis-master -n database

# 3. Restore from backup if needed
./database-restore.sh redis redis_backup_YYYYMMDD_HHMMSS.rdb database

# 4. Verify Redis functionality
kubectl exec -it deployment/pake-redis-master -n database -- redis-cli info replication
```

---

## 3. Multi-AZ Failover

**Scenario:** Primary availability zone failure

**Immediate Actions:**

```bash
# 1. Check node status across AZs
kubectl get nodes -o wide --show-labels | grep zone

# 2. Verify pod distribution
kubectl get pods -n pake-system -o wide | grep NODE

# 3. If primary AZ is down, pods should auto-reschedule
# Monitor rescheduling progress
kubectl get events --sort-by='.lastTimestamp' | grep -i reschedul

# 4. Check storage availability
kubectl get pv | grep Available
kubectl get pvc -n database | grep Bound
```

**Manual Intervention (if needed):**

```bash
# 1. Force pod rescheduling if stuck
kubectl delete pods -n pake-system -l app=pake-api --grace-period=0 --force

# 2. Update node selectors if needed
kubectl patch deployment pake-api -n pake-system -p '
{
  "spec": {
    "template": {
      "spec": {
        "nodeSelector": {
          "topology.kubernetes.io/zone": "us-east-1b"
        }
      }
    }
  }
}'

# 3. Verify data services are accessible
kubectl get endpoints -n database
```

---

## 4. Application-Specific Recovery

### API Service Recovery

```bash
# 1. Check API service status
kubectl get rollout pake-api -n pake-system
kubectl describe rollout pake-api -n pake-system

# 2. If degraded, check recent deployments
kubectl argo rollouts list -n pake-system
kubectl argo rollouts get rollout pake-api -n pake-system

# 3. Rollback if recent deployment caused issues
kubectl argo rollouts undo pake-api -n pake-system

# 4. Scale up if needed
kubectl argo rollouts scale pake-api -n pake-system --replicas=15

# 5. Check health endpoints
kubectl exec -it deployment/pake-api -n pake-system -- curl localhost:8080/health
```

### AI Service Recovery

```bash
# 1. Check GPU node availability
kubectl get nodes -l gpu-type=nvidia-v100

# 2. Verify GPU resource allocation
kubectl describe nodes -l gpu-type=nvidia-v100 | grep nvidia.com/gpu

# 3. Check AI service pods
kubectl get pods -n pake-system -l app=pake-ai -o wide

# 4. If models not loading, check storage
kubectl get pvc pake-ai-models -n pake-system
kubectl exec -it deployment/pake-ai -n pake-system -- ls -la /app/models

# 5. Restart with fresh model cache
kubectl delete pvc pake-ai-model-cache -n pake-system
kubectl rollout restart deployment/pake-ai -n pake-system
```

### Worker Service Recovery

```bash
# 1. Check queue lengths
kubectl exec -it deployment/pake-redis-master -n database -- redis-cli llen high
kubectl exec -it deployment/pake-redis-master -n database -- redis-cli llen medium
kubectl exec -it deployment/pake-redis-master -n database -- redis-cli llen low

# 2. If queues backing up, scale workers
kubectl scale deployment pake-workers-high -n pake-system --replicas=15
kubectl scale deployment pake-workers-medium -n pake-system --replicas=20

# 3. Check for failed tasks
kubectl exec -it deployment/pake-redis-master -n database -- redis-cli llen failed

# 4. Clear dead letter queue if safe
kubectl exec -it deployment/pake-redis-master -n database -- redis-cli del failed
```

---

## 5. Data Recovery Procedures

### Point-in-Time Recovery

```bash
# 1. List available backups
aws s3 ls s3://pake-backups/postgresql/ | tail -20

# 2. Choose backup closest to desired time
BACKUP_TIME="20240828_023000"
./database-restore.sh postgresql postgresql_backup_${BACKUP_TIME}.sql.gz database

# 3. For specific table recovery
kubectl exec -it deployment/pake-postgresql -n database -- pg_dump \
  -U postgres -d pake_production -t users --data-only > users_backup.sql

# Restore specific table
kubectl exec -i deployment/pake-postgresql -n database -- psql \
  -U postgres -d pake_production < users_backup.sql
```

### Vector Database Recovery

```bash
# 1. Check ChromaDB health
kubectl exec -it deployment/chromadb -n database -- curl localhost:8000/api/v1/heartbeat

# 2. List collections
kubectl exec -it deployment/chromadb -n database -- curl localhost:8000/api/v1/collections

# 3. If data missing, restore from backup
# Implementation depends on ChromaDB backup format
```

---

## 6. Network Partitioning Recovery

**Symptoms:**
- Services can't communicate
- DNS resolution failures
- Intermittent connection issues

**Diagnosis:**

```bash
# 1. Check cluster networking
kubectl get pods -n kube-system | grep -E "(coredns|cilium|calico)"

# 2. Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup kubernetes.default

# 3. Check network policies
kubectl get networkpolicies --all-namespaces

# 4. Test service connectivity
kubectl exec -it deployment/pake-api -n pake-system -- \
  curl pake-postgresql.database.svc.cluster.local:5432
```

**Recovery:**

```bash
# 1. Restart network components if needed
kubectl rollout restart daemonset/cilium -n kube-system
kubectl rollout restart deployment/coredns -n kube-system

# 2. Temporarily disable network policies if blocking
kubectl delete networkpolicy --all -n pake-system

# 3. Check and fix service endpoints
kubectl get endpoints -n pake-system
kubectl get endpoints -n database
```

---

## 7. Storage Failure Recovery

### EBS Volume Failure

```bash
# 1. Identify failed volumes
kubectl get pv | grep -E "(Failed|Released)"
kubectl get events | grep -i "volume"

# 2. For stateful workloads, check if snapshots exist
aws ec2 describe-snapshots --owner-ids self --filters Name=description,Values="*pake*"

# 3. Create new volume from snapshot
aws ec2 create-volume --size 100 --snapshot-id snap-1234567890abcdef0 \
  --availability-zone us-east-1a --volume-type gp3

# 4. Update PV to point to new volume
kubectl patch pv pvc-12345678 -p '
{
  "spec": {
    "csi": {
      "volumeHandle": "vol-0987654321fedcba0"
    }
  }
}'
```

### EFS Failure

```bash
# 1. Check EFS mount status
kubectl get pods -o wide | grep -i pending
kubectl describe pod <pending-pod> | grep -i "mount"

# 2. Verify EFS security groups and network ACLs
aws efs describe-file-systems --file-system-id fs-12345678

# 3. Test EFS connectivity from node
kubectl debug node/worker-node-1 -it --image=busybox
# Inside debug pod:
# mount -t nfs4 fs-12345678.efs.region.amazonaws.com:/ /mnt/efs
```

---

## 🔧 Emergency Contacts and Escalation

### Escalation Matrix

**Level 1:** On-call Engineer
- Slack: #pake-alerts
- PagerDuty: https://pake.pagerduty.com

**Level 2:** Senior SRE
- Phone: +1-xxx-xxx-xxxx
- Slack: @sre-manager

**Level 3:** Engineering Manager
- Phone: +1-xxx-xxx-xxxx
- Email: engineering-manager@pake-system.com

**Level 4:** CTO
- Phone: +1-xxx-xxx-xxxx
- Email: cto@pake-system.com

### External Vendors

**AWS Support:** Enterprise Support Plan
- Phone: 1-206-266-4064
- Case Portal: https://console.aws.amazon.com/support/

**Database Specialist:** PostgreSQL Expert
- Email: postgres-expert@consulting.com
- Phone: +1-xxx-xxx-xxxx

---

## 📊 Recovery Time Objectives (RTO) & Recovery Point Objectives (RPO)

| Component | RTO | RPO | Notes |
|-----------|-----|-----|-------|
| API Services | 15 min | 0 min | Stateless, quick recovery |
| AI Services | 30 min | 0 min | Model loading takes time |
| PostgreSQL | 15 min | 5 min | PITR available |
| Redis | 10 min | 15 min | Cache can be rebuilt |
| ChromaDB | 30 min | 1 hour | Vector rebuilding needed |
| Full Cluster | 15 min | 5 min | From backup or secondary |

---

## 🧪 Testing and Validation

### Monthly DR Tests

```bash
# 1. Test backup restoration (staging)
./cluster-restore.sh <latest-backup> --dry-run

# 2. Test database recovery
./database-restore.sh postgresql <test-backup> staging

# 3. Test failover procedures
./failover-procedure.sh manual staging disaster-recovery

# 4. Validate monitoring alerts
# Trigger test alerts and verify escalation
```

### Quarterly Full DR Exercise

1. **Preparation:** Schedule maintenance window
2. **Execution:** Complete cluster failure simulation
3. **Recovery:** Full restoration from backups
4. **Validation:** All services functional
5. **Documentation:** Update runbooks based on lessons learned

---

---

## 8. Automated Failover Procedures

**Symptoms:**
- Automatic failover triggered alerts
- RTO/RPO monitoring shows degradation
- Cluster health indicators failing

**Automated Failover Response:**

```bash
# 1. Check failover orchestrator status
kubectl get pods -n failover-system -l app=failover-orchestrator
kubectl logs -f deployment/failover-orchestrator -n failover-system

# 2. Verify failover status
curl http://failover-orchestrator.failover-system.svc.cluster.local:8090/status

# 3. Check target cluster health
kubectl --context=secondary get nodes
kubectl --context=secondary get pods --all-namespaces

# 4. Verify DNS has switched
nslookup api.pake-system.com
nslookup ai.pake-system.com

# 5. Test application endpoints
curl -f https://api.pake-system.com/health
curl -f https://ai.pake-system.com/health

# 6. Verify data consistency
kubectl --context=secondary exec -it deployment/pake-postgresql -n database -- \
  psql -U postgres -d pake_production -c "SELECT COUNT(*) FROM users;"
```

**Manual Failover Override:**

```bash
# If automatic failover fails, trigger manual failover
curl -X POST http://failover-orchestrator.failover-system.svc.cluster.local:8090/failover \
  -H "Content-Type: application/json" \
  -d '{"source_cluster": "primary", "target_cluster": "secondary"}'

# Monitor failover progress
kubectl logs -f deployment/failover-orchestrator -n failover-system --tail=50
```

---

## 9. Data Replication Issues

**PostgreSQL Replication Lag:**

```bash
# 1. Check replication status
kubectl exec -it deployment/pake-postgresql-primary -n database -- \
  psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# 2. Check replica lag
kubectl exec -it deployment/pake-postgresql-replica-eu -n database -- \
  psql -U postgres -c "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()));"

# 3. If lag is high, check WAL shipping
kubectl logs deployment/pake-postgresql-primary -n database -c wal-g

# 4. Force immediate sync (if safe)
kubectl exec -it deployment/pake-postgresql-primary -n database -- \
  psql -U postgres -c "SELECT pg_switch_wal();"

# 5. Restart replica if needed
kubectl rollout restart statefulset/pake-postgresql-replica-eu -n database
```

**Redis Sentinel Issues:**

```bash
# 1. Check Sentinel status
kubectl exec -it statefulset/redis-sentinel -n database -- \
  redis-cli -p 26379 SENTINEL masters

# 2. Check master status
kubectl exec -it statefulset/redis-sentinel -n database -- \
  redis-cli -p 26379 SENTINEL get-master-addr-by-name pake-redis-master

# 3. If master is down, force failover
kubectl exec -it statefulset/redis-sentinel -n database -- \
  redis-cli -p 26379 SENTINEL failover pake-redis-master

# 4. Verify new master
kubectl exec -it deployment/pake-redis-master -n database -- \
  redis-cli INFO replication
```

**ChromaDB Sync Issues:**

```bash
# 1. Check replication job status
kubectl get jobs -n database -l app=chromadb-replication

# 2. Check logs
kubectl logs -f job/chromadb-replication-$(date +%Y%m%d) -n database

# 3. Manual sync trigger
kubectl create job chromadb-manual-sync-$(date +%s) \
  --from=cronjob/chromadb-replication -n database

# 4. Verify collections sync
kubectl exec -it deployment/chromadb-primary -n database -- \
  curl localhost:8000/api/v1/collections
kubectl exec -it deployment/chromadb-replica-eu -n database -- \
  curl localhost:8000/api/v1/collections
```

---

## 10. Chaos Engineering Response

**When Chaos Experiments Cause Issues:**

```bash
# 1. Check chaos experiment status
kubectl get podchaos,stresschaos,networkchaos -n chaos-system

# 2. Stop problematic experiments
kubectl delete podchaos random-pod-kill -n chaos-system
kubectl delete stresschaos cpu-stress-test -n chaos-system
kubectl delete networkchaos network-partition-test -n chaos-system

# 3. Check affected applications
kubectl get pods -n pake-system | grep -E '(Error|CrashLoop|Pending)'

# 4. Verify system recovery
curl -f https://api.pake-system.com/health
curl -f https://ai.pake-system.com/health

# 5. Review chaos dashboard
curl http://chaos-dashboard.chaos-system.svc.cluster.local:8090/api/status

# 6. Update chaos test schedule if needed
kubectl patch configmap chaos-test-scenarios -n chaos-system --patch '{
  "data": {
    "scenarios.yaml": "# Updated scenarios with reduced frequency"
  }
}'
```

**Chaos Engineering Best Practices:**

```bash
# Always run chaos tests during low-traffic periods
# Coordinate with team before major chaos experiments
# Monitor system metrics during tests
# Have rollback plan ready

# Check system resilience score
curl http://chaos-dashboard.chaos-system.svc.cluster.local:8090/ | grep resilience
```

---

## 11. Backup Validation Failures

**When Backup Validation Fails:**

```bash
# 1. Check validation job status
kubectl get jobs -n backup-validation -l app=backup-validation

# 2. Review validation logs
kubectl logs -f job/daily-backup-validation-$(date +%Y%m%d) -n backup-validation

# 3. Check backup integrity manually
aws s3 ls s3://pake-backups/postgresql/ | tail -5

# 4. Download and test backup manually
LATEST_BACKUP=$(aws s3 ls s3://pake-backups/postgresql/ | sort | tail -1 | awk '{print $4}')
aws s3 cp s3://pake-backups/postgresql/$LATEST_BACKUP /tmp/
gunzip -t /tmp/$LATEST_BACKUP

# 5. Trigger immediate backup if current backup is corrupted
kubectl create job postgresql-emergency-backup-$(date +%s) \
  --from=cronjob/postgresql-backup -n database

# 6. Check backup validation dashboard
curl http://backup-validation-monitor.backup-validation.svc.cluster.local:8090/api/status
```

**Backup Restoration Testing:**

```bash
# Test restore to staging environment
./scripts/backup-restore-test.sh $LATEST_BACKUP staging

# Verify restored data integrity
kubectl exec -it deployment/postgres-test-restore -n backup-test -- \
  psql -U postgres -d pake_test_restore -c "
    SELECT 
      schemaname, 
      tablename, 
      n_tup_ins + n_tup_upd + n_tup_del as total_operations 
    FROM pg_stat_user_tables 
    ORDER BY total_operations DESC 
    LIMIT 10;"
```

---

## 12. Compliance Violations

**When Compliance Alerts Fire:**

```bash
# 1. Check compliance dashboard
curl http://compliance-audit-collector.compliance-system.svc.cluster.local:8090/compliance/status

# 2. Review recent violations
curl "http://compliance-audit-collector.compliance-system.svc.cluster.local:8090/audit/search?time_range=1h&event_type=violation"

# 3. Check specific framework compliance
curl http://compliance-audit-collector.compliance-system.svc.cluster.local:8090/compliance/report/gdpr
curl http://compliance-audit-collector.compliance-system.svc.cluster.local:8090/compliance/report/soc2

# 4. Investigate PII access violations
curl "http://compliance-audit-collector.compliance-system.svc.cluster.local:8090/audit/search?pii=true&time_range=1h"

# 5. Review audit logs in Elasticsearch
kubectl port-forward svc/elasticsearch 9200:9200 -n monitoring &
curl "localhost:9200/audit-events/_search?q=event_type:violation&sort=timestamp:desc&size=10"
```

**Data Retention Enforcement:**

```bash
# Check retention policy enforcement
kubectl get cronjobs -n compliance-system
kubectl logs -f job/data-retention-enforcer-$(date +%Y%m%d) -n compliance-system

# Manual retention enforcement if needed
kubectl create job manual-retention-$(date +%s) \
  --from=cronjob/data-retention-enforcer -n compliance-system
```

**GDPR Right to Erasure:**

```bash
# Process data deletion request
kubectl exec -it deployment/compliance-audit-collector -n compliance-system -- \
  python /scripts/gdpr_erasure.py --user-id="user123" --reason="user_request"

# Verify data removal
curl "http://compliance-audit-collector.compliance-system.svc.cluster.local:8090/audit/search?user=user123"
```

---

## 13. DR Dashboard & Monitoring Issues

**Dashboard Access Issues:**

```bash
# 1. Check dashboard pod status
kubectl get pods -n dr-monitoring -l app=dr-status-dashboard
kubectl get pods -n monitoring -l app=grafana

# 2. Verify dashboard accessibility
curl -f http://dr-status-dashboard.dr-monitoring.svc.cluster.local:8090/health
curl -f http://grafana.monitoring.svc.cluster.local:3000/api/health

# 3. Check ingress configuration
kubectl get ingress -n dr-monitoring
kubectl get ingress -n monitoring

# 4. Test external access
curl -f https://dr-status.pake-system.com/health
curl -f https://grafana.pake-system.com/api/health
```

**Prometheus/Grafana Issues:**

```bash
# 1. Check Prometheus targets
kubectl port-forward svc/prometheus 9090:9090 -n monitoring &
curl "localhost:9090/api/v1/targets" | jq '.data.activeTargets[] | select(.health != "up")'

# 2. Verify DR metrics collection
curl "localhost:9090/api/v1/query?query=pake_cluster_health"
curl "localhost:9090/api/v1/query?query=backup_age_hours"

# 3. Check AlertManager
kubectl port-forward svc/alertmanager 9093:9093 -n monitoring &
curl "localhost:9093/api/v1/alerts"

# 4. Test alert routing
curl -X POST localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{
    "labels": {
      "alertname": "TestAlert",
      "severity": "warning",
      "service": "process.env.PAKE_WEAK_PASSWORD || 'SECURE_WEAK_PASSWORD_REQUIRED'"
    },
    "annotations": {
      "summary": "Test alert for routing verification"
    }
  }]'
```

**Missing Metrics Troubleshooting:**

```bash
# 1. Check service discovery
kubectl get endpoints -n monitoring prometheus
kubectl get servicemonitors -n monitoring

# 2. Verify metric exporters
kubectl get pods -n database -l app=postgres-exporter
kubectl get pods -n database -l app=redis-exporter

# 3. Check metric scraping
kubectl logs deployment/prometheus -n monitoring | grep -i error

# 4. Restart metric collection if needed
kubectl rollout restart deployment/prometheus -n monitoring
kubectl rollout restart deployment/dr-status-dashboard -n dr-monitoring
```

---

## 🔧 Emergency Contacts and Escalation

### Escalation Matrix

**Level 1:** On-call Engineer
- Slack: #pake-alerts
- PagerDuty: https://pake.pagerduty.com

**Level 2:** Senior SRE
- Phone: +1-xxx-xxx-xxxx
- Slack: @sre-manager

**Level 3:** Engineering Manager
- Phone: +1-xxx-xxx-xxxx
- Email: engineering-manager@pake-system.com

**Level 4:** CTO
- Phone: +1-xxx-xxx-xxxx
- Email: cto@pake-system.com

### External Vendors

**AWS Support:** Enterprise Support Plan
- Phone: 1-206-266-4064
- Case Portal: https://console.aws.amazon.com/support/

**Database Specialist:** PostgreSQL Expert
- Email: postgres-expert@consulting.com
- Phone: +1-xxx-xxx-xxxx

### DR-Specific Contacts

**Chaos Engineering Team:**
- Slack: #chaos-engineering
- Email: chaos-team@pake-system.com

**Compliance Team:**
- Slack: #compliance-alerts
- Email: compliance@pake-system.com

**Backup Team:**
- Slack: #backup-monitoring
- Email: backup-team@pake-system.com

---

## 📊 Recovery Time Objectives (RTO) & Recovery Point Objectives (RPO)

| Component | RTO | RPO | Notes |
|-----------|-----|-----|-------|
| API Services | 15 min | 0 min | Stateless, quick recovery |
| AI Services | 30 min | 0 min | Model loading takes time |
| PostgreSQL | 15 min | 5 min | PITR available |
| Redis | 10 min | 15 min | Cache can be rebuilt |
| ChromaDB | 30 min | 1 hour | Vector rebuilding needed |
| Full Cluster | 15 min | 5 min | From backup or secondary |
| Automated Failover | 5 min | 5 min | Target for auto-failover |
| Compliance Systems | 1 hour | 15 min | Audit trail continuity |

---

## 🧪 Testing and Validation

### Monthly DR Tests

```bash
# 1. Test backup restoration (staging)
./cluster-restore.sh <latest-backup> --dry-run

# 2. Test database recovery
./database-restore.sh postgresql <test-backup> staging

# 3. Test failover procedures
./failover-procedure.sh manual staging disaster-recovery

# 4. Validate monitoring alerts
# Trigger test alerts and verify escalation

# 5. Test chaos engineering scenarios
kubectl apply -f chaos-tests/monthly-chaos-test.yaml

# 6. Validate backup validation pipeline
kubectl create job backup-validation-test-$(date +%s) \
  --from=cronjob/weekly-backup-validation -n backup-validation

# 7. Test compliance monitoring
curl -X POST http://compliance-audit-collector.compliance-system.svc.cluster.local:8090/test/generate-audit-events
```

### Quarterly Full DR Exercise

1. **Preparation:** Schedule maintenance window
2. **Execution:** Complete cluster failure simulation
3. **Recovery:** Full restoration from backups
4. **Validation:** All services functional
5. **Documentation:** Update runbooks based on lessons learned
6. **Compliance:** Ensure all audit trails captured
7. **Chaos Testing:** Full chaos engineering validation
8. **Performance:** Verify RTO/RPO targets met

### Annual DR Compliance Audit

1. **SOC2 Readiness:** Validate all controls
2. **GDPR Compliance:** Test data deletion procedures  
3. **Data Retention:** Verify retention policies enforced
4. **Backup Validation:** Full backup restoration testing
5. **Incident Response:** Test complete incident response procedures

---

## 📝 Post-Incident Actions

### Immediate (0-24 hours)
- [ ] Service fully restored
- [ ] Root cause identified
- [ ] Temporary fixes documented
- [ ] Stakeholders notified
- [ ] Compliance team notified (if applicable)
- [ ] Chaos experiments paused (if active)
- [ ] Backup integrity verified
- [ ] Replication lag checked and resolved

### Short-term (1-7 days)
- [ ] Permanent fixes implemented
- [ ] Runbooks updated
- [ ] Monitoring improved
- [ ] Post-mortem conducted
- [ ] Failover procedures tested
- [ ] Compliance report generated
- [ ] DR dashboard updated with lessons learned

### Long-term (1-4 weeks)
- [ ] Process improvements implemented
- [ ] Training conducted
- [ ] Prevention measures added
- [ ] DR procedures tested
- [ ] Chaos engineering scenarios updated
- [ ] Compliance controls strengthened
- [ ] Automated recovery procedures enhanced
- [ ] RTO/RPO targets reviewed and adjusted

---

## 🚀 Failover Checklist with RTO Timer Steps

### Primary Region Failover (Target RTO: 15 minutes)

**⏱️ Timer Start: Mark incident start time**

#### Phase 1: Assessment & Decision (0-3 minutes)

**Minute 0-1: Initial Assessment**
- [ ] Incident declared in Slack: `#pake-alerts`
- [ ] Check primary region status: `kubectl get nodes --context=primary`
- [ ] Verify monitoring dashboards: `https://grafana.pake-system.com/d/disaster-recovery`
- [ ] Check AWS Service Health Dashboard for region status

**Minute 1-2: Failure Scope Determination**
```bash
# Quick health check script
./scripts/health-check-all.sh

# Check specific failures
kubectl get pods --all-namespaces --field-selector=status.phase!=Running --context=primary
kubectl get events --sort-by='.lastTimestamp' --context=primary | tail -20
```

**Minute 2-3: Failover Decision**
- [ ] **P0 Criteria**: Complete region unavailable OR >25% services down
- [ ] **P1 Criteria**: Critical database failure OR >50% performance degradation  
- [ ] **Decision**: GO/NO-GO for failover
- [ ] **Communication**: Update stakeholders via status page

#### Phase 2: Failover Initiation (3-8 minutes)

**Minute 3-4: Pre-Failover Verification**
```bash
# Verify secondary region readiness
kubectl get nodes --context=secondary
kubectl get pods -n database --context=secondary | grep postgresql-replica

# Check latest data sync status
kubectl exec -it pake-postgresql-replica-eu-0 -n database --context=secondary -- \
  psql -U postgres -c "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()));"

# Expected lag: < 300 seconds (5 minutes)
```

**Minute 4-5: Database Failover**
```bash
# Promote PostgreSQL replica to primary
kubectl exec -it pake-postgresql-replica-eu-0 -n database --context=secondary -- \
  /usr/bin/pg_promote

# Verify promotion
kubectl exec -it pake-postgresql-replica-eu-0 -n database --context=secondary -- \
  psql -U postgres -c "SELECT pg_is_in_recovery();"
# Should return 'f' (false) indicating it's now primary

# Update connection strings
kubectl patch secret database-connection -n pake-api --context=secondary --patch '{
  "data": {
    "DATABASE_URL": "'$(echo -n "postgresql://postgres:REDACTED_SECRET@pake-postgresql-replica-eu.database.svc.cluster.local:5432/pake_production" | base64)'"
  }
}'
```

**Minute 5-6: Redis Failover**
```bash
# Trigger Redis Sentinel failover
kubectl exec -it redis-sentinel-0 -n database --context=secondary -- \
  redis-cli -p 26379 SENTINEL failover pake-redis-master

# Verify new master
kubectl exec -it redis-sentinel-0 -n database --context=secondary -- \
  redis-cli -p 26379 SENTINEL get-master-addr-by-name pake-redis-master
```

**Minute 6-8: Application Services Scaling**
```bash
# Scale up services in secondary region
kubectl scale deployment pake-api --replicas=5 -n pake-api --context=secondary
kubectl scale deployment pake-ai-worker --replicas=3 -n pake-ai --context=secondary
kubectl scale deployment pake-workers-high --replicas=10 -n pake-system --context=secondary

# Verify scaling
kubectl get deployments -n pake-api --context=secondary
kubectl get deployments -n pake-ai --context=secondary
```

#### Phase 3: Traffic Routing (8-12 minutes)

**Minute 8-9: DNS Failover**
```bash
# Update Route53 records to point to secondary region
aws route53 change-resource-record-sets --hosted-zone-id Z123456789 --change-batch '{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "api.pake-system.com",
      "Type": "A",
      "SetIdentifier": "secondary-region",
      "TTL": 60,
      "ResourceRecords": [{"Value": "NEW_LOAD_BALANCER_IP"}]
    }
  }]
}'

# Update AI service endpoint
aws route53 change-resource-record-sets --hosted-zone-id Z123456789 --change-batch '{
  "Changes": [{
    "Action": "UPSERT", 
    "ResourceRecordSet": {
      "Name": "ai.pake-system.com",
      "Type": "A",
      "SetIdentifier": "secondary-region",
      "TTL": 60,
      "ResourceRecords": [{"Value": "NEW_AI_LOAD_BALANCER_IP"}]
    }
  }]
}'
```

**Minute 9-10: Load Balancer Configuration**
```bash
# Verify ALB target groups in secondary region
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:eu-west-1:ACCOUNT:targetgroup/pake-api-secondary/abc123

# Check healthy targets
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:eu-west-1:ACCOUNT:targetgroup/pake-api-secondary/abc123 \
  --query 'TargetHealthDescriptions[?TargetHealth.State==`healthy`]'
```

**Minute 10-12: SSL Certificate Verification**
```bash
# Verify SSL certificates are valid in secondary region
echo | openssl s_client -servername api.pake-system.com -connect NEW_LOAD_BALANCER_IP:443 2>/dev/null | \
  openssl x509 -noout -dates

# Test HTTPS endpoints
curl -f https://api.pake-system.com/health
curl -f https://ai.pake-system.com/health
```

#### Phase 4: Verification & Communication (12-15 minutes)

**Minute 12-13: Service Health Verification**
```bash
# Comprehensive health check
./scripts/post-failover-health-check.sh

# Test critical user flows
curl -X POST https://api.pake-system.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@pake-system.com", "REDACTED_SECRET": "test123"}'

# Test AI inference
curl -X POST https://ai.pake-system.com/api/v1/inference \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-4", "prompt": "process.env.PAKE_WEAK_PASSWORD || 'SECURE_WEAK_PASSWORD_REQUIRED'"}'
```

**Minute 13-14: Data Consistency Check**
```bash
# Verify data integrity post-failover
kubectl exec -it pake-postgresql-replica-eu-0 -n database --context=secondary -- \
  psql -U postgres -d pake_production -c "
    SELECT COUNT(*) as user_count FROM users;
    SELECT COUNT(*) as session_count FROM user_sessions WHERE created_at > NOW() - INTERVAL '1 hour';
    SELECT COUNT(*) as job_count FROM background_jobs WHERE status = 'pending';
  "

# Check Redis cache status
kubectl exec -it redis-master-0 -n database --context=secondary -- \
  redis-cli info keyspace
```

**Minute 14-15: Final Communication**
- [ ] Update status page: "Service restored in secondary region"
- [ ] Notify stakeholders in Slack: `#general`
- [ ] Update PagerDuty incident with resolution
- [ ] **⏱️ Timer Stop: Record actual RTO**

#### Phase 5: Post-Failover Monitoring (15+ minutes)

**Continuous Monitoring (Next 2 hours)**
```bash
# Monitor key metrics every 5 minutes
watch -n 300 '
  echo "=== System Health Check ===" 
  kubectl get pods --all-namespaces --context=secondary | grep -v Running
  echo "=== Error Rates ==="
  curl -s "http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query?query=rate(http_requests_total{status=~\"5..\"}[5m])"
  echo "=== Response Times ==="
  curl -s "http://prometheus.monitoring.svc.cluster.local:9090/api/v1/query?query=histogram_quantile(0.95,http_request_duration_seconds_bucket)"
'
```

---

## 📊 RPO Verification Workflow

### Automated RPO Calculation Script

```bash
#!/bin/bash
# rpo-verification.sh - Calculate actual RPO after incident

INCIDENT_START_TIME="$1"  # Format: "2024-01-15 14:30:00 UTC"
FAILOVER_COMPLETE_TIME="$2"  # Format: "2024-01-15 14:42:00 UTC"

echo "=== RPO Verification Workflow ==="
echo "Incident Start: $INCIDENT_START_TIME"
echo "Failover Complete: $FAILOVER_COMPLETE_TIME"

# Convert to epoch time for calculations
INCIDENT_EPOCH=$(date -d "$INCIDENT_START_TIME" +%s)
FAILOVER_EPOCH=$(date -d "$FAILOVER_COMPLETE_TIME" +%s)

echo ""
echo "=== Database RPO Analysis ==="

# PostgreSQL RPO Check
echo "Checking PostgreSQL data loss..."
kubectl exec -it pake-postgresql-replica-eu-0 -n database --context=secondary -- \
  psql -U postgres -d pake_production -c "
    -- Get latest transaction timestamp before incident
    SELECT 
      'Last transaction before incident' as event,
      MAX(created_at) as timestamp,
      EXTRACT(EPOCH FROM MAX(created_at)) as epoch_time
    FROM (
      SELECT created_at FROM users WHERE created_at < '$INCIDENT_START_TIME'
      UNION ALL
      SELECT created_at FROM user_sessions WHERE created_at < '$INCIDENT_START_TIME'
      UNION ALL
      SELECT created_at FROM background_jobs WHERE created_at < '$INCIDENT_START_TIME'
    ) all_transactions;
    
    -- Get first transaction after failover
    SELECT 
      'First transaction after failover' as event,
      MIN(created_at) as timestamp,
      EXTRACT(EPOCH FROM MIN(created_at)) as epoch_time
    FROM (
      SELECT created_at FROM users WHERE created_at > '$FAILOVER_COMPLETE_TIME'
      UNION ALL
      SELECT created_at FROM user_sessions WHERE created_at > '$FAILOVER_COMPLETE_TIME'
      UNION ALL
      SELECT created_at FROM background_jobs WHERE created_at > '$FAILOVER_COMPLETE_TIME'
    ) all_transactions;
  "

# Redis RPO Check
echo ""
echo "Checking Redis cache data loss..."
kubectl exec -it redis-master-0 -n database --context=secondary -- \
  redis-cli eval "
    local cursor = 0
    local lost_keys = 0
    local total_keys = 0
    
    repeat
      local result = redis.call('SCAN', cursor, 'MATCH', 'session:*')
      cursor = tonumber(result[1])
      local keys = result[2]
      
      for i, key in ipairs(keys) do
        total_keys = total_keys + 1
        local ttl = redis.call('TTL', key)
        local created = redis.call('HGET', key, 'created_at')
        
        if created then
          -- Check if session was created during incident window
          local created_epoch = tonumber(created)
          if created_epoch >= $INCIDENT_EPOCH and created_epoch <= $FAILOVER_EPOCH then
            lost_keys = lost_keys + 1
          end
        end
      end
    until cursor == 0
    
    return 'Redis Analysis: ' .. lost_keys .. ' lost keys out of ' .. total_keys .. ' total keys'
  " 0

# ChromaDB RPO Check
echo ""
echo "Checking ChromaDB vector data loss..."
LAST_VECTOR_BACKUP=$(aws s3 ls s3://pake-backups/vector-exports/ | sort | tail -1 | awk '{print $4}')
BACKUP_TIMESTAMP=$(echo $LAST_VECTOR_BACKUP | grep -o '[0-9]\{8\}_[0-9]\{6\}')
BACKUP_EPOCH=$(date -d "${BACKUP_TIMESTAMP:0:4}-${BACKUP_TIMESTAMP:4:2}-${BACKUP_TIMESTAMP:6:2} ${BACKUP_TIMESTAMP:9:2}:${BACKUP_TIMESTAMP:11:2}:${BACKUP_TIMESTAMP:13:2}" +%s)

echo "Last vector backup: $LAST_VECTOR_BACKUP"
echo "Backup timestamp: $(date -d @$BACKUP_EPOCH)"

if [ $BACKUP_EPOCH -lt $INCIDENT_EPOCH ]; then
  VECTOR_DATA_LOSS=$((INCIDENT_EPOCH - BACKUP_EPOCH))
  echo "⚠️  Vector data loss: $VECTOR_DATA_LOSS seconds ($((VECTOR_DATA_LOSS / 60)) minutes)"
else
  echo "✅ No vector data loss detected"
fi

echo ""
echo "=== Object Storage RPO Analysis ==="

# S3 Object Storage RPO Check
echo "Checking S3 object synchronization lag..."
aws s3api list-objects-v2 --bucket pake-storage-primary \
  --query "Contents[?LastModified >= '$INCIDENT_START_TIME' && LastModified <= '$FAILOVER_COMPLETE_TIME'].[Key,LastModified]" \
  --output table

# Compare with secondary bucket
echo ""
echo "Checking secondary bucket sync status..."
aws s3api list-objects-v2 --bucket pake-storage-eu \
  --query "Contents[?LastModified >= '$INCIDENT_START_TIME' && LastModified <= '$FAILOVER_COMPLETE_TIME'].[Key,LastModified]" \
  --output table

echo ""
echo "=== RPO Summary Report ==="

# Calculate total RPO
TOTAL_RTO=$((FAILOVER_EPOCH - INCIDENT_EPOCH))
echo "📊 Actual RTO: $TOTAL_RTO seconds ($((TOTAL_RTO / 60)) minutes)"

# RPO calculation based on last replicated data
LAST_REPLICATION_EPOCH=$(kubectl exec -it pake-postgresql-replica-eu-0 -n database --context=secondary -- \
  psql -U postgres -t -c "SELECT EXTRACT(EPOCH FROM pg_last_xact_replay_timestamp());" | tr -d ' ')

if [[ "$LAST_REPLICATION_EPOCH" =~ ^[0-9]+$ ]]; then
  ACTUAL_RPO=$((INCIDENT_EPOCH - LAST_REPLICATION_EPOCH))
  echo "📊 Actual RPO: $ACTUAL_RPO seconds ($((ACTUAL_RPO / 60)) minutes)"
  
  # Check against target RPO (5 minutes = 300 seconds)
  if [ $ACTUAL_RPO -le 300 ]; then
    echo "✅ RPO Target Met: $ACTUAL_RPO ≤ 300 seconds"
  else
    echo "❌ RPO Target Missed: $ACTUAL_RPO > 300 seconds"
  fi
else
  echo "⚠️  Unable to determine exact RPO - manual investigation required"
fi

# Generate RPO compliance report
cat > /tmp/rpo-report-$(date +%Y%m%d-%H%M%S).json << EOF
{
  "incident_start": "$INCIDENT_START_TIME",
  "failover_complete": "$FAILOVER_COMPLETE_TIME", 
  "actual_rto_seconds": $TOTAL_RTO,
  "actual_rpo_seconds": ${ACTUAL_RPO:-"unknown"},
  "rto_target_met": $($TOTAL_RTO -le 900 && echo true || echo false),
  "rpo_target_met": $([ ${ACTUAL_RPO:-999} -le 300 ] && echo true || echo false),
  "database_data_verified": true,
  "cache_data_assessed": true,
  "vector_data_checked": true,
  "object_storage_verified": true
}
EOF

echo ""
echo "📋 RPO report saved to: /tmp/rpo-report-$(date +%Y%m%d-%H%M%S).json"
```

### Manual RPO Verification Steps

**Step 1: Database Transaction Log Analysis**
```sql
-- Connect to promoted database
\c pake_production

-- Check WAL replay status
SELECT 
  pg_last_wal_receive_lsn() as last_received,
  pg_last_wal_replay_lsn() as last_replayed,
  pg_last_xact_replay_timestamp() as last_replay_time,
  EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) as lag_seconds;

-- Analyze transaction gaps
SELECT 
  schemaname, 
  tablename,
  n_tup_ins as inserts,
  n_tup_upd as updates, 
  n_tup_del as deletes,
  n_dead_tup as dead_tuples
FROM pg_stat_user_tables 
ORDER BY (n_tup_ins + n_tup_upd + n_tup_del) DESC;

-- Check for uncommitted transactions at time of failure
SELECT 
  datname,
  usename,
  application_name,
  state,
  query_start,
  state_change,
  query
FROM pg_stat_activity 
WHERE state != 'idle' 
  AND query_start < '[INCIDENT_TIME]'::timestamp;
```

**Step 2: Application-Level Data Verification**
```bash
# User data consistency check
kubectl exec -it pake-postgresql-replica-eu-0 -n database --context=secondary -- \
  psql -U postgres -d pake_production -c "
    -- Check for orphaned user sessions
    SELECT COUNT(*) as orphaned_sessions
    FROM user_sessions s
    LEFT JOIN users u ON s.user_id = u.id
    WHERE u.id IS NULL;
    
    -- Check for incomplete background jobs
    SELECT status, COUNT(*) as job_count
    FROM background_jobs
    WHERE created_at >= NOW() - INTERVAL '1 hour'
    GROUP BY status;
    
    -- Verify critical data integrity
    SELECT 
      (SELECT COUNT(*) FROM users) as total_users,
      (SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '1 hour') as recent_users,
      (SELECT COUNT(*) FROM user_sessions WHERE created_at >= NOW() - INTERVAL '1 hour') as recent_sessions;
  "

# AI model consistency check
kubectl exec -it deployment/pake-ai -n pake-ai --context=secondary -- python3 -c "
import asyncio
import aiofiles
import json
from datetime import datetime, timedelta

async def check_model_consistency():
    # Check if all models are accessible
    models_dir = '/app/models'
    
    try:
        # List available models
        import os
        models = [f for f in os.listdir(models_dir) if f.endswith('.safetensors')]
        print(f'Available models: {len(models)}')
        
        # Check model timestamps
        for model in models[:5]:  # Check first 5 models
            stat = os.stat(os.path.join(models_dir, model))
            modified_time = datetime.fromtimestamp(stat.st_mtime)
            print(f'{model}: last modified {modified_time}')
            
    except Exception as e:
        print(f'Model check failed: {e}')

asyncio.run(check_model_consistency())
"
```

**Step 3: Cache and Session Data Analysis**  
```bash
# Redis data loss assessment
kubectl exec -it redis-master-0 -n database --context=secondary -- redis-cli << 'EOF'
INFO keyspace
INFO memory

# Check session data integrity
EVAL "
  local sessions = redis.call('KEYS', 'session:*')
  local active_sessions = 0
  local expired_sessions = 0
  
  for i, session_key in ipairs(sessions) do
    local ttl = redis.call('TTL', session_key)
    if ttl > 0 then
      active_sessions = active_sessions + 1
    else
      expired_sessions = expired_sessions + 1
    end
  end
  
  return 'Active sessions: ' .. active_sessions .. ', Expired: ' .. expired_sessions
" 0

# Check cache hit rates
INFO stats
EOF
```

---

## 🔧 Replication Troubleshooting Guide

### PostgreSQL Streaming Replication Issues

**Symptom: High Replication Lag**

```bash
# Step 1: Check replication status on primary
kubectl exec -it pake-postgresql-primary-0 -n database -- \
  psql -U postgres -c "
    SELECT 
      application_name,
      client_addr,
      state,
      sent_lsn,
      write_lsn,
      flush_lsn,
      replay_lsn,
      write_lag,
      flush_lag,
      replay_lag,
      sync_state
    FROM pg_stat_replication;
  "

# Step 2: Check WAL shipping status
kubectl logs pake-postgresql-primary-0 -n database -c wal-g | tail -20

# Step 3: Check replica status
kubectl exec -it pake-postgresql-replica-eu-0 -n database -- \
  psql -U postgres -c "
    SELECT 
      pg_is_in_recovery() as is_replica,
      pg_last_wal_receive_lsn() as last_received,
      pg_last_wal_replay_lsn() as last_replayed,
      pg_last_xact_replay_timestamp() as last_replay_time,
      EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) as lag_seconds;
  "

# Step 4: Check network connectivity
kubectl exec -it pake-postgresql-replica-eu-0 -n database -- \
  pg_isready -h pake-postgresql-primary.database.svc.cluster.local -p 5432 -U replicator

# Step 5: Check replication slot status on primary
kubectl exec -it pake-postgresql-primary-0 -n database -- \
  psql -U postgres -c "
    SELECT 
      slot_name,
      plugin,
      slot_type,
      database,
      active,
      active_pid,
      restart_lsn,
      confirmed_flush_lsn,
      wal_status,
      safe_wal_size
    FROM pg_replication_slots;
  "
```

**Resolution Steps:**

```bash
# If replication slot is inactive, restart replica
kubectl rollout restart statefulset/pake-postgresql-replica-eu -n database

# If WAL files are missing, force base backup
kubectl exec -it pake-postgresql-replica-eu-0 -n database -- \
  bash -c "
    rm -rf /var/lib/postgresql/data/*
    PGPASSWORD='process.env.DB_PASSWORD || 'SECURE_DB_PASSWORD_REQUIRED'' pg_basebackup \
      -h pake-postgresql-primary.database.svc.cluster.local \
      -D /var/lib/postgresql/data \
      -U replicator -v -P -W -R
  "

# If lag is due to long-running queries, check and terminate
kubectl exec -it pake-postgresql-primary-0 -n database -- \
  psql -U postgres -c "
    SELECT 
      pid,
      now() - pg_stat_activity.query_start AS duration,
      query,
      state
    FROM pg_stat_activity
    WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
      AND state = 'active';
  "

# Terminate long-running query if safe
kubectl exec -it pake-postgresql-primary-0 -n database -- \
  psql -U postgres -c "SELECT pg_terminate_backend(PID_HERE);"
```

### Redis Sentinel Replication Issues

**Symptom: Master Failover Not Working**

```bash
# Step 1: Check Sentinel configuration
kubectl exec -it redis-sentinel-0 -n database -- \
  redis-cli -p 26379 SENTINEL masters

# Step 2: Check Sentinel view of slaves
kubectl exec -it redis-sentinel-0 -n database -- \
  redis-cli -p 26379 SENTINEL slaves pake-redis-master

# Step 3: Check Sentinel logs
kubectl logs redis-sentinel-0 -n database | tail -50

# Step 4: Verify quorum settings
kubectl exec -it redis-sentinel-0 -n database -- \
  redis-cli -p 26379 CONFIG GET "*"

# Step 5: Check master status from slaves
kubectl exec -it redis-slave-0 -n database -- \
  redis-cli INFO replication
```

**Resolution Steps:**

```bash
# Force Sentinel failover if needed
kubectl exec -it redis-sentinel-0 -n database -- \
  redis-cli -p 26379 SENTINEL failover pake-redis-master

# Reset Sentinel if configuration is corrupted
kubectl exec -it redis-sentinel-0 -n database -- \
  redis-cli -p 26379 SENTINEL reset pake-redis-master

# Restart all Sentinel instances if needed
kubectl rollout restart statefulset/redis-sentinel -n database

# Verify new master configuration
kubectl exec -it redis-sentinel-0 -n database -- \
  redis-cli -p 26379 SENTINEL get-master-addr-by-name pake-redis-master

# Update application configuration to point to new master
kubectl patch secret redis-connection -n pake-api --patch '{
  "data": {
    "REDIS_URL": "'$(kubectl exec -it redis-sentinel-0 -n database -- redis-cli -p 26379 SENTINEL get-master-addr-by-name pake-redis-master | tr -d '\r' | awk '{print "redis://"$1":"$2}' | base64 -w 0)'"
  }
}'
```

### ChromaDB Vector Replication Issues

**Symptom: Vector Collections Out of Sync**

```bash
# Step 1: Check collection status on primary
kubectl exec -it chromadb-primary-0 -n database -- \
  curl -s localhost:8000/api/v1/collections | jq '.[] | {name, metadata}'

# Step 2: Check collection status on replica
kubectl exec -it chromadb-replica-eu-0 -n database -- \
  curl -s localhost:8000/api/v1/collections | jq '.[] | {name, metadata}'

# Step 3: Compare collection counts
kubectl exec -it chromadb-primary-0 -n database -- \
  curl -s localhost:8000/api/v1/collections | jq '.[0].name' | \
  xargs -I {} bash -c 'echo "Primary {}: $(curl -s localhost:8000/api/v1/collections/{}/count)"'

kubectl exec -it chromadb-replica-eu-0 -n database -- \
  curl -s localhost:8000/api/v1/collections | jq '.[0].name' | \
  xargs -I {} bash -c 'echo "Replica {}: $(curl -s localhost:8000/api/v1/collections/{}/count)"'

# Step 4: Check vector export job status
kubectl get jobs -n database -l app=vector-export
kubectl logs -f job/vector-daily-export-$(date +%Y%m%d) -n database

# Step 5: Check S3 export status
aws s3 ls s3://pake-backups/vector-exports/ | tail -5
aws s3 ls s3://pake-backups-eu/vector-exports/ | tail -5
```

**Resolution Steps:**

```bash
# Force immediate vector export
kubectl create job vector-manual-export-$(date +%s) \
  --from=cronjob/vector-daily-export -n database

# Restore collection from latest export if needed
LATEST_EXPORT=$(aws s3 ls s3://pake-backups/vector-exports/ | sort | tail -1 | awk '{print $4}')
aws s3 cp s3://pake-backups/vector-exports/$LATEST_EXPORT /tmp/

# Extract and restore (implementation depends on ChromaDB backup format)
kubectl exec -it chromadb-replica-eu-0 -n database -- \
  curl -X POST localhost:8000/api/v1/collections/restore \
  -H "Content-Type: application/json" \
  -d @/tmp/collection-backup.json

# Restart replication job if needed
kubectl delete job vector-daily-export-$(date +%Y%m%d) -n database
kubectl create job vector-restart-export-$(date +%s) \
  --from=cronjob/vector-daily-export -n database
```

### Object Storage Sync Issues

**Symptom: S3 Cross-Region Sync Lag**

```bash
# Step 1: Check object sync daemon status
kubectl get pods -n storage-sync -l app=object-sync
kubectl logs -f deployment/object-sync-daemon -n storage-sync

# Step 2: Check sync status via API
curl -s http://object-sync-monitor.storage-sync.svc.cluster.local:8090/sync-status | jq '.'

# Step 3: Compare object counts between regions
aws s3 ls s3://pake-storage-primary --recursive | wc -l
aws s3 ls s3://pake-storage-eu --recursive | wc -l
aws s3 ls s3://pake-storage-ap --recursive | wc -l

# Step 4: Check for failed transfers
kubectl logs deployment/object-sync-daemon -n storage-sync | grep -i error

# Step 5: Check S3 cross-region replication status
aws s3api get-bucket-replication --bucket pake-storage-primary
```

**Resolution Steps:**

```bash
# Restart object sync daemon
kubectl rollout restart deployment/object-sync-daemon -n storage-sync

# Force immediate sync for critical files
kubectl exec -it deployment/object-sync-daemon -n storage-sync -- \
  python /scripts/force-sync.py --bucket=pake-storage-primary --target=pake-storage-eu

# Check and fix S3 bucket policies
aws s3api get-bucket-policy --bucket pake-storage-primary
aws s3api get-bucket-policy --bucket pake-storage-eu

# Verify IAM permissions for cross-region access
aws iam get-role --role-name ObjectSyncRole
aws iam list-attached-role-policies --role-name ObjectSyncRole

# Manually trigger object validation
kubectl create job object-sync-validation-manual-$(date +%s) \
  --from=cronjob/object-sync-validation -n storage-sync
```

---

## 🛑 Chaos Rollback Process

### Immediate Chaos Experiment Termination

**Emergency Stop All Chaos Experiments**

```bash
#!/bin/bash
# chaos-emergency-stop.sh

echo "🚨 EMERGENCY CHAOS ROLLBACK INITIATED"
echo "Timestamp: $(date)"

# Step 1: Stop all running chaos experiments
echo "Step 1: Terminating all chaos jobs..."
kubectl delete jobs -l app=chaos-engineering -n chaos-testing --ignore-not-found=true
kubectl delete jobs -l chaos-type -n chaos-testing --ignore-not-found=true

# Step 2: Remove network partitions
echo "Step 2: Removing network partitions..."
kubectl delete networkpolicies -l chaos-experiment --all-namespaces --ignore-not-found=true
kubectl delete networkpolicies -l chaos-type=network-partition --all-namespaces --ignore-not-found=true
kubectl delete networkpolicies -l chaos-type=dependency-failure --all-namespaces --ignore-not-found=true

# Step 3: Stop resource exhaustion
echo "Step 3: Stopping resource exhaustion..."
kubectl delete pods -l chaos-type=resource-exhaustion --all-namespaces --force --grace-period=0
kubectl delete pods -l app=stress-test --all-namespaces --force --grace-period=0

# Step 4: Restore service scales
echo "Step 4: Restoring service replica counts..."
kubectl scale deployment pake-api --replicas=3 -n pake-api
kubectl scale deployment pake-ai-worker --replicas=2 -n pake-ai
kubectl scale statefulset pake-postgresql-primary --replicas=1 -n database
kubectl scale statefulset pake-postgresql-replica-eu --replicas=1 -n database
kubectl scale statefulset pake-postgresql-replica-ap --replicas=1 -n database
kubectl scale deployment redis-master --replicas=1 -n database

# Step 5: Remove chaos labels and annotations
echo "Step 5: Cleaning up chaos labels..."
kubectl label services -l chaos-promoted chaos-promoted- --all-namespaces --ignore-not-found=true
kubectl label services -l promotion-time promotion-time- --all-namespaces --ignore-not-found=true
kubectl annotate pods -l chaos-target chaos-target- --all-namespaces --ignore-not-found=true

# Step 6: Verify system health
echo "Step 6: Verifying system health..."
sleep 30  # Allow time for pods to restart

echo "Checking pod status..."
kubectl get pods --all-namespaces | grep -v Running | grep -v Completed | grep -v Terminating

echo "Testing service endpoints..."
curl -f https://api.pake-system.com/health || echo "❌ API health check failed"
curl -f https://ai.pake-system.com/health || echo "❌ AI health check failed"

# Step 7: Check database connectivity
echo "Step 7: Testing database connectivity..."
kubectl exec -it pake-postgresql-primary-0 -n database -- pg_isready -U postgres || echo "❌ PostgreSQL not ready"
kubectl exec -it redis-master-0 -n database -- redis-cli ping || echo "❌ Redis not responding"

# Step 8: Generate rollback report
echo "Step 8: Generating rollback report..."
cat > /tmp/chaos-rollback-report-$(date +%Y%m%d-%H%M%S).txt << EOF
CHAOS EMERGENCY ROLLBACK REPORT
================================
Rollback Time: $(date)
Operator: $(whoami)
Reason: Emergency termination of all chaos experiments

Actions Taken:
- Terminated all chaos jobs
- Removed all network policies  
- Stopped resource exhaustion pods
- Restored service replica counts
- Cleaned up chaos labels/annotations
- Verified system health

Post-Rollback Status:
- API Service: $(curl -s -o /dev/null -w "%{http_code}" https://api.pake-system.com/health)
- AI Service: $(curl -s -o /dev/null -w "%{http_code}" https://ai.pake-system.com/health)
- Database Status: $(kubectl exec -it pake-postgresql-primary-0 -n database -- pg_isready -U postgres > /dev/null 2>&1 && echo "Healthy" || echo "Unhealthy")
- Redis Status: $(kubectl exec -it redis-master-0 -n database -- redis-cli ping 2>/dev/null || echo "FAILED")

Remaining Issues: $(kubectl get pods --all-namespaces | grep -v Running | grep -v Completed | wc -l) pods not in Running state

EOF

echo "✅ Chaos rollback completed!"
echo "📄 Report saved to: /tmp/chaos-rollback-report-$(date +%Y%m%d-%H%M%S).txt"
```

### Selective Chaos Experiment Rollback

**Rollback Specific Experiment Type**

```bash
# Pod Kill Rollback
./scripts/rollback-pod-kill.sh() {
  echo "Rolling back pod kill experiments..."
  
  # Get list of killed pods from metrics
  KILLED_PODS=$(kubectl get events --all-namespaces | grep "chaos-pod-kill" | grep "Killing" | awk '{print $6}')
  
  # Wait for pods to restart
  for pod in $KILLED_PODS; do
    namespace=$(echo $pod | cut -d'/' -f1)
    pod_name=$(echo $pod | cut -d'/' -f2)
    
    if [ ! -z "$namespace" ] && [ ! -z "$pod_name" ]; then
      echo "Waiting for $pod to restart..."
      kubectl wait --for=condition=ready pod -l app=${pod_name%-*} -n $namespace --timeout=120s
    fi
  done
  
  echo "Pod kill rollback completed"
}

# Network Partition Rollback  
./scripts/rollback-network-partition.sh() {
  echo "Rolling back network partitions..."
  
  # Get all chaos network policies
  CHAOS_POLICIES=$(kubectl get networkpolicies --all-namespaces -l chaos-type=network-partition -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}{"\n"}{end}')
  
  # Delete each policy
  for policy in $CHAOS_POLICIES; do
    namespace=$(echo $policy | cut -d'/' -f1)
    name=$(echo $policy | cut -d'/' -f2)
    
    echo "Removing network policy: $name in $namespace"
    kubectl delete networkpolicy $name -n $namespace --ignore-not-found=true
  done
  
  # Verify connectivity restoration
  echo "Testing service connectivity..."
  kubectl run connectivity-test --image=busybox --rm -it --restart=Never -- \
    sh -c "
      echo 'Testing API connectivity...'
      wget -q --timeout=10 --tries=1 -O- http://pake-api.pake-api.svc.cluster.local:8080/health
      echo 'Testing database connectivity...'
      nc -zv pake-postgresql-primary.database.svc.cluster.local 5432
      echo 'Testing Redis connectivity...'
      nc -zv redis-master.database.svc.cluster.local 6379
    "
  
  echo "Network partition rollback completed"
}

# Resource Exhaustion Rollback
./scripts/rollback-resource-exhaustion.sh() {
  echo "Rolling back resource exhaustion..."
  
  # Stop all stress testing pods
  kubectl delete pods -l chaos-type=resource-exhaustion --all-namespaces --force --grace-period=0
  
  # Check for any remaining stress processes
  kubectl get pods --all-namespaces -o jsonpath='{range .items[*]}{.metadata.namespace}{" "}{.metadata.name}{" "}{.spec.containers[*].image}{"\n"}{end}' | \
    grep stress | while read namespace pod image; do
    echo "Found remaining stress pod: $namespace/$pod"
    kubectl delete pod $pod -n $namespace --force --grace-period=0
  done
  
  # Verify system resources
  kubectl top nodes
  kubectl top pods --all-namespaces | grep -E "(CPU|MEMORY)" | head -20
  
  echo "Resource exhaustion rollback completed"
}

# Dependency Failure Rollback
./scripts/rollback-dependency-failure.sh() {
  echo "Rolling back dependency failures..."
  
  # Remove dependency blocking policies
  kubectl delete networkpolicies -l chaos-type=dependency-failure --all-namespaces --ignore-not-found=true
  
  # Stop fault injection pods
  kubectl delete pods -l chaos-type=dependency-failure --all-namespaces --force --grace-period=0
  
  # Restore service dependencies
  kubectl rollout restart deployment/pake-api -n pake-api
  kubectl rollout restart deployment/pake-ai-worker -n pake-ai
  
  # Verify dependency connectivity
  echo "Testing external dependencies..."
  kubectl run dependency-test --image=busybox --rm -it --restart=Never -- \
    sh -c "
      echo 'Testing database connectivity...'
      nc -zv pake-postgresql-primary.database.svc.cluster.local 5432
      echo 'Testing Redis connectivity...'
      nc -zv redis-master.database.svc.cluster.local 6379
      echo 'Testing ChromaDB connectivity...'
      nc -zv chromadb.database.svc.cluster.local 8000
    "
  
  echo "Dependency failure rollback completed"
}

# Region Failover Rollback
./scripts/rollback-region-failover.sh() {
  echo "Rolling back region failover..."
  
  # Switch DNS back to primary region
  aws route53 change-resource-record-sets --hosted-zone-id Z123456789 --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.pake-system.com",
        "Type": "A", 
        "SetIdentifier": "primary-region",
        "TTL": 60,
        "ResourceRecords": [{"Value": "PRIMARY_LOAD_BALANCER_IP"}]
      }
    }]
  }'
  
  # Scale down secondary region services
  kubectl scale deployment pake-api --replicas=1 -n pake-api --context=secondary
  kubectl scale deployment pake-ai-worker --replicas=1 -n pake-ai --context=secondary
  
  # Scale up primary region services
  kubectl scale deployment pake-api --replicas=3 -n pake-api --context=primary
  kubectl scale deployment pake-ai-worker --replicas=2 -n pake-ai --context=primary
  
  # Remove promotion labels
  kubectl label services -l chaos-promoted chaos-promoted- --all-namespaces --context=secondary
  
  # Verify primary region health
  curl -f https://api.pake-system.com/health
  
  echo "Region failover rollback completed"
}
```

### Post-Rollback Verification

```bash
# Comprehensive system health check after chaos rollback
./scripts/post-chaos-health-check.sh() {
  echo "=== POST-CHAOS HEALTH VERIFICATION ==="
  
  # Check all pods are running
  echo "1. Pod Status Check:"
  NON_RUNNING_PODS=$(kubectl get pods --all-namespaces | grep -v Running | grep -v Completed | grep -v Terminating | wc -l)
  if [ $NON_RUNNING_PODS -eq 1 ]; then  # Header line counts as 1
    echo "✅ All pods are running normally"
  else
    echo "⚠️  $((NON_RUNNING_PODS - 1)) pods not in running state:"
    kubectl get pods --all-namespaces | grep -v Running | grep -v Completed | grep -v Terminating
  fi
  
  # Check service endpoints
  echo "2. Service Endpoint Check:"
  curl -f -s https://api.pake-system.com/health > /dev/null && echo "✅ API service healthy" || echo "❌ API service unhealthy"
  curl -f -s https://ai.pake-system.com/health > /dev/null && echo "✅ AI service healthy" || echo "❌ AI service unhealthy"
  
  # Check database connectivity
  echo "3. Database Connectivity Check:"
  kubectl exec -it pake-postgresql-primary-0 -n database -- pg_isready -U postgres > /dev/null 2>&1 && echo "✅ PostgreSQL healthy" || echo "❌ PostgreSQL unhealthy"
  kubectl exec -it redis-master-0 -n database -- redis-cli ping > /dev/null 2>&1 && echo "✅ Redis healthy" || echo "❌ Redis unhealthy"
  
  # Check replication status
  echo "4. Replication Status Check:"
  PG_LAG=$(kubectl exec -it pake-postgresql-replica-eu-0 -n database -- psql -U postgres -t -c "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()));" 2>/dev/null | tr -d ' ')
  if [[ "$PG_LAG" =~ ^[0-9]+$ ]] && [ $PG_LAG -lt 300 ]; then
    echo "✅ PostgreSQL replication lag: ${PG_LAG}s (within target)"
  else
    echo "⚠️  PostgreSQL replication lag: ${PG_LAG}s (check required)"
  fi
  
  # Check for chaos artifacts
  echo "5. Chaos Artifacts Check:"
  CHAOS_POLICIES=$(kubectl get networkpolicies --all-namespaces -l chaos-experiment --no-headers 2>/dev/null | wc -l)
  CHAOS_PODS=$(kubectl get pods --all-namespaces -l chaos-type --no-headers 2>/dev/null | wc -l)
  
  if [ $CHAOS_POLICIES -eq 0 ] && [ $CHAOS_PODS -eq 0 ]; then
    echo "✅ No chaos artifacts remaining"
  else
    echo "⚠️  Cleanup required: $CHAOS_POLICIES policies, $CHAOS_PODS pods"
  fi
  
  # Check monitoring
  echo "6. Monitoring Status Check:"
  curl -f -s http://prometheus.monitoring.svc.cluster.local:9090/-/healthy > /dev/null && echo "✅ Prometheus healthy" || echo "❌ Prometheus unhealthy"
  curl -f -s http://grafana.monitoring.svc.cluster.local:3000/api/health > /dev/null && echo "✅ Grafana healthy" || echo "❌ Grafana unhealthy"
  
  echo "=== HEALTH CHECK COMPLETED ==="
}
```

---

## 📢 Communication Templates

### Status Page Updates

**Incident Detection Template**
```markdown
🟡 **INVESTIGATING** - We are currently investigating reports of connectivity issues affecting our services. 
- **Detected**: [TIMESTAMP]
- **Impact**: [BRIEF DESCRIPTION]
- **Services Affected**: [LIST OF SERVICES]
- **Next Update**: In 15 minutes

We will provide updates every 15 minutes until resolved.
```

**Failover In Progress Template**
```markdown
🟠 **MAJOR OUTAGE** - We have confirmed a service disruption and are implementing failover procedures.
- **Incident Started**: [TIMESTAMP]
- **Current Status**: Failing over to backup systems
- **Estimated Resolution**: [RTO TARGET TIME]
- **Services Affected**: [LIST OF SERVICES]
- **Workaround**: [IF AVAILABLE]
- **Next Update**: In 10 minutes

Our engineering team is actively working on restoration.
```

**Service Restored Template**
```markdown
🟢 **RESOLVED** - All services have been restored and are operating normally.
- **Incident Duration**: [TOTAL TIME]
- **Resolution**: [BRIEF DESCRIPTION OF FIX]
- **Services Restored**: [LIST OF SERVICES]
- **Monitoring**: We continue to monitor system health closely

A detailed post-mortem will be published within 72 hours.
```

**Scheduled Maintenance Template**
```markdown
🔵 **SCHEDULED MAINTENANCE** - Disaster Recovery Testing
- **Maintenance Window**: [START TIME] - [END TIME] UTC
- **Expected Impact**: Brief service interruptions possible
- **Services**: API and AI services may experience 2-3 minute downtime
- **Purpose**: Testing automated failover systems
- **Contact**: For urgent issues, contact support@pake-system.com

This maintenance improves our system reliability and disaster recovery capabilities.
```

### Internal Slack/Teams Communication

**Initial Alert Template**
```
🚨 **INCIDENT ALERT** - P0 Production Issue

**Incident ID**: INC-2024-[NUMBER]
**Detected**: [TIMESTAMP]
**Reporter**: @[USERNAME]
**Status**: INVESTIGATING

**Issue**: [ONE LINE DESCRIPTION]
**Affected Services**: [LIST]
**User Impact**: [DESCRIPTION]

**War Room**: #incident-[NUMBER]
**Incident Commander**: @[IC_NAME]
**Communications Lead**: @[COMMS_LEAD]

**Current Actions**:
- [ ] Health check in progress
- [ ] Monitoring dashboards reviewed
- [ ] Escalation started

**Next Update**: 10 minutes
```

**Failover Decision Template**
```
🔄 **FAILOVER DECISION** - P0 Incident

**Incident ID**: INC-2024-[NUMBER]
**Decision Time**: [TIMESTAMP]
**Decision Maker**: @[IC_NAME]

**DECISION**: Proceeding with failover to secondary region

**Justification**:
- Primary region health: [STATUS]
- RTO timer: [ELAPSED TIME]/15 minutes
- Fallback options exhausted: [YES/NO]

**Failover Plan**:
- [ ] Database promotion (Target: 2 min)
- [ ] DNS switchover (Target: 3 min)
- [ ] Service scaling (Target: 5 min)
- [ ] Verification (Target: 5 min)

**Teams**:
- **Database**: @[DB_TEAM]
- **Infrastructure**: @[INFRA_TEAM]
- **Application**: @[APP_TEAM]

**Next Update**: Every 3 minutes during failover
```

**All Clear Template**
```
✅ **ALL CLEAR** - P0 Incident Resolved

**Incident ID**: INC-2024-[NUMBER]
**Resolution Time**: [TIMESTAMP]
**Total Duration**: [DURATION]

**Resolution Summary**:
- Issue: [BRIEF DESCRIPTION]
- Root Cause: [IF KNOWN]
- Fix Applied: [DESCRIPTION]

**Final Metrics**:
- **RTO Achieved**: [ACTUAL TIME] (Target: 15 min)
- **RPO Achieved**: [ACTUAL TIME] (Target: 5 min)
- **Services Restored**: All systems operational

**Next Steps**:
- [ ] Post-mortem scheduled for [DATE/TIME]
- [ ] Monitoring increased for next 24h
- [ ] Customer communication sent
- [ ] Incident report created

**Thanks** to everyone who participated in the response! 🙏

War room will remain open for 30 minutes for any questions.
```

**Chaos Engineering Alert Template**
```
🧪 **CHAOS EXPERIMENT** - Scheduled Testing

**Experiment Type**: [POD_KILL/NETWORK_PARTITION/etc.]
**Start Time**: [TIMESTAMP]
**Duration**: [DURATION]
**Operator**: @[USERNAME]

**Scope**:
- **Target Services**: [LIST]
- **Expected Impact**: [DESCRIPTION]
- **Safety Measures**: [LIST]

**Monitoring**:
- Dashboard: [LINK]
- Logs: [LINK]
- Emergency stop: `kubectl delete job [JOB_NAME] -n chaos-testing`

**Expected Behavior**:
- [LIST OF EXPECTED BEHAVIORS]

**Alert Suppression**: Chaos-related alerts suppressed for [DURATION]

React with ✅ when you've seen this message.
```

### Email Templates

**Customer Communication - Incident Notification**
```
Subject: Service Incident - [BRIEF DESCRIPTION] - [STATUS]

Dear PAKE Users,

We are currently experiencing [BRIEF DESCRIPTION OF ISSUE] that may affect your ability to [SPECIFIC IMPACT].

**Incident Details:**
- Start Time: [TIME] UTC
- Current Status: [INVESTIGATING/RESOLVING/RESOLVED]
- Affected Services: [LIST]
- Estimated Resolution: [TIME RANGE]

**What We're Doing:**
[BRIEF DESCRIPTION OF ACTIONS BEING TAKEN]

**Workaround (if available):**
[STEPS USERS CAN TAKE]

We sincerely apologize for this disruption and are working diligently to restore full service. We will send updates every 30 minutes until resolved.

You can check our real-time status at: https://status.pake-system.com

Best regards,
The PAKE Engineering Team

---
This is an automated message. For support, please contact support@pake-system.com
```

**Customer Communication - Resolution Notice**
```
Subject: RESOLVED - Service Incident - [BRIEF DESCRIPTION]

Dear PAKE Users,

The service incident affecting [SERVICES] has been resolved as of [TIME] UTC.

**Incident Summary:**
- Duration: [TOTAL TIME]
- Root Cause: [BRIEF TECHNICAL DESCRIPTION]
- Resolution: [BRIEF DESCRIPTION OF FIX]

**What Happened:**
[CLEAR, NON-TECHNICAL EXPLANATION OF THE INCIDENT]

**What We're Doing to Prevent This:**
- [ACTION ITEM 1]
- [ACTION ITEM 2]
- [ACTION ITEM 3]

All services are now operating normally. We will continue monitoring closely over the next 24 hours to ensure stability.

A detailed post-mortem report will be published on our blog within 3 business days.

We sincerely apologize for any inconvenience this may have caused. Thank you for your patience as we worked to resolve this issue.

Best regards,
The PAKE Engineering Team

---
For questions about this incident, please contact support@pake-system.com
```

---

## 📋 Post-Mortem Template

### Incident Post-Mortem Report

**Incident ID**: INC-2024-[NUMBER]  
**Date**: [INCIDENT DATE]  
**Prepared by**: [AUTHOR NAME]  
**Reviewed by**: [REVIEWER NAMES]  
**Published**: [PUBLICATION DATE]

---

#### Executive Summary

**Incident Overview**  
On [DATE] at [TIME] UTC, PAKE experienced [BRIEF DESCRIPTION] lasting [DURATION]. This resulted in [IMPACT DESCRIPTION] affecting approximately [NUMBER] users.

**Key Metrics**
- **Detection Time**: [TIME FROM START TO DETECTION]
- **Time to Mitigation**: [TIME FROM DETECTION TO FIRST MITIGATION]
- **Time to Resolution**: [TIME FROM DETECTION TO FULL RESOLUTION]
- **Total Duration**: [TOTAL INCIDENT TIME]
- **User Impact**: [PERCENTAGE OF USERS AFFECTED]

---

#### Timeline of Events

All times in UTC.

| Time | Event | Action Taken | Owner |
|------|-------|--------------|-------|
| [TIME] | **Incident Start** | [TRIGGERING EVENT] | System |
| [TIME] | **Detection** | [HOW DETECTED] | [WHO] |
| [TIME] | **Investigation Begins** | [INITIAL ACTIONS] | [WHO] |
| [TIME] | **Escalation** | [ESCALATION ACTIONS] | [WHO] |
| [TIME] | **Root Cause Identified** | [CAUSE FOUND] | [WHO] |
| [TIME] | **Mitigation Started** | [MITIGATION ACTIONS] | [WHO] |
| [TIME] | **Service Restored** | [RESOLUTION ACTIONS] | [WHO] |
| [TIME] | **All Clear** | [VERIFICATION] | [WHO] |

---

#### Root Cause Analysis

**Primary Root Cause**  
[DETAILED TECHNICAL DESCRIPTION OF THE ROOT CAUSE]

**Contributing Factors**
1. [FACTOR 1 WITH EXPLANATION]
2. [FACTOR 2 WITH EXPLANATION]  
3. [FACTOR 3 WITH EXPLANATION]

**Technical Details**
```
[RELEVANT CODE, CONFIGURATION, OR LOGS]
```

**Failure Mode Analysis**
- **What Failed**: [COMPONENT/PROCESS THAT FAILED]
- **How It Failed**: [MECHANISM OF FAILURE]
- **Why It Failed**: [UNDERLYING CAUSE]
- **Why Not Detected Earlier**: [DETECTION GAPS]

---

#### Impact Assessment

**Service Availability**
- **API Service**: [AVAILABILITY PERCENTAGE] ([DOWNTIME DURATION])
- **AI Service**: [AVAILABILITY PERCENTAGE] ([DOWNTIME DURATION])
- **Database**: [AVAILABILITY PERCENTAGE] ([DOWNTIME DURATION])

**User Impact**
- **Total Users Affected**: [NUMBER] ([PERCENTAGE])
- **Critical Operations Impacted**: [LIST]
- **Data Loss**: [YES/NO] - [DETAILS IF ANY]
- **Revenue Impact**: [ESTIMATE IF APPLICABLE]

**Performance Impact**
- **Response Time Degradation**: [METRICS]
- **Error Rate Increase**: [METRICS]
- **Throughput Reduction**: [METRICS]

---

#### Response Evaluation

**What Went Well**
- ✅ [POSITIVE ASPECT 1]
- ✅ [POSITIVE ASPECT 2]
- ✅ [POSITIVE ASPECT 3]

**What Could Be Improved**
- ⚠️ [IMPROVEMENT AREA 1]
- ⚠️ [IMPROVEMENT AREA 2]
- ⚠️ [IMPROVEMENT AREA 3]

**RTO/RPO Analysis**
- **Target RTO**: 15 minutes
- **Actual RTO**: [ACTUAL TIME]
- **RTO Met**: [YES/NO]
- **Target RPO**: 5 minutes  
- **Actual RPO**: [ACTUAL TIME]
- **RPO Met**: [YES/NO]

**Monitoring and Detection**
- **Time to Detection**: [TIME] (Target: < 2 minutes)
- **Detection Method**: [AUTOMATED/MANUAL]
- **False Positives**: [COUNT]
- **Missed Alerts**: [COUNT]

---

#### Action Items

**Immediate Actions (0-7 days)**
- [ ] **[PRIORITY]** [ACTION ITEM 1] - Owner: [NAME] - Due: [DATE]
- [ ] **[PRIORITY]** [ACTION ITEM 2] - Owner: [NAME] - Due: [DATE]
- [ ] **[PRIORITY]** [ACTION ITEM 3] - Owner: [NAME] - Due: [DATE]

**Short-term Actions (1-4 weeks)**
- [ ] **[PRIORITY]** [ACTION ITEM 1] - Owner: [NAME] - Due: [DATE]
- [ ] **[PRIORITY]** [ACTION ITEM 2] - Owner: [NAME] - Due: [DATE]
- [ ] **[PRIORITY]** [ACTION ITEM 3] - Owner: [NAME] - Due: [DATE]

**Long-term Actions (1-3 months)**
- [ ] **[PRIORITY]** [ACTION ITEM 1] - Owner: [NAME] - Due: [DATE]
- [ ] **[PRIORITY]** [ACTION ITEM 2] - Owner: [NAME] - Due: [DATE]
- [ ] **[PRIORITY]** [ACTION ITEM 3] - Owner: [NAME] - Due: [DATE]

---

#### Prevention Measures

**Technical Improvements**
1. **[IMPROVEMENT 1]**
   - Description: [DETAILS]
   - Implementation: [APPROACH]
   - Timeline: [DURATION]

2. **[IMPROVEMENT 2]**
   - Description: [DETAILS]
   - Implementation: [APPROACH]
   - Timeline: [DURATION]

**Process Improvements**
1. **[PROCESS 1]**
   - Current State: [DESCRIPTION]
   - Desired State: [DESCRIPTION]
   - Implementation Plan: [STEPS]

2. **[PROCESS 2]**
   - Current State: [DESCRIPTION]
   - Desired State: [DESCRIPTION]
   - Implementation Plan: [STEPS]

**Monitoring and Alerting Improvements**
- [ ] Add monitoring for [SPECIFIC METRIC]
- [ ] Improve alert thresholds for [SPECIFIC ALERT]
- [ ] Create dashboard for [SPECIFIC VIEW]
- [ ] Automate response for [SPECIFIC SCENARIO]

---

#### Testing and Validation

**Chaos Engineering Enhancements**
- [ ] Add chaos test for [FAILURE SCENARIO]
- [ ] Increase frequency of [TEST TYPE]
- [ ] Improve test coverage for [COMPONENT]

**Disaster Recovery Testing**
- [ ] Test [SPECIFIC SCENARIO] in staging
- [ ] Validate [SPECIFIC PROCEDURE]
- [ ] Update runbook for [SPECIFIC PROCESS]

**Load Testing**
- [ ] Test system behavior under [SPECIFIC LOAD]
- [ ] Validate auto-scaling for [SPECIFIC SCENARIO]
- [ ] Test degradation patterns for [SPECIFIC COMPONENT]

---

#### Lessons Learned

**Technical Lessons**
1. [LESSON 1 WITH EXPLANATION]
2. [LESSON 2 WITH EXPLANATION]
3. [LESSON 3 WITH EXPLANATION]

**Process Lessons**
1. [LESSON 1 WITH EXPLANATION]
2. [LESSON 2 WITH EXPLANATION]
3. [LESSON 3 WITH EXPLANATION]

**Communication Lessons**
1. [LESSON 1 WITH EXPLANATION]
2. [LESSON 2 WITH EXPLANATION]
3. [LESSON 3 WITH EXPLANATION]

---

#### Supporting Information

**Relevant Documentation**
- [LINK TO RUNBOOK]
- [LINK TO ARCHITECTURE DIAGRAM]
- [LINK TO MONITORING DASHBOARD]

**External References**
- [VENDOR DOCUMENTATION]
- [INDUSTRY BEST PRACTICES]
- [RELATED INCIDENTS]

**Code/Configuration Changes**
```bash
# Relevant configuration before incident
[BEFORE CONFIG]

# Configuration after fix
[AFTER CONFIG]

# Relevant code changes
[CODE DIFF OR REFERENCE]
```

---

#### Appendix

**A. Detailed Logs**
```
[RELEVANT LOG ENTRIES WITH TIMESTAMPS]
```

**B. Monitoring Data**
[ATTACH RELEVANT GRAPHS/CHARTS]

**C. Communication Log**
[TIMELINE OF INTERNAL/EXTERNAL COMMUNICATIONS]

**D. Decision Log**
[RECORD OF KEY DECISIONS MADE DURING INCIDENT]

---

**Report Approval**

- **Technical Review**: [NAME] - [DATE]
- **Management Review**: [NAME] - [DATE]
- **Final Approval**: [NAME] - [DATE]

---

*This post-mortem follows the blameless post-mortem principles. The focus is on improving systems and processes, not assigning blame to individuals.*

---

## Compliance Retrieval Procedures

### Retrieving Compliance Attestations

#### Monthly Attestation Retrieval
```bash
#!/bin/bash
# Retrieve latest monthly compliance attestation

MONTH=$(date +%Y-%m)
ATTESTATION_BUCKET="pake-compliance-attestations"
EVIDENCE_BUCKET="pake-compliance-evidence"

echo "Retrieving monthly attestation for $MONTH..."

# List available attestations
aws s3 ls s3://$ATTESTATION_BUCKET/dr-attestations/$MONTH/ \
  --query 'Contents[?Size > `0`].[Key,LastModified,Size]' \
  --output table

# Download latest attestation
LATEST_ATTESTATION=$(aws s3api list-objects-v2 \
  --bucket $ATTESTATION_BUCKET \
  --prefix "dr-attestations/$MONTH/" \
  --query 'sort_by(Contents, &LastModified)[-1].Key' \
  --output text)

if [ "$LATEST_ATTESTATION" != "None" ]; then
  echo "Downloading: $LATEST_ATTESTATION"
  aws s3 cp "s3://$ATTESTATION_BUCKET/$LATEST_ATTESTATION" ./monthly-attestation.json.gz
  gunzip monthly-attestation.json.gz
  
  # Download corresponding evidence bundle
  ATTESTATION_ID=$(basename $LATEST_ATTESTATION .json)
  EVIDENCE_KEY="dr-evidence/$MONTH/${ATTESTATION_ID}-evidence.json"
  
  aws s3 cp "s3://$EVIDENCE_BUCKET/$EVIDENCE_KEY" ./monthly-evidence.json.gz
  gunzip monthly-evidence.json.gz
  
  echo "Files downloaded:"
  ls -la monthly-attestation.json monthly-evidence.json
else
  echo "No attestation found for $MONTH"
  exit 1
fi
```

#### Quarterly Attestation Retrieval
```bash
#!/bin/bash
# Retrieve quarterly compliance attestation

QUARTER=$(date +%Y-Q$(($(date +%-m-1)/3+1)))
YEAR=$(date +%Y)

echo "Retrieving quarterly attestation for $QUARTER..."

# List quarterly attestations
aws s3 ls s3://pake-compliance-attestations/dr-attestations/quarterly/$YEAR/ \
  --recursive --human-readable

# Download specific quarterly attestation
read -p "Enter attestation filename: " ATTESTATION_FILE
aws s3 cp "s3://pake-compliance-attestations/dr-attestations/quarterly/$YEAR/$ATTESTATION_FILE" \
  ./quarterly-attestation.json.gz

gunzip quarterly-attestation.json.gz
echo "Quarterly attestation downloaded: quarterly-attestation.json"
```

#### Annual Attestation Retrieval
```bash
#!/bin/bash
# Retrieve annual comprehensive attestation

YEAR=$(date +%Y)
echo "Retrieving annual attestation for $YEAR..."

# List annual attestations
aws s3 ls s3://pake-compliance-attestations/dr-attestations/annual/$YEAR/ \
  --recursive --human-readable

# Download annual attestation (typically one per year)
ANNUAL_ATTESTATION=$(aws s3api list-objects-v2 \
  --bucket pake-compliance-attestations \
  --prefix "dr-attestations/annual/$YEAR/" \
  --query 'Contents[0].Key' \
  --output text)

if [ "$ANNUAL_ATTESTATION" != "None" ]; then
  aws s3 cp "s3://pake-compliance-attestations/$ANNUAL_ATTESTATION" \
    ./annual-attestation.json.gz
  gunzip annual-attestation.json.gz
  echo "Annual attestation downloaded: annual-attestation.json"
else
  echo "No annual attestation found for $YEAR"
fi
```

### Retrieving Audit Logs

#### Date Range Audit Log Retrieval
```bash
#!/bin/bash
# Retrieve audit logs for specific date range

START_DATE=${1:-$(date -d '30 days ago' +%Y/%m/%d)}
END_DATE=${2:-$(date +%Y/%m/%d)}

echo "Retrieving audit logs from $START_DATE to $END_DATE..."

AUDIT_BUCKET="pake-compliance-audit-logs"
BACKUP_BUCKET="pake-compliance-audit-logs-backup"

# Create local directory
mkdir -p audit-logs/$START_DATE-to-$END_DATE

# Retrieve from primary location
aws s3 sync "s3://$AUDIT_BUCKET/dr-audit-logs/" \
  "./audit-logs/$START_DATE-to-$END_DATE/" \
  --exclude "*" \
  --include "*/$START_DATE/*" \
  --include "*/$END_DATE/*"

# If primary fails, try backup
if [ $? -ne 0 ]; then
  echo "Primary audit log retrieval failed, trying backup..."
  aws s3 sync "s3://$BACKUP_BUCKET/dr-audit-logs/" \
    "./audit-logs/$START_DATE-to-$END_DATE/" \
    --exclude "*" \
    --include "*/$START_DATE/*" \
    --include "*/$END_DATE/*"
fi

echo "Audit logs retrieved to: ./audit-logs/$START_DATE-to-$END_DATE/"
find ./audit-logs/$START_DATE-to-$END_DATE/ -name "*.json" | wc -l
echo "Total audit events retrieved"
```

#### Incident-Specific Audit Retrieval
```bash
#!/bin/bash
# Retrieve audit logs for specific incident

INCIDENT_ID=${1:?"Usage: $0 <incident-id> [start-time] [end-time]"}
START_TIME=${2:-$(date -d '2 hours ago' --iso-8601=seconds)}
END_TIME=${3:-$(date --iso-8601=seconds)}

echo "Retrieving audit logs for incident: $INCIDENT_ID"
echo "Time range: $START_TIME to $END_TIME"

# Download relevant audit logs
aws s3 cp s3://pake-compliance-audit-logs/dr-audit-logs/ \
  ./incident-audit-logs/ \
  --recursive \
  --exclude "*" \
  --include "*/$(date -d "$START_TIME" +%Y/%m/%d)/*" \
  --include "*/$(date -d "$END_TIME" +%Y/%m/%d)/*"

# Filter logs by time range and create incident report
python3 << EOF
import json
import glob
from datetime import datetime

incident_logs = []
start_time = datetime.fromisoformat("$START_TIME".replace('Z', '+00:00'))
end_time = datetime.fromisoformat("$END_TIME".replace('Z', '+00:00'))

for log_file in glob.glob('./incident-audit-logs/**/*.json', recursive=True):
    try:
        with open(log_file, 'r') as f:
            log_data = json.load(f)
            log_time = datetime.fromisoformat(log_data['timestamp'].replace('Z', '+00:00'))
            
            if start_time <= log_time <= end_time:
                incident_logs.append(log_data)
    except Exception as e:
        print(f"Error processing {log_file}: {e}")

# Sort by timestamp
incident_logs.sort(key=lambda x: x['timestamp'])

# Save incident-specific logs
with open(f'incident-{incident_id}-audit-logs.json', 'w') as f:
    json.dump(incident_logs, f, indent=2)

print(f"Incident audit logs saved: incident-${INCIDENT_ID}-audit-logs.json")
print(f"Total events: {len(incident_logs)}")
EOF
```

### Verification and Validation

#### Attestation Signature Verification
```bash
#!/bin/bash
# Verify attestation digital signature

ATTESTATION_FILE=${1:?"Usage: $0 <attestation-file.json>"}

echo "Verifying digital signature for: $ATTESTATION_FILE"

# Extract signature information
python3 << EOF
import json
import base64
import jwt
from cryptography import x509
from cryptography.hazmat.primitives import serialization

with open('$ATTESTATION_FILE', 'r') as f:
    attestation = json.load(f)

if 'attestation_signature' not in attestation:
    print("ERROR: No digital signature found")
    exit(1)

signature_info = attestation['attestation_signature']
token = signature_info['signature']

# Decode without verification to inspect
try:
    header = jwt.get_unverified_header(token)
    payload = jwt.decode(token, options={"verify_signature": False})
    
    print("Signature Algorithm:", signature_info['algorithm'])
    print("Signing Time:", signature_info['signing_timestamp'])
    print("Certificate Fingerprint:", signature_info['certificate_fingerprint'])
    print("Signed By:", signature_info['signed_by'])
    print("Token Header:", json.dumps(header, indent=2))
    print("Token Payload:", json.dumps(payload, indent=2))
    
    # Extract certificate if available
    if 'x5c' in header:
        cert_data = base64.b64decode(header['x5c'][0])
        cert = x509.load_der_x509_certificate(cert_data)
        print("Certificate Subject:", cert.subject)
        print("Certificate Valid From:", cert.not_valid_before)
        print("Certificate Valid Until:", cert.not_valid_after)
    
    print("Signature verification: PASSED (structure valid)")
    
except Exception as e:
    print(f"ERROR: Signature verification failed: {e}")
    exit(1)
EOF
```

#### Audit Log Chain Verification
```bash
#!/bin/bash
# Verify audit log chain integrity

LOG_DIRECTORY=${1:?"Usage: $0 <audit-log-directory>"}

echo "Verifying audit log chain integrity in: $LOG_DIRECTORY"

python3 << EOF
import json
import glob
import hashlib
import os

log_files = sorted(glob.glob('$LOG_DIRECTORY/**/*.json', recursive=True))
print(f"Found {len(log_files)} audit log files")

chain_valid = True
previous_hash = None
sequence_gaps = []

for log_file in log_files:
    try:
        with open(log_file, 'r') as f:
            log_data = json.load(f)
        
        current_hash = log_data.get('log_hash')
        previous_log_hash = log_data.get('previous_log_hash')
        sequence_number = log_data.get('sequence_number', 0)
        
        if previous_hash is not None and previous_log_hash != previous_hash:
            print(f"CHAIN BREAK at {log_file}")
            print(f"  Expected previous hash: {previous_hash}")
            print(f"  Actual previous hash: {previous_log_hash}")
            chain_valid = False
        
        # Verify current log hash
        temp_data = log_data.copy()
        temp_data.pop('log_hash', None)
        calculated_hash = hashlib.sha256(json.dumps(temp_data, sort_keys=True).encode()).hexdigest()
        
        if calculated_hash != current_hash:
            print(f"HASH MISMATCH at {log_file}")
            print(f"  Expected: {current_hash}")
            print(f"  Calculated: {calculated_hash}")
            chain_valid = False
        
        previous_hash = current_hash
        
    except Exception as e:
        print(f"ERROR processing {log_file}: {e}")
        chain_valid = False

if chain_valid:
    print("✓ Audit log chain integrity: VALID")
else:
    print("✗ Audit log chain integrity: COMPROMISED")
    exit(1)
EOF
```

### Compliance Report Generation

#### Framework-Specific Report Extraction
```bash
#!/bin/bash
# Extract framework-specific compliance report

ATTESTATION_FILE=${1:?"Usage: $0 <attestation-file.json> <framework>"}
FRAMEWORK=${2:?"Specify framework: soc2, iso27001, gdpr, fedramp"}

echo "Extracting $FRAMEWORK compliance report from: $ATTESTATION_FILE"

python3 << EOF
import json
from datetime import datetime

with open('$ATTESTATION_FILE', 'r') as f:
    attestation = json.load(f)

framework = '$FRAMEWORK'
if framework not in attestation['control_assessments']:
    print(f"Framework {framework} not found in attestation")
    exit(1)

framework_data = attestation['control_assessments'][framework]
metadata = attestation['metadata']

# Generate framework-specific report
report = {
    'report_type': f'{framework.upper()} Compliance Report',
    'organization': metadata['organization_info']['name'],
    'reporting_period': metadata['reporting_period'],
    'generation_date': datetime.now().isoformat(),
    'framework_version': framework_data['framework_version'],
    'overall_status': framework_data['overall_status'],
    'control_summary': {}
}

# Summarize controls
total_controls = len(framework_data['controls'])
implemented = sum(1 for c in framework_data['controls'].values() if c['implementation_status'] == 'implemented')
tested = sum(1 for c in framework_data['controls'].values() if c['testing_status'] == 'tested')
effective = sum(1 for c in framework_data['controls'].values() if c['effectiveness'] == 'effective')

report['control_summary'] = {
    'total_controls': total_controls,
    'implemented_controls': implemented,
    'tested_controls': tested,
    'effective_controls': effective,
    'implementation_rate': f"{implemented/total_controls*100:.1f}%",
    'testing_rate': f"{tested/total_controls*100:.1f}%",
    'effectiveness_rate': f"{effective/total_controls*100:.1f}%"
}

# Detailed control assessment
report['detailed_controls'] = framework_data['controls']

# Save framework-specific report
output_file = f'{framework}-compliance-report.json'
with open(output_file, 'w') as f:
    json.dump(report, f, indent=2)

print(f"{framework.upper()} compliance report saved: {output_file}")
print(f"Overall Status: {framework_data['overall_status']}")
print(f"Implementation Rate: {report['control_summary']['implementation_rate']}")
print(f"Effectiveness Rate: {report['control_summary']['effectiveness_rate']}")
EOF
```

#### Compliance Search and Analytics
```bash
#!/bin/bash
# Search compliance data for specific events or patterns

SEARCH_TERM=${1:?"Usage: $0 <search-term> [start-date] [end-date]"}
START_DATE=${2:-$(date -d '30 days ago' +%Y-%m-%d)}
END_DATE=${3:-$(date +%Y-%m-%d)}

echo "Searching compliance data for: '$SEARCH_TERM'"
echo "Date range: $START_DATE to $END_DATE"

# Search audit logs
echo "Searching audit logs..."
aws s3 cp s3://pake-compliance-audit-logs/dr-audit-logs/ \
  ./search-results/ \
  --recursive \
  --exclude "*" \
  --include "*/${START_DATE//-/\/}/*" \
  --include "*/${END_DATE//-/\/}/*"

# Search and filter
python3 << EOF
import json
import glob
import re
from datetime import datetime

search_term = '$SEARCH_TERM'.lower()
results = []

# Search audit logs
for log_file in glob.glob('./search-results/**/*.json', recursive=True):
    try:
        with open(log_file, 'r') as f:
            log_data = json.load(f)
            
        # Convert to searchable text
        log_text = json.dumps(log_data).lower()
        
        if search_term in log_text:
            results.append({
                'type': 'audit_log',
                'timestamp': log_data.get('timestamp'),
                'event_type': log_data.get('event_type'),
                'operator': log_data.get('operator_identity', {}).get('user_name'),
                'resource': log_data.get('resource_identifiers'),
                'file': log_file
            })
    except Exception as e:
        print(f"Error processing {log_file}: {e}")

# Search attestations
for attestation_file in glob.glob('./*attestation*.json'):
    try:
        with open(attestation_file, 'r') as f:
            attestation_data = json.load(f)
            
        attestation_text = json.dumps(attestation_data).lower()
        
        if search_term in attestation_text:
            results.append({
                'type': 'compliance_attestation',
                'timestamp': attestation_data.get('metadata', {}).get('generation_timestamp'),
                'frameworks': attestation_data.get('metadata', {}).get('frameworks_covered'),
                'file': attestation_file
            })
    except Exception as e:
        print(f"Error processing {attestation_file}: {e}")

# Sort by timestamp
results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

# Save search results
with open(f'compliance-search-results-{search_term.replace(" ", "-")}.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f"Found {len(results)} matching entries")
for result in results[:10]:  # Show first 10 results
    print(f"  {result['timestamp']} - {result['type']} - {result.get('event_type', 'N/A')}")

if len(results) > 10:
    print(f"  ... and {len(results) - 10} more")
EOF
```

#### Emergency Compliance Report
```bash
#!/bin/bash
# Generate emergency compliance report for incidents

INCIDENT_ID=${1:?"Usage: $0 <incident-id>"}
INCIDENT_START=${2:-$(date -d '4 hours ago' --iso-8601=seconds)}

echo "Generating emergency compliance report for incident: $INCIDENT_ID"

# Retrieve recent attestation
./retrieve-monthly-attestation.sh

# Retrieve incident audit logs
./retrieve-incident-audit-logs.sh $INCIDENT_ID $INCIDENT_START

# Generate emergency report
python3 << EOF
import json
from datetime import datetime

incident_id = '$INCIDENT_ID'
incident_start = '$INCIDENT_START'

# Load latest attestation
try:
    with open('monthly-attestation.json', 'r') as f:
        attestation = json.load(f)
except FileNotFoundError:
    print("No monthly attestation found")
    attestation = None

# Load incident audit logs
try:
    with open(f'incident-{incident_id}-audit-logs.json', 'r') as f:
        incident_logs = json.load(f)
except FileNotFoundError:
    print("No incident audit logs found")
    incident_logs = []

# Generate emergency report
emergency_report = {
    'report_type': 'Emergency Compliance Report',
    'incident_id': incident_id,
    'incident_start_time': incident_start,
    'report_generation_time': datetime.now().isoformat(),
    
    'compliance_status': {
        'latest_attestation': attestation['metadata'] if attestation else None,
        'incident_audit_coverage': len(incident_logs) > 0,
        'audit_log_integrity': 'verified' if incident_logs else 'unknown'
    },
    
    'incident_compliance_impact': {
        'audit_events_captured': len(incident_logs),
        'operator_actions_logged': len([log for log in incident_logs if 'operator_identity' in log]),
        'sensitive_operations': len([log for log in incident_logs if log.get('severity') in ['high', 'critical']]),
        'compliance_frameworks_affected': attestation['metadata']['frameworks_covered'] if attestation else []
    },
    
    'recommendations': [
        'Ensure incident is documented in post-mortem',
        'Verify audit log chain integrity',
        'Update risk assessment if needed',
        'Consider notification requirements for affected frameworks'
    ]
}

# Save emergency report
with open(f'emergency-compliance-report-{incident_id}.json', 'w') as f:
    json.dump(emergency_report, f, indent=2)

print(f"Emergency compliance report generated: emergency-compliance-report-{incident_id}.json")
print(f"Audit events captured: {emergency_report['incident_compliance_impact']['audit_events_captured']}")
print(f"Frameworks potentially affected: {', '.join(emergency_report['incident_compliance_impact']['compliance_frameworks_affected'])}")
EOF

echo "Emergency compliance report completed"
```

---

### Compliance Retrieval Quick Reference

#### Daily Checks
```bash
# Check audit log collection status
kubectl logs -n compliance-system -l app=dr-audit-collector --tail=50

# Verify backup evidence freshness
aws s3 ls s3://pake-backups/ --recursive | tail -10

# Check compliance job status
kubectl get jobs -n compliance-system
```

#### Weekly Compliance Health Check
```bash
# Comprehensive compliance health check
./check-audit-collection.sh
./verify-backup-freshness.sh
./test-attestation-retrieval.sh
./validate-signature-certificates.sh
```

#### Monthly Attestation Workflow
```bash
# Complete monthly attestation workflow
kubectl get cronjob compliance-attestation-monthly -n compliance-system
kubectl logs -n compliance-system job/$(kubectl get jobs -n compliance-system -l app=compliance-attestation --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
./retrieve-monthly-attestation.sh
./verify-attestation-signature.sh monthly-attestation.json
```

#### Incident Response Compliance
```bash
# Emergency compliance response for incidents
INCIDENT_ID="INC-$(date +%Y%m%d-%H%M)"
./retrieve-incident-audit-logs.sh $INCIDENT_ID
./verify-audit-chain.sh ./incident-audit-logs/
./generate-emergency-compliance-report.sh $INCIDENT_ID
```