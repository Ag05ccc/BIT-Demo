# Client Usage Guide

The client runs on the Test PC and provides a terminal UI to interact with the Jetson server. For a browser-based interface, use the [Web GUI](#web-gui-alternative) instead.

## Installation

### 1. Install Dependencies

```bash
cd client
pip install -r requirements.txt
```

### 2. Configure

Edit `client/client_config.json`:

```json
{
  "jetson": {
    "ip": "192.168.1.2",
    "port": 5000,
    "timeout": 60
  },
  "display": {
    "show_details": true,
    "auto_refresh": true,
    "refresh_interval": 1.0
  },
  "export": {
    "results_dir": "test_results",
    "format": "json",
    "include_timestamp": true
  }
}
```

For local development (server running on same machine):

```bash
python test_client.py --config client_config_local.json run
```

## Commands

### Run All Tests

```bash
python test_client.py run
```

This will:
1. Connect to the Jetson server
2. Start all test checks
3. Display live progress with rich UI
4. Show final summary with solution hints for any failures

Example output:

```
============================================================
              Product Test BIT Client
============================================================

Connecting to server at http://192.168.1.2:5000... ✓ Connected

Starting test run...
✓ Test started (ID: 20260215_143052)

┏━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Status ┃ Category   ┃ Check        ┃ Message      ┃ Duration ┃
┡━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ ✓ pass │ jetson     │ JetsonBoot   │ No errors    │   0.52s  │
│ ✓ pass │ jetson     │ Resources    │ Resources OK │   1.03s  │
│ ✗ fail │ autopilot  │ Detect       │ No heartbeat │   10.1s  │
└────────┴────────────┴──────────────┴──────────────┴──────────┘

╭───────────── Suggested Solutions ─────────────╮
│ AutopilotDetectCheck (failed):                │
│   1. Check the autopilot cable connection     │
│   2. Verify power to the autopilot board      │
│   3. Check baud rate in config.json           │
╰───────────────────────────────────────────────╯

╭───────────── TEST FAILED ──────────────╮
│ ✓ Passed:   32/35                      │
│ ✗ Failed:   2/35                       │
│ ⚠ Warnings: 1/35                       │
│ ○ Skipped:  0/35                       │
╰────────────────────────────────────────╯
```

### Run Specific Category

```bash
python test_client.py run autopilot
python test_client.py run ros
python test_client.py run network
```

Available categories:
- `jetson` - Jetson health checks (boot, resources, temperature)
- `device` - Device checks (udev, existence, permissions, handshake)
- `network` - Network checks (interfaces, ping, Test PC connectivity)
- `ros` - ROS checks (master, nodes, topics, rates, freshness, rosbag)
- `autopilot` - Autopilot checks (heartbeat, status, params, sensors)
- `system` - System checks (services, env vars, time, scripts, metadata)

### Check Server Status

```bash
python test_client.py status
```

Shows:
- Server status (online/offline)
- Hostname
- Platform info
- CPU cores
- RAM and disk space

### View Latest Results

```bash
python test_client.py results
```

Displays the most recent test run results with solution hints.

### Export Autopilot Parameters

```bash
python test_client.py export-params
```

Exports current autopilot parameters with timestamp.

### Compare Autopilot Parameters

```bash
python test_client.py compare-params
```

Compares current parameters against default.param file.

### Using a Custom Config

```bash
python test_client.py --config /path/to/my_config.json run
python test_client.py --config client_config_local.json status
```

## Solution Hints

When checks fail or produce warnings, the client automatically displays suggested solutions. These are actionable fix steps specific to each check and status. For example:

- **AutopilotDetectCheck (failed)**: "Check the autopilot cable and power, verify baud rate..."
- **DevicePermissionsCheck (failed)**: "Add user to dialout group, check udev rules..."
- **ROSMasterCheck (failed)**: "Start roscore, check ROS_MASTER_URI..."

## Web GUI Alternative

Instead of the CLI client, you can use the browser-based Web GUI:

1. Start the server: `python3 server/test_server.py`
2. Open `http://<jetson-ip>:5000` in a browser
3. Click "Run All Tests" or select a category
4. View live results, solution hints, and export JSON

The Web GUI provides the same functionality as the CLI client with a visual interface.

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed or error occurred

This allows integration with CI/CD:

```bash
python test_client.py run
if [ $? -eq 0 ]; then
    echo "Tests passed!"
else
    echo "Tests failed!"
    exit 1
fi
```

## Troubleshooting

### Cannot connect to server

Check:
1. Server is running on Jetson (`python3 test_server.py`)
2. Network connection is active (`ping 192.168.1.2`)
3. IP in `client_config.json` is correct
4. Firewall allows port 5000

### Slow response

- Increase `timeout` in `client_config.json`
- Check network latency
- Some checks (e.g., ROS topic rates) take time to measure

### Test results not updating

- Server may be busy with another test (only one test can run at a time)
- Check server logs on Jetson
- Restart server if needed

## Advanced Usage

### Scripting

```python
from utils.api_client import APIClient

client = APIClient("http://192.168.1.2:5000")

# Run tests
response = client.run_tests()
test_id = response['test_id']

# Wait and get results
import time
time.sleep(30)
results = client.get_results(test_id)

# Check status
if results['summary']['failed'] == 0:
    print("All tests passed!")
else:
    # Print failures
    for r in results['results']:
        if r['status'] == 'failed':
            print(f"FAIL: {r['name']} - {r['message']}")
            if 'solution' in r.get('details', {}):
                print(f"  Fix: {r['details']['solution']}")
```

### Custom Reporting

Results are available as JSON via the API, allowing custom reporting tools:

```bash
curl http://192.168.1.2:5000/api/test/results | python -m json.tool
```

## Configuration Options

### Display Options

| Option | Default | Description |
|--------|---------|-------------|
| `show_details` | `true` | Show detailed error messages |
| `auto_refresh` | `true` | Auto-refresh during test run |
| `refresh_interval` | `1.0` | Refresh rate in seconds |

### Export Options

| Option | Default | Description |
|--------|---------|-------------|
| `results_dir` | `"test_results"` | Directory for exported results |
| `format` | `"json"` | Export format |
| `include_timestamp` | `true` | Add timestamp to filenames |
