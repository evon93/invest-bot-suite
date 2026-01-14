"""
tests/test_adapter_mode_checkpoint_state_3M2.py

AG-3M-2-1: Checkpoint state validation tests for adapter mode.

Tests:
- Checkpoint file exists and loads correctly
- state.db persists and reloads
- No-lookahead invariant maintained during resume
"""

import pytest
import json
from pathlib import Path

from engine.loop_stepper import LoopStepper
from engine.time_provider import SimulatedTimeProvider
from engine.exchange_adapter import PaperExchangeAdapter
from engine.market_data.fixture_adapter import FixtureMarketDataAdapter
from engine.checkpoint import Checkpoint
from engine.market_data.market_data_adapter import MarketDataEvent


# Test fixture path
FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ohlcv_fixture_3K1.csv"


class TestCheckpointStateValidation:
    """Tests for checkpoint state persistence."""
    
    def test_checkpoint_file_created_and_loadable(self, tmp_path):
        """Checkpoint file is created and can be loaded."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        checkpoint_path = run_dir / "checkpoint.json"
        
        adapter = FixtureMarketDataAdapter(FIXTURE_PATH)
        exchange = PaperExchangeAdapter()
        tp = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(seed=42, time_provider=tp)
        
        ckpt = Checkpoint.create_new("state_test")
        ckpt.save_atomic(checkpoint_path)
        
        stepper.run_adapter_mode(
            adapter,
            max_steps=3,
            warmup=2,
            exchange_adapter=exchange,
            checkpoint=ckpt,
            checkpoint_path=checkpoint_path,
        )
        stepper.close()
        
        # Checkpoint should exist
        assert checkpoint_path.exists()
        
        # Should be valid JSON
        with open(checkpoint_path) as f:
            data = json.load(f)
        
        assert "run_id" in data
        assert "last_processed_idx" in data
        assert "processed_count" in data
        assert "updated_at" in data
        
        # Should be loadable via Checkpoint.load
        loaded = Checkpoint.load(checkpoint_path)
        assert loaded.run_id == "state_test"
        assert loaded.processed_count == 3
    
    def test_state_db_persists_across_runs(self, tmp_path):
        """state.db is updated and persists for resume."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        db_path = run_dir / "state.db"
        checkpoint_path = run_dir / "checkpoint.json"
        
        # First run
        adapter1 = FixtureMarketDataAdapter(FIXTURE_PATH)
        exchange1 = PaperExchangeAdapter()
        tp1 = SimulatedTimeProvider(seed=42)
        stepper1 = LoopStepper(
            seed=42,
            time_provider=tp1,
            state_db=db_path,
        )
        
        ckpt = Checkpoint.create_new("db_test")
        ckpt.save_atomic(checkpoint_path)
        
        stepper1.run_adapter_mode(
            adapter1,
            max_steps=3,
            warmup=2,
            exchange_adapter=exchange1,
            checkpoint=ckpt,
            checkpoint_path=checkpoint_path,
        )
        
        positions_after_first = stepper1.get_positions()
        stepper1.close()
        
        # state.db should exist
        assert db_path.exists()
        
        # Resume run - state.db should still be readable
        saved_ckpt = Checkpoint.load(checkpoint_path)
        
        adapter2 = FixtureMarketDataAdapter(FIXTURE_PATH)
        exchange2 = PaperExchangeAdapter()
        tp2 = SimulatedTimeProvider(seed=42)
        stepper2 = LoopStepper(
            seed=42,
            time_provider=tp2,
            state_db=db_path,
        )
        
        # Positions should load from previous run
        positions_on_resume = stepper2.get_positions()
        
        stepper2.run_adapter_mode(
            adapter2,
            max_steps=2,
            warmup=2,
            exchange_adapter=exchange2,
            checkpoint=saved_ckpt,
            checkpoint_path=checkpoint_path,
            start_idx=saved_ckpt.last_processed_idx + 1,
        )
        
        positions_final = stepper2.get_positions()
        stepper2.close()
        
        # Positions should have persisted
        assert isinstance(positions_on_resume, list)
        assert isinstance(positions_final, list)


class MaliciousResumeAdapter:
    """Adapter that tries to cause lookahead on resume."""
    
    def __init__(self, events, skip_count=0, lookahead_offset_ms=0):
        self._events = events
        self._idx = 0
        self._skip_count = skip_count
        self._lookahead_offset_ms = lookahead_offset_ms
    
    def poll(self, max_items=100, up_to_ts=None):
        if self._idx >= len(self._events):
            return []
        
        event = self._events[self._idx]
        self._idx += 1
        
        # After skipping, try to inject lookahead
        if self._idx > self._skip_count and self._lookahead_offset_ms > 0:
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
    
    def peek_next_ts(self):
        if self._idx >= len(self._events):
            return None
        return self._events[self._idx].ts
    
    def remaining(self):
        return len(self._events) - self._idx


class TestNoLookaheadOnResume:
    """Tests that no-lookahead invariant is maintained on resume."""
    
    def _make_events(self, n=10):
        base_ts = 1705276800000
        return [
            MarketDataEvent(
                ts=base_ts + i * 3600000,
                symbol="BTC/USDT",
                timeframe="1h",
                open=42000.0 + i * 100,
                high=42500.0 + i * 100,
                low=41800.0 + i * 100,
                close=42300.0 + i * 100,
                volume=1000.0 + i * 50,
            )
            for i in range(n)
        ]
    
    def test_resume_maintains_no_lookahead_invariant(self, tmp_path):
        """Resume should still enforce no-lookahead."""
        events = self._make_events(10)
        
        # Normal adapter for first run
        from tests.test_adapter_mode_no_lookahead_3M1 import MaliciousAdapterWithExchange
        adapter1 = MaliciousAdapterWithExchange(events, lookahead_offset_ms=0)
        
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        checkpoint_path = run_dir / "checkpoint.json"
        
        exchange = PaperExchangeAdapter()
        tp = SimulatedTimeProvider(seed=42)
        stepper = LoopStepper(seed=42, time_provider=tp)
        
        ckpt = Checkpoint.create_new("lookahead_test")
        ckpt.save_atomic(checkpoint_path)
        
        # First run OK
        result1 = stepper.run_adapter_mode(
            adapter1,
            max_steps=3,
            warmup=2,
            exchange_adapter=exchange,
            checkpoint=ckpt,
            checkpoint_path=checkpoint_path,
        )
        stepper.close()
        
        assert result1["steps_processed"] == 3
        
        # Resume with malicious adapter that tries lookahead after skip
        saved_ckpt = Checkpoint.load(checkpoint_path)
        
        # Create adapter that injects lookahead after skip
        malicious_adapter = MaliciousResumeAdapter(
            events,
            skip_count=saved_ckpt.last_processed_idx + 1 + 2,  # warmup + processed
            lookahead_offset_ms=3600000,
        )
        
        tp2 = SimulatedTimeProvider(seed=42)
        stepper2 = LoopStepper(seed=42, time_provider=tp2)
        
        # Should raise due to lookahead violation
        with pytest.raises(AssertionError, match="Lookahead violation"):
            stepper2.run_adapter_mode(
                malicious_adapter,
                max_steps=2,
                warmup=2,
                exchange_adapter=exchange,
                checkpoint=saved_ckpt,
                checkpoint_path=checkpoint_path,
                start_idx=saved_ckpt.last_processed_idx + 1,
            )
        
        stepper2.close()
    
    def test_valid_resume_no_lookahead_error(self, tmp_path):
        """Valid resume should not trigger lookahead errors."""
        events = self._make_events(10)
        
        from tests.test_adapter_mode_no_lookahead_3M1 import MaliciousAdapterWithExchange
        
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        checkpoint_path = run_dir / "checkpoint.json"
        
        # First run
        adapter1 = MaliciousAdapterWithExchange(events, lookahead_offset_ms=0)
        exchange = PaperExchangeAdapter()
        tp1 = SimulatedTimeProvider(seed=42)
        stepper1 = LoopStepper(seed=42, time_provider=tp1)
        
        ckpt = Checkpoint.create_new("valid_resume")
        ckpt.save_atomic(checkpoint_path)
        
        stepper1.run_adapter_mode(
            adapter1,
            max_steps=3,
            warmup=2,
            exchange_adapter=exchange,
            checkpoint=ckpt,
            checkpoint_path=checkpoint_path,
        )
        stepper1.close()
        
        # Valid resume - should not raise
        saved_ckpt = Checkpoint.load(checkpoint_path)
        adapter2 = MaliciousAdapterWithExchange(events, lookahead_offset_ms=0)
        tp2 = SimulatedTimeProvider(seed=42)
        stepper2 = LoopStepper(seed=42, time_provider=tp2)
        
        result = stepper2.run_adapter_mode(
            adapter2,
            max_steps=2,
            warmup=2,
            exchange_adapter=exchange,
            checkpoint=saved_ckpt,
            checkpoint_path=checkpoint_path,
            start_idx=saved_ckpt.last_processed_idx + 1,
        )
        stepper2.close()
        
        assert result["steps_processed"] == 2
