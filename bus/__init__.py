"""
bus/__init__.py

Event bus abstractions and implementations.

Exports:
- BusEnvelope: Immutable message envelope
- BusBase: Protocol for bus implementations
- InMemoryBus: Deterministic in-memory implementation
"""

from .bus_base import BusBase, BusEnvelope
from .inmemory_bus import InMemoryBus

__all__ = ["BusBase", "BusEnvelope", "InMemoryBus"]
