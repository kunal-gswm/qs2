import os
import json
import pandas as pd
from bveqse.data.universe import NIFTY_100
from bveqse.data.loader import download_data
from bveqse.config import BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09, to_dict
from bveqse.core.hashing import generate_config_hash
from bveqse.research.walk_forward import walk_forward_optimization

def run_engineering_test():
    print("Starting ENGINEERING_TEST for Walk-Forward Optimization")
    os.makedirs('results/ENGINEERING_TEST_run', exist_ok=True)
    
    # We use a severely capped universe just to prove the pipeline executes the 243 grid
    symbols = NIFTY_100[:1]
    
    # Download 2017 to 2026
    print("Downloading data...")
    df_dict, data_report = download_data(symbols, "2017-01-01", "2026-12-31")
    
    print(f"Running 243-combination Walk-Forward Grid over {len(symbols)} symbols...")
    
    # Run the walk-forward optimization
    selection_history, oos_trades, base_trades = walk_forward_optimization(
        df_dict, BASELINE_CONFIG, INDIA_EQUITY_DELIVERY_2026_09
    )
    
    # Output the histories
    with open("results/ENGINEERING_TEST_run/selection_history.json", "w") as f:
        json.dump(selection_history, f, indent=4)
        
    oos_trades_df = pd.DataFrame([
        {"trade_id": t.trade_id, "symbol": t.symbol, "entry_date": t.entry_date.isoformat(), 
         "exit_date": t.exit_date.isoformat(), "entry_price": t.entry_price, 
         "exit_price": t.exit_price, "quantity": t.quantity, 
         "exit_reason": t.exit_reason.name, "net_pnl": t.net_pnl, "r_net": t.r_net}
        for t in oos_trades
    ])
    if not oos_trades_df.empty:
        oos_trades_df.to_csv("results/ENGINEERING_TEST_run/stitched_oos_trades.csv", index=False)
        
    base_trades_df = pd.DataFrame([
        {"trade_id": t.trade_id, "symbol": t.symbol, "entry_date": t.entry_date.isoformat(), 
         "exit_date": t.exit_date.isoformat(), "entry_price": t.entry_price, 
         "exit_price": t.exit_price, "quantity": t.quantity, 
         "exit_reason": t.exit_reason.name, "net_pnl": t.net_pnl, "r_net": t.r_net}
        for t in base_trades
    ])
    if not base_trades_df.empty:
        base_trades_df.to_csv("results/ENGINEERING_TEST_run/baseline_oos_trades.csv", index=False)
        
    print(f"Stitched OOS Trades: {len(oos_trades_df)}")
    print(f"Baseline OOS Trades: {len(base_trades_df)}")
    
    metrics = {
        "run_type": "ENGINEERING_TEST",
        "universe_status": "PARTIAL_UNIVERSE",
        "stitched_oos_trades": len(oos_trades_df),
        "baseline_oos_trades": len(base_trades_df)
    }
    
    with open("results/ENGINEERING_TEST_run/metrics.json", "w") as f:
        json.dump(metrics, f, indent=4)
        
    print("ENGINEERING_TEST completed successfully.")

if __name__ == "__main__":
    run_engineering_test()
