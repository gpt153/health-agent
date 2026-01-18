"""
Endurance Load Test Scenario

Simulates sustained production load:
- 50 concurrent users
- 60-minute duration
- Gradual spawn (5 users/sec)

Purpose: Test system stability over extended period
- Memory leaks detection
- Connection pool exhaustion
- Cache performance over time

Target: P95 < 3s throughout, no degradation over time
"""

import os

# Locust configuration
LOCUSTFILE = os.path.join(os.path.dirname(__file__), "..", "locustfile.py")
HOST = os.getenv("LOAD_TEST_HOST", "http://localhost:8000")

# Test parameters
USERS = 50
SPAWN_RATE = 5  # users/second
RUN_TIME = "60m"

# Success criteria
MAX_P95_MS = 3000  # 3 seconds
MAX_FAILURE_RATE = 1.0  # 1%

# Locust command
COMMAND = [
    "locust",
    "-f", LOCUSTFILE,
    "--host", HOST,
    "--users", str(USERS),
    "--spawn-rate", str(SPAWN_RATE),
    "--run-time", RUN_TIME,
    "--headless",
    "--only-summary",
    "--html", "load_tests/results/endurance_test_report.html",
    "--csv", "load_tests/results/endurance_test",
]

SCENARIO_NAME = "Endurance Test"
DESCRIPTION = f"{USERS} users over {RUN_TIME} (spawn rate: {SPAWN_RATE}/s)"
