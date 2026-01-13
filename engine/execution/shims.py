"""
engine/execution/shims.py

Shims/adapters for bridging legacy ExchangeAdapter to new ExecutionAdapter.

AG-3K-3-1: Compatibility layer - no breaking changes to existing code.

These shims allow:
1. New code to use old adapters via ExecutionAdapter interface
2. Old code to continue using ExchangeAdapter unchanged
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from contracts.events_v1 import OrderIntentV1, RiskDecisionV1, ExecutionReportV1
from engine.execution.execution_adapter import (
    ExecutionAdapter,
    ExecutionContext,
    ExecutionResult,
    OrderRequest,
    CancelRequest,
    CancelResult,
    OrderStatus,
)


# Type alias for legacy adapters (from engine.exchange_adapter)
LegacyExchangeAdapter = Any  # PaperExchangeAdapter, StubNetworkExchangeAdapter, etc.


def order_status_from_string(status_str: str) -> OrderStatus:
    """Convert string status to OrderStatus enum."""
    mapping = {
        "FILLED": OrderStatus.FILLED,
        "PARTIAL": OrderStatus.PARTIAL,
        "PENDING": OrderStatus.PENDING,
        "CANCELLED": OrderStatus.CANCELLED,
        "REJECTED": OrderStatus.REJECTED,
        "EXPIRED": OrderStatus.EXPIRED,
    }
    return mapping.get(status_str.upper(), OrderStatus.PENDING)


@dataclass
class ExchangeAdapterShim:
    """
    Shim that wraps a legacy ExchangeAdapter to provide ExecutionAdapter interface.
    
    This allows new code using ExecutionAdapter to work with existing
    PaperExchangeAdapter, StubNetworkExchangeAdapter, SimulatedRealtimeAdapter.
    
    Usage:
        legacy = PaperExchangeAdapter()
        adapter = ExchangeAdapterShim(legacy)
        result = adapter.place_order(request, context)
    """
    
    legacy: LegacyExchangeAdapter
    _order_counter: int = 0
    
    @property
    def supports_cancel(self) -> bool:
        return False  # Legacy adapters don't support cancel
    
    @property
    def supports_status(self) -> bool:
        return False  # Legacy adapters don't track status
    
    @property
    def is_simulated(self) -> bool:
        # Infer from adapter type
        adapter_name = type(self.legacy).__name__
        return "Paper" in adapter_name or "Stub" in adapter_name or "Simulated" in adapter_name
    
    def place_order(
        self,
        request: OrderRequest,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """
        Place order via legacy ExchangeAdapter.submit().
        
        Converts OrderRequest -> (OrderIntentV1, RiskDecisionV1) for legacy interface,
        then converts ExecutionReportV1 -> ExecutionResult.
        """
        self._order_counter += 1
        
        # Create synthetic OrderIntentV1 from request
        intent = OrderIntentV1(
            symbol=request.symbol,
            side=request.side.upper(),
            qty=request.qty,
            limit_price=request.limit_price,
            notional=request.qty * (request.limit_price or 0) if request.limit_price else None,
            event_id=request.order_id,
            trace_id=request.trace_id,
        )
        
        # Create synthetic RiskDecisionV1 (assuming already approved)
        decision = RiskDecisionV1(
            allowed=True,
            adjusted_qty=request.qty,
            ref_order_event_id=request.order_id,
            event_id=f"risk_{request.order_id}",
            trace_id=request.trace_id,
        )
        
        # Convert context
        legacy_context = context.to_legacy_dict()
        
        # Build extra_meta for price resolution
        extra_meta = dict(request.extra)
        if context.current_price:
            extra_meta["current_price"] = context.current_price
        if context.bar_data:
            extra_meta.update(context.bar_data)
        
        # Generate report_event_id
        report_event_id = f"exec_{request.order_id}_{self._order_counter}"
        
        try:
            # Call legacy submit
            report: ExecutionReportV1 = self.legacy.submit(
                intent=intent,
                decision=decision,
                context=legacy_context,
                report_event_id=report_event_id,
                extra_meta=extra_meta,
            )
            
            # Convert to ExecutionResult
            return ExecutionResult(
                order_id=request.order_id,
                status=order_status_from_string(report.status),
                filled_qty=report.filled_qty,
                avg_price=report.avg_price,
                fee=report.fee,
                slippage_bps=report.slippage,
                latency_ms=report.latency_ms,
                trace_id=report.trace_id,
                ref_order_id=report.ref_order_event_id,
                ref_risk_event_id=report.ref_risk_event_id,
                extra=report.extra or {},
            )
        except Exception as e:
            return ExecutionResult(
                order_id=request.order_id,
                status=OrderStatus.REJECTED,
                error_code="EXECUTION_ERROR",
                error_message=str(e),
                trace_id=request.trace_id,
            )
    
    def cancel_order(
        self,
        request: CancelRequest,
        context: ExecutionContext,
    ) -> CancelResult:
        """Cancel not supported by legacy adapters."""
        return CancelResult(
            order_id=request.order_id,
            success=False,
            status=OrderStatus.FILLED,
            error_code="NOT_SUPPORTED",
            error_message="Legacy ExchangeAdapter does not support cancel",
        )
    
    def get_order_status(
        self,
        order_id: str,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Status tracking not supported by legacy adapters."""
        return ExecutionResult(
            order_id=order_id,
            status=OrderStatus.FILLED,
            error_code="NOT_SUPPORTED",
            error_message="Legacy ExchangeAdapter does not track order status",
        )


def create_execution_adapter_from_legacy(legacy_adapter: LegacyExchangeAdapter) -> ExecutionAdapter:
    """
    Factory function to wrap legacy adapter into ExecutionAdapter.
    
    Args:
        legacy_adapter: PaperExchangeAdapter, StubNetworkExchangeAdapter, etc.
        
    Returns:
        ExecutionAdapter-compatible shim.
    """
    return ExchangeAdapterShim(legacy=legacy_adapter)
