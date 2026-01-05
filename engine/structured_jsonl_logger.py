"""
engine/structured_jsonl_logger.py

Structured JSONL logging for event traceability.

Features:
- No timestamps (deterministic for CI)
- Each log includes: trace_id, event_type, step_id
- File-based JSONL output

Part of ticket AG-3D-4-1.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union


class JSONLFormatter(logging.Formatter):
    """Formatter that outputs raw message (already JSON)."""
    
    def format(self, record: logging.LogRecord) -> str:
        return record.getMessage()


def get_jsonl_logger(
    path: Union[str, Path],
    name: str = "structured_jsonl",
) -> logging.Logger:
    """
    Create a logger that writes JSONL to file.
    
    Args:
        path: Path to JSONL output file
        name: Logger name (default: structured_jsonl)
        
    Returns:
        Configured logger with FileHandler
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Don't bubble up to root
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Add file handler
    handler = logging.FileHandler(path, mode="a", encoding="utf-8")
    handler.setFormatter(JSONLFormatter())
    logger.addHandler(handler)
    
    return logger


def log_event(
    logger: logging.Logger,
    *,
    trace_id: str,
    event_type: str,
    step_id: int,
    action: str,
    topic: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a structured event as JSONL.
    
    Args:
        logger: Logger instance
        trace_id: Correlation ID
        event_type: Type of event (e.g., OrderIntentV1)
        step_id: Processing step counter
        action: Action being performed (publish, consume, persist)
        topic: Optional topic name
        extra: Optional additional data
    """
    record = {
        "trace_id": trace_id,
        "event_type": event_type,
        "step_id": step_id,
        "action": action,
    }
    
    if topic:
        record["topic"] = topic
    
    if extra:
        record["extra"] = extra
    
    # Deterministic JSON (sorted keys, no whitespace)
    line = json.dumps(record, sort_keys=True, separators=(",", ":"))
    logger.info(line)


def close_jsonl_logger(logger: logging.Logger) -> None:
    """Close all handlers of a logger."""
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
