"""
Simulated check classes for local testing without hardware.
Each class mirrors a real check but returns fake data.

Usage: Start the server with --sim flag:
    python test_server.py --sim
"""

import time
import random
import platform
from datetime import datetime
from .base_check import BaseCheck
from common.constants import (
    CATEGORY_JETSON, CATEGORY_DEVICE, CATEGORY_NETWORK,
    CATEGORY_ROS, CATEGORY_AUTOPILOT, CATEGORY_SYSTEM
)


def _sim_delay():
    """Simulate realistic check execution time."""
    time.sleep(random.uniform(0.05, 0.3))


def _decide_outcome(config, check_name):
    """
    Decide simulated outcome based on config.

    Returns: "passed", "failed", or "warning"

    Uses check_name as seed offset so results are consistent
    across runs (unless random_seed changes).
    """
    sim = config.get('sim', {})
    overrides = sim.get('overrides', {})

    # Allow per-check overrides
    if check_name in overrides:
        return overrides[check_name]

    seed = sim.get('random_seed', 42)
    rng = random.Random(seed + hash(check_name))

    pass_rate = sim.get('pass_rate', 0.75)
    warning_rate = sim.get('warning_rate', 0.15)
    # remaining = fail_rate

    roll = rng.random()
    if roll < pass_rate:
        return "passed"
    elif roll < pass_rate + warning_rate:
        return "warning"
    else:
        return "failed"


# ---------------------------------------------------------------------------
# Jetson Checks
# ---------------------------------------------------------------------------

class SimJetsonBootCheck(BaseCheck):
    """[SIM] Check Jetson boot logs for critical errors"""
    category = CATEGORY_JETSON

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "JetsonBootCheck")

        if outcome == "passed":
            self.message = "No critical boot errors found"
            self.details = {"total_error_lines": 0, "simulated": True}
            return True
        elif outcome == "warning":
            self.warn("Found 2 potential error(s)", {
                "errors": [
                    "[    2.341] tegra-i2c: timeout waiting for response",
                    "[    3.012] firmware: optional module not loaded"
                ],
                "simulated": True
            })
            return True
        else:
            self.message = "Found 5 critical error(s)"
            self.details = {
                "errors": [
                    "[    1.001] kernel: memory allocation failure",
                    "[    1.502] pcie: link training failed",
                    "[    2.003] gpu: initialization error",
                    "[    2.504] usb: device not responding",
                    "[    3.005] thermal: zone over temperature"
                ],
                "simulated": True
            }
            return False


class SimJetsonResourcesCheck(BaseCheck):
    """[SIM] Check Jetson CPU, RAM, and Disk usage"""
    category = CATEGORY_JETSON

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "JetsonResourcesCheck")

        if outcome == "passed":
            cpu = round(random.uniform(15, 55), 1)
            ram = round(random.uniform(30, 65), 1)
            disk_free = round(random.uniform(20, 100), 2)
            self.message = f"Resources OK (CPU: {cpu}%, RAM: {ram}%, Disk: {disk_free} GB free)"
            self.details = {
                "cpu_percent": cpu,
                "ram_percent": ram,
                "ram_used_gb": round(ram * 0.16, 2),
                "ram_total_gb": 16.0,
                "disk_free_gb": disk_free,
                "disk_total_gb": 256.0,
                "disk_percent": round(100 - (disk_free / 256 * 100), 1),
                "simulated": True
            }
            return True
        elif outcome == "warning":
            self.warn("CPU usage elevated: 78.5%", {
                "cpu_percent": 78.5,
                "ram_percent": 60.2,
                "disk_free_gb": 15.3,
                "simulated": True
            })
            return True
        else:
            self.message = "CPU usage high: 95.2% (max: 90%); RAM usage high: 88.1% (max: 85%)"
            self.details = {
                "cpu_percent": 95.2,
                "ram_percent": 88.1,
                "disk_free_gb": 3.2,
                "simulated": True
            }
            return False


class SimJetsonTemperatureCheck(BaseCheck):
    """[SIM] Check Jetson temperature and throttling status"""
    category = CATEGORY_JETSON

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "JetsonTemperatureCheck")

        if outcome == "passed":
            max_temp = round(random.uniform(35, 55), 1)
            self.message = f"Temperature OK: {max_temp}\u00b0C (max: 80\u00b0C)"
            self.details = {
                "temperatures_celsius": [max_temp, max_temp - 3.2, max_temp - 5.1],
                "max_temp": max_temp,
                "avg_temp": round(max_temp - 2.8, 1),
                "num_zones": 3,
                "simulated": True
            }
            return True
        elif outcome == "warning":
            self.warn("Temperature approaching limit: 73.5\u00b0C (max: 80\u00b0C)", {
                "temperatures_celsius": [73.5, 70.1, 68.3],
                "max_temp": 73.5,
                "avg_temp": 70.6,
                "num_zones": 3,
                "simulated": True
            })
            return True
        else:
            self.message = "Temperature too high: 85.2\u00b0C (max: 80\u00b0C)"
            self.details = {
                "temperatures_celsius": [85.2, 82.1, 79.3],
                "max_temp": 85.2,
                "avg_temp": 82.2,
                "num_zones": 3,
                "simulated": True
            }
            return False


# ---------------------------------------------------------------------------
# Device Checks
# ---------------------------------------------------------------------------

class SimUdevRulesCheck(BaseCheck):
    """[SIM] Check if udev rules are loaded"""
    category = CATEGORY_DEVICE

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "UdevRulesCheck")
        rules = self.config.get('udev_rules', ['/etc/udev/rules.d/99-autopilot.rules'])

        if outcome == "passed":
            self.message = f"{len(rules)} udev rule(s) found"
            self.details = {"expected_rules": rules, "loaded": rules, "missing": [], "simulated": True}
            return True
        else:
            self.message = f"Missing udev rules: {rules[0]}"
            self.details = {"expected_rules": rules, "loaded": [], "missing": rules, "simulated": True}
            return False


class SimDeviceExistsCheck(BaseCheck):
    """[SIM] Check if required /dev/ devices exist"""
    category = CATEGORY_DEVICE

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "DeviceExistsCheck")
        devices = self.config.get('devices', {})

        found = [{"name": n, "path": d.get("path", ""), "description": d.get("description", "")}
                 for n, d in devices.items()]

        if outcome == "passed":
            self.message = f"{len(found)} device(s) found"
            self.details = {"found": found, "missing": [], "simulated": True}
            return True
        else:
            missing = found[-1:] if found else [{"name": "deviceB", "path": "/dev/ttyUSB1"}]
            self.message = f"Missing device(s): {missing[0]['name']}"
            self.details = {"found": found[:-1], "missing": missing, "simulated": True}
            return False


class SimDeviceHardwareIDCheck(BaseCheck):
    """[SIM] Check device hardware vendor/product IDs"""
    category = CATEGORY_DEVICE

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "DeviceHardwareIDCheck")
        devices = self.config.get('devices', {})
        names = list(devices.keys())

        if outcome == "passed":
            self.message = f"{len(names)} device(s) matched hardware IDs"
            self.details = {"matched": names, "mismatched": [], "simulated": True}
            return True
        else:
            self.message = f"Hardware ID mismatch for: {names[-1] if names else 'unknown'}"
            self.details = {"matched": names[:-1], "mismatched": names[-1:], "simulated": True}
            return False


class SimDevicePermissionsCheck(BaseCheck):
    """[SIM] Test if devices can be opened without sudo"""
    category = CATEGORY_DEVICE

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "DevicePermissionsCheck")
        devices = self.config.get('devices', {})
        names = list(devices.keys())

        if outcome == "passed":
            self.message = f"{len(names)} device(s) accessible"
            self.details = {"accessible": names, "inaccessible": [], "simulated": True}
            return True
        else:
            self.message = f"Permission denied for: {names[-1] if names else 'unknown'}"
            self.details = {
                "accessible": names[:-1], "inaccessible": names[-1:],
                "fix_hint": "Check udev rules and user groups", "simulated": True
            }
            return False


class SimDeviceHandshakeCheck(BaseCheck):
    """[SIM] Perform basic read/write handshake test with devices"""
    category = CATEGORY_DEVICE

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "DeviceHandshakeCheck")
        devices = self.config.get('devices', {})

        test_devices = [n for n, d in devices.items() if d.get('test_command')]

        if not test_devices:
            self.skip("No devices with handshake test configured")
            return False

        if outcome == "passed":
            passed_list = [{"device": n, "response": "OK"} for n in test_devices]
            self.message = f"Handshake OK for {len(passed_list)} device(s)"
            self.details = {"passed": passed_list, "failed": [], "simulated": True}
            return True
        else:
            self.message = f"Handshake failed for 1 device(s)"
            self.details = {
                "passed": [],
                "failed": [{"device": test_devices[0], "expected": "OK", "got": "TIMEOUT"}],
                "simulated": True
            }
            return False


# ---------------------------------------------------------------------------
# Network Checks
# ---------------------------------------------------------------------------

class SimNetworkInterfaceCheck(BaseCheck):
    """[SIM] Check if network interfaces are up"""
    category = CATEGORY_NETWORK

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "NetworkInterfaceCheck")

        if outcome == "passed":
            interfaces = ["eth0", "wlan0"]
            self.message = f"{len(interfaces)} interface(s) UP: {', '.join(interfaces)}"
            self.details = {"up_interfaces": interfaces, "count": len(interfaces), "simulated": True}
            return True
        else:
            self.message = "No network interfaces are UP"
            self.details = {"up_interfaces": [], "count": 0, "simulated": True}
            return False


class SimPingTestCheck(BaseCheck):
    """[SIM] Ping configured targets"""
    category = CATEGORY_NETWORK

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "PingTestCheck")
        targets = self.config.get('ping_targets', ['127.0.0.1'])

        if outcome == "passed":
            reachable = [{"target": t, "latency_ms": round(random.uniform(0.5, 15.0), 2)}
                         for t in targets]
            self.message = f"All {len(reachable)} target(s) reachable"
            self.details = {"reachable": reachable, "unreachable": [], "simulated": True}
            return True
        else:
            self.message = f"Unreachable: {targets[-1]}"
            reachable = [{"target": t, "latency_ms": round(random.uniform(0.5, 15.0), 2)}
                         for t in targets[:-1]]
            self.details = {
                "reachable": reachable, "unreachable": [targets[-1]], "simulated": True
            }
            return False


class SimTestPCConnectivityCheck(BaseCheck):
    """[SIM] Check connectivity to Test PC"""
    category = CATEGORY_NETWORK

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "TestPCConnectivityCheck")
        test_pc_ip = self.config.get('test_pc', {}).get('expected_ip', '127.0.0.1')

        if outcome == "passed":
            self.message = f"Test PC ({test_pc_ip}) is reachable"
            self.details = {"test_pc_ip": test_pc_ip, "simulated": True}
            return True
        else:
            self.message = f"Test PC ({test_pc_ip}) is NOT reachable"
            self.details = {"test_pc_ip": test_pc_ip, "simulated": True}
            return False


# ---------------------------------------------------------------------------
# ROS Checks
# ---------------------------------------------------------------------------

class SimROSMasterCheck(BaseCheck):
    """[SIM] Check if ROS Master is running and reachable"""
    category = CATEGORY_ROS

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "ROSMasterCheck")
        master_uri = self.config.get('ros', {}).get('master_uri', 'http://localhost:11311')

        if outcome == "passed":
            self.message = "ROS Master is running"
            self.details = {"master_uri": master_uri, "simulated": True}
            return True
        else:
            self.message = f"ROS Master not reachable: Connection refused"
            self.details = {"master_uri": master_uri, "simulated": True}
            return False


class SimROSNodesCheck(BaseCheck):
    """[SIM] Check if required ROS nodes are running"""
    category = CATEGORY_ROS

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "ROSNodesCheck")
        required = self.config.get('ros', {}).get('required_nodes', ['/node1', '/node2', '/node3'])

        if outcome == "passed":
            self.message = f"All {len(required)} required node(s) running"
            self.details = {
                "required": required, "running": required, "missing": [],
                "all_running_nodes": required + ["/rosout"],
                "simulated": True
            }
            return True
        elif outcome == "warning":
            self.warn("1 node slow to respond")
            self.details = {"required": required, "running": required, "missing": [], "simulated": True}
            return True
        else:
            missing = required[-1:]
            self.message = f"Missing nodes: {', '.join(missing)}"
            self.details = {
                "required": required, "running": required[:-1], "missing": missing,
                "simulated": True
            }
            return False


class SimROSTopicsCheck(BaseCheck):
    """[SIM] Check if required ROS topics exist and are publishing"""
    category = CATEGORY_ROS

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "ROSTopicsCheck")
        topics = list(self.config.get('ros', {}).get('required_topics', {}).keys())
        if not topics:
            topics = ["/camera/image", "/imu/data", "/odom"]

        if outcome == "passed":
            self.message = f"All {len(topics)} required topic(s) publishing"
            self.details = {
                "required": topics, "publishing": topics, "not_publishing": [],
                "simulated": True
            }
            return True
        else:
            self.message = f"Topics not publishing: {topics[-1]}"
            self.details = {
                "required": topics, "publishing": topics[:-1], "not_publishing": topics[-1:],
                "simulated": True
            }
            return False


class SimTopicRateCheck(BaseCheck):
    """[SIM] Check publishing rates for ROS topics"""
    category = CATEGORY_ROS

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "TopicRateCheck")
        topics_config = self.config.get('ros', {}).get('required_topics', {})

        ok_topics = []
        for name, cfg in topics_config.items():
            min_rate = cfg.get('rate_min', 30)
            ok_topics.append({"topic": name, "rate": round(min_rate * random.uniform(1.0, 1.3), 1), "min": min_rate})

        if outcome == "passed":
            self.message = f"All {len(ok_topics)} topic(s) at acceptable rates"
            self.details = {"ok_topics": ok_topics, "slow_topics": [], "simulated": True}
            return True
        elif outcome == "warning":
            self.warn("1 topic rate borderline")
            self.details = {"ok_topics": ok_topics, "slow_topics": [], "simulated": True}
            return True
        else:
            slow = [{"topic": ok_topics[-1]["topic"], "rate": 5.2, "min": ok_topics[-1]["min"]}]
            self.message = f"1 topic(s) below minimum rate"
            self.details = {"ok_topics": ok_topics[:-1], "slow_topics": slow, "simulated": True}
            return False


class SimTopicFreshnessCheck(BaseCheck):
    """[SIM] Check last message age for ROS topics"""
    category = CATEGORY_ROS

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "TopicFreshnessCheck")
        topics = list(self.config.get('ros', {}).get('required_topics', {}).keys())
        if not topics:
            topics = ["/camera/image", "/imu/data", "/odom"]

        if outcome == "passed":
            self.message = f"All {len(topics)} topic(s) have fresh messages"
            self.details = {"fresh": topics, "stale": [], "simulated": True}
            return True
        else:
            stale = [{"topic": topics[-1], "reason": "Timeout (5.0s)"}]
            self.message = f"1 topic(s) have stale/no messages"
            self.details = {"fresh": topics[:-1], "stale": stale, "simulated": True}
            return False


class SimTFFramesCheck(BaseCheck):
    """[SIM] Check if required TF frames exist"""
    category = CATEGORY_ROS

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "TFFramesCheck")
        frames = self.config.get('ros', {}).get('required_frames', ['base_link', 'camera_link', 'imu_link', 'map'])

        if outcome == "passed":
            self.message = f"All {len(frames)} TF frame(s) available"
            self.details = {"found": frames, "missing": [], "simulated": True}
            return True
        elif outcome == "warning":
            self.warn("TF frame check completed with stale transforms", {
                "found": frames, "missing": [], "simulated": True
            })
            return True
        else:
            self.message = f"Missing TF frames: {frames[-1]}"
            self.details = {"found": frames[:-1], "missing": frames[-1:], "simulated": True}
            return False


class SimRosbagCheck(BaseCheck):
    """[SIM] Check if rosbag logging is enabled and working"""
    category = CATEGORY_ROS

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "RosbagCheck")

        if outcome == "passed":
            self.message = "Rosbag recording active (45.3 MB)"
            self.details = {
                "recording": True,
                "recent_bag": "2026-02-28-10-30-00.bag",
                "size_mb": 45.3,
                "total_bags": 3,
                "simulated": True
            }
            return True
        elif outcome == "warning":
            self.warn("Rosbag recording but no files found yet", {
                "recording": True, "bag_files": 0, "simulated": True
            })
            return True
        else:
            self.message = "Rosbag not recording"
            self.details = {"recording": False, "bag_files": 0, "simulated": True}
            return False


# ---------------------------------------------------------------------------
# Autopilot Checks
# ---------------------------------------------------------------------------

class SimAutopilotDetectCheck(BaseCheck):
    """[SIM] Wait for MAVLink heartbeat from autopilot"""
    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "AutopilotDetectCheck")
        conn = self.config.get('autopilot', {}).get('connection', '/dev/ttyAutopilot')

        if outcome == "passed":
            self.message = "Autopilot detected (System ID: 1)"
            self.details = {
                "system_id": 1, "component_id": 1,
                "connection": conn, "simulated": True
            }
            return True
        else:
            self.message = "No heartbeat received: Connection timed out"
            self.details = {"connection": conn, "simulated": True}
            return False


class SimAutopilotStatusCheck(BaseCheck):
    """[SIM] Check autopilot status for critical errors"""
    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "AutopilotStatusCheck")

        if outcome == "passed":
            voltage = round(random.uniform(12.0, 12.6), 2)
            self.message = f"Autopilot status OK (Battery: {voltage}V)"
            self.details = {
                "voltage": voltage,
                "battery_remaining": random.randint(70, 100),
                "sensors_enabled": 0xFFFF,
                "sensors_health": 0xFFFF,
                "simulated": True
            }
            return True
        elif outcome == "warning":
            self.warn("Battery getting low: 11.0V", {
                "voltage": 11.0,
                "battery_remaining": 25,
                "sensors_enabled": 0xFFFF,
                "sensors_health": 0xFFFE,
                "simulated": True
            })
            return True
        else:
            self.message = "Low battery: 10.2V"
            self.details = {
                "voltage": 10.2,
                "battery_remaining": 5,
                "sensors_enabled": 0xFFFF,
                "sensors_health": 0xFFF0,
                "simulated": True
            }
            return False


class SimAutopilotParamsCheck(BaseCheck):
    """[SIM] Compare autopilot parameters with default.param file"""
    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "AutopilotParamsCheck")

        if outcome in ("passed", "warning"):
            self.warn("Parameter comparison not fully implemented yet")
            self.details = {"default_params_loaded": 142, "simulated": True}
            return True
        else:
            self.message = "Default params file not found"
            self.details = {"simulated": True}
            return False


class SimAutopilotParamExportCheck(BaseCheck):
    """[SIM] Export current autopilot parameters"""
    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        _sim_delay()
        timestamp_filename = datetime.now().strftime("current_device_%Y%m%d_%H%M%S.params")
        self.warn("Parameter export not fully implemented yet")
        self.details = {"export_filename": timestamp_filename, "simulated": True}
        return True


class SimAutopilotSensorsCheck(BaseCheck):
    """[SIM] Check autopilot sensor health (GPS, IMU, barometer)"""
    category = CATEGORY_AUTOPILOT

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "AutopilotSensorsCheck")

        if outcome == "passed":
            self.message = "Sensors OK"
            self.details = {
                "gps_ok": True,
                "gps_fix_type": 3,
                "gps_satellites": random.randint(8, 14),
                "imu_ok": True,
                "simulated": True
            }
            return True
        elif outcome == "warning":
            self.warn("GPS fix type 2 (2D only)", {
                "gps_ok": False,
                "gps_fix_type": 2,
                "gps_satellites": 4,
                "imu_ok": True,
                "simulated": True
            })
            return True
        else:
            self.message = "GPS no 3D fix; IMU data unavailable"
            self.details = {
                "gps_ok": False,
                "gps_fix_type": 1,
                "gps_satellites": 2,
                "imu_ok": False,
                "simulated": True
            }
            return False


# ---------------------------------------------------------------------------
# System Checks
# ---------------------------------------------------------------------------

class SimSystemdServicesCheck(BaseCheck):
    """[SIM] Check if systemd services are active"""
    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "SystemdServicesCheck")
        services = self.config.get('systemd_services', ['roscore', 'autopilot-bridge', 'camera-driver'])

        if outcome == "passed":
            self.message = f"All {len(services)} service(s) active"
            self.details = {"active": services, "inactive": [], "simulated": True}
            return True
        else:
            self.message = f"Inactive services: {services[-1]}"
            self.details = {"active": services[:-1], "inactive": services[-1:], "simulated": True}
            return False


class SimEnvironmentCheck(BaseCheck):
    """[SIM] Check if required environment variables are set"""
    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "EnvironmentCheck")
        env_vars = self.config.get('environment_vars', {})

        if outcome == "passed":
            self.message = f"All {len(env_vars)} environment variable(s) correct"
            self.details = {"correct": env_vars, "incorrect": {}, "missing": [], "simulated": True}
            return True
        elif outcome == "warning":
            self.warn("1 environment variable has non-standard value", {
                "correct": env_vars, "incorrect": {}, "missing": [], "simulated": True
            })
            return True
        else:
            missing = list(env_vars.keys())[-1:]
            self.message = f"Missing: {', '.join(missing)}"
            self.details = {
                "correct": {k: v for k, v in env_vars.items() if k not in missing},
                "incorrect": {},
                "missing": missing,
                "simulated": True
            }
            return False


class SimTimeCheck(BaseCheck):
    """[SIM] Check system time and NTP sync"""
    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "TimeCheck")

        if outcome == "passed":
            self.message = "Time OK, NTP synchronized"
            self.details = {
                "current_time": datetime.utcnow().isoformat(),
                "ntp_synced": True,
                "simulated": True
            }
            return True
        elif outcome == "warning":
            self.warn("Time OK, but NTP sync status unknown", {
                "current_time": datetime.utcnow().isoformat(),
                "ntp_synced": False,
                "simulated": True
            })
            return True
        else:
            self.message = "System time is not set correctly"
            self.details = {"simulated": True}
            return False


class SimStartupScriptCheck(BaseCheck):
    """[SIM] Execute start_system.sh script"""
    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "StartupScriptCheck")

        if outcome == "passed":
            self.message = "Startup script executed successfully"
            self.details = {
                "script": "/home/nvidia/scripts/start_system.sh",
                "exit_code": 0,
                "stdout": "System started successfully.\nAll services launched.",
                "stderr": "",
                "simulated": True
            }
            return True
        else:
            self.message = "Script failed with exit code 1"
            self.details = {
                "script": "/home/nvidia/scripts/start_system.sh",
                "exit_code": 1,
                "stdout": "",
                "stderr": "Error: service failed to start",
                "simulated": True
            }
            return False


class SimLoggingCheck(BaseCheck):
    """[SIM] Run log_test.sh script"""
    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        _sim_delay()
        outcome = _decide_outcome(self.config, "LoggingCheck")

        if outcome == "passed":
            self.message = "Logging check passed"
            self.details = {
                "script": "/home/nvidia/scripts/log_test.sh",
                "exit_code": 0,
                "stdout": "Log test passed. All log targets verified.",
                "stderr": "",
                "simulated": True
            }
            return True
        elif outcome == "warning":
            self.warn("Logging check passed with warnings", {
                "script": "/home/nvidia/scripts/log_test.sh",
                "exit_code": 0,
                "stdout": "Log test passed. Warning: disk space low.",
                "simulated": True
            })
            return True
        else:
            self.message = "Logging check failed with exit code 1"
            self.details = {
                "script": "/home/nvidia/scripts/log_test.sh",
                "exit_code": 1,
                "stderr": "Error: log directory not writable",
                "simulated": True
            }
            return False


class SimMetadataCaptureCheck(BaseCheck):
    """[SIM] Capture system metadata"""
    category = CATEGORY_SYSTEM

    def run(self) -> bool:
        _sim_delay()
        # Metadata capture always passes
        self.message = "Metadata captured"
        self.details = {
            "timestamp": datetime.utcnow().isoformat(),
            "hostname": platform.node(),
            "git_commit": "sim00000",
            "config_file": "config_local.json",
            "simulated": True
        }
        return True


# ---------------------------------------------------------------------------
# Grouped check classes for easy import (mirrors CHECK_CLASSES in test_server)
# ---------------------------------------------------------------------------

SIM_CHECK_CLASSES = {
    'jetson': [SimJetsonBootCheck, SimJetsonResourcesCheck, SimJetsonTemperatureCheck],
    'device': [SimUdevRulesCheck, SimDeviceExistsCheck, SimDeviceHardwareIDCheck,
               SimDevicePermissionsCheck, SimDeviceHandshakeCheck],
    'network': [SimNetworkInterfaceCheck, SimPingTestCheck, SimTestPCConnectivityCheck],
    'ros': [SimROSMasterCheck, SimROSNodesCheck, SimROSTopicsCheck,
            SimTopicRateCheck, SimTopicFreshnessCheck, SimTFFramesCheck, SimRosbagCheck],
    'autopilot': [SimAutopilotDetectCheck, SimAutopilotStatusCheck, SimAutopilotParamsCheck,
                  SimAutopilotParamExportCheck, SimAutopilotSensorsCheck],
    'system': [SimSystemdServicesCheck, SimEnvironmentCheck, SimTimeCheck,
               SimStartupScriptCheck, SimLoggingCheck, SimMetadataCaptureCheck]
}
