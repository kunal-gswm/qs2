import pandas as pd
import numpy as np
import json
import datetime
import itertools
from copy import deepcopy

from bveqse.config import BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09, StrategyConfig, CostConfig
from bveqse.data.universe import INTENDED_SYMBOLS
from bveqse.data.loader import download_and_validate
from bveqse.core.types import Signal, SignalState, Trade
from bveqse.backtest.engine import BacktestEngine
from bveqse.research.walk_forward import GRID_PARAMS, apply_params_to_config, run_evaluation, FOLDS

def run_2x_costs(df_dict):
    print("--- 2x Cost Sensitivity ---")
    df_sig = pd.read_csv('results/FULL_HISTORICAL_run/stitched_oos_signals.csv')
    df_sig = df_sig[df_sig['status'] == 'ACCEPTED']
    
    # Reconstruct signals
    signals = []
    for _, row in df_sig.iterrows():
        dt = datetime.date.fromisoformat(row['signal_date'])
        features = {c: row[c] for c in df_sig.columns if c not in ['signal_id', 'symbol', 'signal_date', 'status', 'atr_signal']}
        s = Signal(row['signal_id'], row['symbol'], dt, SignalState.ACCEPTED, row['atr_signal'], features)
        signals.append(s)
        
    # 2x Cost config
    from dataclasses import replace
    cost_2x = replace(INDIA_EQUITY_DELIVERY_2026_09,
                      stt_rate=INDIA_EQUITY_DELIVERY_2026_09.stt_rate * 2,
                      exchange_transaction_charge_rate=INDIA_EQUITY_DELIVERY_2026_09.exchange_transaction_charge_rate * 2,
                      sebi_turnover_fee_rate=INDIA_EQUITY_DELIVERY_2026_09.sebi_turnover_fee_rate * 2,
                      stamp_duty_rate=INDIA_EQUITY_DELIVERY_2026_09.stamp_duty_rate * 2,
                      slippage_rate=INDIA_EQUITY_DELIVERY_2026_09.slippage_rate * 2,
                      dp_charge_per_sell_inr=INDIA_EQUITY_DELIVERY_2026_09.dp_charge_per_sell_inr * 2)
                      
    engine = BacktestEngine(BASELINE_CONFIG, cost_2x, "WF_2X")
    
    # Process dates
    dates = sorted(list(set(datetime.date.fromisoformat(d) for d in df_sig['signal_date'].unique())))
    # Need all dates from 2021 to 2025 to process exits
    all_dates = []
    for df in df_dict.values():
        all_dates.extend(df[(df['date'] >= datetime.date(2021,1,1)) & (df['date'] <= datetime.date(2025,12,31))]['date'].tolist())
    all_dates = sorted(list(set(all_dates)))
    
    for dt in all_dates:
        todays_signals = [s for s in signals if s.signal_date == dt]
        if todays_signals:
            engine.queue_signals(todays_signals)
        daily_bars = {}
        for sym, df in df_dict.items():
            row = df[df['date'] == dt]
            if not row.empty:
                from bveqse.core.types import Bar, DataQualityFlag
                daily_bars[sym] = Bar(sym, dt, row['open'].values[0], row['high'].values[0], row['low'].values[0], row['close'].values[0], row['volume'].values[0], 1.0, DataQualityFlag.VALID)
        engine.process_day(dt, daily_bars, {sym: 1e9 for sym in df_dict.keys()})
        
    trades_2x = engine.closed_trades
    
    df_2x = pd.DataFrame([{
        "trade_id": t.trade_id, "symbol": t.symbol, "entry_date": t.entry_date, 
        "net_pnl": t.net_pnl, "r_net": t.r_net
    } for t in trades_2x])
    df_2x.to_csv('results/FULL_HISTORICAL_run/cost_sensitivity_results.csv', index=False)
    
    print(f"1x Mean R: {pd.read_csv('results/FULL_HISTORICAL_run/stitched_oos_trades.csv')['r_net'].mean()}")
    print(f"2x Mean R: {df_2x['r_net'].mean() if not df_2x.empty else 0}")
    print(f"2x Trades: {len(df_2x)}")
    return df_2x

def run_neighbor_plateau(df_dict):
    print("--- Neighbor Plateau ---")
    with open('results/FULL_HISTORICAL_run/selection_history.json', 'r') as f:
        history = json.load(f)
        
    results = []
    for h in history:
        fold = [f for f in FOLDS if f['id'] == h['fold_id']][0]
        sel = h['selected_parameters']
        
        # Find neighbors (distance 1 in exactly 1 dimension)
        neighbors = []
        for key, grid_vals in GRID_PARAMS.items():
            idx = grid_vals.index(sel[key])
            if idx > 0:
                n = deepcopy(sel)
                n[key] = grid_vals[idx-1]
                neighbors.append(n)
            if idx < len(grid_vals) - 1:
                n = deepcopy(sel)
                n[key] = grid_vals[idx+1]
                neighbors.append(n)
                
        for n in neighbors:
            cfg = apply_params_to_config(BASELINE_CONFIG, n)
            c_hash = f"N_{n['rho']}_{n['L']}_{n['mu_v']}_{n['k']}_{n['m']}"
            _, trades = run_evaluation(df_dict, fold['train_start'], fold['train_end'], cfg, INDIA_EQUITY_DELIVERY_2026_09, c_hash)
            
            mean_r = sum(t.r_net for t in trades)/len(trades) if len(trades) >= 10 else -999.0
            results.append({
                "fold_id": h['fold_id'],
                "neighbor_params": str(n),
                "trades": len(trades),
                "mean_r": mean_r,
                "is_positive": mean_r > 0
            })
            
    df_res = pd.DataFrame(results)
    df_res.to_csv('results/FULL_HISTORICAL_run/neighbor_plateau_results.csv', index=False)
    
    pos = df_res['is_positive'].sum()
    total = len(df_res)
    print(f"Total Neighbors: {total}, Positive: {pos}, Ratio: {pos/total:.1%}")

def run_random_controls():
    print("--- Random Controls ---")
    df = pd.read_csv('results/FULL_HISTORICAL_run/stitched_oos_trades.csv')
    returns = df['r_net'].values
    
    np.random.seed(42)
    obs_mean = np.mean(returns)
    n_sims = 10000
    sim_means = []
    
    # Sign-flipping permutation test (Zero-mean null hypothesis)
    for _ in range(n_sims):
        signs = np.random.choice([-1, 1], size=len(returns))
        sim_returns = returns * signs
        sim_means.append(np.mean(sim_returns))
        
    sim_means = np.array(sim_means)
    p_val = np.sum(sim_means >= obs_mean) / n_sims
    
    df_rc = pd.DataFrame({
        "simulation_type": ["Sign-Flipping Zero-Mean Test"],
        "n_simulations": [n_sims],
        "seed": [42],
        "observed_mean_r": [obs_mean],
        "p_value": [p_val],
        "N1_PASS": [p_val <= 0.05],
        "N2_PASS": [p_val <= 0.10]
    })
    df_rc.to_csv('results/FULL_HISTORICAL_run/random_control_results.csv', index=False)
    print(f"P-value: {p_val}")

if __name__ == '__main__':
    df_dict, _ = download_and_validate("2017-01-01", "2025-12-31")
    run_2x_costs(df_dict)
    run_neighbor_plateau(df_dict)
    run_random_controls()
