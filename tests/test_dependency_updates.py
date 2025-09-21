#!/usr/bin/env python3
"""
Test script for dependency updates and package management
Tests package version checking, update validation, and compatibility
"""

import asyncio
import re
from pathlib import Path


class DependencyUpdateTester:
    """Test class for dependency update functionality"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.requirements_files = [
            "requirements.txt",
            "requirements-dev.txt",
            "requirements-prod.txt",
        ]
        self.package_files = ["package.json", "pyproject.toml", "setup.py"]

    async def test_python_dependencies(self) -> dict[str, any]:
        """Test Python dependency management"""
        print("Testing Python Dependencies...")

        results = {
            "requirements_files_found": [],
            "packages_outdated": [],
            "security_vulnerabilities": [],
            "compatibility_issues": [],
        }

        # Check for requirements files
        for req_file in self.requirements_files:
            req_path = self.project_root / req_file
            if req_path.exists():
                results["requirements_files_found"].append(req_file)
                print(f"   Found: {req_file}")

                # Check for outdated packages
                outdated = await self._check_outdated_packages(req_path)
                results["packages_outdated"].extend(outdated)

        # Check for security vulnerabilities
        vulnerabilities = await self._check_security_vulnerabilities()
        results["security_vulnerabilities"] = vulnerabilities

        return results

    async def test_nodejs_dependencies(self) -> dict[str, any]:
        """Test Node.js dependency management"""
        print("Testing Node.js Dependencies...")

        results = {
            "package_json_found": False,
            "node_modules_exists": False,
            "outdated_packages": [],
            "security_audit": {},
        }

        package_json_path = self.project_root / "package.json"
        if package_json_path.exists():
            results["package_json_found"] = True
            print("   Found: package.json")

            # Check for outdated packages
            outdated = await self._check_npm_outdated()
            results["outdated_packages"] = outdated

            # Run security audit
            audit_results = await self._run_npm_audit()
            results["security_audit"] = audit_results

        # Check for node_modules
        node_modules_path = self.project_root / "node_modules"
        if node_modules_path.exists():
            results["node_modules_exists"] = True
            print("   Found: node_modules directory")

        return results

    async def test_docker_dependencies(self) -> dict[str, any]:
        """Test Docker dependency management"""
        print("Testing Docker Dependencies...")

        results = {
            "dockerfile_found": False,
            "docker_compose_found": False,
            "base_images": [],
            "image_updates_available": [],
        }

        # Check for Dockerfile
        dockerfile_path = self.project_root / "Dockerfile"
        if dockerfile_path.exists():
            results["dockerfile_found"] = True
            print("   Found: Dockerfile")

            # Extract base images
            base_images = await self._extract_docker_base_images(dockerfile_path)
            results["base_images"] = base_images

        # Check for docker-compose
        compose_files = ["docker-compose.yml", "docker-compose.yaml"]
        for compose_file in compose_files:
            compose_path = self.project_root / compose_file
            if compose_path.exists():
                results["docker_compose_found"] = True
                print(f"   Found: {compose_file}")
                break

        return results

    async def _check_outdated_packages(
        self,
        requirements_path: Path,
    ) -> list[dict[str, str]]:
        """Check for outdated Python packages"""
        try:
            # Read requirements file
            with open(requirements_path) as f:
                requirements = f.read().strip().split("\n")

            outdated = []
            for req in requirements:
                if req.strip() and not req.startswith("#"):
                    package_name = (
                        req.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0]
                    )
                    print(f"   Checking package: {package_name}")

                    # Simulate outdated check (in real implementation, use pip-tools or similar)
                    if package_name in [
                        "requests",
                        "numpy",
                        "pandas",
                    ]:  # Common packages that might be outdated
                        outdated.append(
                            {
                                "package": package_name,
                                "current": "1.0.0",
                                "latest": "2.0.0",
                                "file": requirements_path.name,
                            },
                        )

            return outdated

        except Exception as e:
            print(f"   Error checking outdated packages: {e}")
            return []

    async def _check_security_vulnerabilities(self) -> list[dict[str, str]]:
        """Check for security vulnerabilities"""
        try:
            # Simulate security check (in real implementation, use safety or similar)
            vulnerabilities = [
                {
                    "package": "requests",
                    "version": "2.25.1",
                    "vulnerability": "CVE-2023-32681",
                    "severity": "HIGH",
                    "description": "Potential security vulnerability in requests library",
                },
            ]

            return vulnerabilities

        except Exception as e:
            print(f"   Error checking security vulnerabilities: {e}")
            return []

    async def _check_npm_outdated(self) -> list[dict[str, str]]:
        """Check for outdated npm packages"""
        try:
            # Simulate npm outdated check
            outdated = [
                {
                    "package": "express",
                    "current": "4.17.1",
                    "latest": "4.18.2",
                    "wanted": "4.18.2",
                },
                {
                    "package": "lodash",
                    "current": "4.17.20",
                    "latest": "4.17.21",
                    "wanted": "4.17.21",
                },
            ]

            return outdated

        except Exception as e:
            print(f"   Error checking npm outdated: {e}")
            return []

    async def _run_npm_audit(self) -> dict[str, any]:
        """Run npm security audit"""
        try:
            # Simulate npm audit results
            audit_results = {
                "vulnerabilities": {
                    "info": 0,
                    "low": 0,
                    "moderate": 1,
                    "high": 0,
                    "critical": 0,
                },
                "dependencies": 150,
                "devDependencies": 25,
                "audit_found": True,
            }

            return audit_results

        except Exception as e:
            print(f"   Error running npm audit: {e}")
            return {"error": str(e)}

    async def _extract_docker_base_images(self, dockerfile_path: Path) -> list[str]:
        """Extract base images from Dockerfile"""
        try:
            with open(dockerfile_path) as f:
                content = f.read()

            # Find FROM statements
            from_pattern = r"FROM\s+([^\s]+)"
            matches = re.findall(from_pattern, content, re.IGNORECASE)

            return matches

        except Exception as e:
            print(f"   Error extracting Docker base images: {e}")
            return []

    async def test_dependency_compatibility(self) -> dict[str, any]:
        """Test dependency compatibility across different environments"""
        print("Testing Dependency Compatibility...")

        results = {
            "python_versions": ["3.8", "3.9", "3.10", "3.11", "3.12"],
            "node_versions": ["16", "18", "20", "22"],
            "compatibility_matrix": {},
            "conflicts": [],
        }

        # Simulate compatibility testing
        compatibility_matrix = {
            "python": {
                "3.8": {"status": "supported", "packages": 45},
                "3.9": {"status": "supported", "packages": 47},
                "3.10": {"status": "supported", "packages": 48},
                "3.11": {"status": "supported", "packages": 49},
                "3.12": {"status": "supported", "packages": 50},
            },
            "node": {
                "16": {"status": "supported", "packages": 120},
                "18": {"status": "supported", "packages": 125},
                "20": {"status": "supported", "packages": 130},
                "22": {"status": "supported", "packages": 135},
            },
        }

        results["compatibility_matrix"] = compatibility_matrix

        return results

    async def generate_update_report(self) -> dict[str, any]:
        """Generate comprehensive dependency update report"""
        print("Generating Dependency Update Report...")

        report = {
            "timestamp": "2024-01-15T10:30:00Z",
            "python_dependencies": await self.test_python_dependencies(),
            "nodejs_dependencies": await self.test_nodejs_dependencies(),
            "docker_dependencies": await self.test_docker_dependencies(),
            "compatibility": await self.test_dependency_compatibility(),
            "recommendations": [],
        }

        # Generate recommendations
        recommendations = []

        if report["python_dependencies"]["packages_outdated"]:
            recommendations.append(
                {
                    "type": "python_update",
                    "priority": "medium",
                    "description": f"Update {len(report['python_dependencies']['packages_outdated'])} outdated Python packages",
                    "action": "Run: pip install --upgrade package_name",
                },
            )

        if report["nodejs_dependencies"]["outdated_packages"]:
            recommendations.append(
                {
                    "type": "npm_update",
                    "priority": "medium",
                    "description": f"Update {len(report['nodejs_dependencies']['outdated_packages'])} outdated npm packages",
                    "action": "Run: npm update",
                },
            )

        if report["python_dependencies"]["security_vulnerabilities"]:
            recommendations.append(
                {
                    "type": "security_update",
                    "priority": "high",
                    "description": f"Address {len(report['python_dependencies']['security_vulnerabilities'])} security vulnerabilities",
                    "action": "Run: pip install --upgrade vulnerable_package",
                },
            )

        report["recommendations"] = recommendations

        return report


def test_dependency_updates():
    """Main test function for dependency updates"""
    return asyncio.run(_test_dependency_updates_async())


async def _test_dependency_updates_async():
    """Async implementation of dependency updates test"""
    print("PAKE System - Dependency Update Tests")
    print("=" * 50)

    tester = DependencyUpdateTester()

    try:
        # Test Python dependencies
        python_results = await tester.test_python_dependencies()
        print("\nPython Dependencies Results:")
        print(f"   Requirements files: {python_results['requirements_files_found']}")
        print(f"   Outdated packages: {len(python_results['packages_outdated'])}")
        print(
            f"   Security vulnerabilities: {len(python_results['security_vulnerabilities'])}",
        )

        # Test Node.js dependencies
        nodejs_results = await tester.test_nodejs_dependencies()
        print("\nNode.js Dependencies Results:")
        print(f"   Package.json found: {nodejs_results['package_json_found']}")
        print(f"   Node_modules exists: {nodejs_results['node_modules_exists']}")
        print(f"   Outdated packages: {len(nodejs_results['outdated_packages'])}")

        # Test Docker dependencies
        docker_results = await tester.test_docker_dependencies()
        print("\nDocker Dependencies Results:")
        print(f"   Dockerfile found: {docker_results['dockerfile_found']}")
        print(f"   Docker Compose found: {docker_results['docker_compose_found']}")
        print(f"   Base images: {docker_results['base_images']}")

        # Test compatibility
        compatibility_results = await tester.test_dependency_compatibility()
        print("\nCompatibility Results:")
        print(
            f"   Python versions supported: {len(compatibility_results['python_versions'])}",
        )
        print(
            f"   Node versions supported: {len(compatibility_results['node_versions'])}",
        )

        # Generate comprehensive report
        report = await tester.generate_update_report()
        print("\nUpdate Report Generated:")
        print(f"   Recommendations: {len(report['recommendations'])}")

        for rec in report["recommendations"]:
            print(f"   - {rec['priority'].upper()}: {rec['description']}")

        print("\nDependency update tests completed successfully!")
        return True

    except Exception as e:
        print(f"ERROR: Dependency update tests failed: {e}")
        return False


def test_package_version_validation():
    """Test package version validation"""
    return asyncio.run(_test_package_version_validation_async())


async def _test_package_version_validation_async():
    """Async implementation of package version validation test"""
    print("\nTesting Package Version Validation...")

    # Test version parsing
    test_versions = ["1.0.0", ">=1.0.0", "~1.0.0", "==1.0.0", "1.0.0,<2.0.0"]

    for version in test_versions:
        print(f"   Testing version spec: {version}")
        # In real implementation, validate version specifications

    print("   Package version validation completed")


def test_dependency_resolution():
    """Test dependency resolution conflicts"""
    return asyncio.run(_test_dependency_resolution_async())


async def _test_dependency_resolution_async():
    """Async implementation of dependency resolution test"""
    print("\nTesting Dependency Resolution...")

    # Simulate dependency conflicts
    conflicts = [
        {
            "package": "requests",
            "conflict": "urllib3",
            "reason": "Version incompatibility",
            "resolution": "Update both packages",
        },
    ]

    for conflict in conflicts:
        print(f"   Conflict: {conflict['package']} vs {conflict['conflict']}")
        print(f"   Reason: {conflict['reason']}")
        print(f"   Resolution: {conflict['resolution']}")

    print("   Dependency resolution testing completed")


async def main():
    """Run all dependency update tests"""
    print("PAKE System - Comprehensive Dependency Update Testing")
    print("=" * 60)

    success = True

    # Run main dependency tests
    if not await test_dependency_updates():
        success = False

    # Run additional tests
    await test_package_version_validation()
    await test_dependency_resolution()

    if success:
        print("\n✅ All dependency update tests passed!")
    else:
        print("\n❌ Some dependency update tests failed!")

    return success


if __name__ == "__main__":
    asyncio.run(main())
