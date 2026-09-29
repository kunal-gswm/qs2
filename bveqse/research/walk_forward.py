import datetime
import itertools
from copy import deepcopy
import pandas as pd
from typing import List, Dict, Any, Tuple
import concurrent.futures
from bveqse.config import StrategyConfig, CostConfig
from bveqse.core.types import Signal, Trade, Bar
from bveqse.strategy.signal_generator import generate_signals
from bveqse.backtest.engine import BacktestEngine

FOLDS = [
    {"id": 1, "train_start": datetime.date(2018, 1, 1), "train_end": datetime.date(2020, 12, 31), "oos_start": datetime.date(2021, 1, 1), "oos_end": datetime.date(2021, 12, 31)},
    {"id": 2, "train_start": datetime.date(2018, 1, 1), "train_end": datetime.date(2021, 12, 31), "oos_start": datetime.date(2022, 1, 1), "oos_end": datetime.date(2022, 12, 31)},
    {"id": 3, "train_start": datetime.date(2018, 1, 1), "train_end": datetime.date(2022, 12, 31), "oos_start": datetime.date(2023, 1, 1), "oos_end": datetime.date(2023, 12, 31)},
    {"id": 4, "train_start": datetime.date(2018, 1, 1), "train_end": datetime.date(2023, 12, 31), "oos_start": datetime.date(2024, 1, 1), "oos_end": datetime.date(2024, 12, 31)},
    {"id": 5, "train_start": datetime.date(2018, 1, 1), "train_end": datetime.date(2024, 12, 31), "oos_start": datetime.date(2025, 1, 1), "oos_end": datetime.date(2025, 12, 31)}
]

GRID_PARAMS = {
    "rho": [0.075, 0.10, 0.125],
    "L": [15, 20, 30],
    "mu_v": [1.25, 1.5, 2.0],
    "k": [1.25, 1.5, 1.75],
    "m": [1.5, 2.0, 3.0]
}

def generate_grid() -> List[Dict[str, float]]:
    keys = list(GRID_PARAMS.keys())
    combinations = list(itertools.product(*[GRID_PARAMS[k] for k in keys]))
    return [dict(zip(keys, combo)) for combo in combinations]

def apply_params_to_config(base_config: StrategyConfig, params: Dict[str, float]) -> StrategyConfig:
    d = deepcopy(base_config)
    from dataclasses import replace
    return replace(d,
                   range_threshold_rho=params["rho"],
                   consolidation_lookback_L=int(params["L"]),
                   volume_multiple_mu=params["mu_v"],
                   stop_atr_multiple_k=params["k"],
                   target_r_multiple_m=params["m"])

def run_evaluation(
    df_dict: Dict[str, pd.DataFrame], 
    start_date: datetime.date, 
    end_date: datetime.date, 
    config: StrategyConfig, 
    cost_config: CostConfig, 
    c_hash: str
) -> Tuple[List[Signal], List[Trade]]:
    all_signals = []
    for sym, df in df_dict.items():
        df_masked = df[df['date'] <= end_date]
        sigs = generate_signals(sym, df_masked, config, c_hash)
        all_signals.extend(sigs)
        
    eval_signals = [s for s in all_signals if start_date <= s.signal_date <= end_date]
    engine = BacktestEngine(config, cost_config, c_hash)
    
    dates_list = []
    for df in df_dict.values():
        dates_list.extend(df[(df['date'] >= start_date) & (df['date'] <= end_date)]['date'].tolist())
    dates = sorted(list(set(dates_list)))
    
    for dt in dates:
        todays_signals = [s for s in eval_signals if s.signal_date == dt]
        engine.queue_signals(todays_signals)
        daily_bars = {}
        for sym, df in df_dict.items():
            row = df[df['date'] == dt]
            if not row.empty:
                daily_bars[sym] = Bar(sym, dt, row['open'].values[0], row['high'].values[0], 
                                      row['low'].values[0], row['close'].values[0], row['volume'].values[0])
        engine.process_day(dt, daily_bars, {sym: 1e9 for sym in df_dict.keys()})
        
    trades = [t for t in engine.closed_trades if t.exit_date <= end_date and t.entry_date >= start_date]
    return eval_signals, trades

def evaluate_single_param(p, df_dict, fold, base_config, cost_config):
    cfg = apply_params_to_config(base_config, p)
    c_hash = f"WF_{p['rho']}_{p['L']}_{p['mu_v']}_{p['k']}_{p['m']}"
    t_sigs, t_trades = run_evaluation(df_dict, fold["train_start"], fold["train_end"], cfg, cost_config, c_hash)
    
    if len(t_trades) >= 10:
        mean_r = sum(t.r_net for t in t_trades) / len(t_trades)
    else:
        mean_r = -999.0
    
    return (p["rho"], p["L"], p["mu_v"], p["k"], p["m"]), mean_r

def walk_forward_optimization(df_dict: Dict[str, pd.DataFrame], base_config: StrategyConfig, cost_config: CostConfig) -> Dict[str, Any]:
    grid = generate_grid()
    results = {
        "selection_history": [],
        "stitched_oos_trades": [],
        "stitched_oos_signals": [],
        "stitched_baseline_trades": [],
        "stitched_baseline_signals": []
    }
    
    for fold in FOLDS:
        # Evaluate Baseline OOS
        b_sigs, b_trades = run_evaluation(df_dict, fold["oos_start"], fold["oos_end"], base_config, cost_config, "BASELINE")
        for t in b_trades:
            t.trade_id = f"BASE_{fold['id']}_{t.trade_id}"
            t.parameter_set_id = "BASELINE"
        results["stitched_baseline_trades"].extend(b_trades)
        results["stitched_baseline_signals"].extend(b_sigs)
        
        # Grid Search with multiprocessing
        best_param = None
        best_score = -9999.0
        cell_expectancies = {}
        
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(evaluate_single_param, p, df_dict, fold, base_config, cost_config)
                for p in grid
            ]
            for future in concurrent.futures.as_completed(futures):
                p_tuple, mean_r = future.result()
                cell_expectancies[p_tuple] = mean_r
        
        for p in grid:
            p_tuple = (p["rho"], p["L"], p["mu_v"], p["k"], p["m"])
            score = cell_expectancies[p_tuple]
            if score > best_score and score > 0:
                best_score = score
                best_param = p
                
        flags = []
        if best_param is None:
            # PRD Section 13.1 fallback
            best_param = {"rho": base_config.range_threshold_rho, "L": base_config.consolidation_lookback_L, 
                          "mu_v": base_config.volume_multiple_mu, "k": base_config.stop_atr_multiple_k, 
                          "m": base_config.target_r_multiple_m}
            flags.append("NO_POSITIVE_TRAIN_CELL")
            
        oos_cfg = apply_params_to_config(base_config, best_param)
        oos_c_hash = f"WF_{best_param['rho']}_{best_param['L']}_{best_param['mu_v']}_{best_param['k']}_{best_param['m']}"
        oos_sigs, oos_trades = run_evaluation(df_dict, fold["oos_start"], fold["oos_end"], oos_cfg, cost_config, oos_c_hash)
        
        for t in oos_trades:
            t.trade_id = f"WF_{fold['id']}_{t.trade_id}"
            t.parameter_set_id = oos_c_hash
            
        results["stitched_oos_trades"].extend(oos_trades)
        results["stitched_oos_signals"].extend(oos_sigs)
        
        results["selection_history"].append({
            "fold_id": fold["id"],
            "training_start": fold["train_start"].isoformat(),
            "training_end": fold["train_end"].isoformat(),
            "oos_start": fold["oos_start"].isoformat(),
            "oos_end": fold["oos_end"].isoformat(),
            "selected_parameters": best_param,
            "selection_metric": best_score,
            "oos_trade_count": len(oos_trades),
            "flags": flags
        })
        
    return results
