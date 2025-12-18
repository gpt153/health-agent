#!/bin/bash
# Single-instance bot startup script

PIDFILE="/tmp/health-agent-bot.pid"
LOGFILE="logs/bot.log"

# Check if already running
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo "Bot already running (PID: $OLD_PID)"
        exit 1
    else
        echo "Removing stale PID file"
        rm -f "$PIDFILE"
    fi
fi

# Kill any other instances (including root-owned)
sudo pkill -9 -f "python.*src.main" 2>/dev/null
sleep 2

# Start bot
cd /home/samuel/workspace/health-agent
.venv/bin/python -m src.main >> "$LOGFILE" 2>&1 &
NEW_PID=$!

# Save PID
echo $NEW_PID > "$PIDFILE"
echo "Bot started (PID: $NEW_PID)"
echo "Logs: tail -f $LOGFILE"
