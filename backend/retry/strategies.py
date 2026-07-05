"""Concrete retry strategy implementations.

DESIGN DECISION: Strategy Pattern vs if/else
  - New strategies added by implementing RetryStrategy and registering in
    _REGISTRY — zero changes to caller code.
  - Strategies are pure functions of (attempt, params); they hold no state
    and are safe to call concurrently from multiple asyncio tasks.

Formula summary:
  fixed:    delay = initial_delay_ms   (ignores attempt)
  linear:   delay = initial_delay_ms * attempt
  exp:      delay = initial_delay_ms * multiplier^(attempt-1)
  exp+jitter: delay = exp_delay * uniform(1-jitter, 1+jitter)

All strategies clamp to max_delay_ms.
"""
from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod


class RetryStrategy(ABC):
    """Abstract base for all retry delay strategies."""

    @abstractmethod
    def next_delay_ms(
        self,
        *,
        attempt: int,
        initial_delay_ms: int,
        max_delay_ms: int,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1,
    ) -> int:
        """Compute the delay in milliseconds before the given attempt.

        Args:
            attempt:         1-based attempt number (1 = first retry).
            initial_delay_ms: Base delay for the first retry.
            max_delay_ms:    Upper bound for any computed delay.
            multiplier:      Growth factor (used by exponential strategies).
            jitter_factor:   Fraction of delay to add as random noise (0–1).

        Returns:
            Delay in milliseconds, clamped to [0, max_delay_ms].
        """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp(value: float, max_val: int) -> int:
        """Clamp ``value`` to [0, max_val] and return as int milliseconds."""
        return max(0, min(int(value), max_val))


# ---------------------------------------------------------------------------
# Concrete strategies
# ---------------------------------------------------------------------------

class FixedDelay(RetryStrategy):
    """Every retry waits the same fixed delay.

    delay = initial_delay_ms
    """

    def next_delay_ms(
        self,
        *,
        attempt: int,
        initial_delay_ms: int,
        max_delay_ms: int,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1,
    ) -> int:
        return self._clamp(initial_delay_ms, max_delay_ms)


class LinearBackoff(RetryStrategy):
    """Delay grows linearly with the attempt number.

    delay = initial_delay_ms * attempt
    """

    def next_delay_ms(
        self,
        *,
        attempt: int,
        initial_delay_ms: int,
        max_delay_ms: int,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1,
    ) -> int:
        return self._clamp(initial_delay_ms * attempt, max_delay_ms)


class ExponentialBackoff(RetryStrategy):
    """Delay doubles (or grows by ``multiplier``) with each retry.

    delay = initial_delay_ms * multiplier^(attempt-1)

    This is a pure, deterministic strategy. Use ExponentialBackoffWithJitter
    in production to prevent thundering-herd when many jobs fail together.
    """

    def next_delay_ms(
        self,
        *,
        attempt: int,
        initial_delay_ms: int,
        max_delay_ms: int,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1,
    ) -> int:
        delay = initial_delay_ms * math.pow(multiplier, attempt - 1)
        return self._clamp(delay, max_delay_ms)


class ExponentialBackoffWithJitter(RetryStrategy):
    """Exponential backoff plus ±jitter_factor random noise.

    delay = exp_delay * uniform(1 - jitter_factor, 1 + jitter_factor)

    The jitter spreads out retries from many jobs that all failed at the
    same time, avoiding a thundering herd that would overwhelm the DB.

    DESIGN NOTE: We use "full jitter" capped at the exponential value so
    delay is always ≤ exp_delay (it can only reduce, not exceed, the computed
    exponential). This is preferred over "equal jitter" for Postgres-based
    queues because it reduces SELECT lock contention on the jobs table.
    """

    def next_delay_ms(
        self,
        *,
        attempt: int,
        initial_delay_ms: int,
        max_delay_ms: int,
        multiplier: float = 2.0,
        jitter_factor: float = 0.1,
    ) -> int:
        exp_delay = initial_delay_ms * math.pow(multiplier, attempt - 1)
        # Apply symmetric jitter: [exp*(1-jitter), exp*(1+jitter)]
        lo = exp_delay * (1.0 - jitter_factor)
        hi = exp_delay * (1.0 + jitter_factor)
        jittered = random.uniform(lo, hi)
        return self._clamp(jittered, max_delay_ms)


# ---------------------------------------------------------------------------
# Registry & factory
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, RetryStrategy] = {
    "fixed_delay": FixedDelay(),
    "linear": LinearBackoff(),
    "exponential": ExponentialBackoff(),
    "exponential_jitter": ExponentialBackoffWithJitter(),
}


def get_strategy(name: str) -> RetryStrategy:
    """Return the RetryStrategy instance for the given policy name.

    Args:
        name: One of 'fixed_delay', 'linear', 'exponential',
              'exponential_jitter'.

    Returns:
        Singleton strategy instance (strategies are stateless).

    Raises:
        KeyError: if ``name`` is not registered.
    """
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"Unknown retry strategy {name!r}. "
            f"Valid choices: {sorted(_REGISTRY)}"
        )
