"""
Steady Load Test Scenario

Simulates normal production load:
- 100 concurrent users
- 10-minute duration
- Gradual spawn (10 users/sec)

Target: P95 < 3s, errors < 1%
"""

import os

# Locust configuration
LOCUSTFILE = os.path.join(os.path.dirname(__file__), "..", "locustfile.py")
HOST = os.getenv("LOAD_TEST_HOST", "http://localhost:8000")

# Test parameters
USERS = 100
SPAWN_RATE = 10  # users/second
RUN_TIME = "10m"

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
    "--html", "load_tests/results/steady_load_report.html",
    "--csv", "load_tests/results/steady_load",
]

SCENARIO_NAME = "Steady Load"
DESCRIPTION = f"{USERS} users over {RUN_TIME} (spawn rate: {SPAWN_RATE}/s)"
