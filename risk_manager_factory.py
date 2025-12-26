"""
risk_manager_factory.py — Selector de versión de RiskManager.

Permite instanciar RiskManager v0.4 o v0.5 según:
- parámetro `version`, o
- campo `risk_manager.version` en risk_rules.yaml.

No rompe la API actual: ambos managers aceptan el mismo parámetro `rules`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union, Dict, Any, Optional

import yaml

from risk_manager_v0_4_shim import RiskManager as RiskManagerV04
from risk_manager_v0_5 import RiskManagerV05

RulesType = Union[Dict[str, Any], str, Path]


def _read_version_from_rules(rules: RulesType) -> str:
    """
    Lee la versión configurada desde `rules`:

    - Si `rules` es un dict, busca `rules["risk_manager"]["version"]`.
    - Si es str/Path, carga el YAML y lee ese campo.
    - Fallback seguro: "0.4".
    """
    try:
        if isinstance(rules, dict):
            cfg = rules
        else:
            rules_path = Path(rules)
            with rules_path.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}

        risk_cfg = cfg.get("risk_manager", {}) or {}
        version = risk_cfg.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
    except Exception:
        # Cualquier error → comportamiento conservador
        pass

    return "0.4"


def get_risk_manager(
    version: Optional[str] = None,
    rules: RulesType = "risk_rules.yaml",
    **kwargs: Any,
):
    """
    Factoría de RiskManager.

    - version is None  → se lee de `rules` (campo risk_manager.version), fallback "0.4".
    - version == "0.4" → instancia RiskManager v0.4 vía shim.
    - version == "0.5" → instancia RiskManagerV05.
    - cualquier otro valor → fallback seguro a "0.4".

    `rules` se pasa tal cual (dict, str o Path) al constructor concreto.
    """
    if version is None:
        version = _read_version_from_rules(rules)

    if version == "0.5":
        return RiskManagerV05(rules, **kwargs)

    # Default seguro: v0.4
    return RiskManagerV04(rules, **kwargs)
