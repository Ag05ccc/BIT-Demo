"""
Autopilot checks: connection, status, parameters, sensors via MAVROS ROS topics.

Requires MAVProxy and MAVROS to be running. Reads autopilot data from
standard MAVROS topics instead of opening a direct MAVLink connection.
"""

import os
from datetime import datetime
from .base_check import BaseCheck
from common.constants import CATEGORY_AUTOPILOT, PARAM_EXPORT_FORMAT

# Try to import ROS/MAVROS libraries (pre-installed on the Jetson with ROS)
try:
    import rospy
    from sensor_msgs.msg import NavSatFix, Imu, BatteryState
    from mavros_msgs.msg import State
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False


def _wait(topic, msg_type, timeout):
    """Wrapper around rospy.wait_for_message with a clear timeout error."""
    return rospy.wait_for_message(topic, msg_type, timeout=timeout)


class AutopilotDetectCheck(BaseCheck):
    """Verify autopilot connection via the MAVROS /state topic."""

    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("rospy / mavros_msgs not installed")
            return False

        ap = self.config.get('autopilot', {})
        ns = ap.get('mavros_ns', '/mavros')
        timeout = ap.get('heartbeat_timeout', 10)

        topic = f"{ns}/state"
        try:
            state = _wait(topic, State, timeout)
        except rospy.ROSException:
            self.status = "failed"
            self.message = f"No MAVROS state on {topic} within {timeout}s"
            return False

        if state.connected:
            self.status = "passed"
            self.message = f"Autopilot connected (mode: {state.mode})"
            self.details = {
                "connected": state.connected,
                "armed": state.armed,
                "mode": state.mode,
                "system_status": state.system_status,
            }
            return True
        else:
            self.status = "failed"
            self.message = "MAVROS reports autopilot not connected"
            self.details = {"connected": False, "mode": state.mode}
            return False


class AutopilotStatusCheck(BaseCheck):
    """Check battery voltage and system status via MAVROS topics."""

    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("rospy / mavros_msgs not installed")
            return False

        ap = self.config.get('autopilot', {})
        ns = ap.get('mavros_ns', '/mavros')
        timeout = ap.get('heartbeat_timeout', 10)
        v_error = ap.get('battery_voltage_error', 10.5)
        v_warn  = ap.get('battery_voltage_warning', 11.1)

        # Battery voltage
        bat_topic = f"{ns}/battery"
        try:
            battery = _wait(bat_topic, BatteryState, timeout)
            voltage = battery.voltage
        except rospy.ROSException:
            self.status = "failed"
            self.message = f"No battery data on {bat_topic} within {timeout}s"
            return False

        # System state (best-effort — don't fail if unavailable)
        state_topic = f"{ns}/state"
        try:
            state = _wait(state_topic, State, timeout)
        except rospy.ROSException:
            state = None

        errors   = []
        warnings = []

        if voltage < v_error:
            errors.append(f"Low battery: {voltage:.1f}V (min: {v_error}V)")
        elif voltage < v_warn:
            warnings.append(f"Battery getting low: {voltage:.1f}V (warn: {v_warn}V)")

        self.details = {
            "voltage_v": round(voltage, 2),
            "battery_pct": round(battery.percentage * 100, 1) if battery.percentage >= 0 else None,
            "system_status": state.system_status if state else None,
            "armed": state.armed if state else None,
        }

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


class AutopilotParamsCheck(BaseCheck):
    """Compare autopilot parameters with a default .param file."""

    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("rospy / mavros_msgs not installed")
            return False

        ap = self.config.get('autopilot', {})
        params_file = ap.get('default_params_file')

        if not params_file or not os.path.exists(params_file):
            self.skip("Default params file not configured or not found")
            return False

        # Load default params from file
        default_params = {}
        try:
            with open(params_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        default_params[parts[0]] = float(parts[1])
        except Exception as e:
            self.status = "failed"
            self.message = f"Error reading default params: {e}"
            return False

        # Full parameter fetch via /mavros/param/get service is
        # mission-specific; comparison flagged as pending.
        self.warn("Parameter comparison not fully implemented yet")
        self.details = {"default_params_loaded": len(default_params)}
        return True


class AutopilotParamExportCheck(BaseCheck):
    """Export current autopilot parameters (stub)."""

    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("rospy / mavros_msgs not installed")
            return False

        try:
            filename = datetime.now().strftime(PARAM_EXPORT_FORMAT)
            self.details = {"export_filename": filename}
            self.warn("Parameter export not fully implemented yet")
            return True
        except Exception as e:
            self.status = "failed"
            self.message = f"Error exporting params: {e}"
            return False


class AutopilotSensorsCheck(BaseCheck):
    """Check GPS and IMU health via MAVROS topics."""

    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("rospy / mavros_msgs not installed")
            return False

        ap = self.config.get('autopilot', {})
        ns = ap.get('mavros_ns', '/mavros')
        timeout = ap.get('heartbeat_timeout', 10)

        # GPS — NavSatFix status: -1=no fix, 0=fix, 1=SBAS, 2=GBAS
        gps_topic = f"{ns}/global_position/raw/fix"
        try:
            fix = _wait(gps_topic, NavSatFix, timeout)
            gps_ok     = fix.status.status >= 0
            gps_status = fix.status.status
        except rospy.ROSException:
            gps_ok     = False
            gps_status = -1

        # IMU
        imu_topic = f"{ns}/imu/data"
        try:
            _wait(imu_topic, Imu, timeout)
            imu_ok = True
        except rospy.ROSException:
            imu_ok = False

        self.details = {
            "gps_ok": gps_ok,
            "gps_status": gps_status,
            "imu_ok": imu_ok,
        }

        issues = []
        if not gps_ok:
            issues.append("GPS: no fix")
        if not imu_ok:
            issues.append("IMU: no data")

        if issues:
            self.status = "failed"
            self.message = "; ".join(issues)
            return False

        self.status = "passed"
        self.message = "Sensors OK (GPS fix, IMU responding)"
        return True
