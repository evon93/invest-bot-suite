"""
test_freeze_topk_2H.py — Tests for freeze_topk_2H.py

Verification of:
1. Determinism (byte-for-byte output equality).
2. Tie-breaking logic (combo_id prefered over param_id over hash).
3. Schema (required keys present).
"""
import pytest
import pandas as pd
import json
import hashlib
import sys
import subprocess
from pathlib import Path

# Tool path
TOOL_PATH = Path(__file__).resolve().parent.parent / "tools" / "freeze_topk_2H.py"
REPO_ROOT = Path(__file__).resolve().parent.parent

class TestFreezeTopK:

    def test_freeze_determinism(self, tmp_path):
        """
        Running the tool twice on the same input must yield identical output files.
        """
        # Create synthesis results_agg.csv
        csv_path = tmp_path / "results_agg.csv"
        df = pd.DataFrame([
            {"combo_id": "C2", "score_robust": 10.0, "param_a": 1, "param_b": 2},
            {"combo_id": "C1", "score_robust": 10.0, "param_a": 10, "param_b": 20}, # Tie in score, C1 < C2 should win
            {"combo_id": "C3", "score_robust": 5.0,  "param_a": 5, "param_b": 6},
        ])
        df.to_csv(csv_path, index=False)
        
        out_cfg_1 = tmp_path / "cfg1.json"
        out_rep_1 = tmp_path / "rep1.json"
        out_cfg_2 = tmp_path / "cfg2.json"
        out_rep_2 = tmp_path / "rep2.json"

        # Run 1
        subprocess.run([sys.executable, str(TOOL_PATH), 
                        "--results-agg", str(csv_path),
                        "--out-config", str(out_cfg_1),
                        "--out-report", str(out_rep_1)], check=True, cwd=str(REPO_ROOT))

        # Run 2
        subprocess.run([sys.executable, str(TOOL_PATH), 
                        "--results-agg", str(csv_path),
                        "--out-config", str(out_cfg_2),
                        "--out-report", str(out_rep_2)], check=True, cwd=str(REPO_ROOT))

        # Check binary equality
        assert out_cfg_1.read_bytes() == out_cfg_2.read_bytes()
        assert out_rep_1.read_bytes() == out_rep_2.read_bytes()

    def test_tie_breaking(self, tmp_path):
        """
        Tie-breaking logic: score desc, then combo_id asc.
        """
        csv_path = tmp_path / "results_agg.csv"
        # C1 and C2 have same score. C1 lexicographically smaller -> should be rank 1.
        df = pd.DataFrame([
            {"combo_id": "B_combo", "score_robust": 100.0, "param_x": 1},
            {"combo_id": "A_combo", "score_robust": 100.0, "param_x": 2},
        ])
        df.to_csv(csv_path, index=False)
        
        out_cfg = tmp_path / "best.json"
        out_rep = tmp_path / "topk.json"

        subprocess.run([sys.executable, str(TOOL_PATH), 
                        "--results-agg", str(csv_path),
                        "--out-config", str(out_cfg),
                        "--out-report", str(out_rep)], check=True, cwd=str(REPO_ROOT))

        with open(out_cfg, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Expect A_combo to be selected (A < B)
        assert data["selected"]["combo_id"] == "A_combo"
        assert data["selected"]["score_value"] == 100.0
        assert data["selected"]["params"]["param_x"] == 2

    def test_schema_and_meta(self, tmp_path):
        """
        Verify output JSON schema structure and metadata.
        """
        csv_path = tmp_path / "results_agg.csv"
        df = pd.DataFrame([
            {"combo_id": "C1", "score": 50.0}, # Fallback to score
        ])
        df.to_csv(csv_path, index=False)
        
        out_cfg = tmp_path / "best.json"
        out_rep = tmp_path / "topk.json"

        subprocess.run([sys.executable, str(TOOL_PATH), 
                        "--results-agg", str(csv_path),
                        "--out-config", str(out_cfg),
                        "--out-report", str(out_rep)], check=True, cwd=str(REPO_ROOT))

        with open(out_cfg, "r") as f:
            cfg = json.load(f)
        
        assert "selected" in cfg
        assert "meta" in cfg
        assert "source_results_agg_sha256" in cfg["meta"]
        assert "git_commit" in cfg["meta"]
        assert cfg["selected"]["combo_id"] == "C1"
        assert cfg["selected"]["score_column"] == "score"

    def test_param_detection_heuristic(self, tmp_path):
        """
        Verify heuristic for param detection columns.
        """
        csv_path = tmp_path / "results_agg.csv"
        df = pd.DataFrame([
            {"combo_id": "C1", "score_robust": 10.0, 
             "param_abc": 1, "param_xyz": 2, 
             "max_drawdown_median": -0.1, "random_col": "ignore"}
        ])
        # random_col might be included if it doesn't match exclusions. 
        # But let's check explicit param_ prefix works.
        df.to_csv(csv_path, index=False)
        
        out_cfg = tmp_path / "out.json"
        
        subprocess.run([sys.executable, str(TOOL_PATH), 
                        "--results-agg", str(csv_path),
                        "--out-config", str(out_cfg),
                        "--out-report", str(tmp_path/"rep.json")], check=True, cwd=str(REPO_ROOT))

        with open(out_cfg, "r") as f:
            cfg = json.load(f)
            
        params = cfg["selected"]["params"]
        assert "param_abc" in params
        assert "param_xyz" in params
        assert "max_drawdown_median" not in params
