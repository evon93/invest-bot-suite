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
from engine.exchange_adapter import ExchangeAdapter, PaperExchangeAdapter, ExecutionContext, TransientNetworkError
from engine.retry_policy import RetryPolicy, retry_call, RetryExhaustedError
from engine.idempotency import IdempotencyStore, InMemoryIdempotencyStore

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
        jsonl_logger=None,
    ):
        """
        Initialize RiskWorker.
        
        Args:
            risk_manager: RiskManager instance (v0.4 or v0.6)
            gen_event_id: Optional callable to generate deterministic event IDs
            jsonl_logger: Optional structured JSONL logger
        """
        self._rm = risk_manager
        self._gen_event_id = gen_event_id or (lambda: "risk-event-id")
        self._jsonl_logger = jsonl_logger
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
        
        # Log event if logger configured
        if self._jsonl_logger:
            from engine.structured_jsonl_logger import log_event
            log_event(
                self._jsonl_logger,
                trace_id=trace_id,
                event_type="RiskDecisionV1",
                step_id=self._processed_count,
                action="publish",
                topic=TOPIC_RISK_DECISION,
                extra={
                    "allowed": allowed,
                    "rejection_reasons": rejection_reasons,
                    "ref_order_event_id": decision.ref_order_event_id,
                },
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
        exchange_adapter: Optional[ExchangeAdapter] = None,
        gen_event_id=None,
        intent_cache: Optional[Dict[str, Dict]] = None,
        jsonl_logger=None,
        retry_policy: Optional[RetryPolicy] = None,
        idempotency_store: Optional[IdempotencyStore] = None,
        sleep_fn=None,
    ):
        """
        Initialize ExecWorker.
        
        Args:
            execution_config: Config for slippage, fees, etc.
            gen_event_id: Optional callable to generate deterministic event IDs
            intent_cache: Dict mapping ref_order_event_id to intent payload (for fill details)
            jsonl_logger: Optional structured JSONL logger
            retry_policy: Optional RetryPolicy for retrying failed submissions
            idempotency_store: Optional IdempotencyStore for preventing duplicates
            sleep_fn: Optional sleep function (ms) for retry delays (no-op by default)
        """
        self._config = execution_config or {"slippage_bps": 5.0}
        
        # Initialize adapter
        if exchange_adapter:
            self._adapter = exchange_adapter
        else:
            # Default to Paper with config
            slippage = self._config.get("slippage_bps", 5.0)
            fee = self._config.get("fee_bps", 10.0)
            self._adapter = PaperExchangeAdapter(slippage_bps=slippage, fee_bps=fee)
            
        self._gen_event_id = gen_event_id or (lambda: "exec-event-id")
        self._intent_cache = intent_cache if intent_cache is not None else {}
        self._jsonl_logger = jsonl_logger
        self._processed_count = 0
        self._fill_count = 0
        
        # Retry and idempotency
        self._retry_policy = retry_policy
        self._idempotency_store = idempotency_store
        self._sleep_fn = sleep_fn or (lambda ms: None)  # No-op default for paper/simulated
        self._retry_attempts_total = 0  # For observability
    
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
        
        # Get original intent details from cache (REQUIRED)
        intent_payload = self._intent_cache.get(decision.ref_order_event_id)
        
        # FAIL-FAST: No defaults allowed for missing cache entries
        if not intent_payload:
            raise ValueError(
                f"ExecWorker cache miss: ref_order_event_id={decision.ref_order_event_id} "
                f"trace_id={trace_id} not found in intent_cache. "
                f"Cache has {len(self._intent_cache)} entries. "
                "Cannot process execution without original intent data."
            )
        
        # Validate required fields FIRST (order matters for error messages)
        symbol = intent_payload.get("symbol")
        if not symbol:
            raise ValueError(
                f"ExecWorker: Missing symbol for ref_order_event_id={decision.ref_order_event_id}"
            )
        
        side = intent_payload.get("side", "").upper()
        if side not in ("BUY", "SELL"):
            raise ValueError(
                f"ExecWorker: Invalid side={side} for ref_order_event_id={decision.ref_order_event_id}"
            )
        
        filled_qty = intent_payload.get("qty")
        if filled_qty is None or filled_qty <= 0:
            raise ValueError(
                f"ExecWorker: Invalid qty={filled_qty} for ref_order_event_id={decision.ref_order_event_id}"
            )
        
        # Try to get price from various sources
        base_price = intent_payload.get("limit_price")
        if not base_price or base_price <= 0:
            # Try notional / qty
            notional = intent_payload.get("notional")
            if notional and notional > 0:
                base_price = notional / filled_qty
        if not base_price or base_price <= 0:
            # Fallback to meta (current_price, close, bar_close)
            meta = intent_payload.get("meta", {})
            base_price = meta.get("current_price") or meta.get("close") or meta.get("bar_close")
        if not base_price or base_price <= 0:
            raise ValueError(
                f"ExecWorker: No valid price available for ref_order_event_id={decision.ref_order_event_id}"
            )
        
        # Prepare Context
        # Note: intent_payload contains meta, which we might need.
        # Reconstruct OrderIntentV1 is ideal but expensive/redundant if we just pass dict?
        # Adapter expects OrderIntentV1. Let's reconstruct it quickly or pass a shell.
        # Actually ExecWorker had 'symbol' etc from intent_payload.
        # To satisfy Protocol, we must pass intent object.
        intent = OrderIntentV1.from_dict(intent_payload)
        
        exec_ctx: ExecutionContext = {
            "step_id": self._processed_count,
            "time_provider": None # We don't have access to time_provider here easily unless injected
        }
        
        # Pass ts from intent if available for the report
        if "ts" in intent_payload:
            intent_payload["ts"] = intent_payload["ts"]
            
        # Delegate to Adapter
        report_event_id = self._gen_event_id()
        
        # Extract meta from intent to help adapter find price
        extra_meta = intent_payload.get("meta", {}).copy()
        extra_meta["ts"] = intent_payload.get("ts") # Ensure TS is available
        
        # Generate stable op_key for idempotency and retry
        op_key = f"exec:{decision.ref_order_event_id}"
        
        # Idempotency check: skip if already processed
        if self._idempotency_store:
            if not self._idempotency_store.mark_once(op_key):
                logger.debug("ExecWorker: duplicate op_key=%s, skipping", op_key)
                return  # Skip duplicate - no report generated
        
        # Define submit function for retry wrapper
        def do_submit():
            return self._adapter.submit(
                intent=intent,
                decision=decision,
                context=exec_ctx,
                report_event_id=report_event_id,
                extra_meta=extra_meta
            )
        
        # Execute with retry if policy configured
        try:
            if self._retry_policy:
                # Retry only on transient network errors (including SimulatedRealtimeAdapter's TransientNetworkError)
                def is_retryable(e):
                    return isinstance(e, (ConnectionError, TimeoutError, OSError, TransientNetworkError))
                
                report, attempts = retry_call(
                    do_submit,
                    is_retryable_exc=is_retryable,
                    policy=self._retry_policy,
                    op_key=op_key,
                    sleep_fn=self._sleep_fn,
                )
                self._retry_attempts_total += attempts
            else:
                report = do_submit()
            
            # Enrich extra from worker context if needed (e.g. bus_seq)
            if not report.extra:
                report.extra = {}
            report.extra["worker"] = "ExecWorker"
            report.extra["bus_seq"] = env.seq
            
        except RetryExhaustedError as e:
            # All retries failed - log and skip (don't crash the worker)
            logger.error("ExecWorker: retries exhausted for op_key=%s: %s", op_key, e.last_exception)
            return  # Skip - no report generated
        except ValueError as e:
            # Re-raise or log? The requirement says "maintain fail-fast in cache miss".
            # Cache miss checks happen ABOVE this block (lines 197-203).
            # Price missing might raise ValueError in adapter. 
            # We allow it to propagate to crash/fail-fast as per current behavior logic.
            raise e
        
        # Publish to execution_report topic
        bus.publish(
            topic=TOPIC_EXECUTION_REPORT,
            event_type="ExecutionReportV1",
            trace_id=trace_id,
            payload=report.to_dict(),
        )
        
        # Log event if logger configured
        if self._jsonl_logger:
            from engine.structured_jsonl_logger import log_event
            log_event(
                self._jsonl_logger,
                trace_id=trace_id,
                event_type="ExecutionReportV1",
                step_id=self._processed_count,
                action="publish",
                topic=TOPIC_EXECUTION_REPORT,
                extra={
                    "status": report.status,
                    "filled_qty": report.filled_qty,
                    "avg_price": report.avg_price,
                    "ref_order_event_id": report.ref_order_event_id,
                },
            )
        
        self._fill_count += 1
        logger.debug("ExecWorker produced fill for %s", decision.ref_order_event_id)


class PositionStoreWorker:
    """
    Consumes ExecutionReportV1 from execution_report topic.
    Updates SQLite position store.
    """
    
    def __init__(self, store: PositionStoreSQLite, jsonl_logger=None):
        """
        Initialize PositionStoreWorker.
        
        Args:
            store: PositionStoreSQLite instance
            jsonl_logger: Optional structured JSONL logger
        """
        self._store = store
        self._jsonl_logger = jsonl_logger
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
        trace_id = env.trace_id
        
        report = ExecutionReportV1.from_dict(payload)
        
        if report.status not in ("FILLED", "PARTIALLY_FILLED"):
            logger.debug("PositionStoreWorker: status=%s, skipping", report.status)
            return
        
        # Extract symbol and side from extra (set by ExecWorker)
        extra = report.extra or {}
        symbol = extra.get("symbol", "UNKNOWN")
        side = extra.get("side", "BUY")
        
        # Apply fill to store (returns updated position dict)
        new_pos = self._store.apply_fill(
            symbol=symbol,
            side=side,
            qty=report.filled_qty,
            price=report.avg_price,
        )
        
        # Log event if logger configured
        if self._jsonl_logger:
            from engine.structured_jsonl_logger import log_event
            
            # 1. Existing Log (PositionUpdated) - maintaining backward compatibility/existing trace
            log_event(
                self._jsonl_logger,
                trace_id=trace_id,
                event_type="PositionUpdated",
                step_id=self._processed_count,
                action="persist",
                topic=None,  # No topic produced
                extra={
                    "symbol": symbol,
                    "side": side,
                    "qty": report.filled_qty,
                    "price": report.avg_price,
                    "ref_exec_report_id": report.event_id,
                },
            )

            # 2. PROPOSED: position_changed (Observability Gap Gap)
            # Payload: symbol, qty (holding), avg_px, step_id
            # We use the new_pos dict returned by apply_fill
            log_event(
                self._jsonl_logger,
                trace_id=trace_id,
                event_type="position_changed",
                step_id=self._processed_count, 
                action="state_change",
                topic=None,
                extra={
                    "symbol": symbol,
                    "qty": new_pos.get("qty", 0.0),
                    "avg_px": new_pos.get("avg_price"),
                    "step_id": self._processed_count, # Deterministic worker step
                },
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
