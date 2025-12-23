"""
test_backtester_closed_trades.py — Tests para closed_trades y realized_pnl

Valida que SimpleBacktester registra correctamente trades cerrados con PnL.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from backtest_initial import SimpleBacktester


class TestClosedTrades:
    """Tests para validar closed_trades y realized_pnl."""

    def test_closed_trade_profit(self):
        """
        Escenario: Comprar a 100, vender a 110 → PnL +100.
        
        - t0: precio 100, target_weight 1.0 → compra 10 shares (capital 1000)
        - t1: precio 110, target_weight 0.0 → vende 10 shares
        - Esperado: 1 closed_trade con realized_pnl = (110-100)*10 = 100
        """
        # Crear prices con 2 fechas
        dates = pd.date_range("2024-01-02", periods=2, freq="D")  # Martes, Miércoles
        prices = pd.DataFrame({"AAA": [100.0, 110.0]}, index=dates)
        
        bt = SimpleBacktester(prices, initial_capital=1000)
        # Forzar target_weights para el test
        bt.target_weights = {"AAA": 1.0}
        # Inicializar estado necesario
        bt.last_valid_prices["AAA"] = 100.0
        bt.portfolio_value = [1000.0]
        
        # Primera fecha: comprar
        bt._rebalance(dates[0])
        
        # Verificar posición abierta
        assert bt.positions["AAA"] == pytest.approx(10.0, rel=0.01)
        assert bt._avg_cost["AAA"] == pytest.approx(100.0)
        
        # Segunda fecha: cerrar posición (cambiar target a 0)
        bt.target_weights = {"AAA": 0.0}
        bt.last_valid_prices["AAA"] = 110.0
        bt.portfolio_value.append(1100.0)  # NAV actualizado
        bt._rebalance(dates[1])
        
        # Verificar closed_trade
        assert len(bt.closed_trades) == 1
        ct = bt.closed_trades[0]
        assert ct["asset"] == "AAA"
        assert ct["qty"] == pytest.approx(10.0, rel=0.01)
        assert ct["entry_cost"] == pytest.approx(100.0)
        assert ct["exit_price"] == pytest.approx(110.0)
        assert ct["realized_pnl"] == pytest.approx(100.0, rel=0.01)

    def test_closed_trade_loss(self):
        """
        Escenario: Comprar a 100, vender a 90 → PnL -100.
        """
        dates = pd.date_range("2024-01-02", periods=2, freq="D")
        prices = pd.DataFrame({"BBB": [100.0, 90.0]}, index=dates)
        
        bt = SimpleBacktester(prices, initial_capital=1000)
        bt.target_weights = {"BBB": 1.0}
        bt.last_valid_prices["BBB"] = 100.0
        bt.portfolio_value = [1000.0]
        
        # Comprar
        bt._rebalance(dates[0])
        assert bt.positions["BBB"] == pytest.approx(10.0, rel=0.01)
        
        # Cerrar con pérdida
        bt.target_weights = {"BBB": 0.0}
        bt.last_valid_prices["BBB"] = 90.0
        bt.portfolio_value.append(900.0)
        bt._rebalance(dates[1])
        
        assert len(bt.closed_trades) == 1
        ct = bt.closed_trades[0]
        assert ct["realized_pnl"] == pytest.approx(-100.0, rel=0.01)

    def test_scale_in_updates_avg_cost(self):
        """
        Escenario: Comprar 5 a 100, luego 5 más a 120 → avg_cost = 110.
        """
        dates = pd.date_range("2024-01-02", periods=2, freq="D")
        prices = pd.DataFrame({"CCC": [100.0, 120.0]}, index=dates)
        
        bt = SimpleBacktester(prices, initial_capital=1000)
        bt.target_weights = {"CCC": 0.5}  # 500 / 100 = 5 shares
        bt.last_valid_prices["CCC"] = 100.0
        bt.portfolio_value = [1000.0]
        
        # Primera compra
        bt._rebalance(dates[0])
        assert bt.positions["CCC"] == pytest.approx(5.0, rel=0.01)
        assert bt._avg_cost["CCC"] == pytest.approx(100.0)
        
        # Scale-in: ahora queremos 100% a precio 120
        bt.target_weights = {"CCC": 1.0}
        bt.last_valid_prices["CCC"] = 120.0
        bt.portfolio_value.append(1100.0)  # 5*120 + 500 cash = 1100
        bt._rebalance(dates[1])
        
        # Nuevas shares: 1100 / 120 ≈ 9.17
        # Avg cost: (100*5 + 120*4.17) / 9.17 ≈ 109.1
        assert bt.positions["CCC"] == pytest.approx(9.17, rel=0.05)
        # El avg_cost debe estar entre 100 y 120
        assert 100 < bt._avg_cost["CCC"] < 120

    def test_partial_close(self):
        """
        Escenario: Comprar 10 shares, vender 5 → closed_trade con qty=5.
        """
        dates = pd.date_range("2024-01-02", periods=2, freq="D")
        prices = pd.DataFrame({"DDD": [100.0, 110.0]}, index=dates)
        
        bt = SimpleBacktester(prices, initial_capital=1000)
        bt.target_weights = {"DDD": 1.0}  # 1000 / 100 = 10 shares
        bt.last_valid_prices["DDD"] = 100.0
        bt.portfolio_value = [1000.0]
        
        bt._rebalance(dates[0])
        assert bt.positions["DDD"] == pytest.approx(10.0, rel=0.01)
        
        # Reducir a 50% (5 shares)
        bt.target_weights = {"DDD": 0.5}
        bt.last_valid_prices["DDD"] = 110.0
        bt.portfolio_value.append(1100.0)
        bt._rebalance(dates[1])
        
        # Debería tener 1 closed_trade con qty ≈ 5
        assert len(bt.closed_trades) == 1
        ct = bt.closed_trades[0]
        assert ct["qty"] == pytest.approx(5.0, rel=0.1)
        assert ct["realized_pnl"] == pytest.approx(50.0, rel=0.1)  # (110-100)*5
