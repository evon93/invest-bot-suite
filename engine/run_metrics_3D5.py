"""
engine/run_metrics_3D5.py

Collects deterministic run metrics from structured JSONL logs.

Metrics:
- Counts of events (intents, decisions, reports)
- Risk outcomes (allowed/rejected)
- System stats (drain_iterations, unique traces)

Part of ticket AG-3D-5-1.
"""

import json
from pathlib import Path
from typing import Dict, Any, Union


def collect_metrics_from_jsonl(log_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Parse JSONL log file and calculate metrics.
    
    Args:
        log_path: Path to JSONL file
        
    Returns:
        Dictionary with metrics. No timestamps.
    """
    metrics = {
        "num_order_intents": 0,
        "num_risk_decisions_total": 0,
        "num_risk_allowed": 0,
        "num_risk_rejected": 0,
        "num_execution_reports": 0,
        "num_fills": 0,
        "num_positions_updated": 0,
        "drain_iterations": 0,
        "max_step_id": 0,
        "unique_trace_ids": 0,
    }
    
    trace_ids = set()
    
    path = Path(log_path)
    if not path.exists():
        return metrics
    
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            
            event_type = record.get("event_type")
            action = record.get("action")
            trace_id = record.get("trace_id")
            step_id = record.get("step_id", 0)
            extra = record.get("extra", {})
            
            # Track max step
            if isinstance(step_id, int) and step_id > metrics["max_step_id"]:
                metrics["max_step_id"] = step_id
            
            # Track trace IDs (exclude SYSTEM)
            if trace_id and trace_id != "SYSTEM":
                trace_ids.add(trace_id)
            
            # Count events
            if event_type == "OrderIntentV1" and action == "publish":
                metrics["num_order_intents"] += 1
                
            elif event_type == "RiskDecisionV1" and action == "publish":
                metrics["num_risk_decisions_total"] += 1
                if extra.get("allowed"):
                    metrics["num_risk_allowed"] += 1
                else:
                    metrics["num_risk_rejected"] += 1
                    
            elif event_type == "ExecutionReportV1" and action == "publish":
                metrics["num_execution_reports"] += 1
                status = extra.get("status")
                if status in ("FILLED", "PARTIALLY_FILLED"):
                    metrics["num_fills"] += 1
                    
            elif event_type == "PositionUpdated" and action == "persist":
                metrics["num_positions_updated"] += 1
                
            elif event_type == "BusModeDone" and action == "complete":
                metrics["drain_iterations"] = extra.get("drain_iterations", 0)
    
    metrics["unique_trace_ids"] = len(trace_ids)
    
    # Sort keys for deterministic output dump? 
    # The return is a dict, caller should use json.dump(sort_keys=True)
    return metrics
