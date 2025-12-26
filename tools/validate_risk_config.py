#!/usr/bin/env python
"""
tools/validate_risk_config.py

Valida risk_rules.yaml usando config_schema.py y genera un informe en /report.

Uso típico:
    python tools/validate_risk_config.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import datetime as dt

# Aseguramos que la raíz del repo está en sys.path para importar config_schema
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config_schema import RiskConfigError, load_and_validate


def build_report(config_path: Path, errors, warnings) -> str:
    now = dt.datetime.now().astimezone()
    lines = []
    lines.append("Risk config validation report")
    lines.append("")
    lines.append(f"- Config path: {config_path}")
    lines.append(f"- Generated: {now.isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("Summary:")
    lines.append(f"- Errors: {len(errors)}")
    lines.append(f"- Warnings: {len(warnings)}")
    lines.append("")

    if warnings:
        lines.append("Warnings:")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    if errors:
        lines.append("Errors:")
        for e in errors:
            lines.append(f"- {e}")
        lines.append("")

    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate risk_rules.yaml configuration.")
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="risk_rules.yaml",
        help="Ruta al fichero de configuración de riesgo (por defecto: risk_rules.yaml).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="report/validate_risk_config_step5.txt",
        help="Ruta al fichero de informe (por defecto: report/validate_risk_config_step5.txt).",
    )

    args = parser.parse_args(argv)
    config_path = Path(args.config)
    output_path = Path(args.output)

    errors = []
    warnings = []

    try:
        cfg, errors, warnings = load_and_validate(config_path)
    except RiskConfigError as exc:
        errors = [str(exc)]
        warnings = []

    report = build_report(config_path, errors, warnings)

    # Aseguramos que /report existe
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print(report)

    # exit code: 0 si no hay errores, 1 si los hay
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
