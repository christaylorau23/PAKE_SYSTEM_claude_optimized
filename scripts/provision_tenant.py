#!/usr/bin/env python3
"""
PAKE System - Phase 16 Tenant Provisioning Automation
Automated tenant provisioning with Kubernetes namespace creation and configuration.
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import secrets
import string
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.services.database.multi_tenant_schema import (
    MultiTenantDatabaseConfig,
    MultiTenantPostgreSQLService,
)

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class TenantPlan:
    """Tenant plan configuration"""

    name: str
    cpu_request_limit: str
    cpu_limit: str
    memory_request_limit: str
    memory_limit: str
    pod_limit: str
    service_limit: str
    configmap_limit: str
    secret_limit: str
    pvc_limit: str
    rc_limit: str
    max_replicas: str
    default_cpu_limit: str
    default_memory_limit: str
    default_cpu_request: str
    default_memory_request: str


# Predefined tenant plans
TENANT_PLANS = {
    "basic": TenantPlan(
        name="basic",
        cpu_request_limit="1",
        cpu_limit="2",
        memory_request_limit="2Gi",
        memory_limit="4Gi",
        pod_limit="5",
        service_limit="3",
        configmap_limit="10",
        secret_limit="5",
        pvc_limit="2",
        rc_limit="5",
        max_replicas="3",
        default_cpu_limit="200m",
        default_memory_limit="256Mi",
        default_cpu_request="50m",
        default_memory_request="64Mi",
    ),
    "professional": TenantPlan(
        name="professional",
        cpu_request_limit="2",
        cpu_limit="4",
        memory_request_limit="4Gi",
        memory_limit="8Gi",
        pod_limit="10",
        service_limit="5",
        configmap_limit="20",
        secret_limit="10",
        pvc_limit="5",
        rc_limit="10",
        max_replicas="5",
        default_cpu_limit="500m",
        default_memory_limit="512Mi",
        default_cpu_request="100m",
        default_memory_request="128Mi",
    ),
    "enterprise": TenantPlan(
        name="enterprise",
        cpu_request_limit="4",
        cpu_limit="8",
        memory_request_limit="8Gi",
        memory_limit="16Gi",
        pod_limit="20",
        service_limit="10",
        configmap_limit="50",
        secret_limit="20",
        pvc_limit="10",
        rc_limit="20",
        max_replicas="10",
        default_cpu_limit="1000m",
        default_memory_limit="1Gi",
        default_cpu_request="200m",
        default_memory_request="256Mi",
    ),
}


class TenantProvisioner:
    """
    Automated tenant provisioning system.

    Features:
    - Database tenant creation
    - Kubernetes namespace provisioning
    - Resource quota configuration
    - Network policy setup
    - RBAC configuration
    - Service account creation
    - Configuration and secrets management
    - Health validation
    """

    def __init__(
        self,
        db_config: MultiTenantDatabaseConfig,
        kubeconfig_path: str | None = None,
    ):
        self.db_config = db_config
        self.kubeconfig_path = kubeconfig_path
        self.db_service: MultiTenantPostgreSQLService | None = None
        self.provisioning_stats = {
            "tenants_created": 0,
            "namespaces_created": 0,
            "errors": [],
        }

    async def initialize(self) -> None:
        """Initialize database service"""
        try:
            self.db_service = MultiTenantPostgreSQLService(self.db_config)
            await self.db_service.initialize()
            logger.info("✅ Database service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database service: {e}")
            raise

    async def close(self) -> None:
        """Close database connections"""
        if self.db_service:
            await self.db_service.close()
        logger.info("Database connections closed")

    def _generate_tenant_id(self) -> str:
        """Generate unique tenant ID"""
        return f"tenant-{secrets.token_hex(8)}"

    def _generate_credentials(self) -> dict[str, str]:
        """Generate secure credentials for tenant"""
        # Generate random REDACTED_SECRETs
        db_REDACTED_SECRET = "".join(
            secrets.choices(string.ascii_letters + string.digits, k=16),
        )
        api_key = "".join(secrets.choices(string.ascii_letters + string.digits, k=32))
        jwt_secret = "".join(
            secrets.choices(string.ascii_letters + string.digits, k=64),
        )
        encryption_key = "".join(
            secrets.choices(string.ascii_letters + string.digits, k=32),
        )

        return {
            "db_REDACTED_SECRET": db_REDACTED_SECRET,
            "api_key": api_key,
            "jwt_secret": jwt_secret,
            "encryption_key": encryption_key,
        }

    def _base64_encode(self, value: str) -> str:
        """Base64 encode value for Kubernetes secrets"""
        return base64.b64encode(value.encode()).decode()

    async def create_database_tenant(
        self,
        tenant_name: str,
        display_name: str,
        domain: str | None,
        plan: str,
        admin_email: str,
    ) -> dict[str, Any]:
        """Create tenant in database"""
        try:
            # Create tenant in database
            tenant = await self.db_service.create_tenant(
                name=tenant_name,
                display_name=display_name,
                domain=domain,
                plan=plan,
                settings={
                    "provisioned_at": datetime.utcnow().isoformat(),
                    "admin_email": admin_email,
                    "provisioning_method": "automated",
                },
                limits=TENANT_PLANS[plan].__dict__,
            )

            # Create admin user
            admin_user = await self.db_service.create_user(
                tenant_id=tenant["id"],
                username="admin",
                email=admin_email,
                REDACTED_SECRET_hash="temp_REDACTED_SECRET_hash",  # Will be updated with real hash
                full_name=f"{display_name} Administrator",
                role="admin",
            )

            logger.info(
                f"✅ Created database tenant: {tenant['name']} ({tenant['id']})",
            )
            self.provisioning_stats["tenants_created"] += 1

            return {"tenant": tenant, "admin_user": admin_user}

        except Exception as e:
            error_msg = f"Failed to create database tenant: {e}"
            logger.error(error_msg)
            self.provisioning_stats["errors"].append(error_msg)
            raise

    def _generate_k8s_manifests(
        self,
        tenant_data: dict[str, Any],
        credentials: dict[str, str],
    ) -> str:
        """Generate Kubernetes manifests for tenant"""
        tenant_id = tenant_data["tenant"]["id"]
        tenant_name = tenant_data["tenant"]["name"]
        tenant_domain = tenant_data["tenant"].get("domain", "")
        tenant_plan = tenant_data["tenant"]["plan"]
        admin_email = tenant_data["admin_user"]["email"]

        plan_config = TENANT_PLANS[tenant_plan]

        # Load template
        template_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "k8s",
            "multitenant",
            "tenant-namespace.yaml",
        )

        with open(template_path) as f:
            template = f.read()

        # Replace template variables
        manifest = template.replace("{{TENANT_ID}}", tenant_id)
        manifest = manifest.replace("{{TENANT_NAME}}", tenant_name)
        manifest = manifest.replace("{{TENANT_DOMAIN}}", tenant_domain)
        manifest = manifest.replace("{{TENANT_PLAN}}", tenant_plan)
        manifest = manifest.replace("{{TENANT_STATUS}}", "active")
        manifest = manifest.replace("{{CREATED_AT}}", datetime.utcnow().isoformat())
        manifest = manifest.replace("{{TENANT_ADMIN_USER}}", admin_email)

        # Plan-specific resource limits
        manifest = manifest.replace(
            "{{CPU_REQUEST_LIMIT}}",
            plan_config.cpu_request_limit,
        )
        manifest = manifest.replace("{{CPU_LIMIT}}", plan_config.cpu_limit)
        manifest = manifest.replace(
            "{{MEMORY_REQUEST_LIMIT}}",
            plan_config.memory_request_limit,
        )
        manifest = manifest.replace("{{MEMORY_LIMIT}}", plan_config.memory_limit)
        manifest = manifest.replace("{{POD_LIMIT}}", plan_config.pod_limit)
        manifest = manifest.replace("{{SERVICE_LIMIT}}", plan_config.service_limit)
        manifest = manifest.replace("{{CONFIGMAP_LIMIT}}", plan_config.configmap_limit)
        manifest = manifest.replace("{{SECRET_LIMIT}}", plan_config.secret_limit)
        manifest = manifest.replace("{{PVC_LIMIT}}", plan_config.pvc_limit)
        manifest = manifest.replace("{{RC_LIMIT}}", plan_config.rc_limit)
        manifest = manifest.replace("{{MAX_REPLICAS}}", plan_config.max_replicas)
        manifest = manifest.replace(
            "{{DEFAULT_CPU_LIMIT}}",
            plan_config.default_cpu_limit,
        )
        manifest = manifest.replace(
            "{{DEFAULT_MEMORY_LIMIT}}",
            plan_config.default_memory_limit,
        )
        manifest = manifest.replace(
            "{{DEFAULT_CPU_REQUEST}}",
            plan_config.default_cpu_request,
        )
        manifest = manifest.replace(
            "{{DEFAULT_MEMORY_REQUEST}}",
            plan_config.default_memory_request,
        )

        # Credentials
        manifest = manifest.replace(
            "{{DB_USERNAME_B64}}",
            self._base64_encode("pake_user"),
        )
        manifest = manifest.replace(
            "{{DB_PASSWORD_B64}}",
            self._base64_encode(credentials["db_REDACTED_SECRET"]),
        )
        manifest = manifest.replace(
            "{{DB_NAME_B64}}",
            self._base64_encode("pake_system_multitenant"),
        )
        manifest = manifest.replace(
            "{{API_KEY_B64}}",
            self._base64_encode(credentials["api_key"]),
        )
        manifest = manifest.replace(
            "{{JWT_SECRET_B64}}",
            self._base64_encode(credentials["jwt_secret"]),
        )
        manifest = manifest.replace(
            "{{ENCRYPTION_KEY_B64}}",
            self._base64_encode(credentials["encryption_key"]),
        )

        return manifest

    async def create_k8s_namespace(
        self,
        tenant_data: dict[str, Any],
        credentials: dict[str, str],
    ) -> bool:
        """Create Kubernetes namespace and resources"""
        try:
            tenant_id = tenant_data["tenant"]["id"]

            # Generate manifests
            manifest_content = self._generate_k8s_manifests(tenant_data, credentials)

            # Write manifest to temporary file
            manifest_path = f"/tmp/tenant-{tenant_id}-manifest.yaml"
            with open(manifest_path, "w") as f:
                f.write(manifest_content)

            # Apply manifests using kubectl
            cmd = ["kubectl", "apply", "-f", manifest_path]
            if self.kubeconfig_path:
                cmd.extend(["--kubeconfig", self.kubeconfig_path])

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Clean up temporary file
            os.remove(manifest_path)

            logger.info(f"✅ Created Kubernetes namespace: tenant-{tenant_id}")
            self.provisioning_stats["namespaces_created"] += 1

            return True

        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to create Kubernetes namespace: {e.stderr}"
            logger.error(error_msg)
            self.provisioning_stats["errors"].append(error_msg)
            return False
        except Exception as e:
            error_msg = f"Kubernetes namespace creation error: {e}"
            logger.error(error_msg)
            self.provisioning_stats["errors"].append(error_msg)
            return False

    async def validate_tenant_provisioning(self, tenant_id: str) -> dict[str, Any]:
        """Validate tenant provisioning"""
        try:
            # Check database tenant
            tenant_data = await self.db_service.get_tenant_by_id(tenant_id)
            if not tenant_data:
                return {"status": "failed", "error": "Tenant not found in database"}

            # Check Kubernetes namespace
            cmd = ["kubectl", "get", "namespace", f"tenant-{tenant_id}"]
            if self.kubeconfig_path:
                cmd.extend(["--kubeconfig", self.kubeconfig_path])

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {"status": "failed", "error": "Kubernetes namespace not found"}

            # Check namespace resources
            cmd = ["kubectl", "get", "all", "-n", f"tenant-{tenant_id}"]
            if self.kubeconfig_path:
                cmd.extend(["--kubeconfig", self.kubeconfig_path])

            result = subprocess.run(cmd, capture_output=True, text=True)

            return {
                "status": "success",
                "tenant_data": tenant_data,
                "namespace_exists": True,
                "resources_created": result.stdout,
            }

        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def provision_tenant(
        self,
        tenant_name: str,
        display_name: str,
        domain: str | None,
        plan: str,
        admin_email: str,
    ) -> dict[str, Any]:
        """Complete tenant provisioning process"""
        logger.info(f"🚀 Starting tenant provisioning: {tenant_name}")

        try:
            # Generate credentials
            credentials = self._generate_credentials()

            # Create database tenant
            tenant_data = await self.create_database_tenant(
                tenant_name,
                display_name,
                domain,
                plan,
                admin_email,
            )

            # Create Kubernetes namespace
            k8s_success = await self.create_k8s_namespace(tenant_data, credentials)

            if not k8s_success:
                logger.warning(
                    "Kubernetes namespace creation failed, but database tenant was created",
                )

            # Validate provisioning
            validation = await self.validate_tenant_provisioning(
                tenant_data["tenant"]["id"],
            )

            # Generate provisioning report
            report = {
                "status": "success" if validation["status"] == "success" else "partial",
                "tenant_id": tenant_data["tenant"]["id"],
                "tenant_name": tenant_data["tenant"]["name"],
                "tenant_domain": tenant_data["tenant"].get("domain"),
                "plan": plan,
                "admin_email": admin_email,
                "credentials": credentials,
                "validation": validation,
                "provisioning_stats": self.provisioning_stats,
                "next_steps": [
                    "Update admin user REDACTED_SECRET with secure hash",
                    "Configure tenant-specific DNS records",
                    "Set up monitoring and alerting for tenant",
                    "Create tenant-specific backup policies",
                    "Configure tenant access to shared services",
                    "Set up tenant billing and usage tracking",
                ],
            }

            logger.info(f"🎉 Tenant provisioning completed: {tenant_name}")
            return report

        except Exception as e:
            logger.error(f"❌ Tenant provisioning failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "provisioning_stats": self.provisioning_stats,
            }

    async def list_tenants(self) -> list[dict[str, Any]]:
        """List all provisioned tenants"""
        try:
            tenants = await self.db_service.get_all_tenants()

            tenant_list = []
            for tenant in tenants:
                # Check if Kubernetes namespace exists
                cmd = ["kubectl", "get", "namespace", f"tenant-{tenant['id']}"]
                if self.kubeconfig_path:
                    cmd.extend(["--kubeconfig", self.kubeconfig_path])

                result = subprocess.run(cmd, capture_output=True, text=True)
                namespace_exists = result.returncode == 0

                tenant_list.append(
                    {
                        **tenant,
                        "namespace_exists": namespace_exists,
                        "provisioning_status": (
                            "complete" if namespace_exists else "database_only"
                        ),
                    },
                )

            return tenant_list

        except Exception as e:
            logger.error(f"Failed to list tenants: {e}")
            return []

    async def delete_tenant(
        self,
        tenant_id: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Delete tenant and all associated resources"""
        logger.info(f"🗑️ Starting tenant deletion: {tenant_id}")

        try:
            # Get tenant data
            tenant_data = await self.db_service.get_tenant_by_id(tenant_id)
            if not tenant_data:
                return {"status": "failed", "error": "Tenant not found"}

            # Delete Kubernetes namespace
            cmd = ["kubectl", "delete", "namespace", f"tenant-{tenant_id}"]
            if self.kubeconfig_path:
                cmd.extend(["--kubeconfig", self.kubeconfig_path])

            if force:
                cmd.append("--force")

            result = subprocess.run(cmd, capture_output=True, text=True)

            # Update tenant status in database
            await self.db_service.update_tenant_status(tenant_id, "deleted")

            logger.info(f"✅ Tenant deleted: {tenant_id}")
            return {
                "status": "success",
                "tenant_id": tenant_id,
                "tenant_name": tenant_data["name"],
                "k8s_deletion": result.stdout,
            }

        except Exception as e:
            logger.error(f"❌ Tenant deletion failed: {e}")
            return {"status": "failed", "error": str(e)}


async def main():
    """Main provisioning function"""
    parser = argparse.ArgumentParser(description="PAKE System Tenant Provisioning")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Provision command
    provision_parser = subparsers.add_parser("provision", help="Provision new tenant")
    provision_parser.add_argument("--name", required=True, help="Tenant name")
    provision_parser.add_argument(
        "--display-name",
        required=True,
        help="Tenant display name",
    )
    provision_parser.add_argument("--domain", help="Tenant domain")
    provision_parser.add_argument(
        "--plan",
        choices=["basic", "professional", "enterprise"],
        default="basic",
        help="Tenant plan",
    )
    provision_parser.add_argument("--admin-email", required=True, help="Admin email")

    # List command
    list_parser = subparsers.add_parser("list", help="List all tenants")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete tenant")
    delete_parser.add_argument("--tenant-id", required=True, help="Tenant ID")
    delete_parser.add_argument("--force", action="store_true", help="Force deletion")

    # Common arguments
    parser.add_argument("--db-host", default="localhost", help="Database host")
    parser.add_argument(
        "--db-name",
        default="pake_system_multitenant",
        help="Database name",
    )
    parser.add_argument("--kubeconfig", help="Kubernetes config file path")
    parser.add_argument("--output-report", help="Output provisioning report to file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Configure database
    db_config = MultiTenantDatabaseConfig(host=args.db_host, database=args.db_name)

    # Initialize provisioner
    provisioner = TenantProvisioner(db_config, args.kubeconfig)
    await provisioner.initialize()

    try:
        if args.command == "provision":
            result = await provisioner.provision_tenant(
                tenant_name=args.name,
                display_name=args.display_name,
                domain=args.domain,
                plan=args.plan,
                admin_email=args.admin_email,
            )

            if args.output_report:
                with open(args.output_report, "w") as f:
                    json.dump(result, f, indent=2)
                logger.info(f"📄 Provisioning report saved to: {args.output_report}")

            print("\n" + "=" * 60)
            print("TENANT PROVISIONING SUMMARY")
            print("=" * 60)
            print(f"Status: {result['status'].upper()}")
            print(f"Tenant ID: {result.get('tenant_id', 'N/A')}")
            print(f"Tenant Name: {result.get('tenant_name', 'N/A')}")
            print(f"Plan: {result.get('plan', 'N/A')}")
            print(f"Admin Email: {result.get('admin_email', 'N/A')}")

            if result["status"] == "success":
                print("\n📋 Next Steps:")
                for i, step in enumerate(result.get("next_steps", []), 1):
                    print(f"  {i}. {step}")

        elif args.command == "list":
            tenants = await provisioner.list_tenants()

            print("\n" + "=" * 80)
            print("PROVISIONED TENANTS")
            print("=" * 80)
            print(f"{'ID':<20} {'Name':<20} {'Plan':<12} {'Status':<15} {'Domain':<20}")
            print("-" * 80)

            for tenant in tenants:
                print(
                    f"{tenant['id']:<20} {tenant['name']:<20} {tenant['plan']:<12} "
                    f"{tenant['provisioning_status']:<15} {
                        tenant.get('domain', 'N/A'):<20}",
                )

        elif args.command == "delete":
            result = await provisioner.delete_tenant(args.tenant_id, args.force)

            print("\n" + "=" * 60)
            print("TENANT DELETION SUMMARY")
            print("=" * 60)
            print(f"Status: {result['status'].upper()}")
            print(f"Tenant ID: {result.get('tenant_id', 'N/A')}")
            print(f"Tenant Name: {result.get('tenant_name', 'N/A')}")

            if result["status"] == "failed":
                print(f"Error: {result['error']}")

    finally:
        await provisioner.close()


if __name__ == "__main__":
    asyncio.run(main())
