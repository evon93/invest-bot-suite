"""
engine/checkpoint.py

Atomic checkpoint persistence for crash recovery.
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class Checkpoint:
    """
    Checkpoint state for crash recovery.
    
    Attributes:
        run_id: Unique identifier for this run
        last_processed_idx: Index of last successfully processed item (0-indexed)
        processed_count: Total number of items processed so far
        updated_at: ISO timestamp of last update
    """
    run_id: str
    last_processed_idx: int
    processed_count: int
    updated_at: str
    
    def save_atomic(self, path: Path) -> None:
        """
        Save checkpoint atomically using tmp file + rename.
        
        This ensures the checkpoint file is always valid JSON,
        even if the process crashes mid-write.
        """
        path = Path(path)
        tmp_path = path.with_suffix(".json.tmp")
        
        # Write to temp file
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk
        
        # Atomic rename
        os.replace(tmp_path, path)
    
    @classmethod
    def load(cls, path: Path) -> "Checkpoint":
        """
        Load checkpoint from file.
        
        Raises:
            FileNotFoundError: If checkpoint doesn't exist
            json.JSONDecodeError: If checkpoint is corrupted
        """
        path = Path(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return cls(
            run_id=data["run_id"],
            last_processed_idx=data["last_processed_idx"],
            processed_count=data["processed_count"],
            updated_at=data["updated_at"],
        )
    
    @classmethod
    def create_new(cls, run_id: str) -> "Checkpoint":
        """Create a new checkpoint with initial values."""
        return cls(
            run_id=run_id,
            last_processed_idx=-1,  # Nothing processed yet
            processed_count=0,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def update(self, idx: int) -> "Checkpoint":
        """
        Update checkpoint after processing an item.
        
        Returns a new Checkpoint instance (immutable pattern).
        """
        return Checkpoint(
            run_id=self.run_id,
            last_processed_idx=idx,
            processed_count=self.processed_count + 1,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
