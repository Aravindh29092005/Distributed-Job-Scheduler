"""Retry strategy implementations (Strategy Pattern).

Each strategy computes the delay (in milliseconds) before the next attempt.
Callers select a strategy via RetryPolicy.strategy and never use if/else.

Usage::

    from backend.retry import get_strategy

    strategy = get_strategy(policy.strategy)
    delay_ms = strategy.next_delay_ms(
        attempt=job.current_attempt,
        initial_delay_ms=policy.initial_delay_ms,
        max_delay_ms=policy.max_delay_ms,
        multiplier=policy.multiplier,
        jitter_factor=policy.jitter_factor,
    )
"""
from backend.retry.strategies import (
    RetryStrategy,
    FixedDelay,
    LinearBackoff,
    ExponentialBackoff,
    ExponentialBackoffWithJitter,
    get_strategy,
)

__all__ = [
    "RetryStrategy",
    "FixedDelay",
    "LinearBackoff",
    "ExponentialBackoff",
    "ExponentialBackoffWithJitter",
    "get_strategy",
]
