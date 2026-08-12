"""HTTP-library-independent asynchronous retries."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    maximum_attempts: int = 3
    initial_delay_seconds: float = 0.5
    multiplier: float = 2.0
    maximum_delay_seconds: float = 10.0


async def retry_async[T](
    operation: Callable[[], Awaitable[T]],
    policy: RetryPolicy | None = None,
    retryable: Callable[[Exception], bool] | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Run an async operation with deterministic exponential backoff."""
    policy = policy or RetryPolicy()
    retryable = retryable or (lambda _exc: True)
    if policy.maximum_attempts < 1:
        raise ValueError("maximum_attempts must be positive")
    delay = policy.initial_delay_seconds
    for attempt in range(1, policy.maximum_attempts + 1):
        try:
            return await operation()
        except Exception as exc:
            if attempt == policy.maximum_attempts or not retryable(exc):
                raise
            await sleep(delay)
            delay = min(delay * policy.multiplier, policy.maximum_delay_seconds)
    raise RuntimeError("unreachable")
