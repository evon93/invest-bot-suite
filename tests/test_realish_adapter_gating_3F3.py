"""
tests/test_realish_adapter_gating_3F3.py

Tests for SimulatedRealtimeAdapter gating behavior.
Confirms that paper/stub/realish modes work without requiring env vars.
"""

import pytest
import sys
import os
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.runtime_config import RuntimeConfig
from engine.exchange_adapter import (
    PaperExchangeAdapter, 
    StubNetworkExchangeAdapter, 
    SimulatedRealtimeAdapter,
    TransientNetworkError
)
from contracts.events_v1 import OrderIntentV1, RiskDecisionV1


def make_test_intent() -> OrderIntentV1:
    """Create test intent."""
    return OrderIntentV1(
        symbol="BTC-USD",
        side="BUY",
        qty=1.0,
        notional=100.0,
        order_type="MARKET",
        limit_price=100.0,
        event_id="intent-001",
        trace_id="trace-001",
        ts="2024-01-01T00:00:00Z",
        meta={"bar_close": 100.0}
    )


def make_test_decision() -> RiskDecisionV1:
    """Create test decision."""
    return RiskDecisionV1(
        ref_order_event_id="intent-001",
        allowed=True,
        rejection_reasons=[],
        trace_id="trace-001",
        event_id="decision-001",
        ts="2024-01-01T00:00:01Z",
        extra={}
    )


class TestGatingNoEnvVarsRequired:
    """Tests confirming no env vars required for simulation modes."""
    
    def test_paper_mode_no_env_vars_required(self):
        """Paper + simulated doesn't require any env vars."""
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = RuntimeConfig.from_env()
            # Should not raise
            cfg.validate_for("simulated", "paper")
            assert cfg.exchange_kind == "paper"
    
    def test_stub_mode_no_env_vars_required(self):
        """Stub + simulated doesn't require any env vars."""
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = RuntimeConfig.from_env()
            # Should not raise
            cfg.validate_for("simulated", "stub")
    
    def test_realish_mode_no_env_vars_required(self):
        """Realish + simulated doesn't require any env vars (it's local simulation)."""
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = RuntimeConfig.from_env()
            # Realish is treated same as stub - local simulation, no secrets needed
            cfg.validate_for("simulated", "realish")


class TestSimulatedRealtimeAdapter:
    """Tests for SimulatedRealtimeAdapter behavior."""
    
    def test_adapter_can_instantiate(self):
        """Adapter can be created without any special setup."""
        adapter = SimulatedRealtimeAdapter()
        assert adapter.failure_rate_1_in_n == 10
        assert adapter.base_latency_ms == 50
        assert adapter.max_latency_ms == 500
    
    def test_adapter_submit_success(self):
        """Adapter can submit and return report (when not failing)."""
        # Use high failure_rate to avoid failure
        adapter = SimulatedRealtimeAdapter(failure_rate_1_in_n=1000000)
        
        intent = make_test_intent()
        decision = make_test_decision()
        context = {"step_id": 1, "time_provider": None}
        
        report = adapter.submit(intent, decision, context, "report-001", {"bar_close": 100.0})
        
        assert report.status == "FILLED"
        assert report.extra["adapter"] == "SimulatedRealtimeAdapter"
        assert report.filled_qty == 1.0
    
    def test_transient_failure_deterministic(self):
        """Transient failures are deterministic based on op_key hash."""
        # With failure_rate_1_in_n=2, about 50% will fail
        adapter = SimulatedRealtimeAdapter(failure_rate_1_in_n=2)
        
        intent = make_test_intent()
        decision = make_test_decision()
        context = {"step_id": 1, "time_provider": None}
        
        # Track which op_keys fail
        failures = []
        successes = []
        
        for i in range(20):
            test_decision = RiskDecisionV1(
                ref_order_event_id=f"intent-{i:03d}",
                allowed=True,
                rejection_reasons=[],
                trace_id=f"trace-{i:03d}",
                event_id=f"decision-{i:03d}",
                extra={}
            )
            try:
                adapter.submit(intent, test_decision, context, f"report-{i:03d}", {"bar_close": 100.0})
                successes.append(i)
            except TransientNetworkError:
                failures.append(i)
        
        # Should have mix of failures and successes
        assert len(failures) > 0, "Expected some failures"
        assert len(successes) > 0, "Expected some successes"
        
        # Determinism: running again should give same pattern
        adapter2 = SimulatedRealtimeAdapter(failure_rate_1_in_n=2)
        failures2 = []
        
        for i in range(20):
            test_decision = RiskDecisionV1(
                ref_order_event_id=f"intent-{i:03d}",
                allowed=True,
                rejection_reasons=[],
                trace_id=f"trace-{i:03d}",
                event_id=f"decision-{i:03d}",
                extra={}
            )
            try:
                adapter2.submit(intent, test_decision, context, f"report-{i:03d}", {"bar_close": 100.0})
            except TransientNetworkError:
                failures2.append(i)
        
        assert failures == failures2, "Failures should be deterministic"
    
    def test_latency_deterministic(self):
        """Latency values are deterministic based on op_key hash."""
        adapter = SimulatedRealtimeAdapter(failure_rate_1_in_n=1000000)  # No failures
        
        intent = make_test_intent()
        decision = make_test_decision() 
        context = {"step_id": 1, "time_provider": None}
        
        report1 = adapter.submit(intent, decision, context, "report-001", {"bar_close": 100.0})
        
        # Same inputs should give same latency
        adapter2 = SimulatedRealtimeAdapter(failure_rate_1_in_n=1000000)
        report2 = adapter2.submit(intent, decision, context, "report-001", {"bar_close": 100.0})
        
        assert report1.latency_ms == report2.latency_ms, "Latency should be deterministic"
    
    def test_no_real_sleep_by_default(self):
        """Default sleep_fn is no-op (safe for tests)."""
        import time
        
        adapter = SimulatedRealtimeAdapter(
            failure_rate_1_in_n=1000000,
            base_latency_ms=100000,  # 100 seconds would be obvious if blocking
            max_latency_ms=200000
        )
        
        intent = make_test_intent()
        decision = make_test_decision()
        context = {"step_id": 1, "time_provider": None}
        
        start = time.time()
        adapter.submit(intent, decision, context, "report-001", {"bar_close": 100.0})
        elapsed = time.time() - start
        
        # Should complete nearly instantly
        assert elapsed < 1.0, f"Expected no blocking sleep, got {elapsed}s"


class TestTransientNetworkError:
    """Tests for TransientNetworkError exception."""
    
    def test_exception_exists(self):
        """TransientNetworkError is importable and can be raised/caught."""
        try:
            raise TransientNetworkError("test error")
        except TransientNetworkError as e:
            assert "test error" in str(e)
