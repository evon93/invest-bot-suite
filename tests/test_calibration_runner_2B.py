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
        
        # --- 2. Verificar columnas en CSV ---
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

    def test_runner_activity_columns(self, tmp_path):
        """Verifica nuevas columnas is_active y rejection_* en results.csv."""
        output_dir = tmp_path / "calibration_output"
        
        result = subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "quick",
                "--max-combinations", "3",
                "--seed", "42",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        
        csv_content = (output_dir / "results.csv").read_text()
        header_line = csv_content.split("\n")[0]
        
        # Nuevas columnas 2E
        assert "is_active" in header_line, "is_active column missing"
        assert "rejection_no_signal" in header_line, "rejection_no_signal column missing"
        assert "rejection_blocked_risk" in header_line, "rejection_blocked_risk column missing"
        assert "rejection_size_zero" in header_line, "rejection_size_zero column missing"
        assert "rejection_price_missing" in header_line, "rejection_price_missing column missing"
        assert "rejection_other" in header_line, "rejection_other column missing"

    def test_runner_meta_activity_fields(self, tmp_path):
        """Verifica nuevos campos en run_meta.json relacionados con activity/gates."""
        output_dir = tmp_path / "calibration_output"
        
        result = subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "quick",
                "--max-combinations", "3",
                "--seed", "42",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        
        meta_data = json.loads((output_dir / "run_meta.json").read_text())
        
        # Nuevos campos 2E
        assert "active_n" in meta_data, "active_n missing from run_meta.json"
        assert "inactive_n" in meta_data, "inactive_n missing from run_meta.json"
        assert "active_rate" in meta_data, "active_rate missing from run_meta.json"
        assert "inactive_rate" in meta_data, "inactive_rate missing from run_meta.json"
        assert "active_pass_rate" in meta_data, "active_pass_rate missing from run_meta.json"
        assert "gate_passed" in meta_data, "gate_passed missing from run_meta.json"
        assert "insufficient_activity" in meta_data, "insufficient_activity missing from run_meta.json"
        assert "gate_fail_reasons" in meta_data, "gate_fail_reasons missing from run_meta.json"
        assert "suggested_exit_code" in meta_data, "suggested_exit_code missing from run_meta.json"
        assert "rejection_reasons_agg" in meta_data, "rejection_reasons_agg missing from run_meta.json"
        assert "top_inactive_reasons" in meta_data, "top_inactive_reasons missing from run_meta.json"
        
        # Tipos correctos
        assert isinstance(meta_data["active_n"], int), "active_n should be int"
        assert isinstance(meta_data["gate_passed"], bool), "gate_passed should be bool"
        assert isinstance(meta_data["gate_fail_reasons"], list), "gate_fail_reasons should be list"

    def test_runner_topk_has_is_active(self, tmp_path):
        """Verifica que topk.json incluye is_active en cada candidato."""
        output_dir = tmp_path / "calibration_output"
        
        result = subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "quick",
                "--max-combinations", "3",
                "--seed", "42",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        
        topk_data = json.loads((output_dir / "topk.json").read_text())
        
        for candidate in topk_data.get("candidates", []):
            assert "is_active" in candidate, f"is_active missing from candidate {candidate.get('combo_id')}"

    def test_strict_gate_flag_exists(self, tmp_path):
        """Verifica que --strict-gate flag está disponible."""
        result = subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--help",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=REPO_ROOT,
        )
        
        assert "--strict-gate" in result.stdout, "--strict-gate flag should be in help"
