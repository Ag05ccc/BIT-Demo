# Product Test BIT (Built-In Test)

A built-in test application for robotics/drone systems using a client-server architecture. Test logic runs **on the Jetson device** (direct access to autopilot, peripherals, ROS). A Test PC triggers tests and displays results via browser or CLI.

## Architecture

```
┌───────────────────┐  Ethernet / HTTP  ┌──────────────────────────────────┐
│   Test PC         │ ◄───────────────► │   Jetson (Test Device)           │
│  (Windows/Linux)  │                   │                                  │
│                   │                   │  test_server.py (Flask REST API) │
│  launcher.py      │  SSH (start)      │  Web GUI  (port 5500)            │
│  ── CONNECT ──►──────────────────────►│  Check Modules                   │
│                   │                   │  Direct hardware access          │
│  Web Browser      │  HTTP (results)   │  ROS / MAVROS topics             │
│  ◄─────────────────────────────────── │                                  │
│                   │                   └──────────┬───────────────────────┘
│  CLI Client       │                              │ USB / Serial / I2C
│  test_client.py   │                   ┌──────────┴───────────────────────┐
└───────────────────┘                   │  Autopilot, Cameras, IMU, GPS…   │
                                        └──────────────────────────────────┘
```

## Features

### Test Categories
1. **Jetson** — Boot status, CPU/RAM/Disk, temperature
2. **Device** — udev rules, `/dev/` devices, permissions, serial handshake
3. **Network** — Interface status, ping, Test PC connectivity
4. **ROS** — Master, nodes, topics, rates, TF frames, rosbag logging
5. **Autopilot** — MAVROS state, battery, GPS, IMU (via rospy)
6. **System** — systemd services, environment variables, NTP, scripts, metadata

### Interfaces
- **Web GUI** — Aerospace dark-theme dashboard, live streaming results, inline solutions, one-click HTML report export
- **CLI Client** — ANSI-colour terminal table, live row streaming, solutions and debug tracebacks
- **Launcher** — SSH-based one-click remote start (`launcher.py`)

### Developer / Debug Mode
Start the server with `--debug` to attach source file:line references to every error and warning, and include full Python tracebacks in API results and the CLI output.

```bash
python3 server/test_server.py --debug
```

### Simulation Mode
Run the full application on any PC — no Jetson, hardware, or ROS required:

```bash
python3 run_local.py          # start sim server, open browser
python3 run_local.py --run    # start + run all tests via CLI
```

---

## Quick Start

### Option 1 — Local simulation (no hardware)

```bash
# Install server dependencies
pip install flask psutil

# Start sim server + open web GUI at http://localhost:5500
python3 run_local.py
```

Or start the server directly:

```bash
python3 server/test_server.py --sim
# Open http://localhost:5500 in your browser
```

### Option 2 — Remote Jetson via Launcher (recommended for real hardware)

**On your PC** (one-time SSH key setup):
```bash
ssh-copy-id ubuntu@192.168.1.2   # copies your public key to Jetson
```

**Start the launcher on your PC:**
```bash
pip install flask
python3 launcher.py              # opens http://localhost:8080 automatically
```

1. Enter the Jetson IP (pre-filled from `client/client_config.json`)
2. Click **CONNECT** — launcher SSHes in and starts `test_server.py`
3. BIT dashboard opens automatically at `http://192.168.1.2:5500`

### Option 3 — Manual SSH + server start

```bash
# Copy project to Jetson (first time only)
scp -r BIT-Demo  ubuntu@192.168.1.2:~/BIT-Demo

# SSH in and start server
ssh ubuntu@192.168.1.2
cd ~/BIT-Demo/server
pip3 install flask psutil pyserial
python3 test_server.py
```

Then open `http://192.168.1.2:5500` in your browser.

### Option 4 — CLI client (Test PC terminal)

```bash
# Run all tests
python3 client/test_client.py run

# Run a single category
python3 client/test_client.py run autopilot

# Check server status
python3 client/test_client.py status

# View latest results
python3 client/test_client.py results

# Download HTML report
python3 client/test_client.py report
```

---

## Requirements

### Server (Jetson / test device)
| Package | Purpose |
|---------|---------|
| `flask>=2.3` | REST API + Web GUI |
| `psutil>=5.9` | System metrics |
| `pyserial>=3.5` | Serial device handshake (optional) |

### Client (Test PC)
No external dependencies — uses Python stdlib only (`urllib`, `json`, `argparse`, …).

### Launcher (Test PC)
| Package | Purpose |
|---------|---------|
| `flask>=2.3` | Launcher web page |

### Development / Tests
```bash
pip install pytest pytest-cov flask psutil
python -m pytest tests/ -v
```

---

## Project Structure

```
BIT-Demo/
├── common/
│   ├── models.py               # TestRun, CheckResult, TestSummary data models
│   └── constants.py            # API endpoints, categories, status symbols
│
├── server/                     # Runs on Jetson
│   ├── test_server.py          # Flask API + HTML report generator (--sim, --debug)
│   ├── config.json             # Production configuration
│   ├── config_local.json       # Local / simulation configuration
│   ├── requirements.txt        # flask, psutil, pyserial
│   ├── templates/
│   │   └── index.html          # Web GUI (aerospace dark theme, single-page app)
│   └── checks/
│       ├── base_check.py       # Abstract base — debug mode, source location
│       ├── jetson_checks.py
│       ├── device_checks.py
│       ├── network_checks.py
│       ├── ros_checks.py
│       ├── autopilot_checks.py # Uses rospy + MAVROS topics
│       ├── system_checks.py
│       ├── sim_checks.py       # Simulated checks for --sim mode
│       └── solutions.py        # Solution hints for all checks
│
├── client/                     # Runs on Test PC
│   ├── test_client.py          # CLI — ANSI colours, streaming rows, report command
│   ├── client_config.json      # Jetson IP / port (production)
│   ├── client_config_local.json# localhost (development)
│   ├── requirements.txt        # (empty — stdlib only)
│   └── utils/
│       └── api_client.py       # HTTP client using urllib (no external deps)
│
├── launcher.py                 # PC-side SSH launcher + browser UI (port 8080)
├── run_local.py                # All-in-one local sim launcher
├── run_tests.py                # pytest runner helper
└── requirements-test.txt       # pytest, pytest-cov, flask, psutil
```

---

## Configuration

All behaviour is controlled by JSON files — no code changes needed for deployment.

| File | Purpose |
|------|---------|
| `server/config.json` | Production: device paths, IPs, thresholds, timeouts |
| `server/config_local.json` | Sim/dev: localhost settings, pass/fail rates |
| `client/client_config.json` | Client: Jetson IP (192.168.1.2), port (5500) |
| `client/client_config_local.json` | Client: localhost (127.0.0.1), port (5500) |

See [Server Setup](README_SERVER.md#configuration-reference) for the full config reference.

---

## Web GUI Highlights

- Aerospace avionics colour palette (dark cockpit, electric-blue accent `#1a8cff`)
- Live result streaming — rows appear as each check completes
- Inline "How to fix" guidance for failed / warning checks
- Click any row for full details side-panel
- **Export JSON** — raw results data
- **Export Report** — self-contained HTML report (aerospace styled, printable)

---

## Documentation

- [Server Setup & Configuration](README_SERVER.md)
- [Client Commands & Scripting](README_CLIENT.md)

---

## License

MIT License
