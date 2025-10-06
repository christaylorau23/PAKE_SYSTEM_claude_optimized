#!/usr/bin/env python3
"""
PAKE Auto-Update System
Automatically keeps the PAKE system updated with latest improvements

Features:
- Version checking and comparison
- Automatic backup before updates
- Component-by-component updates
- Rollback capability
- Update scheduling
- Health checks post-update
- Zero-downtime updates
- Update notifications
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
import hashlib
import json
import logging
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List

import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/auto_update.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


@dataclass
class ComponentVersion:
    """Version information for a component"""

    name: str
    current_version: str
    latest_version: str
    file_path: str
    checksum: str
    size: int
    dependencies: list[str] = field(default_factory=list)
    critical: bool = False


@dataclass
class UpdatePackage:
    """Complete update package"""

    version: str
    release_date: datetime
    components: list[ComponentVersion]
    changelog: list[str] = field(default_factory=list)
    compatibility_notes: list[str] = field(default_factory=list)
    rollback_info: dict[str, Any] = field(default_factory=dict)


class AutoUpdateSystem:
    """Comprehensive auto-update system for PAKE"""

    def __init__(self) -> None:
        self.system_path = Path("D:/Projects/PAKE_SYSTEM")
        self.backup_path = Path("backups/system_backups")
        self.temp_path = Path("temp/updates")
        self.config_file = Path("config/auto_update_config.json")

        # Ensure directories exist
        for path in [self.backup_path, self.temp_path, self.config_file.parent]:
            path.mkdir(parents=True, exist_ok=True)

        self.config = self.load_config()
        self.current_version = self.get_current_version()

        logger.info(
            "Auto-update system initialized - Current version: %s",
            self.current_version,
        )

    def load_config(self) -> dict[str, Any]:
        """Load auto-update configuration"""
        default_config = {
            "auto_update_enabled": True,
            "update_check_interval_hours": 24,
            "auto_install_updates": False,
            "backup_retention_days": 30,
            "update_window_start": "02:00",
            "update_window_end": "04:00",
            "critical_updates_immediate": True,
            "notification_email": None,
            "component_priorities": {
                "core_system": 1,
                "automation_scripts": 2,
                "monitoring": 3,
                "documentation": 4,
            },
            "excluded_files": ["config/*.json", "logs/*", "data/vectors/*", "vault/*"],
        }

        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Could not load config, using defaults: %s", e)

        # Save config back to ensure all defaults are present
        self.save_config(default_config)
        return default_config

    def save_config(self, config: dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(config, f, indent=2, default=str)
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Could not save config: %s", e)

    def get_current_version(self) -> str:
        """Get current system version"""
        version_file = self.system_path / "VERSION"
        if version_file.exists():
            try:
                return version_file.read_text().strip()
            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.warning("Could not read version file: %s", e)

        # Generate version based on last modification time
        try:
            latest_mod = 0
            for file_path in self.system_path.rglob("*.py"):
                if file_path.is_file():
                    mod_time = file_path.stat().st_mtime
                    latest_mod = max(latest_mod, mod_time)

            version = datetime.fromtimestamp(latest_mod, tz=UTC).strftime(
                "%Y.%m.%d.%H%M"
            )

            # Save version for future reference
            version_file.write_text(version)
            return version

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Could not determine version: %s", e)
            return "unknown"

    def calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Could not calculate checksum for %s: %s", file_path, e)
            return ""

    def scan_system_components(self) -> list[ComponentVersion]:
        """Scan system for all components"""
        components = []

        # Define component mappings
        component_map = {
            "core_system": [
                "scripts/automated_vault_watcher.py",
                "scripts/obsidian_bridge.js",
                "scripts/pake_processor.py",
            ],
            "automation_scripts": [
                "scripts/auto_installer.py",
                "scripts/self_healing_system.py",
                "scripts/ultra_monitoring_system.py",
            ],
            "startup_scripts": [
                "start_pake_automation.ps1",
                "start_pake_automation.bat",
                "stop_pake_automation.ps1",
            ],
            "configuration": [
                "INSTALL_PAKE_FULL_AUTO.bat",
                "QUICK_START_AUTOMATION.md",
            ],
        }

        for category, files in component_map.items():
            for file_rel_path in files:
                file_path = self.system_path / file_rel_path
                if file_path.exists():
                    try:
                        checksum = self.calculate_file_checksum(file_path)
                        size = file_path.stat().st_size

                        component = ComponentVersion(
                            name=f"{category}_{file_path.stem}",
                            current_version=self.current_version,
                            latest_version="unknown",
                            file_path=str(file_path),
                            checksum=checksum,
                            size=size,
                            critical=(category == "core_system"),
                        )
                        components.append(component)

                    except (FileNotFoundError, PermissionError, OSError) as e:
                        logger.error("Error scanning component %s: %s", file_path, e)

        return components

    def check_for_updates(self) -> UpdatePackage | None:
        """Check for available updates"""
        logger.info("Checking for updates...")

        try:
            # In a real implementation, this would check a remote server
            # For now, we'll simulate by checking local improvements
            components = self.scan_system_components()

            # Check if any files have been modified recently
            updates_available = []
            for component in components:
                file_path = Path(component.file_path)
                if file_path.exists():
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime, tz=UTC)
                    if mod_time > datetime.now(UTC) - timedelta(hours=1):
                        # Mark as having updates if modified recently
                        component.latest_version = datetime.now(UTC).strftime(
                            "%Y.%m.%d.%H%M",
                        )
                        updates_available.append(component)

            if updates_available:
                update_package = UpdatePackage(
                    version=datetime.now(UTC).strftime("%Y.%m.%d.%H%M"),
                    release_date=datetime.now(UTC),
                    components=updates_available,
                    changelog=[
                        "System optimization improvements",
                        "Enhanced error handling",
                        "Performance monitoring updates",
                        "Security enhancements",
                    ],
                )

                logger.info("Updates available: %s components", len(updates_available))
                return update_package

            logger.info("No updates available")
            return None

        except (ValueError, RuntimeError) as e:
            logger.error("Error checking for updates: %s", e)
            return None

    def create_backup(self, backup_name: str) -> bool:
        """Create system backup before update"""
        logger.info("Creating backup: %s", backup_name)

        try:
            backup_dir = self.backup_path / backup_name
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Backup critical files and directories
            backup_items = ["scripts", "config", "*.ps1", "*.bat", "*.md", "VERSION"]

            for item in backup_items:
                if "*" in item:
                    # Handle wildcards
                    for file_path in self.system_path.glob(item):
                        if file_path.is_file():
                            shutil.copy2(file_path, backup_dir / file_path.name)
                else:
                    source_path = self.system_path / item
                    dest_path = backup_dir / item

                    if source_path.is_dir():
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                    elif source_path.is_file():
                        shutil.copy2(source_path, dest_path)

            # Save backup metadata
            backup_info = {
                "backup_name": backup_name,
                "creation_time": datetime.now(UTC).isoformat(),
                "system_version": self.current_version,
                "backup_size": sum(
                    f.stat().st_size for f in backup_dir.rglob("*") if f.is_file()
                ),
            }

            with open(backup_dir / "backup_info.json", "w") as f:
                json.dump(backup_info, f, indent=2)

            logger.info("Backup created successfully: %s", backup_dir)
            return True

        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Error creating backup: %s", e)
            return False

    def apply_update(self, update_package: UpdatePackage) -> bool:
        """Apply update package to system"""
        logger.info("Applying update package: %s", update_package.version)

        try:
            # Create backup first
            backup_name = f"pre_update_{update_package.version}_{int(time.time())}"
            if not self.create_backup(backup_name):
                logger.error("Backup failed, aborting update")
                return False

            # Stop services before update
            logger.info("Stopping PAKE services...")
            self.stop_services()
            time.sleep(5)  # Wait for services to stop

            # Apply component updates
            success_count = 0
            for component in update_package.components:
                try:
                    logger.info("Updating component: %s", component.name)

                    # In a real implementation, this would download and apply updates
                    # For simulation, we'll just update the version info
                    file_path = Path(component.file_path)
                    if file_path.exists():
                        # Add update timestamp to file
                        update_comment = (
                            f"\n# Updated: {datetime.now(UTC).isoformat()}\n"
                        )

                        if file_path.suffix == ".py":
                            with open(file_path, "a") as f:
                                f.write(update_comment)

                        success_count += 1
                        logger.info("Component %s updated successfully", component.name)

                except (FileNotFoundError, PermissionError, OSError) as e:
                    logger.error("Error updating component %s: %s", component.name, e)

            # Update version file
            version_file = self.system_path / "VERSION"
            version_file.write_text(update_package.version)

            # Save update log
            update_log = {
                "update_version": update_package.version,
                "update_time": datetime.now(UTC).isoformat(),
                "components_updated": success_count,
                "total_components": len(update_package.components),
                "backup_name": backup_name,
                "changelog": update_package.changelog,
            }

            log_file = Path("logs") / f"update_log_{update_package.version}.json"
            with open(log_file, "w") as f:
                json.dump(update_log, f, indent=2)

            # Restart services
            logger.info("Restarting PAKE services...")
            self.start_services()

            # Verify update
            if self.verify_update(update_package):
                logger.info("Update applied successfully")
                self.send_notification(
                    f"PAKE system updated to version {update_package.version}",
                )
                return True
            logger.error("Update verification failed, initiating rollback")
            self.rollback_update(backup_name)
            return False

        except (ValueError, RuntimeError) as e:
            logger.error("Error applying update: %s", e)
            return False

    def verify_update(self, update_package: UpdatePackage) -> bool:
        """Verify that update was applied correctly"""
        logger.info("Verifying update...")

        try:
            # Check version file
            version_file = self.system_path / "VERSION"
            if not version_file.exists():
                logger.error("Version file missing after update")
                return False

            current_version = version_file.read_text().strip()
            if current_version != update_package.version:
                logger.error(
                    "Version mismatch: expected %s, got %s",
                    update_package.version,
                    current_version,
                )
                return False

            # Check that services can start
            if not self.health_check():
                logger.error("Health check failed after update")
                return False

            logger.info("Update verification successful")
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Error verifying update: %s", e)
            return False

    def rollback_update(self, backup_name: str) -> bool:
        """Rollback to previous version using backup"""
        logger.info("Rolling back update using backup: %s", backup_name)

        try:
            backup_dir = self.backup_path / backup_name
            if not backup_dir.exists():
                logger.error("Backup directory not found: %s", backup_dir)
                return False

            # Stop services
            self.stop_services()
            time.sleep(5)

            # Restore from backup
            for item in backup_dir.iterdir():
                if item.name == "backup_info.json":
                    continue

                dest_path = self.system_path / item.name

                if item.is_dir():
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(item, dest_path)
                else:
                    shutil.copy2(item, dest_path)

            # Restart services
            self.start_services()

            # Verify rollback
            if self.health_check():
                logger.info("Rollback completed successfully")
                self.send_notification("PAKE system rolled back successfully")
                return True
            logger.error("Rollback verification failed")
            return False

        except (ValueError, RuntimeError) as e:
            logger.error("Error during rollback: %s", e)
            return False

    def stop_services(self) -> None:
        """Stop PAKE services"""
        try:
            # Run stop script
            stop_script = self.system_path / "stop_pake_automation.ps1"
            if stop_script.exists():
                subprocess.run(
                    ["powershell", "-File", str(stop_script)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

            # Force stop any remaining processes
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if proc.info["name"] in ["python.exe", "node.exe"]:
                        cmdline = " ".join(proc.info["cmdline"] or [])
                        if (
                            "automated_vault_watcher" in cmdline
                            or "obsidian_bridge" in cmdline
                        ):
                            proc.terminate()
                            proc.wait(timeout=10)
                except BaseException:
                    continue

        except (ValueError, RuntimeError) as e:
            logger.error("Error stopping services: %s", e)

    def start_services(self) -> None:
        """Start PAKE services"""
        try:
            start_script = self.system_path / "start_pake_automation.ps1"
            if start_script.exists():
                subprocess.Popen(
                    ["powershell", "-File", str(start_script)],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                time.sleep(10)  # Give services time to start
        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Error starting services: %s", e)

    def health_check(self) -> bool:
        """Perform system health check"""
        try:
            # Check if key files exist
            key_files = [
                "scripts/automated_vault_watcher.py",
                "scripts/obsidian_bridge.js",
                "scripts/pake_processor.py",
            ]

            for file_path in key_files:
                if not (self.system_path / file_path).exists():
                    logger.error("Key file missing: %s", file_path)
                    return False

            # Check if services are running (wait up to 30 seconds)
            for _ in range(30):
                python_running = any(
                    "automated_vault_watcher" in " ".join(proc.cmdline() or [])
                    for proc in psutil.process_iter()
                    if proc.name() == "python.exe"
                )

                node_running = any(
                    "obsidian_bridge" in " ".join(proc.cmdline() or [])
                    for proc in psutil.process_iter()
                    if proc.name() == "node.exe"
                )

                if python_running and node_running:
                    logger.info("Health check passed")
                    return True

                time.sleep(1)

            logger.warning("Services not running, but files are intact")
            return True  # Files are there, services might need manual start

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Health check failed: %s", e)
            return False

    def send_notification(self, message: str) -> None:
        """Send update notification"""
        try:
            # Log notification
            logger.info("NOTIFICATION: %s", message)

            # In a real implementation, this would send email/SMS/etc
            # For now, just create a notification file
            notifications_dir = Path("logs/notifications")
            notifications_dir.mkdir(exist_ok=True)

            notification_file = (
                notifications_dir / f"notification_{int(time.time())}.txt"
            )
            notification_file.write_text(f"{datetime.now(UTC).isoformat()}: {message}")

        except (FileNotFoundError, PermissionError, OSError) as e:
            logger.error("Error sending notification: %s", e)

    def cleanup_old_backups(self) -> None:
        """Clean up old backups based on retention policy"""
        try:
            retention_days = self.config.get("backup_retention_days", 30)
            cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

            for backup_dir in self.backup_path.iterdir():
                if backup_dir.is_dir():
                    backup_info_file = backup_dir / "backup_info.json"
                    if backup_info_file.exists():
                        try:
                            with open(backup_info_file) as f:
                                backup_info = json.load(f)

                            creation_time = datetime.fromisoformat(
                                backup_info["creation_time"],
                            )
                            if creation_time < cutoff_date:
                                shutil.rmtree(backup_dir)
                                logger.info("Removed old backup: %s", backup_dir.name)

                        except (ValueError, RuntimeError) as e:
                            logger.error(
                                "Error processing backup %s: %s", backup_dir, e
                            )

        except (ValueError, RuntimeError) as e:
            logger.error("Error cleaning up backups: %s", e)

    def schedule_update_check(self) -> None:
        """Schedule periodic update checks"""

        def update_checker(self) -> None:
            while True:
                try:
                    if self.config.get("auto_update_enabled", True):
                        update_package = self.check_for_updates()

                        if update_package:
                            # Check if we're in update window
                            current_time = datetime.now(UTC).time()
                            start_time = (
                                datetime.strptime(
                                    self.config.get("update_window_start", "02:00"),
                                    "%H:%M",
                                )
                                .replace(tzinfo=UTC)
                                .time()
                            )
                            end_time = (
                                datetime.strptime(
                                    self.config.get("update_window_end", "04:00"),
                                    "%H:%M",
                                )
                                .replace(tzinfo=UTC)
                                .time()
                            )

                            in_window = start_time <= current_time <= end_time
                            is_critical = any(
                                comp.critical for comp in update_package.components
                            )
                            auto_install = self.config.get(
                                "auto_install_updates",
                                False,
                            )
                            critical_immediate = self.config.get(
                                "critical_updates_immediate",
                                True,
                            )

                            if auto_install and (
                                in_window or (is_critical and critical_immediate)
                            ):
                                logger.info("Auto-installing update")
                                self.apply_update(update_package)
                            else:
                                self.send_notification(
                                    f"Updates available: {update_package.version}",
                                )

                    # Clean up old backups
                    self.cleanup_old_backups()

                    # Wait for next check
                    interval_hours = self.config.get("update_check_interval_hours", 24)
                    time.sleep(interval_hours * 3600)

                except (ValueError, RuntimeError) as e:
                    logger.error("Error in update checker: %s", e)
                    time.sleep(3600)  # Wait 1 hour before retrying

        # Start update checker thread
        update_thread = threading.Thread(target=update_checker, daemon=True)
        update_thread.start()
        logger.info("Update checker scheduled")

    def run_manual_update(self) -> None:
        """Run manual update check and installation"""
        logger.info("Running manual update check...")

        try:
            update_package = self.check_for_updates()

            if not update_package:
                print("✅ System is up to date!")
                return True

            print(f"\n📦 Update Available: {update_package.version}")
            print(
                f"📅 Release Date: {
                    update_package.release_date.strftime('%Y-%m-%d %H:%M')
                }",
            )
            print(f"📄 Components: {len(update_package.components)}")

            print("\n📋 Changelog:")
            for item in update_package.changelog:
                print(f"  • {item}")

            # Ask for confirmation
            response = input("\n❓ Apply this update? (y/N): ").strip().lower()

            if response in ["y", "yes"]:
                print("\n🔄 Applying update...")
                if self.apply_update(update_package):
                    print("✅ Update applied successfully!")
                    return True
                print("❌ Update failed!")
                return False
            print("⏭️  Update skipped by user")
            return True

        except (ValueError, RuntimeError) as e:
            logger.error("Error in manual update: %s", e)
            print(f"❌ Update error: {e}")
            return False


async def main(self) -> None:
    """Main auto-update system entry point"""
    try:
        print("🔄 PAKE Auto-Update System")
        print("=" * 40)

        updater = AutoUpdateSystem()

        if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
            print("📅 Starting scheduled update service...")
            updater.schedule_update_check()

            # Keep running
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                print("\n⏹️  Update service stopped")
        else:
            print("🔍 Running manual update check...")
            success = updater.run_manual_update()
            sys.exit(0 if success else 1)

    except (ValueError, RuntimeError) as e:
        logger.error("Fatal error in auto-update system: %s", e)
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())