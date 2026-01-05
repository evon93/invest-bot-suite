"""
bus/bus_base.py

Base abstractions for event bus.

Defines:
- BusEnvelope: Immutable envelope wrapping event payloads
- BusBase: Protocol for bus implementations

Design decisions:
- seq: Global monotonic counter (not per-topic) for total ordering
- No timestamps: Ensures determinism for CI/testing
- Payloads must be JSON-serializable dicts

Part of ticket AG-3D-2-1.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Protocol, runtime_checkable


@dataclass(frozen=True)
class BusEnvelope:
    """
    Immutable envelope for bus messages.
    
    Attributes:
        seq: Global monotonic sequence number (total ordering)
        topic: Destination topic (e.g., 'order_intent', 'risk_decision')
        event_type: Type of event (e.g., 'OrderIntentV1', 'RiskDecisionV1')
        trace_id: Correlation ID for tracing
        payload: JSON-serializable dict with event data
    """
    seq: int
    topic: str
    event_type: str
    trace_id: str
    payload: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert envelope to dict for serialization."""
        return {
            "seq": self.seq,
            "topic": self.topic,
            "event_type": self.event_type,
            "trace_id": self.trace_id,
            "payload": self.payload,
        }


@runtime_checkable
class BusBase(Protocol):
    """
    Protocol for event bus implementations.
    
    All implementations must provide:
    - publish: Send event to topic
    - poll: Retrieve events from topic (FIFO)
    - size: Count pending events in topic
    """
    
    def publish(
        self,
        topic: str,
        event_type: str,
        trace_id: str,
        payload: Dict[str, Any],
    ) -> BusEnvelope:
        """
        Publish an event to a topic.
        
        Args:
            topic: Destination topic
            event_type: Type of event
            trace_id: Correlation ID
            payload: JSON-serializable dict
            
        Returns:
            BusEnvelope with assigned seq number
        """
        ...
    
    def poll(self, topic: str, max_items: int = 1) -> List[BusEnvelope]:
        """
        Poll events from a topic (FIFO).
        
        Args:
            topic: Topic to poll from
            max_items: Maximum number of envelopes to return
            
        Returns:
            List of BusEnvelope (empty if no messages)
        """
        ...
    
    def size(self, topic: str) -> int:
        """
        Get number of pending events in a topic.
        
        Args:
            topic: Topic to check
            
        Returns:
            Number of pending envelopes
        """
        ...
