import json
import csv
import math
import numpy as np
from typing import List, Dict, Any

from bveqse.forward.state import ForwardState
from bveqse.forward.config_freeze import generate_config_hash

def calculate_metrics(trades: list) -> Dict[str, Any]:
    if not trades:
        return {}
    r_vals = [t['r_net'] for t in trades]
    mean_r = sum(r_vals) / len(r_vals)
    wins = [r for r in r_vals if r > 0]
    win_rate = len(wins) / len(r_vals)
    gross_win = sum([t['net_pnl'] for t in trades if t['net_pnl'] > 0])
    gross_loss = abs(sum([t['net_pnl'] for t in trades if t['net_pnl'] < 0]))
    pf = gross_win / gross_loss if gross_loss > 0 else float('inf')
    
    # Bootstrap
    np.random.seed(42)
    means = []
    for _ in range(1000):
        samp = np.random.choice(r_vals, size=len(r_vals), replace=True)
        means.append(np.mean(samp))
    lower_ci = np.percentile(means, 5) if means else 0.0
    
    return {
        "mean_r": mean_r,
        "win_rate": win_rate,
        "profit_factor": pf,
        "bootstrap_lower_ci": lower_ci
    }

def check_failure_conditions(metrics: Dict[str, Any], count: int) -> List[str]:
    flags = []
    if count >= 50:
        if metrics.get("mean_r", 0) < 0:
            flags.append("EXPECTANCY_FAILURE")
        if metrics.get("bootstrap_lower_ci", 0) < 0:
            flags.append("EXPECTANCY_SEVERE")
    return flags

def generate_reports(state: ForwardState):
    trades = state.get_all_trades()
    count = len(trades)
    
    # Milestones
    milestones = [25, 50, 100, 150, 200]
    current_ms = 0
    for m in milestones:
        if count >= m:
            current_ms = m
            
    metrics = calculate_metrics(trades)
    flags = check_failure_conditions(metrics, count)
    
    status = {
        "forward_status": "ACTIVE" if not flags else "FAILED",
        "current_milestone": current_ms,
        "completed_trades": count,
        "metrics": metrics,
        "failure_flags": flags,
        "config_hash": generate_config_hash()
    }
    
    with open("results/forward_status.json", "w") as f:
        json.dump(status, f, indent=4)
        
    if trades:
        with open("results/forward_trades.csv", "w", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=trades[0].keys())
            writer.writeheader()
            writer.writerows(trades)
            
    print(f"Forward Report Generated. Status: {status['forward_status']} | Milestone: {current_ms} | Trades: {count}")

if __name__ == "__main__":
    st = ForwardState()
    generate_reports(st)
