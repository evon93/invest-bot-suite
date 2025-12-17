from pathlib import Path

from config_schema import RiskConfigError, load_and_validate


def test_risk_rules_yaml_is_present_and_valid():
    config_path = Path("risk_rules.yaml")
    assert config_path.is_file(), "risk_rules.yaml debe existir en la raíz del repo"

    cfg, errors, warnings = load_and_validate(config_path)

    # La validación no debe reportar errores estructurales
    assert errors == [], f"Config de riesgo inválida: {errors}"

    # Las warnings son aceptables (pueden indicar campos recomendados faltantes)
    assert isinstance(warnings, list)
