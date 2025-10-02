# AWS OIDC Authentication Setup for PAKE System

This document provides step-by-step instructions for configuring secure AWS authentication using OpenID Connect (OIDC) for GitHub Actions.

## Overview

Instead of using long-lived IAM access keys (which is an anti-pattern), we use OIDC to allow GitHub Actions to assume AWS IAM roles using temporary credentials. This approach is more secure because:

- No long-lived credentials are stored
- Temporary credentials are automatically rotated
- Fine-grained permissions can be applied
- Audit trail is maintained

## Prerequisites

- AWS CLI configured with administrative permissions
- GitHub repository with admin access
- Understanding of IAM roles and policies

## Step 1: Configure AWS IAM OIDC Provider

### 1.1 Create OIDC Identity Provider

```bash
# Create the OIDC identity provider
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  --tags Key=Project,Value=PAKE-System Key=Environment,Value=All
```

**Note**: The thumbprint `6938fd4d98bab03faadb97b34396831e3780aea1` is GitHub's current thumbprint. Verify this is current at: https://docs.github.com/en/actions/deployment/security/hardening-your-deployments/about-security-hardening-with-openid-connect

### 1.2 Verify OIDC Provider

```bash
# List OIDC providers to verify creation
aws iam list-open-id-connect-providers
```

## Step 2: Create IAM Role for Deployment

### 2.1 Create Trust Policy

Create a file `trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/YOUR_REPO_NAME:*"
        }
      }
    }
  ]
}
```

**Replace**:
- `YOUR_ACCOUNT_ID` with your AWS account ID
- `YOUR_GITHUB_ORG` with your GitHub organization name
- `YOUR_REPO_NAME` with your repository name

### 2.2 Create IAM Role

```bash
# Create the IAM role
aws iam create-role \
  --role-name PAKE-System-GitHubActions-Role \
  --assume-role-policy-document file://trust-policy.json \
  --description "Role for PAKE System GitHub Actions deployment" \
  --tags Key=Project,Value=PAKE-System Key=Environment,Value=All
```

### 2.3 Create Least-Privilege Policy

Create a file `deployment-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::pake-system-*",
        "arn:aws:s3:::pake-system-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath"
      ],
      "Resource": [
        "arn:aws:ssm:*:*:parameter/pake-system/*"
      ]
    }
  ]
}
```

### 2.4 Attach Policy to Role

```bash
# Create the policy
aws iam create-policy \
  --policy-name PAKE-System-Deployment-Policy \
  --policy-document file://deployment-policy.json \
  --description "Least privilege policy for PAKE System deployment"

# Attach policy to role
aws iam attach-role-policy \
  --role-name PAKE-System-GitHubActions-Role \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/PAKE-System-Deployment-Policy
```

## Step 3: Configure GitHub Secrets

### 3.1 Required Secrets

Add these secrets to your GitHub repository:

1. **AWS_ROLE_ARN**: The ARN of the IAM role created above
   ```
   arn:aws:iam::YOUR_ACCOUNT_ID:role/PAKE-System-GitHubActions-Role
   ```

2. **AWS_REGION**: The AWS region for your resources
   ```
   us-west-2
   ```

### 3.2 Optional Secrets

- **KUBE_CONFIG_STAGING**: Base64 encoded kubeconfig for staging
- **KUBE_CONFIG_PRODUCTION**: Base64 encoded kubeconfig for production
- **SLACK_WEBHOOK_URL**: For deployment notifications

## Step 4: Test the Configuration

### 4.1 Create Test Workflow

Create `.github/workflows/test-aws-auth.yml`:

```yaml
name: Test AWS Authentication

on:
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  test-auth:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION || 'us-west-2' }}
          role-session-name: test-authentication
      
      - name: Test AWS access
        run: |
          aws sts get-caller-identity
          aws ecr describe-repositories --region ${{ secrets.AWS_REGION || 'us-west-2' }} || echo "ECR access test completed"
```

### 4.2 Run Test

1. Go to Actions tab in GitHub
2. Select "Test AWS Authentication" workflow
3. Click "Run workflow"
4. Verify the job completes successfully

## Step 5: Environment-Specific Configuration

### 5.1 Staging Environment

For staging deployments, you may want to restrict the role further:

```json
{
  "StringLike": {
    "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/YOUR_REPO_NAME:ref:refs/heads/develop"
  }
}
```

### 5.2 Production Environment

For production deployments, require manual approval and restrict to main branch:

```json
{
  "StringLike": {
    "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/YOUR_REPO_NAME:ref:refs/heads/main"
  }
}
```

## Troubleshooting

### Common Issues

1. **"Could not load credentials"**
   - Verify `AWS_ROLE_ARN` secret is set correctly
   - Check that the OIDC provider is configured
   - Ensure the trust policy allows your repository

2. **"Access Denied"**
   - Verify the IAM policy has the required permissions
   - Check that the role is attached to the policy
   - Ensure the AWS region is correct

3. **"Invalid token"**
   - Verify the OIDC provider thumbprint is current
   - Check that the audience is `sts.amazonaws.com`
   - Ensure the subject matches your repository

### Debug Commands

```bash
# Check OIDC provider
aws iam get-open-id-connect-provider --open-id-connect-provider-arn arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com

# Check role trust policy
aws iam get-role --role-name PAKE-System-GitHubActions-Role

# Check attached policies
aws iam list-attached-role-policies --role-name PAKE-System-GitHubActions-Role
```

## Security Best Practices

1. **Least Privilege**: Only grant the minimum permissions required
2. **Environment Separation**: Use different roles for different environments
3. **Branch Restrictions**: Limit role assumption to specific branches
4. **Regular Audits**: Review and rotate policies regularly
5. **Monitoring**: Enable CloudTrail for audit logging

## Next Steps

After completing this setup:

1. Test the authentication with the test workflow
2. Update your deployment workflows to use the new authentication
3. Remove any old long-lived credentials from GitHub secrets
4. Monitor the deployment logs for any permission issues
5. Document any additional permissions needed for your specific use case

## References

- [GitHub Actions OIDC Documentation](https://docs.github.com/en/actions/deployment/security/hardening-your-deployments/about-security-hardening-with-openid-connect)
- [AWS IAM OIDC Documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [AWS Actions Configure Credentials](https://github.com/aws-actions/configure-aws-credentials)
