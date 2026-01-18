"""
Spike Load Test Scenario

Simulates sudden traffic spike:
- 0 → 200 concurrent users in 1 minute
- 5-minute duration total
- Aggressive spawn (200 users/min = ~3.3 users/sec)

Purpose: Test system resilience under sudden load increase
Target: System remains stable, no crashes
"""

import os

# Locust configuration
LOCUSTFILE = os.path.join(os.path.dirname(__file__), "..", "locustfile.py")
HOST = os.getenv("LOAD_TEST_HOST", "http://localhost:8000")

# Test parameters
USERS = 200
SPAWN_RATE = 200  # Spawn all users in ~1 second (aggressive spike)
RUN_TIME = "5m"

# Success criteria (more lenient for spike test)
MAX_P95_MS = 5000  # 5 seconds (higher threshold for spike)
MAX_FAILURE_RATE = 5.0  # 5% (allow some failures during spike)

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
    "--html", "load_tests/results/spike_test_report.html",
    "--csv", "load_tests/results/spike_test",
]

SCENARIO_NAME = "Spike Test"
DESCRIPTION = f"0 → {USERS} users (instant spike), {RUN_TIME} duration"
