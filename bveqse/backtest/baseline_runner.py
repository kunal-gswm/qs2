import os
import json
import datetime
import pandas as pd
import numpy as np

from bveqse.config import BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09, to_dict
from bveqse.core.hashing import generate_config_hash
from bveqse.core.types import DataQualityFlag, Bar
from bveqse.strategy.signal_generator import generate_signals
from bveqse.backtest.engine import BacktestEngine

def _generate_dummy_data(symbols, num_days):
    dates = [datetime.date(2017, 1, 1) + datetime.timedelta(days=i) for i in range(num_days)]
    df_dict = {}
    for sym in symbols:
        np.random.seed(hash(sym) % (2**32))
        closes = np.cumprod(1 + np.random.randn(num_days) * 0.01) * 100
        df = pd.DataFrame({
            'date': dates,
            'open': closes,
            'high': closes * 1.02,
            'low': closes * 0.98,
            'close': closes,
            'volume': [10000000] * num_days,
            'quality_flag': [DataQualityFlag.VALID] * num_days
        })
        df_dict[sym] = df
    return df_dict

def run_baseline():
    os.makedirs('results/BASELINE_run', exist_ok=True)
    
    # Generate 500 days of data for 5 dummy symbols
    df_dict = _generate_dummy_data(["SYM1", "SYM2", "SYM3", "SYM4", "SYM5"], 500)
    dates = sorted(df_dict["SYM1"]['date'].tolist())
    
    strat_dict = to_dict(BASELINE_CONFIG)
    cost_dict = to_dict(INDIA_EQUITY_DELIVERY_2026_09)
    c_hash = generate_config_hash(strat_dict, cost_dict)
    
    # 1. Signal Level - Vectorized Generation
    all_signals = []
    for sym, df in df_dict.items():
        sigs = generate_signals(sym, df, BASELINE_CONFIG, c_hash)
        all_signals.extend(sigs)
        
    signals_df = pd.DataFrame([
        {"signal_id": s.signal_id, "symbol": s.symbol, "signal_date": s.signal_date, 
         "status": s.status.name, "atr_signal": s.atr_signal, **s.features}
        for s in all_signals
    ])
    
    # 2. Portfolio Capacity Constrained - Engine simulation
    engine = BacktestEngine(BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09, c_hash)
    
    portfolio_history = []
    for dt in dates:
        # Group today's signals
        todays_signals = [s for s in all_signals if s.signal_date == dt]
        engine.queue_signals(todays_signals)
        
        # Prepare daily bars
        daily_bars = {}
        for sym, df in df_dict.items():
            row = df[df['date'] == dt]
            if not row.empty:
                daily_bars[sym] = Bar(sym, dt, row['open'].values[0], row['high'].values[0], 
                                      row['low'].values[0], row['close'].values[0], row['volume'].values[0])
                                      
        engine.process_day(dt, daily_bars, {sym: 1e9 for sym in df_dict.keys()})
        portfolio_history.append({
            "date": dt,
            "cash": engine.cash,
            "equity": engine.equity,
            "open_positions": len(engine.open_positions)
        })
        
    trades_df = pd.DataFrame([
        {"trade_id": t.trade_id, "symbol": t.symbol, "entry_date": t.entry_date, "exit_date": t.exit_date,
         "entry_price": t.entry_price, "exit_price": t.exit_price, "quantity": t.quantity, 
         "exit_reason": t.exit_reason.name, "net_pnl": t.net_pnl}
        for t in engine.closed_trades
    ])
    
    port_df = pd.DataFrame(portfolio_history)
    
    metrics = {
        "run_type": "BASELINE",
        "result_layer": "PORTFOLIO_CAPACITY_CONSTRAINED",
        "completed_trades": len(engine.closed_trades),
        "final_equity": engine.equity,
        "config_hash": c_hash
    }
    
    manifest = {
        "experiment_id": "EXP_BASELINE_TEST",
        "run_type": "BASELINE",
        "config_hash": c_hash,
        "cost_config_id": INDIA_EQUITY_DELIVERY_2026_09.version_id,
        "data_source": "mock_generator"
    }
    
    # Output to results directory
    signals_df.to_csv("results/BASELINE_run/signals.csv", index=False)
    if not trades_df.empty:
        trades_df.to_csv("results/BASELINE_run/trades.csv", index=False)
    port_df.to_csv("results/BASELINE_run/portfolio_history.csv", index=False)
    
    with open("results/BASELINE_run/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
        
    with open("results/BASELINE_run/run_manifest.json", "w") as f:
        json.dump(manifest, f, indent=4)
        
    print("Baseline run completed. Results stored in results/BASELINE_run/")
    
if __name__ == "__main__":
    run_baseline()
