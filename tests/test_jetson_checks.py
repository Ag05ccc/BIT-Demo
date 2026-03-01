"""
Tests for server/checks/jetson_checks.py - Jetson health checks.
All external dependencies are mocked for local testing.
"""

import pytest
from unittest.mock import patch, MagicMock
from checks.jetson_checks import JetsonBootCheck, JetsonResourcesCheck, JetsonTemperatureCheck


class TestJetsonBootCheck:
    def test_no_errors(self, sample_config):
        """Boot check passes when dmesg shows no critical errors"""
        check = JetsonBootCheck(sample_config)

        mock_result = MagicMock()
        mock_result.stdout = ""  # No error lines
        mock_result.returncode = 0

        with patch('checks.jetson_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "passed"
        assert "No critical" in result.message

    def test_critical_errors_found(self, sample_config):
        """Boot check fails when critical errors are found"""
        check = JetsonBootCheck(sample_config)

        mock_result = MagicMock()
        mock_result.stdout = "error: GPU init failed\nerror: I2C bus timeout\nerror: DMA failure\n"
        mock_result.returncode = 0

        with patch('checks.jetson_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "failed"
        assert "3 critical" in result.message

    def test_few_errors_warning(self, sample_config):
        """Boot check warns when few errors found"""
        check = JetsonBootCheck(sample_config)

        mock_result = MagicMock()
        mock_result.stdout = "error: something minor\n"
        mock_result.returncode = 0

        with patch('checks.jetson_checks.subprocess.run', return_value=mock_result):
            result = check.execute()

        assert result.status == "warning"

    def test_dmesg_not_found(self, sample_config):
        """Boot check skips when dmesg not available (e.g., on Windows)"""
        check = JetsonBootCheck(sample_config)

        with patch('checks.jetson_checks.subprocess.run', side_effect=FileNotFoundError):
            result = check.execute()

        assert result.status == "skipped"

    def test_dmesg_timeout(self, sample_config):
        """Boot check fails when dmesg times out"""
        check = JetsonBootCheck(sample_config)
        from subprocess import TimeoutExpired

        with patch('checks.jetson_checks.subprocess.run', side_effect=TimeoutExpired('dmesg', 10)):
            result = check.execute()

        assert result.status == "failed"
        assert "timed out" in result.message


class TestJetsonResourcesCheck:
    def test_resources_ok(self, sample_config):
        """Resource check passes when all within limits"""
        check = JetsonResourcesCheck(sample_config)

        mock_cpu = 50.0
        mock_vmem = MagicMock()
        mock_vmem.percent = 60.0
        mock_vmem.used = 4 * 1024**3
        mock_vmem.total = 8 * 1024**3
        mock_disk = MagicMock()
        mock_disk.free = 20 * 1024**3
        mock_disk.total = 128 * 1024**3
        mock_disk.percent = 85.0

        with patch('checks.jetson_checks.psutil.cpu_percent', return_value=mock_cpu), \
             patch('checks.jetson_checks.psutil.virtual_memory', return_value=mock_vmem), \
             patch('checks.jetson_checks.psutil.disk_usage', return_value=mock_disk):
            result = check.execute()

        assert result.status == "passed"
        assert "Resources OK" in result.message
        assert result.details["cpu_percent"] == 50.0
        assert result.details["ram_percent"] == 60.0

    def test_cpu_too_high(self, sample_config):
        """Resource check fails when CPU exceeds threshold"""
        check = JetsonResourcesCheck(sample_config)

        mock_vmem = MagicMock()
        mock_vmem.percent = 50.0
        mock_vmem.used = 4 * 1024**3
        mock_vmem.total = 8 * 1024**3
        mock_disk = MagicMock()
        mock_disk.free = 20 * 1024**3
        mock_disk.total = 128 * 1024**3
        mock_disk.percent = 50.0

        with patch('checks.jetson_checks.psutil.cpu_percent', return_value=95.0), \
             patch('checks.jetson_checks.psutil.virtual_memory', return_value=mock_vmem), \
             patch('checks.jetson_checks.psutil.disk_usage', return_value=mock_disk):
            result = check.execute()

        assert result.status == "failed"
        assert "CPU" in result.message

    def test_ram_too_high(self, sample_config):
        """Resource check fails when RAM exceeds threshold"""
        check = JetsonResourcesCheck(sample_config)

        mock_vmem = MagicMock()
        mock_vmem.percent = 95.0
        mock_vmem.used = 7 * 1024**3
        mock_vmem.total = 8 * 1024**3
        mock_disk = MagicMock()
        mock_disk.free = 20 * 1024**3
        mock_disk.total = 128 * 1024**3
        mock_disk.percent = 50.0

        with patch('checks.jetson_checks.psutil.cpu_percent', return_value=30.0), \
             patch('checks.jetson_checks.psutil.virtual_memory', return_value=mock_vmem), \
             patch('checks.jetson_checks.psutil.disk_usage', return_value=mock_disk):
            result = check.execute()

        assert result.status == "failed"
        assert "RAM" in result.message

    def test_disk_low(self, sample_config):
        """Resource check fails when disk space too low"""
        check = JetsonResourcesCheck(sample_config)

        mock_vmem = MagicMock()
        mock_vmem.percent = 50.0
        mock_vmem.used = 4 * 1024**3
        mock_vmem.total = 8 * 1024**3
        mock_disk = MagicMock()
        mock_disk.free = 2 * 1024**3  # 2 GB free, min is 5 GB
        mock_disk.total = 128 * 1024**3
        mock_disk.percent = 98.0

        with patch('checks.jetson_checks.psutil.cpu_percent', return_value=30.0), \
             patch('checks.jetson_checks.psutil.virtual_memory', return_value=mock_vmem), \
             patch('checks.jetson_checks.psutil.disk_usage', return_value=mock_disk):
            result = check.execute()

        assert result.status == "failed"
        assert "Disk" in result.message


class TestJetsonTemperatureCheck:
    def test_temperature_ok(self, sample_config):
        """Temperature check passes when below threshold"""
        check = JetsonTemperatureCheck(sample_config)

        # Mock reading thermal zone files
        def mock_open_thermal(path, *args, **kwargs):
            if 'thermal_zone0' in path:
                return MagicMock(__enter__=lambda s: MagicMock(read=lambda: "45000\n", strip=lambda: "45000"),
                                 __exit__=lambda *a: None)
            raise FileNotFoundError

        # Use a simpler approach: mock builtins.open
        from unittest.mock import mock_open
        import builtins

        # Create a mock that simulates thermal zone files
        thermal_data = {"0": "45000", "1": "50000"}
        call_count = [0]

        def mock_open_fn(path, *args, **kwargs):
            for zone_id, temp in thermal_data.items():
                if f'thermal_zone{zone_id}' in path:
                    m = MagicMock()
                    m.__enter__ = lambda s: MagicMock(read=lambda: temp + "\n", strip=lambda: temp)
                    m.__exit__ = lambda *a: None
                    m.read.return_value = temp + "\n"
                    return m
            raise FileNotFoundError

        with patch('builtins.open', side_effect=mock_open_fn):
            result = check.execute()

        assert result.status == "passed"
        assert "50.0" in result.message  # max temp

    def test_temperature_too_high(self, sample_config):
        """Temperature check fails when above threshold"""
        check = JetsonTemperatureCheck(sample_config)

        def mock_open_fn(path, *args, **kwargs):
            if 'thermal_zone0' in path:
                m = MagicMock()
                m.__enter__ = lambda s: MagicMock(read=lambda: "85000\n")
                m.__exit__ = lambda *a: None
                return m
            raise FileNotFoundError

        with patch('builtins.open', side_effect=mock_open_fn):
            result = check.execute()

        assert result.status == "failed"
        assert "85.0" in result.message

    def test_no_thermal_zones(self, sample_config):
        """Temperature check skips when no thermal zones found"""
        check = JetsonTemperatureCheck(sample_config)

        with patch('builtins.open', side_effect=FileNotFoundError):
            result = check.execute()

        assert result.status == "skipped"
