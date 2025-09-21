# Compliance and Audit System for PAKE Disaster Recovery

This directory contains the compliance and audit trail components for the PAKE System disaster recovery infrastructure, providing enterprise-grade regulatory compliance, audit logging, and attestation capabilities.

## 📋 Overview

The compliance system ensures that all disaster recovery operations are properly logged, audited, and compliant with major regulatory frameworks including SOC 2, ISO 27001, GDPR, and FedRAMP.

### 🏗️ Architecture

```
compliance/
├── audit-config.yaml          # Signed, immutable audit logging
├── attestation-cron.yaml      # Automated compliance attestation
└── README.md                  # This documentation
```

## 🔒 Audit Logging System

### **File**: `audit-config.yaml`

Implements comprehensive audit logging with cryptographic signatures and immutable storage.

#### **Key Features**:

- **Digital Signatures**: All audit events signed with RS256 and X.509 certificates
- **Immutable Storage**: S3 Object Lock with 7-year retention for compliance
- **Chain Integrity**: Cryptographic hash linking prevents tampering
- **Multi-Source Collection**: Kubernetes events, webhook integrations, manual operations

#### **Event Types Tracked**:

```yaml
Backup Operations:
  - backup_started, backup_completed, backup_failed
  - backup_validated, backup_deleted

Restore Operations:
  - restore_initiated, restore_completed, restore_failed
  - restore_validated, restore_rollback

Failover Operations:
  - failover_triggered, failover_completed, failover_failed
  - dns_switched, traffic_redirected

Chaos Operations:
  - chaos_experiment_started, chaos_experiment_completed
  - chaos_rollback_triggered

Access Operations:
  - emergency_access_granted, privileged_command_executed
  - configuration_changed

Compliance Operations:
  - attestation_generated, audit_log_exported
  - compliance_check_performed, violation_detected
```

#### **Deployment Components**:

- **DR Audit Collector**: Real-time event collection and signing
- **Webhook Server**: External system integration (port 8080)
- **Dual Storage**: Primary and backup S3 buckets with cross-region replication

#### **Security Features**:

- **Certificate Management**: Automatic rotation every 90 days
- **Identity Verification**: Multi-method authentication tracking
- **Network Isolation**: Network policies and RBAC controls

## 📋 Compliance Attestation System

### **File**: `attestation-cron.yaml`

Automated generation of compliance attestation bundles with evidence collection.

#### **Attestation Schedules**:

```yaml
Monthly Attestation:
  - Schedule: 1st of each month at 2:00 AM UTC
  - Scope: 30-day reporting period
  - Retention: 2 years of history
  - Frameworks: SOC2, ISO27001, GDPR

Quarterly Attestation:
  - Schedule: 1st of quarter at 3:00 AM UTC
  - Scope: 90-day reporting period
  - Retention: 2 years of history
  - Enhanced metrics and analysis

Annual Attestation:
  - Schedule: January 1st at 4:00 AM UTC
  - Scope: 365-day comprehensive review
  - Retention: 10 years of history
  - All frameworks including FedRAMP
```

#### **Evidence Sources**:

- **Audit Logs**: Signed events with integrity validation
- **Backup Records**: Multi-service metadata with validation
- **Monitoring Metrics**: Prometheus queries across multiple time windows
- **Configuration State**: Kubernetes resources and network policies
- **Test Results**: Chaos engineering, backup validation, security scans

#### **Compliance Frameworks**:

**SOC 2 Type II**:

- CC6.1: Logical and physical access controls
- CC6.2: System software and applications
- CC6.3: Data access and transmission
- CC6.7: System backup and recovery
- CC7.1: System monitoring
- CC8.1: Change management controls

**ISO 27001**:

- A.12.3.1: Information backup
- A.12.6.1: Management of technical vulnerabilities
- A.16.1.1: Incident management responsibilities
- A.17.1.1: Planning information security continuity
- A.17.1.2: Implementing information security continuity

**GDPR**:

- Article 25: Data protection by design and by default
- Article 32: Security of processing
- Article 33: Notification of a personal data breach
- Article 35: Data protection impact assessment

**FedRAMP** (Annual only):

- CP-1: Contingency Planning Policy
- CP-2: Contingency Plan
- CP-6: Alternate Storage Site
- CP-9: Information System Backup
- CP-10: Information System Recovery

## 🚀 Deployment Guide

### Prerequisites

1. **AWS Credentials**: Configured for S3 access
2. **Signing Certificates**: X.509 certificates for audit log signing
3. **Prometheus**: For metrics collection and queries
4. **S3 Buckets**: Primary and backup audit log storage

### 1. Deploy Audit System

```bash
# Create namespace
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: compliance-system
  labels:
    compliance: enabled
EOF

# Generate signing certificates
openssl req -x509 -newkey rsa:4096 -keyout audit-signing.key -out audit-signing.crt -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=PAKE System/CN=audit-signing"

# Create certificate secret
kubectl create secret tls audit-signing-certs \
  --cert=audit-signing.crt \
  --key=audit-signing.key \
  -n compliance-system

# Deploy audit configuration
kubectl apply -f audit-config.yaml
```

### 2. Configure S3 Storage

```bash
# Create S3 buckets with Object Lock
aws s3 mb s3://pake-compliance-audit-logs --region us-east-1
aws s3 mb s3://pake-compliance-audit-logs-backup --region eu-west-1
aws s3 mb s3://pake-compliance-attestations --region us-east-1
aws s3 mb s3://pake-compliance-evidence --region us-east-1

# Enable Object Lock for immutable storage
aws s3api put-object-lock-configuration \
  --bucket pake-compliance-audit-logs \
  --object-lock-configuration ObjectLockEnabled=Enabled,Rule='{DefaultRetention={Mode=COMPLIANCE,Years=7}}'
```

### 3. Deploy Attestation System

```bash
# Deploy attestation configuration
kubectl apply -f attestation-cron.yaml

# Verify CronJob schedules
kubectl get cronjobs -n compliance-system
```

### 4. Verify Deployment

```bash
# Check audit collector status
kubectl get pods -n compliance-system -l app=dr-audit-collector

# Check audit logs collection
kubectl logs -n compliance-system -l app=dr-audit-collector --tail=50

# Verify attestation job execution
kubectl get jobs -n compliance-system -l app=compliance-attestation
```

## 📊 Monitoring and Metrics

### Key Metrics

- `audit_events_stored_total`: Total audit events collected
- `audit_signature_validation_rate`: Signature validation success rate
- `attestation_generation_status`: Attestation generation success/failure
- `attestation_generation_duration_seconds`: Time to generate attestations
- `backup_age_hours`: Backup freshness for compliance

### Alerts

- **Audit Log Gap**: No events stored despite DR operations
- **Signature Validation Failure**: High rate of invalid signatures
- **Missing Attestations**: Monthly/quarterly attestations overdue
- **Compliance Violations**: Framework-specific violations detected

## 🔍 Compliance Retrieval

### Monthly Attestation Retrieval

```bash
# Download latest monthly attestation
MONTH=$(date +%Y-%m)
aws s3 cp s3://pake-compliance-attestations/dr-attestations/$MONTH/ . --recursive

# Verify attestation signature
python3 verify-attestation-signature.py monthly-attestation.json
```

### Audit Log Retrieval for Incidents

```bash
# Retrieve audit logs for specific incident
INCIDENT_ID="INC-20240101-001"
START_TIME="2024-01-01T10:00:00Z"
END_TIME="2024-01-01T12:00:00Z"

aws s3 sync s3://pake-compliance-audit-logs/dr-audit-logs/ ./incident-logs/ \
  --exclude "*" \
  --include "*/$(date -d "$START_TIME" +%Y/%m/%d)/*"

# Filter logs by time range
python3 filter-incident-logs.py $INCIDENT_ID $START_TIME $END_TIME
```

### Framework-Specific Reports

```bash
# Extract SOC2 compliance report
python3 extract-framework-report.py monthly-attestation.json soc2

# Generate GDPR compliance summary
python3 extract-framework-report.py quarterly-attestation.json gdpr
```

## 🔧 Maintenance

### Certificate Rotation

```bash
# Generate new signing certificate
openssl req -x509 -newkey rsa:4096 -keyout new-audit-signing.key -out new-audit-signing.crt -days 365 -nodes

# Update certificate secret
kubectl create secret tls audit-signing-certs-new \
  --cert=new-audit-signing.crt \
  --key=new-audit-signing.key \
  -n compliance-system

# Rolling update audit collector
kubectl patch deployment dr-audit-collector -n compliance-system \
  -p '{"spec":{"template":{"spec":{"volumes":[{"name":"signing-certs","secret":{"secretName":"audit-signing-certs-new"}}]}}}}'
```

### Storage Lifecycle Management

```bash
# Configure S3 lifecycle for cost optimization
aws s3api put-bucket-lifecycle-configuration \
  --bucket pake-compliance-audit-logs \
  --lifecycle-configuration file://audit-logs-lifecycle.json
```

### Compliance Reporting

```bash
# Generate annual compliance report
kubectl create job manual-annual-attestation-$(date +%s) \
  --from=cronjob/compliance-attestation-annual -n compliance-system

# Monitor attestation generation
kubectl logs -f job/manual-annual-attestation-* -n compliance-system
```

## 🚨 Incident Response

### Compliance Violation Response

1. **Immediate Assessment**: Determine scope and impact
2. **Evidence Preservation**: Secure audit logs and attestations
3. **Notification**: Alert compliance team and legal counsel
4. **Investigation**: Use audit trail to reconstruct events
5. **Remediation**: Implement corrective measures
6. **Documentation**: Update compliance documentation

### Audit Log Integrity Verification

```bash
# Verify audit log chain integrity
python3 verify-audit-chain.py /path/to/audit-logs/

# Check signature validation across date range
python3 validate-signatures.py 2024-01-01 2024-01-31
```

## 📚 References

- **SOC 2 Controls**: [AICPA Trust Services Criteria](https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/aicpasoc2report.html)
- **ISO 27001**: [ISO/IEC 27001:2013](https://www.iso.org/standard/54534.html)
- **GDPR**: [General Data Protection Regulation](https://gdpr.eu/)
- **FedRAMP**: [Federal Risk and Authorization Management Program](https://www.fedramp.gov/)

## 🔗 Integration Points

- **Disaster Recovery Runbooks**: `/disaster-recovery/runbooks.md`
- **Monitoring Dashboards**: `/monitoring/grafana-dr-dashboards.json`
- **Alert Configuration**: `/monitoring/alerting-rules-compliance.yaml`
- **Backup Validation**: `/validation/restore-validate-job.yaml`
- **Chaos Testing**: `/chaos/README.md`

---

**Last Updated**: December 2024  
**Version**: 1.0  
**Maintainer**: PAKE System SRE Team
