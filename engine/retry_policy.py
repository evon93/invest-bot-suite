"""
engine/retry_policy.py

Deterministic retry/backoff policy for execution calls.
Supports hash-based jitter for determinism without random().
"""

from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple, TypeVar

T = TypeVar("T")


@dataclass
class RetryPolicy:
    """
    Retry policy with deterministic backoff.
    
    Attributes:
        max_attempts: Maximum number of attempts (including first try)
        base_delay_ms: Base delay in milliseconds
        max_delay_ms: Maximum delay cap in milliseconds
        multiplier: Exponential backoff multiplier
        jitter_mode: "none" for pure exponential, "hash" for deterministic jitter
    """
    max_attempts: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000
    multiplier: float = 2.0
    jitter_mode: str = "none"  # "none" | "hash"
    
    def compute_delay_ms(self, attempt_idx: int, op_key: Optional[str] = None) -> int:
        """
        Compute delay for given attempt index.
        
        Args:
            attempt_idx: 0-indexed attempt number (0 = first retry after failure)
            op_key: Operation key for hash-based jitter (required if jitter_mode="hash")
            
        Returns:
            Delay in milliseconds
        """
        # Base exponential backoff
        raw_delay = self.base_delay_ms * (self.multiplier ** attempt_idx)
        delay = min(int(raw_delay), self.max_delay_ms)
        
        if self.jitter_mode == "hash" and op_key:
            # Deterministic jitter via hash
            # Hash the op_key + attempt_idx to get a deterministic "random" value
            hash_input = f"{op_key}:{attempt_idx}".encode("utf-8")
            hash_bytes = hashlib.sha256(hash_input).digest()
            # Use first 4 bytes as unsigned int
            hash_int = int.from_bytes(hash_bytes[:4], "big")
            # Jitter: add 0-25% of delay
            jitter_range = max(1, delay // 4)
            jitter = hash_int % jitter_range
            delay = delay + jitter
        
        return min(delay, self.max_delay_ms)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, last_exception: Exception, attempts: int):
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(f"Retry exhausted after {attempts} attempts: {last_exception}")


def retry_call(
    fn: Callable[[], T],
    *,
    is_retryable_exc: Callable[[Exception], bool],
    policy: RetryPolicy,
    op_key: str,
    sleep_fn: Callable[[int], None] = lambda ms: None,
) -> Tuple[T, int]:
    """
    Execute function with retry logic.
    
    Args:
        fn: Function to execute (no arguments)
        is_retryable_exc: Predicate to check if exception is retryable
        policy: RetryPolicy configuration
        op_key: Operation key for deterministic jitter
        sleep_fn: Sleep function (ms) - defaults to no-op for tests
        
    Returns:
        Tuple of (result, attempts_used) where attempts_used is 1-indexed
        
    Raises:
        RetryExhaustedError: If all attempts fail with retryable exceptions
        Exception: If a non-retryable exception occurs
    """
    last_exception: Optional[Exception] = None
    
    for attempt in range(policy.max_attempts):
        try:
            result = fn()
            return (result, attempt + 1)
        except Exception as e:
            if not is_retryable_exc(e):
                # Non-retryable: propagate immediately
                raise
            
            last_exception = e
            
            # Check if more attempts remaining
            if attempt + 1 >= policy.max_attempts:
                break
            
            # Compute and apply delay before next attempt
            delay_ms = policy.compute_delay_ms(attempt, op_key)
            if delay_ms > 0:
                sleep_fn(delay_ms)
    
    # All attempts exhausted
    raise RetryExhaustedError(last_exception, policy.max_attempts)
