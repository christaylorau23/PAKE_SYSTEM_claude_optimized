# 🚀 Production Deployment with Secure Secret Management

## Overview

This document provides step-by-step instructions for deploying PAKE System in production with AWS Secrets Manager for secure credential management.

## Architecture

```
Development Environment:
┌─────────────────┐    ┌──────────────┐
│   Application   │───▶│ Environment  │
│   (MCP Server)  │    │  Variables   │
└─────────────────┘    │   (.env)     │
                       └──────────────┘

Production Environment:
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Application   │───▶│    Secret    │───▶│  AWS Secrets   │
│   (MCP Server)  │    │   Manager    │    │    Manager     │
└─────────────────┘    │   (Python)   │    │   (Encrypted)  │
                       └──────────────┘    └─────────────────┘
```

## Prerequisites

### 1. AWS Account Setup
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]  
# Default region: us-east-1
# Default output format: json

# Verify access
aws sts get-caller-identity
```

### 2. Python Dependencies
```bash
cd D:\Projects\PAKE_SYSTEM
pip install -r configs/requirements.txt
```

## Deployment Steps

### Step 1: Create AWS Secrets
```bash
cd D:\Projects\PAKE_SYSTEM

# Create all required secrets in AWS Secrets Manager
python scripts/setup_aws_secrets.py --region us-east-1

# The script will output generated REDACTED_SECRETs - save these securely!
```

### Step 2: Update API Keys in AWS Console
1. Go to AWS Secrets Manager Console
2. Update the following secrets with your actual API keys:
   - `pake-system/api-keys/openai`
   - `pake-system/api-keys/anthropic`
   - `pake-system/api-keys/elevenlabs`

### Step 3: Configure IAM Permissions

**Option A: EC2 Instance Role (Recommended)**
```bash
# Attach the created policy to your EC2 instance role
aws iam attach-role-policy \
  --role-name YourEC2Role \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT:policy/PAKESystemSecretsAccess
```

**Option B: IAM User (Development/Testing)**
```bash
# Attach policy to IAM user
aws iam attach-user-policy \
  --user-name your-username \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT:policy/PAKESystemSecretsAccess
```

### Step 4: Set Production Environment Variables
```bash
# Set on your production server
export NODE_ENV=production
export AWS_REGION=us-east-1

# Optional: Specify different secret names
# export PAKE_SECRET_PREFIX=pake-system-prod
```

### Step 5: Start Production Services
```bash
cd D:\Projects\PAKE_SYSTEM

# Start MCP server (will automatically use AWS Secrets Manager)
python mcp-servers/base_server.py

# Or start with uvicorn for production
uvicorn mcp-servers.base_server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

## Verification

### Test Secret Loading
```bash
cd D:\Projects\PAKE_SYSTEM

# Test script to verify secret loading
python -c "
import asyncio
import sys
import os
sys.path.append('configs')
from secrets_manager import get_secret_manager

async def test():
    sm = get_secret_manager()
    print(f'Secret Manager: {sm.backend.name}')
    
    db_config = await sm.get_database_config()
    print(f'Database Host: {db_config[\"host\"]}')
    
    redis_config = await sm.get_redis_config()  
    print(f'Redis Host: {redis_config[\"host\"]}')
    
    openai_key = await sm.get_api_key('openai')
    print(f'OpenAI Key: {openai_key[:10]}...' if openai_key else 'Not configured')

asyncio.run(test())
"
```

### Test Application Connectivity
```bash
# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Check logs for successful secret loading
tail -f logs/application.log | grep -i "secret\|aws"
```

## Environment-Specific Configuration

### Development (.env file)
```bash
# .env file (git-ignored)
NODE_ENV=development
DB_PASSWORD=your_dev_REDACTED_SECRET
REDIS_PASSWORD=your_dev_redis_REDACTED_SECRET
OPENAI_API_KEY=sk-your_dev_key
```

### Staging (AWS Secrets Manager)
```bash
# Environment variables
export NODE_ENV=staging  
export AWS_REGION=us-east-1
export PAKE_SECRET_PREFIX=pake-system-staging
```

### Production (AWS Secrets Manager)
```bash
# Environment variables
export NODE_ENV=production
export AWS_REGION=us-east-1
export PAKE_SECRET_PREFIX=pake-system
```

## Security Best Practices

### 1. Secret Rotation
```bash
# Rotate database REDACTED_SECRET
aws secretsmanager update-secret \
  --secret-id pake-system/database \
  --secret-string '{"host":"localhost","port":5432,"database":"pake_system","user":"pake_user","REDACTED_SECRET":"NEW_STRONG_PASSWORD_HERE"}'

# Restart application to pick up new REDACTED_SECRET
sudo systemctl restart pake-mcp-server
```

### 2. Monitoring and Alerting
```bash
# Enable CloudTrail for secret access auditing
aws cloudtrail create-trail \
  --name pake-secrets-audit \
  --s3-bucket-name your-audit-bucket

# Set up CloudWatch alerts for secret access
aws logs create-log-group --log-group-name /aws/secretsmanager/pake-system
```

### 3. Least Privilege Access
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:pake-system/*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        },
        "IpAddress": {
          "aws:SourceIp": ["10.0.0.0/16", "192.168.1.0/24"]
        }
      }
    }
  ]
}
```

## Troubleshooting

### Common Issues

**1. AWS Credentials Not Found**
```bash
# Check AWS configuration
aws sts get-caller-identity
aws configure list

# For EC2, verify instance role
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

**2. Secret Not Found**
```bash
# List all secrets
aws secretsmanager list-secrets --query 'SecretList[?starts_with(Name, `pake-system`)].Name'

# Check specific secret
aws secretsmanager describe-secret --secret-id pake-system/database
```

**3. Permission Denied**
```bash
# Check IAM policy attachment
aws iam list-attached-role-policies --role-name YourEC2Role

# Test secret access manually
aws secretsmanager get-secret-value --secret-id pake-system/database
```

**4. Application Can't Connect to Database**
```bash
# Check secret manager logs
tail -f logs/application.log | grep -i "secret\|database"

# Test database connection manually
psql -h localhost -U pake_user -d pake_system
```

### Debug Mode
```bash
# Enable debug logging for secret manager
export PAKE_DEBUG_SECRETS=true

# Start application with debug output
python mcp-servers/base_server.py --log-level debug
```

## Cost Optimization

### AWS Secrets Manager Costs
- **$0.40 per secret per month**
- **$0.05 per 10,000 API calls**
- **Estimated monthly cost: ~$3-5 for PAKE system**

### Cost Reduction Strategies
```bash
# Use fewer secrets by combining related credentials
# Store multiple API keys in one JSON secret:
{
  "openai": "sk-your-key",
  "anthropic": "your-key", 
  "elevenlabs": "your-key"
}

# Cache secrets to reduce API calls (already implemented)
```

## Backup and Recovery

### Secret Backup
```bash
# Export secrets for backup (store securely!)
aws secretsmanager get-secret-value --secret-id pake-system/database \
  --query SecretString --output text > database-backup.json

# Backup to another region
aws secretsmanager replicate-secret-to-regions \
  --secret-id pake-system/database \
  --add-replica-regions Region=us-west-2
```

### Disaster Recovery
```bash
# Restore from backup
aws secretsmanager create-secret \
  --name pake-system/database \
  --secret-string file://database-backup.json

# Switch regions in emergency
export AWS_REGION=us-west-2
```

---

## Summary Checklist

✅ **AWS Secrets Created**
- [ ] Database credentials
- [ ] Redis credentials  
- [ ] Service REDACTED_SECRETs
- [ ] API keys updated

✅ **IAM Permissions**
- [ ] Policy created
- [ ] Role/User attached
- [ ] Permissions tested

✅ **Environment Configuration**
- [ ] NODE_ENV=production
- [ ] AWS_REGION set
- [ ] Application restarted

✅ **Security Measures**
- [ ] CloudTrail enabled
- [ ] Access monitoring configured
- [ ] Regular rotation scheduled
- [ ] Backup strategy implemented

✅ **Verification**  
- [ ] Secret loading tested
- [ ] Database connectivity verified
- [ ] Application endpoints responding
- [ ] Logs showing successful initialization

**🎉 Production deployment with secure secret management complete!**