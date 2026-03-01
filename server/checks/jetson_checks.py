"""
Jetson health checks: boot status, resources, temperature.
"""

import subprocess
import psutil
from .base_check import BaseCheck
from common.constants import CATEGORY_JETSON


class JetsonBootCheck(BaseCheck):
    """Check Jetson boot logs for critical errors"""

    category = CATEGORY_JETSON

    def run(self) -> bool:
        try:
            # Check dmesg for critical errors
            result = subprocess.run(
                ['dmesg', '--level=err,crit,alert,emerg'],
                capture_output=True,
                text=True,
                timeout=self.config.get('timeouts', {}).get('command', 10)
            )

            error_lines = [line for line in result.stdout.strip().split('\n') if line]

            # Filter out known harmless errors (customize as needed)
            critical_errors = []
            for line in error_lines:
                # Skip empty lines
                if not line.strip():
                    continue
                # Add filters for known harmless errors here
                # Example: if 'firmware' in line.lower() and 'optional' in line.lower():
                #     continue
                critical_errors.append(line)

            if not critical_errors:
                self.status = "passed"
                self.message = "No critical boot errors found"
                self.details["total_error_lines"] = len(error_lines)
            elif len(critical_errors) < 3:
                self.status = "warning"
                self.message = f"Found {len(critical_errors)} potential error(s)"
                self.details["errors"] = critical_errors[:5]  # Limit to first 5
            else:
                self.status = "failed"
                self.message = f"Found {len(critical_errors)} critical error(s)"
                self.details["errors"] = critical_errors[:10]  # Limit to first 10

            return self.status in ["passed", "warning"]

        except subprocess.TimeoutExpired:
            self.status = "failed"
            self.message = "dmesg command timed out"
            return False
        except FileNotFoundError:
            self.skip("dmesg command not found (not running on Linux?)")
            return False
        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking boot logs: {e}"
            return False


class JetsonResourcesCheck(BaseCheck):
    """Check Jetson CPU, RAM, and Disk usage"""

    category = CATEGORY_JETSON

    def run(self) -> bool:
        try:
            resources_config = self.config.get('resources', {})
            cpu_max = resources_config.get('cpu_max_percent', 90)
            ram_max = resources_config.get('ram_max_percent', 85)
            disk_min_free = resources_config.get('disk_min_free_gb', 5)

            # Get CPU usage (averaged over 1 second)
            cpu_percent = psutil.cpu_percent(interval=1)

            # Get RAM usage
            ram = psutil.virtual_memory()
            ram_percent = ram.percent

            # Get disk usage (root partition)
            disk = psutil.disk_usage('/')
            disk_free_gb = disk.free / (1024**3)
            disk_percent = disk.percent

            # Store details
            self.details = {
                "cpu_percent": round(cpu_percent, 1),
                "ram_percent": round(ram_percent, 1),
                "ram_used_gb": round(ram.used / (1024**3), 2),
                "ram_total_gb": round(ram.total / (1024**3), 2),
                "disk_free_gb": round(disk_free_gb, 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_percent": round(disk_percent, 1)
            }

            # Check thresholds
            issues = []
            if cpu_percent > cpu_max:
                issues.append(f"CPU usage high: {cpu_percent:.1f}% (max: {cpu_max}%)")

            if ram_percent > ram_max:
                issues.append(f"RAM usage high: {ram_percent:.1f}% (max: {ram_max}%)")

            if disk_free_gb < disk_min_free:
                issues.append(f"Disk space low: {disk_free_gb:.2f} GB free (min: {disk_min_free} GB)")

            if issues:
                self.status = "failed"
                self.message = "; ".join(issues)
                return False
            else:
                self.status = "passed"
                self.message = f"Resources OK (CPU: {cpu_percent:.1f}%, RAM: {ram_percent:.1f}%, Disk: {disk_free_gb:.1f} GB free)"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking resources: {e}"
            return False


class JetsonTemperatureCheck(BaseCheck):
    """Check Jetson temperature and throttling status"""

    category = CATEGORY_JETSON

    def run(self) -> bool:
        try:
            temp_max = self.config.get('resources', {}).get('temp_max_celsius', 80)

            # Read thermal zones
            temps = []
            thermal_zone_path = '/sys/class/thermal'

            try:
                for i in range(20):  # Check up to 20 thermal zones
                    temp_file = f'{thermal_zone_path}/thermal_zone{i}/temp'
                    try:
                        with open(temp_file, 'r') as f:
                            temp_millicelsius = int(f.read().strip())
                            temp_celsius = temp_millicelsius / 1000.0
                            temps.append(temp_celsius)
                    except FileNotFoundError:
                        break  # No more thermal zones
                    except (ValueError, IOError):
                        continue  # Skip invalid thermal zones

            except Exception as e:
                self.details["thermal_read_error"] = str(e)

            if not temps:
                self.skip("No thermal zones found")
                return False

            max_temp = max(temps)
            avg_temp = sum(temps) / len(temps)

            self.details = {
                "temperatures_celsius": [round(t, 1) for t in temps],
                "max_temp": round(max_temp, 1),
                "avg_temp": round(avg_temp, 1),
                "num_zones": len(temps)
            }

            if max_temp > temp_max:
                self.status = "failed"
                self.message = f"Temperature too high: {max_temp:.1f}°C (max: {temp_max}°C)"
                return False
            elif max_temp > temp_max * self.config.get('resources', {}).get('temp_warning_percent', 90) / 100.0:
                self.warn(
                    f"Temperature approaching limit: {max_temp:.1f}°C (max: {temp_max}°C)",
                    self.details
                )
                return True
            else:
                self.status = "passed"
                self.message = f"Temperature OK: {max_temp:.1f}°C (max: {temp_max}°C)"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking temperature: {e}"
            return False
