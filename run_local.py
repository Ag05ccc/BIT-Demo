"""
Local test launcher for Product Test BIT.
Runs the server in simulation mode and optionally the client, all locally.
No hardware, sensors, ROS, or Jetson required.

Usage:
    python run_local.py                    # Start server only (for manual client testing)
    python run_local.py --run              # Start server + run all tests via client
    python run_local.py --run autopilot    # Start server + run autopilot tests only
    python run_local.py --status           # Start server + show status via client
    python run_local.py --results          # Start server + show latest results via client
"""

import sys
import os
import time
import threading
import subprocess

# Paths
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(PROJECT_ROOT, 'server')
CLIENT_DIR = os.path.join(PROJECT_ROOT, 'client')
CLIENT_CONFIG = os.path.join(CLIENT_DIR, 'client_config_local.json')


def start_sim_server():
    """Start the server in simulation mode in a background thread."""
    # Add paths for imports
    sys.path.insert(0, PROJECT_ROOT)
    sys.path.insert(0, SERVER_DIR)

    import json
    from server.test_server import app, CHECK_CLASSES
    from server.checks.sim_checks import SIM_CHECK_CLASSES

    # Load local config
    config_path = os.path.join(SERVER_DIR, 'config_local.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    # Inject config into server module
    import server.test_server as server_module
    server_module.config = config

    # Swap to simulated checks
    CHECK_CLASSES.clear()
    CHECK_CLASSES.update(SIM_CHECK_CLASSES)

    host = config.get('server', {}).get('host', '127.0.0.1')
    port = config.get('server', {}).get('port', 5000)

    print("=" * 60)
    print(" Product Test BIT - Local Simulation".center(60))
    print("=" * 60)
    print()
    print(f"\u2713 Simulation mode active")
    print(f"\u2713 Server starting on http://{host}:{port}")
    print(f"\u2713 No hardware required")
    print()

    # Run Flask in a daemon thread
    server_thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True
    )
    server_thread.start()

    # Wait for server to be ready
    import urllib.request
    for i in range(30):
        try:
            urllib.request.urlopen(f'http://{host}:{port}/api/status', timeout=2)
            print("\u2713 Server is ready\n")
            return host, port
        except Exception:
            time.sleep(0.3)

    print("\u2717 Server failed to start")
    sys.exit(1)


def run_client(command, category=None):
    """Run the client against the local sim server."""
    cmd = [sys.executable, os.path.join(CLIENT_DIR, 'test_client.py')]
    cmd.extend(['--config', CLIENT_CONFIG])
    cmd.append(command)
    if category:
        cmd.append(category)

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Local test launcher - runs server in simulation mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_local.py                     Start sim server only
  python run_local.py --run               Run all tests
  python run_local.py --run autopilot     Run autopilot tests only
  python run_local.py --run jetson        Run jetson tests only
  python run_local.py --status            Show server status
  python run_local.py --results           Show latest results
        """
    )
    parser.add_argument('--run', nargs='?', const='__all__', default=None,
                        metavar='CATEGORY',
                        help='Run tests (optionally specify category: jetson, device, network, ros, autopilot, system)')
    parser.add_argument('--status', action='store_true',
                        help='Show server status')
    parser.add_argument('--results', action='store_true',
                        help='Show latest test results')

    args = parser.parse_args()

    # Start the sim server
    host, port = start_sim_server()

    # If no client command specified, just keep server running
    if not args.run and not args.status and not args.results:
        print("Server running in simulation mode.")
        print(f"Connect your client to http://{host}:{port}")
        print()
        print("Quick test with client:")
        print(f"  python client/test_client.py --config client/client_config_local.json run")
        print()
        print("Or use this launcher:")
        print(f"  python run_local.py --run")
        print()
        print("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nServer stopped.")
            return 0

    # Run the requested client command
    exit_code = 0

    if args.status:
        exit_code = run_client('status')

    if args.run:
        category = None if args.run == '__all__' else args.run
        exit_code = run_client('run', category)

    if args.results:
        exit_code = run_client('results')

    return exit_code


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
