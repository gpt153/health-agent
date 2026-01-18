"""Unit tests for circuit breaker functionality"""
import pytest
import pybreaker
from src.resilience.circuit_breaker import (
    OPENAI_BREAKER,
    ANTHROPIC_BREAKER,
    USDA_BREAKER,
    with_circuit_breaker,
    CircuitBreakerListener,
)


@pytest.fixture(autouse=True)
def reset_circuit_breakers():
    """Reset all circuit breakers before each test"""
    for breaker in [OPENAI_BREAKER, ANTHROPIC_BREAKER, USDA_BREAKER]:
        breaker._state = pybreaker.STATE_CLOSED
        breaker._failure_count = 0
    yield


@pytest.mark.asyncio
async def test_circuit_breaker_closes_on_success():
    """Test that circuit breaker remains CLOSED when calls succeed"""

    @with_circuit_breaker(OPENAI_BREAKER)
    async def successful_function():
        return "success"

    # Make 10 successful calls
    for _ in range(10):
        result = await successful_function()
        assert result == "success"

    # Circuit should still be CLOSED
    assert OPENAI_BREAKER.current_state == pybreaker.STATE_CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Test that circuit breaker opens after threshold failures"""

    @with_circuit_breaker(ANTHROPIC_BREAKER)
    async def failing_function():
        raise Exception("Simulated failure")

    # Trigger 5 failures (threshold)
    for i in range(5):
        with pytest.raises(Exception, match="Simulated failure"):
            await failing_function()

    # Circuit should now be OPEN
    assert ANTHROPIC_BREAKER.current_state == pybreaker.STATE_OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_fails_fast_when_open():
    """Test that circuit breaker fails fast when OPEN"""

    @with_circuit_breaker(USDA_BREAKER)
    async def failing_function():
        raise Exception("Simulated failure")

    # Trigger failures to open circuit
    for _ in range(5):
        with pytest.raises(Exception):
            await failing_function()

    # Circuit is now OPEN
    assert USDA_BREAKER.current_state == pybreaker.STATE_OPEN

    # Next call should fail immediately with CircuitBreakerError
    with pytest.raises(pybreaker.CircuitBreakerError):
        await failing_function()


@pytest.mark.asyncio
async def test_circuit_breaker_decorator():
    """Test that circuit breaker decorator works correctly"""

    call_count = 0

    @with_circuit_breaker(OPENAI_BREAKER)
    async def tracked_function():
        nonlocal call_count
        call_count += 1
        return "success"

    # Call function 3 times
    for _ in range(3):
        await tracked_function()

    # Verify function was called 3 times
    assert call_count == 3


@pytest.mark.asyncio
async def test_circuit_breaker_mixed_results():
    """Test circuit breaker with mixed success/failure results"""

    attempt = 0

    @with_circuit_breaker(ANTHROPIC_BREAKER)
    async def flaky_function():
        nonlocal attempt
        attempt += 1
        # Fail on attempts 1, 3, 5, 7 (4 failures total, below threshold)
        if attempt % 2 == 1:
            raise Exception("Flaky error")
        return "success"

    # Run 8 attempts (4 failures, 4 successes)
    for i in range(8):
        if i % 2 == 0:  # Even attempts (0, 2, 4, 6) should fail
            with pytest.raises(Exception, match="Flaky error"):
                await flaky_function()
        else:  # Odd attempts (1, 3, 5, 7) should succeed
            result = await flaky_function()
            assert result == "success"

    # Circuit should still be CLOSED (successes reset failure count)
    assert ANTHROPIC_BREAKER.current_state == pybreaker.STATE_CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_listener_state_change():
    """Test that circuit breaker listener logs state changes"""

    listener = CircuitBreakerListener()
    state_changes = []

    # Mock the state_change method to track calls
    original_state_change = listener.state_change

    def tracked_state_change(cb, old_state, new_state):
        state_changes.append((old_state.name, new_state.name))
        original_state_change(cb, old_state, new_state)

    listener.state_change = tracked_state_change

    # Create a test circuit breaker with our listener
    test_breaker = pybreaker.CircuitBreaker(
        fail_max=2,
        timeout_duration=1,
        name="test_breaker",
        listeners=[listener]
    )

    @with_circuit_breaker(test_breaker)
    async def failing_function():
        raise Exception("Test failure")

    # Trigger 2 failures to open circuit
    for _ in range(2):
        with pytest.raises(Exception):
            await failing_function()

    # Verify state change was logged (CLOSED -> OPEN)
    assert len(state_changes) >= 1
    # The last state change should be to OPEN
    assert state_changes[-1][1] == "OPEN"


def test_circuit_breaker_configuration():
    """Test that circuit breakers are configured correctly"""

    # Test OPENAI_BREAKER configuration
    assert OPENAI_BREAKER.name == "openai_api"
    assert OPENAI_BREAKER.fail_max == 5
    assert OPENAI_BREAKER.timeout_duration == 60

    # Test ANTHROPIC_BREAKER configuration
    assert ANTHROPIC_BREAKER.name == "anthropic_api"
    assert ANTHROPIC_BREAKER.fail_max == 5
    assert ANTHROPIC_BREAKER.timeout_duration == 60

    # Test USDA_BREAKER configuration
    assert USDA_BREAKER.name == "usda_api"
    assert USDA_BREAKER.fail_max == 5
    assert USDA_BREAKER.timeout_duration == 60


@pytest.mark.asyncio
async def test_circuit_breaker_listener_failure():
    """Test that circuit breaker listener tracks failures"""

    listener = CircuitBreakerListener()
    failures = []

    # Mock the failure method to track calls
    original_failure = listener.failure

    def tracked_failure(cb, exc):
        failures.append(exc)
        original_failure(cb, exc)

    listener.failure = tracked_failure

    # Create a test circuit breaker with our listener
    test_breaker = pybreaker.CircuitBreaker(
        fail_max=3,
        timeout_duration=1,
        name="test_breaker",
        listeners=[listener]
    )

    @with_circuit_breaker(test_breaker)
    async def failing_function():
        raise ValueError("Test error")

    # Trigger 3 failures
    for _ in range(3):
        with pytest.raises(ValueError):
            await failing_function()

    # Verify failures were tracked
    assert len(failures) == 3
    assert all(isinstance(f, ValueError) for f in failures)


@pytest.mark.asyncio
async def test_circuit_breaker_listener_success():
    """Test that circuit breaker listener tracks successes"""

    listener = CircuitBreakerListener()
    successes = []

    # Mock the success method to track calls
    original_success = listener.success

    def tracked_success(cb):
        successes.append(True)
        original_success(cb)

    listener.success = tracked_success

    # Create a test circuit breaker with our listener
    test_breaker = pybreaker.CircuitBreaker(
        fail_max=5,
        timeout_duration=60,
        name="test_breaker",
        listeners=[listener]
    )

    @with_circuit_breaker(test_breaker)
    async def successful_function():
        return "success"

    # Make 5 successful calls
    for _ in range(5):
        await successful_function()

    # Verify successes were tracked
    assert len(successes) == 5
