"""
tests/test_market_data_no_lookahead_enforced_3L1.py

Adversarial tests for no-lookahead invariant in LoopStepper.run_adapter_mode().

AG-3L-1-1: Validates that run_adapter_mode() rejects/raises when adapter
returns events with ts > current_step_ts, ensuring no future data leakage.
"""

import pytest
from pathlib import Path
from typing import List, Optional

from engine.loop_stepper import LoopStepper
from engine.time_provider import SimulatedTimeProvider
from engine.market_data.market_data_adapter import MarketDataEvent


class MaliciousAdapter:
    """
    Fake adapter that intentionally returns events with ts > up_to_ts.
    
    This simulates a buggy or adversarial data source that could cause lookahead.
    Used to verify that LoopStepper enforces the no-lookahead guard.
    """
    
    def __init__(self, events: List[MarketDataEvent], lookahead_offset_ms: int = 0):
        """
        Args:
            events: List of events to emit.
            lookahead_offset_ms: If > 0, returned events will have ts += offset,
                                 causing ts > up_to_ts violation.
        """
        self._events = events
        self._idx = 0
        self._lookahead_offset_ms = lookahead_offset_ms
    
    def poll(
        self, 
        max_items: int = 100, 
        up_to_ts: Optional[int] = None
    ) -> List[MarketDataEvent]:
        """Return events, optionally with lookahead violation."""
        if self._idx >= len(self._events):
            return []
        
        event = self._events[self._idx]
        self._idx += 1
        
        # Apply lookahead offset if configured
        if self._lookahead_offset_ms > 0:
            # Create new event with modified ts (lookahead violation)
            event = MarketDataEvent(
                ts=event.ts + self._lookahead_offset_ms,  # VIOLATION
                symbol=event.symbol,
                timeframe=event.timeframe,
                open=event.open,
                high=event.high,
                low=event.low,
                close=event.close,
                volume=event.volume,
            )
        
        return [event]
    
    def peek_next_ts(self) -> Optional[int]:
        """Peek without consuming."""
        if self._idx >= len(self._events):
            return None
        return self._events[self._idx].ts
    
    def remaining(self) -> int:
        return len(self._events) - self._idx
    
    def reset(self) -> None:
        self._idx = 0


class TestNoLookaheadGuard:
    """Tests that verify LoopStepper rejects lookahead violations."""
    
    def _make_test_events(self, n: int = 10) -> List[MarketDataEvent]:
        """Create deterministic test events."""
        base_ts = 1705276800000  # 2024-01-15 00:00:00 UTC
        events = []
        for i in range(n):
            events.append(MarketDataEvent(
                ts=base_ts + i * 3600000,  # Hourly
                symbol="BTC/USDT",
                timeframe="1h",
                open=42000.0 + i * 100,
                high=42500.0 + i * 100,
                low=41800.0 + i * 100,
                close=42300.0 + i * 100,
                volume=1000.0 + i * 50,
            ))
        return events
    
    def test_lookahead_violation_raises_assertion_error(self):
        """
        When adapter returns event with ts > current_step_ts, 
        run_adapter_mode() should raise AssertionError.
        """
        events = self._make_test_events(10)
        
        # Create malicious adapter that adds 1 hour to returned events
        # This causes ts > up_to_ts (lookahead)
        malicious_adapter = MaliciousAdapter(
            events, 
            lookahead_offset_ms=3600000  # +1 hour
        )
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        # Should raise AssertionError due to lookahead violation
        with pytest.raises(AssertionError, match="Lookahead violation"):
            stepper.run_adapter_mode(
                malicious_adapter,
                max_steps=5,
                warmup=2,
            )
        
        stepper.close()
    
    def test_valid_adapter_no_violation(self):
        """Normal adapter without lookahead should work correctly."""
        events = self._make_test_events(10)
        
        # Normal adapter (no offset)
        normal_adapter = MaliciousAdapter(events, lookahead_offset_ms=0)
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        # Should NOT raise
        result = stepper.run_adapter_mode(
            normal_adapter,
            max_steps=3,
            warmup=2,
        )
        
        assert result["steps_processed"] == 3
        
        stepper.close()
    
    def test_exact_boundary_ts_allowed(self):
        """Event with ts == current_step_ts is valid (not lookahead)."""
        events = self._make_test_events(10)
        
        # Adapter with zero offset (ts == boundary)
        adapter = MaliciousAdapter(events, lookahead_offset_ms=0)
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        # Should work fine
        result = stepper.run_adapter_mode(
            adapter,
            max_steps=5,
            warmup=2,
        )
        
        assert result["consumed"] == 7  # warmup + steps
        
        stepper.close()


class TestNoLookaheadEdgeCases:
    """Edge cases for no-lookahead enforcement."""
    
    def test_lookahead_by_1ms_still_violates(self):
        """Even 1ms lookahead should be caught."""
        base_ts = 1705276800000
        events = [
            MarketDataEvent(
                ts=base_ts,
                symbol="BTC/USDT",
                timeframe="1h",
                open=42000.0,
                high=42500.0,
                low=41800.0,
                close=42300.0,
                volume=1000.0,
            )
            for _ in range(10)
        ]
        
        # Offset by just 1ms
        malicious_adapter = MaliciousAdapter(events, lookahead_offset_ms=1)
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        with pytest.raises(AssertionError, match="Lookahead violation"):
            stepper.run_adapter_mode(
                malicious_adapter,
                max_steps=5,
                warmup=2,
            )
        
        stepper.close()
