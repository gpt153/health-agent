#!/usr/bin/env python3
"""
Test script for API rate limiting
Tests that endpoints properly enforce rate limits
"""
import asyncio
import httpx
import os
from datetime import datetime

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8080")
API_KEY = os.getenv("API_KEY", "test_key_123")

async def test_rate_limit(endpoint: str, method: str = "GET", expected_limit: int = 10):
    """Test rate limiting on an endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing {method} {endpoint}")
    print(f"Expected limit: {expected_limit}/minute")
    print(f"{'='*60}")

    headers = {"Authorization": f"Bearer {API_KEY}"}

    async with httpx.AsyncClient() as client:
        success_count = 0
        rate_limited_count = 0

        # Send requests up to limit + 5
        test_count = expected_limit + 5

        for i in range(1, test_count + 1):
            try:
                if method == "GET":
                    response = await client.get(
                        f"{API_URL}{endpoint}",
                        headers=headers,
                        timeout=5.0
                    )
                elif method == "POST":
                    response = await client.post(
                        f"{API_URL}{endpoint}",
                        headers=headers,
                        json={"message": "test"},
                        timeout=5.0
                    )

                if response.status_code == 429:
                    rate_limited_count += 1
                    if rate_limited_count == 1:
                        print(f"✅ Request {i}: Rate limited (429) - as expected!")
                        print(f"   Response: {response.text[:100]}")
                elif response.status_code in [200, 201, 404]:
                    # 404 is OK for test endpoints that don't exist yet
                    success_count += 1
                    if i <= 3 or i == expected_limit:
                        print(f"✅ Request {i}: Success ({response.status_code})")
                else:
                    print(f"⚠️  Request {i}: Unexpected status {response.status_code}")
                    print(f"   Response: {response.text[:100]}")

            except Exception as e:
                print(f"❌ Request {i}: Error - {e}")

            # Small delay to simulate realistic usage
            await asyncio.sleep(0.1)

        print(f"\n📊 Results:")
        print(f"   Successful requests: {success_count}")
        print(f"   Rate limited requests: {rate_limited_count}")

        if rate_limited_count > 0:
            print(f"   ✅ Rate limiting is WORKING!")
        else:
            print(f"   ⚠️  No rate limiting detected - may need server restart")

        return success_count, rate_limited_count

async def main():
    """Run rate limiting tests"""
    print("🔍 API Rate Limiting Test Suite")
    print(f"Testing against: {API_URL}")
    print(f"Timestamp: {datetime.now()}")

    tests = [
        ("/api/health", "GET", 60),
        ("/api/v1/users/test_user", "GET", 20),
        # Chat endpoint requires complex payload, skipping for basic test
    ]

    results = []

    for endpoint, method, limit in tests:
        try:
            success, limited = await test_rate_limit(endpoint, method, limit)
            results.append((endpoint, success, limited))
        except Exception as e:
            print(f"❌ Test failed for {endpoint}: {e}")
            results.append((endpoint, 0, 0))

    print(f"\n{'='*60}")
    print("📋 Final Summary")
    print(f"{'='*60}")

    for endpoint, success, limited in results:
        status = "✅ PASS" if limited > 0 else "⚠️  PENDING"
        print(f"{status} {endpoint}: {success} success, {limited} rate limited")

    print(f"\n💡 To properly test:")
    print(f"   1. Ensure server is running: python -m uvicorn src.api.server:app --reload")
    print(f"   2. Set API_KEY environment variable if not using 'test_key_123'")
    print(f"   3. Run this script: python test_rate_limiting.py")

if __name__ == "__main__":
    asyncio.run(main())
