#!/bin/bash
# Start health-agent bot

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Check if already running
PID=$("$SCRIPT_DIR/get_bot_pid.sh")
if [ ! -z "$PID" ]; then
    echo "⚠️  Health-agent bot is already running (PID: $PID)!"
    exit 1
fi

echo "🚀 Starting health-agent bot..."
nohup .venv/bin/python -m src.main >> logs/bot.log 2>&1 &

sleep 3

PID=$("$SCRIPT_DIR/get_bot_pid.sh")
if [ ! -z "$PID" ]; then
    echo "✅ Health-agent bot started successfully (PID: $PID)"
else
    echo "❌ Failed to start health-agent bot"
    echo "Check logs/bot.log for errors"
    tail -20 logs/bot.log
    exit 1
fi
