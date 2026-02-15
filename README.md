# Product Test BIT (Built-In Test) Application

A comprehensive test application for robotics/drone systems with a client-server architecture. The test logic runs ON the Jetson device (with direct access to autopilot and peripherals), while the Test PC acts as a client to trigger tests and display results.

## Architecture

```
┌─────────────────┐                      ┌──────────────────────────────────┐
│   Test PC       │  Ethernet/HTTP       │   Jetson (Test Device)           │
│  (Windows/Linux)│◄────────────────────►│   (Linux)                        │
│                 │                      │                                  │
│  - CLI Client   │                      │  - Test Server (Flask REST API)  │
│  - Rich UI      │                      │  - Check Modules                 │
│  - Display      │                      │  - Direct device access          │
│    results      │                      │  - MAVLink to autopilot          │
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

### User Interface

- Terminal/CLI with rich UI (colors, progress bars, tables)
- Real-time progress updates
- Color-coded results (✓ passed, ✗ failed, ⚠ warning, ○ skipped)
- Detailed error messages
- Summary reports

## Quick Start

### Server Setup (On Jetson)

```bash
cd server
pip3 install -r requirements.txt
nano config.json  # Configure as needed
python3 test_server.py
```

### Client Usage (On Test PC)

```bash
cd client
pip install -r requirements.txt
nano client_config.json  # Set Jetson IP
python test_client.py run  # Run all tests
```

## Documentation

- [Server Setup](README_SERVER.md) - Detailed server installation and configuration
- [Client Usage](README_CLIENT.md) - Client commands and options

## Requirements

### Server (Jetson)
- Python 3.7+
- Flask, pymavlink, psutil, pyserial
- ROS (optional, checks will skip if not installed)

### Client (Test PC)
- Python 3.7+
- rich, requests

## Project Structure

```
product_test_bit/
├── common/              # Shared code
│   ├── models.py        # Data models
│   └── constants.py     # Constants
├── server/              # Runs on Jetson
│   ├── test_server.py   # Flask API
│   ├── config.json      # Configuration
│   ├── checks/          # Test modules
│   └── scripts/         # Template scripts
└── client/              # Runs on Test PC
    ├── test_client.py   # CLI application
    └── utils/           # Client utilities
```

## Configuration

All configuration is done via JSON files:
- `server/config.json` - Server-side configuration (IP addresses, devices, thresholds)
- `client/client_config.json` - Client-side configuration (Jetson IP, display options)

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
```

## License

MIT License

## Author

Built with Claude Code for comprehensive robotics system testing.
