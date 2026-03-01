# Client Usage Guide

The **CLI client** (`client/test_client.py`) runs on your Test PC and communicates with the BIT server over HTTP. It uses Python stdlib only — no external dependencies.

For a browser-based interface, use the **Web GUI** at `http://<jetson-ip>:5500` or the **Launcher** (`launcher.py`).

---

## Installation

No packages to install. The client uses Python stdlib only.

Configure the Jetson IP and port:

```bash
nano client/client_config.json
```

```json
{
  "jetson": {
    "ip": "192.168.1.2",
    "port": 5500,
    "timeout": 60
  }
}
```

For local testing (server running on the same machine):

```bash
python3 client/test_client.py --config client/client_config_local.json run
```

---

## Commands

### `run` — Run tests

```bash
python3 client/test_client.py run              # all categories
python3 client/test_client.py run autopilot    # one category
python3 client/test_client.py run ros
python3 client/test_client.py run network
```

Results stream live to the terminal as each check completes:

```
============================================================
              Product Test BIT Client
============================================================

Connecting to server at http://192.168.1.2:5500... ✓ Connected

Starting test run...
✓ Test started (ID: 20260301_143025)

Status         Category      Check                           Message                                            Duration
──────────────────────────────────────────────────────────────────────────────────────────────────────────────
✓ passed       jetson        JetsonBootCheck                 No boot errors found                                  0.52s
✓ passed       jetson        JetsonResourcesCheck            CPU 12%, RAM 34%, Disk 48GB free                      1.03s
⚠ warning      jetson        JetsonTemperatureCheck          CPU temp 72°C (warning threshold)                     0.31s
✗ failed       autopilot     AutopilotDetectCheck            No MAVROS state on /mavros/state within 10s          10.14s
──────────────────────────────────────────────────────────────────────────────────────────────────────────────

──────────────────── Suggested Solutions ──────────────────────
⚠ JetsonTemperatureCheck - CPU temp 72°C
  How to fix:
    Check cooling fan is running
    Clear ventilation around Jetson

✗ AutopilotDetectCheck - No MAVROS state on /mavros/state within 10s
  How to fix:
    Verify MAVROS is running: rosnode list | grep mavros
    Check autopilot cable and power
────────────────────────────────────────────────────────────────

──────────────────── TEST FAILED ────────────────────
  ✓ Passed:   18/21
  ✗ Failed:    1/21
  ⚠ Warnings:  1/21
  ○ Skipped:   1/21
──────────────────────────────────────────────────────
```

Available categories: `jetson`, `device`, `network`, `ros`, `autopilot`, `system`

---

### `status` — Server status

```bash
python3 client/test_client.py status
```

Shows hostname, OS, CPU, RAM, and disk of the Jetson.

---

### `results` — Latest results

```bash
python3 client/test_client.py results
```

Displays the most recent test run without triggering a new one.

---

### `report` — Download HTML report

```bash
python3 client/test_client.py report
```

Downloads a self-contained HTML report for the latest test run and saves it locally as `bit_report_<test_id>.html`. The report includes the full results table, solutions, source locations (debug mode), and tracebacks.

---

### `export-params` / `compare-params`

```bash
python3 client/test_client.py export-params    # export autopilot params
python3 client/test_client.py compare-params   # compare with defaults
```

---

### Custom config path

```bash
python3 client/test_client.py --config /path/to/my_config.json run
```

---

## Launcher (Web-based entry point)

For a graphical entry point that starts the server on the Jetson via SSH:

```bash
# On your PC (one-time SSH key setup):
ssh-copy-id ubuntu@192.168.1.2

# Start launcher:
python3 launcher.py    # opens http://localhost:8080
```

Click **CONNECT** → the launcher SSHes into the Jetson, starts `test_server.py`, and opens the BIT dashboard automatically.

---

## Testing locally (no Jetson)

Two terminals:

**Terminal 1 — start sim server:**
```bash
python3 run_local.py
# Server running at http://localhost:5500
```

**Terminal 2 — run CLI:**
```bash
python3 client/test_client.py --config client/client_config_local.json run
```

Or just open `http://localhost:5500` in your browser.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All checks passed |
| `1` | One or more checks failed, or connection error |

CI/CD example:
```bash
python3 client/test_client.py run
if [ $? -eq 0 ]; then echo "PASS"; else echo "FAIL"; exit 1; fi
```

---

## Scripting with the API client

```python
import sys, os
sys.path.insert(0, 'path/to/BIT-Demo')
from client.utils.api_client import APIClient
import time

client = APIClient('http://192.168.1.2:5500')

# Start tests
resp    = client.run_tests()          # or run_tests(category='ros')
test_id = resp['test_id']

# Poll until complete
while True:
    results = client.get_results(test_id)
    if results['status'] == 'completed':
        break
    time.sleep(1)

# Check outcome
summary = results['summary']
print(f"Passed: {summary['passed']}/{summary['total']}")

for r in results['results']:
    if r['status'] == 'failed':
        print(f"FAIL: {r['name']} — {r['message']}")
        sol = (r.get('details') or {}).get('solution', '')
        if sol:
            print(f"  Fix: {sol}")

# Download report
report_bytes = client.get_report(test_id)
with open(f"report_{test_id}.html", 'wb') as f:
    f.write(report_bytes)
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Cannot connect to server | Verify server is running on Jetson; check IP in `client_config.json`; ping device |
| Port refused | Default port is **5500** — make sure config matches |
| Slow response | Increase `timeout` in config; some checks (ROS rate measurement) take several seconds |
| Results not updating | Only one test can run at a time; wait for the current run to finish |
