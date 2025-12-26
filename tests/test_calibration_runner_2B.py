"""
test_calibration_runner_2B.py — Smoke test del runner de calibración 2B

Ejecuta el runner en modo quick con output.dir temporal para no ensuciar report/.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Repo root para ejecutar el runner
REPO_ROOT = Path(__file__).resolve().parent.parent


class TestCalibrationRunner2B:
    """Smoke tests para el runner de calibración 2B."""

    def test_runner_smoke_comprehensive(self, tmp_path):
        """
        Test comprehensivo: ejecuta runner y verifica todos los artefactos en un solo test.
        
        Verifica:
        - 5 artefactos existen
        - results.csv tiene columnas nuevas
        - topk.json es JSON válido
        - run_meta.json tiene campos requeridos
        """
        output_dir = tmp_path / "calibration_output"
        
        # Ejecutar runner via CLI
        result = subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "quick",
                "--max-combinations", "2",
                "--seed", "42",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        
        # --- 1. Verificar artefactos existen ---
        assert (output_dir / "results.csv").exists(), f"results.csv missing. stderr: {result.stderr}"
        assert (output_dir / "run_log.txt").exists(), "run_log.txt missing"
        assert (output_dir / "summary.md").exists(), "summary.md missing"
        assert (output_dir / "topk.json").exists(), "topk.json missing"
        assert (output_dir / "run_meta.json").exists(), "run_meta.json missing"
        
        # --- 2. Verificar columnas nuevas en CSV ---
        csv_content = (output_dir / "results.csv").read_text()
        header_line = csv_content.split("\n")[0]
        assert "atr_stop_count" in header_line, "atr_stop_count missing from CSV"
        assert "hard_stop_trigger_count" in header_line, "hard_stop_trigger_count missing from CSV"
        assert "pct_time_hard_stop" in header_line, "pct_time_hard_stop missing from CSV"
        assert "missing_risk_events" in header_line, "missing_risk_events missing from CSV"
        
        # --- 3. Verificar topk.json válido ---
        topk_data = json.loads((output_dir / "topk.json").read_text())
        assert isinstance(topk_data, dict), "topk.json should be a dict"
        assert "candidates" in topk_data, "topk.json should have 'candidates'"
        assert isinstance(topk_data["candidates"], list), "candidates should be a list"
        
        # --- 4. Verificar run_meta.json campos ---
        meta_data = json.loads((output_dir / "run_meta.json").read_text())
        assert "seed" in meta_data, "seed missing from run_meta.json"
        assert "mode" in meta_data, "mode missing from run_meta.json"
        assert "num_combos" in meta_data, "num_combos missing from run_meta.json"
        assert "duration_s" in meta_data, "duration_s missing from run_meta.json"
