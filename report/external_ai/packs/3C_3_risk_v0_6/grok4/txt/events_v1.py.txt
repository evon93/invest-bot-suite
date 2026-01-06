"""
contracts/events_v1.py

Canonical Event Contracts v1 for Invest-Bot-Suite (Phase 3C).
Defines strict schemas with:
- to_dict(): Stable JSON-safe serialization
- from_dict(): Tolerant to legacy aliases
- validate(): Explicit invariant checks (no deps)

Compatible with pipeline 3B; does NOT replace event_messages.py.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
import uuid
import datetime

# Schema version
SCHEMA_VERSION = "1.0"

# Valid values for validation
VALID_SIDES = frozenset({"BUY", "SELL", "buy", "sell"})
VALID_ORDER_TYPES = frozenset({"MARKET", "LIMIT", "market", "limit"})
VALID_STATUSES = frozenset({"NEW", "FILLED", "PARTIALLY_FILLED", "CANCELED", "REJECTED"})


class ValidationError(Exception):
    """Raised when validate() fails."""
    pass


def _normalize_side(side: str) -> str:
    """Normalize side to uppercase."""
    return side.upper() if side else ""


def _normalize_reasons(reasons: Any) -> List[str]:
    """
    Normalize rejection_reasons to list[str].
    Accepts: str, list[str], None, or other iterables.
    """
    if reasons is None:
        return []
    if isinstance(reasons, str):
        return [reasons] if reasons else []
    if isinstance(reasons, (list, tuple)):
        return [str(r) for r in reasons if r]
    return []


def _generate_event_id() -> str:
    return str(uuid.uuid4())


def _generate_timestamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# Alias mappings for from_dict tolerance
ALIASES_ORDER_INTENT = {
    "ticker": "symbol",
    "asset": "symbol",
    "quantity": "qty",
    "amount": "qty",
    "action": "side",
    "direction": "side",
    "type": "order_type",
}

ALIASES_RISK_DECISION = {
    "reasons": "rejection_reasons",
    "reason": "rejection_reasons",
    "order_event_id": "ref_order_event_id",
    "order_id": "ref_order_event_id",
}

ALIASES_EXECUTION_REPORT = {
    "order_event_id": "ref_order_event_id",
    "order_id": "ref_order_event_id",
    "risk_event_id": "ref_risk_event_id",
    "price": "avg_price",
    "fill_price": "avg_price",
    "quantity": "filled_qty",
    "qty": "filled_qty",
}


def _apply_aliases(data: Dict[str, Any], aliases: Dict[str, str]) -> Dict[str, Any]:
    """Apply alias mapping to input dict."""
    result = dict(data)
    for alias, canonical in aliases.items():
        if alias in result and canonical not in result:
            result[canonical] = result.pop(alias)
    return result


@dataclass
class OrderIntentV1:
    """
    Strategy signal translated into an order intent.
    
    Fields:
        symbol: Asset identifier (required)
        side: BUY or SELL (required, normalized to uppercase)
        qty: Quantity (required, must be > 0)
        order_type: MARKET or LIMIT (default: MARKET)
        limit_price: Price for LIMIT orders (optional)
        notional: Alternative to qty (optional)
        event_id: Unique event ID (auto-generated)
        ts: ISO timestamp (auto-generated)
        trace_id: Trace ID for correlation (auto-generated)
        meta: Additional metadata (optional)
    """
    symbol: str
    side: str
    qty: Optional[float] = None
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    notional: Optional[float] = None
    event_id: str = field(default_factory=_generate_event_id)
    ts: str = field(default_factory=_generate_timestamp)
    trace_id: str = field(default_factory=_generate_event_id)
    meta: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self):
        # Normalize side to uppercase
        self.side = _normalize_side(self.side)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict with stable key order."""
        return {
            "schema_id": "OrderIntentV1",
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "ts": self.ts,
            "trace_id": self.trace_id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "notional": self.notional,
            "order_type": self.order_type,
            "limit_price": self.limit_price,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrderIntentV1":
        """
        Deserialize from dict, tolerant to legacy aliases.
        
        Supported aliases:
            ticker/asset -> symbol
            quantity/amount -> qty
            action/direction -> side
            type -> order_type
        """
        d = _apply_aliases(data, ALIASES_ORDER_INTENT)
        return cls(
            symbol=d.get("symbol", ""),
            side=d.get("side", ""),
            qty=d.get("qty"),
            order_type=d.get("order_type", "MARKET"),
            limit_price=d.get("limit_price"),
            notional=d.get("notional"),
            event_id=d.get("event_id", _generate_event_id()),
            ts=d.get("ts", _generate_timestamp()),
            trace_id=d.get("trace_id", _generate_event_id()),
            meta=d.get("meta", {}),
            schema_version=d.get("schema_version", SCHEMA_VERSION),
        )

    def validate(self) -> bool:
        """
        Validate invariants. Raises ValidationError on failure.
        
        Checks:
            - symbol is non-empty
            - side is BUY or SELL
            - qty > 0 OR notional > 0
            - order_type is MARKET or LIMIT
            - limit_price required if order_type is LIMIT
        
        Returns True if valid.
        """
        errors = []

        if not self.symbol or not self.symbol.strip():
            errors.append("symbol is required")

        if self.side not in {"BUY", "SELL"}:
            errors.append(f"side must be BUY or SELL, got '{self.side}'")

        has_qty = self.qty is not None and self.qty > 0
        has_notional = self.notional is not None and self.notional > 0
        if not has_qty and not has_notional:
            errors.append("qty or notional must be > 0")

        if self.order_type.upper() not in {"MARKET", "LIMIT"}:
            errors.append(f"order_type must be MARKET or LIMIT, got '{self.order_type}'")

        if self.order_type.upper() == "LIMIT" and self.limit_price is None:
            errors.append("limit_price required for LIMIT orders")

        if errors:
            raise ValidationError("; ".join(errors))
        return True


@dataclass
class RiskDecisionV1:
    """
    Risk Manager evaluation result for an OrderIntent.
    
    Fields:
        ref_order_event_id: Reference to original OrderIntent (required)
        allowed: Whether the order is allowed (default: False)
        adjusted_qty: Adjusted quantity if modified (optional)
        adjusted_notional: Adjusted notional if modified (optional)
        rejection_reasons: List of rejection reason strings (normalized)
        event_id: Unique event ID (auto-generated)
        ts: ISO timestamp (auto-generated)
        trace_id: Trace ID for correlation (auto-generated)
        extra: Additional metadata (optional)
    """
    ref_order_event_id: str
    allowed: bool = False
    adjusted_qty: Optional[float] = None
    adjusted_notional: Optional[float] = None
    rejection_reasons: List[str] = field(default_factory=list)
    event_id: str = field(default_factory=_generate_event_id)
    ts: str = field(default_factory=_generate_timestamp)
    trace_id: str = field(default_factory=_generate_event_id)
    extra: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self):
        # Normalize rejection_reasons to list[str]
        self.rejection_reasons = _normalize_reasons(self.rejection_reasons)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict with stable key order."""
        return {
            "schema_id": "RiskDecisionV1",
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "ts": self.ts,
            "trace_id": self.trace_id,
            "ref_order_event_id": self.ref_order_event_id,
            "allowed": self.allowed,
            "adjusted_qty": self.adjusted_qty,
            "adjusted_notional": self.adjusted_notional,
            "rejection_reasons": self.rejection_reasons,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskDecisionV1":
        """
        Deserialize from dict, tolerant to legacy aliases.
        
        Supported aliases:
            reasons/reason -> rejection_reasons
            order_event_id/order_id -> ref_order_event_id
        """
        d = _apply_aliases(data, ALIASES_RISK_DECISION)
        return cls(
            ref_order_event_id=d.get("ref_order_event_id", ""),
            allowed=d.get("allowed", False),
            adjusted_qty=d.get("adjusted_qty"),
            adjusted_notional=d.get("adjusted_notional"),
            rejection_reasons=d.get("rejection_reasons", []),
            event_id=d.get("event_id", _generate_event_id()),
            ts=d.get("ts", _generate_timestamp()),
            trace_id=d.get("trace_id", _generate_event_id()),
            extra=d.get("extra", {}),
            schema_version=d.get("schema_version", SCHEMA_VERSION),
        )

    def validate(self) -> bool:
        """
        Validate invariants. Raises ValidationError on failure.
        
        Checks:
            - ref_order_event_id is non-empty
            - rejection_reasons is a list
            - if not allowed, rejection_reasons should not be empty (warning, not error)
        
        Returns True if valid.
        """
        errors = []

        if not self.ref_order_event_id or not self.ref_order_event_id.strip():
            errors.append("ref_order_event_id is required")

        if not isinstance(self.rejection_reasons, list):
            errors.append("rejection_reasons must be a list")

        if errors:
            raise ValidationError("; ".join(errors))
        return True


@dataclass
class ExecutionReportV1:
    """
    Execution feedback (fill, reject, ack).
    
    Fields:
        ref_order_event_id: Reference to original OrderIntent (required)
        status: Execution status (required, validated)
        filled_qty: Filled quantity (default: 0.0)
        avg_price: Average fill price (default: 0.0)
        fee: Execution fee (default: 0.0)
        slippage: Slippage amount (optional)
        latency_ms: Execution latency in ms (optional)
        ref_risk_event_id: Reference to RiskDecision (optional)
        event_id: Unique event ID (auto-generated)
        ts: ISO timestamp (auto-generated)
        trace_id: Trace ID for correlation (auto-generated)
        extra: Additional metadata (optional)
    """
    ref_order_event_id: str
    status: str = "NEW"
    filled_qty: float = 0.0
    avg_price: float = 0.0
    fee: float = 0.0
    slippage: Optional[float] = None
    latency_ms: Optional[float] = None
    ref_risk_event_id: Optional[str] = None
    event_id: str = field(default_factory=_generate_event_id)
    ts: str = field(default_factory=_generate_timestamp)
    trace_id: str = field(default_factory=_generate_event_id)
    extra: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict with stable key order."""
        return {
            "schema_id": "ExecutionReportV1",
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "ts": self.ts,
            "trace_id": self.trace_id,
            "ref_order_event_id": self.ref_order_event_id,
            "ref_risk_event_id": self.ref_risk_event_id,
            "status": self.status,
            "filled_qty": self.filled_qty,
            "avg_price": self.avg_price,
            "fee": self.fee,
            "slippage": self.slippage,
            "latency_ms": self.latency_ms,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionReportV1":
        """
        Deserialize from dict, tolerant to legacy aliases.
        
        Supported aliases:
            order_event_id/order_id -> ref_order_event_id
            risk_event_id -> ref_risk_event_id
            price/fill_price -> avg_price
            quantity/qty -> filled_qty
        """
        d = _apply_aliases(data, ALIASES_EXECUTION_REPORT)
        return cls(
            ref_order_event_id=d.get("ref_order_event_id", ""),
            status=d.get("status", "NEW"),
            filled_qty=d.get("filled_qty", 0.0),
            avg_price=d.get("avg_price", 0.0),
            fee=d.get("fee", 0.0),
            slippage=d.get("slippage"),
            latency_ms=d.get("latency_ms"),
            ref_risk_event_id=d.get("ref_risk_event_id"),
            event_id=d.get("event_id", _generate_event_id()),
            ts=d.get("ts", _generate_timestamp()),
            trace_id=d.get("trace_id", _generate_event_id()),
            extra=d.get("extra", {}),
            schema_version=d.get("schema_version", SCHEMA_VERSION),
        )

    def validate(self) -> bool:
        """
        Validate invariants. Raises ValidationError on failure.
        
        Checks:
            - ref_order_event_id is non-empty
            - status is one of VALID_STATUSES
            - filled_qty >= 0
            - avg_price >= 0
        
        Returns True if valid.
        """
        errors = []

        if not self.ref_order_event_id or not self.ref_order_event_id.strip():
            errors.append("ref_order_event_id is required")

        if self.status not in VALID_STATUSES:
            errors.append(
                f"status must be one of {sorted(VALID_STATUSES)}, got '{self.status}'"
            )

        if self.filled_qty < 0:
            errors.append(f"filled_qty must be >= 0, got {self.filled_qty}")

        if self.avg_price < 0:
            errors.append(f"avg_price must be >= 0, got {self.avg_price}")

        if errors:
            raise ValidationError("; ".join(errors))
        return True
