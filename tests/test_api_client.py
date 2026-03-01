"""
Tests for client/utils/api_client.py - REST API client wrapper.
Uses mocked HTTP responses for local testing.
"""

import pytest
from unittest.mock import patch, MagicMock
from client.utils.api_client import APIClient
from common.constants import (
    API_STATUS, API_CONFIG, API_TEST_RUN, API_TEST_RESULTS,
    API_SYSTEM_INFO, API_AUTOPILOT_PARAMS_EXPORT, API_AUTOPILOT_PARAMS_COMPARE,
    API_SCRIPTS_START, API_SCRIPTS_LOG_TEST
)


@pytest.fixture
def api_client():
    """Create an API client for testing"""
    return APIClient("http://192.168.1.2:5000", timeout=10)


class TestAPIClientInit:
    def test_init(self):
        client = APIClient("http://192.168.1.2:5000")
        assert client.base_url == "http://192.168.1.2:5000"
        assert client.timeout == 60  # default

    def test_init_with_timeout(self):
        client = APIClient("http://10.0.0.1:5000", timeout=30)
        assert client.timeout == 30

    def test_strips_trailing_slash(self):
        client = APIClient("http://192.168.1.2:5000/")
        assert client.base_url == "http://192.168.1.2:5000"


class TestAPIClientGetStatus:
    def test_get_status(self, api_client):
        """Test getting server status"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "online",
            "server": "Product Test BIT Server",
            "version": "1.0.0"
        }
        mock_response.status_code = 200

        with patch.object(api_client.session, 'get', return_value=mock_response) as mock_get:
            result = api_client.get_status()

        mock_get.assert_called_once_with(
            f"http://192.168.1.2:5000{API_STATUS}",
            timeout=10
        )
        assert result["status"] == "online"


class TestAPIClientGetSystemInfo:
    def test_get_system_info(self, api_client):
        """Test getting system info"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hostname": "jetson-test",
            "cpu_count": 6,
            "total_ram_gb": 8.0
        }

        with patch.object(api_client.session, 'get', return_value=mock_response):
            result = api_client.get_system_info()

        assert result["hostname"] == "jetson-test"
        assert result["cpu_count"] == 6


class TestAPIClientRunTests:
    def test_run_all_tests(self, api_client):
        """Test starting all tests"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": "Test started",
            "test_id": "20260115_143000"
        }

        with patch.object(api_client.session, 'post', return_value=mock_response) as mock_post:
            result = api_client.run_tests()

        mock_post.assert_called_once_with(
            f"http://192.168.1.2:5000{API_TEST_RUN}",
            json=None,
            timeout=10
        )
        assert result["test_id"] == "20260115_143000"

    def test_run_specific_category(self, api_client):
        """Test running specific category"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": "Test started",
            "test_id": "20260115_143000"
        }

        with patch.object(api_client.session, 'post', return_value=mock_response) as mock_post:
            result = api_client.run_tests(category="autopilot")

        mock_post.assert_called_once_with(
            f"http://192.168.1.2:5000{API_TEST_RUN}/autopilot",
            json=None,
            timeout=10
        )


class TestAPIClientGetResults:
    def test_get_latest_results(self, api_client):
        """Test getting latest results"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "test_id": "latest",
            "status": "completed",
            "summary": {"total": 10, "passed": 8, "failed": 2}
        }

        with patch.object(api_client.session, 'get', return_value=mock_response):
            result = api_client.get_results()

        assert result["test_id"] == "latest"

    def test_get_specific_results(self, api_client):
        """Test getting results by ID"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "test_id": "test_abc",
            "status": "completed"
        }

        with patch.object(api_client.session, 'get', return_value=mock_response) as mock_get:
            result = api_client.get_results("test_abc")

        mock_get.assert_called_once_with(
            f"http://192.168.1.2:5000{API_TEST_RESULTS}/test_abc",
            timeout=10
        )


class TestAPIClientAutopilot:
    def test_export_params(self, api_client):
        """Test exporting autopilot params"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"filename": "current_device_20260115.params"}

        with patch.object(api_client.session, 'post', return_value=mock_response):
            result = api_client.export_params()

        assert "filename" in result

    def test_compare_params(self, api_client):
        """Test comparing autopilot params"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"message": "Comparison done"}

        with patch.object(api_client.session, 'post', return_value=mock_response):
            result = api_client.compare_params()

        assert "message" in result


class TestAPIClientScripts:
    def test_run_start_script(self, api_client):
        """Test running start script"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"exit_code": 0, "stdout": "OK"}

        with patch.object(api_client.session, 'post', return_value=mock_response):
            result = api_client.run_start_script()

        assert result["exit_code"] == 0

    def test_run_log_test_script(self, api_client):
        """Test running log test script"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"exit_code": 0, "stdout": "Logs OK"}

        with patch.object(api_client.session, 'post', return_value=mock_response):
            result = api_client.run_log_test_script()

        assert result["exit_code"] == 0


class TestAPIClientPing:
    def test_ping_success(self, api_client):
        """Test ping returns True when server is reachable"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "online"}

        with patch.object(api_client.session, 'get', return_value=mock_response):
            assert api_client.ping() is True

    def test_ping_failure(self, api_client):
        """Test ping returns False when server is unreachable"""
        with patch.object(api_client.session, 'get', side_effect=Exception("Connection refused")):
            assert api_client.ping() is False


class TestAPIClientErrorHandling:
    def test_connection_error(self, api_client):
        """Test that connection errors propagate"""
        from requests.exceptions import ConnectionError

        with patch.object(api_client.session, 'get', side_effect=ConnectionError("Connection refused")):
            with pytest.raises(ConnectionError):
                api_client.get_status()

    def test_timeout_error(self, api_client):
        """Test that timeout errors propagate"""
        from requests.exceptions import Timeout

        with patch.object(api_client.session, 'get', side_effect=Timeout("Request timed out")):
            with pytest.raises(Timeout):
                api_client.get_status()
