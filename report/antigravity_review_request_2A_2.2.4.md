# Antigravity Review Request — 2A / Subpaso 2.2.4 (RiskContext v0.6 wiring)

## Objetivo
Hacer que `RiskManagerV05.filter_signal()` acepte `risk_ctx` como:
- dict (contrato lógico 1D)
- o `RiskContextV06` (dataclass)

Sin romper compatibilidad con kwargs actuales:
- `equity_curve`, `dd_cfg`, `atr_ctx`, `last_prices` siguen funcionando igual si no se pasa `risk_ctx`.

## Estado actual
- Excerpt “before”: `report/filter_signal_before_2A_2.2.4.txt`
- Helper ya añadido: `_ensure_risk_context_v06(risk_ctx)` en `risk_manager_v0_5.py`

## Cambio propuesto (patch conceptual)
Insertar justo después de:
`risk_decision = self._init_risk_decision()`

    ctx = _ensure_risk_context_v06(kwargs.get("risk_ctx"))
    env = {}
    cfg_block = {}

    if ctx is not None:
        env = ctx.raw.get("env") or {}
        cfg_block = ctx.raw.get("config") or {}

    equity_curve = (
        kwargs.get("equity_curve")
        or (ctx.raw.get("equity_curve") if ctx is not None else None)
        or env.get("equity_curve")
    )

    dd_cfg = (
        kwargs.get("dd_cfg")
        or (ctx.raw.get("dd_cfg") if ctx is not None else None)
        or cfg_block.get("dd_cfg")
        or cfg_block.get("dd_guardrail")
    )

    atr_ctx = (
        kwargs.get("atr_ctx")
        or (ctx.raw.get("atr_ctx") if ctx is not None else None)
        or env.get("atr_ctx")
        or {}
    )

    last_prices = (
        kwargs.get("last_prices")
        or (ctx.raw.get("last_prices") if ctx is not None else None)
        or env.get("last_prices")
        or {}
    )

Y eliminar las asignaciones redundantes actuales:
- En bloque DD: `equity_curve = kwargs.get("equity_curve")` y `dd_cfg = kwargs.get("dd_cfg")`
- En bloque ATR: `atr_ctx = kwargs.get("atr_ctx") or {}` y `last_prices = kwargs.get("last_prices") or {}`

## Criterios de aceptación
1) Backward-compatible: tests existentes no deben romperse.
2) Con `risk_ctx` presente, debe extraer correctamente:
   - `equity_curve`, `dd_cfg`, `atr_ctx`, `last_prices` desde `risk_ctx` (o `risk_ctx.env` / `risk_ctx.config`).
3) No cambiar la lógica de decisión (solo wiring).
4) Pytest parcial: `tests/test_risk_decision_v0_5.py` + `tests/test_risk_v0_5_extended.py` pasan.
5) Pytest global: `python -m pytest -q` pasa.

## Preguntas para reviewer (Claude Opus 4.5)
- ¿Riesgo de precedencia incorrecta de kwargs vs risk_ctx?
- ¿Fallback `config.dd_cfg` / `config.dd_guardrail` correcto?
- ¿Mejoras mínimas de robustez sin ampliar superficie?
