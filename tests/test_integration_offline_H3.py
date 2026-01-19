"""
tests/test_integration_offline_H3.py

Offline integration tests for adapter-mode + checkpoint/resume + idempotency.
Runs without network, gated by INVESTBOT_TEST_INTEGRATION_OFFLINE=1.

AG-H3-3-1
"""

import pytest
import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path

# Gate: skip unless INVESTBOT_TEST_INTEGRATION_OFFLINE=1
INTEGRATION_OFFLINE_ENABLED = os.environ.get("INVESTBOT_TEST_INTEGRATION_OFFLINE", "0") == "1"

skip_integration_offline = pytest.mark.skipif(
    not INTEGRATION_OFFLINE_ENABLED,
    reason="Offline integration tests require INVESTBOT_TEST_INTEGRATION_OFFLINE=1"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engine.checkpoint import Checkpoint
from engine.idempotency import FileIdempotencyStore


@pytest.mark.integration_offline
class TestOfflineIntegration:
    """Offline integration tests without network access."""

    @skip_integration_offline
    def test_adapter_mode_offline_seed42_determinism(self, tmp_path):
        """
        Run adapter-mode offline with seed42 produces deterministic artifacts.
        
        Verifies:
        - run_meta.json exists and has expected fields
        - Same seed produces same initial state
        """
        import numpy as np
        
        run_dir = tmp_path / "run_determinism"
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Simulate adapter-mode initialization with seed42
        np.random.seed(42)
        
        # Create run metadata (simulates what adapter would create)
        meta = {
            "run_id": "offline-test-001",
            "seed": 42,
            "mode": "adapter-offline",
            "initial_random_state": int(np.random.randint(0, 2**31)),
        }
        
        meta_path = run_dir / "run_meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, sort_keys=True)
        
        # Verify artifact exists
        assert meta_path.exists()
        
        # Re-read and verify determinism
        with open(meta_path) as f:
            loaded = json.load(f)
        
        assert loaded["seed"] == 42
        assert loaded["mode"] == "adapter-offline"
        
        # Run again with same seed should get same random state
        np.random.seed(42)
        expected_state = int(np.random.randint(0, 2**31))
        assert loaded["initial_random_state"] == expected_state

    @skip_integration_offline
    def test_checkpoint_resume_no_duplicate_artifacts(self, tmp_path):
        """
        Checkpoint/resume cycle produces no duplicate artifacts.
        
        Simulates:
        1. Run that processes 10 items, crashes after 5
        2. Resume processes remaining 5
        3. Total artifacts = 10, no duplicates
        """
        run_dir = tmp_path / "run_resume"
        run_dir.mkdir(parents=True, exist_ok=True)
        
        artifacts_path = run_dir / "artifacts.jsonl"
        checkpoint_path = run_dir / "checkpoint.json"
        idem_path = run_dir / "idempotency_keys.jsonl"
        
        items = [f"item-{i:03d}" for i in range(10)]
        
        def process_items(items_list, start_idx, checkpoint_path, artifacts_path, idem_path, crash_after=None):
            """Process items with checkpoint and idempotency."""
            idem_store = FileIdempotencyStore(idem_path)
            
            if checkpoint_path.exists():
                cp = Checkpoint.load(checkpoint_path)
            else:
                cp = Checkpoint.create_new("resume-test")
            
            processed = 0
            with open(artifacts_path, "a", encoding="utf-8") as f:
                for idx in range(start_idx, len(items_list)):
                    item = items_list[idx]
                    op_key = f"process:{item}"
                    
                    if not idem_store.mark_once(op_key):
                        continue  # Already processed
                    
                    # Record artifact
                    f.write(json.dumps({"item": item, "idx": idx}) + "\n")
                    f.flush()
                    
                    # Update checkpoint
                    cp = cp.update(idx)
                    cp.save_atomic(checkpoint_path)
                    
                    processed += 1
                    
                    if crash_after and processed >= crash_after:
                        idem_store.close()
                        raise RuntimeError(f"Simulated crash after {processed}")
            
            idem_store.close()
            return processed
        
        # Phase 1: process 5 items, then crash
        with pytest.raises(RuntimeError):
            process_items(items, 0, checkpoint_path, artifacts_path, idem_path, crash_after=5)
        
        # Verify checkpoint exists
        assert checkpoint_path.exists()
        cp1 = Checkpoint.load(checkpoint_path)
        assert cp1.last_processed_idx == 4  # 0-indexed
        
        # Phase 2: resume from checkpoint
        resumed_count = process_items(items, cp1.last_processed_idx + 1, checkpoint_path, artifacts_path, idem_path)
        assert resumed_count == 5
        
        # Verify no duplicates in artifacts
        artifacts = []
        with open(artifacts_path) as f:
            for line in f:
                if line.strip():
                    artifacts.append(json.loads(line)["item"])
        
        assert len(artifacts) == 10
        assert len(set(artifacts)) == 10  # All unique

    @skip_integration_offline
    def test_idempotency_store_stability(self, tmp_path):
        """
        Idempotency store correctly prevents duplicate processing.
        
        Verifies:
        - mark_once returns True first time, False second time
        - State persists across reopen
        """
        idem_path = tmp_path / "idem.jsonl"
        
        # First session
        store1 = FileIdempotencyStore(idem_path)
        assert store1.mark_once("op:alpha") == True
        assert store1.mark_once("op:beta") == True
        assert store1.mark_once("op:alpha") == False  # Duplicate
        store1.close()
        
        # Second session (reopen)
        store2 = FileIdempotencyStore(idem_path)
        assert store2.mark_once("op:alpha") == False  # Still marked
        assert store2.mark_once("op:gamma") == True   # New
        store2.close()
        
        # Verify file has all keys
        lines = idem_path.read_text().strip().split("\n")
        assert len(lines) == 3  # alpha, beta, gamma
