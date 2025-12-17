# RiskContextV06 — Implementación 2A

**Branch:** `feature/2A_riskcontext_v0_6_and_monitor`  
**Fecha:** 2025-12-16

---

## ¿Qué es RiskContextV06?

Dataclass tipada que normaliza el contexto de riesgo recibido desde el backtester o pipeline event-driven. Convierte un dict con claves variables en bloques estructurados sin imponer un esquema rígido.

**Archivo:** [`risk_context_v0_6.py`](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/risk_context_v0_6.py)

---

## Estructura

```python
@dataclass(slots=True)
class RiskContextV06:
    raw: Mapping[str, Any]           # Dict original completo
    portfolio: PortfolioBlock        # Posición/activo
    atr_ctx: ATRContext              # ATR y stops dinámicos
    cfg: RiskConfigBlock             # Config global de riesgo
```

### Bloques

| Bloque | Campos | Aliases soportados |
|--------|--------|-------------------|
| `PortfolioBlock` | symbol, side, quantity, price, portfolio_value, sector | asset_id, instrument_id, position, qty, equity, nav |
| `ATRContext` | atr, atr_window, atr_mult, atr_stop_price | atr_period, atr_lookback, atr_multiple, atr_k, stop_price |
| `RiskConfigBlock` | max_dd_pct, max_position_pct, max_leverage, kelly_fraction | max_drawdown_pct, dd_guardrail_pct, max_position_ratio, kelly_fraction_clipped |

---

## Mapeo dict → dataclass

```python
RiskContextV06.from_dict(data: Mapping[str, Any]) -> RiskContextV06
```

- Intenta múltiples aliases para cada campo (ej. `atr_mult` o `atr_multiple` o `atr_k`)
- Valores numéricos se convierten con `_to_float_or_none` / `_to_int_or_none`
- Campos no mapeados quedan accesibles vía `raw`
- Si un campo no existe o no es convertible → `None` (no lanza excepción)

---

## Precedencia en filter_signal

En [`risk_manager_v0_5.py`](file:///c:/Users/ivn_b/Desktop/invest-bot-suite/risk_manager_v0_5.py) líneas 201-236:

```
kwargs > risk_ctx.raw > risk_ctx.raw.env > risk_ctx.raw.config
```

Cada input se resuelve así:
1. **kwargs directos** (ej. `equity_curve=...`)  
2. **risk_ctx.raw** (nivel raíz del dict original)  
3. **risk_ctx.raw["env"]** (sub-dict env)  
4. **risk_ctx.raw["config"]** (sub-dict config, para dd_cfg/dd_guardrail)

---

## Campos esperados por filter_signal

| Campo | Tipo | Fuente | Si falta |
|-------|------|--------|----------|
| `equity_curve` | list[float] | kwargs / raw / env | `dd_skipped=True` |
| `dd_cfg` | dict | kwargs / raw / config.dd_cfg / config.dd_guardrail | `dd_skipped=True` |
| `atr_ctx` | dict[ticker, ctx] | kwargs / raw / env | `atr_skipped=True` |
| `last_prices` | dict[ticker, float] | kwargs / raw / env | (fallback a atr_ctx.last_price) |

---

## Flags de degradación

Cuando faltan contextos, el RiskManager añade flags y continúa sin bloquear:

- `annotated["dd_skipped_reason"]` → `"missing_equity_curve_or_dd_cfg"` o `"invalid_or_empty_equity_curve"`
- `annotated["atr_skipped_reason"]` → `"missing_or_empty_atr_ctx"`
- `risk_decision["dd_skipped"]` / `risk_decision["atr_skipped"]` → `True`

---

## Método as_dict()

Devuelve dict combinando raw + campos canónicos (para logging/monitor). `raw` prevalece en conflictos de clave.
