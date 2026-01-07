"""
tests/test_crash_recovery_resume_no_duplicates_3F4.py

Tests for crash recovery: resume without duplicates.
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.checkpoint import Checkpoint
from engine.idempotency import FileIdempotencyStore


class SimulatedProcessor:
    """
    Simulates a processor that can crash and resume.
    Tracks all processed items to verify no duplicates.
    """
    
    def __init__(
        self,
        run_dir: Path,
        crash_after: int = None,  # Crash after N items
    ):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_path = self.run_dir / "checkpoint.json"
        self.idem_path = self.run_dir / "idempotency_keys.jsonl"
        self.effects_path = self.run_dir / "effects.jsonl"  # Track side effects
        
        self.crash_after = crash_after
        self._effects_handle = None
    
    def run(self, items: List[str], resume: bool = False) -> int:
        """
        Process items, optionally resuming from checkpoint.
        
        Returns number of items processed in this run.
        Raises RuntimeError after crash_after items (if set).
        """
        # Load or create checkpoint
        if resume and self.checkpoint_path.exists():
            checkpoint = Checkpoint.load(self.checkpoint_path)
            start_idx = checkpoint.last_processed_idx + 1
        else:
            checkpoint = Checkpoint.create_new("test-run")
            start_idx = 0
        
        # Initialize idempotency store
        idem_store = FileIdempotencyStore(self.idem_path)
        
        # Open effects file for appending
        self._effects_handle = open(self.effects_path, "a", encoding="utf-8")
        
        processed_this_run = 0
        
        try:
            for idx in range(start_idx, len(items)):
                item = items[idx]
                op_key = f"process:{item}"
                
                # Check idempotency
                if not idem_store.mark_once(op_key):
                    # Already processed (shouldn't happen in normal flow)
                    continue
                
                # Simulate processing (side effect)
                self._record_effect(item)
                
                # Update checkpoint
                checkpoint = checkpoint.update(idx)
                checkpoint.save_atomic(self.checkpoint_path)
                
                processed_this_run += 1
                
                # Simulate crash
                if self.crash_after and processed_this_run >= self.crash_after:
                    raise RuntimeError(f"Simulated crash after {processed_this_run} items")
        
        finally:
            self._effects_handle.close()
            idem_store.close()
        
        return processed_this_run
    
    def _record_effect(self, item: str) -> None:
        """Record a side effect (simulates actual work)."""
        self._effects_handle.write(json.dumps({"item": item}) + "\n")
        self._effects_handle.flush()
    
    def get_all_effects(self) -> List[str]:
        """Get all recorded effects."""
        effects = []
        if self.effects_path.exists():
            with open(self.effects_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        effects.append(data["item"])
        return effects
    
    def get_checkpoint(self) -> Checkpoint:
        """Get current checkpoint."""
        return Checkpoint.load(self.checkpoint_path)


class TestCrashRecoveryResume:
    """Tests for crash recovery resume without duplicates."""
    
    def test_resume_no_duplicates(self):
        """
        Crash after K items, resume completes without duplicates.
        
        Scenario:
        - 20 items total
        - Crash after 7
        - Resume processes remaining 13
        - Total effects = 20 (no duplicates)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            items = [f"item-{i:03d}" for i in range(20)]
            
            # First run: crash after 7
            processor1 = SimulatedProcessor(run_dir, crash_after=7)
            
            with pytest.raises(RuntimeError) as exc_info:
                processor1.run(items, resume=False)
            
            assert "Simulated crash after 7 items" in str(exc_info.value)
            
            # Verify partial progress
            effects_after_crash = processor1.get_all_effects()
            assert len(effects_after_crash) == 7
            
            checkpoint = processor1.get_checkpoint()
            assert checkpoint.last_processed_idx == 6  # 0-indexed
            assert checkpoint.processed_count == 7
            
            # Second run: resume without crash
            processor2 = SimulatedProcessor(run_dir, crash_after=None)
            processed = processor2.run(items, resume=True)
            
            assert processed == 13  # Remaining items
            
            # Verify no duplicates
            all_effects = processor2.get_all_effects()
            assert len(all_effects) == 20
            assert len(set(all_effects)) == 20  # All unique
            
            # Verify final checkpoint
            final_checkpoint = processor2.get_checkpoint()
            assert final_checkpoint.last_processed_idx == 19
            assert final_checkpoint.processed_count == 20
    
    def test_processed_count_final(self):
        """Final processed_count equals total items."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            items = [f"item-{i:03d}" for i in range(15)]
            
            # Run without crash
            processor = SimulatedProcessor(run_dir, crash_after=None)
            processed = processor.run(items, resume=False)
            
            assert processed == 15
            
            checkpoint = processor.get_checkpoint()
            assert checkpoint.processed_count == 15
    
    def test_multiple_crashes_and_resumes(self):
        """Multiple crash/resume cycles still produce no duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            items = [f"item-{i:03d}" for i in range(30)]
            
            # First run: crash after 5
            processor1 = SimulatedProcessor(run_dir, crash_after=5)
            with pytest.raises(RuntimeError):
                processor1.run(items, resume=False)
            
            # Second run: crash after 10 more
            processor2 = SimulatedProcessor(run_dir, crash_after=10)
            with pytest.raises(RuntimeError):
                processor2.run(items, resume=True)
            
            # Third run: complete
            processor3 = SimulatedProcessor(run_dir, crash_after=None)
            processor3.run(items, resume=True)
            
            # Verify no duplicates
            all_effects = processor3.get_all_effects()
            assert len(all_effects) == 30
            assert len(set(all_effects)) == 30
    
    def test_resume_from_scratch_if_no_checkpoint(self):
        """Resume without checkpoint starts from beginning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "run"
            items = [f"item-{i:03d}" for i in range(10)]
            
            # Run with resume=True but no existing checkpoint
            processor = SimulatedProcessor(run_dir, crash_after=None)
            processed = processor.run(items, resume=True)
            
            assert processed == 10
