"""
engine/metrics_collector.py

Real-time metrics collection for event-driven loop observability.

Features:
- Latency tracking per message (start/end)
- Counters: processed, allowed, rejected, filled, errors, retries, dupes_filtered
- Percentile calculation (p50, p95) with empty-set safety
- Deterministic clock injection for tests
- File-first persistence (NDJSON + summary JSON)

Part of ticket AG-3G-3-1.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any


@dataclass
class MetricsCollector:
    """
    Collects real-time metrics during event processing loop.
    
    Thread-safety: Not thread-safe. Use one collector per worker.
    
    Attributes:
        clock_fn: Function returning monotonic time (injectable for tests)
    """
    clock_fn: Callable[[], float] = field(default_factory=lambda: time.monotonic)
    
    # Internal state
    _starts: Dict[str, float] = field(default_factory=dict, init=False)
    _latencies: List[float] = field(default_factory=list, init=False)
    
    # Counters
    _processed: int = field(default=0, init=False)
    _allowed: int = field(default=0, init=False)
    _rejected: int = field(default=0, init=False)
    _filled: int = field(default=0, init=False)
    _errors: int = field(default=0, init=False)
    _retries: int = field(default=0, init=False)
    _dupes_filtered: int = field(default=0, init=False)
    
    # Error breakdown
    _errors_by_reason: Dict[str, int] = field(default_factory=dict, init=False)
    _rejects_by_reason: Dict[str, int] = field(default_factory=dict, init=False)
    
    def start(self, msg_id: str, t: Optional[float] = None) -> None:
        """
        Record start time for a message.
        
        Args:
            msg_id: Unique message identifier
            t: Optional timestamp (uses clock_fn if not provided)
        """
        self._starts[msg_id] = t if t is not None else self.clock_fn()
    
    def end(
        self,
        msg_id: str,
        status: str,
        reason: Optional[str] = None,
        retry_count: int = 0,
        dupe: bool = False,
        t: Optional[float] = None
    ) -> None:
        """
        Record end of message processing.
        
        Args:
            msg_id: Unique message identifier (must match start())
            status: Outcome status (ALLOWED, REJECTED, FILLED, ERROR)
            reason: Optional reason for rejection/error
            retry_count: Number of retries before this outcome
            dupe: True if message was filtered as duplicate
            t: Optional end timestamp
        """
        end_t = t if t is not None else self.clock_fn()
        
        # Calculate latency if we have start
        if msg_id in self._starts:
            latency = end_t - self._starts[msg_id]
            self._latencies.append(latency)
            del self._starts[msg_id]
        
        self._processed += 1
        self._retries += retry_count
        
        if dupe:
            self._dupes_filtered += 1
            return
        
        status_upper = status.upper()
        
        if status_upper == "ALLOWED":
            self._allowed += 1
        elif status_upper == "REJECTED":
            self._rejected += 1
            if reason:
                self._rejects_by_reason[reason] = self._rejects_by_reason.get(reason, 0) + 1
        elif status_upper in ("FILLED", "PARTIALLY_FILLED"):
            self._filled += 1
        elif status_upper == "ERROR":
            self._errors += 1
            if reason:
                self._errors_by_reason[reason] = self._errors_by_reason.get(reason, 0) + 1
    
    def _percentile(self, p: float) -> Optional[float]:
        """
        Calculate percentile safely.
        
        Returns None if no data available.
        """
        if not self._latencies:
            return None
        
        sorted_lat = sorted(self._latencies)
        n = len(sorted_lat)
        idx = int(p / 100.0 * (n - 1))
        idx = max(0, min(n - 1, idx))
        return sorted_lat[idx]
    
    def snapshot_summary(self) -> Dict[str, Any]:
        """
        Get current metrics snapshot.
        
        Returns:
            Dictionary with all metrics, safe for JSON serialization.
        """
        return {
            "processed": self._processed,
            "allowed": self._allowed,
            "rejected": self._rejected,
            "filled": self._filled,
            "errors": self._errors,
            "retries": self._retries,
            "dupes_filtered": self._dupes_filtered,
            "latency_p50_ms": round(self._percentile(50) * 1000, 3) if self._percentile(50) is not None else None,
            "latency_p95_ms": round(self._percentile(95) * 1000, 3) if self._percentile(95) is not None else None,
            "latency_count": len(self._latencies),
            "errors_by_reason": dict(sorted(self._errors_by_reason.items())),
            "rejects_by_reason": dict(sorted(self._rejects_by_reason.items())),
        }
    
    def reset(self) -> None:
        """Reset all counters and latencies."""
        self._starts.clear()
        self._latencies.clear()
        self._processed = 0
        self._allowed = 0
        self._rejected = 0
        self._filled = 0
        self._errors = 0
        self._retries = 0
        self._dupes_filtered = 0
        self._errors_by_reason.clear()
        self._rejects_by_reason.clear()


class MetricsWriter:
    """
    File-first metrics writer.
    
    Writes:
    - metrics.ndjson: Append-only event stream
    - metrics_summary.json: Final summary
    """
    
    def __init__(self, run_dir: Optional[Path] = None):
        """
        Initialize writer.
        
        Args:
            run_dir: Directory for output files. If None, operates in no-op mode.
        """
        self._run_dir = Path(run_dir) if run_dir else None
        self._ndjson_handle = None
        
        if self._run_dir:
            self._run_dir.mkdir(parents=True, exist_ok=True)
            ndjson_path = self._run_dir / "metrics.ndjson"
            self._ndjson_handle = open(ndjson_path, "a", encoding="utf-8")
    
    @property
    def enabled(self) -> bool:
        """Return True if writer is active (has run_dir)."""
        return self._run_dir is not None
    
    def append_event(self, payload: Dict[str, Any]) -> None:
        """
        Append a metric event to NDJSON file.
        
        Args:
            payload: Event data (will be JSON-serialized)
        """
        if self._ndjson_handle:
            self._ndjson_handle.write(json.dumps(payload, sort_keys=True) + "\n")
            self._ndjson_handle.flush()
    
    def write_summary(self, summary: Dict[str, Any]) -> None:
        """
        Write final summary JSON.
        
        Args:
            summary: Summary dictionary from MetricsCollector.snapshot_summary()
        """
        if self._run_dir:
            summary_path = self._run_dir / "metrics_summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, sort_keys=True, indent=2)
    
    def close(self) -> None:
        """Close file handles."""
        if self._ndjson_handle:
            self._ndjson_handle.close()
            self._ndjson_handle = None
    
    def __del__(self):
        self.close()


# Convenience function for no-op mode
class NoOpMetricsCollector:
    """No-op collector for when metrics are disabled."""
    
    def start(self, msg_id: str, t: Optional[float] = None) -> None:
        pass
    
    def end(
        self,
        msg_id: str,
        status: str,
        reason: Optional[str] = None,
        retry_count: int = 0,
        dupe: bool = False,
        t: Optional[float] = None
    ) -> None:
        pass
    
    def snapshot_summary(self) -> Dict[str, Any]:
        return {}
    
    def reset(self) -> None:
        pass
