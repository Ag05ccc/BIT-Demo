"""
Base class for all system checks.
All check classes should inherit from BaseCheck.
"""

import time
import traceback as tb_module
import inspect
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any
import sys
import os

logger = logging.getLogger(__name__)

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
        self.debug_mode = config.get('developer', {}).get('debug', False)

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

            # Capture the source location (file:line) where the exception originated
            frames = tb_module.extract_tb(sys.exc_info()[2])
            source_frame = None
            for frame in reversed(frames):
                # Skip frames from base_check.py itself to point at the check's own code
                if os.path.basename(frame.filename) != 'base_check.py':
                    source_frame = frame
                    break
            if source_frame is None and frames:
                source_frame = frames[-1]

            if source_frame:
                try:
                    rel_path = os.path.relpath(source_frame.filename)
                except ValueError:
                    rel_path = source_frame.filename
                self.details["source_location"] = (
                    f"{rel_path}:{source_frame.lineno} in {source_frame.name}()"
                )

            if self.debug_mode:
                self.details["traceback"] = tb_module.format_exc()

            logger.error(
                "[%s] %s: %s  -->  %s",
                self.__class__.__name__,
                type(e).__name__,
                str(e),
                self.details.get("source_location", "unknown location"),
            )
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

        # Capture the caller's source location so developers can see which line triggered the warning
        caller = inspect.currentframe().f_back
        if caller:
            try:
                rel_path = os.path.relpath(caller.f_code.co_filename)
            except ValueError:
                rel_path = caller.f_code.co_filename
            self.details["source_location"] = (
                f"{rel_path}:{caller.f_lineno} in {caller.f_code.co_name}()"
            )

        logger.warning(
            "[%s] %s  -->  %s",
            self.__class__.__name__,
            message,
            self.details.get("source_location", "unknown location"),
        )
