#!/usr/bin/env python3
"""Ensure only one bot instance runs"""
import os
import sys
import time
import signal
import psutil
from pathlib import Path

LOCKFILE = "/tmp/health-agent.lock"
PIDFILE = "/tmp/health-agent.pid"

def kill_existing():
    """Kill any existing bot processes"""
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'python' in cmdline and 'src.main' in cmdline:
                print(f"Killing existing process: {proc.info['pid']}")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(2)

def main():
    # Check if already running
    if Path(PIDFILE).exists():
        try:
            old_pid = int(Path(PIDFILE).read_text().strip())
            if psutil.pid_exists(old_pid):
                print(f"Bot already running (PID: {old_pid})")
                sys.exit(1)
        except:
            pass

    # Kill any strays
    kill_existing()

    # Start new instance
    os.chdir('/home/samuel/workspace/health-agent')
    pid = os.fork()

    if pid == 0:
        # Child process - run the bot
        Path(PIDFILE).write_text(str(os.getpid()))
        os.execv('.venv/bin/python', ['.venv/bin/python', '-m', 'src.main'])
    else:
        # Parent - just exit
        print(f"Bot started (PID: {pid})")
        print(f"Logs: tail -f logs/bot.log")

if __name__ == '__main__':
    main()
