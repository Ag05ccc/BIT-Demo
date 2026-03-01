"""
Tests for server/checks/autopilot_checks.py - MAVLink autopilot checks.
pymavlink is mocked for local testing.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys

# Mock pymavlink module
mock_mavutil = MagicMock()
sys.modules['pymavlink'] = MagicMock()
sys.modules['pymavlink.mavutil'] = mock_mavutil

from checks.autopilot_checks import (
    AutopilotDetectCheck, AutopilotStatusCheck,
    AutopilotParamsCheck, AutopilotParamExportCheck, AutopilotSensorsCheck
)


class TestAutopilotDetectCheck:
    def test_heartbeat_received(self, sample_config):
        """Passes when heartbeat is received"""
        check = AutopilotDetectCheck(sample_config)

        mock_conn = MagicMock()
        mock_conn.target_system = 1
        mock_conn.target_component = 1

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', True), \
             patch('checks.autopilot_checks.mavutil.mavlink_connection', return_value=mock_conn):
            result = check.execute()

        assert result.status == "passed"
        assert "Autopilot detected" in result.message
        assert result.details["system_id"] == 1

    def test_no_heartbeat(self, sample_config):
        """Fails when no heartbeat received"""
        check = AutopilotDetectCheck(sample_config)

        mock_conn = MagicMock()
        mock_conn.wait_heartbeat.side_effect = Exception("Timeout")

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', True), \
             patch('checks.autopilot_checks.mavutil.mavlink_connection', return_value=mock_conn):
            result = check.execute()

        assert result.status == "failed"
        assert "No heartbeat" in result.message

    def test_mavlink_not_installed(self, sample_config):
        """Skips when pymavlink not installed"""
        check = AutopilotDetectCheck(sample_config)

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', False):
            result = check.execute()

        assert result.status == "skipped"

    def test_no_connection_configured(self, empty_config):
        """Skips when no connection configured"""
        check = AutopilotDetectCheck(empty_config)

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', True):
            result = check.execute()

        assert result.status == "skipped"


class TestAutopilotStatusCheck:
    def test_status_ok(self, sample_config):
        """Passes when autopilot status is OK"""
        check = AutopilotStatusCheck(sample_config)

        mock_conn = MagicMock()
        mock_msg = MagicMock()
        mock_msg.voltage_battery = 12500  # 12.5V
        mock_msg.battery_remaining = 85
        mock_msg.onboard_control_sensors_enabled = 0xFF
        mock_msg.onboard_control_sensors_health = 0xFF  # All healthy
        mock_conn.recv_match.return_value = mock_msg

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', True), \
             patch('checks.autopilot_checks.mavutil.mavlink_connection', return_value=mock_conn):
            result = check.execute()

        assert result.status == "passed"
        assert "12.5V" in result.message

    def test_low_battery(self, sample_config):
        """Fails when battery is low"""
        check = AutopilotStatusCheck(sample_config)

        mock_conn = MagicMock()
        mock_msg = MagicMock()
        mock_msg.voltage_battery = 10000  # 10.0V - too low
        mock_msg.battery_remaining = 15
        mock_msg.onboard_control_sensors_enabled = 0xFF
        mock_msg.onboard_control_sensors_health = 0xFF
        mock_conn.recv_match.return_value = mock_msg

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', True), \
             patch('checks.autopilot_checks.mavutil.mavlink_connection', return_value=mock_conn):
            result = check.execute()

        assert result.status == "failed"
        assert "battery" in result.message.lower()

    def test_no_status_message(self, sample_config):
        """Fails when no SYS_STATUS message received"""
        check = AutopilotStatusCheck(sample_config)

        mock_conn = MagicMock()
        mock_conn.recv_match.return_value = None

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', True), \
             patch('checks.autopilot_checks.mavutil.mavlink_connection', return_value=mock_conn):
            result = check.execute()

        assert result.status == "failed"
        assert "No SYS_STATUS" in result.message


class TestAutopilotParamsCheck:
    def test_no_params_file(self, sample_config):
        """Skips when default params file not found"""
        check = AutopilotParamsCheck(sample_config)

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', True), \
             patch('os.path.exists', return_value=False):
            result = check.execute()

        assert result.status == "skipped"


class TestAutopilotParamExportCheck:
    def test_export_placeholder(self, sample_config):
        """Param export returns warning (placeholder)"""
        check = AutopilotParamExportCheck(sample_config)

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', True):
            result = check.execute()

        assert result.status == "warning"
        assert "export_filename" in result.details


class TestAutopilotSensorsCheck:
    def test_sensors_ok(self, sample_config):
        """Passes when all sensors are healthy"""
        check = AutopilotSensorsCheck(sample_config)

        mock_conn = MagicMock()
        mock_gps = MagicMock()
        mock_gps.fix_type = 3  # 3D fix
        mock_gps.satellites_visible = 12

        mock_att = MagicMock()

        def recv_match_side_effect(**kwargs):
            msg_type = kwargs.get('type')
            if msg_type == 'GPS_RAW_INT':
                return mock_gps
            elif msg_type == 'ATTITUDE':
                return mock_att
            return None

        mock_conn.recv_match.side_effect = recv_match_side_effect

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', True), \
             patch('checks.autopilot_checks.mavutil.mavlink_connection', return_value=mock_conn):
            result = check.execute()

        assert result.status == "passed"
        assert result.details["gps_ok"] is True

    def test_no_gps_fix(self, sample_config):
        """Fails when no GPS fix"""
        check = AutopilotSensorsCheck(sample_config)

        mock_conn = MagicMock()
        mock_gps = MagicMock()
        mock_gps.fix_type = 0  # No fix

        mock_att = MagicMock()

        def recv_match_side_effect(**kwargs):
            msg_type = kwargs.get('type')
            if msg_type == 'GPS_RAW_INT':
                return mock_gps
            elif msg_type == 'ATTITUDE':
                return mock_att
            return None

        mock_conn.recv_match.side_effect = recv_match_side_effect

        with patch('checks.autopilot_checks.MAVLINK_AVAILABLE', True), \
             patch('checks.autopilot_checks.mavutil.mavlink_connection', return_value=mock_conn):
            result = check.execute()

        assert result.status == "failed"
        assert "GPS" in result.message
