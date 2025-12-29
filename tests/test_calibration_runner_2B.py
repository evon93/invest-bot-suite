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
# Repo root para ejecutar el runner
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.run_calibration_2B import classify_inactive_reason


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

    def test_gate_fail_active_rate_below_min(self, tmp_path):
        """
        Verifica que el gate falla con active_rate_below_min cuando 
        active_rate < min_active_rate (60%).
        
        Con kelly grid [0.3, 0.5, 0.7], solo kelly=0.7 produce trades,
        resultando en ~33% active_rate < 60% threshold.
        """
        output_dir = tmp_path / "calibration_output"
        
        # Ejecutar en full mode con profile strict
        result = subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "full",
                "--profile", "full",  # Use strict thresholds
                "--config", "configs/risk_calibration_2B_candidate_kelly05.yaml",  # Control config for gate failure
                "--max-combinations", "12",
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
        
        # Con ~33% active_rate y 60% threshold, debe fallar
        assert meta_data["gate_passed"] is False, "Gate should fail with low active_rate"
        assert "active_rate_below_min" in meta_data["gate_fail_reasons"], \
            f"Should include active_rate_below_min, got: {meta_data['gate_fail_reasons']}"
        assert meta_data["insufficient_activity"] is True, "Should flag insufficient_activity"

    def test_gate_granular_fail_reasons(self, tmp_path):
        """
        Verifica que gate_fail_reasons contiene razones granulares específicas.
        """
        output_dir = tmp_path / "calibration_output"
        
        result = subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "full",
                "--profile", "full",  # Use strict thresholds
                "--config", "configs/risk_calibration_2B_candidate_kelly05.yaml",  # Control config for gate failure
                "--max-combinations", "9",
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
        
        # Verificar que las razones son específicas (no genéricas)
        valid_reasons = {
            "active_n_below_min",
            "active_rate_below_min", 
            "inactive_rate_above_max",
            "active_pass_rate_below_min",
            "no_results",
        }
        
        for reason in meta_data["gate_fail_reasons"]:
            assert reason in valid_reasons, \
                f"Unexpected fail reason: {reason}, expected one of {valid_reasons}"

    def test_strict_gate_exit_code_on_fail(self, tmp_path):
        """
        Verifica que --strict-gate produce exit code 1 cuando gate falla.
        """
        output_dir = tmp_path / "calibration_output"
        
        result = subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "full",
                "--profile", "full",  # Use strict thresholds
                "--max-combinations", "12",
                "--seed", "42",
                "--strict-gate",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        
        # Con 33% active_rate < 60%, gate falla, y con --strict-gate debe ser exit 1
        meta_data = json.loads((output_dir / "run_meta.json").read_text())
        
        if not meta_data["gate_passed"]:
            assert result.returncode == 1, \
                f"With --strict-gate and gate_passed=false, exit code should be 1, got {result.returncode}"

    def test_mode_full_uses_full_demo_profile(self, tmp_path):
        """Verifica que --mode full usa profile full_demo y PASS en entorno sintético."""
        output_dir = tmp_path / "calibration_output"
        
        result = subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "full",
                "--max-combinations", "40",
                "--seed", "42",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO_ROOT,
        )
        
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        
        meta_data = json.loads((output_dir / "run_meta.json").read_text())
        
        # Debe usar full_demo profile
        assert meta_data.get("gate_profile") == "full_demo", \
            f"Expected gate_profile='full_demo', got: {meta_data.get('gate_profile')}"
        
        # Con full_demo thresholds (30% min), ~33% active rate debe PASS
        assert meta_data["gate_passed"] is True, \
            f"Gate should pass with full_demo profile, got fail_reasons: {meta_data.get('gate_fail_reasons')}"

    def test_profile_full_strict_fails(self, tmp_path):
        """Verifica que --profile full usa thresholds strict y FAIL."""
        output_dir = tmp_path / "calibration_output"
        
        result = subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "full",
                "--profile", "full",
                "--config", "configs/risk_calibration_2B_candidate_kelly05.yaml",  # Control config for gate failure
                "--max-combinations", "40",
                "--seed", "42",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=REPO_ROOT,
        )
        
        assert result.returncode == 0, f"Runner failed: {result.stderr}"
        
        meta_data = json.loads((output_dir / "run_meta.json").read_text())
        
        # Debe usar full profile (strict)
        assert meta_data.get("gate_profile") == "full", \
            f"Expected gate_profile='full', got: {meta_data.get('gate_profile')}"
        
        # Con full thresholds (60% min), ~33% active rate debe FAIL
        assert meta_data["gate_passed"] is False, \
            "Gate should fail with strict full profile"
        assert "active_rate_below_min" in meta_data["gate_fail_reasons"], \
            f"Should include active_rate_below_min, got: {meta_data['gate_fail_reasons']}"

    def test_profile_flag_in_help(self, tmp_path):
        """Verifica que --profile flag está documentado en help."""
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
        
        assert "--profile" in result.stdout, "--profile flag should be in help"
        assert "full_demo" in result.stdout, "full_demo should be mentioned in --profile help"

    def test_classify_inactive_reason_logic(self):
        """Unit test para la lógica de clasificación de inactividad."""
        # 1. Active trade > 0 -> all zeros
        res = classify_inactive_reason(1, {"price_missing_count": 5})
        assert sum(res.values()) == 0, f"Active trade should have 0 flags, got {res}"
        
        # 2. Priority: Price missing
        res = classify_inactive_reason(0, {"price_missing_count": 1, "signal_count": 0})
        assert res["rejection_price_missing"] == 1
        assert sum(res.values()) == 1
        
        # 3. Priority: No signal
        res = classify_inactive_reason(0, {"price_missing_count": 0, "signal_count": 0})
        assert res["rejection_no_signal"] == 1
        assert sum(res.values()) == 1
        
        # 4. Priority: Blocked risk
        res = classify_inactive_reason(0, {"signal_count": 5, "signal_rejected_count": 5})
        assert res["rejection_blocked_risk"] == 1
        assert sum(res.values()) == 1
        
        # 5. Priority: Size zero
        res = classify_inactive_reason(0, {"signal_count": 5, "signal_rejected_count": 0, "size_zero_count": 5})
        assert res["rejection_size_zero"] == 1
        assert sum(res.values()) == 1
        
        # 6. Fallback: Other
        res = classify_inactive_reason(0, {"signal_count": 5, "signal_rejected_count": 0, "size_zero_count": 0})
        assert res["rejection_other"] == 1
        assert sum(res.values()) == 1

    def test_inactive_rows_have_exactly_one_rejection_flag(self, tmp_path):
        """Verifica que filas inactivas tengan exactamente 1 flag de rechazo activado."""
        output_dir = tmp_path / "calibration_output"
        
        subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "quick",
                "--max-combinations", "6",
                "--seed", "42",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        
        results_file = output_dir / "results.csv"
        # Leer como dict
        import csv
        with open(results_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        rejection_cols = [
            "rejection_no_signal",
            "rejection_blocked_risk",
            "rejection_size_zero",
            "rejection_price_missing",
            "rejection_other",
        ]
        
        for row in rows:
            is_active = row.get("is_active", "False") == "True"
            flags_sum = sum(int(row.get(c, 0)) for c in rejection_cols)
            
            if is_active:
                assert flags_sum == 0, f"Active row {row['combo_id']} has active rejection flags"
            else:
                assert flags_sum == 1, f"Inactive row {row['combo_id']} should have exactly 1 rejection flag, got {flags_sum}"

    def test_risk_reject_reasons_in_csv_and_meta(self, tmp_path):
        """Verifica que risk_reject_reasons aparece en CSV y run_meta.json (2E-4-2)."""
        output_dir = tmp_path / "calibration_output"
        
        subprocess.run(
            [
                sys.executable,
                "tools/run_calibration_2B.py",
                "--mode", "full",
                "--max-combinations", "12",
                "--seed", "42",
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=REPO_ROOT,
        )
        
        # Check CSV column exists
        results_file = output_dir / "results.csv"
        import csv
        with open(results_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert "risk_reject_reasons_top" in rows[0], "CSV should have risk_reject_reasons_top column"
        
        # Check run_meta.json has topk
        meta_data = json.loads((output_dir / "run_meta.json").read_text())
        assert "risk_reject_reasons_topk" in meta_data, "run_meta should have risk_reject_reasons_topk"
        
        # With synthetic data, we expect some rejections
        topk = meta_data["risk_reject_reasons_topk"]
        assert isinstance(topk, dict), f"Expected dict, got {type(topk)}"

