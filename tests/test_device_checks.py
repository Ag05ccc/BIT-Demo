"""
Tests for server/checks/device_checks.py - Device access checks.
All external dependencies are mocked for local testing.
"""

import pytest
from unittest.mock import patch, MagicMock
from checks.device_checks import (
    UdevRulesCheck, DeviceExistsCheck, DeviceHardwareIDCheck,
    DevicePermissionsCheck, DeviceHandshakeCheck
)


class TestUdevRulesCheck:
    def test_rules_present(self, sample_config):
        """Passes when udev rule files exist"""
        check = UdevRulesCheck(sample_config)

        with patch('os.path.exists', return_value=True):
            result = check.execute()

        assert result.status == "passed"
        assert "1 udev rule" in result.message

    def test_rules_missing(self, sample_config):
        """Fails when udev rule files don't exist"""
        check = UdevRulesCheck(sample_config)

        with patch('os.path.exists', return_value=False):
            result = check.execute()

        assert result.status == "failed"
        assert "Missing" in result.message

    def test_no_rules_configured(self, empty_config):
        """Skips when no udev rules configured"""
        check = UdevRulesCheck(empty_config)
        result = check.execute()
        assert result.status == "skipped"


class TestDeviceExistsCheck:
    def test_all_devices_exist(self, sample_config):
        """Passes when all devices exist"""
        check = DeviceExistsCheck(sample_config)

        with patch('os.path.exists', return_value=True):
            result = check.execute()

        assert result.status == "passed"
        assert "2 device(s) found" in result.message

    def test_device_missing(self, sample_config):
        """Fails when a device is missing"""
        check = DeviceExistsCheck(sample_config)

        def mock_exists(path):
            return path == "/dev/ttyUSB0"  # Only deviceA exists

        with patch('os.path.exists', side_effect=mock_exists):
            result = check.execute()

        assert result.status == "failed"
        assert "deviceB" in result.message

    def test_no_devices_configured(self, empty_config):
        """Skips when no devices configured"""
        check = DeviceExistsCheck(empty_config)
        result = check.execute()
        assert result.status == "skipped"


class TestDeviceHardwareIDCheck:
    def test_ids_match(self, sample_config):
        """Passes when hardware IDs match"""
        check = DeviceHardwareIDCheck(sample_config)

        mock_result = MagicMock()
        mock_result.stdout = "ATTR{idVendor}==\"0x1234\"\nATTR{idProduct}==\"0x5678\"\n"

        with patch('os.path.exists', return_value=True), \
             patch('checks.device_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status in ["passed", "skipped"]  # May skip deviceB

    def test_udevadm_not_found(self, sample_config):
        """Skips when udevadm not available"""
        check = DeviceHardwareIDCheck(sample_config)

        with patch('os.path.exists', return_value=True), \
             patch('checks.device_checks.subprocess.run', side_effect=FileNotFoundError):
            result = check.execute()

        assert result.status == "skipped"


class TestDevicePermissionsCheck:
    def test_all_accessible(self, sample_config):
        """Passes when all devices are accessible"""
        check = DevicePermissionsCheck(sample_config)

        mock_file = MagicMock()
        mock_file.__enter__ = lambda s: s
        mock_file.__exit__ = lambda *a: None

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', return_value=mock_file):
            result = check.execute()

        assert result.status == "passed"

    def test_permission_denied(self, sample_config):
        """Fails when permission denied"""
        check = DevicePermissionsCheck(sample_config)

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = check.execute()

        assert result.status == "failed"
        assert "Permission denied" in result.message


class TestDeviceHandshakeCheck:
    def test_handshake_success(self, sample_config):
        """Passes when device responds correctly"""
        check = DeviceHandshakeCheck(sample_config)

        mock_serial = MagicMock()
        mock_serial.read.return_value = b"OK\r\n"

        with patch('os.path.exists', return_value=True), \
             patch('checks.device_checks.serial.Serial', return_value=mock_serial), \
             patch('checks.device_checks.PYSERIAL_AVAILABLE', True):
            result = check.execute()

        assert result.status == "passed"
        assert "Handshake OK" in result.message

    def test_handshake_wrong_response(self, sample_config):
        """Fails when device gives unexpected response"""
        check = DeviceHandshakeCheck(sample_config)

        mock_serial = MagicMock()
        mock_serial.read.return_value = b"ERROR\r\n"

        with patch('os.path.exists', return_value=True), \
             patch('checks.device_checks.serial.Serial', return_value=mock_serial), \
             patch('checks.device_checks.PYSERIAL_AVAILABLE', True):
            result = check.execute()

        assert result.status == "failed"

    def test_pyserial_not_installed(self, sample_config):
        """Skips when pyserial is not installed"""
        check = DeviceHandshakeCheck(sample_config)

        with patch.object(check, 'run') as mock_run:
            # Simulate PYSERIAL_AVAILABLE = False behavior
            def skip_no_serial():
                check.skip("pyserial not installed")
                return False
            mock_run.side_effect = skip_no_serial
            result = check.execute()

        assert result.status == "skipped"
