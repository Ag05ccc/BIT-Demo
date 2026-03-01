#!/usr/bin/env python3
"""
BIT Launcher — runs on Test PC.

Opens a browser control page.  Click CONNECT to SSH into the Jetson,
start test_server.py there, then the BIT dashboard opens automatically.

Usage:
    python3 launcher.py               # then open http://localhost:8080
    python3 launcher.py --port 9090   # use a different launcher port
"""

import sys
import os
import json
import subprocess
import time
import urllib.request
import urllib.error
from flask import Flask, jsonify, request, Response

app = Flask(__name__)


# ── Defaults from client config ───────────────────────────────────────────────

def _load_defaults():
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'client', 'client_config.json')
    try:
        with open(cfg_path) as fh:
            cfg = json.load(fh)
        jetson = cfg.get('jetson', {})
        return jetson.get('ip', '192.168.1.2'), int(jetson.get('port', 5500))
    except Exception:
        return '192.168.1.2', 5500

DEFAULT_IP, DEFAULT_PORT = _load_defaults()


# ── CORS (needed when browser fetches from the launcher) ─────────────────────

@app.after_request
def _cors(resp):
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return resp


# ── SSH + probe helpers ───────────────────────────────────────────────────────

def _ssh_start_server(ip, user, key_path, remote_path):
    """
    SSH into the device and launch test_server.py in the background.
    Kills any previous instance first so re-launching always works.
    Requires key-based SSH auth (no password prompts).
    """
    cmd = [
        'ssh',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'ConnectTimeout=10',
        '-o', 'BatchMode=yes',       # fail immediately if key auth isn't set up
    ]
    if key_path:
        cmd += ['-i', os.path.expanduser(key_path)]

    # Kill any running instance, then start a fresh one
    remote_cmd = (
        'pkill -f "python3 test_server.py" 2>/dev/null || true; '
        'sleep 0.5; '
        'cd ' + remote_path + '/server && '
        'nohup python3 test_server.py > /tmp/bit_server.log 2>&1 & '
        'echo __BIT_STARTED__'
    )
    cmd += [user + '@' + ip, remote_cmd]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        raise RuntimeError('SSH connection timed out (20 s). '
                           'Check the IP address and that the device is reachable.')

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        if not err:
            err = 'SSH exited with code ' + str(result.returncode)
        raise RuntimeError(err)

    if '__BIT_STARTED__' not in result.stdout:
        raise RuntimeError(
            'SSH succeeded but the start command did not confirm. '
            'Check that the remote path is correct and Python 3 is available.'
        )


def _probe_server(ip, port, retries=25, delay=1.2):
    """Poll /api/status until BIT server responds or we give up (~30 s)."""
    url = 'http://' + ip + ':' + str(port) + '/api/status'
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(delay)
    return False


# ── Launcher HTML (inline — no template file needed) ─────────────────────────

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BIT Launcher</title>
<style>
:root {
  --bg:     #0c0f14;
  --bg2:    #131821;
  --bg3:    #1a2232;
  --text:   #c8d8e8;
  --text2:  #4e6070;
  --green:  #00c853;
  --red:    #ff3d3d;
  --yellow: #ff9500;
  --border: #1e2d40;
  --accent: #1a8cff;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-top: 2px solid var(--accent);
  border-radius: 12px;
  padding: 40px;
  max-width: 500px;
  width: 100%;
  box-shadow: 0 8px 40px rgba(0,0,0,.5);
}
.logo {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 4px;
}
.logo span { color: var(--accent); }
.subtitle {
  font-size: 12px;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 32px;
}
.form-group { margin-bottom: 16px; }
.form-group label {
  display: block;
  font-size: 11px;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}
.form-group input {
  width: 100%;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 12px;
  color: var(--text);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}
.form-group input:focus { border-color: var(--accent); }
.form-group input:disabled { opacity: 0.5; }
.row2 { display: grid; grid-template-columns: 1fr 100px; gap: 12px; }
.btn-connect {
  width: 100%;
  margin-top: 8px;
  padding: 14px;
  background: var(--accent);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  cursor: pointer;
  transition: filter 0.2s, transform 0.1s;
}
.btn-connect:hover:not(:disabled) { filter: brightness(1.15); transform: translateY(-1px); }
.btn-connect:active { transform: translateY(0); }
.btn-connect:disabled { opacity: 0.45; cursor: not-allowed; }

/* Status area */
.status-area {
  margin-top: 24px;
  padding: 16px;
  background: var(--bg3);
  border-radius: 8px;
  display: none;
}
.status-area.visible { display: block; }
.status-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}
.indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #555;
  flex-shrink: 0;
  transition: background 0.3s;
}
.indicator.spinning {
  background: var(--accent);
  animation: pulse 1s ease-in-out infinite;
}
.indicator.ok  { background: var(--green); box-shadow: 0 0 8px var(--green); }
.indicator.err { background: var(--red);   box-shadow: 0 0 8px var(--red);   }
.indicator.warn{ background: var(--yellow);box-shadow: 0 0 8px var(--yellow);}
@keyframes pulse { 0%,100%{ opacity:1 } 50%{ opacity:0.35 } }

.log-lines {
  margin-top: 10px;
  font-size: 11px;
  color: var(--text2);
  font-family: monospace;
  line-height: 1.8;
}

/* Dashboard button */
.btn-dashboard {
  display: none;
  width: 100%;
  margin-top: 16px;
  padding: 14px;
  background: var(--green);
  color: #0c0f14;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  cursor: pointer;
  text-decoration: none;
  text-align: center;
  transition: filter 0.2s;
}
.btn-dashboard.visible { display: block; }
.btn-dashboard:hover { filter: brightness(1.1); }

.hint {
  margin-top: 20px;
  font-size: 11px;
  color: var(--text2);
  text-align: center;
  line-height: 1.7;
}
.hint code { color: var(--accent); font-family: monospace; }
</style>
</head>
<body>
<div class="card">
  <div class="logo"><span>Product Test</span> BIT</div>
  <div class="subtitle">Launcher &mdash; connect to test device via SSH</div>

  <div class="form-group">
    <label>Device IP Address</label>
    <input id="ip" type="text" value="__DEFAULT_IP__" placeholder="192.168.1.2">
  </div>
  <div class="form-group">
    <label>SSH Username</label>
    <input id="user" type="text" value="ubuntu" placeholder="ubuntu">
  </div>
  <div class="form-group">
    <label>SSH Private Key Path
      <span style="text-transform:none;letter-spacing:0;font-size:10px;margin-left:6px">
        (leave blank to use default key)
      </span>
    </label>
    <input id="key" type="text" value="" placeholder="~/.ssh/id_rsa">
  </div>
  <div class="row2">
    <div class="form-group" style="margin:0">
      <label>Remote Project Path</label>
      <input id="path" type="text" value="~/BIT-Demo" placeholder="~/BIT-Demo">
    </div>
    <div class="form-group" style="margin:0">
      <label>Server Port</label>
      <input id="port" type="text" value="__DEFAULT_PORT__" placeholder="5500">
    </div>
  </div>

  <button class="btn-connect" id="btnConnect" onclick="doConnect()"
          title="SSH into device and start BIT server">
    &#9654; CONNECT
  </button>

  <!-- Status / progress area -->
  <div class="status-area" id="statusArea">
    <div class="status-row">
      <div class="indicator" id="indicator"></div>
      <span id="statusText">—</span>
    </div>
    <div class="log-lines" id="logLines"></div>
  </div>

  <!-- Opens after successful connection -->
  <a class="btn-dashboard" id="btnDash" href="#" target="_blank">
    &#9654; OPEN BIT DASHBOARD
  </a>

  <div class="hint">
    Requires SSH key-based authentication on the device.<br>
    One-time setup: <code>ssh-copy-id user@device-ip</code>
  </div>
</div>

<script>
function setForm(disabled) {
  ['ip','user','key','path','port'].forEach(id => {
    document.getElementById(id).disabled = disabled;
  });
  document.getElementById('btnConnect').disabled = disabled;
}

function showStatus(state, text) {
  // state: 'spinning' | 'ok' | 'err' | 'warn'
  document.getElementById('statusArea').className = 'status-area visible';
  document.getElementById('indicator').className  = 'indicator ' + state;
  document.getElementById('statusText').textContent = text;
}

function addLog(line) {
  const el = document.getElementById('logLines');
  el.textContent += (el.textContent ? '\\n' : '') + line;
}

async function doConnect() {
  const ip   = document.getElementById('ip').value.trim();
  const user = document.getElementById('user').value.trim();
  const key  = document.getElementById('key').value.trim();
  const path = document.getElementById('path').value.trim();
  const port = parseInt(document.getElementById('port').value.trim()) || __DEFAULT_PORT__;

  if (!ip || !user) { alert('IP address and username are required.'); return; }

  setForm(true);
  document.getElementById('logLines').textContent = '';
  document.getElementById('btnDash').className = 'btn-dashboard';
  showStatus('spinning', 'Connecting via SSH\u2026');
  addLog('\u25b6 Opening SSH connection to ' + user + '@' + ip);

  try {
    const res = await fetch('/api/connect', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ ip, user, key_path: key, remote_path: path, port })
    });
    const data = await res.json();

    if (data.success) {
      showStatus('ok', '\u2713 BIT server running on ' + ip + ':' + port);
      addLog('\u2713 Server confirmed reachable');
      const dash = document.getElementById('btnDash');
      dash.href = data.url;
      dash.className = 'btn-dashboard visible';
      // Auto-open dashboard
      addLog('\u25b6 Opening dashboard\u2026');
      setTimeout(() => window.open(data.url, '_blank'), 600);
    } else {
      showStatus('err', '\u2717 ' + (data.error || 'Connection failed'));
      addLog('Tip: run ssh-copy-id ' + user + '@' + ip + ' to set up key auth');
      setForm(false);
    }
  } catch (e) {
    showStatus('err', '\u2717 Request error: ' + e.message);
    setForm(false);
  }
}

// On load: check if BIT server is already reachable — skip CONNECT if so
window.addEventListener('load', async () => {
  const ip   = document.getElementById('ip').value;
  const port = parseInt(document.getElementById('port').value) || __DEFAULT_PORT__;
  try {
    const res  = await fetch('/api/probe?ip=' + encodeURIComponent(ip)
                                 + '&port=' + encodeURIComponent(port));
    const data = await res.json();
    if (data.reachable) {
      showStatus('ok', '\u2713 BIT server already running on ' + ip + ':' + port);
      addLog('Server was already up \u2014 no SSH needed');
      const dash = document.getElementById('btnDash');
      dash.href = data.url;
      dash.className = 'btn-dashboard visible';
    }
  } catch (e) { /* server not reachable yet — normal */ }
});
</script>
</body>
</html>
"""


# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    html = (_HTML_TEMPLATE
            .replace('__DEFAULT_IP__',   DEFAULT_IP)
            .replace('__DEFAULT_PORT__', str(DEFAULT_PORT)))
    return Response(html, mimetype='text/html')


@app.route('/api/connect', methods=['POST'])
def connect():
    """SSH into device, start BIT server, wait until it is reachable."""
    data        = request.get_json() or {}
    ip          = data.get('ip',          DEFAULT_IP)
    user        = data.get('user',        'ubuntu')
    key_path    = data.get('key_path',    '')
    remote_path = data.get('remote_path', '~/BIT-Demo')
    port        = int(data.get('port',    DEFAULT_PORT))

    # 1 — SSH and start the server
    try:
        _ssh_start_server(ip, user, key_path, remote_path)
    except RuntimeError as exc:
        return jsonify({'success': False, 'error': str(exc)})

    # 2 — Wait until the BIT server answers HTTP
    if not _probe_server(ip, port):
        return jsonify({
            'success': False,
            'error':   ('BIT server started on the device but did not respond '
                        'within 30 s. Check /tmp/bit_server.log on the device.')
        })

    dashboard_url = 'http://' + ip + ':' + str(port)
    return jsonify({'success': True, 'url': dashboard_url})


@app.route('/api/probe', methods=['GET'])
def probe():
    """Quick check: is the BIT server already reachable at ip:port?"""
    ip   = request.args.get('ip',   DEFAULT_IP)
    port = int(request.args.get('port', DEFAULT_PORT))
    up   = _probe_server(ip, port, retries=1, delay=0)
    return jsonify({'reachable': up,
                    'url':       'http://' + ip + ':' + str(port)})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    import webbrowser

    parser = argparse.ArgumentParser(description='BIT Launcher')
    parser.add_argument('--port', type=int, default=8080,
                        help='Port for this launcher page (default: 8080)')
    args = parser.parse_args()

    launcher_url = 'http://localhost:' + str(args.port)

    print('=' * 55)
    print(' Product Test BIT — Launcher'.center(55))
    print('=' * 55)
    print()
    print('  Open this URL in your browser:')
    print('  ' + launcher_url)
    print()
    print('  Default Jetson target: ' + DEFAULT_IP + ':' + str(DEFAULT_PORT))
    print()
    print('  Click CONNECT to SSH into the device and start the')
    print('  BIT server. The dashboard will open automatically.')
    print()
    print('  Press Ctrl+C to stop the launcher.')
    print('=' * 55)
    print()

    # Auto-open browser after a short delay
    def _open_browser():
        time.sleep(1.2)
        webbrowser.open(launcher_url)

    import threading
    threading.Thread(target=_open_browser, daemon=True).start()

    app.run(host='0.0.0.0', port=args.port, debug=False)
