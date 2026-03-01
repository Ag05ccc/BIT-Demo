"""
Base class for all system checks.
All check classes should inherit from BaseCheck.
"""

import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.models import CheckResult
from common.constants import (
    TIMESTAMP_FORMAT,
    DEFAULT_CHECK_TIMEOUT,
    CATEGORY_JETSON,
    CATEGORY_DEVICE,
    CATEGORY_NETWORK,
    CATEGORY_ROS,
    CATEGORY_AUTOPILOT,
    CATEGORY_SYSTEM
)
from checks.solutions import get_solution


class BaseCheck(ABC):
    """
    Base class for all checks.

    Attributes:
        category: Check category (jetson, device, network, ros, autopilot, system)
        config: Configuration dictionary
        status: Current status (pending, running, passed, failed, warning, skipped)
        message: Human-readable result message
        details: Additional details dictionary
        duration: Check execution time in seconds
        timestamp: ISO formatted timestamp
    """

    category = "unknown"  # Override in subclass

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize check.

        Args:
            config: Configuration dictionary from config.json
        """
        self.config = config
        self.status = "pending"
        self.message = ""
        self.details = {}
        self.duration = 0.0
        self.timestamp = None
        self.timeout = config.get('checks', {}).get('timeout_seconds', DEFAULT_CHECK_TIMEOUT)

    @abstractmethod
    def run(self) -> bool:
        """
        Execute the check.
        Must be implemented by subclass.

        Returns:
            True if check passed, False otherwise
        """
        pass

    def execute(self) -> CheckResult:
        """
        Execute the check with timing and error handling.

        Returns:
            CheckResult object with results
        """
        self.status = "running"
        self.timestamp = datetime.utcnow().strftime(TIMESTAMP_FORMAT)
        start_time = time.time()

        try:
            success = self.run()
            if self.status == "running":  # Only update if not already set
                self.status = "passed" if success else "failed"
        except Exception as e:
            self.status = "failed"
            self.message = f"Exception: {str(e)}"
            self.details["exception"] = str(e)
            self.details["exception_type"] = type(e).__name__
        finally:
            self.duration = time.time() - start_time

        # Attach solution hint for non-passed statuses
        if self.status in ("failed", "warning", "skipped"):
            solution = get_solution(self.__class__.__name__, self.status)
            if solution:
                self.details["solution"] = solution

        return self.get_result()

    def get_result(self) -> CheckResult:
        """
        Get check result as CheckResult object.

        Returns:
            CheckResult object
        """
        return CheckResult(
            name=self.__class__.__name__,
            category=self.category,
            status=self.status,
            message=self.message,
            details=self.details,
            duration=self.duration,
            timestamp=self.timestamp
        )

    def skip(self, reason: str):
        """
        Skip this check with a reason.

        Args:
            reason: Reason for skipping
        """
        self.status = "skipped"
        self.message = reason

    def warn(self, message: str, details: Dict[str, Any] = None):
        """
        Mark check as warning.

        Args:
            message: Warning message
            details: Additional details
        """
        self.status = "warning"
        self.message = message
        if details:
            self.details.update(details)
