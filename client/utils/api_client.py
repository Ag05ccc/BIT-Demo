"""
API Client for communicating with Product Test BIT Server.
Uses only Python stdlib (urllib) — no external dependencies.
"""

import json
import sys
import os
import urllib.request
import urllib.error

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.constants import (
    API_STATUS, API_CONFIG, API_TEST_RUN, API_TEST_RESULTS,
    API_SYSTEM_INFO, API_AUTOPILOT_PARAMS_EXPORT, API_AUTOPILOT_PARAMS_COMPARE,
    API_SCRIPTS_START, API_SCRIPTS_LOG_TEST
)


class APIClient:
    """Client for Test BIT Server REST API"""

    def __init__(self, base_url, timeout=60):
        self.base_url = base_url.rstrip('/')
        self.timeout  = timeout

    def _get(self, endpoint):
        """GET request → parsed JSON dict."""
        url = self.base_url + endpoint
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            # Try to parse an error body returned by the server
            try:
                return json.loads(e.read())
            except Exception:
                raise Exception(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e.reason}")

    def _post(self, endpoint, data=None):
        """POST request with JSON body → parsed JSON dict."""
        url  = self.base_url + endpoint
        body = json.dumps(data or {}).encode()
        req  = urllib.request.Request(
            url, data=body,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read())
            except Exception:
                raise Exception(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection error: {e.reason}")

    # ---- Public API methods ----

    def get_status(self):
        return self._get(API_STATUS)

    def get_config(self):
        return self._get(API_CONFIG)

    def get_system_info(self):
        return self._get(API_SYSTEM_INFO)

    def run_tests(self, category=None):
        endpoint = f"{API_TEST_RUN}/{category}" if category else API_TEST_RUN
        return self._post(endpoint)

    def get_results(self, test_id=None):
        endpoint = f"{API_TEST_RESULTS}/{test_id}" if test_id else API_TEST_RESULTS
        return self._get(endpoint)

    def export_params(self):
        return self._post(API_AUTOPILOT_PARAMS_EXPORT)

    def compare_params(self):
        return self._post(API_AUTOPILOT_PARAMS_COMPARE)

    def run_start_script(self):
        return self._post(API_SCRIPTS_START)

    def run_log_test_script(self):
        return self._post(API_SCRIPTS_LOG_TEST)

    def get_report(self, test_id=None):
        """Download the HTML report for a test run. Returns raw bytes."""
        endpoint = '/api/report'
        if test_id:
            endpoint += '/' + test_id
        url = self.base_url + endpoint
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read())
                raise Exception(err.get('error', f'HTTP {e.code}'))
            except (json.JSONDecodeError, KeyError):
                raise Exception(f'HTTP {e.code}: {e.reason}')
        except urllib.error.URLError as e:
            raise Exception(f'Connection error: {e.reason}')

    def ping(self):
        """Return True if the server is reachable."""
        try:
            self.get_status()
            return True
        except Exception:
            return False
