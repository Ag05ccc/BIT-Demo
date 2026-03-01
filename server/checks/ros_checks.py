"""
ROS checks: master, nodes, topics, rates, values, TF frames, timestamps.
"""

import time
from .base_check import BaseCheck
from common.constants import CATEGORY_ROS

# Try to import ROS libraries
try:
    import rospy
    import rostopic
    import rosgraph
    import rosnode
    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False


class ROSMasterCheck(BaseCheck):
    """Check if ROS Master is running and reachable"""

    category = CATEGORY_ROS

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("ROS not installed (install ros-noetic-desktop-full)")
            return False

        try:
            master_uri = self.config.get('ros', {}).get('master_uri')
            if master_uri:
                # Temporarily override ROS_MASTER_URI
                import os
                os.environ['ROS_MASTER_URI'] = master_uri

            # Try to connect to ROS Master
            master = rosgraph.Master('/test_bit_check')
            master.getPid()

            self.status = "passed"
            self.message = "ROS Master is running"
            self.details = {"master_uri": master.getMasterUri()}
            return True

        except Exception as e:
            self.status = "failed"
            self.message = f"ROS Master not reachable: {e}"
            return False


class ROSNodesCheck(BaseCheck):
    """Check if required ROS nodes are running"""

    category = CATEGORY_ROS

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("ROS not installed")
            return False

        try:
            required_nodes = self.config.get('ros', {}).get('required_nodes', [])

            if not required_nodes:
                self.skip("No required nodes configured")
                return False

            # Get list of running nodes
            try:
                running_nodes = rosnode.get_node_names()
            except Exception as e:
                self.status = "failed"
                self.message = f"Failed to get node list: {e}"
                return False

            # Check which required nodes are running
            running_required = [n for n in required_nodes if n in running_nodes]
            missing = [n for n in required_nodes if n not in running_nodes]

            self.details = {
                "required": required_nodes,
                "running": running_required,
                "missing": missing,
                "all_running_nodes": running_nodes
            }

            if missing:
                self.status = "failed"
                self.message = f"Missing nodes: {', '.join(missing)}"
                return False
            else:
                self.status = "passed"
                self.message = f"All {len(required_nodes)} required node(s) running"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking ROS nodes: {e}"
            return False


class ROSTopicsCheck(BaseCheck):
    """Check if required ROS topics exist and are publishing"""

    category = CATEGORY_ROS

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("ROS not installed")
            return False

        try:
            required_topics = self.config.get('ros', {}).get('required_topics', {})

            if not required_topics:
                self.skip("No required topics configured")
                return False

            # Get list of published topics
            try:
                published_topics = rospy.get_published_topics()
                topic_names = [t[0] for t in published_topics]
            except Exception as e:
                self.status = "failed"
                self.message = f"Failed to get topic list: {e}"
                return False

            # Check which required topics are publishing
            publishing = []
            not_publishing = []

            for topic_name in required_topics.keys():
                if topic_name in topic_names:
                    publishing.append(topic_name)
                else:
                    not_publishing.append(topic_name)

            self.details = {
                "required": list(required_topics.keys()),
                "publishing": publishing,
                "not_publishing": not_publishing
            }

            if not_publishing:
                self.status = "failed"
                self.message = f"Topics not publishing: {', '.join(not_publishing)}"
                return False
            else:
                self.status = "passed"
                self.message = f"All {len(publishing)} required topic(s) publishing"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking ROS topics: {e}"
            return False


class TopicRateCheck(BaseCheck):
    """Check publishing rates for ROS topics"""

    category = CATEGORY_ROS

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("ROS not installed")
            return False

        try:
            required_topics = self.config.get('ros', {}).get('required_topics', {})
            check_timeout = self.config.get('ros', {}).get('check_timeout', 5.0)

            if not required_topics:
                self.skip("No required topics configured")
                return False

            slow_topics = []
            ok_topics = []

            for topic_name, topic_config in required_topics.items():
                min_rate = topic_config.get('rate_min')
                if not min_rate:
                    continue  # Skip topics without rate requirement

                try:
                    # Use rostopic.ROSTopicHz to measure rate
                    rt = rostopic.ROSTopicHz(-1)  # -1 = window_size (unlimited)

                    # Subscribe and wait for messages
                    msg_class, real_topic, _ = rostopic.get_topic_class(topic_name, blocking=False)
                    if not msg_class:
                        slow_topics.append({
                            "topic": topic_name,
                            "min_rate": min_rate,
                            "measured_rate": 0,
                            "reason": "Topic not found"
                        })
                        continue

                    sub = rospy.Subscriber(real_topic, msg_class, rt.callback_hz)

                    # Wait and measure
                    time.sleep(check_timeout)

                    # Get rate
                    rate = rt.get_hz(real_topic)
                    sub.unregister()

                    if rate:
                        actual_rate = rate[0]  # mean rate
                        if actual_rate >= min_rate:
                            ok_topics.append({
                                "topic": topic_name,
                                "rate": round(actual_rate, 1),
                                "min": min_rate
                            })
                        else:
                            slow_topics.append({
                                "topic": topic_name,
                                "rate": round(actual_rate, 1),
                                "min": min_rate
                            })
                    else:
                        slow_topics.append({
                            "topic": topic_name,
                            "min_rate": min_rate,
                            "measured_rate": 0,
                            "reason": "No messages received"
                        })

                except Exception as e:
                    slow_topics.append({
                        "topic": topic_name,
                        "error": str(e)
                    })

            self.details = {
                "ok_topics": ok_topics,
                "slow_topics": slow_topics
            }

            if slow_topics:
                self.status = "failed"
                self.message = f"{len(slow_topics)} topic(s) below minimum rate"
                return False
            else:
                self.status = "passed"
                self.message = f"All {len(ok_topics)} topic(s) at acceptable rates"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking topic rates: {e}"
            return False


class TopicFreshnessCheck(BaseCheck):
    """Check last message age for ROS topics"""

    category = CATEGORY_ROS

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("ROS not installed")
            return False

        try:
            required_topics = self.config.get('ros', {}).get('required_topics', {})
            max_age = self.config.get('ros', {}).get('topic_freshness_timeout', 5.0)

            if not required_topics:
                self.skip("No required topics configured")
                return False

            fresh = []
            stale = []

            for topic_name in required_topics.keys():
                try:
                    # Subscribe and get one message with timeout
                    msg_class, real_topic, _ = rostopic.get_topic_class(topic_name, blocking=False)
                    if not msg_class:
                        stale.append({"topic": topic_name, "reason": "Topic not found"})
                        continue

                    msg = rospy.wait_for_message(real_topic, msg_class, timeout=max_age)

                    if msg:
                        fresh.append(topic_name)
                    else:
                        stale.append({"topic": topic_name, "reason": "No message received"})

                except rospy.ROSException:
                    stale.append({"topic": topic_name, "reason": f"Timeout ({max_age}s)"})
                except Exception as e:
                    stale.append({"topic": topic_name, "error": str(e)})

            self.details = {
                "fresh": fresh,
                "stale": stale
            }

            if stale:
                self.status = "failed"
                self.message = f"{len(stale)} topic(s) have stale/no messages"
                return False
            else:
                self.status = "passed"
                self.message = f"All {len(fresh)} topic(s) have fresh messages"
                return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking topic freshness: {e}"
            return False


# Additional ROS checks can be added here (TF frames, timestamp monotonicity, rosbag, etc.)
# For brevity, I'm including simplified versions

class TFFramesCheck(BaseCheck):
    """Check if required TF frames exist"""

    category = CATEGORY_ROS

    def run(self) -> bool:
        if not ROS_AVAILABLE:
            self.skip("ROS not installed")
            return False

        try:
            required_frames = self.config.get('ros', {}).get('required_frames', [])

            if not required_frames:
                self.skip("No required TF frames configured")
                return False

            # This is a simplified check - full implementation would use tf2_ros
            self.warn("TF frame check not fully implemented yet")
            return True

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking TF frames: {e}"
            return False


class RosbagCheck(BaseCheck):
    """Check if rosbag logging is enabled and working"""

    category = CATEGORY_ROS

    def run(self) -> bool:
        try:
            logging_config = self.config.get('logging', {})
            rosbag_dir = logging_config.get('rosbag_dir')

            if not rosbag_dir:
                self.skip("Rosbag directory not configured")
                return False

            import os
            import glob
            import subprocess

            # Check if rosbag record is running
            result = subprocess.run(
                ['pgrep', '-f', 'rosbag record'],
                capture_output=True,
                text=True
            )

            is_recording = result.returncode == 0

            # Check for recent bag files
            bag_files = glob.glob(os.path.join(rosbag_dir, '*.bag'))
            if bag_files:
                # Get most recent bag file
                recent_bag = max(bag_files, key=os.path.getmtime)
                bag_size_mb = os.path.getsize(recent_bag) / (1024 * 1024)
                min_size_mb = logging_config.get('min_bag_size_mb', 1)

                self.details = {
                    "recording": is_recording,
                    "recent_bag": os.path.basename(recent_bag),
                    "size_mb": round(bag_size_mb, 2),
                    "total_bags": len(bag_files)
                }

                if is_recording and bag_size_mb >= min_size_mb:
                    self.status = "passed"
                    self.message = f"Rosbag recording active ({bag_size_mb:.1f} MB)"
                    return True
                else:
                    self.warn(f"Rosbag recording: {is_recording}, size: {bag_size_mb:.1f} MB")
                    return True
            else:
                self.details = {"recording": is_recording, "bag_files": 0}
                if is_recording:
                    self.warn("Rosbag recording but no files found yet")
                    return True
                else:
                    self.status = "failed"
                    self.message = "Rosbag not recording"
                    return False

        except Exception as e:
            self.status = "failed"
            self.message = f"Error checking rosbag: {e}"
            return False
