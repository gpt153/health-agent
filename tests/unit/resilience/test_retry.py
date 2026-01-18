"""Unit tests for retry logic"""
import pytest
import httpx
from src.resilience.retry import (
    retry_with_backoff,
    with_retry,
    is_retryable_error,
    calculate_backoff,
    MAX_RETRIES,
)


def test_is_retryable_error_timeout():
    """Test that timeout errors are retryable"""
    assert is_retryable_error(httpx.TimeoutException("Timeout")) == True
    assert is_retryable_error(httpx.ConnectTimeout("Connect timeout")) == True
    assert is_retryable_error(httpx.ReadTimeout("Read timeout")) == True


def test_is_retryable_error_http_status():
    """Test that certain HTTP status codes are retryable"""
    # Create mock responses
    retryable_codes = [429, 500, 502, 503, 504]
    non_retryable_codes = [400, 401, 403, 404, 422]

    for code in retryable_codes:
        response = httpx.Response(code)
        error = httpx.HTTPStatusError("Error", request=None, response=response)
        assert is_retryable_error(error) == True, f"HTTP {code} should be retryable"

    for code in non_retryable_codes:
        response = httpx.Response(code)
        error = httpx.HTTPStatusError("Error", request=None, response=response)
        assert is_retryable_error(error) == False, f"HTTP {code} should not be retryable"


def test_is_retryable_error_non_retryable():
    """Test that non-retryable errors are identified correctly"""
    # Generic exceptions should not be retried
    assert is_retryable_error(ValueError("Bad value")) == False
    assert is_retryable_error(KeyError("Missing key")) == False
    assert is_retryable_error(TypeError("Type error")) == False


def test_calculate_backoff():
    """Test exponential backoff calculation"""
    # First attempt: ~1s
    delay_0 = calculate_backoff(0)
    assert 0.9 <= delay_0 <= 1.1  # 1s ± 10% jitter

    # Second attempt: ~2s
    delay_1 = calculate_backoff(1)
    assert 1.8 <= delay_1 <= 2.2  # 2s ± 10% jitter

    # Third attempt: ~4s
    delay_2 = calculate_backoff(2)
    assert 3.6 <= delay_2 <= 4.4  # 4s ± 10% jitter

    # Fourth attempt: ~8s
    delay_3 = calculate_backoff(3)
    assert 7.2 <= delay_3 <= 8.8  # 8s ± 10% jitter

    # Verify exponential growth
    assert delay_1 > delay_0
    assert delay_2 > delay_1
    assert delay_3 > delay_2


def test_calculate_backoff_max_delay():
    """Test that backoff respects max delay"""
    # Very high attempt number should cap at MAX_DELAY (30s)
    delay = calculate_backoff(20)
    assert delay <= 33.0  # 30s + 10% jitter


@pytest.mark.asyncio
async def test_retry_with_backoff_success_first_try():
    """Test that function succeeds on first try"""

    call_count = 0

    async def successful_function():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await retry_with_backoff(successful_function, max_retries=3)

    assert result == "success"
    assert call_count == 1  # Should only be called once


@pytest.mark.asyncio
async def test_retry_with_backoff_success_after_retries():
    """Test that function succeeds after some retries"""

    attempt = 0

    async def flaky_function():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise httpx.TimeoutException("Simulated timeout")
        return "success"

    result = await retry_with_backoff(flaky_function, max_retries=3)

    assert result == "success"
    assert attempt == 3  # Should succeed on 3rd attempt


@pytest.mark.asyncio
async def test_retry_with_backoff_exhausted():
    """Test that retries are exhausted for persistent failures"""

    attempt = 0

    async def always_fails():
        nonlocal attempt
        attempt += 1
        raise httpx.TimeoutException("Always fails")

    with pytest.raises(httpx.TimeoutException, match="Always fails"):
        await retry_with_backoff(always_fails, max_retries=3)

    # Should be called 4 times (initial + 3 retries)
    assert attempt == 4


@pytest.mark.asyncio
async def test_retry_with_backoff_non_retryable_error():
    """Test that non-retryable errors are not retried"""

    attempt = 0

    async def non_retryable_function():
        nonlocal attempt
        attempt += 1
        raise ValueError("Non-retryable error")

    with pytest.raises(ValueError, match="Non-retryable error"):
        await retry_with_backoff(non_retryable_function, max_retries=3)

    # Should only be called once (no retries)
    assert attempt == 1


@pytest.mark.asyncio
async def test_with_retry_decorator():
    """Test that @with_retry decorator works correctly"""

    attempt = 0

    @with_retry(max_retries=2)
    async def flaky_function():
        nonlocal attempt
        attempt += 1
        if attempt < 2:
            raise httpx.TimeoutException("Flaky error")
        return "success"

    result = await flaky_function()

    assert result == "success"
    assert attempt == 2


@pytest.mark.asyncio
async def test_with_retry_decorator_exhausted():
    """Test that decorator respects max_retries limit"""

    attempt = 0

    @with_retry(max_retries=2)
    async def always_fails():
        nonlocal attempt
        attempt += 1
        raise httpx.TimeoutException("Always fails")

    with pytest.raises(httpx.TimeoutException):
        await always_fails()

    # Should be called 3 times (initial + 2 retries)
    assert attempt == 3


@pytest.mark.asyncio
async def test_retry_with_http_429_rate_limit():
    """Test that HTTP 429 rate limit errors are retried"""

    attempt = 0

    async def rate_limited_function():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            response = httpx.Response(429)
            raise httpx.HTTPStatusError("Rate limited", request=None, response=response)
        return "success"

    result = await retry_with_backoff(rate_limited_function, max_retries=3)

    assert result == "success"
    assert attempt == 3


@pytest.mark.asyncio
async def test_retry_with_http_500_server_error():
    """Test that HTTP 500 server errors are retried"""

    attempt = 0

    async def server_error_function():
        nonlocal attempt
        attempt += 1
        if attempt < 2:
            response = httpx.Response(500)
            raise httpx.HTTPStatusError("Internal server error", request=None, response=response)
        return "success"

    result = await retry_with_backoff(server_error_function, max_retries=3)

    assert result == "success"
    assert attempt == 2


@pytest.mark.asyncio
async def test_retry_with_http_401_unauthorized():
    """Test that HTTP 401 unauthorized errors are not retried"""

    attempt = 0

    async def unauthorized_function():
        nonlocal attempt
        attempt += 1
        response = httpx.Response(401)
        raise httpx.HTTPStatusError("Unauthorized", request=None, response=response)

    with pytest.raises(httpx.HTTPStatusError, match="Unauthorized"):
        await retry_with_backoff(unauthorized_function, max_retries=3)

    # Should only be called once (not retried)
    assert attempt == 1


@pytest.mark.asyncio
async def test_retry_preserves_function_args():
    """Test that retry logic preserves function arguments"""

    async def function_with_args(x, y, z=10):
        return x + y + z

    result = await retry_with_backoff(function_with_args, 5, 3, z=7, max_retries=2)

    assert result == 15  # 5 + 3 + 7


def test_default_max_retries():
    """Test that default MAX_RETRIES is set correctly"""
    assert MAX_RETRIES == 3
