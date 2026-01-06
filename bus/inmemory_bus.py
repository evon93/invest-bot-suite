"""
bus/inmemory_bus.py

In-memory event bus implementation.

Features:
- FIFO per-topic queues (deque)
- Global monotonic seq counter for total ordering
- No external dependencies
- Deterministic (no timestamps, no randomness)

Part of ticket AG-3D-2-1.
"""

from collections import deque
from typing import Any, Dict, List

from .bus_base import BusBase, BusEnvelope


class InMemoryBus(BusBase):
    """
    In-memory event bus with deterministic behavior.
    
    Design:
    - Uses global seq counter (not per-topic) for total ordering
    - FIFO queues per topic using deque
    - Thread-safe for single-threaded use (no locks needed)
    
    Example:
        bus = InMemoryBus()
        env = bus.publish("order_intent", "OrderIntentV1", "T-001", {"qty": 10})
        events = bus.poll("order_intent", max_items=1)
    """
    
    def __init__(self) -> None:
        """Initialize empty bus with seq counter at 0."""
        self._seq: int = 0
        self._queues: Dict[str, deque[BusEnvelope]] = {}
    
    def _next_seq(self) -> int:
        """Get next sequence number (global monotonic)."""
        self._seq += 1
        return self._seq
    
    def _get_queue(self, topic: str) -> deque[BusEnvelope]:
        """Get or create queue for topic."""
        if topic not in self._queues:
            self._queues[topic] = deque()
        return self._queues[topic]
    
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
        envelope = BusEnvelope(
            seq=self._next_seq(),
            topic=topic,
            event_type=event_type,
            trace_id=trace_id,
            payload=payload,
        )
        self._get_queue(topic).append(envelope)
        return envelope
    
    def poll(self, topic: str, max_items: int = 1) -> List[BusEnvelope]:
        """
        Poll events from a topic (FIFO).
        
        Args:
            topic: Topic to poll from
            max_items: Maximum number of envelopes to return
            
        Returns:
            List of BusEnvelope (empty if no messages)
        """
        queue = self._get_queue(topic)
        result: List[BusEnvelope] = []
        
        for _ in range(min(max_items, len(queue))):
            result.append(queue.popleft())
        
        return result
    
    def size(self, topic: str) -> int:
        """
        Get number of pending events in a topic.
        
        Args:
            topic: Topic to check
            
        Returns:
            Number of pending envelopes
        """
        return len(self._get_queue(topic))
    
    def clear(self, topic: str | None = None) -> None:
        """
        Clear events from topic(s).
        
        Args:
            topic: Specific topic to clear, or None for all topics
        """
        if topic is None:
            self._queues.clear()
            self._seq = 0
        elif topic in self._queues:
            self._queues[topic].clear()
