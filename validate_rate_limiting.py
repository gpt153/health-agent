#!/usr/bin/env python3
"""
Static validation script for rate limiting implementation
Checks that all endpoints have rate limits applied correctly
"""
import ast
import re
from pathlib import Path

def check_rate_limiting_implementation():
    """Validate rate limiting implementation"""
    print("🔍 Rate Limiting Implementation Validation\n")

    errors = []
    warnings = []
    success = []

    # Check 1: Verify config.py has RATE_LIMIT_STORAGE_URL
    print("1️⃣  Checking config.py...")
    config_path = Path("src/config.py")
    if config_path.exists():
        config_content = config_path.read_text()
        if "RATE_LIMIT_STORAGE_URL" in config_content:
            success.append("✅ config.py: RATE_LIMIT_STORAGE_URL is defined")
        else:
            errors.append("❌ config.py: RATE_LIMIT_STORAGE_URL is missing")
    else:
        errors.append("❌ config.py not found")

    # Check 2: Verify middleware.py imports and uses the config
    print("2️⃣  Checking middleware.py...")
    middleware_path = Path("src/api/middleware.py")
    if middleware_path.exists():
        middleware_content = middleware_path.read_text()
        if "from src.config import RATE_LIMIT_STORAGE_URL" in middleware_content:
            success.append("✅ middleware.py: Imports RATE_LIMIT_STORAGE_URL from config")
        else:
            errors.append("❌ middleware.py: Does not import RATE_LIMIT_STORAGE_URL")

        if "storage_uri=RATE_LIMIT_STORAGE_URL" in middleware_content:
            success.append("✅ middleware.py: Limiter uses storage_uri")
        else:
            errors.append("❌ middleware.py: Limiter does not use storage_uri")
    else:
        errors.append("❌ middleware.py not found")

    # Check 3: Verify routes.py imports limiter
    print("3️⃣  Checking routes.py...")
    routes_path = Path("src/api/routes.py")
    if routes_path.exists():
        routes_content = routes_path.read_text()

        if "from src.api.middleware import limiter" in routes_content:
            success.append("✅ routes.py: Imports limiter from middleware")
        else:
            errors.append("❌ routes.py: Does not import limiter")

        # Check 4: Count endpoints with rate limits
        print("4️⃣  Checking endpoint rate limits...")

        # Find all @limiter.limit decorators
        limit_pattern = r'@limiter\.limit\("(\d+)/minute"\)'
        limits = re.findall(limit_pattern, routes_content)

        # Expected rate limits per endpoint type
        expected_limits = {
            "10": 1,   # Chat endpoint
            "20": 11,  # Food, user, profile, preferences, reminders
            "30": 3,   # XP, streaks, achievements
            "60": 1,   # Health check
        }

        limit_counts = {}
        for limit in limits:
            limit_counts[limit] = limit_counts.get(limit, 0) + 1

        print(f"\n   Found rate limits:")
        for limit, count in sorted(limit_counts.items()):
            print(f"   - {limit}/minute: {count} endpoints")

        # Validate counts
        for limit, expected_count in expected_limits.items():
            actual_count = limit_counts.get(limit, 0)
            if actual_count >= expected_count:
                success.append(f"✅ routes.py: {actual_count} endpoints with {limit}/minute limit")
            elif actual_count > 0:
                warnings.append(f"⚠️  routes.py: Expected {expected_count} endpoints with {limit}/minute, found {actual_count}")
            else:
                errors.append(f"❌ routes.py: No endpoints with {limit}/minute limit found")

        # Check that Request parameter is added to endpoints
        if "fastapi_request: Request" in routes_content:
            success.append("✅ routes.py: Endpoints have Request parameter for rate limiting")
        else:
            errors.append("❌ routes.py: Endpoints missing Request parameter")

    else:
        errors.append("❌ routes.py not found")

    # Check 5: Verify requirements.txt has slowapi
    print("\n5️⃣  Checking requirements.txt...")
    requirements_path = Path("requirements.txt")
    if requirements_path.exists():
        requirements_content = requirements_path.read_text()
        if "slowapi" in requirements_content:
            success.append("✅ requirements.txt: slowapi is present")
        else:
            errors.append("❌ requirements.txt: slowapi is missing")
    else:
        errors.append("❌ requirements.txt not found")

    # Print results
    print("\n" + "="*60)
    print("📋 VALIDATION RESULTS")
    print("="*60)

    if success:
        print(f"\n✅ Success ({len(success)}):")
        for msg in success:
            print(f"   {msg}")

    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for msg in warnings:
            print(f"   {msg}")

    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for msg in errors:
            print(f"   {msg}")

    print("\n" + "="*60)

    if not errors:
        print("✅ VALIDATION PASSED - Rate limiting is properly implemented!")
        print("\n📝 Next steps:")
        print("   1. Start the server: python -m uvicorn src.api.server:app --reload")
        print("   2. Test with curl or run: python test_rate_limiting.py")
        return True
    else:
        print("❌ VALIDATION FAILED - Please fix the errors above")
        return False

if __name__ == "__main__":
    success = check_rate_limiting_implementation()
    exit(0 if success else 1)
