"""
Locust load testing configuration for health agent API.

Simulates realistic user behavior:
- Text messages (50%)
- Food logging (20%)
- Reminders (20%)
- Gamification (10%)

Target: 100 concurrent users, P95 < 3s
"""

import random
import json
from locust import HttpUser, task, between, events
from locust.exception import StopUser


class HealthAgentUser(HttpUser):
    """
    Simulates a health agent user interacting with the API.

    Realistic behavior:
    - Wait 5-15 seconds between requests (human-like)
    - Mix of different operation types
    - Persistent user context across requests
    """

    wait_time = between(5, 15)  # Realistic pause between actions

    def on_start(self):
        """Initialize user session"""
        # Unique user ID for this load test user
        self.user_id = f"loadtest_user_{random.randint(1000, 999999)}"
        self.api_key = "test_key_123"  # From .env.example

        # Track request count for this user
        self.request_count = 0

        # Headers for all requests
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    @task(5)  # Weight: 50% (5/10)
    def send_text_message(self):
        """
        Send a text message to the agent.

        Simulates common user queries.
        """
        messages = [
            "How many calories did I eat today?",
            "What did I log yesterday?",
            "Show my progress",
            "What's my streak?",
            "How am I doing with my goals?",
            "What should I eat for lunch?",
            "Did I take my vitamins?",
            "Show me my nutrition summary",
        ]

        with self.client.post(
            "/api/v1/chat",
            json={
                "user_id": self.user_id,
                "message": random.choice(messages)
            },
            headers=self.headers,
            catch_response=True,
            name="Text Message"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

        self.request_count += 1
        self._check_request_limit()

    @task(2)  # Weight: 20% (2/10)
    def log_food(self):
        """
        Log a food entry.

        Simulates food logging behavior.
        """
        foods = [
            {"name": "chicken breast", "quantity": "170g"},
            {"name": "rice", "quantity": "200g"},
            {"name": "banana", "quantity": "1 medium"},
            {"name": "apple", "quantity": "1 large"},
            {"name": "egg", "quantity": "2 whole"},
            {"name": "salmon", "quantity": "150g"},
        ]

        food = random.choice(foods)

        with self.client.post(
            "/api/v1/food",
            json={
                "user_id": self.user_id,
                "food_name": food["name"],
                "quantity": food["quantity"]
            },
            headers=self.headers,
            catch_response=True,
            name="Log Food"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

        self.request_count += 1
        self._check_request_limit()

    @task(2)  # Weight: 20% (2/10)
    def get_reminders(self):
        """
        Fetch active reminders.

        Simulates checking reminders.
        """
        with self.client.get(
            f"/api/v1/reminders?user_id={self.user_id}",
            headers=self.headers,
            catch_response=True,
            name="Get Reminders"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

        self.request_count += 1
        self._check_request_limit()

    @task(1)  # Weight: 10% (1/10)
    def check_gamification(self):
        """
        Check XP and achievements.

        Simulates checking gamification stats.
        """
        with self.client.get(
            f"/api/v1/gamification/xp?user_id={self.user_id}",
            headers=self.headers,
            catch_response=True,
            name="Check XP"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

        self.request_count += 1
        self._check_request_limit()

    def _check_request_limit(self):
        """
        Stop user after 50 requests (simulates 10-minute session).

        From issue requirements: "50 messages over 10 minutes"
        """
        if self.request_count >= 50:
            raise StopUser()


# Event listeners for custom metrics

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log when load test starts"""
    print("\n" + "="*80)
    print("🚀 LOAD TEST STARTING")
    print("="*80)
    print(f"Target: {environment.parsed_options.num_users} concurrent users")
    print(f"Spawn rate: {environment.parsed_options.spawn_rate} users/sec")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log final statistics when test completes"""
    print("\n" + "="*80)
    print("✅ LOAD TEST COMPLETE")
    print("="*80)

    stats = environment.stats

    print("\n📊 FINAL STATISTICS:")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Failure rate: {stats.total.fail_ratio * 100:.2f}%")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"P50: {stats.total.get_response_time_percentile(0.5):.2f}ms")
    print(f"P95: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"P99: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"RPS: {stats.total.total_rps:.2f}")

    print("\n" + "="*80)

    # Check if test met success criteria
    p95_ms = stats.total.get_response_time_percentile(0.95)
    p95_s = p95_ms / 1000
    failure_rate = stats.total.fail_ratio * 100

    print("\n🎯 SUCCESS CRITERIA:")
    print(f"  P95 < 3s: {'✅ PASS' if p95_s < 3 else '❌ FAIL'} ({p95_s:.2f}s)")
    print(f"  Errors < 1%: {'✅ PASS' if failure_rate < 1 else '❌ FAIL'} ({failure_rate:.2f}%)")
    print("="*80 + "\n")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """
    Log slow requests in real-time.

    Helps identify performance issues during the test.
    """
    if response_time > 3000:  # > 3 seconds
        print(f"⚠️  SLOW REQUEST: {name} took {response_time:.2f}ms")
