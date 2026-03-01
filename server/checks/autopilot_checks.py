"""
Autopilot checks: MAVLink connection, status, parameters, sensors.
"""

import os
import time
from datetime import datetime
from .base_check import BaseCheck
from common.constants import CATEGORY_AUTOPILOT, PARAM_EXPORT_FORMAT

# Try to import MAVLink libraries
try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False


class AutopilotDetectCheck(BaseCheck):
    """Wait for MAVLink heartbeat from autopilot"""

    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        if not MAVLINK_AVAILABLE:
            self.skip("pymavlink not installed")
            return False

        try:
            autopilot_config = self.config.get('autopilot', {})
            connection_string = autopilot_config.get('connection')
            baud_rate = autopilot_config.get('baud_rate', 57600)
            heartbeat_timeout = autopilot_config.get('heartbeat_timeout', 10)

            if not connection_string:
                self.skip("Autopilot connection not configured")
                return False

            # Connect to autopilot
            try:
                # Handle different connection types
                if connection_string.startswith('/dev/'):
                    # Serial connection
                    mav = mavutil.mavlink_connection(connection_string, baud=baud_rate)
                else:
                    # TCP/UDP connection
                    mav = mavutil.mavlink_connection(connection_string)

                # Wait for heartbeat
                self.status = "running"
                self.message = "Waiting for heartbeat..."

                mav.wait_heartbeat(timeout=heartbeat_timeout)

                # Got heartbeat
                self.status = "passed"
                self.message = f"Autopilot detected (System ID: {mav.target_system})"
                self.details = {
                    "system_id": mav.target_system,
                    "component_id": mav.target_component,
                    "connection": connection_string
                }

                # Close connection (will be reopened by other checks if needed)
                mav.close()
                return True

            except Exception as e:
                self.status = "failed"
                self.message = f"No heartbeat received: {e}"
                return False

        except Exception as e:
            self.status = "failed"
            self.message = f"Error connecting to autopilot: {e}"
            return False


class AutopilotStatusCheck(BaseCheck):
    """Check autopilot status for critical errors"""

    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        if not MAVLINK_AVAILABLE:
            self.skip("pymavlink not installed")
            return False

        try:
            autopilot_config = self.config.get('autopilot', {})
            connection_string = autopilot_config.get('connection')
            baud_rate = autopilot_config.get('baud_rate', 57600)

            if not connection_string:
                self.skip("Autopilot connection not configured")
                return False

            # Connect
            if connection_string.startswith('/dev/'):
                mav = mavutil.mavlink_connection(connection_string, baud=baud_rate)
            else:
                mav = mavutil.mavlink_connection(connection_string)

            heartbeat_timeout = autopilot_config.get('heartbeat_timeout', 10)
            msg_timeout = autopilot_config.get('message_timeout', 5)
            mav.wait_heartbeat(timeout=heartbeat_timeout)

            # Request SYS_STATUS message
            mav.mav.request_data_stream_send(
                mav.target_system,
                mav.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_EXTENDED_STATUS,
                1,  # 1 Hz
                1   # start
            )

            # Wait for SYS_STATUS
            msg = mav.recv_match(type='SYS_STATUS', blocking=True, timeout=msg_timeout)

            if msg:
                # Check for errors/warnings
                errors = []
                warnings = []

                # Voltage check (thresholds from config)
                voltage = msg.voltage_battery / 1000.0  # mV to V
                voltage_error = autopilot_config.get('battery_voltage_error', 10.5)
                voltage_warning = autopilot_config.get('battery_voltage_warning', 11.1)
                if voltage < voltage_error:
                    errors.append(f"Low battery: {voltage:.1f}V (min: {voltage_error}V)")
                elif voltage < voltage_warning:
                    warnings.append(f"Battery getting low: {voltage:.1f}V (warn: {voltage_warning}V)")

                # Check sensors
                sensors_enabled = msg.onboard_control_sensors_enabled
                sensors_health = msg.onboard_control_sensors_health

                # Check if critical sensors are unhealthy
                # (This is simplified - actual implementation would check specific bits)
                if sensors_enabled != sensors_health:
                    warnings.append("Some sensors unhealthy")

                self.details = {
                    "voltage": round(voltage, 2),
                    "battery_remaining": msg.battery_remaining,
                    "sensors_enabled": sensors_enabled,
                    "sensors_health": sensors_health
                }

                mav.close()

                if errors:
                    self.status = "failed"
                    self.message = "; ".join(errors)
                    return False
                elif warnings:
                    self.warn("; ".join(warnings), self.details)
                    return True
                else:
                    self.status = "passed"
                    self.message = f"Autopilot status OK (Battery: {voltage:.1f}V)"
                    return True
            else:
                mav.close()
                self.status = "failed"
                self.message = "No SYS_STATUS message received"
                return False

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking autopilot status: {e}"
            return False


class AutopilotParamsCheck(BaseCheck):
    """Compare autopilot parameters with default.param file"""

    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        if not MAVLINK_AVAILABLE:
            self.skip("pymavlink not installed")
            return False

        try:
            autopilot_config = self.config.get('autopilot', {})
            default_params_file = autopilot_config.get('default_params_file')

            if not default_params_file or not os.path.exists(default_params_file):
                self.skip("Default params file not configured or not found")
                return False

            # Load default params
            default_params = {}
            try:
                with open(default_params_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split()
                        if len(parts) >= 2:
                            param_name = parts[0]
                            param_value = float(parts[1])
                            default_params[param_name] = param_value
            except Exception as e:
                self.status = "failed"
                self.message = f"Error reading default params: {e}"
                return False

            # Get current params from autopilot (simplified - full implementation needed)
            self.warn("Parameter comparison not fully implemented yet")
            self.details = {"default_params_loaded": len(default_params)}
            return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking autopilot params: {e}"
            return False


class AutopilotParamExportCheck(BaseCheck):
    """Export current autopilot parameters"""

    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        if not MAVLINK_AVAILABLE:
            self.skip("pymavlink not installed")
            return False

        try:
            # This would export current params with timestamp
            # Full implementation requires fetching all params via MAVLink

            timestamp_filename = datetime.now().strftime(PARAM_EXPORT_FORMAT)
            self.details = {"export_filename": timestamp_filename}
            self.warn("Parameter export not fully implemented yet")
            return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error exporting params: {e}"
            return False


class AutopilotSensorsCheck(BaseCheck):
    """Check autopilot sensor health (GPS, IMU, barometer)"""

    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        if not MAVLINK_AVAILABLE:
            self.skip("pymavlink not installed")
            return False

        try:
            autopilot_config = self.config.get('autopilot', {})
            connection_string = autopilot_config.get('connection')
            baud_rate = autopilot_config.get('baud_rate', 57600)

            if not connection_string:
                self.skip("Autopilot connection not configured")
                return False

            # Connect
            if connection_string.startswith('/dev/'):
                mav = mavutil.mavlink_connection(connection_string, baud=baud_rate)
            else:
                mav = mavutil.mavlink_connection(connection_string)

            heartbeat_timeout = autopilot_config.get('heartbeat_timeout', 10)
            msg_timeout = autopilot_config.get('message_timeout', 5)
            mav.wait_heartbeat(timeout=heartbeat_timeout)

            # Check GPS
            msg_gps = mav.recv_match(type='GPS_RAW_INT', blocking=True, timeout=msg_timeout)
            gps_ok = msg_gps and msg_gps.fix_type >= 3  # 3D fix

            # Check IMU (ATTITUDE message)
            msg_att = mav.recv_match(type='ATTITUDE', blocking=True, timeout=msg_timeout)
            imu_ok = msg_att is not None

            self.details = {
                "gps_ok": gps_ok,
                "gps_fix_type": msg_gps.fix_type if msg_gps else None,
                "gps_satellites": msg_gps.satellites_visible if msg_gps else None,
                "imu_ok": imu_ok
            }

            mav.close()

            issues = []
            if not gps_ok:
                issues.append("GPS no 3D fix")
            if not imu_ok:
                issues.append("IMU data unavailable")

            if issues:
                self.status = "failed"
                self.message = "; ".join(issues)
                return False
            else:
                self.status = "passed"
                self.message = "Sensors OK"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking sensors: {e}"
            return False
