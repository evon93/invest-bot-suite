"""
contracts/event_messages.py

Event-Driven Contracts v1 for Invest-Bot-Suite (Phase 3A).
Defines canonical schemas for:
- OrderIntent
- RiskDecision
- ExecutionReport
- ExecutionContext

Includes serialization helpers (to_dict/from_dict/to_json/from_json).
"""

import json
import uuid
import datetime
from dataclasses import dataclass, field, asdict, is_dataclass
from typing import Dict, Any, Optional, List, Union

# Common constants
SCHEMA_VERSION_V1 = "1.0"

def _ensure_strict_types(cls, data):
    """
    Validation best-effort: missing required fields raise TypeError/KeyError.
    Extra fields are generally ignored by dataclass init if not strictly handled,
    but here we rely on Python's dataclass default behavior (ignores extra args if init=True? 
    No, standard dataclass does NOT ignore extra args in __init__ if strictly typed, 
    but unpacking dict into it will fail if extra keys exist unless filtered).
    
    We will strictly extract only known fields to avoid errors on extra inputs (forward compatibility),
    but enforce missing required fields.
    """
    pass

@dataclass
class BaseEvent:
    """Base class for all event messages."""
    schema_id: str
    schema_version: str = SCHEMA_VERSION_V1
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        # Filter keys to match dataclass fields (ignore extra fields for compatibility)
        known_fields = cls.__dataclass_fields__.keys()
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered_data)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)

    @classmethod
    def from_json(cls, json_str: str):
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class OrderIntent(BaseEvent):
    """
    Represents a Strategy signal translated into an Order intent.
    Topic: 'signal' (or 'order_intent')
    """
    schema_id: str = "OrderIntent"
    symbol: str = ""   # Required
    side: str = ""     # 'BUY' or 'SELL'
    qty: Optional[float] = None
    notional: Optional[float] = None
    order_type: str = "MARKET"
    limit_price: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("symbol is required")
        if not self.side:
            raise ValueError("side is required")
        if self.qty is None and self.notional is None:
            raise ValueError("Either qty or notional must be provided")


@dataclass
class RiskDecision(BaseEvent):
    """
    Outcome of a Risk Manager evaluation on an OrderIntent.
    Topic: 'risk_eval'
    """
    schema_id: str = "RiskDecision"
    ref_order_event_id: str = "" # Required
    allowed: bool = False
    adjusted_qty: Optional[float] = None
    adjusted_notional: Optional[float] = None
    rejection_reasons: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.ref_order_event_id:
            raise ValueError("ref_order_event_id is required")


@dataclass
class ExecutionReport(BaseEvent):
    """
    Feedback from Execution (Fill, Rejection, Ack).
    Topic: 'execution_report'
    """
    schema_id: str = "ExecutionReport"
    ref_order_event_id: str = "" # Required
    ref_risk_event_id: Optional[str] = None
    status: str = "NEW" # NEW, FILLED, PARTIALLY_FILLED, CANCELED, REJECTED
    filled_qty: float = 0.0
    avg_price: float = 0.0
    fee: float = 0.0
    slippage: Optional[float] = None
    latency_ms: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.ref_order_event_id:
            raise ValueError("ref_order_event_id is required")


@dataclass
class ExecutionContext(BaseEvent):
    """
    Context for simulation/paper trading (slippage models, seed).
    Used to configure the environment or passed along with requests.
    """
    schema_id: str = "ExecutionContext"
    slippage_model: str = "default_fixed"
    latency_model: str = "zero_latency"
    seed: int = 42
    extra: Dict[str, Any] = field(default_factory=dict)
