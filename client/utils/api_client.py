"""
API Client for communicating with Product Test BIT Server.
"""

import requests
import sys
import os

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
        """
        Initialize API client.

        Args:
            base_url: Base URL of server (e.g., "http://192.168.1.2:5000")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, endpoint):
        """Make GET request"""
        url = self.base_url + endpoint
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint, data=None):
        """Make POST request"""
        url = self.base_url + endpoint
        response = self.session.post(url, json=data, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_status(self):
        """Get server status"""
        return self._get(API_STATUS)

    def get_config(self):
        """Get server configuration"""
        return self._get(API_CONFIG)

    def get_system_info(self):
        """Get system information"""
        return self._get(API_SYSTEM_INFO)

    def run_tests(self, category=None):
        """
        Start test run.

        Args:
            category: Specific category to test (None for all)

        Returns:
            dict with test_id
        """
        endpoint = API_TEST_RUN
        if category:
            endpoint = f"{API_TEST_RUN}/{category}"
        return self._post(endpoint)

    def get_results(self, test_id=None):
        """
        Get test results.

        Args:
            test_id: Specific test ID (None for latest)

        Returns:
            dict with test results
        """
        endpoint = API_TEST_RESULTS
        if test_id:
            endpoint = f"{API_TEST_RESULTS}/{test_id}"
        return self._get(endpoint)

    def export_params(self):
        """Export autopilot parameters"""
        return self._post(API_AUTOPILOT_PARAMS_EXPORT)

    def compare_params(self):
        """Compare autopilot parameters with default"""
        return self._post(API_AUTOPILOT_PARAMS_COMPARE)

    def run_start_script(self):
        """Run start_system.sh script"""
        return self._post(API_SCRIPTS_START)

    def run_log_test_script(self):
        """Run log_test.sh script"""
        return self._post(API_SCRIPTS_LOG_TEST)

    def ping(self):
        """Check if server is reachable"""
        try:
            self.get_status()
            return True
        except Exception:
            return False
