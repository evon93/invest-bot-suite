"""
config_schema.py

Esquema mínimo y validación best-effort para risk_rules.yaml.

No impone una estructura rígida: sólo garantiza que:
- El YAML se puede parsear.
- La raíz es un dict.
- Las claves de nivel superior son strings.
- Algunos campos numéricos, si existen, tienen valores coherentes (> 0).

Se diseña para no romper configuraciones existentes y servir como punto de partida
para validaciones más estrictas en futuras versiones.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


class RiskConfigError(Exception):
    """Error de carga o estructura básica del fichero de configuración de riesgo."""


@dataclass
class RiskConfig:
    path: Path
    data: Dict[str, Any]


# Secciones recomendadas, pero no obligatorias (se reportan como warnings si faltan)
RECOMMENDED_TOP_LEVEL_SECTIONS = (
    "risk_limits",
    "position_limits",
    "dd_limits",
    "atr_stop",
    "kelly",
    "position_sizing",
)


def load_raw_risk_config(path: Path) -> Dict[str, Any]:
    """
    Carga risk_rules.yaml como dict.

    Levanta RiskConfigError si:
    - El fichero no existe.
    - El YAML no se puede parsear.
    - La raíz no es un dict.
    """
    if not path.is_file():
        raise RiskConfigError(f"Config file not found: {path}")

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RiskConfigError(f"Cannot read config file {path}: {exc}") from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RiskConfigError(f"YAML parse error in {path}: {exc}") from exc

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise RiskConfigError(f"Root of {path} must be a mapping/dict, got {type(data)!r}")

    return data


def _is_positive_number(x: Any) -> bool:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return v > 0.0


def validate_risk_config_data(data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """
    Valida de forma ligera el dict de configuración de riesgo.

    Devuelve (errors, warnings).
    - errors: problemas estructurales serios.
    - warnings: recomendaciones o potenciales inconsistencias que no rompen ejecución.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(data, dict):
        errors.append("Root config must be a dict/mapping.")
        return errors, warnings

    # Claves de nivel superior deben ser strings
    for key in data.keys():
        if not isinstance(key, str):
            errors.append("All top-level keys must be strings.")
            break

    # Secciones recomendadas, pero no obligatorias
    for section in RECOMMENDED_TOP_LEVEL_SECTIONS:
        if section not in data:
            warnings.append(f"Recommended top-level section '{section}' is missing.")

    # Validaciones numéricas best-effort (solo si las secciones existen)
    dd_limits = data.get("dd_limits")
    if isinstance(dd_limits, dict):
        max_dd = dd_limits.get("max_drawdown_pct")
        if max_dd is not None and not _is_positive_number(max_dd):
            errors.append("dd_limits.max_drawdown_pct should be a positive number (> 0).")

    atr_stop = data.get("atr_stop")
    if isinstance(atr_stop, dict):
        atr_mult = atr_stop.get("atr_multiple")
        if atr_mult is not None and not _is_positive_number(atr_mult):
            errors.append("atr_stop.atr_multiple should be a positive number (> 0).")

    # Validación risk_manager: mode y logging
    rm_section = data.get("risk_manager")
    if isinstance(rm_section, dict):
        mode = rm_section.get("mode")
        if mode is not None and mode not in ("active", "monitor"):
            errors.append(
                f"risk_manager.mode must be 'active' or 'monitor', got {mode!r}."
            )

        logging_cfg = rm_section.get("logging")
        if isinstance(logging_cfg, dict):
            enabled = logging_cfg.get("enabled")
            if enabled is not None and not isinstance(enabled, bool):
                errors.append(
                    f"risk_manager.logging.enabled must be a boolean, got {type(enabled).__name__}."
                )

    return errors, warnings


def load_and_validate(path: Path) -> Tuple[RiskConfig, List[str], List[str]]:
    """
    Helper de alto nivel:

    - Carga el fichero.
    - Ejecuta validación best-effort.
    - Devuelve (RiskConfig, errors, warnings).
    """
    raw = load_raw_risk_config(path)
    errors, warnings = validate_risk_config_data(raw)
    return RiskConfig(path=path, data=raw), errors, warnings
