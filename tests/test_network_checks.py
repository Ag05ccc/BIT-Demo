"""
Tests for server/checks/network_checks.py - Network connectivity checks.
All external dependencies are mocked for local testing.
"""

import pytest
from unittest.mock import patch, MagicMock
from checks.network_checks import NetworkInterfaceCheck, PingTestCheck, TestPCConnectivityCheck


class TestNetworkInterfaceCheck:
    def test_interfaces_up(self, sample_config):
        """Passes when interfaces are UP"""
        check = NetworkInterfaceCheck(sample_config)

        mock_result = MagicMock()
        mock_result.stdout = (
            "1: lo: <LOOPBACK,UP> mtu 65536 state UNKNOWN\n"
            "2: eth0: <BROADCAST,MULTICAST,UP> mtu 1500 state UP\n"
            "3: wlan0: <BROADCAST,MULTICAST,UP> mtu 1500 state UP\n"
        )
        mock_result.returncode = 0

        with patch('checks.network_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "passed"
        assert "2 interface(s) UP" in result.message
        assert "eth0" in result.details["up_interfaces"]

    def test_no_interfaces_up(self, sample_config):
        """Fails when no interfaces are UP"""
        check = NetworkInterfaceCheck(sample_config)

        mock_result = MagicMock()
        mock_result.stdout = "1: lo: <LOOPBACK> mtu 65536 state DOWN\n"
        mock_result.returncode = 0

        with patch('checks.network_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "failed"

    def test_ip_command_not_found(self, sample_config):
        """Skips when ip command not found (e.g., Windows)"""
        check = NetworkInterfaceCheck(sample_config)

        with patch('checks.network_checks.subprocess.run', side_effect=FileNotFoundError):
            result = check.execute()

        assert result.status == "skipped"


class TestPingTestCheck:
    def test_all_reachable(self, sample_config):
        """Passes when all targets are reachable"""
        check = PingTestCheck(sample_config)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "rtt min/avg/max/mdev = 0.5/1.2/2.0/0.3 ms\n"

        with patch('checks.network_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "passed"
        assert "2 target(s) reachable" in result.message

    def test_some_unreachable(self, sample_config):
        """Fails when some targets are unreachable"""
        check = PingTestCheck(sample_config)

        call_count = [0]

        def mock_ping(*args, **kwargs):
            call_count[0] += 1
            mock = MagicMock()
            mock.stdout = "rtt min/avg/max/mdev = 0.5/1.2/2.0/0.3 ms\n"
            if call_count[0] == 1:
                mock.returncode = 0  # First target reachable
            else:
                mock.returncode = 1  # Second target unreachable
            return mock

        with patch('checks.network_checks.subprocess.run', side_effect=mock_ping):
            result = check.execute()

        assert result.status == "failed"
        assert "Unreachable" in result.message

    def test_no_targets(self, empty_config):
        """Skips when no targets configured"""
        check = PingTestCheck(empty_config)
        result = check.execute()
        assert result.status == "skipped"


class TestTestPCConnectivityCheck:
    def test_pc_reachable(self, sample_config):
        """Passes when Test PC is reachable"""
        check = TestPCConnectivityCheck(sample_config)

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch('checks.network_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "passed"
        assert "192.168.1.1" in result.message

    def test_pc_unreachable(self, sample_config):
        """Fails when Test PC is unreachable"""
        check = TestPCConnectivityCheck(sample_config)

        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch('checks.network_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "failed"

    def test_no_pc_ip(self, empty_config):
        """Skips when no Test PC IP configured"""
        check = TestPCConnectivityCheck(empty_config)
        result = check.execute()
        assert result.status == "skipped"
