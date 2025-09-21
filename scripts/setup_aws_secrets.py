#!/usr/bin/env python3
"""
AWS Secrets Manager Setup Script for PAKE System
Creates and configures secrets for secure production deployment
"""

import json
import logging
import secrets
import string
import sys

import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_strong_password(length: int = 16) -> str:
    """Generate a strong password with mixed characters"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def create_aws_secrets(region: str = "us-east-1") -> None:
    """Create all required secrets in AWS Secrets Manager"""
    try:
        client = boto3.client("secretsmanager", region_name=region)
        logger.info(f"Connected to AWS Secrets Manager in {region}")

        # Generate new strong passwords
        db_password = generate_strong_password(20)
        redis_password = generate_strong_password(16)
        n8n_password = generate_strong_password(16)

        secrets_to_create = [
            {
                "name": "pake-system/database",
                "description": "PostgreSQL database credentials for PAKE system",
                "secret": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "pake_system",
                    "user": "pake_user",
                    "password": db_password,
                },
            },
            {
                "name": "pake-system/redis",
                "description": "Redis cache credentials for PAKE system",
                "secret": {
                    "host": "localhost",
                    "port": 6379,
                    "password": redis_password,
                },
            },
            {
                "name": "pake-system/services/n8n",
                "description": "n8n workflow automation credentials",
                "secret": {"username": "n8n_admin", "password": n8n_password},
            },
            {
                "name": "pake-system/api-keys/openai",
                "description": "OpenAI API key for PAKE system",
                "secret": "REPLACE_WITH_YOUR_ACTUAL_OPENAI_API_KEY",
            },
            {
                "name": "pake-system/api-keys/anthropic",
                "description": "Anthropic API key for PAKE system",
                "secret": "REPLACE_WITH_YOUR_ACTUAL_ANTHROPIC_API_KEY",
            },
            {
                "name": "pake-system/api-keys/elevenlabs",
                "description": "ElevenLabs API key for PAKE system",
                "secret": "REPLACE_WITH_YOUR_ACTUAL_ELEVENLABS_API_KEY",
            },
        ]

        created_secrets = []

        for secret_config in secrets_to_create:
            try:
                # Check if secret already exists
                try:
                    client.describe_secret(SecretId=secret_config["name"])
                    logger.warning(
                        f"Secret {secret_config['name']} already exists, skipping...",
                    )
                    continue
                except client.exceptions.ResourceNotFoundException:
                    pass  # Secret doesn't exist, proceed to create

                # Create the secret
                secret_value = (
                    json.dumps(secret_config["secret"])
                    if isinstance(secret_config["secret"], dict)
                    else secret_config["secret"]
                )

                response = client.create_secret(
                    Name=secret_config["name"],
                    Description=secret_config["description"],
                    SecretString=secret_value,
                    Tags=[
                        {"Key": "Project", "Value": "PAKE-System"},
                        {"Key": "Environment", "Value": "Production"},
                        {"Key": "ManagedBy", "Value": "PAKE-System-Setup"},
                    ],
                )

                created_secrets.append(
                    {
                        "name": secret_config["name"],
                        "arn": response["ARN"],
                        "version": response["VersionId"],
                    },
                )

                logger.info(f"✅ Created secret: {secret_config['name']}")

            except Exception as e:
                logger.error(f"❌ Failed to create secret {secret_config['name']}: {e}")
                continue

        # Create IAM policy for PAKE system to access these secrets
        create_iam_policy(created_secrets, region)

        # Print summary
        print("\n" + "=" * 80)
        print("🔐 AWS SECRETS MANAGER SETUP COMPLETE")
        print("=" * 80)
        print(f"Region: {region}")
        print(f"Created {len(created_secrets)} secrets:")

        for secret in created_secrets:
            print(f"  ✅ {secret['name']}")

        print("\n📋 NEXT STEPS:")
        print("1. Update your actual API keys in the AWS Console:")
        for secret_config in secrets_to_create:
            if "api-keys" in secret_config["name"]:
                print(f"   - {secret_config['name']}")

        print("\n2. Set environment variables for production:")
        print("   export NODE_ENV=production")
        print(f"   export AWS_REGION={region}")
        print("   # Ensure AWS credentials are configured (AWS CLI, IAM role, etc.)")

        print("\n3. Attach the created IAM policy to your EC2 instance role or user")
        print(
            "   Policy ARN: arn:aws:iam::YOUR_ACCOUNT:policy/PAKESystemSecretsAccess",
        )

        print("\n4. Generated passwords for immediate use:")
        print(f"   Database password: {db_password}")
        print(f"   Redis password: {redis_password}")
        print(f"   n8n password: {n8n_password}")
        print("   ⚠️  Store these securely - they won't be shown again!")

        print("\n🛡️ SECURITY NOTES:")
        print("- All secrets are encrypted at rest with AWS KMS")
        print("- Access is controlled by IAM policies")
        print("- Enable CloudTrail to audit secret access")
        print("- Rotate secrets regularly (recommended: every 90 days)")

    except Exception as e:
        logger.error(f"Failed to setup AWS secrets: {e}")
        sys.exit(1)


def create_iam_policy(secrets: list, region: str) -> None:
    """Create IAM policy for accessing PAKE secrets"""
    try:
        iam = boto3.client("iam")

        # Get current AWS account ID
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]

        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PAKESystemSecretsAccess",
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret",
                    ],
                    "Resource": [
                        f"arn:aws:secretsmanager:{region}:{account_id}:secret:pake-system/*",
                    ],
                },
                {
                    "Sid": "PAKESystemKMSAccess",
                    "Effect": "Allow",
                    "Action": ["kms:Decrypt", "kms:DescribeKey"],
                    "Resource": f"arn:aws:kms:{region}:{account_id}:key/*",
                    "Condition": {
                        "StringEquals": {
                            "kms:ViaService": f"secretsmanager.{region}.amazonaws.com",
                        },
                    },
                },
            ],
        }

        policy_name = "PAKESystemSecretsAccess"

        # Check if policy already exists
        try:
            iam.get_policy(PolicyArn=f"arn:aws:iam::{account_id}:policy/{policy_name}")
            logger.info(f"IAM policy {policy_name} already exists")
        except iam.exceptions.NoSuchEntityException:
            # Create the policy
            response = iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document, indent=2),
                Description="Allows PAKE system to access required secrets from AWS Secrets Manager",
                Tags=[
                    {"Key": "Project", "Value": "PAKE-System"},
                    {"Key": "Purpose", "Value": "SecretsAccess"},
                ],
            )
            logger.info(f"✅ Created IAM policy: {policy_name}")
            logger.info(f"Policy ARN: {response['Policy']['Arn']}")

    except Exception as e:
        logger.error(f"Failed to create IAM policy: {e}")


def delete_all_secrets(region: str = "us-east-1") -> None:
    """Delete all PAKE system secrets (for cleanup/testing)"""
    try:
        client = boto3.client("secretsmanager", region_name=region)

        # List all secrets with pake-system prefix
        response = client.list_secrets(
            Filters=[{"Key": "name", "Values": ["pake-system/"]}],
        )

        for secret in response["SecretList"]:
            secret_name = secret["Name"]
            try:
                client.delete_secret(
                    SecretId=secret_name,
                    ForceDeleteWithoutRecovery=True,
                )
                logger.info(f"🗑️ Deleted secret: {secret_name}")
            except Exception as e:
                logger.error(f"Failed to delete {secret_name}: {e}")

    except Exception as e:
        logger.error(f"Failed to delete secrets: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup AWS Secrets Manager for PAKE System",
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete all PAKE secrets (dangerous!)",
    )

    args = parser.parse_args()

    if args.delete:
        confirm = input(
            "⚠️ This will permanently delete all PAKE secrets. Type 'DELETE' to confirm: ",
        )
        if confirm == "DELETE":
            delete_all_secrets(args.region)
        else:
            print("Deletion cancelled.")
    else:
        create_aws_secrets(args.region)
