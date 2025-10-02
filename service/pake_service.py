#!/usr/bin/env python3
"""
PAKE Knowledge Vault Auto-Processing Service
Windows Service that automatically monitors and processes vault changes
Runs continuously in background without user intervention
"""

import asyncio
import logging
import os
import sys
import time
import threading
from pathlib import Path
import json
import traceback
from datetime import datetime

# Service-specific imports
import win32serviceutil
import win32service
import win32event
import servicemanager

# Add PAKE system to path
pake_path = Path("D:/Projects/PAKE_SYSTEM/scripts")
if str(pake_path) not in sys.path:
    sys.path.insert(0, str(pake_path))

# Set service environment variable
os.environ['RUNNING_AS_SERVICE'] = 'true'

from service_enhanced_vault_watcher import ServiceEnhancedVaultWatcher as VaultWatcher

class PAKEService(win32serviceutil.ServiceFramework):
    """Windows Service for PAKE Knowledge Vault Automation"""

    _svc_name_ = "PAKEKnowledgeService"
    _svc_display_name_ = "PAKE Knowledge Vault Auto-Processor"
    _svc_description_ = "Automatically processes and enhances knowledge vault content with AI analysis, vector embeddings, and knowledge graph updates"
    _svc_deps_ = None  # No dependencies

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = False
        self.vault_watcher = None
        self.monitoring_thread = None

        # Setup service logging
        self.setup_service_logging()

        # Configuration
        self.config = {
            'vault_path': 'D:/Knowledge-Vault',
            'pake_system_path': 'D:/Projects/PAKE_SYSTEM',
            'check_interval': 2,  # seconds
            'health_check_interval': 30,  # seconds
            'max_restart_attempts': 5,
            'restart_delay': 10  # seconds
        }

        self.restart_attempts = 0
        self.last_restart = None

        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTING,
            (self._svc_name_, f"PAKE Service initialized - Monitoring {self.config['vault_path']}")
        )

    def setup_service_logging(self):
        """Setup comprehensive logging for the service"""
        log_dir = Path("D:/Projects/PAKE_SYSTEM/logs")
        log_dir.mkdir(exist_ok=True)

        # Service-specific log file
        log_file = log_dir / "pake_service.log"

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger('PAKEService')
        self.logger.info("Service logging initialized")

    def SvcStop(self):
        """Stop the service"""
        self.logger.info("Service stop requested")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPING,
            (self._svc_name_, "PAKE Service stopping...")
        )

        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_running = False
        win32event.SetEvent(self.hWaitStop)

        # Stop vault watcher
        if self.vault_watcher:
            try:
                self.vault_watcher.stop()
                self.logger.info("Vault watcher stopped")
            except Exception as e:
                self.logger.error(f"Error stopping vault watcher: {e}")

        self.logger.info("Service stopped successfully")

    def SvcDoRun(self):
        """Main service execution"""
        self.logger.info("Starting PAKE Knowledge Vault Service")
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "PAKE Service started successfully")
        )

        self.is_running = True

        try:
            # Initialize monitoring in separate thread
            self.monitoring_thread = threading.Thread(target=self.run_monitoring, daemon=True)
            self.monitoring_thread.start()

            # Service main loop - wait for stop signal
            while self.is_running:
                # Wait for stop event with timeout for health checks
                rc = win32event.WaitForSingleObject(self.hWaitStop, self.config['health_check_interval'] * 1000)

                if rc == win32event.WAIT_OBJECT_0:
                    # Stop event signaled
                    break
                elif rc == win32event.WAIT_TIMEOUT:
                    # Timeout - perform health check
                    self.perform_health_check()

        except Exception as e:
            self.logger.error(f"Service execution error: {e}")
            self.logger.error(traceback.format_exc())
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_ERROR_TYPE,
                servicemanager.PYS_SERVICE_STOPPING,
                (self._svc_name_, f"Service error: {str(e)}")
            )
        finally:
            self.is_running = False
            self.logger.info("Service execution completed")

    def run_monitoring(self):
        """Run the vault monitoring in async context"""
        self.logger.info("Starting vault monitoring thread")

        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the async monitoring
            loop.run_until_complete(self.async_monitoring())

        except Exception as e:
            self.logger.error(f"Monitoring thread error: {e}")
            self.logger.error(traceback.format_exc())

            # Attempt restart if within limits
            if self.should_attempt_restart():
                self.restart_monitoring()
        finally:
            try:
                loop.close()
            except:
                pass

    async def async_monitoring(self):
        """Async vault monitoring and processing"""
        self.logger.info(f"Initializing vault watcher for {self.config['vault_path']}")

        try:
            # Initialize vault watcher
            self.vault_watcher = VaultWatcher(self.config['vault_path'])

            # Start continuous monitoring
            self.logger.info("Starting continuous vault monitoring...")

            while self.is_running:
                try:
                    # Run one cycle of monitoring
                    await self.vault_watcher.run_monitoring_cycle()

                    # Wait before next cycle
                    await asyncio.sleep(self.config['check_interval'])

                except Exception as e:
                    self.logger.error(f"Monitoring cycle error: {e}")
                    await asyncio.sleep(5)  # Brief pause before retry

        except Exception as e:
            self.logger.error(f"Vault monitoring initialization error: {e}")
            raise

    def should_attempt_restart(self):
        """Check if we should attempt to restart monitoring"""
        now = datetime.now()

        # Reset counter if enough time has passed
        if self.last_restart and (now - self.last_restart).total_seconds() > 300:  # 5 minutes
            self.restart_attempts = 0

        # Check if we're within restart limits
        if self.restart_attempts < self.config['max_restart_attempts']:
            self.restart_attempts += 1
            self.last_restart = now
            return True

        self.logger.error(f"Maximum restart attempts ({self.config['max_restart_attempts']}) reached")
        return False

    def restart_monitoring(self):
        """Restart the monitoring thread"""
        self.logger.info(f"Attempting to restart monitoring (attempt {self.restart_attempts})")

        try:
            # Wait before restart
            time.sleep(self.config['restart_delay'])

            # Start new monitoring thread
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.logger.info("Previous monitoring thread still running, waiting...")
                time.sleep(5)

            self.monitoring_thread = threading.Thread(target=self.run_monitoring, daemon=True)
            self.monitoring_thread.start()

            self.logger.info("Monitoring thread restarted successfully")

        except Exception as e:
            self.logger.error(f"Failed to restart monitoring: {e}")

    def perform_health_check(self):
        """Perform periodic health checks"""
        try:
            # Check if monitoring thread is alive
            if not self.monitoring_thread or not self.monitoring_thread.is_alive():
                self.logger.warning("Monitoring thread is not running, attempting restart...")
                if self.should_attempt_restart():
                    self.restart_monitoring()

            # Check vault path accessibility
            vault_path = Path(self.config['vault_path'])
            if not vault_path.exists():
                self.logger.error(f"Vault path not accessible: {vault_path}")

            # Log health status
            status = {
                'timestamp': datetime.now().isoformat(),
                'monitoring_thread_alive': self.monitoring_thread and self.monitoring_thread.is_alive(),
                'vault_accessible': vault_path.exists(),
                'restart_attempts': self.restart_attempts,
                'service_running': self.is_running
            }

            self.logger.debug(f"Health check: {status}")

            # Write health status to file
            health_file = Path("D:/Projects/PAKE_SYSTEM/logs/service_health.json")
            with open(health_file, 'w') as f:
                json.dump(status, f, indent=2)

        except Exception as e:
            self.logger.error(f"Health check error: {e}")

def main():
    """Main service entry point"""
    if len(sys.argv) == 1:
        # Service is starting via Windows Service Manager
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PAKEService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Command line - handle install/remove/debug
        win32serviceutil.HandleCommandLine(PAKEService)

if __name__ == '__main__':
    main()