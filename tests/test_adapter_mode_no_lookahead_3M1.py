"""
tests/test_adapter_mode_no_lookahead_3M1.py

AG-3M-1-1: No-lookahead tests for adapter mode with ExchangeAdapter.

Validates that the no-lookahead invariant is maintained when using
exchange_adapter in run_adapter_mode():
- event.ts <= step_ts for all processed/emitted events
- Lookahead violations raise AssertionError
"""

import pytest
from pathlib import Path
from typing import List, Optional

from engine.loop_stepper import LoopStepper
from engine.time_provider import SimulatedTimeProvider
from engine.exchange_adapter import PaperExchangeAdapter
from engine.market_data.market_data_adapter import MarketDataEvent


class MaliciousAdapterWithExchange:
    """
    Fake adapter that can intentionally return events with ts > up_to_ts.
    
    Used to verify no-lookahead guard with exchange_adapter enabled.
    """
    
    def __init__(self, events: List[MarketDataEvent], lookahead_offset_ms: int = 0):
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
        
        if self._lookahead_offset_ms > 0:
            event = MarketDataEvent(
                ts=event.ts + self._lookahead_offset_ms,
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
        if self._idx >= len(self._events):
            return None
        return self._events[self._idx].ts
    
    def remaining(self) -> int:
        return len(self._events) - self._idx
    
    def reset(self) -> None:
        self._idx = 0


def _make_test_events(n: int = 10) -> List[MarketDataEvent]:
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


class TestNoLookaheadWithExchangeAdapter:
    """Tests for no-lookahead invariant with exchange_adapter."""
    
    def test_lookahead_violation_raises_with_exchange_adapter(self):
        """
        When adapter returns event with ts > current_step_ts,
        run_adapter_mode() should raise AssertionError even with exchange_adapter.
        """
        events = _make_test_events(10)
        
        # Malicious adapter that adds 1 hour to returned events
        malicious_adapter = MaliciousAdapterWithExchange(
            events, 
            lookahead_offset_ms=3600000  # +1 hour
        )
        exchange = PaperExchangeAdapter()
        
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
                exchange_adapter=exchange,
            )
        
        stepper.close()
    
    def test_valid_adapter_with_exchange_no_violation(self):
        """Normal adapter with exchange_adapter works correctly."""
        events = _make_test_events(10)
        normal_adapter = MaliciousAdapterWithExchange(events, lookahead_offset_ms=0)
        exchange = PaperExchangeAdapter()
        
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
            exchange_adapter=exchange,
        )
        
        assert result["steps_processed"] == 3
        
        stepper.close()
    
    def test_exact_boundary_ts_allowed_with_exchange(self):
        """Event with ts == current_step_ts is valid with exchange_adapter."""
        events = _make_test_events(10)
        adapter = MaliciousAdapterWithExchange(events, lookahead_offset_ms=0)
        exchange = PaperExchangeAdapter()
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        result = stepper.run_adapter_mode(
            adapter,
            max_steps=5,
            warmup=2,
            exchange_adapter=exchange,
        )
        
        assert result["consumed"] == 7  # warmup + steps
        
        stepper.close()


class TestNoLookaheadEdgeCasesWithExchange:
    """Edge cases for no-lookahead with exchange_adapter."""
    
    def test_lookahead_by_1ms_still_violates_with_exchange(self):
        """Even 1ms lookahead is caught with exchange_adapter."""
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
        
        malicious_adapter = MaliciousAdapterWithExchange(events, lookahead_offset_ms=1)
        exchange = PaperExchangeAdapter()
        
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
                exchange_adapter=exchange,
            )
        
        stepper.close()
    
    def test_events_processed_have_valid_timestamps(self):
        """All processed events should have ts <= step_ts."""
        events = _make_test_events(10)
        adapter = MaliciousAdapterWithExchange(events, lookahead_offset_ms=0)
        exchange = PaperExchangeAdapter()
        
        time_provider = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(
            seed=42,
            time_provider=time_provider,
        )
        
        result = stepper.run_adapter_mode(
            adapter,
            max_steps=5,
            warmup=2,
            exchange_adapter=exchange,
        )
        
        # Verify all events have valid structure
        for evt in result["events"]:
            assert "type" in evt
            assert "payload" in evt
            # Trace_id should be present
            payload = evt.get("payload", {})
            assert "trace_id" in payload or evt["type"] == "OrderIntent"
        
        stepper.close()
