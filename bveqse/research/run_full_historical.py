import os
import json
import pandas as pd
from bveqse.data.universe import INTENDED_SYMBOLS
from bveqse.data.loader import download_and_validate
from bveqse.config import BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09
from bveqse.research.walk_forward import walk_forward_optimization
import hashlib
import time

def generate_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

def execute_run(run_id, df_dict):
    print(f"Starting {run_id}...")
    start_t = time.time()
    results = walk_forward_optimization(
        df_dict, BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09
    )
    print(f"{run_id} completed in {time.time() - start_t:.1f}s")
    return results

def run_full_research():
    print("Starting FULL_HISTORICAL_RESEARCH")
    os.makedirs('results/FULL_HISTORICAL_run', exist_ok=True)
    
    # Step 1: Download & Validate (2017 to 2025 to give 1 year warmup for 2018)
    print("Downloading data & building universe...")
    df_dict, data_report = download_and_validate("2017-01-01", "2025-12-31")
    
    with open("results/FULL_HISTORICAL_run/historical_data_quality_report.json", "w") as f:
        json.dump(data_report, f, indent=4)
        
    print(f"Loaded {data_report['actual_symbol_count']} symbols.")
    
    # Step 2: Reproducibility Runs
    # Run 1
    res1 = execute_run("Run 1", df_dict)
    
    # Run 2
    res2 = execute_run("Run 2", df_dict)
    
    hash1 = generate_hash(res1["selection_history"])
    hash2 = generate_hash(res2["selection_history"])
    
    is_reproducible = (hash1 == hash2)
    print(f"Reproducibility Check: {'IDENTICAL' if is_reproducible else 'DIFFERENT'}")
    
    # Step 3: Serialize Results (using Run 1)
    selection_history = res1["selection_history"]
    oos_trades = res1["stitched_oos_trades"]
    base_trades = res1["stitched_baseline_trades"]
    oos_signals = res1["stitched_oos_signals"]
    base_signals = res1["stitched_baseline_signals"]
    
    with open("results/FULL_HISTORICAL_run/selection_history.json", "w") as f:
        json.dump(selection_history, f, indent=4)
        
    def to_df(trades):
        return pd.DataFrame([
            {"trade_id": t.trade_id, "symbol": t.symbol, "entry_date": t.entry_date.isoformat(), 
             "exit_date": t.exit_date.isoformat(), "entry_price": t.entry_price, 
             "exit_price": t.exit_price, "quantity": t.quantity, 
             "exit_reason": t.exit_reason.name, "net_pnl": t.net_pnl, "r_net": t.r_net, 
             "parameter_set": getattr(t, 'parameter_set_id', 'UNKNOWN')}
            for t in trades
        ])

    def sig_to_df(sigs):
        return pd.DataFrame([
            {"signal_id": s.signal_id, "symbol": s.symbol, "signal_date": s.signal_date.isoformat(), 
             "status": s.status.name, "atr_signal": s.atr_signal, **s.features}
            for s in sigs
        ])
        
    oos_trades_df = to_df(oos_trades)
    base_trades_df = to_df(base_trades)
    
    if not oos_trades_df.empty: oos_trades_df.to_csv("results/FULL_HISTORICAL_run/stitched_oos_trades.csv", index=False)
    if not base_trades_df.empty: base_trades_df.to_csv("results/FULL_HISTORICAL_run/baseline_oos_trades.csv", index=False)
    
    oos_sigs_df = sig_to_df(oos_signals)
    base_sigs_df = sig_to_df(base_signals)
    
    if not oos_sigs_df.empty: oos_sigs_df.to_csv("results/FULL_HISTORICAL_run/stitched_oos_signals.csv", index=False)
    if not base_sigs_df.empty: base_sigs_df.to_csv("results/FULL_HISTORICAL_run/baseline_oos_signals.csv", index=False)
        
    metrics = {
        "run_type": "FULL_HISTORICAL_RESEARCH",
        "universe_status": data_report["universe_status"],
        "stitched_oos_trades": len(oos_trades_df),
        "baseline_oos_trades": len(base_trades_df),
        "stitched_oos_signals": len(oos_sigs_df),
        "baseline_oos_signals": len(base_sigs_df),
        "reproducibility": {
            "run1_hash": hash1,
            "run2_hash": hash2,
            "is_identical": is_reproducible
        }
    }
    
    with open("results/FULL_HISTORICAL_run/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
        
    print(f"Stitched OOS Trades: {len(oos_trades_df)}")

if __name__ == "__main__":
    run_full_research()
