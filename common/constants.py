"""
Shared constants for Product Test BIT application.
"""

# API Endpoints
API_PREFIX = "/api"
API_STATUS = f"{API_PREFIX}/status"
API_CONFIG = f"{API_PREFIX}/config"
API_TEST_RUN = f"{API_PREFIX}/test/run"
API_TEST_RESULTS = f"{API_PREFIX}/test/results"
API_SYSTEM_INFO = f"{API_PREFIX}/system/info"
API_AUTOPILOT_PARAMS_EXPORT = f"{API_PREFIX}/autopilot/params/export"
API_AUTOPILOT_PARAMS_COMPARE = f"{API_PREFIX}/autopilot/params/compare"
API_SCRIPTS_START = f"{API_PREFIX}/scripts/start"
API_SCRIPTS_LOG_TEST = f"{API_PREFIX}/scripts/log_test"

# Check Categories
CATEGORY_JETSON = "jetson"
CATEGORY_DEVICE = "device"
CATEGORY_NETWORK = "network"
CATEGORY_ROS = "ros"
CATEGORY_AUTOPILOT = "autopilot"
CATEGORY_SYSTEM = "system"

ALL_CATEGORIES = [
    CATEGORY_JETSON,
    CATEGORY_DEVICE,
    CATEGORY_NETWORK,
    CATEGORY_ROS,
    CATEGORY_AUTOPILOT,
    CATEGORY_SYSTEM
]

# Status Colors (for rich UI)
COLOR_PASSED = "green"
COLOR_FAILED = "red"
COLOR_WARNING = "yellow"
COLOR_SKIPPED = "blue"
COLOR_RUNNING = "cyan"
COLOR_PENDING = "white"

# Status Symbols
SYMBOL_PASSED = "✓"
SYMBOL_FAILED = "✗"
SYMBOL_WARNING = "⚠"
SYMBOL_SKIPPED = "○"
SYMBOL_RUNNING = "⟳"
SYMBOL_PENDING = "..."

# Timeouts (seconds)
DEFAULT_CHECK_TIMEOUT = 30
DEFAULT_API_TIMEOUT = 60
DEFAULT_AUTOPILOT_HEARTBEAT_TIMEOUT = 10

# Default Ports
DEFAULT_SERVER_PORT = 5000

# Date/Time Formats
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
TEST_ID_FORMAT = "%Y%m%d_%H%M%S"
PARAM_EXPORT_FORMAT = "current_device_%Y%m%d_%H%M%S.params"
