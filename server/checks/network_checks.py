"""
Network checks: interface status, connectivity, ping tests.
"""

import subprocess
import socket
from .base_check import BaseCheck
from common.constants import CATEGORY_NETWORK


class NetworkInterfaceCheck(BaseCheck):
    """Check if network interfaces are up"""

    category = CATEGORY_NETWORK

    def run(self) -> bool:
        try:
            # Use ip command to get interface status
            result = subprocess.run(
                ['ip', 'link', 'show'],
                capture_output=True,
                text=True,
                timeout=5
            )

            output = result.stdout

            # Look for interfaces that are UP
            up_interfaces = []
            for line in output.split('\n'):
                if 'state UP' in line:
                    # Extract interface name
                    parts = line.split(':')
                    if len(parts) >= 2:
                        iface_name = parts[1].strip()
                        up_interfaces.append(iface_name)

            self.details = {
                "up_interfaces": up_interfaces,
                "count": len(up_interfaces)
            }

            if not up_interfaces:
                self.status = "failed"
                self.message = "No network interfaces are UP"
                return False
            else:
                self.status = "passed"
                self.message = f"{len(up_interfaces)} interface(s) UP: {', '.join(up_interfaces)}"
                return True

        except subprocess.TimeoutExpired:
            self.status = "failed"
            self.message = "ip command timed out"
            return False
        except FileNotFoundError:
            self.skip("ip command not found")
            return False
        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking network interfaces: {e}"
            return False


class PingTestCheck(BaseCheck):
    """Ping configured targets from Jetson"""

    category = CATEGORY_NETWORK

    def run(self) -> bool:
        try:
            ping_targets = self.config.get('ping_targets', [])

            if not ping_targets:
                self.skip("No ping targets configured")
                return False

            reachable = []
            unreachable = []

            for target in ping_targets:
                try:
                    # Ping with count=3, timeout=3 seconds
                    result = subprocess.run(
                        ['ping', '-c', '3', '-W', '3', target],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        # Extract latency from output if possible
                        latency = None
                        for line in result.stdout.split('\n'):
                            if 'avg' in line or 'rtt' in line:
                                # Example: rtt min/avg/max/mdev = 0.123/0.456/0.789/0.012 ms
                                try:
                                    parts = line.split('=')[1].strip().split('/')
                                    latency = float(parts[1])  # avg
                                except (IndexError, ValueError):
                                    pass
                        reachable.append({"target": target, "latency_ms": latency})
                    else:
                        unreachable.append(target)

                except subprocess.TimeoutExpired:
                    unreachable.append(target)
                except Exception as e:
                    unreachable.append(target)

            self.details = {
                "reachable": reachable,
                "unreachable": unreachable
            }

            if unreachable:
                self.status = "failed"
                self.message = f"Unreachable: {', '.join(unreachable)}"
                return False
            else:
                self.status = "passed"
                self.message = f"All {len(reachable)} target(s) reachable"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error during ping test: {e}"
            return False


class TestPCConnectivityCheck(BaseCheck):
    """Check connectivity to Test PC"""

    category = CATEGORY_NETWORK

    def run(self) -> bool:
        try:
            test_pc_ip = self.config.get('test_pc', {}).get('expected_ip')

            if not test_pc_ip:
                self.skip("Test PC IP not configured")
                return False

            # Try to ping Test PC
            result = subprocess.run(
                ['ping', '-c', '3', '-W', '3', test_pc_ip],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.status = "passed"
                self.message = f"Test PC ({test_pc_ip}) is reachable"
                self.details = {"test_pc_ip": test_pc_ip}
                return True
            else:
                self.status = "failed"
                self.message = f"Test PC ({test_pc_ip}) is NOT reachable"
                self.details = {"test_pc_ip": test_pc_ip}
                return False

        except subprocess.TimeoutExpired:
            self.status = "failed"
            self.message = f"Ping to Test PC timed out"
            return False
        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking Test PC connectivity: {e}"
            return False
