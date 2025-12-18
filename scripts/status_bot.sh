#!/bin/bash
# Check health-agent bot status

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔍 Health-Agent Bot Status"
echo "=========================="

PID=$("$SCRIPT_DIR/get_bot_pid.sh")

if [ -z "$PID" ]; then
    echo "❌ Status: NOT RUNNING"
    exit 1
else
    echo "✅ Status: RUNNING"
    echo ""
    ps aux | grep "^[^ ]* *$PID" | awk '{print "PID:", $2, "| CPU:", $3"%", "| Memory:", $4"%", "| Started:", $9}'
    echo ""
    echo "Log file: $PROJECT_DIR/logs/bot.log"
    echo ""
    echo "Recent activity:"
    tail -5 "$PROJECT_DIR/logs/bot.log" 2>/dev/null || echo "No logs found"
fi

echo ""
echo "=========================="
echo "🔍 Other Python Bots Running:"
for pid in $(pgrep -f "python.*main"); do
    cwd=$(pwdx $pid 2>/dev/null | cut -d' ' -f2)
    if [[ "$cwd" != *"health-agent"* ]]; then
        ps aux | grep "^[^ ]* *$pid" | grep -v grep
    fi
done
