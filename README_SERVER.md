# Server Setup Guide

The server runs on the Jetson device and provides REST API endpoints for test execution, plus a browser-based Web GUI.

## Installation

### 1. Copy Server Files to Jetson

```bash
# From your development machine
scp -r product_test_bit/server nvidia@192.168.1.2:/home/nvidia/test_server
scp -r product_test_bit/common nvidia@192.168.1.2:/home/nvidia/test_server/
```

### 2. SSH into Jetson

```bash
ssh nvidia@192.168.1.2
cd /home/nvidia/test_server
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip3 install -r server/requirements.txt

# For ROS checks (if using ROS)
# sudo apt-get install ros-noetic-desktop-full
# source /opt/ros/noetic/setup.bash
```

### 4. Configure

Edit `server/config.json` to match your system. This is the **only file** you need to change for deployment -- all device paths, IPs, thresholds, and timeouts are controlled here.

```bash
nano server/config.json
```

See [Configuration Reference](#configuration-reference) below for all available options.

### 5. Make Scripts Executable (Optional)

Shell scripts are **optional** -- they are only needed if you configure them in `config.json` under the `scripts` section. If you don't use them, the related checks will simply skip.

```bash
chmod +x server/scripts/*.sh
```

### 6. Customize Template Scripts (Optional)

Edit the template scripts for your system if you want the server to run startup or logging scripts:

```bash
nano server/scripts/start_system.sh
nano server/scripts/log_test.sh
```

## Running the Server

### Production Mode

```bash
cd /home/nvidia/test_server
python3 server/test_server.py
```

You should see:

```
============================================================
             Product Test BIT Server
============================================================

✓ Configuration loaded from server/config.json

Starting server on 0.0.0.0:5000...
Debug mode: False

Web GUI:  http://192.168.1.2:5000

API endpoints:
  GET  /api/status
  GET  /api/system/info
  POST /api/test/run
  GET  /api/test/results

Server is ready. Press Ctrl+C to stop.
============================================================
```

### Simulation Mode (No Hardware)

```bash
python3 server/test_server.py --sim
```

This uses `config_local.json` and replaces all real checks with simulated versions. No hardware, sensors, or ROS required. Useful for:

- Development and testing
- Demos and presentations
- CI/CD pipelines

### Custom Config File

```bash
python3 server/test_server.py --config /path/to/my_config.json
```

### Auto-Start with systemd (Optional)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/test-server.service
```

Add:

```ini
[Unit]
Description=Product Test BIT Server
After=network.target

[Service]
Type=simple
User=nvidia
WorkingDirectory=/home/nvidia/test_server
ExecStart=/usr/bin/python3 /home/nvidia/test_server/server/test_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable test-server
sudo systemctl start test-server
sudo systemctl status test-server
```

## Web GUI

Open `http://<jetson-ip>:5000` in any browser on the network.

Features:
- Dark theme dashboard with server status indicator
- "Run All Tests" button + per-category buttons
- Live progress bar with colored counters (passed/failed/warnings/skipped)
- Results table with status icons, check names, messages, and durations
- Solution hints shown inline for failed/warning checks
- Click any row to see full details JSON
- Export results as JSON file

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/status` | Server health check |
| `GET`  | `/api/system/info` | System information (hostname, CPU, RAM, disk) |
| `GET`  | `/api/config` | Current configuration (secrets excluded) |
| `POST` | `/api/test/run` | Run all tests |
| `POST` | `/api/test/run/<category>` | Run tests for a specific category |
| `GET`  | `/api/test/results` | Get latest test results |
| `GET`  | `/api/test/results/<test_id>` | Get results for a specific test run |
| `POST` | `/api/autopilot/params/export` | Export autopilot parameters |
| `POST` | `/api/autopilot/params/compare` | Compare parameters with defaults |
| `POST` | `/api/scripts/start` | Run start_system.sh |
| `POST` | `/api/scripts/log_test` | Run log_test.sh |

## Testing the Server

```bash
# From Jetson or another machine on the network
curl http://localhost:5000/api/status
curl http://localhost:5000/api/system/info
curl -X POST http://localhost:5000/api/test/run
sleep 5
curl http://localhost:5000/api/test/results
```

## Solution Hints

Every check has built-in solution hints for `failed`, `warning`, and `skipped` states. When a check fails, the result includes a `solution` field with actionable fix steps. These are displayed in both the CLI client and Web GUI.

Solutions are defined in `server/checks/solutions.py` and auto-attached by `BaseCheck.execute()`.

## Simulation Mode Details

When running with `--sim`, all real checks are replaced with simulated versions:

- Each sim check generates realistic-looking results with configurable outcomes
- Configure in the `sim` section of `config_local.json`:

```json
{
  "sim": {
    "pass_rate": 0.75,
    "warning_rate": 0.15,
    "random_seed": 42,
    "overrides": {
      "MetadataCaptureCheck": "passed",
      "AutopilotParamExportCheck": "warning"
    }
  }
}
```

- `pass_rate`: Probability of a check passing (0.0-1.0)
- `warning_rate`: Probability of a warning (from the remaining non-pass pool)
- `random_seed`: Set for reproducible results, or `null` for random
- `overrides`: Force specific checks to always return a given status

## Troubleshooting

### Port already in use
```bash
# Find process using port 5000
sudo lsof -i :5000
# Kill if necessary
sudo kill -9 <PID>
```

### Permission denied for devices
```bash
# Add user to dialout group for serial devices
sudo usermod -a -G dialout nvidia
# Logout and login again
```

### ROS checks skipped
- Install ROS: `sudo apt-get install ros-noetic-desktop-full`
- Source ROS: Add to `~/.bashrc`: `source /opt/ros/noetic/setup.bash`
- Set environment variables in config.json

### Autopilot checks failing
- Check the serial cable and power to the autopilot
- Verify `autopilot.connection` path in config.json (e.g., `/dev/ttyUSB0`)
- Verify `autopilot.baud_rate` matches the autopilot's configuration
- Try increasing `autopilot.heartbeat_timeout` if connection is slow

## Configuration Reference

All values in `config.json` with their descriptions:

```json
{
  "server": {
    "host": "0.0.0.0",           // Listen address (0.0.0.0 = all interfaces)
    "port": 5000,                // HTTP port
    "debug": false               // Flask debug mode
  },

  "test_pc": {
    "expected_ip": "192.168.1.1" // Test PC IP for connectivity check
  },

  "ping_targets": ["192.168.1.1", "192.168.1.3"],  // IPs to ping

  "environment_vars": {          // Expected environment variables
    "ROS_MASTER_URI": "http://192.168.1.1:11311",
    "ROS_IP": "192.168.1.2",
    "ROS_HOSTNAME": "jetson-test"
  },

  "devices": {                   // Serial/USB devices to check
    "deviceA": {
      "path": "/dev/ttyUSB0",    // Device path
      "description": "Custom sensor A",
      "vendor_id": "0x1234",     // Expected USB vendor ID
      "product_id": "0x5678",    // Expected USB product ID
      "baudrate": 9600,          // Serial baud rate
      "test_command": "AT\r\n",  // Handshake command to send
      "expected_response": "OK", // Expected handshake response
      "serial_timeout": 2,       // Serial read timeout (seconds)
      "read_buffer_size": 200    // Serial read buffer size (bytes)
    }
  },

  "autopilot": {
    "connection": "/dev/ttyAutopilot",  // MAVLink connection string
    "baud_rate": 921600,                // Serial baud rate
    "heartbeat_timeout": 10,            // Heartbeat wait timeout (seconds)
    "message_timeout": 5,               // MAVLink message timeout (seconds)
    "battery_voltage_error": 10.5,      // Battery voltage error threshold (V)
    "battery_voltage_warning": 11.1,    // Battery voltage warning threshold (V)
    "default_params_file": "params/default.param",  // Reference param file
    "param_tolerance": 0.01             // Param comparison tolerance
  },

  "ros": {
    "master_uri": "http://192.168.1.1:11311",  // ROS master URI
    "required_nodes": ["/node1", "/node2"],     // Nodes that must be running
    "required_topics": {                         // Topics that must be publishing
      "/camera/image": {
        "rate_min": 30,                          // Minimum publish rate (Hz)
        "type": "sensor_msgs/Image"
      },
      "/imu/data": {
        "rate_min": 100,
        "type": "sensor_msgs/Imu",
        "value_checks": {                        // Value range checks
          "angular_velocity": {"max": 10.0},
          "linear_acceleration": {"max": 50.0}
        }
      }
    },
    "required_frames": ["base_link", "camera_link"],  // Required TF frames
    "check_timeout": 5.0,                // Rate measurement duration (seconds)
    "topic_freshness_timeout": 5.0       // Max message age (seconds)
  },

  "resources": {
    "cpu_max_percent": 90,         // CPU usage error threshold (%)
    "ram_max_percent": 85,         // RAM usage error threshold (%)
    "disk_min_free_gb": 5,         // Minimum free disk space (GB)
    "temp_max_celsius": 80,        // Temperature error threshold (C)
    "temp_warning_percent": 90     // Warning at this % of temp_max (e.g., 90 = warn at 72C)
  },

  "network": {
    "ping_count": 3,               // Number of ping packets
    "ping_timeout": 3              // Ping timeout per packet (seconds)
  },

  "timeouts": {
    "command": 10,                 // General subprocess command timeout (seconds)
    "script": 60                   // Shell script execution timeout (seconds)
  },

  "systemd_services": ["roscore", "autopilot-bridge"],  // Services to check

  "udev_rules": ["/etc/udev/rules.d/99-autopilot.rules"],  // udev rule files

  "scripts": {
    "startup": "/home/nvidia/scripts/start_system.sh",  // Optional startup script
    "log_test": "/home/nvidia/scripts/log_test.sh"      // Optional log test script
  },

  "logging": {
    "rosbag_dir": "/home/nvidia/rosbags",  // Rosbag directory
    "min_bag_size_mb": 1,                  // Minimum bag size for pass
    "max_bag_age_hours": 24                // Maximum bag age
  },

  "checks": {
    "enabled_categories": ["all"],   // Categories to enable ("all" or list)
    "disabled_checks": [],           // Individual checks to disable
    "timeout_seconds": 30,           // Per-check timeout
    "continue_on_failure": true      // Continue after a check fails
  }
}
```

### Deploying to a New System

1. Copy the project to the target Jetson
2. Edit `server/config.json`:
   - Set correct device paths (`/dev/ttyUSB0`, etc.)
   - Set network IPs (`test_pc.expected_ip`, `ping_targets`)
   - Set autopilot connection and baud rate
   - Set ROS nodes and topics for your system
   - Adjust resource thresholds if needed
   - Configure systemd services to monitor
3. (Optional) Create/edit shell scripts in `server/scripts/`
4. Start the server: `python3 server/test_server.py`

No code changes required.
