"""
Tests for server/checks/ros_checks.py - ROS checks.
ROS libraries are mocked since they won't be installed on the test PC.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys


# Mock ROS modules before importing ros_checks
mock_rospy = MagicMock()
mock_rostopic = MagicMock()
mock_rosgraph = MagicMock()
mock_rosnode = MagicMock()

sys.modules['rospy'] = mock_rospy
sys.modules['rostopic'] = mock_rostopic
sys.modules['rosgraph'] = mock_rosgraph
sys.modules['rosnode'] = mock_rosnode

from checks.ros_checks import (
    ROSMasterCheck, ROSNodesCheck, ROSTopicsCheck,
    TopicFreshnessCheck, TFFramesCheck, RosbagCheck
)


class TestROSMasterCheck:
    def test_master_running(self, sample_config):
        """Passes when ROS Master is reachable"""
        check = ROSMasterCheck(sample_config)

        mock_master = MagicMock()
        mock_master.getPid.return_value = 12345
        mock_master.getMasterUri.return_value = "http://192.168.1.1:11311"

        with patch('checks.ros_checks.ROS_AVAILABLE', True), \
             patch('checks.ros_checks.rosgraph.Master', return_value=mock_master):
            result = check.execute()

        assert result.status == "passed"
        assert "ROS Master is running" in result.message

    def test_master_not_reachable(self, sample_config):
        """Fails when ROS Master is not reachable"""
        check = ROSMasterCheck(sample_config)

        with patch('checks.ros_checks.ROS_AVAILABLE', True), \
             patch('checks.ros_checks.rosgraph.Master', side_effect=Exception("Connection refused")):
            result = check.execute()

        assert result.status == "failed"
        assert "not reachable" in result.message

    def test_ros_not_installed(self, sample_config):
        """Skips when ROS not installed"""
        check = ROSMasterCheck(sample_config)

        with patch('checks.ros_checks.ROS_AVAILABLE', False):
            result = check.execute()

        assert result.status == "skipped"
        assert "ROS not installed" in result.message


class TestROSNodesCheck:
    def test_all_nodes_running(self, sample_config):
        """Passes when all required nodes are running"""
        check = ROSNodesCheck(sample_config)

        with patch('checks.ros_checks.ROS_AVAILABLE', True), \
             patch('checks.ros_checks.rosnode.get_node_names',
                   return_value=['/node1', '/node2', '/node3', '/rosout']):
            result = check.execute()

        assert result.status == "passed"
        assert "3 required node(s) running" in result.message

    def test_nodes_missing(self, sample_config):
        """Fails when required nodes are missing"""
        check = ROSNodesCheck(sample_config)

        with patch('checks.ros_checks.ROS_AVAILABLE', True), \
             patch('checks.ros_checks.rosnode.get_node_names',
                   return_value=['/node1', '/rosout']):
            result = check.execute()

        assert result.status == "failed"
        assert "/node2" in result.message or "/node3" in result.message

    def test_ros_not_installed(self, sample_config):
        """Skips when ROS not installed"""
        check = ROSNodesCheck(sample_config)

        with patch('checks.ros_checks.ROS_AVAILABLE', False):
            result = check.execute()

        assert result.status == "skipped"


class TestROSTopicsCheck:
    def test_all_topics_publishing(self, sample_config):
        """Passes when all required topics are publishing"""
        check = ROSTopicsCheck(sample_config)

        with patch('checks.ros_checks.ROS_AVAILABLE', True), \
             patch('checks.ros_checks.rospy.get_published_topics',
                   return_value=[
                       ['/camera/image', 'sensor_msgs/Image'],
                       ['/imu/data', 'sensor_msgs/Imu'],
                       ['/rosout', 'rosgraph_msgs/Log']
                   ]):
            result = check.execute()

        assert result.status == "passed"
        assert "2 required topic(s) publishing" in result.message

    def test_topics_missing(self, sample_config):
        """Fails when required topics not publishing"""
        check = ROSTopicsCheck(sample_config)

        with patch('checks.ros_checks.ROS_AVAILABLE', True), \
             patch('checks.ros_checks.rospy.get_published_topics',
                   return_value=[['/rosout', 'rosgraph_msgs/Log']]):
            result = check.execute()

        assert result.status == "failed"
        assert "not publishing" in result.message


class TestTFFramesCheck:
    def test_warning_not_implemented(self, sample_config):
        """Issues warning since TF check is not fully implemented"""
        check = TFFramesCheck(sample_config)

        with patch('checks.ros_checks.ROS_AVAILABLE', True):
            result = check.execute()

        assert result.status == "warning"


class TestRosbagCheck:
    def test_recording_active_with_files(self, sample_config):
        """Passes when rosbag is recording and bag files exist"""
        check = RosbagCheck(sample_config)

        mock_pgrep = MagicMock()
        mock_pgrep.returncode = 0

        import os

        with patch('checks.ros_checks.subprocess.run', return_value=mock_pgrep), \
             patch('checks.ros_checks.os.path.exists', return_value=True), \
             patch('checks.ros_checks.glob.glob', return_value=['/home/nvidia/rosbags/test.bag']), \
             patch('checks.ros_checks.os.path.getmtime', return_value=1700000000), \
             patch('checks.ros_checks.os.path.getsize', return_value=10 * 1024 * 1024):  # 10 MB
            result = check.execute()

        assert result.status == "passed"

    def test_no_bag_dir(self, empty_config):
        """Skips when rosbag dir not configured"""
        check = RosbagCheck(empty_config)
        result = check.execute()
        assert result.status == "skipped"
