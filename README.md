# Product Test BIT (Built-In Test) Application

A comprehensive test application for robotics/drone systems with a client-server architecture. The test logic runs ON the Jetson device (with direct access to autopilot and peripherals), while the Test PC acts as a client to trigger tests and display results.

## Architecture

```
┌─────────────────┐                      ┌──────────────────────────────────┐
│   Test PC       │  Ethernet/HTTP       │   Jetson (Test Device)           │
│  (Windows/Linux)│◄────────────────────►│   (Linux)                        │
│                 │                      │                                  │
│  - CLI Client   │                      │  - Test Server (Flask REST API)  │
│  - Rich UI      │                      │  - Web GUI (browser-based)       │
│  - Display      │                      │  - Check Modules                 │
│    results      │                      │  - Direct device access          │
│                 │                      │  - MAVLink to autopilot          │
└─────────────────┘                      │  - ROS nodes                     │
                                         │                                  │
                                         └─────────┬────────────────────────┘
                                                   │ USB/Serial/I2C
                                         ┌─────────┴────────────────────────┐
                                         │  - Autopilot (MAVLink)           │
                                         │  - /dev/deviceA, /dev/deviceB    │
                                         │  - Cameras, IMU, GPS, etc.       │
                                         └──────────────────────────────────┘
```

## Features

### Test Categories

1. **Jetson Checks**: Boot status, resources (CPU/RAM/Disk), temperature
2. **Device Checks**: udev rules, /dev/ devices, permissions, handshake tests
3. **Network Checks**: Interface status, connectivity, ping tests
4. **ROS Checks**: Master, nodes, topics, rates, freshness, rosbag logging
5. **Autopilot Checks**: MAVLink heartbeat, status, parameters, sensors
6. **System Checks**: systemd services, environment variables, time/NTP, scripts, metadata

### User Interfaces

- **Web GUI**: Browser-based dashboard with dark theme, live progress, clickable details
- **CLI Client**: Terminal UI with rich colors, progress bars, and tables
- Color-coded results: passed, failed, warning, skipped
- **Solution hints**: Failed/warning checks show actionable fix suggestions

### Simulation Mode

Run the full application locally without any hardware, sensors, or ROS:

```bash
python server/test_server.py --sim
```

Uses simulated checks with configurable pass/fail/warning rates. Ideal for development, demos, and CI/CD testing.

## Quick Start

### Option 1: Local Development (No Hardware)

```bash
# Install dependencies
pip install flask flask-cors psutil requests rich

# Start server in simulation mode
python server/test_server.py --sim

# Open Web GUI at http://127.0.0.1:5000
# Or use CLI client:
python client/test_client.py --config client/client_config_local.json run
```

Or use the all-in-one launcher:

```bash
python run_local.py          # Start server only
python run_local.py --run    # Start server + run all tests
```

### Option 2: Production (On Real Hardware)

**Server (On Jetson):**

```bash
cd server
pip3 install -r requirements.txt
nano config.json    # Configure devices, IPs, thresholds
python3 test_server.py
```

**Client (On Test PC):**

```bash
cd client
pip install -r requirements.txt
nano client_config.json    # Set Jetson IP
python test_client.py run  # Run all tests
```

**Web GUI:** Open `http://<jetson-ip>:5000` in a browser.

## Documentation

- [Server Setup](README_SERVER.md) - Detailed server installation, configuration reference, and simulation mode
- [Client Usage](README_CLIENT.md) - Client commands, options, and scripting

## Requirements

### Server (Jetson)
- Python 3.7+
- Flask, flask-cors, psutil
- pymavlink (for autopilot checks)
- pyserial (for device handshake checks)
- ROS (optional, checks will skip if not installed)

### Client (Test PC)
- Python 3.7+
- rich, requests

## Project Structure

```
product_test_bit/
├── common/                        # Shared code
│   ├── models.py                  # Data models (TestRun, CheckResult, etc.)
│   └── constants.py               # API endpoints, categories, symbols
├── server/                        # Runs on Jetson
│   ├── test_server.py             # Flask API + CLI (--sim, --config)
│   ├── config.json                # Production configuration
│   ├── config_local.json          # Local/simulation configuration
│   ├── templates/
│   │   └── index.html             # Web GUI (single-page app)
│   ├── checks/                    # Test modules
│   │   ├── base_check.py          # Abstract base class
│   │   ├── jetson_checks.py       # Jetson health checks
│   │   ├── device_checks.py       # USB/serial device checks
│   │   ├── network_checks.py      # Network connectivity checks
│   │   ├── ros_checks.py          # ROS ecosystem checks
│   │   ├── autopilot_checks.py    # MAVLink autopilot checks
│   │   ├── system_checks.py       # OS/service checks
│   │   ├── sim_checks.py          # Simulated checks (--sim mode)
│   │   └── solutions.py           # Solution hints for all checks
│   └── scripts/                   # Optional shell script templates
│       ├── start_system.sh
│       └── log_test.sh
├── client/                        # Runs on Test PC
│   ├── test_client.py             # CLI application
│   ├── client_config.json         # Production client config
│   ├── client_config_local.json   # Local dev client config
│   └── utils/
│       └── api_client.py          # HTTP API client wrapper
├── tests/                         # pytest test suite (152 tests)
├── run_local.py                   # All-in-one local launcher
└── run_tests.py                   # Test runner script
```

## Configuration

All behavior is controlled via JSON config files -- no code changes needed for deployment:

- `server/config.json` - Server-side: device paths, IPs, thresholds, timeouts
- `server/config_local.json` - Local dev: localhost settings + simulation config
- `client/client_config.json` - Client-side: Jetson IP, display options
- `client/client_config_local.json` - Local dev: points to localhost

See [Server Setup](README_SERVER.md#configuration-reference) for full config reference.

## Example Usage

```bash
# Check server status
python test_client.py status

# Run all tests
python test_client.py run

# Run specific category
python test_client.py run autopilot

# View latest results
python test_client.py results

# Run in simulation mode (no hardware)
python server/test_server.py --sim
```

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## License

MIT License

## Author

Built with Claude Code for comprehensive robotics system testing.
