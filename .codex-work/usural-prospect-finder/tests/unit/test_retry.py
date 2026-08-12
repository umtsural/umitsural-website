import asyncio

import pytest

from usural_prospect_finder.utils.retry import RetryPolicy, retry_async


def test_retry_uses_deterministic_backoff_without_real_sleep() -> None:
    attempts = 0
    delays: list[float] = []

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError
        return "ok"

    async def sleep(delay: float) -> None:
        delays.append(delay)

    result = asyncio.run(retry_async(operation, RetryPolicy(3, 0.25, 2, 10), sleep=sleep))
    assert result == "ok"
    assert attempts == 3
    assert delays == [0.25, 0.5]


def test_non_retryable_error_stops_immediately() -> None:
    attempts = 0

    async def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise ValueError("stop")

    with pytest.raises(ValueError, match="stop"):
        asyncio.run(retry_async(operation, retryable=lambda _error: False))
    assert attempts == 1
