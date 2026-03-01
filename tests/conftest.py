"""
Shared test fixtures for Product Test BIT application.
Sets up sys.path and provides common test data.
"""

import sys
import os
import json
import pytest

# Setup sys.path so all imports work correctly
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))  # product_test_bit/
SERVER_DIR = os.path.join(PROJECT_ROOT, 'server')

sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SERVER_DIR)


@pytest.fixture
def sample_config():
    """Sample configuration for testing checks"""
    return {
        "server": {
            "host": "0.0.0.0",
            "port": 5000,
            "debug": False
        },
        "test_pc": {
            "expected_ip": "192.168.1.1"
        },
        "ping_targets": ["192.168.1.1", "192.168.1.3"],
        "environment_vars": {
            "ROS_MASTER_URI": "http://192.168.1.1:11311",
            "ROS_IP": "192.168.1.2",
            "ROS_HOSTNAME": "jetson-test"
        },
        "devices": {
            "deviceA": {
                "path": "/dev/ttyUSB0",
                "description": "Custom sensor A",
                "vendor_id": "0x1234",
                "product_id": "0x5678",
                "baudrate": 9600,
                "test_command": "AT\r\n",
                "expected_response": "OK"
            },
            "deviceB": {
                "path": "/dev/ttyUSB1",
                "description": "Custom sensor B",
                "vendor_id": "0xabcd",
                "product_id": "0xef01",
                "baudrate": 115200
            }
        },
        "autopilot": {
            "connection": "/dev/ttyAutopilot",
            "baud_rate": 921600,
            "heartbeat_timeout": 10,
            "default_params_file": "params/default.param",
            "param_tolerance": 0.01
        },
        "ros": {
            "master_uri": "http://192.168.1.1:11311",
            "required_nodes": ["/node1", "/node2", "/node3"],
            "required_topics": {
                "/camera/image": {
                    "rate_min": 30,
                    "type": "sensor_msgs/Image"
                },
                "/imu/data": {
                    "rate_min": 100,
                    "type": "sensor_msgs/Imu"
                }
            },
            "required_frames": ["base_link", "camera_link"],
            "check_timeout": 5.0
        },
        "resources": {
            "cpu_max_percent": 90,
            "ram_max_percent": 85,
            "disk_min_free_gb": 5,
            "temp_max_celsius": 80
        },
        "systemd_services": ["roscore", "autopilot-bridge"],
        "udev_rules": ["/etc/udev/rules.d/99-autopilot.rules"],
        "scripts": {
            "startup": "/home/nvidia/scripts/start_system.sh",
            "log_test": "/home/nvidia/scripts/log_test.sh"
        },
        "logging": {
            "rosbag_dir": "/home/nvidia/rosbags",
            "min_bag_size_mb": 1,
            "max_bag_age_hours": 24
        },
        "checks": {
            "enabled_categories": ["all"],
            "disabled_checks": [],
            "timeout_seconds": 30,
            "continue_on_failure": True
        }
    }


@pytest.fixture
def empty_config():
    """Minimal/empty configuration for testing edge cases"""
    return {
        "checks": {
            "timeout_seconds": 5
        }
    }


@pytest.fixture
def flask_app(sample_config):
    """Flask test client"""
    # Import after sys.path setup
    import server.test_server as ts
    ts.config = sample_config
    ts.test_runs = {}
    ts.current_test_id = None
    ts.app.config['TESTING'] = True
    return ts.app


@pytest.fixture
def client(flask_app):
    """Flask test client"""
    return flask_app.test_client()
