"""
Product Test BIT Server - Flask REST API
Runs on Jetson and provides test execution services to Test PC client.
"""

import sys
import os
import json
import time
import threading
import logging
from datetime import datetime
from flask import Flask, jsonify, request, render_template, Response

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

@app.after_request
def _add_cors(response):
    """Allow cross-origin requests without requiring flask-cors."""
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

# Global state
config = {}
test_runs = {}  # Store test results by test_id
current_test_id = None
test_lock = threading.Lock()

def setup_debug_logging(debug_mode: bool):
    """
    Configure Python logging for developer/debug mode.

    Normal mode  – WARNING+ messages printed with a compact format.
    Debug mode   – DEBUG+  messages printed with file:line references so
                   developers can click straight to the offending source.
    """
    level = logging.DEBUG if debug_mode else logging.WARNING
    fmt = (
        "[%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        if debug_mode
        else "[%(levelname)s] %(message)s"
    )
    logging.basicConfig(level=level, format=fmt, force=True)
    # Silence Flask/Werkzeug noise unless we are in debug mode
    logging.getLogger("werkzeug").setLevel(logging.DEBUG if debug_mode else logging.ERROR)


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


def generate_html_report(test_run_dict, sys_info_dict=None):
    """
    Build a self-contained HTML test report from a TestRun dict.
    Uses only stdlib — no external template engine required.
    """
    import html as _html

    def _e(s):
        """HTML-escape a value."""
        return _html.escape(str(s)) if s is not None else ''

    td       = test_run_dict
    summary  = td.get('summary', {})
    results  = td.get('results', [])
    test_id  = td.get('test_id', 'unknown')
    started  = td.get('started', '')
    completed = td.get('completed', '')

    total    = summary.get('total',    0)
    passed   = summary.get('passed',   0)
    failed   = summary.get('failed',   0)
    warnings = summary.get('warnings', 0)
    skipped  = summary.get('skipped',  0)

    # Overall verdict
    if failed > 0:
        verdict, verdict_color = 'FAILED',                '#ff3d3d'
    elif warnings > 0:
        verdict, verdict_color = 'PASSED WITH WARNINGS',  '#ff9500'
    else:
        verdict, verdict_color = 'PASSED',                '#00c853'

    # Duration
    duration_str = 'N/A'
    if started and completed:
        try:
            from datetime import datetime as _dt2
            s_dt = _dt2.fromisoformat(started.rstrip('Z'))
            e_dt = _dt2.fromisoformat(completed.rstrip('Z'))
            secs = (e_dt - s_dt).total_seconds()
            duration_str = f'{secs:.1f}s'
        except Exception:
            pass

    _icons  = {
        'passed':  '\u2713',
        'failed':  '\u2717',
        'warning': '\u26a0',
        'skipped': '\u25cb',
        'running': '\u27f3',
    }
    _colors = {
        'passed':  '#00c853',
        'failed':  '#ff3d3d',
        'warning': '#ff9500',
        'skipped': '#4488cc',
        'running': '#00b8d4',
    }

    # ------------------------------------------------------------------ #
    # Results table rows
    # ------------------------------------------------------------------ #
    rows = []
    for r in results:
        status   = r.get('status', 'unknown')
        icon     = _icons.get(status, '?')
        color    = _colors.get(status, '#c8d8e8')
        raw_name = r.get('name', '')
        if raw_name.startswith('Sim'):
            raw_name = raw_name[3:]
        category = r.get('category', '')
        message  = r.get('message', '')
        duration = r.get('duration', 0)

        rows.append(
            '<tr>'
            '<td><span style="color:' + color + ';font-weight:600">'
            + icon + ' ' + _e(status) + '</span></td>'
            '<td><span class="cat-badge">' + _e(category) + '</span></td>'
            '<td>' + _e(raw_name) + '</td>'
            '<td>' + _e(message) + '</td>'
            '<td style="text-align:right;font-family:monospace;color:#4e6070">'
            + f'{duration:.2f}s' + '</td>'
            '</tr>'
        )

        details  = r.get('details') or {}
        solution = details.get('solution', '')
        if solution and status in ('failed', 'warning', 'skipped'):
            border_c = '#ff3d3d' if status == 'failed' else '#ff9500'
            rows.append(
                '<tr><td colspan="5" style="padding:0 12px 12px 44px">'
                '<div style="background:#1a2232;border-radius:6px;padding:10px 14px;'
                'border-left:3px solid ' + border_c + ';white-space:pre-wrap;'
                'color:#4e6070;font-size:12px;line-height:1.6">'
                '<div style="font-weight:600;color:#c8d8e8;margin-bottom:4px">'
                '\U0001f6e0 How to fix:</div>'
                + _e(solution) +
                '</div></td></tr>'
            )

    all_rows = '\n'.join(rows)

    # ------------------------------------------------------------------ #
    # Issues detail section (failed / warning / skipped with extra data)
    # ------------------------------------------------------------------ #
    issues = [
        r for r in results
        if r.get('status') in ('failed', 'warning', 'skipped')
        and (
            (r.get('details') or {}).get('solution')
            or (r.get('details') or {}).get('source_location')
            or (r.get('details') or {}).get('traceback')
        )
    ]

    issue_cards = []
    for r in issues:
        status   = r.get('status', '')
        color    = _colors.get(status, '#c8d8e8')
        icon     = _icons.get(status, '?')
        raw_name = r.get('name', '')
        if raw_name.startswith('Sim'):
            raw_name = raw_name[3:]
        details    = r.get('details') or {}
        source_loc = details.get('source_location', '')
        solution   = details.get('solution', '')
        tb_text    = details.get('traceback', '')

        card = [
            '<div style="background:#131821;border-radius:8px;padding:16px;'
            'margin-bottom:16px;border-left:3px solid ' + color + '">',
            '<div style="font-size:15px;font-weight:600;color:' + color
            + ';margin-bottom:8px">' + icon + ' ' + _e(raw_name) + '</div>',
            '<div style="color:#4e6070;font-size:13px;margin-bottom:8px">'
            + _e(r.get('message', '')) + '</div>',
        ]

        if source_loc:
            card.append(
                '<div style="font-size:12px;color:#4e6070;margin-bottom:8px">'
                '<b style="color:#c8d8e8">Source:</b> '
                '<code style="color:#1a8cff">' + _e(source_loc) + '</code></div>'
            )

        if solution:
            border_c = '#ff3d3d' if status == 'failed' else '#ff9500'
            card.append(
                '<div style="background:#1a2232;border-radius:6px;padding:10px 14px;'
                'border-left:3px solid ' + border_c + ';white-space:pre-wrap;'
                'color:#4e6070;font-size:12px;margin-bottom:8px">'
                '<b style="color:#c8d8e8">How to fix:</b>\n'
                + _e(solution) + '</div>'
            )

        if tb_text:
            card.append(
                '<details><summary style="cursor:pointer;color:#4e6070;font-size:12px">'
                '\u25b6 Full Traceback</summary>'
                '<pre style="background:#0c0f14;padding:12px;border-radius:6px;'
                'font-size:11px;overflow-x:auto;white-space:pre-wrap;'
                'color:#ff6b6b;margin-top:8px">'
                + _e(tb_text) + '</pre></details>'
            )

        card.append('</div>')
        issue_cards.append(''.join(card))

    issues_html = ''
    if issue_cards:
        issues_html = (
            '<h2 style="margin:32px 0 16px;font-size:16px;letter-spacing:1px;'
            'text-transform:uppercase;color:#c8d8e8;'
            'border-bottom:1px solid #1e2d40;padding-bottom:8px">Issues Detail</h2>'
            + ''.join(issue_cards)
        )

    # ------------------------------------------------------------------ #
    # System info table
    # ------------------------------------------------------------------ #
    si = sys_info_dict or {}
    sys_section = ''
    if si:
        si_rows = [
            ('Hostname',  si.get('hostname',       '?')),
            ('OS',        si.get('os_version',     '?')),
            ('Kernel',    si.get('kernel_version', '?')),
            ('CPU Cores', si.get('cpu_count',      '?')),
            ('RAM',       f"{si.get('total_ram_gb',  0):.2f} GB"),
            ('Disk',      f"{si.get('total_disk_gb', 0):.2f} GB"),
        ]
        si_html = ''.join(
            '<tr><td style="color:#4e6070;width:120px">' + _e(lbl) + '</td>'
            '<td><b>' + _e(val) + '</b></td></tr>'
            for lbl, val in si_rows
        )
        sys_section = (
            '<h2 style="margin-bottom:16px;font-size:16px;letter-spacing:1px;'
            'text-transform:uppercase;color:#c8d8e8;'
            'border-bottom:1px solid #1e2d40;padding-bottom:8px">'
            'System Information</h2>'
            '<table style="margin-bottom:32px">' + si_html + '</table>'
        )

    # ------------------------------------------------------------------ #
    # Summary stat cards
    # ------------------------------------------------------------------ #
    def _stat_card(count, label, color):
        return (
            '<div style="background:#131821;border-radius:8px;padding:16px;'
            'border-left:3px solid ' + color + ';text-align:center">'
            '<div style="font-size:28px;font-weight:700;color:' + color + '">'
            + str(count) +
            '</div><div style="font-size:12px;color:#4e6070;'
            'text-transform:uppercase;margin-top:4px">' + label + '</div>'
            '</div>'
        )

    stat_cards = (
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
        'gap:12px;margin-bottom:32px">'
        + _stat_card(passed,   'Passed',   '#00c853')
        + _stat_card(failed,   'Failed',   '#ff3d3d')
        + _stat_card(warnings, 'Warnings', '#ff9500')
        + _stat_card(skipped,  'Skipped',  '#4488cc')
        + '</div>'
    )

    generated_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    # ------------------------------------------------------------------ #
    # Assemble full document
    # ------------------------------------------------------------------ #
    doc = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<title>BIT Test Report \u2014 ' + _e(test_id) + '</title>\n'
        '<style>\n'
        '  * { margin:0; padding:0; box-sizing:border-box; }\n'
        '  body { font-family: \'Segoe UI\', system-ui, sans-serif;'
        ' background:#0c0f14; color:#c8d8e8;'
        ' padding:32px; max-width:1100px; margin:0 auto; }\n'
        '  h1 { font-size:22px; font-weight:700; letter-spacing:1px;'
        ' text-transform:uppercase; }\n'
        '  table { width:100%; border-collapse:collapse; font-size:13px; }\n'
        '  th { text-align:left; padding:10px 12px; background:#131821;'
        ' color:#4e6070; font-size:12px; text-transform:uppercase;'
        ' letter-spacing:0.5px; border-bottom:1px solid #1e2d40; }\n'
        '  td { padding:10px 12px; border-bottom:1px solid #1e2d40;'
        ' vertical-align:top; }\n'
        '  .cat-badge { display:inline-block; padding:2px 8px;'
        ' border-radius:4px; background:#1a2232;'
        ' font-size:11px; color:#4e6070; }\n'
        '  @media print { body { background:white; color:black;'
        ' padding:16px; } }\n'
        '</style>\n</head>\n<body>\n'

        # Page header
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;margin-bottom:24px;padding-bottom:16px;'
        'border-bottom:2px solid #1a8cff">\n'
        '  <div>\n'
        '    <div style="color:#4e6070;font-size:12px;letter-spacing:1px;'
        'text-transform:uppercase;margin-bottom:6px">Automated Test Report</div>\n'
        '    <h1><span style="color:#1a8cff">Product Test</span> BIT</h1>\n'
        '  </div>\n'
        '  <div style="text-align:right;font-size:12px;color:#4e6070">\n'
        '    <div>Test ID: <b style="color:#c8d8e8">' + _e(test_id) + '</b></div>\n'
        '    <div>Started: <b style="color:#c8d8e8">' + _e(started) + '</b></div>\n'
        '    <div>Duration: <b style="color:#c8d8e8">' + _e(duration_str) + '</b></div>\n'
        '    <div>Generated: <b style="color:#c8d8e8">' + _e(generated_at) + '</b></div>\n'
        '  </div>\n</div>\n'

        # Verdict banner
        '<div style="background:' + verdict_color + '22;border:1px solid '
        + verdict_color + ';border-radius:8px;padding:16px 24px;'
        'margin-bottom:24px;text-align:center">\n'
        '  <div style="font-size:24px;font-weight:700;color:' + verdict_color
        + ';letter-spacing:2px">' + verdict + '</div>\n'
        '  <div style="color:#4e6070;font-size:13px;margin-top:4px">'
        + str(passed) + '/' + str(total) + ' checks passed</div>\n'
        '</div>\n'

        # Summary cards
        + stat_cards

        # System info
        + sys_section

        # Results table
        + '<h2 style="margin-bottom:16px;font-size:16px;letter-spacing:1px;'
        'text-transform:uppercase;color:#c8d8e8;'
        'border-bottom:1px solid #1e2d40;padding-bottom:8px">Test Results</h2>\n'
        '<table style="margin-bottom:32px">\n'
        '<thead><tr>'
        '<th style="width:100px">Status</th>'
        '<th style="width:110px">Category</th>'
        '<th>Check</th>'
        '<th>Message</th>'
        '<th style="width:70px;text-align:right">Duration</th>'
        '</tr></thead>\n'
        '<tbody>\n' + all_rows + '\n</tbody>\n</table>\n'

        # Issues detail
        + issues_html

        # Footer
        + '<div style="margin-top:32px;padding-top:16px;'
        'border-top:1px solid #1e2d40;font-size:12px;color:#4e6070;text-align:center">'
        'Generated by Product Test BIT &nbsp;|&nbsp; ' + _e(generated_at)
        + '</div>\n'
        '</body>\n</html>'
    )

    return doc


@app.route('/api/report', methods=['GET'])
@app.route('/api/report/<test_id>', methods=['GET'])
def get_report(test_id=None):
    """Generate and download a self-contained HTML test report."""
    import platform
    import psutil
    global current_test_id

    if test_id is None:
        test_id = current_test_id

    if not test_id or test_id not in test_runs:
        return jsonify({"error": "No test results available"}), 404

    try:
        sys_info = {
            "hostname":       platform.node(),
            "os_version":     platform.system() + " " + platform.release(),
            "kernel_version": platform.version(),
            "cpu_count":      psutil.cpu_count(),
            "total_ram_gb":   round(psutil.virtual_memory().total / (1024 ** 3), 2),
            "total_disk_gb":  round(psutil.disk_usage('/').total  / (1024 ** 3), 2),
        }
    except Exception:
        sys_info = {}

    html_content = generate_html_report(test_runs[test_id].to_dict(), sys_info)
    filename = f"bit_report_{test_id}.html"

    return Response(
        html_content,
        mimetype='text/html',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


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
    parser.add_argument('--debug', action='store_true',
                        help='Enable developer/debug mode: logs source file:line for every '
                             'error and warning and includes full tracebacks in API results')
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
    if server_args.debug:
        print("\u26a0  Developer/Debug mode ON")
        print("   - Source file:line logged for every error and warning")
        print("   - Full tracebacks included in API results")
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

    # Resolve developer/debug mode (CLI flag takes priority over config file)
    debug_mode = server_args.debug or config.get('developer', {}).get('debug', False)
    if 'developer' not in config:
        config['developer'] = {}
    config['developer']['debug'] = debug_mode
    setup_debug_logging(debug_mode)

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
