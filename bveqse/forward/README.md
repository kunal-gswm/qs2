# BVEQSE v1.0 Forward Observation Framework

## Overview
This package implements the rigid, immutable forward observation framework required by the BVEQSE v1.0 PRD. 
Because the historical protocol status is `INCONCLUSIVE` (91 stitched OOS trades vs 200 required), this framework exclusively acts as a passive, non-trading monitor. It accumulates genuine out-of-sample data on a daily basis to natively satisfy the 200-trade requirement over time.

## Frozen Components
* **Configuration**: Strategy parameters, sizing, and filters are cryptographically hashed and actively checked for drift.
* **Universe**: Frozen list of NIFTY 100 components exactly as configured during historical evaluation.
* **Execution/Costs**: Locked at v1.0 canonical rates (e.g., zero brokerage, full STT/Exchange fees, 0.05% slippage).

## How it works (Idempotency & State)
* The script `engine.py` is invoked daily via a cron job or GitHub Action.
* The state is persisted in an SQLite database (`bveqse_forward.db`) utilizing WAL mode for robust concurrent reads/writes.
* Using deterministic IDs and SQLite `INSERT OR IGNORE`, running the engine multiple times for the same market session is fully **idempotent**. State cannot be corrupted by redundant CI runs.

## Milestone Tracking & Failure Monitoring
Milestones are actively logged at `25, 50, 100, 150, 200` completed trades.
The system automatically tracks these failure thresholds:
1. **EXPECTANCY_FAILURE**: Net expectancy < 0 after 50 trades.
2. **EXPECTANCY_SEVERE**: Cluster-bootstrap lower bound < 0.
3. **DRAWDOWN**: > 20% hard threshold or exceeding the historical 95th Monte Carlo percentile.
4. **INTEGRITY_SEVERE**: Configuration hash mismatch or duplicate ID detection.

## Restarting & Recovery
Because all signals, rejections, and trades are deterministically hashed, simply executing `python -m bveqse.forward.engine <YYYY-MM-DD>` will seamlessly resume the portfolio state by pulling historical context up to that point. No manual recovery is needed.
