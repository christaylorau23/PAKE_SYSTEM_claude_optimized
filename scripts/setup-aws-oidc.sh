#!/bin/bash

# PAKE System - AWS OIDC Setup Script
# This script automates the setup of AWS OIDC authentication for GitHub Actions

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ROLE_NAME="PAKE-System-GitHubActions-Role"
POLICY_NAME="PAKE-System-Deployment-Policy"
OIDC_PROVIDER_URL="https://token.actions.githubusercontent.com"
OIDC_AUDIENCE="sts.amazonaws.com"
OIDC_THUMBPRINT="6938fd4d98bab03faadb97b34396831e3780aea1"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if AWS CLI is configured
check_aws_cli() {
    print_status "Checking AWS CLI configuration..."

    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured or credentials are invalid."
        print_status "Please run 'aws configure' to set up your credentials."
        exit 1
    fi

    print_success "AWS CLI is configured and working."
}

# Function to get AWS account ID
get_aws_account_id() {
    aws sts get-caller-identity --query Account --output text
}

# Function to check if OIDC provider already exists
check_oidc_provider() {
    local account_id=$1
    local provider_arn="arn:aws:iam::${account_id}:oidc-provider/token.actions.githubusercontent.com"

    if aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$provider_arn" &> /dev/null; then
        print_warning "OIDC provider already exists: $provider_arn"
        return 0
    else
        return 1
    fi
}

# Function to create OIDC provider
create_oidc_provider() {
    print_status "Creating OIDC identity provider..."

    aws iam create-open-id-connect-provider \
        --url "$OIDC_PROVIDER_URL" \
        --client-id-list "$OIDC_AUDIENCE" \
        --thumbprint-list "$OIDC_THUMBPRINT" \
        --tags Key=Project,Value=PAKE-System Key=Environment,Value=All

    print_success "OIDC identity provider created successfully."
}

# Function to create trust policy
create_trust_policy() {
    local account_id=$1
    local github_org=$2
    local repo_name=$3

    print_status "Creating trust policy..."

    cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${account_id}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${github_org}/${repo_name}:*"
        }
      }
    }
  ]
}
EOF

    print_success "Trust policy created: trust-policy.json"
}

# Function to create deployment policy
create_deployment_policy() {
    print_status "Creating deployment policy..."

    cat > deployment-policy.json << EOF
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
EOF

    print_success "Deployment policy created: deployment-policy.json"
}

# Function to create IAM role
create_iam_role() {
    print_status "Creating IAM role: $ROLE_NAME"

    aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document file://trust-policy.json \
        --description "Role for PAKE System GitHub Actions deployment" \
        --tags Key=Project,Value=PAKE-System Key=Environment,Value=All

    print_success "IAM role created: $ROLE_NAME"
}

# Function to create and attach policy
create_and_attach_policy() {
    local account_id=$1

    print_status "Creating IAM policy: $POLICY_NAME"

    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document file://deployment-policy.json \
        --description "Least privilege policy for PAKE System deployment"

    print_success "IAM policy created: $POLICY_NAME"

    print_status "Attaching policy to role..."

    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::${account_id}:policy/${POLICY_NAME}"

    print_success "Policy attached to role successfully."
}

# Function to clean up temporary files
cleanup() {
    print_status "Cleaning up temporary files..."
    rm -f trust-policy.json deployment-policy.json
    print_success "Cleanup completed."
}

# Function to display next steps
display_next_steps() {
    local account_id=$1

    echo ""
    print_success "AWS OIDC setup completed successfully!"
    echo ""
    print_status "Next steps:"
    echo "1. Add the following secrets to your GitHub repository:"
    echo "   - AWS_ROLE_ARN: arn:aws:iam::${account_id}:role/${ROLE_NAME}"
    echo "   - AWS_REGION: us-west-2 (or your preferred region)"
    echo ""
    echo "2. Test the configuration by running the test workflow:"
    echo "   - Go to Actions tab in GitHub"
    echo "   - Run the 'Test AWS Authentication' workflow"
    echo ""
    echo "3. Update your deployment workflows to use the new authentication"
    echo ""
    print_warning "Remember to remove any old long-lived credentials from GitHub secrets!"
}

# Main function
main() {
    echo "PAKE System - AWS OIDC Setup Script"
    echo "===================================="
    echo ""

    # Check if required arguments are provided
    if [ $# -ne 2 ]; then
        print_error "Usage: $0 <github-org> <repo-name>"
        print_status "Example: $0 myorg pake-system"
        exit 1
    fi

    local github_org=$1
    local repo_name=$2

    print_status "Setting up AWS OIDC for repository: ${github_org}/${repo_name}"
    echo ""

    # Check AWS CLI
    check_aws_cli

    # Get AWS account ID
    local account_id
    account_id=$(get_aws_account_id)
    print_status "AWS Account ID: $account_id"

    # Check if OIDC provider exists
    if ! check_oidc_provider "$account_id"; then
        create_oidc_provider
    fi

    # Create trust policy
    create_trust_policy "$account_id" "$github_org" "$repo_name"

    # Create deployment policy
    create_deployment_policy

    # Create IAM role
    create_iam_role

    # Create and attach policy
    create_and_attach_policy "$account_id"

    # Cleanup
    cleanup

    # Display next steps
    display_next_steps "$account_id"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Run main function with all arguments
main "$@"
