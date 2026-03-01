"""
Tests for server/test_server.py - Flask REST API endpoints.
Uses Flask's test client for local testing.
"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock

import server.test_server as ts
from common.constants import (
    API_STATUS, API_CONFIG, API_TEST_RUN, API_TEST_RESULTS,
    API_SYSTEM_INFO, API_AUTOPILOT_PARAMS_EXPORT, API_AUTOPILOT_PARAMS_COMPARE,
    API_SCRIPTS_START, API_SCRIPTS_LOG_TEST
)


class TestStatusEndpoint:
    def test_get_status(self, client):
        """GET /api/status returns server info"""
        with patch('psutil.boot_time', return_value=time.time() - 3600):
            response = client.get(API_STATUS)

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "online"
        assert data["server"] == "Product Test BIT Server"
        assert data["version"] == "1.0.0"
        assert "platform" in data
        assert "hostname" in data


class TestConfigEndpoint:
    def test_get_config(self, client, sample_config):
        """GET /api/config returns configuration"""
        response = client.get(API_CONFIG)

        assert response.status_code == 200
        data = response.get_json()
        assert "server" in data
        assert "devices" in data
        assert "autopilot" in data

    def test_config_filters_secrets(self, client, sample_config):
        """Config endpoint should not expose secrets"""
        # Add a secret to config
        ts.config["secrets"] = {"api_key": "super_secret"}
        ts.config["passwords"] = {"admin": "pass123"}

        response = client.get(API_CONFIG)
        data = response.get_json()

        assert "secrets" not in data
        assert "passwords" not in data


class TestSystemInfoEndpoint:
    def test_get_system_info(self, client):
        """GET /api/system/info returns system information"""
        mock_vmem = MagicMock()
        mock_vmem.total = 8 * 1024**3
        mock_disk = MagicMock()
        mock_disk.total = 128 * 1024**3

        with patch('psutil.cpu_count', return_value=6), \
             patch('psutil.virtual_memory', return_value=mock_vmem), \
             patch('psutil.disk_usage', return_value=mock_disk), \
             patch('psutil.boot_time', return_value=time.time() - 3600):
            response = client.get(API_SYSTEM_INFO)

        assert response.status_code == 200
        data = response.get_json()
        assert "hostname" in data
        assert data["cpu_count"] == 6
        assert data["total_ram_gb"] == 8.0


class TestTestRunEndpoint:
    def test_start_test_run(self, client):
        """POST /api/test/run starts a test"""
        # Reset state
        ts.test_runs = {}
        ts.current_test_id = None

        response = client.post(API_TEST_RUN)

        assert response.status_code == 202
        data = response.get_json()
        assert "test_id" in data
        assert data["message"] == "Test started"

    def test_start_test_with_category(self, client):
        """POST /api/test/run/jetson runs only jetson checks"""
        ts.test_runs = {}
        ts.current_test_id = None

        response = client.post(f"{API_TEST_RUN}/jetson")

        assert response.status_code == 202
        data = response.get_json()
        assert "test_id" in data

    def test_concurrent_test_blocked(self, client, sample_config):
        """POST /api/test/run returns 409 if test already running"""
        from common.models import TestRun, TestSummary

        # Simulate a running test
        ts.current_test_id = "running_test"
        ts.test_runs["running_test"] = TestRun(
            test_id="running_test",
            status="running",
            started="2026-01-15T10:30:00Z",
            summary=TestSummary()
        )

        response = client.post(API_TEST_RUN)

        assert response.status_code == 409
        data = response.get_json()
        assert "already running" in data["error"]

        # Cleanup
        ts.test_runs = {}
        ts.current_test_id = None


class TestTestResultsEndpoint:
    def test_get_results_no_test(self, client):
        """GET /api/test/results returns 404 when no test exists"""
        ts.test_runs = {}
        ts.current_test_id = None

        response = client.get(API_TEST_RESULTS)

        assert response.status_code == 404

    def test_get_results_by_id(self, client):
        """GET /api/test/results/<id> returns specific test"""
        from common.models import TestRun, TestSummary, CheckResult

        test_run = TestRun(
            test_id="test_123",
            status="completed",
            started="2026-01-15T10:30:00Z",
            completed="2026-01-15T10:31:00Z",
            summary=TestSummary(total=3, passed=2, failed=1),
            results=[
                CheckResult(name="Check1", category="jetson", status="passed", message="OK"),
                CheckResult(name="Check2", category="device", status="passed", message="OK"),
                CheckResult(name="Check3", category="network", status="failed", message="Err"),
            ]
        )
        ts.test_runs["test_123"] = test_run
        ts.current_test_id = "test_123"

        response = client.get(f"{API_TEST_RESULTS}/test_123")

        assert response.status_code == 200
        data = response.get_json()
        assert data["test_id"] == "test_123"
        assert data["status"] == "completed"
        assert data["summary"]["total"] == 3
        assert data["summary"]["passed"] == 2
        assert data["summary"]["failed"] == 1
        assert len(data["results"]) == 3

        # Cleanup
        ts.test_runs = {}
        ts.current_test_id = None

    def test_get_latest_results(self, client):
        """GET /api/test/results returns latest test"""
        from common.models import TestRun, TestSummary

        ts.test_runs["latest"] = TestRun(
            test_id="latest",
            status="completed",
            started="2026-01-15T10:30:00Z",
            summary=TestSummary(total=1, passed=1)
        )
        ts.current_test_id = "latest"

        response = client.get(API_TEST_RESULTS)

        assert response.status_code == 200
        data = response.get_json()
        assert data["test_id"] == "latest"

        # Cleanup
        ts.test_runs = {}
        ts.current_test_id = None

    def test_get_nonexistent_test(self, client):
        """GET /api/test/results/<invalid_id> returns 404"""
        response = client.get(f"{API_TEST_RESULTS}/nonexistent_test")
        assert response.status_code == 404


class TestAutopilotParamsEndpoints:
    def test_export_params(self, client):
        """POST /api/autopilot/params/export returns filename"""
        response = client.post(API_AUTOPILOT_PARAMS_EXPORT)

        assert response.status_code == 200
        data = response.get_json()
        assert "filename" in data

    def test_compare_params(self, client):
        """POST /api/autopilot/params/compare returns result"""
        response = client.post(API_AUTOPILOT_PARAMS_COMPARE)

        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data


class TestScriptEndpoints:
    def test_start_script_not_configured(self, client):
        """POST /api/scripts/start returns 400 when not configured"""
        ts.config = {"scripts": {}}
        response = client.post(API_SCRIPTS_START)
        assert response.status_code == 400

    def test_log_test_not_configured(self, client):
        """POST /api/scripts/log_test returns 400 when not configured"""
        ts.config = {"scripts": {}}
        response = client.post(API_SCRIPTS_LOG_TEST)
        assert response.status_code == 400


class TestRunTestsAsync:
    def test_run_tests_async_completes(self, sample_config):
        """Test that run_tests_async runs checks and stores results"""
        ts.config = sample_config
        ts.test_runs = {}
        ts.current_test_id = None

        # Run with only system checks (they'll fail/skip on Windows but won't crash)
        ts.run_tests_async(categories=['system'], test_id='async_test')

        assert 'async_test' in ts.test_runs
        test_run = ts.test_runs['async_test']
        assert test_run.status == "completed"
        assert test_run.summary.total > 0
        assert len(test_run.results) > 0
        assert test_run.completed is not None

        # Cleanup
        ts.test_runs = {}
        ts.current_test_id = None

    def test_run_all_categories(self, sample_config):
        """Test that all categories can be instantiated and executed"""
        ts.config = sample_config
        ts.test_runs = {}
        ts.current_test_id = None

        ts.run_tests_async(categories=None, test_id='all_test')

        test_run = ts.test_runs['all_test']
        assert test_run.status == "completed"
        # All checks should have a result (even if failed/skipped)
        assert test_run.summary.total > 0
        total = (test_run.summary.passed + test_run.summary.failed +
                 test_run.summary.warnings + test_run.summary.skipped)
        assert total == test_run.summary.total

        # Cleanup
        ts.test_runs = {}
        ts.current_test_id = None
