"""
Tests for server/checks/system_checks.py - System checks.
All system commands are mocked for local testing.
"""

import pytest
from unittest.mock import patch, MagicMock
from checks.system_checks import (
    SystemdServicesCheck, EnvironmentCheck, TimeCheck,
    StartupScriptCheck, LoggingCheck, MetadataCaptureCheck
)


class TestSystemdServicesCheck:
    def test_all_services_active(self, sample_config):
        """Passes when all services are active"""
        check = SystemdServicesCheck(sample_config)

        mock_result = MagicMock()
        mock_result.stdout = "active\n"
        mock_result.returncode = 0

        with patch('checks.system_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "passed"
        assert "2 service(s) active" in result.message

    def test_service_inactive(self, sample_config):
        """Fails when a service is inactive"""
        check = SystemdServicesCheck(sample_config)

        call_count = [0]

        def mock_systemctl(*args, **kwargs):
            call_count[0] += 1
            mock = MagicMock()
            if call_count[0] == 1:
                mock.stdout = "active\n"
            else:
                mock.stdout = "inactive\n"
            return mock

        with patch('checks.system_checks.subprocess.run', side_effect=mock_systemctl):
            result = check.execute()

        assert result.status == "failed"
        assert "Inactive" in result.message

    def test_systemctl_not_found(self, sample_config):
        """Skips when systemctl not found (e.g., Windows)"""
        check = SystemdServicesCheck(sample_config)

        with patch('checks.system_checks.subprocess.run', side_effect=FileNotFoundError):
            result = check.execute()

        assert result.status == "skipped"

    def test_no_services(self, empty_config):
        """Skips when no services configured"""
        check = SystemdServicesCheck(empty_config)
        result = check.execute()
        assert result.status == "skipped"


class TestEnvironmentCheck:
    def test_all_vars_correct(self, sample_config):
        """Passes when all env vars match"""
        check = EnvironmentCheck(sample_config)

        env_mock = {
            "ROS_MASTER_URI": "http://192.168.1.1:11311",
            "ROS_IP": "192.168.1.2",
            "ROS_HOSTNAME": "jetson-test"
        }

        with patch.dict('os.environ', env_mock):
            result = check.execute()

        assert result.status == "passed"
        assert "3 environment variable(s) correct" in result.message

    def test_var_missing(self, sample_config):
        """Fails when env var is missing"""
        check = EnvironmentCheck(sample_config)

        env_mock = {
            "ROS_MASTER_URI": "http://192.168.1.1:11311",
            # ROS_IP missing
            # ROS_HOSTNAME missing
        }

        with patch.dict('os.environ', env_mock, clear=True):
            result = check.execute()

        assert result.status == "failed"
        assert "Missing" in result.message

    def test_var_wrong_value(self, sample_config):
        """Fails when env var has wrong value"""
        check = EnvironmentCheck(sample_config)

        env_mock = {
            "ROS_MASTER_URI": "http://wrong-host:11311",
            "ROS_IP": "192.168.1.2",
            "ROS_HOSTNAME": "jetson-test"
        }

        with patch.dict('os.environ', env_mock, clear=True):
            result = check.execute()

        assert result.status == "failed"
        assert "Incorrect" in result.message

    def test_no_vars_configured(self, empty_config):
        """Skips when no env vars configured"""
        check = EnvironmentCheck(empty_config)
        result = check.execute()
        assert result.status == "skipped"


class TestTimeCheck:
    def test_time_ok_with_ntp(self, sample_config):
        """Passes when time is correct and NTP synced"""
        check = TimeCheck(sample_config)

        mock_result = MagicMock()
        mock_result.stdout = "System clock synchronized: yes\n"

        with patch('checks.system_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "passed"
        assert "NTP" in result.message

    def test_time_ok_no_ntp(self, sample_config):
        """Warning when time is OK but NTP status unknown"""
        check = TimeCheck(sample_config)

        with patch('checks.system_checks.subprocess.run', side_effect=FileNotFoundError):
            result = check.execute()

        assert result.status == "warning"
        assert "NTP sync status unknown" in result.message


class TestStartupScriptCheck:
    def test_script_succeeds(self, sample_config):
        """Passes when script exits with 0"""
        check = StartupScriptCheck(sample_config)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "System started\n"
        mock_result.stderr = ""

        with patch('os.path.exists', return_value=True), \
             patch('checks.system_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "passed"
        assert "successfully" in result.message

    def test_script_fails(self, sample_config):
        """Fails when script returns non-zero"""
        check = StartupScriptCheck(sample_config)

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error\n"

        with patch('os.path.exists', return_value=True), \
             patch('checks.system_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "failed"
        assert "exit code 1" in result.message

    def test_script_not_found(self, sample_config):
        """Fails when script file doesn't exist"""
        check = StartupScriptCheck(sample_config)

        with patch('os.path.exists', return_value=False):
            result = check.execute()

        assert result.status == "failed"
        assert "not found" in result.message

    def test_no_script_configured(self, empty_config):
        """Skips when no script configured"""
        check = StartupScriptCheck(empty_config)
        result = check.execute()
        assert result.status == "skipped"


class TestLoggingCheck:
    def test_log_test_passes(self, sample_config):
        """Passes when log test script succeeds"""
        check = LoggingCheck(sample_config)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Logs OK\n"
        mock_result.stderr = ""

        with patch('os.path.exists', return_value=True), \
             patch('checks.system_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "passed"

    def test_no_log_script(self, empty_config):
        """Skips when no log test script configured"""
        check = LoggingCheck(empty_config)
        result = check.execute()
        assert result.status == "skipped"


class TestMetadataCaptureCheck:
    def test_captures_metadata(self, sample_config):
        """Passes and captures metadata"""
        check = MetadataCaptureCheck(sample_config)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc12345\n"

        with patch('checks.system_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "passed"
        assert "Metadata captured" in result.message
        assert "timestamp" in result.details

    def test_git_not_available(self, sample_config):
        """Still passes when git is not available"""
        check = MetadataCaptureCheck(sample_config)

        with patch('checks.system_checks.subprocess.run', side_effect=FileNotFoundError):
            result = check.execute()

        assert result.status == "passed"
        assert result.details["git_commit"] == "unknown"
