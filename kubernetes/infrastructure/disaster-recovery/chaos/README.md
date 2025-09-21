# Chaos Engineering Framework for PAKE System

## 🎯 Overview

This directory contains a comprehensive chaos engineering framework designed to validate the resilience and disaster recovery capabilities of the PAKE System. The framework implements automated chaos experiments that test system behavior under various failure conditions, ensuring our disaster recovery mechanisms work as expected.

## 🏗️ Architecture

### Core Components

```
chaos/
├── random-pod-kill-cron.yaml      # Pod failure testing
├── network-partition-job.yaml     # Network resilience testing
├── resource-exhaustion-job.yaml   # Resource stress testing
├── dependency-failure-job.yaml    # External dependency failure testing
├── region-failover-drill.yaml     # Multi-region failover testing
└── README.md                      # This documentation
```

### Chaos Testing Schedule

| Experiment Type         | Schedule       | Duration | Intensity                | Auto-Rollback |
| ----------------------- | -------------- | -------- | ------------------------ | ------------- |
| **Pod Kill**            | Monthly (15th) | 10-15m   | 25-50% pods              | ✅            |
| **Network Partition**   | Quarterly      | 5-15m    | Selective services       | ✅            |
| **Resource Exhaustion** | Quarterly      | 8-15m    | 60-95% resources         | ✅            |
| **Dependency Failure**  | Quarterly      | 10-20m   | Complete service failure | ✅            |
| **Region Failover**     | Annual         | 30m      | Full region isolation    | ✅            |

## 🧪 Experiment Types

### 1. Random Pod Kill Chaos

**Purpose**: Tests system resilience to unexpected pod failures and validates Kubernetes self-healing mechanisms.

**Targets**:

- API services (25-50% pods)
- AI workers (20-40% pods)
- Database replicas (50-100% pods)

**Safety Measures**:

- Never kills primary database
- Maintains minimum healthy replicas
- Excludes critical system pods (etcd, kube-apiserver)
- Pre-flight health checks

**Expected Behavior**:

- Kubernetes automatically restarts killed pods
- Load balancing distributes traffic to healthy pods
- No service disruption for end users
- Recovery within 2-5 minutes

### 2. Network Partition Testing

**Purpose**: Validates service resilience to network connectivity issues and inter-service communication failures.

**Scenarios**:

- API ↔ Database partition (3-5m)
- AI Workers ↔ Redis partition (2-3m)
- Cross-region latency injection (4-7m)

**Implementation**:

- Uses Kubernetes NetworkPolicies for controlled isolation
- Simulates both unidirectional and bidirectional partitions
- Injects realistic network latency and packet loss

**Expected Behavior**:

- Services gracefully handle connection timeouts
- Circuit breakers activate to prevent cascading failures
- Retry mechanisms with exponential backoff
- Fallback to cached data when available

### 3. Resource Exhaustion Testing

**Purpose**: Tests system behavior under extreme resource pressure (CPU, memory, disk, network).

**Stress Scenarios**:

- CPU stress: 80-95% utilization
- Memory pressure: 70-90% usage
- Disk I/O saturation: 60-80% capacity
- Network bandwidth limiting

**Implementation**:

- Uses stress-ng containers for realistic resource pressure
- Targets specific nodes where services run
- Gradual ramp-up to avoid sudden system shock

**Expected Behavior**:

- Kubernetes resource limits prevent noisy neighbor issues
- Horizontal Pod Autoscaler (HPA) scales services under load
- Quality of Service (QoS) classes prioritize critical workloads
- Performance degradation is graceful, not catastrophic

### 4. Dependency Failure Testing

**Purpose**: Validates fallback mechanisms when external dependencies become unavailable.

**Dependencies Tested**:

- PostgreSQL primary database
- Redis cache cluster
- ChromaDB vector database
- External AI APIs (OpenAI, Anthropic)
- S3 storage services

**Failure Modes**:

- Complete service unavailability
- HTTP error injection (503, 504, 429)
- Network-level blocking
- Timeout simulation

**Expected Behavior**:

- Database replica promotion for PostgreSQL failures
- Cache bypass mechanisms for Redis failures
- Fallback search for vector database failures
- Local model usage for external AI API failures
- Local caching and delayed upload for storage failures

### 5. Region Failover Drill

**Purpose**: Tests complete regional disaster recovery and multi-region failover capabilities.

**Failover Scenarios**:

- Primary region (us-east-1) complete failure → EU failover
- Secondary region (eu-west-1) failure → AP failover
- Primary region recovery and traffic restoration

**Components Tested**:

- DNS failover mechanisms
- Database replica promotion
- Cross-region data synchronization
- Traffic routing and load balancing
- Data consistency verification

**Expected Behavior**:

- RTO < 15 minutes for complete region failover
- RPO < 5 minutes (minimal data loss)
- Automatic DNS updates for traffic routing
- Successful database promotion in target region
- Full functionality restoration in backup region

## 🔒 Safety Framework

### Multi-Layer Protection

1. **Pre-Flight Checks**
   - System health validation
   - Resource availability confirmation
   - Dependency connectivity verification
   - Minimum replica count validation

2. **Runtime Safeguards**
   - Protected service exclusions
   - Resource utilization limits
   - Blast radius containment
   - Real-time monitoring

3. **Auto-Rollback Mechanisms**
   - Automatic cleanup after experiment duration
   - Emergency stop capabilities
   - State restoration procedures
   - Orphaned resource cleanup

### Protected Resources

```yaml
protected_services:
  - 'kube-system/kube-dns'
  - 'kube-system/kube-apiserver'
  - 'kube-system/kube-scheduler'
  - 'kube-system/kube-controller-manager'
  - 'monitoring/prometheus'
  - 'monitoring/grafana'
```

### Safety Constraints

| Component        | Constraint                 | Value                |
| ---------------- | -------------------------- | -------------------- |
| **Pod Kill**     | Min healthy replicas       | API: 2, AI: 1, DB: 1 |
| **Network**      | Max partition duration     | 10 minutes           |
| **Resources**    | Max CPU usage              | 95%                  |
| **Dependencies** | Max error rate during test | 25%                  |
| **Regional**     | Min healthy regions        | 1                    |

## 📊 Monitoring & Observability

### Prometheus Metrics

All chaos experiments emit comprehensive metrics to Prometheus:

```
# Experiment Status
chaos_experiment_status{experiment_type, status}
chaos_experiment_duration_seconds{experiment_type}

# Pod Kill Metrics
chaos_pods_killed_total{namespace, app, scenario}
chaos_pod_kill_failures_total{pod_name}

# Network Partition Metrics
chaos_network_partitions_created_total{scenario, partition_type}
chaos_partition_health_status{service}

# Resource Exhaustion Metrics
chaos_stress_pods_created_total{scenario, resource_type}
chaos_stress_health_status{service}

# Dependency Failure Metrics
chaos_dependency_failures_created_total{scenario, failure_type}
chaos_fallback_verification_status{scenario, check_type}

# Regional Failover Metrics
chaos_region_isolation_status{region, status}
chaos_database_promotion_status{region, service}
chaos_traffic_redirection_status{source_region, target_region}
```

### Alerting Rules

Critical alerts are automatically triggered for:

- Experiment failures or timeouts
- Safety constraint violations
- Auto-rollback failures
- Post-experiment health issues
- RTO/RPO target breaches

### Dashboards

Grafana dashboards provide real-time visibility into:

- Experiment execution status
- System health during chaos
- Recovery time metrics
- Success/failure rates over time
- Trend analysis and improvement tracking

## 🚀 Usage Guide

### Prerequisites

1. **RBAC Setup**

   ```bash
   kubectl apply -f random-pod-kill-cron.yaml  # Creates ServiceAccount
   ```

2. **Namespace Creation**

   ```bash
   kubectl create namespace chaos-testing
   kubectl label namespace chaos-testing chaos-engineering=enabled
   ```

3. **Secret Configuration**
   ```bash
   kubectl create secret generic aws-credentials \
     --from-literal=access-key-id=<key> \
     --from-literal=secret-access-key=<secret> \
     -n chaos-testing
   ```

### Manual Experiment Execution

#### Run Pod Kill Test (Dry Run)

```bash
kubectl create job chaos-pod-kill-manual \
  --from=cronjob/chaos-pod-kill-monthly \
  -n chaos-testing

# Override for dry run
kubectl set env job/chaos-pod-kill-manual \
  DRY_RUN=true -n chaos-testing
```

#### Run Network Partition Test

```bash
kubectl apply -f - <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: chaos-network-partition-manual
  namespace: chaos-testing
spec:
  template:
    spec:
      serviceAccountName: chaos-engineering
      restartPolicy: OnFailure
      containers:
      - name: network-partition
        image: python:3.11-alpine
        command: ["/bin/sh", "-c"]
        args: ["pip install kubernetes pyyaml aiohttp requests && python /scripts/network-partition.py"]
        env:
        - name: CONFIG_PATH
          value: "/etc/config/config.yaml"
        volumeMounts:
        - name: config
          mountPath: /etc/config
        - name: scripts
          mountPath: /scripts
      volumes:
      - name: config
        configMap:
          name: chaos-network-partition-config
      - name: scripts
        configMap:
          name: chaos-network-partition-config
          defaultMode: 0755
EOF
```

#### Run Resource Exhaustion Test

```bash
kubectl create job chaos-resource-exhaustion-manual \
  --from=job/chaos-resource-exhaustion-quarterly \
  -n chaos-testing
```

#### Run Dependency Failure Test

```bash
kubectl create job chaos-dependency-failure-manual \
  --from=job/chaos-dependency-failure-quarterly \
  -n chaos-testing
```

#### Run Region Failover Drill

```bash
kubectl create job chaos-region-failover-manual \
  --from=job/chaos-region-failover-annual \
  -n chaos-testing
```

### Monitoring Execution

```bash
# Watch job status
kubectl get jobs -n chaos-testing -w

# View experiment logs
kubectl logs -f job/chaos-pod-kill-manual -n chaos-testing

# Check experiment metrics
curl -s http://prometheus-pushgateway.monitoring.svc.cluster.local:9091/api/v1/metrics | grep chaos_

# View current health status
kubectl get pods --all-namespaces | grep -E "(pake-api|pake-ai|database)"
```

### Emergency Stop Procedures

#### Stop Running Experiment

```bash
# Delete the job to stop experiment
kubectl delete job <experiment-job-name> -n chaos-testing

# Force cleanup of any remaining artifacts
kubectl delete networkpolicies -l chaos-experiment=<experiment-id> --all-namespaces
kubectl delete pods -l chaos-experiment=<experiment-id> --all-namespaces
```

#### Manual Recovery Steps

1. **Restore Network Connectivity**

   ```bash
   kubectl delete networkpolicies -l chaos-type=network-partition --all-namespaces
   kubectl delete networkpolicies -l chaos-type=dependency-failure --all-namespaces
   ```

2. **Scale Services Back Up**

   ```bash
   kubectl scale deployment pake-api --replicas=3 -n pake-api
   kubectl scale deployment pake-ai-worker --replicas=2 -n pake-ai
   kubectl scale statefulset pake-postgresql-primary --replicas=1 -n database
   ```

3. **Remove Stress Pods**

   ```bash
   kubectl delete pods -l chaos-type=resource-exhaustion --all-namespaces
   ```

4. **Verify System Health**
   ```bash
   kubectl get pods --all-namespaces | grep -v Running
   kubectl get services --all-namespaces
   ```

## 🔄 Rollback Procedures

### Automatic Rollback

All experiments include automatic rollback mechanisms:

1. **Duration-Based Rollback**
   - Experiments automatically clean up after configured duration
   - Timeout-based emergency stops for runaway experiments

2. **Health-Based Rollback**
   - Experiments monitor system health continuously
   - Auto-abort if critical thresholds are breached

3. **Manual Rollback Triggers**
   - Emergency stop via job deletion
   - Manual cleanup scripts for artifact removal

### Manual Rollback Scripts

#### Complete System Rollback

```bash
#!/bin/bash
# complete-rollback.sh

echo "Starting complete chaos experiment rollback..."

# Remove all chaos-related network policies
kubectl delete networkpolicies -l "chaos-experiment" --all-namespaces --ignore-not-found=true

# Remove all stress testing pods
kubectl delete pods -l "chaos-type" --all-namespaces --ignore-not-found=true

# Scale services back to normal
kubectl scale deployment pake-api --replicas=3 -n pake-api
kubectl scale deployment pake-ai-worker --replicas=2 -n pake-ai
kubectl scale statefulset pake-postgresql-primary --replicas=1 -n database
kubectl scale statefulset pake-postgresql-replica-eu --replicas=1 -n database
kubectl scale statefulset pake-postgresql-replica-ap --replicas=1 -n database

# Remove chaos labels from services
kubectl label services -l "chaos-promoted" chaos-promoted- --all-namespaces
kubectl label services -l "promotion-time" promotion-time- --all-namespaces

# Verify cleanup
echo "Verifying system health..."
kubectl get pods --all-namespaces | grep -v Running | grep -v Completed

echo "Rollback completed!"
```

#### Network Rollback Only

```bash
#!/bin/bash
# network-rollback.sh

echo "Rolling back network changes..."

# Remove network partition policies
kubectl delete networkpolicies -l chaos-type=network-partition --all-namespaces --ignore-not-found=true

# Remove dependency failure policies
kubectl delete networkpolicies -l chaos-type=dependency-failure --all-namespaces --ignore-not-found=true

# Remove region failover policies
kubectl delete networkpolicies -l chaos-type=region-failover --all-namespaces --ignore-not-found=true

echo "Network rollback completed!"
```

#### Resource Rollback Only

```bash
#!/bin/bash
# resource-rollback.sh

echo "Rolling back resource changes..."

# Remove all stress testing pods
kubectl delete pods -l chaos-type=resource-exhaustion --all-namespaces --ignore-not-found=true

# Wait for cleanup
sleep 10

# Verify no stress pods remain
kubectl get pods -l chaos-type=resource-exhaustion --all-namespaces

echo "Resource rollback completed!"
```

## 📈 Success Criteria

### Experiment Success Metrics

| Experiment              | Success Criteria                                                                                                                      |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Pod Kill**            | ✅ System recovers within 5 minutes<br/>✅ No user-visible downtime<br/>✅ All services return to healthy state                       |
| **Network Partition**   | ✅ Circuit breakers activate correctly<br/>✅ Fallback mechanisms engage<br/>✅ Recovery within 2 minutes of connectivity restoration |
| **Resource Exhaustion** | ✅ Performance degrades gracefully<br/>✅ No service crashes<br/>✅ Auto-scaling activates appropriately                              |
| **Dependency Failure**  | ✅ Fallback systems activate within 30s<br/>✅ Degraded mode maintains core functionality<br/>✅ Data consistency preserved           |
| **Region Failover**     | ✅ RTO < 15 minutes<br/>✅ RPO < 5 minutes<br/>✅ Complete functionality in backup region                                             |

### Key Performance Indicators (KPIs)

- **Mean Time To Recovery (MTTR)**: < 5 minutes for single-component failures
- **Recovery Success Rate**: > 95% for all automated recovery attempts
- **Data Loss**: < 5 minutes of transactions during worst-case scenarios
- **User Impact**: < 1% error rate increase during chaos experiments
- **False Positive Rate**: < 5% for monitoring alerts during experiments

## 🔍 Troubleshooting

### Common Issues

#### 1. Experiment Stuck or Not Starting

**Symptoms**: Job remains in Pending state

```bash
kubectl describe job <job-name> -n chaos-testing
```

**Common Causes**:

- Insufficient RBAC permissions
- Missing ConfigMaps or Secrets
- Node resource constraints
- Image pull issues

**Solutions**:

```bash
# Check RBAC
kubectl auth can-i create networkpolicies --as=system:serviceaccount:chaos-testing:chaos-engineering

# Verify ConfigMaps
kubectl get configmaps -n chaos-testing

# Check node resources
kubectl describe nodes
```

#### 2. Experiments Not Cleaning Up

**Symptoms**: NetworkPolicies or stress pods remain after experiment

```bash
kubectl get networkpolicies -l chaos-experiment --all-namespaces
kubectl get pods -l chaos-type --all-namespaces
```

**Solutions**:

```bash
# Manual cleanup
kubectl delete networkpolicies -l chaos-experiment --all-namespaces
kubectl delete pods -l chaos-type --all-namespaces

# Check for finalizers
kubectl get networkpolicies <policy-name> -o yaml | grep finalizers
```

#### 3. Health Checks Failing

**Symptoms**: Pre-flight health checks prevent experiment execution

**Investigation**:

```bash
# Check service status
kubectl get services --all-namespaces
kubectl get endpoints --all-namespaces

# Test connectivity
kubectl run test-pod --image=busybox --rm -it -- /bin/sh
wget -O- http://pake-api.pake-api.svc.cluster.local:8080/health
```

**Solutions**:

- Wait for services to become healthy
- Check DNS resolution issues
- Verify service mesh configuration

#### 4. Metrics Not Appearing

**Symptoms**: Prometheus metrics missing for chaos experiments

**Investigation**:

```bash
# Check pushgateway
curl http://prometheus-pushgateway.monitoring.svc.cluster.local:9091/api/v1/metrics

# Verify network connectivity from chaos pods
kubectl logs <chaos-pod> -n chaos-testing
```

**Solutions**:

- Verify pushgateway service is running
- Check network policies blocking metrics
- Validate pushgateway configuration

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
# Set debug environment variable
kubectl set env job/<job-name> DEBUG=true -n chaos-testing

# View detailed logs
kubectl logs -f job/<job-name> -n chaos-testing | grep DEBUG
```

### Validation Scripts

#### Health Check Script

```bash
#!/bin/bash
# health-check.sh

echo "=== PAKE System Health Check ==="

# Check API services
echo "Checking API services..."
kubectl get pods -n pake-api
curl -f http://pake-api.pake-api.svc.cluster.local:8080/health || echo "API health check failed"

# Check AI services
echo "Checking AI services..."
kubectl get pods -n pake-ai
curl -f http://pake-ai.pake-ai.svc.cluster.local:8080/health || echo "AI health check failed"

# Check databases
echo "Checking databases..."
kubectl get pods -n database
kubectl exec pake-postgresql-primary-0 -n database -- pg_isready -U postgres || echo "PostgreSQL health check failed"

# Check monitoring
echo "Checking monitoring..."
kubectl get pods -n monitoring
curl -f http://prometheus.monitoring.svc.cluster.local:9090/-/healthy || echo "Prometheus health check failed"

echo "Health check completed!"
```

## 📚 References

### Chaos Engineering Best Practices

1. **Principles of Chaos Engineering**
   - Start with a hypothesis about steady state behavior
   - Introduce variables that reflect real world events
   - Run experiments in production
   - Automate experiments to run continuously
   - Minimize blast radius

2. **Netflix Chaos Monkey Principles**
   - Build systems that tolerate failure
   - Test in production with real traffic
   - Start small and gradually increase complexity
   - Learn from failures and improve

3. **Google SRE Practices**
   - Error budgets for acceptable failure rates
   - Canary deployments for gradual rollouts
   - Disaster recovery testing (DiRT)
   - Comprehensive monitoring and alerting

### External Tools Integration

- **Chaos Mesh**: Kubernetes-native chaos engineering platform
- **Litmus**: Cloud-native chaos engineering framework
- **Gremlin**: Commercial chaos engineering platform
- **Pumba**: Chaos testing for Docker containers

### Documentation Links

- [Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Prometheus Pushgateway](https://github.com/prometheus/pushgateway)
- [Chaos Engineering Book](https://www.oreilly.com/library/view/chaos-engineering/9781491988459/)
- [SRE Workbook](https://sre.google/workbook/table-of-contents/)

---

## 🎯 Conclusion

This chaos engineering framework provides comprehensive testing of the PAKE System's resilience and disaster recovery capabilities. By regularly executing these experiments, we ensure our system can handle real-world failures gracefully and recover quickly.

The framework is designed with safety as the top priority, implementing multiple layers of protection and automatic rollback mechanisms. All experiments are thoroughly monitored and provide detailed metrics for continuous improvement.

For questions or issues, please refer to the troubleshooting section or contact the Platform Engineering team.

**Remember**: Chaos engineering is not about breaking things - it's about building confidence in our system's ability to handle the unexpected! 🛡️
