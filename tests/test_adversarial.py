import pytest
import datetime
import pandas as pd
import numpy as np
from copy import deepcopy

from bveqse.core.types import Bar, Signal, Position, ExitReason, SignalState, DataQualityFlag
from bveqse.config import StrategyConfig, CostConfig, INDIA_EQUITY_DELIVERY_2026_09, to_dict
from bveqse.core.hashing import generate_config_hash
from bveqse.backtest.execution import evaluate_entry, evaluate_exit
from bveqse.backtest.costs import calculate_leg_costs
from bveqse.strategy.signal_generator import generate_signals

def test_circuit_lock_heuristic_entry():
    config = StrategyConfig()
    signal = Signal("id", "SYM", datetime.date(2026, 1, 1), SignalState.ACCEPTED, 5.0, {})
    # O=H=L=C and Open > Prev_Close (Upper circuit)
    bar = Bar("SYM", datetime.date(2026, 1, 2), 110.0, 110.0, 110.0, 110.0, 1000)
    prev_close = 100.0
    
    state, pos, gap = evaluate_entry(signal, bar, prev_close, config, INDIA_EQUITY_DELIVERY_2026_09)
    assert state == SignalState.EXPIRED_CIRCUIT_LOCK
    assert pos is None

def test_circuit_lock_heuristic_exit():
    config = StrategyConfig()
    pos = Position("SYM", datetime.date(2026, 1, 1), 100.0, 10, 5.0, 90.0, 120.0)
    # O=H=L=C and Close < Prev_Close (Lower circuit)
    bar = Bar("SYM", datetime.date(2026, 1, 3), 80.0, 80.0, 80.0, 80.0, 1000)
    prev_close = 100.0
    
    is_exited, exit_price, reason = evaluate_exit(pos, bar, prev_close, config, INDIA_EQUITY_DELIVERY_2026_09)
    assert is_exited == False
    assert exit_price is None

def test_same_bar_ambiguity_stop_first():
    config = StrategyConfig()
    # Entry at 100. Stop = 90, Target = 120
    pos = Position("SYM", datetime.date(2026, 1, 1), 100.0, 10, 5.0, 90.0, 120.0)
    # Bar touches both target and stop, no gap (Open inside)
    bar = Bar("SYM", datetime.date(2026, 1, 2), 100.0, 125.0, 85.0, 110.0, 1000)
    
    is_exited, exit_price, reason = evaluate_exit(pos, bar, 100.0, config, INDIA_EQUITY_DELIVERY_2026_09)
    assert is_exited == True
    assert reason == ExitReason.STOP
    # Exit price should be Stop * (1 - slippage) if slippage_on_limit_exits=True
    expected_exit = 90.0 * (1.0 - INDIA_EQUITY_DELIVERY_2026_09.slippage_rate)
    assert exit_price == expected_exit

def test_gap_through_stop():
    config = StrategyConfig()
    pos = Position("SYM", datetime.date(2026, 1, 1), 100.0, 10, 5.0, 90.0, 120.0)
    # Gap down below stop (Open = 80)
    bar = Bar("SYM", datetime.date(2026, 1, 2), 80.0, 85.0, 75.0, 82.0, 1000)
    
    is_exited, exit_price, reason = evaluate_exit(pos, bar, 100.0, config, INDIA_EQUITY_DELIVERY_2026_09)
    assert is_exited == True
    assert reason == ExitReason.GAP_STOP
    # Exits at Open * (1 - slippage)
    expected_exit = 80.0 * (1.0 - INDIA_EQUITY_DELIVERY_2026_09.slippage_rate)
    assert exit_price == expected_exit

def test_cost_golden():
    # Golden values test for INDIA_EQUITY_DELIVERY_2026_09
    fill = 1000.0
    qty = 100
    # Turnover = 100,000
    # Brokerage = 0.0
    # STT = 100000 * 0.001 = 100.0
    # Exch = 100000 * 0.0000322 = 3.22
    # SEBI = 100000 * 0.000001 = 0.1
    # Stamp (buy only) = 100000 * 0.00015 = 15.0
    # GST = 18% of (0 + 3.22 + 0.1) = 0.5976
    # Total buy = 100 + 3.22 + 0.1 + 15.0 + 0.5976 = 118.9176
    
    buy_cost = calculate_leg_costs(fill, qty, True, INDIA_EQUITY_DELIVERY_2026_09)
    assert abs(buy_cost - 118.9176) < 1e-5
    
    # Sell side: no stamp duty (15.0), but DP charge (15.34 * 1.18 = 18.1012)
    # Total sell = 100 + 3.22 + 0.1 + 0.5976 + 18.1012 = 122.0188
    sell_cost = calculate_leg_costs(fill, qty, False, INDIA_EQUITY_DELIVERY_2026_09)
    assert abs(sell_cost - 122.0188) < 1e-5

def test_config_hash_changes():
    c1_strat = to_dict(StrategyConfig())
    c1_cost = to_dict(INDIA_EQUITY_DELIVERY_2026_09)
    h1 = generate_config_hash(c1_strat, c1_cost)
    
    # Change strategy param
    c2_strat = to_dict(StrategyConfig(ema_period=55))
    h2 = generate_config_hash(c2_strat, c1_cost)
    assert h1 != h2
    
    # Change cost param
    c3_cost = deepcopy(c1_cost)
    c3_cost['stt_rate'] = 0.002
    h3 = generate_config_hash(c1_strat, c3_cost)
    assert h1 != h3

def test_lookahead_future_modification():
    config = StrategyConfig()
    c_hash = "dummy"
    
    # Generate 100 days of random mock data to pass warmup
    dates = [datetime.date(2026, 1, 1) + datetime.timedelta(days=i) for i in range(100)]
    np.random.seed(42)
    closes = np.cumprod(1 + np.random.randn(100) * 0.02) * 100
    df = pd.DataFrame({
        'date': dates,
        'open': closes,
        'high': closes * 1.01,
        'low': closes * 0.99,
        'close': closes,
        'volume': [1000000] * 100,
        'quality_flag': [DataQualityFlag.VALID] * 100
    })
    
    # Baseline signals
    signals_base = generate_signals("SYM", df, config, c_hash)
    
    # Modify future data (last 10 days)
    df_mod = df.copy()
    df_mod.loc[90:, 'close'] *= 1.5
    df_mod.loc[90:, 'volume'] *= 10
    
    signals_mod = generate_signals("SYM", df_mod, config, c_hash)
    
    # Verify all signals before day 90 remain strictly identical
    base_before_90 = [s for s in signals_base if s.signal_date < dates[90]]
    mod_before_90 = [s for s in signals_mod if s.signal_date < dates[90]]
    
    assert len(base_before_90) == len(mod_before_90)
    for s1, s2 in zip(base_before_90, mod_before_90):
        assert s1.signal_id == s2.signal_id
        assert s1.signal_date == s2.signal_date
        assert s1.atr_signal == s2.atr_signal

def test_indicator_warmup():
    config = StrategyConfig()
    c_hash = "dummy"
    # Create exactly 61 days of data (W=62 for baseline)
    dates = [datetime.date(2026, 1, 1) + datetime.timedelta(days=i) for i in range(61)]
    closes = [100.0] * 61
    df = pd.DataFrame({
        'date': dates,
        'open': closes,
        'high': closes,
        'low': closes,
        'close': closes,
        'volume': [1000000] * 61,
        'quality_flag': [DataQualityFlag.VALID] * 61
    })
    signals = generate_signals("SYM", df, config, c_hash)
    assert len(signals) == 0 # Must be exactly 0 due to warmup W=62
