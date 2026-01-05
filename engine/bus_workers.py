"""
engine/bus_workers.py

Bus-mode workers for event-driven processing.

Workers:
- RiskWorker: Consumes OrderIntentV1, produces RiskDecisionV1
- ExecWorker: Consumes RiskDecisionV1 (allowed), produces ExecutionReportV1
- PositionStoreWorker: Consumes ExecutionReportV1, updates SQLite

All workers are deterministic and single-threaded.

Part of ticket AG-3D-3-1.
"""

from typing import Any, Dict, List, Optional
import logging

from bus import InMemoryBus, BusEnvelope
from contracts.events_v1 import OrderIntentV1, RiskDecisionV1, ExecutionReportV1
from state.position_store_sqlite import PositionStoreSQLite

logger = logging.getLogger(__name__)

# Topic constants
TOPIC_ORDER_INTENT = "order_intent"
TOPIC_RISK_DECISION = "risk_decision"
TOPIC_EXECUTION_REPORT = "execution_report"


class RiskWorker:
    """
    Consumes OrderIntentV1 from order_intent topic.
    Produces RiskDecisionV1 to risk_decision topic.
    """
    
    def __init__(
        self,
        risk_manager,
        *,
        gen_event_id=None,
    ):
        """
        Initialize RiskWorker.
        
        Args:
            risk_manager: RiskManager instance (v0.4 or v0.6)
            gen_event_id: Optional callable to generate deterministic event IDs
        """
        self._rm = risk_manager
        self._gen_event_id = gen_event_id or (lambda: "risk-event-id")
        self._processed_count = 0
    
    def step(self, bus: InMemoryBus, max_items: int = 10) -> int:
        """
        Process up to max_items from order_intent topic.
        
        Returns:
            Number of items processed
        """
        envelopes = bus.poll(TOPIC_ORDER_INTENT, max_items=max_items)
        
        for env in envelopes:
            self._process_one(bus, env)
        
        return len(envelopes)
    
    def _process_one(self, bus: InMemoryBus, env: BusEnvelope) -> None:
        """Process single OrderIntentV1 envelope."""
        payload = env.payload
        trace_id = env.trace_id
        
        # Parse OrderIntentV1
        intent = OrderIntentV1.from_dict(payload)
        
        # Evaluate risk
        # Use filter_signal for v0.4 style
        signal = {
            "assets": [intent.symbol],
            "deltas": {intent.symbol: 0.10},
        }
        
        if hasattr(self._rm, "filter_signal"):
            allowed, annotated = self._rm.filter_signal(signal, {}, nav_eur=10000.0)
            rejection_reasons = annotated.get("risk_reasons", [])
        else:
            # v0.6 style (assess)
            decision = self._rm.assess(intent)
            allowed = decision.allowed
            rejection_reasons = decision.rejection_reasons
        
        # Create RiskDecisionV1
        decision = RiskDecisionV1(
            ref_order_event_id=intent.event_id,
            allowed=allowed,
            rejection_reasons=rejection_reasons,
            trace_id=trace_id,
            event_id=self._gen_event_id(),
            extra={
                "worker": "RiskWorker",
                "bus_seq": env.seq,
            }
        )
        
        # Publish to risk_decision topic
        bus.publish(
            topic=TOPIC_RISK_DECISION,
            event_type="RiskDecisionV1",
            trace_id=trace_id,
            payload=decision.to_dict(),
        )
        
        self._processed_count += 1
        logger.debug("RiskWorker processed intent %s -> allowed=%s", intent.event_id, allowed)


class ExecWorker:
    """
    Consumes RiskDecisionV1 from risk_decision topic.
    If allowed, produces ExecutionReportV1 to execution_report topic.
    """
    
    def __init__(
        self,
        execution_config: Optional[Dict[str, Any]] = None,
        *,
        gen_event_id=None,
        intent_cache: Optional[Dict[str, Dict]] = None,
    ):
        """
        Initialize ExecWorker.
        
        Args:
            execution_config: Config for slippage, fees, etc.
            gen_event_id: Optional callable to generate deterministic event IDs
            intent_cache: Dict mapping ref_order_event_id to intent payload (for fill details)
        """
        self._config = execution_config or {"slippage_bps": 5.0}
        self._gen_event_id = gen_event_id or (lambda: "exec-event-id")
        self._intent_cache = intent_cache if intent_cache is not None else {}
        self._processed_count = 0
        self._fill_count = 0
    
    def step(self, bus: InMemoryBus, max_items: int = 10) -> int:
        """
        Process up to max_items from risk_decision topic.
        
        Returns:
            Number of items processed
        """
        envelopes = bus.poll(TOPIC_RISK_DECISION, max_items=max_items)
        
        for env in envelopes:
            self._process_one(bus, env)
        
        return len(envelopes)
    
    def _process_one(self, bus: InMemoryBus, env: BusEnvelope) -> None:
        """Process single RiskDecisionV1 envelope."""
        payload = env.payload
        trace_id = env.trace_id
        
        decision = RiskDecisionV1.from_dict(payload)
        self._processed_count += 1
        
        if not decision.allowed:
            logger.debug("ExecWorker: decision not allowed, skipping %s", decision.ref_order_event_id)
            return
        
        # Get original intent details from cache (if available)
        intent_payload = self._intent_cache.get(decision.ref_order_event_id, {})
        
        if not intent_payload:
            logger.warning(
                "ExecWorker: No intent in cache for ref_order_event_id=%s. "
                "Cache has %d entries. Keys sample: %s",
                decision.ref_order_event_id,
                len(self._intent_cache),
                list(self._intent_cache.keys())[:3]
            )
        
        # Simulate execution (deterministic)
        slippage_bps = self._config.get("slippage_bps", 5.0)
        fee_bps = self._config.get("fee_bps", 10.0)
        
        # Default fill values
        filled_qty = intent_payload.get("qty", 1.0)
        base_price = intent_payload.get("limit_price") or 100.0
        
        # Apply slippage
        side = intent_payload.get("side", "BUY").upper()
        if side == "BUY":
            avg_price = base_price * (1 + slippage_bps / 10000)
        else:
            avg_price = base_price * (1 - slippage_bps / 10000)
        
        fee = filled_qty * avg_price * (fee_bps / 10000)
        
        # Create ExecutionReportV1
        report = ExecutionReportV1(
            ref_order_event_id=decision.ref_order_event_id,
            status="FILLED",
            filled_qty=filled_qty,
            avg_price=avg_price,
            fee=fee,
            slippage=slippage_bps,
            latency_ms=1.0,
            ref_risk_event_id=decision.event_id,
            trace_id=trace_id,
            event_id=self._gen_event_id(),
            extra={
                "worker": "ExecWorker",
                "bus_seq": env.seq,
                "symbol": intent_payload.get("symbol", "UNKNOWN"),
                "side": side,
            }
        )
        
        # Publish to execution_report topic
        bus.publish(
            topic=TOPIC_EXECUTION_REPORT,
            event_type="ExecutionReportV1",
            trace_id=trace_id,
            payload=report.to_dict(),
        )
        
        self._fill_count += 1
        logger.debug("ExecWorker produced fill for %s", decision.ref_order_event_id)


class PositionStoreWorker:
    """
    Consumes ExecutionReportV1 from execution_report topic.
    Updates SQLite position store.
    """
    
    def __init__(self, store: PositionStoreSQLite):
        """
        Initialize PositionStoreWorker.
        
        Args:
            store: PositionStoreSQLite instance
        """
        self._store = store
        self._processed_count = 0
    
    def step(self, bus: InMemoryBus, max_items: int = 10) -> int:
        """
        Process up to max_items from execution_report topic.
        
        Returns:
            Number of items processed
        """
        envelopes = bus.poll(TOPIC_EXECUTION_REPORT, max_items=max_items)
        
        for env in envelopes:
            self._process_one(env)
        
        return len(envelopes)
    
    def _process_one(self, env: BusEnvelope) -> None:
        """Process single ExecutionReportV1 envelope."""
        payload = env.payload
        
        report = ExecutionReportV1.from_dict(payload)
        
        if report.status not in ("FILLED", "PARTIALLY_FILLED"):
            logger.debug("PositionStoreWorker: status=%s, skipping", report.status)
            return
        
        # Extract symbol and side from extra (set by ExecWorker)
        extra = report.extra or {}
        symbol = extra.get("symbol", "UNKNOWN")
        side = extra.get("side", "BUY")
        
        # Apply fill to store
        self._store.apply_fill(
            symbol=symbol,
            side=side,
            qty=report.filled_qty,
            price=report.avg_price,
        )
        
        self._processed_count += 1
        logger.debug("PositionStoreWorker applied fill: symbol=%s qty=%s", symbol, report.filled_qty)


class DrainWorker:
    """
    Simple worker that drains messages from a topic without processing.
    Used when no consumer is available (e.g., no SQLite store).
    """
    
    def __init__(self, topic: str):
        self._topic = topic
        self._drained_count = 0
    
    def step(self, bus: InMemoryBus, max_items: int = 10) -> int:
        """Drain up to max_items from topic."""
        envelopes = bus.poll(self._topic, max_items=max_items)
        self._drained_count += len(envelopes)
        return len(envelopes)
