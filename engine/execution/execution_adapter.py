"""
engine/execution/execution_adapter.py

Standardized ExecutionAdapter protocol for order execution.

AG-3K-3-1: Defines stable contract for execution layer.

This module provides a forward-looking interface while maintaining
compatibility with the existing ExchangeAdapter protocol via shims.
"""

from dataclasses import dataclass, field
from typing import Protocol, Optional, Dict, Any, List
from enum import Enum
from engine.time_provider import TimeProvider


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class OrderRequest:
    """
    Standardized order request.
    
    This is a simplified view for execution - risk checks should be
    done before creating this request.
    
    Attributes:
        order_id: Unique order identifier.
        symbol: Trading pair (e.g., "BTC/USDT").
        side: BUY or SELL.
        qty: Order quantity.
        order_type: MARKET, LIMIT, etc.
        limit_price: Limit price (for LIMIT orders).
        time_in_force: GTC, IOC, FOK, etc.
        client_order_id: Optional client-assigned ID.
    """
    order_id: str
    symbol: str
    side: str  # BUY or SELL
    qty: float
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    time_in_force: str = "GTC"
    client_order_id: Optional[str] = None
    trace_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CancelRequest:
    """Request to cancel an order."""
    order_id: str
    client_order_id: Optional[str] = None


@dataclass
class ExecutionResult:
    """
    Result of order execution (place or status check).
    
    Attributes:
        order_id: Order identifier.
        status: Current order status.
        filled_qty: Quantity filled so far.
        avg_price: Average fill price.
        fee: Execution fees.
        latency_ms: Execution latency in milliseconds.
        error_code: Error code if failed.
        error_message: Error message if failed.
        extra: Additional metadata.
    """
    order_id: str
    status: OrderStatus
    filled_qty: float = 0.0
    avg_price: float = 0.0
    fee: float = 0.0
    slippage_bps: float = 0.0
    latency_ms: float = 0.0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    trace_id: Optional[str] = None
    ref_order_id: Optional[str] = None
    ref_risk_event_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CancelResult:
    """Result of cancel request."""
    order_id: str
    success: bool
    status: OrderStatus
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ExecutionContext:
    """
    Context passed to execution operations.
    
    Attributes:
        step_id: Current simulation step (for determinism).
        time_provider: Time provider for timestamps.
        current_price: Current market price (for fills).
    """
    step_id: int = 0
    time_provider: Optional[TimeProvider] = None
    current_price: Optional[float] = None
    bar_data: Optional[Dict[str, Any]] = None
    
    def to_legacy_dict(self) -> Dict[str, Any]:
        """Convert to legacy ExecutionContext dict format."""
        return {
            "step_id": self.step_id,
            "time_provider": self.time_provider,
        }


class ExecutionAdapter(Protocol):
    """
    Protocol for order execution adapters.
    
    Contract:
        - place_order: Submit order, returns ExecutionResult
        - cancel_order: Cancel order, returns CancelResult (optional)
        - get_order_status: Check order status (optional)
    
    Implementations should be:
        - Deterministic when given same inputs (for simulated modes)
        - Thread-safe for concurrent access (if needed)
        - Idempotent for retries (best-effort)
    
    Flags:
        - supports_cancel: True if cancel_order is implemented
        - supports_status: True if get_order_status is implemented
        - is_simulated: True if this is a simulation adapter
    """
    
    @property
    def supports_cancel(self) -> bool:
        """Whether cancel_order is supported."""
        ...
    
    @property
    def supports_status(self) -> bool:
        """Whether get_order_status is supported."""
        ...
    
    @property
    def is_simulated(self) -> bool:
        """Whether this is a simulated (non-live) adapter."""
        ...
    
    def place_order(
        self,
        request: OrderRequest,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """
        Place an order for execution.
        
        Args:
            request: Order request details.
            context: Execution context (timing, prices).
            
        Returns:
            ExecutionResult with fill details.
        """
        ...
    
    def cancel_order(
        self,
        request: CancelRequest,
        context: ExecutionContext,
    ) -> CancelResult:
        """
        Cancel an existing order (optional - check supports_cancel).
        
        Args:
            request: Cancel request.
            context: Execution context.
            
        Returns:
            CancelResult indicating success/failure.
        """
        ...
    
    def get_order_status(
        self,
        order_id: str,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """
        Get current status of an order (optional - check supports_status).
        
        Args:
            order_id: Order to check.
            context: Execution context.
            
        Returns:
            ExecutionResult with current status.
        """
        ...


class SimExecutionAdapter:
    """
    Simulated execution adapter for testing and paper trading.
    
    Provides deterministic fills based on seed and step_id.
    No network calls - all execution is local/simulated.
    """
    
    def __init__(
        self,
        slippage_bps: float = 5.0,
        fee_bps: float = 10.0,
        fill_probability: float = 1.0,
        seed: int = 42,
    ):
        """
        Initialize simulated adapter.
        
        Args:
            slippage_bps: Slippage in basis points.
            fee_bps: Fee in basis points.
            fill_probability: Probability of fill (1.0 = always fill).
            seed: Random seed for determinism.
        """
        self.slippage_bps = slippage_bps
        self.fee_bps = fee_bps
        self.fill_probability = fill_probability
        self.seed = seed
        self._order_count = 0
    
    @property
    def supports_cancel(self) -> bool:
        return False  # Sim adapter: immediate fill, no cancel needed
    
    @property
    def supports_status(self) -> bool:
        return False  # Immediate fill, no status tracking
    
    @property
    def is_simulated(self) -> bool:
        return True
    
    def place_order(
        self,
        request: OrderRequest,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """
        Place simulated order with immediate fill.
        
        Deterministic behavior based on seed + step_id.
        """
        import random
        
        self._order_count += 1
        
        # Deterministic RNG based on seed + step
        rng = random.Random(self.seed + context.step_id + self._order_count)
        
        # Resolve base price
        base_price = request.limit_price
        if not base_price or base_price <= 0:
            base_price = context.current_price
        if not base_price or base_price <= 0:
            if context.bar_data:
                base_price = context.bar_data.get("close", 0)
        if not base_price or base_price <= 0:
            return ExecutionResult(
                order_id=request.order_id,
                status=OrderStatus.REJECTED,
                error_code="NO_PRICE",
                error_message="No valid price available",
                trace_id=request.trace_id,
            )
        
        # Check fill probability
        if rng.random() > self.fill_probability:
            return ExecutionResult(
                order_id=request.order_id,
                status=OrderStatus.REJECTED,
                error_code="NO_FILL",
                error_message="Order not filled (probability)",
                trace_id=request.trace_id,
            )
        
        # Apply slippage
        slippage_factor = 1 + (self.slippage_bps / 10000)
        if request.side.upper() == "BUY":
            avg_price = base_price * slippage_factor
        else:
            avg_price = base_price / slippage_factor
        
        # Calculate fee
        fee = request.qty * avg_price * (self.fee_bps / 10000)
        
        return ExecutionResult(
            order_id=request.order_id,
            status=OrderStatus.FILLED,
            filled_qty=request.qty,
            avg_price=avg_price,
            fee=fee,
            slippage_bps=self.slippage_bps,
            latency_ms=1.0,
            trace_id=request.trace_id,
            extra={
                "adapter": "SimExecutionAdapter",
                "seed": self.seed,
                "step_id": context.step_id,
            }
        )
    
    def cancel_order(
        self,
        request: CancelRequest,
        context: ExecutionContext,
    ) -> CancelResult:
        """Cancel not supported for immediate-fill sim adapter."""
        return CancelResult(
            order_id=request.order_id,
            success=False,
            status=OrderStatus.FILLED,
            error_code="NOT_SUPPORTED",
            error_message="SimExecutionAdapter fills immediately, cancel not applicable",
        )
    
    def get_order_status(
        self,
        order_id: str,
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Status not tracked for immediate-fill sim adapter."""
        return ExecutionResult(
            order_id=order_id,
            status=OrderStatus.FILLED,
            error_code="NOT_SUPPORTED",
            error_message="SimExecutionAdapter does not track order status",
        )
