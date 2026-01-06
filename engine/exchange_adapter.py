"""
engine/exchange_adapter.py

Defines ExchangeAdapter protocol and implementations for decoupled execution logic.
"""

from typing import Protocol, TypedDict, Optional, Any, Dict, Callable
from dataclasses import dataclass, field
from engine.time_provider import TimeProvider
from contracts.events_v1 import OrderIntentV1, RiskDecisionV1, ExecutionReportV1


class ExecutionContext(TypedDict):
    """Context required for execution."""
    step_id: int
    time_provider: Optional[TimeProvider]


class ExchangeAdapter(Protocol):
    """Protocol for exchange interaction."""
    
    def submit(
        self,
        intent: OrderIntentV1,
        decision: RiskDecisionV1,
        context: ExecutionContext,
        report_event_id: str,
        extra_meta: Optional[Dict[str, Any]] = None
    ) -> ExecutionReportV1:
        """
        Submit a risk-approved order for execution.
        
        Args:
            intent: Original order intent
            decision: Risk decision (allowed=True)
            context: Execution context (step/time)
            report_event_id: Deterministic event ID for the resulting report
            extra_meta: Additional metadata (e.g. from cache) needed for price/fill
            
        Returns:
            ExecutionReportV1
        """
        ...


@dataclass
class PaperExchangeAdapter:
    """
    Paper trading adapter: Immediate partial/full fill logic.
    Reproduces deterministic behavior of ExecWorker v1.
    """
    slippage_bps: float = 5.0
    fee_bps: float = 10.0
    
    def submit(
        self,
        intent: OrderIntentV1,
        decision: RiskDecisionV1,
        context: ExecutionContext,
        report_event_id: str,
        extra_meta: Optional[Dict[str, Any]] = None
    ) -> ExecutionReportV1:
        
        meta = extra_meta or {}
        
        symbol = intent.symbol
        side = intent.side.upper() if intent.side else "BUY"
        qty = intent.qty
        
        # Resolve Price
        base_price = intent.limit_price
        if not base_price or base_price <= 0:
            if intent.notional and intent.notional > 0 and qty > 0:
                base_price = intent.notional / qty
        
        if not base_price or base_price <= 0:
            base_price = meta.get("current_price") or meta.get("close") or meta.get("bar_close")
            
        if not base_price or base_price <= 0:
             raise ValueError(
                f"ExchangeAdapter: No valid price available for ref_order_event_id={decision.ref_order_event_id}"
            )

        # Apply slippage
        if side == "BUY":
            avg_price = base_price * (1 + self.slippage_bps / 10000)
        else:
            avg_price = base_price * (1 - self.slippage_bps / 10000)
            
        fee = qty * avg_price * (self.fee_bps / 10000)
        
        # Resolve Timestamp
        ts_str = None
        if context.get("time_provider"):
             # Use time provider if available to reconstruct TS or use current
             pass
        # Usually ts comes from intent or we use the passed one in meta if provided
        ts_str = meta.get("ts") # ExecWorker might pass this
        
        return ExecutionReportV1(
            ref_order_event_id=decision.ref_order_event_id,
            status="FILLED",
            filled_qty=qty,
            avg_price=avg_price,
            fee=fee,
            slippage=self.slippage_bps,
            latency_ms=1.0,
            ref_risk_event_id=decision.event_id,
            trace_id=decision.trace_id,
            event_id=report_event_id,
            ts=ts_str,
            extra={
                "adapter": "PaperExchangeAdapter",
                "symbol": symbol,
                "side": side
            }
        )


@dataclass
class StubNetworkExchangeAdapter:
    """
    Stub network adapter simulating latency.
    Gated feature: returns FILLED but with simulated latency metrics.
    """
    latency_steps: int = 1
    slippage_bps: float = 5.0
    fee_bps: float = 10.0
    
    def submit(
        self,
        intent: OrderIntentV1,
        decision: RiskDecisionV1,
        context: ExecutionContext,
        report_event_id: str,
        extra_meta: Optional[Dict[str, Any]] = None
    ) -> ExecutionReportV1:
        
        # Reuse logic from Paper but adjust latency
        paper = PaperExchangeAdapter(slippage_bps=self.slippage_bps, fee_bps=self.fee_bps)
        report = paper.submit(intent, decision, context, report_event_id, extra_meta)
        
        # Calculate latency in ms (approx based on provider quantum or default assumption)
        # Verify if time_provider is Simulated
        latency_ms = 1.0
        tp = context.get("time_provider")
        if tp and hasattr(tp, "quantum_ns"):
             # quantum_ns to ms
             quantum_ms = tp.quantum_ns / 1_000_000
             latency_ms = max(1.0, self.latency_steps * quantum_ms)
        else:
             # Default fallback if real time or unknown
             latency_ms = float(self.latency_steps * 1000) # Assume 1s step? Or just use steps as proxy?
             # Requirement: "latencia determinista por latency_steps"
             # Let's map 1 step = 1000ms by default for metric visibility
             if self.latency_steps > 0:
                 latency_ms = self.latency_steps * 1000.0
        
        report.latency_ms = latency_ms
        report.extra["adapter"] = "StubNetworkExchangeAdapter"
        report.extra["simulated_latency_steps"] = self.latency_steps
        
        return report
