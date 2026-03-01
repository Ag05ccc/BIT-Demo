"""
Product Test BIT Server - Flask REST API
Runs on Jetson and provides test execution services to Test PC client.
"""

import sys
import os
import json
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from common.models import TestRun, TestSummary, CheckStatus, TestStatus
from common.constants import (
    API_STATUS, API_CONFIG, API_TEST_RUN, API_TEST_RESULTS,
    API_SYSTEM_INFO, API_AUTOPILOT_PARAMS_EXPORT, API_AUTOPILOT_PARAMS_COMPARE,
    API_SCRIPTS_START, API_SCRIPTS_LOG_TEST,
    ALL_CATEGORIES, TEST_ID_FORMAT, TIMESTAMP_FORMAT
)

# Import all check classes
from checks.jetson_checks import JetsonBootCheck, JetsonResourcesCheck, JetsonTemperatureCheck
from checks.device_checks import (
    UdevRulesCheck, DeviceExistsCheck, DeviceHardwareIDCheck,
    DevicePermissionsCheck, DeviceHandshakeCheck
)
from checks.network_checks import NetworkInterfaceCheck, PingTestCheck, TestPCConnectivityCheck
from checks.ros_checks import (
    ROSMasterCheck, ROSNodesCheck, ROSTopicsCheck,
    TopicRateCheck, TopicFreshnessCheck, TFFramesCheck, RosbagCheck
)
from checks.autopilot_checks import (
    AutopilotDetectCheck, AutopilotStatusCheck, AutopilotParamsCheck,
    AutopilotParamExportCheck, AutopilotSensorsCheck
)
from checks.system_checks import (
    SystemdServicesCheck, EnvironmentCheck, TimeCheck,
    StartupScriptCheck, LoggingCheck, MetadataCaptureCheck
)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Global state
config = {}
test_runs = {}  # Store test results by test_id
current_test_id = None
test_lock = threading.Lock()

# All available check classes grouped by category
CHECK_CLASSES = {
    'jetson': [JetsonBootCheck, JetsonResourcesCheck, JetsonTemperatureCheck],
    'device': [UdevRulesCheck, DeviceExistsCheck, DeviceHardwareIDCheck,
               DevicePermissionsCheck, DeviceHandshakeCheck],
    'network': [NetworkInterfaceCheck, PingTestCheck, TestPCConnectivityCheck],
    'ros': [ROSMasterCheck, ROSNodesCheck, ROSTopicsCheck,
            TopicRateCheck, TopicFreshnessCheck, TFFramesCheck, RosbagCheck],
    'autopilot': [AutopilotDetectCheck, AutopilotStatusCheck, AutopilotParamsCheck,
                  AutopilotParamExportCheck, AutopilotSensorsCheck],
    'system': [SystemdServicesCheck, EnvironmentCheck, TimeCheck,
               StartupScriptCheck, LoggingCheck, MetadataCaptureCheck]
}


def load_config():
    """Load configuration from config.json"""
    global config
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"✓ Configuration loaded from {config_path}")
        return True
    except FileNotFoundError:
        print(f"✗ Configuration file not found: {config_path}")
        print("  Please create config.json before starting the server")
        return False
    except json.JSONDecodeError as e:
        print(f"✗ Error parsing config.json: {e}")
        return False


def run_tests_async(categories=None, test_id=None):
    """Run tests asynchronously in background thread"""
    global test_runs, current_test_id

    if test_id is None:
        test_id = datetime.now().strftime(TEST_ID_FORMAT)

    # Create test run object
    test_run = TestRun(
        test_id=test_id,
        status=TestStatus.RUNNING.value,
        started=datetime.utcnow().strftime(TIMESTAMP_FORMAT),
        completed=None,
        summary=TestSummary(),
        results=[]
    )

    with test_lock:
        test_runs[test_id] = test_run
        current_test_id = test_id

    # Determine which categories to run
    if categories is None or 'all' in categories:
        categories_to_run = ALL_CATEGORIES
    else:
        categories_to_run = [c for c in categories if c in ALL_CATEGORIES]

    # Get all check classes to run
    checks_to_run = []
    for category in categories_to_run:
        if category in CHECK_CLASSES:
            for CheckClass in CHECK_CLASSES[category]:
                checks_to_run.append(CheckClass(config))

    # Run checks
    total = len(checks_to_run)
    passed = 0
    failed = 0
    warnings = 0
    skipped = 0

    for check in checks_to_run:
        result = check.execute()
        test_run.results.append(result)

        # Update counters
        if result.status == CheckStatus.PASSED.value:
            passed += 1
        elif result.status == CheckStatus.FAILED.value:
            failed += 1
        elif result.status == CheckStatus.WARNING.value:
            warnings += 1
        elif result.status == CheckStatus.SKIPPED.value:
            skipped += 1

    # Update summary
    test_run.summary.total = total
    test_run.summary.passed = passed
    test_run.summary.failed = failed
    test_run.summary.warnings = warnings
    test_run.summary.skipped = skipped

    # Mark as completed
    test_run.status = TestStatus.COMPLETED.value
    test_run.completed = datetime.utcnow().strftime(TIMESTAMP_FORMAT)

    with test_lock:
        test_runs[test_id] = test_run

    print(f"✓ Test run {test_id} completed: {passed}/{total} passed")


@app.route('/')
def web_gui():
    """Serve the web GUI"""
    return render_template('index.html')


@app.route(API_STATUS, methods=['GET'])
def get_status():
    """Get server health status"""
    import psutil
    import platform

    return jsonify({
        "status": "online",
        "server": "Product Test BIT Server",
        "version": "1.0.0",
        "platform": platform.system(),
        "hostname": platform.node(),
        "uptime_seconds": int(time.time() - psutil.boot_time()) if hasattr(psutil, 'boot_time') else None
    })


@app.route(API_CONFIG, methods=['GET'])
def get_config():
    """Get current configuration"""
    # Return config without sensitive data
    safe_config = {k: v for k, v in config.items() if k not in ['secrets', 'passwords']}
    return jsonify(safe_config)


@app.route(API_TEST_RUN, methods=['POST'])
@app.route(API_TEST_RUN + '/<category>', methods=['POST'])
def run_tests(category=None):
    """Run all tests or tests for specific category"""
    global current_test_id

    # Check if a test is already running
    with test_lock:
        if current_test_id and test_runs.get(current_test_id):
            if test_runs[current_test_id].status == TestStatus.RUNNING.value:
                return jsonify({
                    "error": "A test is already running",
                    "current_test_id": current_test_id
                }), 409  # Conflict

    # Start test in background thread
    test_id = datetime.now().strftime(TEST_ID_FORMAT)
    categories = [category] if category else None

    thread = threading.Thread(target=run_tests_async, args=(categories, test_id))
    thread.daemon = True
    thread.start()

    return jsonify({
        "message": "Test started",
        "test_id": test_id
    }), 202  # Accepted


@app.route(API_TEST_RESULTS, methods=['GET'])
@app.route(API_TEST_RESULTS + '/<test_id>', methods=['GET'])
def get_results(test_id=None):
    """Get test results"""
    global current_test_id

    if test_id is None:
        # Return latest test
        test_id = current_test_id

    if not test_id or test_id not in test_runs:
        return jsonify({"error": "Test not found"}), 404

    test_run = test_runs[test_id]
    return jsonify(test_run.to_dict())


@app.route(API_SYSTEM_INFO, methods=['GET'])
def get_system_info():
    """Get system information"""
    import psutil
    import platform

    try:
        return jsonify({
            "hostname": platform.node(),
            "ip_address": "unknown",  # Would need socket operations
            "os_version": platform.system() + " " + platform.release(),
            "kernel_version": platform.version(),
            "uptime_seconds": int(time.time() - psutil.boot_time()) if hasattr(psutil, 'boot_time') else 0,
            "cpu_count": psutil.cpu_count(),
            "total_ram_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "total_disk_gb": round(psutil.disk_usage('/').total / (1024**3), 2)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route(API_AUTOPILOT_PARAMS_EXPORT, methods=['POST'])
def export_autopilot_params():
    """Export current autopilot parameters"""
    # This would trigger parameter export
    # Placeholder implementation
    return jsonify({
        "message": "Parameter export not fully implemented",
        "filename": datetime.now().strftime("current_device_%Y%m%d_%H%M%S.params")
    })


@app.route(API_AUTOPILOT_PARAMS_COMPARE, methods=['POST'])
def compare_autopilot_params():
    """Compare autopilot parameters with default"""
    # Placeholder implementation
    return jsonify({
        "message": "Parameter comparison not fully implemented"
    })


@app.route(API_SCRIPTS_START, methods=['POST'])
def run_start_script():
    """Run start_system.sh script"""
    import subprocess
    script_path = config.get('scripts', {}).get('startup')
    if not script_path:
        return jsonify({"error": "Startup script not configured"}), 400

    try:
        result = subprocess.run([script_path], capture_output=True, text=True, timeout=60)
        return jsonify({
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route(API_SCRIPTS_LOG_TEST, methods=['POST'])
def run_log_test_script():
    """Run log_test.sh script"""
    import subprocess
    script_path = config.get('scripts', {}).get('log_test')
    if not script_path:
        return jsonify({"error": "Log test script not configured"}), 400

    try:
        result = subprocess.run([script_path], capture_output=True, text=True, timeout=60)
        return jsonify({
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    import time
    import argparse

    parser = argparse.ArgumentParser(description="Product Test BIT Server")
    parser.add_argument('--sim', action='store_true',
                        help='Run in simulation mode (no hardware required)')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to config file (default: config.json, or config_local.json with --sim)')
    server_args = parser.parse_args()

    # Determine config file
    if server_args.config:
        config_file = server_args.config
    elif server_args.sim:
        config_file = os.path.join(os.path.dirname(__file__), 'config_local.json')
    else:
        config_file = None  # Will use default config.json

    print("=" * 60)
    if server_args.sim:
        print(" Product Test BIT Server [SIMULATION MODE]".center(60))
    else:
        print(" Product Test BIT Server".center(60))
    print("=" * 60)
    print()

    # Load configuration
    if config_file:
        # Load from specified path
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"\u2713 Configuration loaded from {config_file}")
        except FileNotFoundError:
            print(f"\u2717 Configuration file not found: {config_file}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"\u2717 Error parsing config file: {e}")
            sys.exit(1)
    else:
        if not load_config():
            sys.exit(1)

    # Swap to simulated checks if --sim
    if server_args.sim:
        from checks.sim_checks import SIM_CHECK_CLASSES
        CHECK_CLASSES.clear()
        CHECK_CLASSES.update(SIM_CHECK_CLASSES)
        print("\u2713 Simulation mode active - using simulated checks")
        print("  No hardware, sensors, or ROS required")

    # Get server config
    server_config = config.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 5000)
    debug = server_config.get('debug', False)

    print(f"\nStarting server on {host}:{port}...")
    print(f"Debug mode: {debug}")
    print()
    gui_host = '127.0.0.1' if host == '0.0.0.0' else host
    print(f"Web GUI:  http://{gui_host}:{port}")
    print()
    print("API endpoints:")
    print(f"  GET  {API_STATUS}")
    print(f"  GET  {API_SYSTEM_INFO}")
    print(f"  POST {API_TEST_RUN}")
    print(f"  GET  {API_TEST_RESULTS}")
    print()
    print("Server is ready. Press Ctrl+C to stop.")
    print("=" * 60)
    print()

    app.run(host=host, port=port, debug=debug)
