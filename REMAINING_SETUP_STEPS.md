# 🔧 PAKE System - Remaining Setup Steps

## ✅ Completed Security Fixes

All code-level security issues have been resolved:
- ✅ PAKE_WEAK_PASSWORD: 0 instances in source code (only in .security_backup files)
- ✅ Unsafe pickle usage: 0 instances (safe wrapper exists)
- ✅ MD5 usage: 0 instances in source code (only in tests/docs)
- ✅ Terraform RDS configuration: `manage_master_user_password = false` set
- ✅ GitHub Actions OIDC: Properly configured in workflows

## 🚀 Remaining Manual Steps

### 1. AWS IAM OIDC Setup

**Required Actions:**
```bash
# Run the automated setup script
./scripts/setup-aws-oidc.sh
```

**Manual Steps After Script:**
1. **Create IAM OIDC Identity Provider** (if script fails):
   ```bash
   aws iam create-open-id-connect-provider \
     --url https://token.actions.githubusercontent.com \
     --client-id-list sts.amazonaws.com \
     --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
     --tags Key=Project,Value=PAKE-System
   ```

2. **Create IAM Role** with trust policy for GitHub Actions
3. **Create IAM Policy** with least privilege permissions for deployment

### 2. GitHub Repository Secrets

**Required Secrets to Add:**
```bash
# AWS Configuration
AWS_ROLE_ARN=arn:aws:iam::YOUR_ACCOUNT_ID:role/PAKE-System-GitHubActions-Role
AWS_REGION=us-west-2
AWS_ACCOUNT_ID=YOUR_ACCOUNT_ID

# Database
DATABASE_PASSWORD=your-secure-database-password

# Container Registry
DOCKER_USERNAME=your-docker-username
DOCKER_PASSWORD=your-docker-password

# Kubernetes (for GitOps deployment)
KUBE_CONFIG_STAGING=base64-encoded-kubeconfig-for-staging
KUBE_CONFIG_PRODUCTION=base64-encoded-kubeconfig-for-production

# ArgoCD (for GitOps)
ARGOCD_PASSWORD=your-argocd-admin-password

# Notifications
SLACK_WEBHOOK_URL=your-slack-webhook-url

# Security Tools (optional)
GITLEAKS_LICENSE=your-gitleaks-license
```

### 3. Terraform State Backend Configuration

**Current Status:** Backend is commented out in `infra/terraform/main.tf:21-25`

**Required Actions:**
1. **Create S3 bucket for Terraform state:**
   ```bash
   aws s3 mb s3://pake-system-terraform-state --region us-west-2
   aws s3api put-bucket-versioning --bucket pake-system-terraform-state --versioning-configuration Status=Enabled
   aws s3api put-bucket-encryption --bucket pake-system-terraform-state --server-side-encryption-configuration '{
     "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
   }'
   ```

2. **Create DynamoDB table for state locking:**
   ```bash
   aws dynamodb create-table \
     --table-name pake-system-terraform-locks \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
   ```

3. **Update Terraform configuration:**
   ```hcl
   backend "s3" {
     bucket = "pake-system-terraform-state"
     key    = "infrastructure/terraform.tfstate"
     region = "us-west-2"
     dynamodb_table = "pake-system-terraform-locks"
     encrypt = true
   }
   ```

### 4. Test CI/CD Pipeline

**Test AWS Authentication:**
1. Go to GitHub Actions tab
2. Run "Test AWS Authentication" workflow
3. Verify all steps complete successfully

**Test Terraform Pipeline:**
1. Make a small change to `infra/terraform/main.tf`
2. Push to `develop` branch
3. Verify terraform-validate and terraform-plan jobs complete

### 5. Environment Setup (Local Development)

**Database Setup:**
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE pake_db;
CREATE USER pakeuser WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE pake_db TO pakeuser;
ALTER USER pakeuser CREATEDB;
\q
```

**Redis Setup:**
```bash
# Install Redis
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**Python Environment:**
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head
```

**Node.js Environment:**
```bash
# Install Node.js 22
nvm install 22
nvm use 22

# Install dependencies
npm install
```

## 🎯 Quick Start Commands

**Start Development Servers:**
```bash
# Terminal 1: Bridge Server
npm run start:bridge

# Terminal 2: Python Backend
source .venv/bin/activate
python -m uvicorn src.main:app --reload --port 8000

# Terminal 3: Frontend (if applicable)
npm run dev
```

**Health Checks:**
```bash
# Test APIs
python scripts/test_apis_simple.py

# Check services
curl http://localhost:8000/health
curl http://localhost:3001/health
```

## 🔍 Verification Checklist

- [ ] AWS OIDC provider created
- [ ] IAM role and policy configured
- [ ] GitHub secrets added
- [ ] Terraform state backend configured
- [ ] AWS authentication test passes
- [ ] Terraform pipeline test passes
- [ ] Local development environment running
- [ ] Database migrations completed
- [ ] All health checks passing

## 📞 Support

If you encounter issues:
1. Check GitHub Actions logs
2. Review AWS CloudTrail logs
3. Verify IAM permissions
4. Check Terraform state file
5. Review application logs

## 🚨 Security Notes

- Never commit secrets to version control
- Use environment variables for all sensitive data
- Regularly rotate AWS credentials
- Monitor CloudTrail for suspicious activity
- Keep dependencies updated
