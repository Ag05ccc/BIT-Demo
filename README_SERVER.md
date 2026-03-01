# Server Setup Guide

The server (`test_server.py`) runs on the Jetson (or any Linux test device). It provides a Flask REST API and serves the browser-based Web GUI.

---

## Installation

### 1. Copy project to the Jetson

```bash
# From your PC:
scp -r BIT-Demo  ubuntu@192.168.1.2:~/BIT-Demo

# Faster on subsequent updates:
rsync -av BIT-Demo/  ubuntu@192.168.1.2:~/BIT-Demo/
```

### 2. SSH in and install dependencies

```bash
ssh ubuntu@192.168.1.2
cd ~/BIT-Demo/server
pip3 install flask psutil pyserial
```

### 3. Edit config

```bash
nano server/config.json   # set device paths, IPs, thresholds
```

See [Configuration Reference](#configuration-reference) below.

---

## Starting the Server

### Production (real hardware)

```bash
cd ~/BIT-Demo/server
python3 test_server.py
```

Expected output:
```
============================================================
             Product Test BIT Server
============================================================

✓ Configuration loaded from config.json

Starting server on 0.0.0.0:5500...
Web GUI:  http://127.0.0.1:5500

API endpoints:
  GET  /api/status
  GET  /api/system/info
  POST /api/test/run
  GET  /api/test/results

Server is ready. Press Ctrl+C to stop.
============================================================
```

Open `http://<jetson-ip>:5500` in any browser.

### Simulation mode (no hardware)

```bash
python3 test_server.py --sim
```

Uses `config_local.json` and replaces all real checks with simulated versions. No hardware, sensors, or ROS required. Good for development, demos, and CI/CD.

### Developer / debug mode

```bash
python3 test_server.py --debug          # production + debug
python3 test_server.py --sim --debug    # sim + debug
```

Debug mode attaches the **source file and line number** of every error or warning to the check result, and includes full Python tracebacks in the API response. Both the Web GUI and CLI client display this extra information automatically.

### Custom config file

```bash
python3 test_server.py --config /path/to/my_config.json
```

### Keep running after SSH disconnect

```bash
# Option A — nohup (simple)
nohup python3 test_server.py > server.log 2>&1 &

# Option B — screen (re-attachable)
screen -S bit
python3 test_server.py
# Detach: Ctrl+A, D   |   Re-attach: screen -r bit
```

### Auto-start with systemd (optional)

```bash
sudo nano /etc/systemd/system/bit-server.service
```

```ini
[Unit]
Description=Product Test BIT Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/BIT-Demo/server
ExecStart=/usr/bin/python3 /home/ubuntu/BIT-Demo/server/test_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable bit-server
sudo systemctl start  bit-server
sudo systemctl status bit-server
```

---

## Web GUI

Open `http://<jetson-ip>:5500` in any browser on the same network.

### Features
- **Aerospace avionics theme** — dark cockpit background, electric-blue accent
- **Server status indicator** — live dot in header (green = online)
- **System info bar** — hostname, OS, CPU, RAM, disk
- **RUN ALL TESTS** button + per-category buttons (Jetson, Device, Network, ROS, Autopilot, System)
- **Live streaming** — result rows appear as each check completes
- **Progress bar** — colour-segmented (green / amber / red)
- **Inline solutions** — "How to fix" guidance shown below failed/warning rows
- **Details panel** — click any row for full information (message, solution, source location, traceback)
- **Export JSON** — downloads raw results as `.json`
- **Export Report** — downloads a self-contained, printable HTML report with full results, solutions, and (if debug mode) tracebacks

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/status` | Server health + version |
| `GET`  | `/api/system/info` | Hostname, OS, CPU, RAM, disk |
| `GET`  | `/api/config` | Current config (secrets excluded) |
| `POST` | `/api/test/run` | Start all tests (async) |
| `POST` | `/api/test/run/<category>` | Start one category |
| `GET`  | `/api/test/results` | Latest test results |
| `GET`  | `/api/test/results/<test_id>` | Results for a specific run |
| `GET`  | `/api/report` | Download HTML report (latest run) |
| `GET`  | `/api/report/<test_id>` | Download HTML report (specific run) |
| `POST` | `/api/autopilot/params/export` | Export autopilot parameters |
| `POST` | `/api/autopilot/params/compare` | Compare params with defaults |
| `POST` | `/api/scripts/start` | Run `start_system.sh` |
| `POST` | `/api/scripts/log_test` | Run `log_test.sh` |

### Quick curl tests

```bash
curl http://localhost:5500/api/status
curl http://localhost:5500/api/system/info
curl -X POST http://localhost:5500/api/test/run
sleep 10
curl http://localhost:5500/api/test/results
```

---

## Autopilot Checks (MAVROS / rospy)

Autopilot checks connect via **MAVROS ROS topics** using `rospy`. No direct MAVLink or serial connection is needed from Python.

| Check | Topic | Type |
|-------|-------|------|
| AutopilotDetect | `<ns>/state` | `mavros_msgs/State` |
| AutopilotStatus | `<ns>/battery` | `sensor_msgs/BatteryState` |
| AutopilotSensors | `<ns>/global_position/raw/fix`, `<ns>/imu/data` | `NavSatFix`, `Imu` |

Configure the MAVROS namespace in `config.json`:
```json
"autopilot": {
  "mavros_ns": "/mavros",
  "heartbeat_timeout": 10,
  "battery_voltage_error": 10.5,
  "battery_voltage_warning": 11.1
}
```

If `rospy` is not installed, all autopilot checks are automatically skipped (no crash).

---

## Simulation Mode Details

When `--sim` is used, all real checks are replaced by `sim_checks.py`:

```json
"sim": {
  "pass_rate": 0.75,
  "warning_rate": 0.15,
  "random_seed": 42,
  "overrides": {
    "MetadataCaptureCheck": "passed",
    "AutopilotParamExportCheck": "warning"
  }
}
```

| Key | Description |
|-----|-------------|
| `pass_rate` | Probability a check passes (0.0–1.0) |
| `warning_rate` | Probability of warning from the non-pass pool |
| `random_seed` | Set for reproducible results; `null` for random |
| `overrides` | Force specific checks to a fixed status |

---

## Troubleshooting

### Port already in use
```bash
sudo lsof -i :5500
sudo kill -9 <PID>
```

### Permission denied for serial devices
```bash
sudo usermod -a -G dialout ubuntu
# Log out and back in
```

### ROS checks skipped
- Install ROS and source it: `source /opt/ros/noetic/setup.bash`
- Ensure `ROS_MASTER_URI` is set correctly in `config.json`

### Autopilot checks failing
- Verify MAVROS is running: `rosnode list | grep mavros`
- Check the `mavros_ns` setting matches your MAVROS namespace
- Increase `heartbeat_timeout` if connection is slow

---

## Configuration Reference

```json
{
  "server": {
    "host": "0.0.0.0",          // Listen on all interfaces
    "port": 5500,               // HTTP port
    "debug": false              // Flask debug mode
  },

  "test_pc": {
    "expected_ip": "192.168.1.1"  // Test PC IP (for connectivity check)
  },

  "ping_targets": ["192.168.1.1", "192.168.1.3"],

  "environment_vars": {
    "ROS_MASTER_URI": "http://192.168.1.1:11311",
    "ROS_IP": "192.168.1.2",
    "ROS_HOSTNAME": "jetson-test"
  },

  "devices": {
    "deviceA": {
      "path": "/dev/ttyUSB0",
      "description": "Custom sensor A",
      "vendor_id": "0x1234",
      "product_id": "0x5678",
      "baudrate": 9600,
      "test_command": "AT\r\n",
      "expected_response": "OK"
    }
  },

  "autopilot": {
    "mavros_ns": "/mavros",         // MAVROS ROS namespace
    "heartbeat_timeout": 10,        // Seconds to wait for MAVROS state
    "battery_voltage_error": 10.5,  // Voltage below this → failed
    "battery_voltage_warning": 11.1 // Voltage below this → warning
  },

  "ros": {
    "master_uri": "http://192.168.1.1:11311",
    "required_nodes": ["/node1", "/node2"],
    "required_topics": {
      "/camera/image": { "rate_min": 30, "type": "sensor_msgs/Image" },
      "/imu/data":     { "rate_min": 100, "type": "sensor_msgs/Imu" }
    },
    "required_frames": ["base_link", "camera_link"],
    "check_timeout": 5.0,
    "topic_freshness_timeout": 5.0
  },

  "resources": {
    "cpu_max_percent": 90,
    "ram_max_percent": 85,
    "disk_min_free_gb": 5,
    "temp_max_celsius": 80,
    "temp_warning_percent": 90
  },

  "network": {
    "ping_count": 3,
    "ping_timeout": 3
  },

  "timeouts": {
    "command": 10,
    "script": 60
  },

  "systemd_services": ["roscore", "autopilot-bridge", "camera-driver"],
  "udev_rules": ["/etc/udev/rules.d/99-autopilot.rules"],

  "scripts": {
    "startup":  "/home/ubuntu/scripts/start_system.sh",
    "log_test": "/home/ubuntu/scripts/log_test.sh"
  },

  "logging": {
    "rosbag_dir": "/home/ubuntu/rosbags",
    "min_bag_size_mb": 1,
    "max_bag_age_hours": 24
  },

  "checks": {
    "enabled_categories": ["all"],
    "disabled_checks": [],
    "timeout_seconds": 30,
    "continue_on_failure": true
  },

  "developer": {
    "debug": false    // Set true (or use --debug flag) for source locations + tracebacks
  }
}
```
