"""
Solution hints for all checks.
When a check fails or warns, the corresponding solution is attached
to the result details so the user knows what to do.

Keys are check class names (without the 'Sim' prefix for sim checks).
Each entry has solutions for 'failed', 'warning', and optionally 'skipped'.
"""

SOLUTION_HINTS = {
    # -------------------------------------------------------------------------
    # Jetson Checks
    # -------------------------------------------------------------------------
    "JetsonBootCheck": {
        "failed": (
            "1. Review the listed dmesg errors to identify the failing subsystem\n"
            "2. Check if a recent kernel or firmware update caused new errors\n"
            "3. Reboot the Jetson and check if errors persist\n"
            "4. For GPU/PCIe errors: reseat the module and check thermal paste\n"
            "5. For USB errors: disconnect and reconnect external devices"
        ),
        "warning": (
            "1. Review the listed warnings - they may be harmless (e.g. optional firmware)\n"
            "2. Add known-harmless errors to the filter list in JetsonBootCheck\n"
            "3. Monitor if warnings increase over time"
        ),
    },
    "JetsonResourcesCheck": {
        "failed": (
            "1. CPU high: Identify heavy processes with 'top' or 'htop', kill unnecessary ones\n"
            "2. RAM high: Check for memory leaks, restart services consuming excess memory\n"
            "3. Disk low: Remove old rosbags/logs with 'du -sh /home/nvidia/rosbags/*'\n"
            "4. Adjust thresholds in config.json under 'resources' if current limits are too strict"
        ),
        "warning": (
            "1. Monitor resource trends - usage may spike during test execution\n"
            "2. Consider closing unnecessary applications before running tests\n"
            "3. If recurring, adjust thresholds in config.json"
        ),
    },
    "JetsonTemperatureCheck": {
        "failed": (
            "1. Check that the Jetson fan is spinning and not blocked\n"
            "2. Ensure adequate airflow around the device\n"
            "3. Clean dust from heatsink and fan\n"
            "4. Reduce CPU/GPU load - stop non-essential processes\n"
            "5. If in an enclosure, verify ventilation holes are not obstructed\n"
            "6. Wait for the device to cool down before retesting"
        ),
        "warning": (
            "1. Temperature is approaching the limit - ensure good airflow\n"
            "2. Check that the fan profile is set to active cooling\n"
            "3. Consider reducing workload or improving thermal solution"
        ),
    },

    # -------------------------------------------------------------------------
    # Device Checks
    # -------------------------------------------------------------------------
    "UdevRulesCheck": {
        "failed": (
            "1. Copy the udev rules file to /etc/udev/rules.d/:\n"
            "   sudo cp rules/99-autopilot.rules /etc/udev/rules.d/\n"
            "2. Reload udev rules: sudo udevadm control --reload-rules\n"
            "3. Trigger udev: sudo udevadm trigger\n"
            "4. Verify the rules file has correct syntax"
        ),
        "skipped": "No udev rules are configured in config.json to check.",
    },
    "DeviceExistsCheck": {
        "failed": (
            "1. Check that all USB devices/sensors are physically connected\n"
            "2. Try a different USB port or cable\n"
            "3. Run 'lsusb' to see if the device is detected by the system\n"
            "4. Check 'dmesg | tail -20' for USB connection errors\n"
            "5. Verify the device path in config.json matches actual /dev/ entries\n"
            "6. If using a USB hub, try connecting directly to the Jetson"
        ),
        "skipped": "No devices are configured in config.json to check.",
    },
    "DeviceHardwareIDCheck": {
        "failed": (
            "1. The connected device has a different vendor/product ID than expected\n"
            "2. Run 'lsusb' to find the actual vendor:product IDs\n"
            "3. Update config.json with the correct vendor_id and product_id\n"
            "4. Verify you have the correct hardware model connected\n"
            "5. Check if a firmware update changed the device IDs"
        ),
        "skipped": "udevadm not available or no hardware IDs configured.",
    },
    "DevicePermissionsCheck": {
        "failed": (
            "1. Add your user to the 'dialout' group: sudo usermod -a -G dialout $USER\n"
            "2. Log out and log back in for group changes to take effect\n"
            "3. Verify udev rules grant proper permissions (MODE=\"0666\")\n"
            "4. As a quick test: sudo chmod 666 /dev/ttyUSB0\n"
            "5. Check device ownership: ls -la /dev/ttyUSB*"
        ),
    },
    "DeviceHandshakeCheck": {
        "failed": (
            "1. Check that the device is powered on and ready to communicate\n"
            "2. Verify the baud rate in config.json matches the device setting\n"
            "3. Check the cable connection - try reseating or replacing the cable\n"
            "4. Test manually: screen /dev/ttyUSB0 9600 (then type the test command)\n"
            "5. Verify the test_command and expected_response in config.json are correct\n"
            "6. Check if another process is using the serial port: lsof /dev/ttyUSB0"
        ),
        "skipped": "pyserial not installed or no handshake test configured for devices.",
    },

    # -------------------------------------------------------------------------
    # Network Checks
    # -------------------------------------------------------------------------
    "NetworkInterfaceCheck": {
        "failed": (
            "1. Check physical Ethernet cable connection\n"
            "2. For WiFi: verify the adapter is enabled and connected to the network\n"
            "3. Bring interface up: sudo ip link set eth0 up\n"
            "4. Check network manager: nmcli device status\n"
            "5. Restart networking: sudo systemctl restart NetworkManager"
        ),
        "skipped": "'ip' command not found on this system.",
    },
    "PingTestCheck": {
        "failed": (
            "1. Verify the target IP addresses in config.json are correct\n"
            "2. Check network cable and switch connections\n"
            "3. Verify the target devices are powered on\n"
            "4. Check firewall rules on both Jetson and target: sudo iptables -L\n"
            "5. Verify subnet and gateway: ip route show\n"
            "6. Try ping manually: ping -c 3 <target_ip>"
        ),
        "skipped": "No ping targets configured in config.json.",
    },
    "TestPCConnectivityCheck": {
        "failed": (
            "1. Verify the Test PC is powered on and connected to the same network\n"
            "2. Check the expected_ip in config.json matches the Test PC's actual IP\n"
            "3. Check firewall on the Test PC - ICMP ping may be blocked\n"
            "4. Verify both devices are on the same subnet\n"
            "5. Try pinging from the Test PC to the Jetson to test the reverse path"
        ),
        "skipped": "Test PC IP not configured in config.json.",
    },

    # -------------------------------------------------------------------------
    # ROS Checks
    # -------------------------------------------------------------------------
    "ROSMasterCheck": {
        "failed": (
            "1. Start ROS Master: roscore\n"
            "2. Verify ROS_MASTER_URI is set correctly: echo $ROS_MASTER_URI\n"
            "3. If Master is on another machine, check network connectivity\n"
            "4. Check if port 11311 is blocked by firewall\n"
            "5. Restart roscore if it crashed: killall -9 roscore && roscore"
        ),
        "skipped": "ROS is not installed. Install ros-noetic-desktop-full.",
    },
    "ROSNodesCheck": {
        "failed": (
            "1. Check which nodes are missing from the error message\n"
            "2. Start the missing node's launch file\n"
            "3. Check node logs: rosnode info /<node_name>\n"
            "4. Look for crash logs: ~/.ros/log/latest/*.log\n"
            "5. Verify all launch files are configured correctly\n"
            "6. Check if a required dependency node needs to start first"
        ),
        "warning": (
            "1. A node is responding slowly - check system CPU/memory load\n"
            "2. Verify the node isn't stuck in a processing loop\n"
            "3. Check node logs for warnings: rosnode info /<node_name>"
        ),
        "skipped": "ROS not installed or no required nodes configured.",
    },
    "ROSTopicsCheck": {
        "failed": (
            "1. Check which topics are missing from the error message\n"
            "2. Verify the publishing node is running: rosnode list\n"
            "3. Check topic manually: rostopic list | grep <topic_name>\n"
            "4. Verify the sensor/camera driver is running and publishing\n"
            "5. Check for namespace issues: rostopic list to see actual topic names"
        ),
        "skipped": "ROS not installed or no required topics configured.",
    },
    "TopicRateCheck": {
        "failed": (
            "1. Check the publishing rate: rostopic hz /<topic_name>\n"
            "2. If rate is low, the sensor/driver may be overloaded\n"
            "3. Check CPU usage - high CPU can cause rate drops\n"
            "4. Verify sensor configuration (e.g., camera FPS setting)\n"
            "5. Check for network bandwidth issues if topics are remapped\n"
            "6. Adjust rate_min in config.json if the requirement is too strict"
        ),
        "warning": (
            "1. Topic rate is borderline - monitor for degradation\n"
            "2. Check system load and consider reducing other processes"
        ),
    },
    "TopicFreshnessCheck": {
        "failed": (
            "1. The topic exists but no new messages are being published\n"
            "2. Check if the sensor/driver is frozen or crashed\n"
            "3. Restart the publishing node\n"
            "4. Verify hardware connections for the sensor\n"
            "5. Check for error output in the node's terminal"
        ),
    },
    "TFFramesCheck": {
        "failed": (
            "1. Check which TF frames are missing\n"
            "2. Verify the robot_state_publisher or static_transform_publisher is running\n"
            "3. View the TF tree: rosrun tf view_frames\n"
            "4. Check URDF/xacro for correct frame definitions\n"
            "5. Verify the sensor drivers are publishing TF transforms"
        ),
        "warning": (
            "1. TF transforms may be stale - check the publishing nodes\n"
            "2. Run: rosrun tf tf_echo <parent_frame> <child_frame>"
        ),
        "skipped": "ROS not installed or no required TF frames configured.",
    },
    "RosbagCheck": {
        "failed": (
            "1. Start rosbag recording: rosbag record -a -o /home/nvidia/rosbags/test\n"
            "2. Check if the rosbag directory exists and is writable\n"
            "3. Verify disk space is sufficient for recording\n"
            "4. Check if rosbag record process crashed: ps aux | grep rosbag"
        ),
        "warning": (
            "1. Recording started but bag files are small or not yet created\n"
            "2. Wait a moment and recheck - bag files take time to flush\n"
            "3. Verify topics are being published for recording"
        ),
        "skipped": "Rosbag directory not configured in config.json.",
    },

    # -------------------------------------------------------------------------
    # Autopilot Checks
    # -------------------------------------------------------------------------
    "AutopilotDetectCheck": {
        "failed": (
            "1. Check the autopilot USB/serial cable connection\n"
            "2. Verify the autopilot is powered on (check LEDs)\n"
            "3. Check the connection string in config.json (e.g., /dev/ttyAutopilot)\n"
            "4. Verify the baud rate matches the autopilot setting (usually 921600)\n"
            "5. Check if another process is using the port: lsof /dev/ttyAutopilot\n"
            "6. Try power-cycling the autopilot\n"
            "7. Test with MAVProxy: mavproxy.py --master=/dev/ttyAutopilot --baudrate=921600"
        ),
        "skipped": "pymavlink not installed. Install with: pip install pymavlink",
    },
    "AutopilotStatusCheck": {
        "failed": (
            "1. Low battery: Charge or replace the battery immediately\n"
            "2. Sensor errors: Check IMU, GPS, and barometer connections\n"
            "3. Verify no pre-arm errors in the autopilot log\n"
            "4. Connect via Mission Planner/QGroundControl for detailed diagnostics\n"
            "5. Check if the autopilot firmware needs updating"
        ),
        "warning": (
            "1. Battery getting low - consider charging before testing\n"
            "2. Some sensors may be unhealthy - check via GCS for details\n"
            "3. Monitor battery voltage during test execution"
        ),
    },
    "AutopilotParamsCheck": {
        "failed": (
            "1. Ensure the default.param file exists at the configured path\n"
            "2. Re-export the baseline parameters: python run_local.py --run autopilot\n"
            "3. If parameters were intentionally changed, update default.param\n"
            "4. Check param_tolerance in config.json if small drifts are expected"
        ),
        "warning": "Parameter comparison is not fully implemented yet. This is expected.",
        "skipped": "Default params file not configured or not found.",
    },
    "AutopilotParamExportCheck": {
        "warning": "Parameter export is not fully implemented yet. This is expected.",
        "skipped": "pymavlink not installed.",
    },
    "AutopilotSensorsCheck": {
        "failed": (
            "1. GPS no 3D fix: Move to an area with clear sky view, wait for fix\n"
            "2. GPS antenna: Check GPS antenna cable and connector\n"
            "3. IMU unavailable: Check the IMU module connection to the autopilot\n"
            "4. Barometer: Ensure the barometer port is not blocked or damaged\n"
            "5. Power-cycle the autopilot and wait 30 seconds for sensors to initialize\n"
            "6. Check for electromagnetic interference near GPS antenna"
        ),
        "warning": (
            "1. GPS has only 2D fix - move to a location with better sky visibility\n"
            "2. Wait for more satellites to lock (need at least 8 for good fix)"
        ),
    },

    # -------------------------------------------------------------------------
    # System Checks
    # -------------------------------------------------------------------------
    "SystemdServicesCheck": {
        "failed": (
            "1. Start the failed service: sudo systemctl start <service_name>\n"
            "2. Check service logs: journalctl -u <service_name> --no-pager -n 50\n"
            "3. Check service status: systemctl status <service_name>\n"
            "4. Enable the service to start at boot: sudo systemctl enable <service_name>\n"
            "5. If the service keeps crashing, check its configuration files"
        ),
        "skipped": "systemctl not found - not a systemd-based system.",
    },
    "EnvironmentCheck": {
        "failed": (
            "1. Set missing environment variables in ~/.bashrc or /etc/environment:\n"
            "   export ROS_MASTER_URI=http://192.168.1.1:11311\n"
            "   export ROS_IP=192.168.1.2\n"
            "2. Source the file: source ~/.bashrc\n"
            "3. Verify values match config.json expected values\n"
            "4. For systemd services, set env vars in the service file's [Service] section"
        ),
        "warning": (
            "1. An environment variable has a non-standard value\n"
            "2. Verify it is intentional or update config.json to match"
        ),
        "skipped": "No environment variables configured in config.json.",
    },
    "TimeCheck": {
        "failed": (
            "1. Set the system time manually: sudo date -s 'YYYY-MM-DD HH:MM:SS'\n"
            "2. Enable NTP: sudo timedatectl set-ntp true\n"
            "3. Check NTP service: systemctl status systemd-timesyncd\n"
            "4. If no internet, configure a local NTP server in /etc/systemd/timesyncd.conf"
        ),
        "warning": (
            "1. Time appears correct but NTP sync status is unknown\n"
            "2. Enable NTP for accurate time: sudo timedatectl set-ntp true\n"
            "3. On networks without internet, configure a local NTP server"
        ),
    },
    "StartupScriptCheck": {
        "failed": (
            "1. Check if the script exists at the configured path\n"
            "2. Make the script executable: chmod +x /home/nvidia/scripts/start_system.sh\n"
            "3. Check the script for errors: bash -x /home/nvidia/scripts/start_system.sh\n"
            "4. Verify all dependencies the script needs are installed\n"
            "5. Check the stderr output in the check details for specific error messages"
        ),
        "skipped": "Startup script not configured in config.json.",
    },
    "LoggingCheck": {
        "failed": (
            "1. Check if the log test script exists at the configured path\n"
            "2. Make the script executable: chmod +x /home/nvidia/scripts/log_test.sh\n"
            "3. Verify the log directory is writable\n"
            "4. Check disk space: df -h\n"
            "5. Review stderr in check details for the specific error"
        ),
        "warning": (
            "1. Logging works but with warnings - check disk space\n"
            "2. Verify log rotation is configured to prevent disk fill"
        ),
        "skipped": "Log test script not configured in config.json.",
    },
    "MetadataCaptureCheck": {
        "failed": (
            "1. This check rarely fails - check for filesystem permission issues\n"
            "2. Verify git is installed if git commit capture is needed\n"
            "3. Check the exception details for the specific error"
        ),
    },
}


def get_solution(check_name, status):
    """
    Get the solution hint for a check based on its status.

    Args:
        check_name: The check class name (e.g., 'JetsonBootCheck' or 'SimJetsonBootCheck')
        status: The check result status ('failed', 'warning', 'skipped')

    Returns:
        Solution string or None if no solution is available
    """
    # Strip 'Sim' prefix for sim checks to share the same solutions
    clean_name = check_name
    if clean_name.startswith("Sim"):
        clean_name = clean_name[3:]

    hints = SOLUTION_HINTS.get(clean_name, {})
    return hints.get(status)
