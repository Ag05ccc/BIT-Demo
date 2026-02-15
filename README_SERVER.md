# Server Setup Guide

The server runs on the Jetson device and provides REST API endpoints for test execution.

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

Edit `server/config.json` to match your system:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 5000
  },
  "devices": {
    "deviceA": {
      "path": "/dev/ttyUSB0",
      "vendor_id": "0x1234",
      ...
    }
  },
  "autopilot": {
    "connection": "/dev/ttyAutopilot",
    "baud_rate": 921600
  },
  ...
}
```

### 5. Make Scripts Executable

```bash
chmod +x server/scripts/*.sh
```

### 6. Customize Template Scripts

Edit `server/scripts/start_system.sh` and `server/scripts/log_test.sh` for your system:

```bash
nano server/scripts/start_system.sh
nano server/scripts/log_test.sh
```

## Running the Server

### Manual Start

```bash
cd /home/nvidia/test_server/server
python3 test_server.py
```

You should see:

```
============================================================
            Product Test BIT Server
============================================================

✓ Configuration loaded from /home/nvidia/test_server/server/config.json

Starting server on 0.0.0.0:5000...
Debug mode: False

Available endpoints:
  GET  /api/status
  GET  /api/system/info
  POST /api/test/run
  GET  /api/test/results

Server is ready. Press Ctrl+C to stop.
============================================================
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
WorkingDirectory=/home/nvidia/test_server/server
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

## API Endpoints

- `GET /api/status` - Server health check
- `GET /api/system/info` - System information
- `GET /api/config` - Current configuration
- `POST /api/test/run` - Run all tests
- `POST /api/test/run/<category>` - Run specific category
- `GET /api/test/results` - Get latest results
- `GET /api/test/results/<test_id>` - Get specific test run
- `POST /api/autopilot/params/export` - Export autopilot parameters
- `POST /api/autopilot/params/compare` - Compare parameters
- `POST /api/scripts/start` - Run start_system.sh
- `POST /api/scripts/log_test` - Run log_test.sh

## Testing the Server

```bash
# From Jetson or another machine on the network
curl http://localhost:5000/api/status
curl http://localhost:5000/api/system/info
curl -X POST http://localhost:5000/api/test/run
curl http://localhost:5000/api/test/results
```

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

## Configuration Reference

See `server/config.json` for full configuration options:
- Server settings (host, port, debug)
- Device paths and hardware IDs
- Autopilot connection settings
- ROS nodes and topics
- Resource thresholds
- systemd services to check
- Script paths
