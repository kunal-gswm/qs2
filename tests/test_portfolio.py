import pytest
from bveqse.config import StrategyConfig, INDIA_EQUITY_DELIVERY_2026_09
from bveqse.backtest.costs import calculate_leg_costs
from bveqse.backtest.sizing import calculate_position_size

def test_costs():
    cost = calculate_leg_costs(100.0, 100, True, INDIA_EQUITY_DELIVERY_2026_09)
    # turnover = 10000
    # STT = 10
    # Exchange = 0.322
    # SEBI = 0.01
    # Stamp = 1.5
    # GST = 18% of (0 + 0.322 + 0.01) = 0.05976
    # Total ~ 11.89176
    assert 11.8 < cost < 12.0

def test_sizing():
    config = StrategyConfig()
    eq = 1_000_000
    cash = 1_000_000
    # risk fraction = 0.005 -> risk_amount = 5000
    # R = 10
    # q_risk = 500
    
    q = calculate_position_size(
        equity=eq,
        available_cash=cash,
        f_entry=100.0,
        r_per_share=10.0,
        median_traded_value=1_000_000_000.0, # plenty of liquidity
        config=config
    )
    assert q == 500
