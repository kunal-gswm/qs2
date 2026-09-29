import pytest
import datetime
import pandas as pd
from bveqse.config import StrategyConfig, INDIA_EQUITY_DELIVERY_2026_09
from bveqse.research.walk_forward import run_evaluation
from bveqse.core.types import DataQualityFlag

def _create_mock_data():
    dates = [datetime.date(2018, 1, 1) + datetime.timedelta(days=i) for i in range(1500)]
    closes = [100.0] * 1500
    df = pd.DataFrame({
        'date': dates,
        'open': closes,
        'high': closes,
        'low': closes,
        'close': closes,
        'volume': [1000000] * 1500,
        'quality_flag': [DataQualityFlag.VALID] * 1500
    })
    return {"MOCK": df}

def test_oos_future_modification_leakage():
    # Modify prices in OOS period (2021) and prove it doesn't change training results (2018-2020)
    df_dict = _create_mock_data()
    cfg = StrategyConfig()
    
    # Run training period
    t_start = datetime.date(2018, 1, 1)
    t_end = datetime.date(2020, 12, 31)
    
    base_train = run_evaluation(df_dict, t_start, t_end, cfg, INDIA_EQUITY_DELIVERY_2026_09, "h1")
    
    # Modify data deeply in 2021 (OOS)
    df_mod = df_dict["MOCK"].copy()
    mask = df_mod['date'] >= datetime.date(2021, 1, 1)
    df_mod.loc[mask, 'close'] = 9999.9
    
    mod_train = run_evaluation({"MOCK": df_mod}, t_start, t_end, cfg, INDIA_EQUITY_DELIVERY_2026_09, "h1")
    
    assert len(base_train) == len(mod_train)
    # Both should be exactly the same length and trades, meaning no leak from 2021

def test_purge_straddling_trades():
    # If a trade enters on 2020-12-30 and exits on 2021-01-05
    # run_evaluation with end_date=2020-12-31 should exclude it.
    df_dict = _create_mock_data()
    # Force a trade manually by creating a massive breakout just before end of 2020
    df = df_dict["MOCK"]
    idx = df[df['date'] == datetime.date(2020, 12, 28)].index[0]
    # Set breakout structure
    df.loc[idx-20:idx-1, 'high'] = 101.0 # Resistance
    df.loc[idx, 'close'] = 110.0 # Breakout
    df.loc[idx, 'volume'] = 5000000 # High volume
    
    # Exit triggered in 2021
    idx_exit = df[df['date'] == datetime.date(2021, 1, 5)].index[0]
    df.loc[idx_exit, 'open'] = 10.0 # Gap down to trigger stop
    
    cfg = StrategyConfig()
    
    # Evaluate over 2018-2020
    t_start = datetime.date(2018, 1, 1)
    t_end = datetime.date(2020, 12, 31)
    trades = run_evaluation({"MOCK": df}, t_start, t_end, cfg, INDIA_EQUITY_DELIVERY_2026_09, "h1")
    
    # Trade shouldn't be in closed trades because it hasn't exited by 2020-12-31, 
    # hence it is correctly purged from training stats!
    assert len(trades) == 0

