import pandas as pd
import json
from bveqse.config import BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09, StrategyConfig
from bveqse.data.loader import download_and_validate
from bveqse.research.walk_forward import run_evaluation
import datetime
from copy import deepcopy

def run_ablations():
    print("Downloading data for Ablations (2021-2025)...")
    # Quick mock load since we know the hash and already loaded it in full run, but we must reload
    # Actually, loading from yf takes 30 seconds.
    df_dict, _ = download_and_validate("2020-01-01", "2025-12-31")
    
    start = datetime.date(2021, 1, 1)
    end = datetime.date(2025, 12, 31)
    
    ablations = [
        ("NO_TREND_FILTER", {"trend_ema_period": 1}), # 1 means no EMA trend
        ("NO_VOLUME_FILTER", {"volume_multiple_mu": 0.0}), # 0 means no volume spike req
        ("RELAXED_CONSOLIDATION", {"consolidation_lookback_L": 5}) # 5 instead of 20
    ]
    
    from dataclasses import replace
    for name, params in ablations:
        cfg = replace(BASELINE_CONFIG, **params)
        sigs, trades = run_evaluation(df_dict, start, end, cfg, INDIA_EQUITY_DELIVERY_2026_09, f"ABL_{name}")
        if len(trades) > 0:
            mean_r = sum(t.r_net for t in trades) / len(trades)
        else:
            mean_r = 0.0
        print(f"{name} | Trades: {len(trades)} | Mean R: {mean_r:.3f}")

if __name__ == '__main__':
    run_ablations()
