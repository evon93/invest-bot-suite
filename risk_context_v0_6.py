from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Dict


def _to_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@dataclass(slots=True)
class PortfolioBlock:
    """
    Información principal de la posición/activo dentro del portafolio.
    Campos opcionales, se rellenan de forma best-effort desde el dict original.
    """
    symbol: Optional[str] = None
    side: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    portfolio_value: Optional[float] = None
    sector: Optional[str] = None


@dataclass(slots=True)
class ATRContext:
    """
    Contexto relacionado con ATR y stops dinámicos.
    """
    atr: Optional[float] = None
    atr_window: Optional[int] = None
    atr_mult: Optional[float] = None
    atr_stop_price: Optional[float] = None


@dataclass(slots=True)
class RiskConfigBlock:
    """
    Config global de riesgo relevante para la decisión:
    drawdown máximo, tamaño máximo de posición, apalancamiento, Kelly, etc.
    """
    max_dd_pct: Optional[float] = None
    max_position_pct: Optional[float] = None
    max_leverage: Optional[float] = None
    kelly_fraction: Optional[float] = None


@dataclass(slots=True)
class RiskContextV06:
    """
    Vista tipada del contexto de riesgo.

    - raw: dict original recibido desde el backtester / pipeline event-driven.
    - portfolio, atr_ctx, cfg: bloques estructurados para guardrails y sizing.
    """
    raw: Mapping[str, Any]
    portfolio: PortfolioBlock = field(default_factory=PortfolioBlock)
    atr_ctx: ATRContext = field(default_factory=ATRContext)
    cfg: RiskConfigBlock = field(default_factory=RiskConfigBlock)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RiskContextV06":
        """
        Adaptador desde el dict actual de risk_ctx a la vista tipada v0.6.

        No asume un esquema rígido: intenta mapear campos habituales y
        deja el resto accesible vía `raw`.
        """
        d: Dict[str, Any] = dict(data)

        portfolio = PortfolioBlock(
            symbol=d.get("symbol") or d.get("asset_id") or d.get("instrument_id"),
            side=d.get("side"),
            quantity=_to_float_or_none(
                d.get("position") or d.get("quantity") or d.get("qty")
            ),
            price=_to_float_or_none(d.get("price")),
            portfolio_value=_to_float_or_none(
                d.get("portfolio_value") or d.get("equity") or d.get("nav")
            ),
            sector=d.get("sector"),
        )

        atr_ctx = ATRContext(
            atr=_to_float_or_none(d.get("atr")),
            atr_window=_to_int_or_none(
                d.get("atr_window") or d.get("atr_period") or d.get("atr_lookback")
            ),
            atr_mult=_to_float_or_none(
                d.get("atr_mult") or d.get("atr_multiple") or d.get("atr_k")
            ),
            atr_stop_price=_to_float_or_none(
                d.get("atr_stop_price") or d.get("stop_price")
            ),
        )

        cfg = RiskConfigBlock(
            max_dd_pct=_to_float_or_none(
                d.get("max_dd_pct")
                or d.get("max_drawdown_pct")
                or d.get("dd_guardrail_pct")
            ),
            max_position_pct=_to_float_or_none(
                d.get("max_position_pct") or d.get("max_position_ratio")
            ),
            max_leverage=_to_float_or_none(d.get("max_leverage")),
            kelly_fraction=_to_float_or_none(
                d.get("kelly_fraction") or d.get("kelly_fraction_clipped")
            ),
        )

        return cls(raw=d, portfolio=portfolio, atr_ctx=atr_ctx, cfg=cfg)

    def as_dict(self) -> Dict[str, Any]:
        """
        Devuelve una vista dict combinando bloques estructurados + raw.

        - `raw` siempre prevalece en caso de conflicto de clave.
        - Pensado para logging/monitor y para facilitar compatibilidad.
        """
        result: Dict[str, Any] = dict(self.raw)

        # Overlay opcional de algunos campos "canónicos"
        if self.portfolio.symbol is not None:
            result.setdefault("symbol", self.portfolio.symbol)
        if self.portfolio.side is not None:
            result.setdefault("side", self.portfolio.side)
        if self.portfolio.quantity is not None:
            result.setdefault("position", self.portfolio.quantity)
        if self.portfolio.price is not None:
            result.setdefault("price", self.portfolio.price)
        if self.portfolio.portfolio_value is not None:
            result.setdefault("portfolio_value", self.portfolio.portfolio_value)
        if self.portfolio.sector is not None:
            result.setdefault("sector", self.portfolio.sector)

        if self.atr_ctx.atr is not None:
            result.setdefault("atr", self.atr_ctx.atr)
        if self.atr_ctx.atr_window is not None:
            result.setdefault("atr_window", self.atr_ctx.atr_window)
        if self.atr_ctx.atr_mult is not None:
            result.setdefault("atr_mult", self.atr_ctx.atr_mult)
        if self.atr_ctx.atr_stop_price is not None:
            result.setdefault("atr_stop_price", self.atr_ctx.atr_stop_price)

        if self.cfg.max_dd_pct is not None:
            result.setdefault("max_dd_pct", self.cfg.max_dd_pct)
        if self.cfg.max_position_pct is not None:
            result.setdefault("max_position_pct", self.cfg.max_position_pct)
        if self.cfg.max_leverage is not None:
            result.setdefault("max_leverage", self.cfg.max_leverage)
        if self.cfg.kelly_fraction is not None:
            result.setdefault("kelly_fraction", self.cfg.kelly_fraction)

        return result
