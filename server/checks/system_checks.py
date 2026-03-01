"""
System checks: services, environment variables, time, scripts, metadata.
"""

import os
import subprocess
import time
from datetime import datetime
from .base_check import BaseCheck
from common.constants import CATEGORY_SYSTEM


class SystemdServicesCheck(BaseCheck):
    """Check if systemd services are active"""

    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        try:
            services = self.config.get('systemd_services', [])

            if not services:
                self.skip("No systemd services configured")
                return False

            active = []
            inactive = []

            cmd_timeout = self.config.get('timeouts', {}).get('command', 10)

            for service in services:
                try:
                    result = subprocess.run(
                        ['systemctl', 'is-active', service],
                        capture_output=True,
                        text=True,
                        timeout=cmd_timeout
                    )

                    if result.stdout.strip() == 'active':
                        active.append(service)
                    else:
                        inactive.append(service)

                except subprocess.TimeoutExpired:
                    inactive.append(service)
                except Exception:
                    inactive.append(service)

            self.details = {
                "active": active,
                "inactive": inactive
            }

            if inactive:
                self.status = "failed"
                self.message = f"Inactive services: {', '.join(inactive)}"
                return False
            else:
                self.status = "passed"
                self.message = f"All {len(active)} service(s) active"
                return True

        except FileNotFoundError:
            self.skip("systemctl not found")
            return False
        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking services: {e}"
            return False


class EnvironmentCheck(BaseCheck):
    """Check if required environment variables are set"""

    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        try:
            env_vars = self.config.get('environment_vars', {})

            if not env_vars:
                self.skip("No environment variables configured")
                return False

            correct = {}
            incorrect = {}
            missing = []

            for var_name, expected_value in env_vars.items():
                actual_value = os.environ.get(var_name)

                if actual_value is None:
                    missing.append(var_name)
                elif actual_value == expected_value:
                    correct[var_name] = actual_value
                else:
                    incorrect[var_name] = {
                        "expected": expected_value,
                        "actual": actual_value
                    }

            self.details = {
                "correct": correct,
                "incorrect": incorrect,
                "missing": missing
            }

            issues = []
            if missing:
                issues.append(f"Missing: {', '.join(missing)}")
            if incorrect:
                issues.append(f"Incorrect: {', '.join(incorrect.keys())}")

            if issues:
                self.status = "failed"
                self.message = "; ".join(issues)
                return False
            else:
                self.status = "passed"
                self.message = f"All {len(correct)} environment variable(s) correct"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking environment: {e}"
            return False


class TimeCheck(BaseCheck):
    """Check system time and NTP sync"""

    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        try:
            # Check if time seems reasonable (after 2020)
            current_time = time.time()
            if current_time < 1577836800:  # 2020-01-01
                self.status = "failed"
                self.message = "System time is not set correctly"
                return False

            # Check NTP sync (if available)
            ntp_synced = False
            try:
                cmd_timeout = self.config.get('timeouts', {}).get('command', 10)
                result = subprocess.run(
                    ['timedatectl', 'status'],
                    capture_output=True,
                    text=True,
                    timeout=cmd_timeout
                )

                if 'NTP synchronized: yes' in result.stdout or 'System clock synchronized: yes' in result.stdout:
                    ntp_synced = True

            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass  # timedatectl not available

            self.details = {
                "current_time": datetime.utcnow().isoformat(),
                "ntp_synced": ntp_synced
            }

            if ntp_synced:
                self.status = "passed"
                self.message = "Time OK, NTP synchronized"
                return True
            else:
                self.warn("Time OK, but NTP sync status unknown")
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking time: {e}"
            return False


class StartupScriptCheck(BaseCheck):
    """Execute start_system.sh script"""

    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        try:
            script_path = self.config.get('scripts', {}).get('startup')

            if not script_path:
                self.skip("Startup script not configured")
                return False

            if not os.path.exists(script_path):
                self.status = "failed"
                self.message = f"Script not found: {script_path}"
                return False

            # Execute script
            script_timeout = self.config.get('timeouts', {}).get('script', 60)
            result = subprocess.run(
                [script_path],
                capture_output=True,
                text=True,
                timeout=script_timeout
            )

            self.details = {
                "script": script_path,
                "exit_code": result.returncode,
                "stdout": result.stdout[:500],  # Limit output
                "stderr": result.stderr[:500]
            }

            if result.returncode == 0:
                self.status = "passed"
                self.message = "Startup script executed successfully"
                return True
            else:
                self.status = "failed"
                self.message = f"Script failed with exit code {result.returncode}"
                return False

        except subprocess.TimeoutExpired:
            self.status = "failed"
            self.message = "Script execution timed out"
            return False
        except Exception as e:
            self.status = "failed"
            self.message = f"Error executing script: {e}"
            return False


class LoggingCheck(BaseCheck):
    """Run log_test.sh script"""

    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        try:
            script_path = self.config.get('scripts', {}).get('log_test')

            if not script_path:
                self.skip("Log test script not configured")
                return False

            if not os.path.exists(script_path):
                self.status = "failed"
                self.message = f"Script not found: {script_path}"
                return False

            # Execute script
            script_timeout = self.config.get('timeouts', {}).get('script', 60)
            result = subprocess.run(
                [script_path],
                capture_output=True,
                text=True,
                timeout=script_timeout
            )

            self.details = {
                "script": script_path,
                "exit_code": result.returncode,
                "stdout": result.stdout[:500],
                "stderr": result.stderr[:500]
            }

            if result.returncode == 0:
                self.status = "passed"
                self.message = "Logging check passed"
                return True
            else:
                self.status = "failed"
                self.message = f"Logging check failed with exit code {result.returncode}"
                return False

        except subprocess.TimeoutExpired:
            self.status = "failed"
            self.message = "Logging check timed out"
            return False
        except Exception as e:
            self.status = "failed"
            self.message = f"Error running logging check: {e}"
            return False


class MetadataCaptureCheck(BaseCheck):
    """Capture system metadata (config version, git commit, etc.)"""

    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        try:
            metadata = {
                "timestamp": datetime.utcnow().isoformat(),
                "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown"
            }

            # Try to get git commit hash (if in a git repo)
            try:
                cmd_timeout = self.config.get('timeouts', {}).get('command', 10)
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    capture_output=True,
                    text=True,
                    timeout=cmd_timeout,
                    cwd=os.path.dirname(__file__)
                )
                if result.returncode == 0:
                    metadata["git_commit"] = result.stdout.strip()[:8]
            except (FileNotFoundError, subprocess.TimeoutExpired):
                metadata["git_commit"] = "unknown"

            # Add config info
            metadata["config_file"] = "config.json"

            self.details = metadata
            self.status = "passed"
            self.message = "Metadata captured"
            return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error capturing metadata: {e}"
            return False
