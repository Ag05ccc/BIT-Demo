"""
Tests for common/models.py - Data model serialization, creation, and conversion.
"""

import pytest
from common.models import (
    CheckStatus, TestStatus, CheckResult,
    TestSummary, TestRun, SystemInfo
)


class TestCheckStatus:
    def test_all_statuses_exist(self):
        assert CheckStatus.PENDING.value == "pending"
        assert CheckStatus.RUNNING.value == "running"
        assert CheckStatus.PASSED.value == "passed"
        assert CheckStatus.FAILED.value == "failed"
        assert CheckStatus.WARNING.value == "warning"
        assert CheckStatus.SKIPPED.value == "skipped"

    def test_status_count(self):
        assert len(CheckStatus) == 6


class TestTestStatus:
    def test_all_statuses_exist(self):
        assert TestStatus.PENDING.value == "pending"
        assert TestStatus.RUNNING.value == "running"
        assert TestStatus.COMPLETED.value == "completed"
        assert TestStatus.FAILED.value == "failed"


class TestCheckResult:
    def test_create(self):
        result = CheckResult(
            name="TestCheck",
            category="jetson",
            status="passed",
            message="All good",
            details={"key": "value"},
            duration=1.23,
            timestamp="2026-01-15T10:30:00Z"
        )
        assert result.name == "TestCheck"
        assert result.category == "jetson"
        assert result.status == "passed"
        assert result.message == "All good"
        assert result.details == {"key": "value"}
        assert result.duration == 1.23

    def test_create_with_defaults(self):
        result = CheckResult(
            name="TestCheck",
            category="device",
            status="failed",
            message="Error"
        )
        assert result.details == {}
        assert result.duration == 0.0
        assert result.timestamp is None

    def test_to_dict(self):
        result = CheckResult(
            name="TestCheck",
            category="jetson",
            status="passed",
            message="OK"
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["name"] == "TestCheck"
        assert d["category"] == "jetson"
        assert d["status"] == "passed"
        assert d["message"] == "OK"
        assert "details" in d
        assert "duration" in d

    def test_from_dict(self):
        data = {
            "name": "TestCheck",
            "category": "network",
            "status": "warning",
            "message": "Some warning",
            "details": {"latency": 50},
            "duration": 2.5,
            "timestamp": "2026-01-15T10:30:00Z"
        }
        result = CheckResult.from_dict(data)
        assert result.name == "TestCheck"
        assert result.category == "network"
        assert result.status == "warning"
        assert result.details["latency"] == 50

    def test_roundtrip(self):
        original = CheckResult(
            name="RoundTrip",
            category="system",
            status="passed",
            message="Test message",
            details={"a": 1, "b": [1, 2, 3]},
            duration=0.5,
            timestamp="2026-01-15T10:30:00Z"
        )
        d = original.to_dict()
        restored = CheckResult.from_dict(d)
        assert restored.name == original.name
        assert restored.category == original.category
        assert restored.status == original.status
        assert restored.message == original.message
        assert restored.details == original.details
        assert restored.duration == original.duration


class TestTestSummary:
    def test_create_with_defaults(self):
        summary = TestSummary()
        assert summary.total == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.warnings == 0
        assert summary.skipped == 0

    def test_create_with_values(self):
        summary = TestSummary(total=10, passed=7, failed=2, warnings=1, skipped=0)
        assert summary.total == 10
        assert summary.passed == 7

    def test_to_dict(self):
        summary = TestSummary(total=5, passed=3, failed=1, warnings=1, skipped=0)
        d = summary.to_dict()
        assert d["total"] == 5
        assert d["passed"] == 3
        assert d["failed"] == 1

    def test_roundtrip(self):
        original = TestSummary(total=20, passed=15, failed=3, warnings=1, skipped=1)
        restored = TestSummary.from_dict(original.to_dict())
        assert restored.total == original.total
        assert restored.passed == original.passed
        assert restored.failed == original.failed


class TestTestRun:
    def test_create(self):
        run = TestRun(
            test_id="20260115_103000",
            status="completed",
            started="2026-01-15T10:30:00Z"
        )
        assert run.test_id == "20260115_103000"
        assert run.status == "completed"
        assert run.completed is None
        assert run.results == []

    def test_to_dict(self):
        run = TestRun(
            test_id="test_001",
            status="completed",
            started="2026-01-15T10:30:00Z",
            completed="2026-01-15T10:31:00Z",
            summary=TestSummary(total=2, passed=1, failed=1),
            results=[
                CheckResult(name="Check1", category="jetson", status="passed", message="OK"),
                CheckResult(name="Check2", category="device", status="failed", message="Error"),
            ]
        )
        d = run.to_dict()
        assert d["test_id"] == "test_001"
        assert d["status"] == "completed"
        assert d["summary"]["total"] == 2
        assert len(d["results"]) == 2
        assert d["results"][0]["name"] == "Check1"
        assert d["results"][1]["status"] == "failed"

    def test_from_dict(self):
        data = {
            "test_id": "test_002",
            "status": "running",
            "started": "2026-01-15T10:30:00Z",
            "completed": None,
            "summary": {"total": 1, "passed": 1, "failed": 0, "warnings": 0, "skipped": 0},
            "results": [
                {"name": "Check1", "category": "jetson", "status": "passed",
                 "message": "OK", "details": {}, "duration": 0.1, "timestamp": None}
            ]
        }
        run = TestRun.from_dict(data)
        assert run.test_id == "test_002"
        assert run.status == "running"
        assert len(run.results) == 1
        assert run.results[0].name == "Check1"

    def test_roundtrip(self):
        original = TestRun(
            test_id="rt_test",
            status="completed",
            started="2026-01-15T10:30:00Z",
            completed="2026-01-15T10:31:00Z",
            summary=TestSummary(total=3, passed=2, failed=1),
            results=[
                CheckResult(name="A", category="jetson", status="passed", message="OK"),
                CheckResult(name="B", category="device", status="passed", message="OK"),
                CheckResult(name="C", category="network", status="failed", message="Err"),
            ]
        )
        d = original.to_dict()
        restored = TestRun.from_dict(d)
        assert restored.test_id == original.test_id
        assert len(restored.results) == 3
        assert restored.summary.total == 3


class TestSystemInfo:
    def test_create(self):
        info = SystemInfo(
            hostname="jetson-test",
            ip_address="192.168.1.2",
            os_version="Linux 5.10",
            kernel_version="5.10.0",
            uptime_seconds=3600.0,
            cpu_count=6,
            total_ram_gb=8.0,
            total_disk_gb=128.0
        )
        assert info.hostname == "jetson-test"
        assert info.cpu_count == 6

    def test_to_dict(self):
        info = SystemInfo(
            hostname="test",
            ip_address="10.0.0.1",
            os_version="Linux",
            kernel_version="5.10",
            uptime_seconds=100.0,
            cpu_count=4,
            total_ram_gb=4.0,
            total_disk_gb=64.0
        )
        d = info.to_dict()
        assert d["hostname"] == "test"
        assert d["cpu_count"] == 4
        assert d["total_ram_gb"] == 4.0
