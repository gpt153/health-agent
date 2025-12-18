#!/bin/bash
# Restart health-agent bot safely without affecting other bots

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🔍 Finding health-agent bot process..."
PID=$("$SCRIPT_DIR/get_bot_pid.sh")

if [ ! -z "$PID" ]; then
    echo "🛑 Stopping health-agent bot (PID: $PID)..."
    kill -9 $PID
    sleep 2
else
    echo "ℹ️  No running health-agent bot found"
fi

echo "🚀 Starting health-agent bot..."
nohup .venv/bin/python -m src.main >> logs/bot.log 2>&1 &

sleep 3

NEW_PID=$("$SCRIPT_DIR/get_bot_pid.sh")

if [ ! -z "$NEW_PID" ]; then
    echo "✅ Health-agent bot started successfully (PID: $NEW_PID)"
else
    echo "❌ Failed to start health-agent bot"
    tail -20 logs/bot.log
    exit 1
fi
