#!/bin/bash
# Stop health-agent bot safely

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🔍 Finding health-agent bot process..."
PID=$("$SCRIPT_DIR/get_bot_pid.sh")

if [ -z "$PID" ]; then
    echo "ℹ️  No running health-agent bot found"
    exit 0
fi

echo "🛑 Stopping health-agent bot (PID: $PID)..."
kill -9 $PID
sleep 2

# Verify it stopped
NEW_PID=$("$SCRIPT_DIR/get_bot_pid.sh")
if [ ! -z "$NEW_PID" ]; then
    echo "❌ Failed to stop health-agent bot"
    exit 1
else
    echo "✅ Health-agent bot stopped successfully"
fi
