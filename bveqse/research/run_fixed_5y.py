import pandas as pd
import numpy as np
import datetime
import os
import json
import uuid
import hashlib
import matplotlib.pyplot as plt
from copy import deepcopy

from bveqse.config import BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09
from bveqse.data.loader import download_and_validate
from bveqse.core.types import Bar, SignalState, DataQualityFlag
from bveqse.strategy.signal_generator import generate_signals
from bveqse.backtest.engine import BacktestEngine
from bveqse.research.walk_forward import apply_params_to_config
from bveqse.forward.config_freeze import FORWARD_PARAMS, generate_config_hash, get_frozen_cost_dict
from bveqse.data.universe import INTENDED_SYMBOLS

def run_diagnostic():
    out_dir = "results/FIXED_5Y_DIAGNOSTIC_run"
    os.makedirs(out_dir, exist_ok=True)
    
    print("Loading data...")
    df_dict, _ = download_and_validate("2017-01-01", "2025-12-31")
    
    # Extract unique dates from 2021 to 2025
    all_dates = set()
    for df in df_dict.values():
        all_dates.update(df[(df['date'] >= datetime.date(2021, 1, 1)) & (df['date'] <= datetime.date(2025, 12, 31))]['date'].tolist())
    dates = sorted(list(all_dates))
    
    # Create configuration
    cfg = apply_params_to_config(BASELINE_CONFIG, FORWARD_PARAMS)
    cfg_hash = generate_config_hash()
    universe_hash = hashlib.sha256(str(sorted(INTENDED_SYMBOLS)).encode('utf-8')).hexdigest()
    
    def run_simulation(cost_cfg, capital=20000.0, label="1X"):
        print(f"Running simulation for {label} costs...")
        engine = BacktestEngine(cfg, cost_cfg, cfg_hash)
        engine.cash = capital
        engine.equity = capital
        
        portfolio_history = []
        
        all_signals = []
        for sym, df in df_dict.items():
            sym_sigs = generate_signals(sym, df, cfg, cfg_hash)
            # Filter to 2021-2025
            for s in sym_sigs:
                if datetime.date(2021,1,1) <= s.signal_date <= datetime.date(2025,12,31):
                    all_signals.append(s)
        
        # Precompute median vol
        from collections import defaultdict
        med_vol_series = {}
        for sym, df in df_dict.items():
            df['traded_val'] = df['close'] * df['volume']
            med_vol_series[sym] = df.set_index('date')['traded_val'].rolling(20).median().to_dict()
            
        for dt in dates:
            daily_signals = [s for s in all_signals if s.signal_date == dt]
            if daily_signals:
                # Must deepcopy so signals aren't mutated across 1x and 2x runs
                engine.queue_signals(deepcopy(daily_signals))
                
            # Process day
            daily_bars = {}
            median_vol = {}
            for sym, df in df_dict.items():
                row = df[df['date'] == dt]
                if not row.empty:
                    daily_bars[sym] = Bar(sym, dt, row['open'].values[0], row['high'].values[0], 
                                          row['low'].values[0], row['close'].values[0], 
                                          row['volume'].values[0], 1.0, DataQualityFlag.VALID)
                # Median vol for sizing
                val = med_vol_series[sym].get(dt, 0.0)
                if not pd.isna(val):
                    median_vol[sym] = val
            
            engine.process_day(dt, daily_bars, median_vol)
            
            portfolio_history.append({
                "date": dt.isoformat(),
                "cash": engine.cash,
                "equity": engine.equity,
                "open_positions": len(engine.open_positions)
            })
            
        # Clean up trades at end for metrics
        for sym, pos in list(engine.open_positions.items()):
            if sym in daily_bars:
                engine._execute_exit(pos, daily_bars[sym].close, "DATA_TERMINATION", dt)
        
        return engine, portfolio_history

    engine_1x, hist_1x = run_simulation(INDIA_EQUITY_DELIVERY_2026_09, 20000.0, "1X")
    
    from dataclasses import replace
    cost_2x = replace(INDIA_EQUITY_DELIVERY_2026_09,
                      stt_rate=INDIA_EQUITY_DELIVERY_2026_09.stt_rate * 2,
                      exchange_transaction_charge_rate=INDIA_EQUITY_DELIVERY_2026_09.exchange_transaction_charge_rate * 2,
                      sebi_turnover_fee_rate=INDIA_EQUITY_DELIVERY_2026_09.sebi_turnover_fee_rate * 2,
                      stamp_duty_rate=INDIA_EQUITY_DELIVERY_2026_09.stamp_duty_rate * 2,
                      slippage_rate=INDIA_EQUITY_DELIVERY_2026_09.slippage_rate * 2,
                      dp_charge_per_sell_inr=INDIA_EQUITY_DELIVERY_2026_09.dp_charge_per_sell_inr * 2)
                      
    engine_2x, _ = run_simulation(cost_2x, 20000.0, "2X")
    
    print("Generating outputs...")
    # Exports
    df_trades = pd.DataFrame([vars(t) for t in engine_1x.closed_trades])
    if not df_trades.empty:
        df_trades['entry_date'] = df_trades['entry_date'].astype(str)
        df_trades['exit_date'] = df_trades['exit_date'].astype(str)
        # Convert exit_reason enum
        df_trades['exit_reason'] = df_trades['exit_reason'].apply(lambda x: getattr(x, 'value', str(x)))
        df_trades.to_csv(f"{out_dir}/trades.csv", index=False)
    
    df_hist = pd.DataFrame(hist_1x)
    df_hist.to_csv(f"{out_dir}/portfolio_history.csv", index=False)
    
    # Equity Curve Plot
    if not df_hist.empty:
        plt.figure(figsize=(10,6))
        plt.plot(pd.to_datetime(df_hist['date']), df_hist['equity'], label='1X Equity')
        plt.title('BVEQSE v1.0 Fixed 5-Year Diagnostic (2021-2025)')
        plt.ylabel('Equity (INR)')
        plt.grid(True)
        plt.savefig(f"{out_dir}/fixed_5y_equity_curve.png")
        plt.close()
        
    # Metrics calculation
    def calc_metrics(trades_df):
        if trades_df.empty:
            return {}
        r_vals = trades_df['r_net'].values
        gross_pnl = trades_df['gross_pnl'].sum()
        net_pnl = trades_df['net_pnl'].sum()
        costs = trades_df['fees'].sum()
        wins = r_vals[r_vals > 0]
        losses = r_vals[r_vals <= 0]
        win_rate = len(wins) / len(r_vals)
        pf = abs(trades_df[trades_df['net_pnl'] > 0]['net_pnl'].sum() / trades_df[trades_df['net_pnl'] < 0]['net_pnl'].sum()) if trades_df[trades_df['net_pnl'] < 0]['net_pnl'].sum() != 0 else float('inf')
        return {
            "completed_trades": len(trades_df),
            "win_rate": win_rate,
            "mean_r": np.mean(r_vals),
            "median_r": np.median(r_vals),
            "profit_factor": pf,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "costs": costs
        }
        
    overall = calc_metrics(df_trades)
    
    # 2x comparison
    df_trades_2x = pd.DataFrame([vars(t) for t in engine_2x.closed_trades])
    overall_2x = calc_metrics(df_trades_2x)
    
    # Monte Carlo
    r_vals = df_trades['r_net'].values if not df_trades.empty else np.array([])
    np.random.seed(42)
    dds = []
    terminal_losses = 0
    sims = 10000
    for _ in range(sims):
        sim_r = np.random.choice(r_vals, size=len(r_vals), replace=True)
        cum_r = np.cumsum(sim_r)
        peak = np.maximum.accumulate(cum_r)
        dd = peak - cum_r
        dds.append(np.max(dd))
        if cum_r[-1] < 0:
            terminal_losses += 1
            
    mc_results = {
        "95th_percentile_max_dd": np.percentile(dds, 95) if dds else 0,
        "terminal_loss_probability": terminal_losses / sims
    }
    
    # Annual and Monthly
    if not df_trades.empty:
        df_trades['entry_year'] = pd.to_datetime(df_trades['entry_date']).dt.year
        df_trades['entry_month'] = pd.to_datetime(df_trades['entry_date']).dt.to_period('M')
        
        annual = df_trades.groupby('entry_year').apply(lambda x: pd.Series(calc_metrics(x))).reset_index()
        annual.to_csv(f"{out_dir}/annual_results.csv", index=False)
        
        monthly = df_trades.groupby('entry_month').apply(lambda x: pd.Series(calc_metrics(x))).reset_index()
        monthly.to_csv(f"{out_dir}/monthly_results.csv", index=False)
        
    # Concentration
    concentration = {}
    if not df_trades.empty:
        sym_pnl = df_trades.groupby('symbol')['net_pnl'].sum()
        sym_pnl_pct = sym_pnl / sym_pnl.sum()
        concentration['largest_single_symbol'] = sym_pnl_pct.max()
        
        trade_pnl_pct = df_trades['net_pnl'] / df_trades['net_pnl'].sum()
        concentration['top_5_trades'] = trade_pnl_pct.nlargest(5).sum()
        concentration['largest_single_trade'] = trade_pnl_pct.max()
        
    # Manifest
    manifest = {
        "experiment": "FIXED_5Y_DIAGNOSTIC",
        "run_id": str(uuid.uuid4()),
        "config_hash": cfg_hash,
        "universe_hash": universe_hash,
        "overall_1x": overall,
        "overall_2x": overall_2x,
        "monte_carlo": mc_results,
        "concentration": concentration
    }
    
    with open(f"{out_dir}/run_manifest.json", "w") as f:
        json.dump(manifest, f, indent=4)
        
    print("Done! Check results in", out_dir)

if __name__ == "__main__":
    run_diagnostic()
