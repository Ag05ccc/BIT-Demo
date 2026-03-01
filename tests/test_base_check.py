"""
Tests for server/checks/base_check.py - BaseCheck class behavior.
"""

import pytest
from checks.base_check import BaseCheck
from common.models import CheckResult


class PassingCheck(BaseCheck):
    """Test check that always passes"""
    category = "test"

    def run(self):
        self.message = "All good"
        return True


class FailingCheck(BaseCheck):
    """Test check that always fails"""
    category = "test"

    def run(self):
        self.message = "Something went wrong"
        return False


class ExceptionCheck(BaseCheck):
    """Test check that raises an exception"""
    category = "test"

    def run(self):
        raise RuntimeError("Unexpected error")


class SkippingCheck(BaseCheck):
    """Test check that skips itself"""
    category = "test"

    def run(self):
        self.skip("Not applicable")
        return False


class WarningCheck(BaseCheck):
    """Test check that issues a warning"""
    category = "test"

    def run(self):
        self.warn("Approaching limit", {"value": 78, "threshold": 80})
        return True


class SlowCheck(BaseCheck):
    """Test check that takes time"""
    category = "test"

    def run(self):
        import time
        time.sleep(0.1)
        self.message = "Done"
        return True


class TestBaseCheckInit:
    def test_initial_state(self, sample_config):
        check = PassingCheck(sample_config)
        assert check.status == "pending"
        assert check.message == ""
        assert check.details == {}
        assert check.duration == 0.0
        assert check.timestamp is None

    def test_timeout_from_config(self, sample_config):
        check = PassingCheck(sample_config)
        assert check.timeout == 30  # From sample_config

    def test_default_timeout(self):
        check = PassingCheck({})
        assert check.timeout == 30  # DEFAULT_CHECK_TIMEOUT

    def test_category(self, sample_config):
        check = PassingCheck(sample_config)
        assert check.category == "test"


class TestBaseCheckExecute:
    def test_passing_check(self, sample_config):
        check = PassingCheck(sample_config)
        result = check.execute()
        assert isinstance(result, CheckResult)
        assert result.status == "passed"
        assert result.message == "All good"
        assert result.name == "PassingCheck"
        assert result.category == "test"
        assert result.duration >= 0
        assert result.timestamp is not None

    def test_failing_check(self, sample_config):
        check = FailingCheck(sample_config)
        result = check.execute()
        assert result.status == "failed"
        assert result.message == "Something went wrong"

    def test_exception_check(self, sample_config):
        check = ExceptionCheck(sample_config)
        result = check.execute()
        assert result.status == "failed"
        assert "Unexpected error" in result.message
        assert result.details["exception_type"] == "RuntimeError"

    def test_skipping_check(self, sample_config):
        check = SkippingCheck(sample_config)
        result = check.execute()
        assert result.status == "skipped"
        assert result.message == "Not applicable"

    def test_warning_check(self, sample_config):
        check = WarningCheck(sample_config)
        result = check.execute()
        assert result.status == "warning"
        assert "Approaching limit" in result.message
        assert result.details["value"] == 78

    def test_duration_tracked(self, sample_config):
        check = SlowCheck(sample_config)
        result = check.execute()
        assert result.duration >= 0.1
        assert result.status == "passed"


class TestBaseCheckGetResult:
    def test_get_result_returns_check_result(self, sample_config):
        check = PassingCheck(sample_config)
        check.execute()
        result = check.get_result()
        assert isinstance(result, CheckResult)
        assert result.name == "PassingCheck"

    def test_get_result_to_dict(self, sample_config):
        check = PassingCheck(sample_config)
        check.execute()
        d = check.get_result().to_dict()
        assert isinstance(d, dict)
        assert "name" in d
        assert "status" in d
        assert "message" in d
        assert "duration" in d


class TestBaseCheckSkipAndWarn:
    def test_skip(self, sample_config):
        check = PassingCheck(sample_config)
        check.skip("Test reason")
        assert check.status == "skipped"
        assert check.message == "Test reason"

    def test_warn(self, sample_config):
        check = PassingCheck(sample_config)
        check.warn("Warning message", {"detail": 42})
        assert check.status == "warning"
        assert check.message == "Warning message"
        assert check.details["detail"] == 42

    def test_warn_without_details(self, sample_config):
        check = PassingCheck(sample_config)
        check.warn("Simple warning")
        assert check.status == "warning"
        assert check.details == {}
