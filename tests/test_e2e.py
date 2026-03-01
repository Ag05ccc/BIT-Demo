"""
End-to-end integration tests.
Tests the full flow: server starts -> client runs tests -> results returned.
All hardware dependencies are mocked.
"""

import pytest
import json
import time
import threading
from unittest.mock import patch, MagicMock

import server.test_server as ts
from common.models import TestRun, TestSummary, CheckResult, CheckStatus
from common.constants import ALL_CATEGORIES, API_STATUS, API_TEST_RUN, API_TEST_RESULTS


class TestFullFlow:
    """Test the complete flow from server to client"""

    def test_server_starts_and_responds(self, client):
        """Server starts and responds to health checks"""
        with patch('psutil.boot_time', return_value=time.time() - 100):
            response = client.get(API_STATUS)

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "online"

    def test_run_and_get_results(self, client, sample_config):
        """Full test: start run -> wait -> get results"""
        # Reset state
        ts.config = sample_config
        ts.test_runs = {}
        ts.current_test_id = None

        # Start a test run
        response = client.post(API_TEST_RUN)
        assert response.status_code == 202
        test_id = response.get_json()["test_id"]

        # Wait for completion (checks run in background thread)
        max_wait = 30  # seconds
        start = time.time()
        while time.time() - start < max_wait:
            response = client.get(f"{API_TEST_RESULTS}/{test_id}")
            if response.status_code == 200:
                data = response.get_json()
                if data.get("status") == "completed":
                    break
            time.sleep(0.5)

        # Verify results
        response = client.get(f"{API_TEST_RESULTS}/{test_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "completed"
        assert data["summary"]["total"] > 0
        assert len(data["results"]) == data["summary"]["total"]

        # Every result should have required fields
        for result in data["results"]:
            assert "name" in result
            assert "category" in result
            assert result["category"] in ALL_CATEGORIES
            assert "status" in result
            assert result["status"] in ["passed", "failed", "warning", "skipped"]
            assert "message" in result
            assert "duration" in result
            assert result["duration"] >= 0

        # Summary should add up
        s = data["summary"]
        assert s["passed"] + s["failed"] + s["warnings"] + s["skipped"] == s["total"]

        # Cleanup
        ts.test_runs = {}
        ts.current_test_id = None

    def test_run_specific_category(self, client, sample_config):
        """Run only system checks and verify results"""
        ts.config = sample_config
        ts.test_runs = {}
        ts.current_test_id = None

        # Run only system category
        response = client.post(f"{API_TEST_RUN}/system")
        assert response.status_code == 202
        test_id = response.get_json()["test_id"]

        # Wait for completion
        max_wait = 30
        start = time.time()
        while time.time() - start < max_wait:
            response = client.get(f"{API_TEST_RESULTS}/{test_id}")
            if response.status_code == 200:
                data = response.get_json()
                if data.get("status") == "completed":
                    break
            time.sleep(0.5)

        data = client.get(f"{API_TEST_RESULTS}/{test_id}").get_json()
        assert data["status"] == "completed"

        # All results should be in "system" category
        for result in data["results"]:
            assert result["category"] == "system"

        # Cleanup
        ts.test_runs = {}
        ts.current_test_id = None


class TestCheckClassRegistry:
    """Test that all check classes are properly registered"""

    def test_all_categories_have_checks(self):
        """Every category has at least one check class"""
        for category in ALL_CATEGORIES:
            assert category in ts.CHECK_CLASSES, f"Missing category: {category}"
            assert len(ts.CHECK_CLASSES[category]) > 0, f"No checks in category: {category}"

    def test_all_checks_instantiate(self, sample_config):
        """All check classes can be instantiated"""
        for category, check_classes in ts.CHECK_CLASSES.items():
            for CheckClass in check_classes:
                check = CheckClass(sample_config)
                assert check.category == category, (
                    f"{CheckClass.__name__} has category '{check.category}' "
                    f"but is registered under '{category}'"
                )

    def test_all_checks_have_run_method(self, sample_config):
        """All check classes have a run() method"""
        for category, check_classes in ts.CHECK_CLASSES.items():
            for CheckClass in check_classes:
                check = CheckClass(sample_config)
                assert hasattr(check, 'run'), f"{CheckClass.__name__} missing run()"
                assert hasattr(check, 'execute'), f"{CheckClass.__name__} missing execute()"

    def test_all_checks_execute_without_crash(self, sample_config):
        """All check classes can execute without crashing (they may fail/skip but shouldn't crash)"""
        for category, check_classes in ts.CHECK_CLASSES.items():
            for CheckClass in check_classes:
                check = CheckClass(sample_config)
                result = check.execute()

                # Should return a valid CheckResult
                assert result.name == CheckClass.__name__
                assert result.category == category
                assert result.status in ["passed", "failed", "warning", "skipped"]
                assert isinstance(result.message, str)
                assert isinstance(result.details, dict)
                assert result.duration >= 0


class TestConfigValidation:
    """Test configuration loading and validation"""

    def test_load_config_valid(self, tmp_path):
        """Config loads successfully from valid JSON"""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"server": {"host": "0.0.0.0", "port": 5000}}))

        with patch('os.path.join', return_value=str(config_file)):
            # Directly test config loading
            with open(str(config_file), 'r') as f:
                config = json.load(f)
            assert config["server"]["host"] == "0.0.0.0"

    def test_config_has_required_sections(self, sample_config):
        """Sample config contains all required sections"""
        required_sections = [
            'server', 'test_pc', 'ping_targets', 'environment_vars',
            'devices', 'autopilot', 'ros', 'resources',
            'systemd_services', 'udev_rules', 'scripts', 'logging', 'checks'
        ]
        for section in required_sections:
            assert section in sample_config, f"Missing config section: {section}"


class TestDataModelSerialization:
    """Test that all API responses serialize correctly"""

    def test_test_run_serializes_for_api(self, sample_config):
        """TestRun objects serialize correctly for JSON API"""
        run = TestRun(
            test_id="ser_test",
            status="completed",
            started="2026-01-15T10:30:00Z",
            completed="2026-01-15T10:31:00Z",
            summary=TestSummary(total=2, passed=1, failed=1),
            results=[
                CheckResult(
                    name="Check1",
                    category="jetson",
                    status="passed",
                    message="OK",
                    details={"key": "value"},
                    duration=0.5,
                    timestamp="2026-01-15T10:30:05Z"
                ),
                CheckResult(
                    name="Check2",
                    category="device",
                    status="failed",
                    message="Error",
                    details={"error": "device not found"},
                    duration=1.2,
                    timestamp="2026-01-15T10:30:10Z"
                ),
            ]
        )

        # Should serialize to JSON without errors
        d = run.to_dict()
        json_str = json.dumps(d)
        assert len(json_str) > 0

        # Should deserialize back
        parsed = json.loads(json_str)
        restored = TestRun.from_dict(parsed)
        assert restored.test_id == "ser_test"
        assert len(restored.results) == 2

    def test_check_result_details_serializable(self):
        """CheckResult details field must be JSON-serializable"""
        result = CheckResult(
            name="Test",
            category="test",
            status="passed",
            message="OK",
            details={
                "string_val": "hello",
                "int_val": 42,
                "float_val": 3.14,
                "bool_val": True,
                "none_val": None,
                "list_val": [1, 2, 3],
                "nested": {"a": {"b": "c"}}
            }
        )
        # Should not raise
        json_str = json.dumps(result.to_dict())
        parsed = json.loads(json_str)
        assert parsed["details"]["nested"]["a"]["b"] == "c"
