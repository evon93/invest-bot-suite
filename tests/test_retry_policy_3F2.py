"""
tests/test_retry_policy_3F2.py

Tests for engine/retry_policy.py deterministic retry/backoff.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.retry_policy import RetryPolicy, retry_call, RetryExhaustedError


class TestRetryPolicyComputeDelay:
    """Tests for RetryPolicy.compute_delay_ms()."""
    
    def test_deterministic_same_inputs_same_output(self):
        """Same inputs produce same delays (determinism)."""
        policy = RetryPolicy(base_delay_ms=100, multiplier=2.0, jitter_mode="none")
        
        delay1 = policy.compute_delay_ms(attempt_idx=0)
        delay2 = policy.compute_delay_ms(attempt_idx=0)
        delay3 = policy.compute_delay_ms(attempt_idx=0)
        
        assert delay1 == delay2 == delay3
    
    def test_exponential_backoff(self):
        """Delays increase exponentially."""
        policy = RetryPolicy(base_delay_ms=100, multiplier=2.0, max_delay_ms=10000, jitter_mode="none")
        
        delay0 = policy.compute_delay_ms(attempt_idx=0)
        delay1 = policy.compute_delay_ms(attempt_idx=1)
        delay2 = policy.compute_delay_ms(attempt_idx=2)
        
        assert delay0 == 100
        assert delay1 == 200
        assert delay2 == 400
    
    def test_max_delay_cap(self):
        """Delay is capped at max_delay_ms."""
        policy = RetryPolicy(base_delay_ms=100, multiplier=10.0, max_delay_ms=500, jitter_mode="none")
        
        delay0 = policy.compute_delay_ms(attempt_idx=0)  # 100
        delay1 = policy.compute_delay_ms(attempt_idx=1)  # Would be 1000, capped to 500
        delay2 = policy.compute_delay_ms(attempt_idx=2)  # Would be 10000, capped to 500
        
        assert delay0 == 100
        assert delay1 == 500
        assert delay2 == 500
    
    def test_jitter_hash_deterministic_same_key(self):
        """Hash jitter with same op_key and attempt produces same result."""
        policy = RetryPolicy(base_delay_ms=100, jitter_mode="hash")
        
        delay1 = policy.compute_delay_ms(attempt_idx=0, op_key="exec:abc123")
        delay2 = policy.compute_delay_ms(attempt_idx=0, op_key="exec:abc123")
        delay3 = policy.compute_delay_ms(attempt_idx=0, op_key="exec:abc123")
        
        assert delay1 == delay2 == delay3
    
    def test_jitter_hash_varies_by_op_key(self):
        """Different op_keys produce different jitters."""
        policy = RetryPolicy(base_delay_ms=100, jitter_mode="hash")
        
        delay_a = policy.compute_delay_ms(attempt_idx=0, op_key="exec:aaa")
        delay_b = policy.compute_delay_ms(attempt_idx=0, op_key="exec:bbb")
        delay_c = policy.compute_delay_ms(attempt_idx=0, op_key="exec:ccc")
        
        # At least some should be different (very high probability)
        unique_delays = {delay_a, delay_b, delay_c}
        assert len(unique_delays) > 1, "Expected different delays for different keys"
    
    def test_jitter_hash_varies_by_attempt(self):
        """Same op_key but different attempts produce different jitters."""
        policy = RetryPolicy(base_delay_ms=100, multiplier=1.0, jitter_mode="hash")
        
        delay0 = policy.compute_delay_ms(attempt_idx=0, op_key="exec:same")
        delay1 = policy.compute_delay_ms(attempt_idx=1, op_key="exec:same")
        delay2 = policy.compute_delay_ms(attempt_idx=2, op_key="exec:same")
        
        # Different attempts should produce different jitter offsets
        unique_delays = {delay0, delay1, delay2}
        assert len(unique_delays) > 1, "Expected different jitters for different attempts"


class TestRetryCall:
    """Tests for retry_call() wrapper."""
    
    def test_success_first_try(self):
        """Function succeeds on first try."""
        call_count = 0
        
        def fn():
            nonlocal call_count
            call_count += 1
            return "success"
        
        policy = RetryPolicy(max_attempts=3)
        result, attempts = retry_call(
            fn,
            is_retryable_exc=lambda e: True,
            policy=policy,
            op_key="test",
        )
        
        assert result == "success"
        assert attempts == 1
        assert call_count == 1
    
    def test_retries_on_retryable_exception(self):
        """Retries when retryable exception occurs."""
        call_count = 0
        
        def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("temp failure")
            return "success"
        
        sleep_calls = []
        def mock_sleep(ms):
            sleep_calls.append(ms)
        
        policy = RetryPolicy(max_attempts=5, base_delay_ms=10)
        result, attempts = retry_call(
            fn,
            is_retryable_exc=lambda e: isinstance(e, ConnectionError),
            policy=policy,
            op_key="test",
            sleep_fn=mock_sleep,
        )
        
        assert result == "success"
        assert attempts == 3
        assert call_count == 3
        assert len(sleep_calls) == 2  # Slept before retry 2 and 3
    
    def test_raises_non_retryable_immediately(self):
        """Non-retryable exceptions propagate immediately."""
        call_count = 0
        
        def fn():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")
        
        policy = RetryPolicy(max_attempts=5)
        
        with pytest.raises(ValueError):
            retry_call(
                fn,
                is_retryable_exc=lambda e: isinstance(e, ConnectionError),
                policy=policy,
                op_key="test",
            )
        
        assert call_count == 1  # Only one attempt
    
    def test_retry_exhausted_error(self):
        """RetryExhaustedError raised when all attempts fail."""
        call_count = 0
        
        def fn():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("always fails")
        
        policy = RetryPolicy(max_attempts=3, base_delay_ms=1)
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            retry_call(
                fn,
                is_retryable_exc=lambda e: isinstance(e, ConnectionError),
                policy=policy,
                op_key="test",
            )
        
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exception, ConnectionError)
        assert call_count == 3
    
    def test_no_real_sleep_by_default(self):
        """Default sleep_fn is no-op (safe for tests)."""
        import time
        
        def fn():
            raise ConnectionError("fail")
        
        policy = RetryPolicy(max_attempts=2, base_delay_ms=100000)  # 100 seconds
        
        start = time.time()
        with pytest.raises(RetryExhaustedError):
            retry_call(
                fn,
                is_retryable_exc=lambda e: True,
                policy=policy,
                op_key="test",
                # Using default sleep_fn which is no-op
            )
        elapsed = time.time() - start
        
        # Should complete nearly instantly (< 1 second)
        assert elapsed < 1.0, f"Expected no blocking sleep, got {elapsed}s"
