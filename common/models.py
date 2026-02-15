"""
Shared data models for Product Test BIT application.
Used by both server and client.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class CheckStatus(Enum):
    """Status of a check"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class TestStatus(Enum):
    """Status of overall test run"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CheckResult:
    """Result of a single check"""
    name: str
    category: str
    status: str  # CheckStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckResult':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class TestSummary:
    """Summary of test results"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    skipped: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestSummary':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class TestRun:
    """Complete test run with all results"""
    test_id: str
    status: str  # TestStatus
    started: str
    completed: Optional[str] = None
    summary: TestSummary = field(default_factory=TestSummary)
    results: List[CheckResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_id": self.test_id,
            "status": self.status,
            "started": self.started,
            "completed": self.completed,
            "summary": self.summary.to_dict(),
            "results": [r.to_dict() for r in self.results]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestRun':
        """Create from dictionary"""
        return cls(
            test_id=data["test_id"],
            status=data["status"],
            started=data["started"],
            completed=data.get("completed"),
            summary=TestSummary.from_dict(data.get("summary", {})),
            results=[CheckResult.from_dict(r) for r in data.get("results", [])]
        )


@dataclass
class SystemInfo:
    """System information from Jetson"""
    hostname: str
    ip_address: str
    os_version: str
    kernel_version: str
    uptime_seconds: float
    cpu_count: int
    total_ram_gb: float
    total_disk_gb: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemInfo':
        """Create from dictionary"""
        return cls(**data)
