#!/usr/bin/env python3
"""PAKE System - DAST Security Testing Integration (Phase 3 Architectural Health)
Dynamic Application Security Testing (DAST) integration using OWASP ZAP.

This module provides:
1. OWASP ZAP integration and configuration
2. Automated security scanning workflows
3. Vulnerability triage and remediation tracking
4. CI/CD pipeline integration
5. Security reporting and monitoring
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
import json
import logging
import os
from pathlib import Path
import subprocess
import time
from typing import Any

import requests
import yaml

logger = logging.getLogger(__name__)


class VulnerabilitySeverity(Enum):
    """Vulnerability severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class VulnerabilityStatus(Enum):
    """Vulnerability remediation status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"


class ScanStatus(Enum):
    """DAST scan status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class Vulnerability:
    """Security vulnerability representation."""

    vulnerability_id: str
    name: str
    description: str
    severity: VulnerabilitySeverity
    status: VulnerabilityStatus = VulnerabilityStatus.OPEN
    url: str = ""
    parameter: str = ""
    evidence: str = ""
    confidence: str = ""
    cwe_id: str = ""
    wasc_id: str = ""
    solution: str = ""
    reference: str = ""
    tags: list[str] = field(default_factory=list)
    first_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    assigned_to: str | None = None
    remediation_notes: list[str] = field(default_factory=list)


@dataclass
class ScanConfiguration:
    """DAST scan configuration."""

    target_url: str
    scan_name: str
    scan_type: str = "active"  # "active", "passive", "spider"
    context_id: str | None = None
    policy_id: str | None = None
    user_id: str | None = None
    max_scan_duration: int = 3600  # 1 hour
    max_children: int = 1000
    recurse: bool = True
    subtree_only: bool = False
    custom_headers: dict[str, str] = field(default_factory=dict)
    excluded_paths: list[str] = field(default_factory=list)
    included_paths: list[str] = field(default_factory=list)
    authentication_config: dict[str, Any] | None = None


@dataclass
class ScanResult:
    """DAST scan result."""

    scan_id: str
    scan_name: str
    target_url: str
    status: ScanStatus
    start_time: datetime
    end_time: datetime | None = None
    duration_seconds: int = 0
    vulnerabilities: list[Vulnerability] = field(default_factory=list)
    total_alerts: int = 0
    high_severity_count: int = 0
    medium_severity_count: int = 0
    low_severity_count: int = 0
    informational_count: int = 0
    scan_log: list[str] = field(default_factory=list)
    error_message: str | None = None


class OWASPZAPClient:
    """OWASP ZAP API client for DAST scanning."""

    def __init__(self, zap_host: str = "localhost", zap_port: int = 8080, api_key: str | None = None) -> None:
        self.zap_host = zap_host
        self.zap_port = zap_port
        self.api_key = api_key
        self.base_url = f"http://{zap_host}:{zap_port}"
        self.session = requests.Session()

        if api_key:
            self.session.params = {"apikey": api_key}

    async def start_zap(self) -> bool:
        """Start OWASP ZAP daemon."""
        try:
            # Check if ZAP is already running
            if await self.is_zap_running():
                logger.info("OWASP ZAP is already running")
                return True

            # Start ZAP daemon
            cmd = [
                "zap.sh",
                "-daemon",
                "-config",
                f"api.addrs.addr.name=.*.port={self.zap_port}",
                "-config",
                "api.disablekey=true",  # Disable API key for local testing
            ]

            logger.info("Starting OWASP ZAP: %s", " ".join(cmd))
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=os.environ.copy(),
            )

            # Wait for ZAP to start
            max_wait = 60  # 60 seconds
            wait_time = 0
            while wait_time < max_wait:
                if await self.is_zap_running():
                    logger.info("OWASP ZAP started successfully")
                    return True
                await asyncio.sleep(2)
                wait_time += 2

            logger.error("Failed to start OWASP ZAP within timeout")
            return False

        except (ValueError, RuntimeError) as e:
            logger.error("Error starting OWASP ZAP: %s", e)
            return False

    async def is_zap_running(self) -> bool:
        """Check if OWASP ZAP is running."""
        try:
            response = self.session.get(f"{self.base_url}/JSON/core/view/version/")
            return response.status_code == 200
        except (json.JSONDecodeError, ValueError) as e:
            return False

    async def stop_zap(self) -> bool:
        """Stop OWASP ZAP daemon."""
        try:
            response = self.session.get(f"{self.base_url}/JSON/core/action/shutdown/")
            return response.status_code == 200
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Error stopping OWASP ZAP: %s", e)
            return False

    async def create_context(self, context_name: str, target_url: str) -> str | None:
        """Create a new context for scanning."""
        try:
            # Create context
            response = self.session.get(
                f"{self.base_url}/JSON/context/action/newContext/",
                params={"contextName": context_name},
            )

            if response.status_code != 200:
                return None

            context_id = response.json().get("contextId")

            # Include target URL in context
            include_url_response = self.session.get(
                f"{self.base_url}/JSON/context/action/includeInContext/",
                params={"contextName": context_name, "regex": f"^{target_url}.*"},
            )

            if include_url_response.status_code == 200:
                logger.info(
                    "Created context '%s' with ID: %s", context_name, context_id
                )
                return context_id

            return None

        except (ValueError, RuntimeError) as e:
            logger.error("Error creating context: %s", e)
            return None

    async def start_spider_scan(
        self, target_url: str, context_id: str | None = None
    ) -> str | None:
        """Start spider scan."""
        try:
            params = {"url": target_url}
            if context_id:
                params["contextId"] = context_id

            response = self.session.get(
                f"{self.base_url}/JSON/spider/action/scan/", params=params
            )

            if response.status_code == 200:
                scan_id = response.json().get("scan")
                logger.info("Started spider scan with ID: %s", scan_id)
                return scan_id

            return None

        except (ValueError, RuntimeError) as e:
            logger.error("Error starting spider scan: %s", e)
            return None

    async def start_active_scan(
        self, target_url: str, context_id: str | None = None
    ) -> str | None:
        """Start active scan."""
        try:
            params = {"url": target_url}
            if context_id:
                params["contextId"] = context_id

            response = self.session.get(
                f"{self.base_url}/JSON/ascan/action/scan/", params=params
            )

            if response.status_code == 200:
                scan_id = response.json().get("scan")
                logger.info("Started active scan with ID: %s", scan_id)
                return scan_id

            return None

        except (ValueError, RuntimeError) as e:
            logger.error("Error starting active scan: %s", e)
            return None

    async def get_scan_status(
        self, scan_id: str, scan_type: str = "spider"
    ) -> dict[str, Any]:
        """Get scan status."""
        try:
            endpoint = f"{self.base_url}/JSON/spider/view/status/"
            if scan_type == "active":
                endpoint = f"{self.base_url}/JSON/ascan/view/status/"

            response = self.session.get(endpoint, params={"scanId": scan_id})

            if response.status_code == 200:
                return response.json()

            return {}

        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Error getting scan status: %s", e)
            return {}

    async def get_alerts(self, base_url: str | None = None) -> list[dict[str, Any]]:
        """Get security alerts."""
        try:
            params = {}
            if base_url:
                params["baseurl"] = base_url

            response = self.session.get(
                f"{self.base_url}/JSON/core/view/alerts/", params=params
            )

            if response.status_code == 200:
                return response.json().get("alerts", [])

            return []

        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Error getting alerts: %s", e)
            return []

    async def generate_report(self, report_format: str = "json") -> str | None:
        """Generate security report."""
        try:
            endpoint_map = {
                "json": f"{self.base_url}/OTHER/core/other/jsonreport/",
                "html": f"{self.base_url}/OTHER/core/other/htmlreport/",
                "xml": f"{self.base_url}/OTHER/core/other/xmlreport/",
            }

            endpoint = endpoint_map.get(report_format)
            if not endpoint:
                return None

            response = self.session.get(endpoint)

            if response.status_code == 200:
                return response.text

            return None

        except (ValueError, RuntimeError) as e:
            logger.error("Error generating report: %s", e)
            return None


class PAKEDASTRunner:
    """PAKE System DAST testing runner."""

    def __init__(self, config_file: str = "dast_config.yaml") -> None:
        self.config_file = config_file
        self.zap_client: OWASPZAPClient | None = None
        self.scan_results: list[ScanResult] = []
        self.vulnerabilities: list[Vulnerability] = []
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load DAST configuration."""
        default_config = {
            "zap": {
                "host": "localhost",
                "port": 8080,
                "api_key": None,
                "timeout": 3600,
            },
            "scans": {
                "default_policy": "Default Policy",
                "max_scan_duration": 3600,
                "excluded_paths": ["/api/health", "/api/metrics"],
                "custom_headers": {},
            },
            "reporting": {
                "output_dir": "reports/dast",
                "formats": ["json", "html"],
                "include_false_positives": False,
            },
            "targets": {
                "staging": "http://localhost:3001",
                "production": "https://pake-system.com",
            },
        }

        if self.config_file and Path(self.config_file).exists():
            try:
                with open(self.config_file) as f:
                    user_config = yaml.safe_load(f)
                    default_config.update(user_config)
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Could not load config file %s: %s", self.config_file, e)

        return default_config

    async def initialize(self) -> bool:
        """Initialize DAST runner."""
        try:
            zap_config = self.config["zap"]
            self.zap_client = OWASPZAPClient(
                host=zap_config["host"],
                port=zap_config["port"],
                api_key=zap_config.get("api_key"),
            )

            # Start ZAP if not running
            if not await self.zap_client.is_zap_running():
                logger.info("Starting OWASP ZAP...")
                if not await self.zap_client.start_zap():
                    logger.error("Failed to start OWASP ZAP")
                    return False

            logger.info("DAST runner initialized successfully")
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Error initializing DAST runner: %s", e)
            return False

    async def run_scan(self, config: ScanConfiguration) -> ScanResult:
        """Run DAST scan with given configuration."""
        if not self.zap_client:
            msg = "DAST runner not initialized"
            raise RuntimeError(msg)

        scan_result = ScanResult(
            scan_id=f"scan_{int(time.time())}",
            scan_name=config.scan_name,
            target_url=config.target_url,
            status=ScanStatus.PENDING,
            start_time=datetime.now(UTC),
        )

        try:
            logger.info("Starting DAST scan: %s", config.scan_name)
            scan_result.status = ScanStatus.RUNNING

            # Create context if needed
            context_id = None
            if config.context_id:
                context_id = await self.zap_client.create_context(
                    f"context_{scan_result.scan_id}", config.target_url
                )

            # Start spider scan first
            spider_scan_id = await self.zap_client.start_spider_scan(
                config.target_url, context_id
            )

            if spider_scan_id:
                # Wait for spider scan to complete
                await self._wait_for_scan_completion(spider_scan_id, "spider")

            # Start active scan
            active_scan_id = await self.zap_client.start_active_scan(
                config.target_url, context_id
            )

            if active_scan_id:
                # Wait for active scan to complete
                await self._wait_for_scan_completion(active_scan_id, "active")

            # Get scan results
            alerts = await self.zap_client.get_alerts(config.target_url)
            scan_result.vulnerabilities = self._parse_alerts(alerts)
            scan_result.total_alerts = len(scan_result.vulnerabilities)

            # Count vulnerabilities by severity
            for vuln in scan_result.vulnerabilities:
                if vuln.severity == VulnerabilitySeverity.HIGH:
                    scan_result.high_severity_count += 1
                elif vuln.severity == VulnerabilitySeverity.MEDIUM:
                    scan_result.medium_severity_count += 1
                elif vuln.severity == VulnerabilitySeverity.LOW:
                    scan_result.low_severity_count += 1
                else:
                    scan_result.informational_count += 1

            scan_result.status = ScanStatus.COMPLETED
            scan_result.end_time = datetime.now(UTC)
            scan_result.duration_seconds = int(
                (scan_result.end_time - scan_result.start_time).total_seconds()
            )

            logger.info("DAST scan completed: %s", scan_result.scan_name)
            logger.info("Found %s vulnerabilities", scan_result.total_alerts)

        except (ValueError, RuntimeError) as e:
            logger.error("Error running DAST scan: %s", e)
            scan_result.status = ScanStatus.FAILED
            scan_result.error_message = str(e)
            scan_result.end_time = datetime.now(UTC)

        self.scan_results.append(scan_result)
        return scan_result

    async def _wait_for_scan_completion(self, scan_id: str, scan_type: str) -> None:
        """Wait for scan to complete."""
        max_wait = self.config["scans"]["max_scan_duration"]
        wait_time = 0

        while wait_time < max_wait:
            status = {}
            if self.zap_client:
                status = await self.zap_client.get_scan_status(scan_id, scan_type)

            if status:
                progress = status.get("status", "0")
                if progress == "100":
                    logger.info("%s scan completed", scan_type.capitalize())
                    return
                logger.info("%s scan progress: %s%", scan_type.capitalize(), progress)

            await asyncio.sleep(10)
            wait_time += 10

        logger.warning(
            "%s scan timed out after %s seconds", scan_type.capitalize(), max_wait
        )

    def _parse_alerts(self, alerts: list[dict[str, Any]]) -> list[Vulnerability]:
        """Parse ZAP alerts into vulnerability objects."""
        vulnerabilities = []

        for alert in alerts:
            try:
                severity_map = {
                    "High": VulnerabilitySeverity.HIGH,
                    "Medium": VulnerabilitySeverity.MEDIUM,
                    "Low": VulnerabilitySeverity.LOW,
                    "Informational": VulnerabilitySeverity.INFORMATIONAL,
                }

                vulnerability = Vulnerability(
                    vulnerability_id=alert.get("id", ""),
                    name=alert.get("name", ""),
                    description=alert.get("description", ""),
                    severity=severity_map.get(
                        alert.get("risk", ""), VulnerabilitySeverity.LOW
                    ),
                    url=alert.get("url", ""),
                    parameter=alert.get("param", ""),
                    evidence=alert.get("evidence", ""),
                    confidence=alert.get("confidence", ""),
                    cwe_id=alert.get("cweid", ""),
                    wasc_id=alert.get("wascid", ""),
                    solution=alert.get("solution", ""),
                    reference=alert.get("reference", ""),
                    tags=alert.get("tags", []),
                )

                vulnerabilities.append(vulnerability)

            except (ValueError, RuntimeError) as e:
                logger.warning("Error parsing alert: %s", e)

        return vulnerabilities

    async def generate_reports(self, scan_result: ScanResult) -> dict[str, str]:
        """Generate security reports."""
        reports = {}

        if not self.zap_client:
            return reports

        output_dir = Path(self.config["reporting"]["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        for format_type in self.config["reporting"]["formats"]:
            try:
                report_content = await self.zap_client.generate_report(format_type)

                if report_content:
                    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                    filename = (
                        f"dast_report_{scan_result.scan_name}_{timestamp}.{format_type}"
                    )
                    filepath = output_dir / filename

                    with open(filepath, "w") as f:
                        f.write(report_content)

                    reports[format_type] = str(filepath)
                    logger.info("Generated %s report: %s", format_type, filepath)

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.error("Error generating %s report: %s", format_type, e)

        return reports

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.zap_client:
            await self.zap_client.stop_zap()


class VulnerabilityTriageSystem:
    """System for triaging and tracking vulnerability remediation."""

    def __init__(self, triage_file: str = "vulnerability_triage.yaml") -> None:
        self.triage_file = triage_file
        self.vulnerabilities: list[Vulnerability] = []
        self._load_triage_data()

    def _load_triage_data(self) -> None:
        """Load existing triage data."""
        if Path(self.triage_file).exists():
            try:
                with open(self.triage_file) as f:
                    data = json.load(f)
                    for vuln_data in data.get("vulnerabilities", []):
                        vuln = Vulnerability(**vuln_data)
                        self.vulnerabilities.append(vuln)
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Could not load triage data: %s", e)

    def _save_triage_data(self) -> None:
        """Save triage data."""
        try:
            data = {
                "vulnerabilities": [
                    {
                        "vulnerability_id": v.vulnerability_id,
                        "name": v.name,
                        "description": v.description,
                        "severity": v.severity.value,
                        "status": v.status.value,
                        "url": v.url,
                        "parameter": v.parameter,
                        "evidence": v.evidence,
                        "confidence": v.confidence,
                        "cwe_id": v.cwe_id,
                        "wasc_id": v.wasc_id,
                        "solution": v.solution,
                        "reference": v.reference,
                        "tags": v.tags,
                        "first_seen": v.first_seen.isoformat(),
                        "last_seen": v.last_seen.isoformat(),
                        "assigned_to": v.assigned_to,
                        "remediation_notes": v.remediation_notes,
                    }
                    for v in self.vulnerabilities
                ]
            }

            with open(self.triage_file, "w") as f:
                json.dump(data, f, indent=2)

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Error saving triage data: %s", e)

    def add_vulnerabilities(self, vulnerabilities: list[Vulnerability]) -> None:
        """Add new vulnerabilities to triage system."""
        for new_vuln in vulnerabilities:
            # Check if vulnerability already exists
            existing = next(
                (
                    v
                    for v in self.vulnerabilities
                    if v.vulnerability_id == new_vuln.vulnerability_id
                ),
                None,
            )

            if existing:
                # Update existing vulnerability
                existing.last_seen = datetime.now(UTC)
                if existing.status == VulnerabilityStatus.RESOLVED:
                    existing.status = VulnerabilityStatus.OPEN  # Reopened
            else:
                # Add new vulnerability
                self.vulnerabilities.append(new_vuln)

        self._save_triage_data()

    def get_open_vulnerabilities(self) -> list[Vulnerability]:
        """Get all open vulnerabilities."""
        return [v for v in self.vulnerabilities if v.status == VulnerabilityStatus.OPEN]

    def get_critical_vulnerabilities(self) -> list[Vulnerability]:
        """Get critical and high severity vulnerabilities."""
        return [
            v
            for v in self.vulnerabilities
            if v.severity
            in [VulnerabilitySeverity.CRITICAL, VulnerabilitySeverity.HIGH]
            and v.status == VulnerabilityStatus.OPEN
        ]

    def update_vulnerability_status(
        self,
        vulnerability_id: str,
        status: VulnerabilityStatus,
        notes: str | None = None,
    ) -> bool:
        """Update vulnerability status."""
        vuln = next(
            (v for v in self.vulnerabilities if v.vulnerability_id == vulnerability_id),
            None,
        )

        if vuln:
            vuln.status = status
            if notes:
                vuln.remediation_notes.append(
                    f"{datetime.now(UTC).isoformat()}: {notes}"
                )
            self._save_triage_data()
            return True

        return False


# Global instances
dast_runner: PAKEDASTRunner | None = None
triage_system: VulnerabilityTriageSystem | None = None


async def initialize_dast_system(config_file: str | None = None) -> bool:
    """Initialize the DAST system."""
    global dast_runner, triage_system

    try:
        dast_runner = PAKEDASTRunner(config_file)
        triage_system = VulnerabilityTriageSystem()

        if await dast_runner.initialize():
            logger.info("DAST system initialized successfully")
            return True
        logger.error("Failed to initialize DAST system")
        return False

    except (ValueError, RuntimeError) as e:
        logger.error("Error initializing DAST system: %s", e)
        return False


async def run_dast_scan(
    target_url: str, scan_name: str, environment: str = "staging"
) -> ScanResult | None:
    """Run DAST scan for specified target."""
    if not dast_runner:
        logger.error("DAST system not initialized")
        return None

    try:
        config = ScanConfiguration(
            target_url=target_url, scan_name=scan_name, scan_type="active"
        )

        scan_result = await dast_runner.run_scan(config)

        # Generate reports
        reports = await dast_runner.generate_reports(scan_result)
        logger.info("Generated reports: %s", list(reports.keys()))

        # Add vulnerabilities to triage system
        if triage_system and scan_result.vulnerabilities:
            triage_system.add_vulnerabilities(scan_result.vulnerabilities)

        return scan_result

    except (ValueError, RuntimeError) as e:
        logger.error("Error running DAST scan: %s", e)
        return None


async def cleanup_dast_system() -> None:
    """Cleanup DAST system resources."""
    global dast_runner

    if dast_runner:
        await dast_runner.cleanup()


if __name__ == "__main__":
    # Example usage
    async def main(self) -> None:
        # Initialize DAST system
        if await initialize_dast_system():
            # Run scan
            scan_result = await run_dast_scan(
                target_url="http://localhost:3001", scan_name="staging_security_scan"
            )

            if scan_result:
                print(f"Scan completed: {scan_result.scan_name}")
                print(f"Vulnerabilities found: {scan_result.total_alerts}")
                print(f"High severity: {scan_result.high_severity_count}")
                print(f"Medium severity: {scan_result.medium_severity_count}")
                print(f"Low severity: {scan_result.low_severity_count}")

            # Cleanup
            await cleanup_dast_system()

    asyncio.run(main())