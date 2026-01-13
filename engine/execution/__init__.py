"""
engine/execution/__init__.py

Execution adapter components for standardized order execution.

AG-3K-3-1: Standardized ExecutionAdapter interface with shims for compatibility.
"""

from engine.execution.execution_adapter import (
    ExecutionAdapter,
    ExecutionContext,
    ExecutionResult,
    OrderRequest,
    CancelRequest,
    CancelResult,
    OrderStatus,
)
from engine.execution.shims import (
    ExchangeAdapterShim,
    LegacyExchangeAdapter,
)

__all__ = [
    # Core interface
    "ExecutionAdapter",
    "ExecutionContext",
    "ExecutionResult",
    "OrderRequest",
    "CancelRequest",
    "CancelResult",
    "OrderStatus",
    # Shims
    "ExchangeAdapterShim",
    "LegacyExchangeAdapter",
]
