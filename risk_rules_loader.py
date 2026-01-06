"""
risk_rules_loader.py

Carga y validación fail-fast de risk rules desde YAML.

Parte del ticket AG-3D-1-1: Risk rules loading fail-fast (strict).
"""

from pathlib import Path
from typing import Dict, Any, Union

import yaml


# Critical set: keys que RiskManager v0.4 requiere para funcionar correctamente
CRITICAL_KEYS = {
    "position_limits": dict,
    "kelly": dict,
    "risk_manager": dict,
}


def load_risk_rules(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Carga y parsea un archivo YAML de risk rules.
    
    Args:
        path: Ruta al archivo YAML de risk rules.
        
    Returns:
        Dict con las reglas de riesgo parseadas.
        
    Raises:
        ValueError: Si el archivo no existe, YAML inválido, o resultado vacío/None.
    """
    path = Path(path)
    
    if not path.exists():
        raise ValueError(f"Risk rules file not found: {path}")
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            rules = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in risk rules file {path}: {e}") from e
    
    if rules is None:
        raise ValueError(f"Risk rules file is empty or contains only comments: {path}")
    
    if not isinstance(rules, dict):
        raise ValueError(
            f"Risk rules must be a dict, got {type(rules).__name__}: {path}"
        )
    
    return rules


def validate_risk_rules_critical(rules: Dict[str, Any], path: Union[str, Path, None] = None) -> None:
    """
    Valida que las keys críticas existan y tengan el tipo correcto.
    
    Critical set (derivado de RiskManager v0.4):
      - rules["position_limits"] → dict
      - rules["kelly"] → dict  
      - rules["risk_manager"] → dict
    
    Args:
        rules: Dict con las reglas de riesgo.
        path: Ruta opcional para incluir en mensaje de error.
        
    Raises:
        ValueError: Con mensaje descriptivo listando keys faltantes/inválidas y path.
    """
    missing_keys = []
    wrong_type_keys = []
    
    for key, expected_type in CRITICAL_KEYS.items():
        if key not in rules:
            missing_keys.append(key)
        elif not isinstance(rules[key], expected_type):
            actual_type = type(rules[key]).__name__
            wrong_type_keys.append(f"{key} (expected {expected_type.__name__}, got {actual_type})")
    
    errors = []
    if missing_keys:
        errors.append(f"missing critical keys: {missing_keys}")
    if wrong_type_keys:
        errors.append(f"wrong type for keys: {wrong_type_keys}")
    
    if errors:
        path_info = f" in {path}" if path else ""
        raise ValueError(f"Risk rules validation failed{path_info}: {'; '.join(errors)}")
