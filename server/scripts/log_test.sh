#!/bin/bash
# Template log verification script
# Check rosbag files, application logs, etc.

echo "========================================"
echo " Log Test"
echo "========================================"
echo ""

LOG_DIR="/var/log/test_system"
BAG_DIR="$HOME/rosbags"

echo "[1/3] Checking rosbag recording status..."
# Check if rosbag is recording
if pgrep -f "rosbag record" > /dev/null; then
    echo "  ✓ Rosbag recording: ACTIVE"
else
    echo "  ✗ Rosbag recording: INACTIVE"
    # Uncomment to fail if rosbag not recording
    # exit 1
fi

echo "[2/3] Checking bag file sizes..."
# Check bag file sizes
if [ -d "$BAG_DIR" ]; then
    BAG_COUNT=$(ls -1 "$BAG_DIR"/*.bag 2>/dev/null | wc -l)
    if [ $BAG_COUNT -gt 0 ]; then
        echo "  ✓ Found $BAG_COUNT bag file(s):"
        for bag in "$BAG_DIR"/*.bag; do
            if [ -f "$bag" ]; then
                size=$(du -h "$bag" | cut -f1)
                echo "    - $(basename "$bag"): $size"
            fi
        done
    else
        echo "  ⚠ No bag files found in $BAG_DIR"
    fi
else
    echo "  ⚠ Bag directory not found: $BAG_DIR"
fi

echo "[3/3] Checking application logs..."
# Check if log directory exists
if [ -d "$LOG_DIR" ]; then
    LOG_COUNT=$(ls -1 "$LOG_DIR"/*.log 2>/dev/null | wc -l)
    if [ $LOG_COUNT -gt 0 ]; then
        echo "  ✓ Found $LOG_COUNT log file(s)"
    else
        echo "  ⚠ No log files found in $LOG_DIR"
    fi
else
    echo "  ℹ Log directory not found: $LOG_DIR (create if needed)"
fi

echo ""
echo "========================================"
echo " Log test complete"
echo "========================================"

exit 0
