#!/bin/bash
PIDFILE="/tmp/health-agent-bot.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    echo "Stopping bot (PID: $PID)..."
    kill -9 "$PID" 2>/dev/null
    rm -f "$PIDFILE"
    echo "✓ Bot stopped"
else
    echo "No PID file found"
    pkill -9 -f "python.*src.main" 2>/dev/null && echo "✓ Killed running instances"
fi
