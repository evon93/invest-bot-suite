"""
test_runner_realdata_wiring_2F3.py — Test realdata wiring in robustness runner

Validates that the runner correctly uses realdata source when configured.
Uses synthetic CSV in tmp_path (no external data required).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestRealdataWiring:
    """Test realdata source wiring in robustness runner."""

    @pytest.fixture
    def synthetic_ohlcv_csv(self, tmp_path):
        """Create a small synthetic OHLCV CSV file."""
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        df = pd.DataFrame({
            "date": dates,
            "open": [100 + i * 0.1 for i in range(100)],
            "high": [105 + i * 0.1 for i in range(100)],
            "low": [95 + i * 0.1 for i in range(100)],
            "close": [102 + i * 0.1 for i in range(100)],
            "volume": [1000 * (i + 1) for i in range(100)],
        })
        path = tmp_path / "test_ohlcv.csv"
        df.to_csv(path, index=False, encoding="utf-8")
        return path

    @pytest.fixture
    def realdata_config(self, tmp_path, synthetic_ohlcv_csv):
        """Create a minimal robustness config with realdata enabled."""
        config = {
            "meta": {
                "schema_version": "1.0.0",
                "description": "Test realdata config",
            },
            "data_source": "realdata",
            "realdata": {"path": str(synthetic_ohlcv_csv)},
            "baseline": {
                "risk_rules_path": "risk_rules.yaml",
                "candidate_params_path": "configs/best_params_2C.json",
                "dataset": {
                    "source": "binance",
                    "symbols": ["BTCUSDT"],
                    "start_date": "2024-01-01",
                    "end_date": "2024-04-01",
                    "frequency": "1d",
                },
            },
            "engine": {
                "reproducibility": {
                    "default_seed": 42,
                    "seed_list": [42],
                    "deterministic_scenario_id": True,
                },
                "modes": {
                    "quick": {
                        "description": "Test mode",
                        "max_scenarios": 2,
                        "seed_count": 1,
                        "param_perturbations_sample": 0.1,
                        "data_perturbations_sample": 0.1,
                        "timeout_minutes": 5,
                    },
                    "full": {
                        "description": "Full mode",
                        "max_scenarios": 10,
                        "seed_count": 1,
                        "param_perturbations_sample": 1.0,
                        "data_perturbations_sample": 1.0,
                        "timeout_minutes": 60,
                    },
                },
            },
            "risk_constraints": {
                "gates": {
                    "quick": {
                        "max_errors": 0,
                        "require_candidate_params": True,
                        "min_trades": 0,
                        "max_drawdown_absolute": -0.99,
                    },
                    "full": {
                        "max_errors": 0,
                        "require_candidate_params": True,
                        "min_trades": 0,
                        "max_drawdown_absolute": -0.99,
                    },
                },
                "warnings": {
                    "max_drawdown_soft": -0.10,
                },
            },
            "sweep": {
                "param_perturbations": {},
                "data_perturbations": {},
            },
            "scenario_id": {
                "format": "{mode}_{seed}_{param_hash}_{data_hash}",
                "max_label_length": 128,
            },
            "output": {
                "directory": str(tmp_path / "output"),
                "files": {
                    "results": "results.csv",
                    "summary": "summary.md",
                    "run_meta": "run_meta.json",
                    "errors": "errors.jsonl",
                },
            },
            "scoring": {
                "enabled": True,
                "weights": {
                    "sharpe_ratio": 1.0,
                    "cagr": 0.5,
                },
            },
        }
        config_path = tmp_path / "realdata_config.yaml"
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f)
        return config_path

    def test_realdata_wiring_produces_results(self, realdata_config, tmp_path):
        """Runner with realdata config produces results.csv and run_meta.json."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        from tools.run_robustness_2D import run_robustness
        
        outdir = tmp_path / "output"
        
        # Call directly instead of subprocess
        meta = run_robustness(
            config_path=realdata_config,
            mode="quick",
            max_scenarios_override=2,
        )
        
        # Check outputs exist
        assert (outdir / "results.csv").exists(), "results.csv not found"
        assert (outdir / "run_meta.json").exists(), "run_meta.json not found"
        
        # Check meta
        assert meta.get("data_source") == "realdata"

    def test_run_meta_has_data_source_realdata(self, realdata_config, tmp_path):
        """run_meta.json should contain data_source='realdata'."""
        outdir = tmp_path / "output"
        
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "run_robustness_2D.py"),
                "--config", str(realdata_config),
                "--mode", "quick",
                "--max-scenarios", "2",
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(REPO_ROOT),
        )
        
        with open(outdir / "run_meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        
        assert meta.get("data_source") == "realdata"
        assert "realdata_path" in meta
        assert "n_rows" in meta

    def test_backward_compat_synthetic_default(self, tmp_path):
        """Config without data_source should default to synthetic."""
        # Use the existing robustness config (synthetic)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        outdir = tmp_path / "synthetic_out"
        
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "run_robustness_2D.py"),
                "--mode", "quick",
                "--max-scenarios", "2",
                "--outdir", str(outdir),
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(REPO_ROOT),
        )
        
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        
        with open(outdir / "run_meta.json", "r", encoding="utf-8") as f:
            meta = json.load(f)
        
        assert meta.get("data_source") == "synthetic"
        assert "realdata_path" not in meta
