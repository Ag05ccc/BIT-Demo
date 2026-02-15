"""
Device checks: udev rules, /dev/ devices, permissions, handshake tests.
"""

import os
import subprocess
import glob
from .base_check import BaseCheck
from common.constants import CATEGORY_DEVICE

try:
    import serial
    PYSERIAL_AVAILABLE = True
except ImportError:
    PYSERIAL_AVAILABLE = False


class UdevRulesCheck(BaseCheck):
    """Check if udev rules are loaded"""

    category = CATEGORY_DEVICE

    def run(self) -> bool:
        try:
            rules_files = self.config.get('udev_rules', [])

            if not rules_files:
                self.skip("No udev rules configured to check")
                return False

            missing = []
            loaded = []

            for rules_file in rules_files:
                if os.path.exists(rules_file):
                    loaded.append(rules_file)
                else:
                    missing.append(rules_file)

            self.details = {
                "expected_rules": rules_files,
                "loaded": loaded,
                "missing": missing
            }

            if missing:
                self.status = "failed"
                self.message = f"Missing udev rules: {', '.join(missing)}"
                return False
            else:
                self.status = "passed"
                self.message = f"{len(loaded)} udev rule(s) found"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking udev rules: {e}"
            return False


class DeviceExistsCheck(BaseCheck):
    """Check if required /dev/ devices exist"""

    category = CATEGORY_DEVICE

    def run(self) -> bool:
        try:
            devices_config = self.config.get('devices', {})

            if not devices_config:
                self.skip("No devices configured to check")
                return False

            missing = []
            found = []

            for device_name, device_info in devices_config.items():
                device_path = device_info.get('path')
                if not device_path:
                    continue

                if os.path.exists(device_path):
                    found.append({
                        "name": device_name,
                        "path": device_path,
                        "description": device_info.get('description', '')
                    })
                else:
                    missing.append({
                        "name": device_name,
                        "path": device_path,
                        "description": device_info.get('description', '')
                    })

            self.details = {
                "found": found,
                "missing": missing
            }

            if missing:
                self.status = "failed"
                self.message = f"Missing device(s): {', '.join([d['name'] for d in missing])}"
                return False
            else:
                self.status = "passed"
                self.message = f"{len(found)} device(s) found"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking devices: {e}"
            return False


class DeviceHardwareIDCheck(BaseCheck):
    """Check device hardware vendor/product IDs using lsusb or udevadm"""

    category = CATEGORY_DEVICE

    def run(self) -> bool:
        try:
            devices_config = self.config.get('devices', {})

            if not devices_config:
                self.skip("No devices configured to check")
                return False

            matched = []
            mismatched = []

            for device_name, device_info in devices_config.items():
                device_path = device_info.get('path')
                expected_vendor = device_info.get('vendor_id')
                expected_product = device_info.get('product_id')

                # Skip if no hardware IDs configured
                if not expected_vendor or not expected_product:
                    continue

                # Skip if device doesn't exist
                if not os.path.exists(device_path):
                    continue

                # Use udevadm to get device info
                try:
                    result = subprocess.run(
                        ['udevadm', 'info', '--name=' + device_path, '--attribute-walk'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )

                    output = result.stdout

                    # Simple check for vendor/product IDs in output
                    if expected_vendor.lower() in output.lower() and expected_product.lower() in output.lower():
                        matched.append(device_name)
                    else:
                        mismatched.append(device_name)

                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # udevadm not available or timed out
                    self.skip("udevadm not available")
                    return False

            if not matched and not mismatched:
                self.skip("No devices with vendor/product IDs configured")
                return False

            self.details = {
                "matched": matched,
                "mismatched": mismatched
            }

            if mismatched:
                self.status = "failed"
                self.message = f"Hardware ID mismatch for: {', '.join(mismatched)}"
                return False
            else:
                self.status = "passed"
                self.message = f"{len(matched)} device(s) matched hardware IDs"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking hardware IDs: {e}"
            return False


class DevicePermissionsCheck(BaseCheck):
    """Test if devices can be opened without sudo"""

    category = CATEGORY_DEVICE

    def run(self) -> bool:
        try:
            devices_config = self.config.get('devices', {})

            if not devices_config:
                self.skip("No devices configured to check")
                return False

            accessible = []
            inaccessible = []

            for device_name, device_info in devices_config.items():
                device_path = device_info.get('path')

                if not device_path or not os.path.exists(device_path):
                    continue

                # Try to open device
                try:
                    with open(device_path, 'rb') as f:
                        # Just try to open, don't read
                        pass
                    accessible.append(device_name)
                except PermissionError:
                    inaccessible.append(device_name)
                except Exception:
                    # Other errors (device busy, etc.) still count as accessible permission-wise
                    accessible.append(device_name)

            self.details = {
                "accessible": accessible,
                "inaccessible": inaccessible
            }

            if inaccessible:
                self.status = "failed"
                self.message = f"Permission denied for: {', '.join(inaccessible)}"
                self.details["fix_hint"] = "Check udev rules and user groups"
                return False
            else:
                self.status = "passed"
                self.message = f"{len(accessible)} device(s) accessible"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking permissions: {e}"
            return False


class DeviceHandshakeCheck(BaseCheck):
    """Perform basic read/write handshake test with devices"""

    category = CATEGORY_DEVICE

    def run(self) -> bool:
        if not PYSERIAL_AVAILABLE:
            self.skip("pyserial not installed")
            return False

        try:
            devices_config = self.config.get('devices', {})

            if not devices_config:
                self.skip("No devices configured to check")
                return False

            passed = []
            failed = []

            for device_name, device_info in devices_config.items():
                device_path = device_info.get('path')
                test_command = device_info.get('test_command')
                expected_response = device_info.get('expected_response')

                # Skip if no test command configured
                if not test_command or not expected_response:
                    continue

                # Skip if device doesn't exist
                if not os.path.exists(device_path):
                    continue

                try:
                    # Open serial port
                    ser = serial.Serial(
                        port=device_path,
                        baudrate=device_info.get('baudrate', 9600),
                        timeout=2
                    )

                    # Send command
                    ser.write(test_command.encode())

                    # Read response
                    response = ser.read(200).decode('utf-8', errors='ignore')

                    ser.close()

                    # Check response
                    if expected_response in response:
                        passed.append({
                            "device": device_name,
                            "response": response[:100]  # Limit length
                        })
                    else:
                        failed.append({
                            "device": device_name,
                            "expected": expected_response,
                            "got": response[:100]
                        })

                except Exception as e:
                    failed.append({
                        "device": device_name,
                        "error": str(e)
                    })

            if not passed and not failed:
                self.skip("No devices with handshake test configured")
                return False

            self.details = {
                "passed": passed,
                "failed": failed
            }

            if failed:
                self.status = "failed"
                self.message = f"Handshake failed for {len(failed)} device(s)"
                return False
            else:
                self.status = "passed"
                self.message = f"Handshake OK for {len(passed)} device(s)"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error during handshake test: {e}"
            return False
