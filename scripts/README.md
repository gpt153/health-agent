# Health-Agent Bot Management Scripts

These scripts safely manage the health-agent bot **without interfering** with other bots (like remote-coding-agent).

## Problem Solved

Previously, using `pkill -f "python.*src.main"` would accidentally kill BOTH:
- Health-agent bot: `.venv/bin/python -m src.main`
- Remote-coding-agent: `python -m uvicorn src.server.main:app` ❌

These scripts use **working directory detection** to target only the health-agent bot.

## Scripts

### 🔍 `status_bot.sh`
Check if the bot is running and show stats.
```bash
./scripts/status_bot.sh
```

### 🚀 `start_bot.sh`
Start the health-agent bot (fails if already running).
```bash
./scripts/start_bot.sh
```

### 🛑 `stop_bot.sh`
Stop the health-agent bot safely.
```bash
./scripts/stop_bot.sh
```

### 🔄 `restart_bot.sh`
Stop and start the bot in one command.
```bash
./scripts/restart_bot.sh
```

## How It Works

The `get_bot_pid.sh` helper:
1. Finds all `python.*src.main` processes
2. Checks their working directory using `pwdx`
3. Returns only the PID running in `/home/samuel/workspace/health-agent`

This ensures **zero interference** with other Python bots!

## Example Output

```bash
$ ./scripts/status_bot.sh

🔍 Health-Agent Bot Status
==========================
✅ Status: RUNNING

PID: 2029570 | CPU: 0.5% | Memory: 1.4% | Started: Dec16

Log file: /home/samuel/workspace/health-agent/logs/bot.log

Recent activity:
2025-12-17 13:50:55,658 - httpx - INFO - HTTP Request: POST https://api.telegram.org...

==========================
🔍 Other Python Bots Running:
root        1569  0.1  0.0 104532  8040 ?        Ssl  Dec14   4:36 python -m uvicorn src.server.main:app --host 0.0.0.0 --port 8181 --reload
```

## Migration Guide

**Old way (dangerous):**
```bash
sudo pkill -9 -f "python.*src.main"  # ❌ Kills ALL bots!
```

**New way (safe):**
```bash
./scripts/restart_bot.sh  # ✅ Only affects health-agent
```
