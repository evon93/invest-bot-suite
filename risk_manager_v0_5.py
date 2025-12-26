from __future__ import annotations
import logging
import math
from typing import Dict, Tuple, Union, Any, Optional
from pathlib import Path
import yaml

from risk_logging import emit_risk_decision_log

from risk_context_v0_6 import RiskContextV06
def _ensure_risk_context_v06(risk_ctx: Any) -> Optional[RiskContextV06]:
    """
    Adapter para aceptar tanto dict (risk_ctx 1D) como RiskContextV06.

    NO cambia todavía la lógica interna del RiskManager: solo normaliza el tipo
    y deja preparado el contexto para ser usado por el core de decisión.
    """
    if risk_ctx is None:
        return None
    if isinstance(risk_ctx, RiskContextV06):
        return risk_ctx
    if isinstance(risk_ctx, dict):
        return RiskContextV06.from_dict(risk_ctx)
    raise TypeError(f"Unsupported risk_ctx type: {type(risk_ctx)!r}")

class RiskManagerV05:
    """Gestor de riesgo v0.5 – clon inicial de v0.4 para implementar nuevos guardrails."""

    # --------------------------------------------------------------------- #
    #  Inicialización                                                       #
    # --------------------------------------------------------------------- #
    def __init__(self, rules: Union[Dict, str, Path]):
        if isinstance(rules, (str, Path)):
            with open(rules, "r", encoding="utf-8") as f:
                self.rules = yaml.safe_load(f)
        else:
            self.rules = rules

        # Defaults robustos
        self.pos_limits = self.rules.get(
            "position_limits",
            {
                "max_single_asset_pct": 0.10,
                "max_crypto_pct": 0.30,
                "max_altcoin_pct": 0.05,
            },
        )

        self.kelly_rules = self.rules.get(
            "kelly",
            {
                "cap_factor": 0.5,
                "crypto_overrides": {
                    "high_vol": 0.3,
                    "med_vol": 0.4,
                    "low_vol": 0.5,
                },
                "percentile_thresholds": {"low": 0.5, "high": 0.8},
            },
        )

        self.major_cryptos = set(self.rules.get("major_cryptos", []))
        self.liquidity_filter = self.rules.get(
            "liquidity_filter", {"min_volume_usd": 10_000_000}
        )

        # Logger sencillo
        self.logger = logging.getLogger("RiskManager")
        if not self.logger.handlers:
            self.logger.addHandler(logging.StreamHandler())
        self.logger.setLevel(logging.INFO)

        # Modo de ejecución del risk_manager: active | monitor
        rm_cfg = self.rules.get("risk_manager", {}) or {}
        self.mode = str(rm_cfg.get("mode", "active")).lower()
        if self.mode not in ("active", "monitor"):
            self.logger.warning(
                "Unknown risk_manager.mode=%r; defaulting to 'active'", self.mode
            )
            self.mode = "active"
        self.logger.info("RiskManager initialized with %d rules", len(self.rules))

    # --------------------------------------------------------------------- #
    #  Acceso a configuración DD                                            #
    # --------------------------------------------------------------------- #
    def get_dd_cfg(self) -> Dict[str, Any]:
        """Devuelve la configuración de DD guardrail desde las reglas cargadas.
        
        Mapea los nombres de risk_rules.yaml a los esperados por eval_dd_guardrail:
        - soft_limit_pct -> max_dd_soft
        - hard_limit_pct -> max_dd_hard
        - size_multiplier_soft -> size_multiplier_soft
        """
        dd_rules = self.rules.get("max_drawdown", {})
        return {
            "max_dd_soft": float(dd_rules.get("soft_limit_pct", 0.05)),
            "max_dd_hard": float(dd_rules.get("hard_limit_pct", 0.10)),
            "size_multiplier_soft": float(dd_rules.get("size_multiplier_soft", 0.5)),
        }

    # --------------------------------------------------------------------- #
    #  Kelly / tamaño de posición                                           #
    # --------------------------------------------------------------------- #
    def cap_position_size(self, asset: str, nav_eur: float, vol_pct: float) -> float:
        """Calcula el tamaño máximo en EUR aplicando Kelly dinámico y overrides."""
        base_fraction = self.kelly_rules.get("cap_factor", 0.5)

        crypto_over = self.kelly_rules.get("crypto_overrides", {})
        thresholds = self.kelly_rules.get("percentile_thresholds", {})
        th_high = thresholds.get("high", 0.8)
        th_low = thresholds.get("low", 0.5)

        if asset in self.major_cryptos:
            if vol_pct >= th_high:
                base_fraction = crypto_over.get("high_vol", base_fraction)
            elif vol_pct >= th_low:
                base_fraction = crypto_over.get("med_vol", base_fraction)
            else:
                base_fraction = crypto_over.get("low_vol", base_fraction)

        return nav_eur * base_fraction

    def max_position_size(self, nav_eur: float) -> float:
        """Tamaño máximo absoluto (EUR) permitido por reglas generales."""
        pct = self.pos_limits.get("max_single_asset_pct", 0.10)
        return nav_eur * pct

    # --------------------------------------------------------------------- #
    #  Límites de posición                                                  #
    # --------------------------------------------------------------------- #
    def within_position_limits(self, alloc: Dict[str, float]) -> bool:
        """Comprueba que un allocation dict respeta límites single/sector/altcoin."""
        max_single = self.pos_limits.get("max_single_asset_pct", 0.10)
        if any(w > max_single for w in alloc.values()):
            self.logger.warning("Asset limit exceeded")
            return False

        crypto_assets = [a for a in alloc if a.startswith("CRYPTO")]
        if crypto_assets:
            crypto_total = sum(alloc[a] for a in crypto_assets)
            if crypto_total > self.pos_limits.get("max_crypto_pct", 0.30):
                self.logger.warning("Crypto sector limit exceeded")
                return False

            altcoins = [a for a in crypto_assets if a not in self.major_cryptos]
            if altcoins:
                altcoin_total = sum(alloc[a] for a in altcoins)
                if altcoin_total > self.pos_limits.get("max_altcoin_pct", 0.05):
                    self.logger.warning("Altcoin limit exceeded")
                    return False
        return True

    # --------------------------------------------------------------------- #
    #  Helpers de decisión unificada                                        #
    # --------------------------------------------------------------------- #
    @staticmethod
    def _init_risk_decision() -> Dict[str, Any]:
        """Inicializa el bloque risk_decision con valores por defecto."""
        return {
            "allow_new_trades": True,
            "force_close_positions": False,
            "size_multiplier": 1.0,
            "stop_signals": [],
            "reasons": [],
        }

    @staticmethod
    def _add_reason(risk_decision: Dict[str, Any], reasons: list[str], tag: str) -> None:
        """Añade un motivo a ambas listas evitando duplicados."""
        if tag not in reasons:
            reasons.append(tag)
        if tag not in risk_decision["reasons"]:
            risk_decision["reasons"].append(tag)

    # --------------------------------------------------------------------- #
    #  Filtro principal de señales                                          #
    # --------------------------------------------------------------------- #
    def filter_signal(
        self,
        signal: dict,
        current_weights: dict,
        nav_eur: float | None = None,
        **kwargs,
    ) -> Tuple[bool, dict]:
        """Filtra señales; devuelve (allow, annotated_signal) – compatible con tests.

        === RiskDecision v0.5: agregación de guardrails (DD, ATR, reglas v0.4) ===
        - Mantiene contrato público de v0.4: (allow, annotated_signal).
        - El comportamiento sin guardrails activos es equivalente a v0.4.
        - risk_decision unifica DD, ATR, límites y Kelly en una estructura única.
        === Fin bloque RiskDecision v0.5 ===
        """
        allow = True
        reasons: list[str] = []
        annotated = signal.copy()
        signal_original = signal.copy()
        # Snapshot de deltas originales (deep copy) para restauración en modo monitor
        orig_deltas = dict(signal.get("deltas", {}))

        # Bloque de decisión unificada
        risk_decision = self._init_risk_decision()
        risk_decision["mode"] = getattr(self, "mode", "active")
        
        # ------------------------------------------------------------------
        # RiskContext v0.6 adapter (dict o dataclass) — compat con kwargs planos
        # ------------------------------------------------------------------
        risk_ctx_obj = _ensure_risk_context_v06(kwargs.get("risk_ctx"))
        env = {}
        cfg_block = {}

        if risk_ctx_obj is not None:
            env = risk_ctx_obj.raw.get("env") or {}
            cfg_block = risk_ctx_obj.raw.get("config") or {}

        equity_curve = (
            kwargs.get("equity_curve")
            or (risk_ctx_obj.raw.get("equity_curve") if risk_ctx_obj is not None else None)
            or env.get("equity_curve")
        )

        dd_cfg = (
            kwargs.get("dd_cfg")
            or (risk_ctx_obj.raw.get("dd_cfg") if risk_ctx_obj is not None else None)
            or cfg_block.get("dd_cfg")
            or cfg_block.get("dd_guardrail")
        )

        atr_ctx = (
            kwargs.get("atr_ctx")
            or (risk_ctx_obj.raw.get("atr_ctx") if risk_ctx_obj is not None else None)
            or env.get("atr_ctx")
            or {}
        )

        last_prices = (
            kwargs.get("last_prices")
            or (risk_ctx_obj.raw.get("last_prices") if risk_ctx_obj is not None else None)
            or env.get("last_prices")
            or {}
        )


        # ------------------------------------------------------------------
        # 1) Límites de posición (lógica v0.4)
        # ------------------------------------------------------------------
        if not self.within_position_limits(current_weights):
            allow = False
            risk_decision["allow_new_trades"] = False
            self._add_reason(risk_decision, reasons, "position_limits")

        # ------------------------------------------------------------------
        # 2) Filtros de liquidez (stub v0.4)
        # ------------------------------------------------------------------
        for asset in signal.get("assets", []):
            if not self._check_liquidity(asset):
                allow = False
                risk_decision["allow_new_trades"] = False
                self._add_reason(risk_decision, reasons, f"liquidity:{asset}")

        # ------------------------------------------------------------------
        # 3) Guardrail de Drawdown (DD) global
        # ------------------------------------------------------------------
        # Prioridad máxima: DD hard_stop → force_close_positions=True,
        # size_multiplier=0.0, allow_new_trades=False
        # ------------------------------------------------------------------
        if equity_curve is not None and dd_cfg is not None:
            dd_stats = self.compute_drawdown(equity_curve)
            
            # Caso: curva inválida (vacía o solo NaN/inf)
            if dd_stats.get("skipped", False):
                risk_decision["dd_skipped"] = True
                annotated["dd_skipped_reason"] = "invalid_or_empty_equity_curve"
                self.logger.warning(
                    "DD guardrail desactivado: equity_curve sin datos válidos"
                )
            else:
                dd_val = dd_stats.get("max_dd", 0.0)
                dd_eval = self.eval_dd_guardrail(dd_val, dd_cfg)

                state = dd_eval.get("state", "normal")
                if state == "risk_off_light":
                    # Reducimos tamaño global de forma conservadora
                    dd_mult = float(dd_eval.get("size_multiplier", 1.0))
                    risk_decision["size_multiplier"] = min(
                        risk_decision["size_multiplier"], dd_mult
                    )
                    self._add_reason(risk_decision, reasons, "dd_soft")
                elif state == "hard_stop":
                    risk_decision["allow_new_trades"] = False
                    risk_decision["force_close_positions"] = True
                    risk_decision["size_multiplier"] = 0.0
                    allow = False
                    self._add_reason(risk_decision, reasons, "dd_hard")
        else:
            # Contexto DD faltante → modo degrade-to-safe
            risk_decision["dd_skipped"] = True
            annotated["dd_skipped_reason"] = "missing_equity_curve_or_dd_cfg"

        # ------------------------------------------------------------------
        # 4) Stop-loss ATR por posición
        # ------------------------------------------------------------------
        # Prioridad secundaria: ATR stop → añade tickers a stop_signals
        # sin anular DD hard_stop
        # ------------------------------------------------------------------
        if not atr_ctx:
            # Contexto ATR faltante → modo degrade-to-safe
            risk_decision["atr_skipped"] = True
            annotated["atr_skipped_reason"] = "missing_or_empty_atr_ctx"
        else:
            for ticker, ticker_ctx in atr_ctx.items():
                entry_price = ticker_ctx.get("entry_price")
                atr = ticker_ctx.get("atr")
                side = ticker_ctx.get("side")
                if entry_price is None or side is None:
                    continue

                cfg = {
                    "atr_multiplier": ticker_ctx.get("atr_multiplier", 2.5),
                    "min_stop_pct": ticker_ctx.get("min_stop_pct", 0.02),
                }
                stop_price = self.compute_atr_stop(entry_price, atr, side, cfg)
                if stop_price is None:
                    continue

                last_price = ticker_ctx.get("last_price", last_prices.get(ticker))
                if last_price is None:
                    continue

                if self.is_stop_triggered(side, stop_price, last_price):
                    if ticker not in risk_decision["stop_signals"]:
                        risk_decision["stop_signals"].append(ticker)
                    self._add_reason(risk_decision, reasons, "stop_loss_atr")

        # ------------------------------------------------------------------
        # 5) Kelly sizing (lógica v0.4, integrada en risk_decision)
        # ------------------------------------------------------------------
        if nav_eur:
            deltas = signal.get("deltas", {})
            annotated.setdefault("deltas", dict(deltas))
            for asset, target_weight in deltas.items():
                vol_pct = self._get_volatility(asset)
                max_eur = self.cap_position_size(asset, nav_eur, vol_pct)
                max_weight = max_eur / nav_eur
                if target_weight > max_weight:
                    allow = False
                    risk_decision["allow_new_trades"] = False
                    tag = f"kelly_cap:{asset}"
                    self._add_reason(risk_decision, reasons, tag)
                    annotated["deltas"][asset] = max_weight

        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # 6) Modo monitor: calcular pero NO aplicar (solo anotar) — 2A
        # ------------------------------------------------------------------
        if getattr(self, "mode", "active") == "monitor":
            monitor_payload = {
                "would_allow": allow,
                "would_reasons": list(reasons),
                "would_decision": risk_decision,
            }
            if "deltas" in annotated:
                monitor_payload["would_deltas"] = annotated.get("deltas")

            # Reset: comportamiento aplicado debe ser NO-OP
            allow = True
            reasons = []
            annotated = signal_original.copy()
            # Restaurar deltas originales (usando snapshot previo a mutación Kelly)
            annotated["deltas"] = dict(orig_deltas)
            risk_decision = self._init_risk_decision()
            risk_decision["mode"] = "monitor"
            annotated["risk_monitor"] = monitor_payload

        # 6) Sincronización final con annotated_signal
        # ------------------------------------------------------------------
        if not risk_decision["allow_new_trades"]:
            allow = False

        annotated["risk_allow"] = allow
        annotated["risk_reasons"] = reasons
        annotated["risk_decision"] = risk_decision


        # ------------------------------------------------------------------
        #  Observabilidad mínima (logging estructurado de decisiones de riesgo)
        # ------------------------------------------------------------------
        rm_cfg = (self.rules.get('risk_manager') or {}) if isinstance(self.rules, dict) else {}
        rm_log = rm_cfg.get('logging') or {}
        log_enabled = bool(rm_log.get('enabled', False)) if isinstance(rm_log, dict) else False
        mode = getattr(self, 'mode', rm_cfg.get('mode', 'active'))
        emit_risk_decision_log(
            logger=self.logger,
            enabled=log_enabled,
            mode=str(mode),
            risk_ctx=risk_ctx_obj,
            risk_decision=risk_decision,
            annotated=annotated,
        )

        return allow, annotated

    # --------------------------------------------------------------------- #
    #  Helpers (stubs)                                                      #
    # --------------------------------------------------------------------- #
    def _get_volatility(self, asset: str) -> float:
        """Stub: devuelve volatilidad histórica (para tests)."""
        return 0.65  # reemplazar con cálculo real

    def _check_liquidity(self, asset: str) -> bool:
        """Stub: chequea liquidez mínima (para tests)."""
        return True

    # --------------------------------------------------------------------- #
    #  Guardrail: max drawdown global                                       #
    # --------------------------------------------------------------------- #
    @staticmethod
    def compute_drawdown(equity_curve: list[float]) -> Dict[str, Any]:
        """
        Calcula el max drawdown de una curva de equity.

        Retorna un dict con:
        - max_dd: drawdown máximo en [0, 1].
        - peak_idx: índice del máximo previo al DD máximo.
        - trough_idx: índice del mínimo asociado al DD máximo.
        - skipped: True si la curva no tenía datos válidos.
        """
        # Filtrar valores no válidos (None, NaN, inf)
        valid_curve: list[tuple[int, float]] = []
        for i, val in enumerate(equity_curve):
            try:
                fval = float(val)
                if math.isfinite(fval):
                    valid_curve.append((i, fval))
            except (TypeError, ValueError):
                pass

        if not valid_curve:
            return {"max_dd": 0.0, "peak_idx": None, "trough_idx": None, "skipped": True}

        peak = valid_curve[0][1]
        peak_orig_idx = valid_curve[0][0]
        max_dd = 0.0
        dd_peak_idx = peak_orig_idx
        dd_trough_idx = peak_orig_idx

        for orig_idx, nav in valid_curve:
            if nav > peak:
                peak = nav
                peak_orig_idx = orig_idx

            if peak <= 0:
                # Sin referencia válida de peak → no definimos DD > 0
                continue

            dd = (peak - nav) / peak
            if dd > max_dd:
                max_dd = dd
                dd_peak_idx = peak_orig_idx
                dd_trough_idx = orig_idx

        return {
            "max_dd": float(max_dd),
            "peak_idx": dd_peak_idx,
            "trough_idx": dd_trough_idx,
            "skipped": False,
        }

    @staticmethod
    def eval_dd_guardrail(dd_value: float, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa el estado del guardrail de max_drawdown.

        cfg campos esperados:
        - max_dd_soft: umbral soft (ej. 0.05)
        - max_dd_hard: umbral hard (ej. 0.10)
        - size_multiplier_soft: multiplicador de tamaño en zona soft (ej. 0.5)

        Devuelve un dict con:
        - state: "normal" | "risk_off_light" | "hard_stop"
        - allow_new_trades: bool
        - size_multiplier: float
        - hard_stop: bool
        """
        max_dd_soft = float(cfg.get("max_dd_soft", 0.05))
        max_dd_hard = float(cfg.get("max_dd_hard", 0.10))
        size_mult_soft = float(cfg.get("size_multiplier_soft", 0.5))

        # Comportamiento inocuo si dd_value no es válido
        try:
            dd = float(dd_value)
        except (TypeError, ValueError):
            return {
                "state": "normal",
                "allow_new_trades": True,
                "size_multiplier": 1.0,
                "hard_stop": False,
            }

        if dd < 0:
            dd = 0.0

        if dd < max_dd_soft:
            return {
                "state": "normal",
                "allow_new_trades": True,
                "size_multiplier": 1.0,
                "hard_stop": False,
            }

        if dd < max_dd_hard:
            return {
                "state": "risk_off_light",
                "allow_new_trades": True,
                "size_multiplier": size_mult_soft,
                "hard_stop": False,
            }

        return {
            "state": "hard_stop",
            "allow_new_trades": False,
            "size_multiplier": 0.0,
            "hard_stop": True,
        }

    # --------------------------------------------------------------------- #
    #  Guardrail: stop-loss basado en ATR                                   #
    # --------------------------------------------------------------------- #
    @staticmethod
    def compute_atr_stop(
        entry_price: float,
        atr: float | None,
        side: str,
        cfg: Dict[str, Any],
    ) -> float | None:
        """
        Calcula el nivel de stop-loss dinámico basado en ATR.

        Parámetros:
        - entry_price: precio de entrada de la operación.
        - atr: valor de ATR (misma unidad que el precio) o None si no hay datos.
        - side: "long" o "short".
        - cfg:
            - atr_multiplier (ej. 2.5)
            - min_stop_pct (ej. 0.02 → 2%)

        Devuelve:
        - stop_price (float) o None si no se puede calcular.
        """
        try:
            price = float(entry_price)
        except (TypeError, ValueError):
            return None

        if price <= 0:
            return None

        atr_multiplier = float(cfg.get("atr_multiplier", 2.5))
        min_stop_pct = float(cfg.get("min_stop_pct", 0.02))

        # Distancia mínima como % del precio
        dist_min_pct = price * min_stop_pct

        dist_atr = None
        if atr is not None:
            try:
                atr_val = float(atr)
                if atr_val > 0:
                    dist_atr = atr_multiplier * atr_val
            except (TypeError, ValueError):
                dist_atr = None

        if dist_atr is not None:
            distance = max(dist_atr, dist_min_pct)
        else:
            # Sin ATR válido → usamos sólo el mínimo porcentual
            distance = dist_min_pct

        side_l = side.lower()
        if side_l == "long":
            return price - distance
        elif side_l == "short":
            return price + distance

        # Side desconocido → preferimos no devolver stop
        return None

    @staticmethod
    def is_stop_triggered(side: str, stop_price: float, last_price: float) -> bool:
        """
        Determina si el stop-loss ha sido activado en función del último precio.

        - Para posiciones long → triggered si last_price <= stop_price.
        - Para posiciones short → triggered si last_price >= stop_price.
        - Para side desconocido o precios inválidos → False.
        """
        try:
            stop = float(stop_price)
            last = float(last_price)
        except (TypeError, ValueError):
            return False

        side_l = side.lower()
        if side_l == "long":
            return last <= stop
        elif side_l == "short":
            return last >= stop

        return False
