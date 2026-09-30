# BVEQSE v1.0

**Breakout Volatility Expansion Quantitative Strategy Engine**

BVEQSE is a research framework for testing a long-only breakout and volatility-compression strategy on Indian equities. It utilizes deterministic backtesting, expanding walk-forward evaluation, statistical robustness tests, and a controlled forward observation pipeline.

---

## Research Status

```text
Engineering Status: REPRODUCIBLE
Historical Protocol Status: INCONCLUSIVE
Forward Observation: ACTIVE
```

The historical walk-forward evaluation produced **91** stitched Out-Of-Sample (OOS) trades. Because the frozen protocol strictly requires a minimum of **200** OOS trades for statistical validation, the strategy cannot yet be classified as Historically Promising. As a result, the protocol status is `INCONCLUSIVE`. Forward observation began on `2026-10-01` to accumulate genuine out-of-sample data. No live order routing is enabled.

---

## What BVEQSE Tests

**Strategy Hypothesis**: A breakout following consolidation and volatility compression, accompanied by abnormal volume and trend confirmation, may contain information about subsequent price continuation after realistic costs and slippage.

Core evaluated components include:
* EMA(50) trend filter
* Consolidation / breakout structure
* NATR compression
* Abnormal volume
* Traded-value liquidity filter
* Next-session-open execution semantics
* ATR-based stop-loss
* Fixed-R target
* Fractional risk sizing
* Strict portfolio capacity constraints

---

## Research Principles

* Long-only
* Daily data
* No leverage
* No derivatives
* No intraday trading
* No pyramiding
* No averaging down
* No ML in v1.0
* No automatic parameter adaptation
* No live order routing
* Deterministic execution
* Explicit transaction costs
* Explicit slippage
* Look-ahead protection
* Expanding walk-forward validation
* Temporal holdout
* Reproducible experiment manifests
* Frozen configuration

---

## Historical Research Results

The following metrics represent the final audited values derived from the historical expanding walk-forward simulation:

| Metric | Result |
| :--- | ---: |
| Stitched OOS Trades | 91 |
| Required OOS Trades | 200 |
| Mean OOS Expectancy | 1.042R |
| Bootstrap 95% Lower Bound | 0.742R |
| Profit Factor | 3.40 |
| Positive OOS Folds | 5/5 |
| 2× Cost Expectancy | 0.842R |
| Neighbor Plateau | 92.0% |
| Single Symbol Contribution | 8.5% |
| Top 5 Trade Contribution | 17.0% |
| Monte Carlo Terminal Loss Probability | 0.0% |

> **Note**: These results are descriptive evidence from the available historical sample. They do not satisfy the frozen ≥200 OOS-trade requirement, so BVEQSE v1.0 remains `INCONCLUSIVE`.

---

## Statistical Research

### Evaluated
* Expectancy
* Bootstrap confidence bound
* Profit factor
* Fold consistency
* 2× cost sensitivity
* Neighbor plateau
* Random-control sign-flipping test
* Monte Carlo analysis
* Concentration analysis
* Regime analysis (where sufficient trade counts exist)

### Not Yet Evaluable
* **Deflated Sharpe Ratio (DSR)**: The required rejected-trial equity-curve information was purposefully not retained during the massive parameter search to prevent out-of-memory errors.
* **2026 Temporal Holdout**: The historical dataset strictly ends on `2025-12-30`.
* **Regime Buckets**: Buckets with fewer than 30 trades (2021–2024).

### Unresolved
* Historical survivorship bias remains `UNRESOLVED` due to the configured partial/current universe limitations.

---

## Walk-Forward Methodology

BVEQSE employs an expanding-window walk-forward validation framework across five historical OOS periods:

| Training | OOS |
| :--- | :--- |
| 2018–2020 | 2021 |
| 2018–2021 | 2022 |
| 2018–2022 | 2023 |
| 2018–2023 | 2024 |
| 2018–2024 | 2025 |

Parameters are deterministically selected using only training data. OOS data is strictly isolated and is not used for parameter selection. Any boundary-straddling trades are purged from selection statistics. Selected parameters are frozen for the corresponding OOS period, and the final OOS results are stitched chronologically. 

---

## Universe and Data Limitations

* The historical research utilized a configured partial universe.
* 44 of 45 configured symbols successfully resolved.
* `TATAMOTORS.NS` remains unresolved due to vendor 404 constraints.
* Survivorship bias is `UNRESOLVED`.
* Therefore, the historical results should not be interpreted as a perfect point-in-time NIFTY 100 backtest.

---

## Forward Observation

Forward observation began natively on **2026-10-01**.
Current milestone: **0 completed trades**.

The controlled forward observation pipeline:
* Uses the fully frozen configuration and hashes.
* Uses the canonical signal/execution path.
* Records executed trades, raw signals, and capacity-rejected signals.
* Persists durable state in an SQLite WAL database.
* Is fully idempotent (re-running a session will not duplicate trades).
* Actively checks configuration hashes to prevent drift.
* Monitors failure conditions continuously.
* Does **not** place real trades.

**Milestone Track**: `25 → 50 → 100 → 150 → 200 trades`
*(Note: Reaching 200 trades does not automatically mean validation. The remaining acceptance criteria must also be independently evaluated at that milestone).*

---

## Failure Monitoring

The forward engine actively monitors the following failure conditions:
* **Expectancy Failure**: Net expectancy < 0 after ≥50 trades.
* **Severe Expectancy Failure**: Cluster-bootstrap lower confidence bound < 0.
* **Drawdown**: Breach of the 20% hard threshold, or exceeding the scaled historical 95th Monte Carlo percentile.
* **Slippage**: Rolling median of the latest 25 trades > 0.15% (when independently evaluable).
* **Data-Quality**: >5% expected sessions missing or late over a rolling 60-session window.
* **Integrity**: Immediate severe failure on configuration hash mismatch or corrupted/duplicate IDs.

---

## Repository Structure

```text
bveqse/
├── data/           # Dataloaders, validation, and universe definition
├── strategy/       # Signal generation and strategy logic
├── backtest/       # Canonical execution semantics and engine
├── research/       # Historical walk-forward, statistical audits, and ablations
├── forward/        # Controlled forward-observation framework and durable state
├── reporting/      # Metrics calculation and milestone reporting
├── analysis/       # Standalone analytical notebooks
│   └── tpqse_comparison/
├── dashboard/      # Visualization and read-only status monitoring
├── ml_export/      # Signal-time dataset generation (features/labels)
└── tests/          # Unit tests, adversarial look-ahead tests, and integrity tests
```

---

## Reproducibility

Every research run tracks standard lineage requirements: experiment ID, configuration state, deterministic seeds, Python/dependency versions, and Git commits. 

Deterministic reruns of the 106,920-evaluation historical walk-forward architecture perfectly reproduced the baseline state. 

**Historical Reproducibility Hash**: 
`84c9c8660505c2a0bf12df3fd8607d00cda96177c455efdc72b07dcb35fd886e`

---

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/bveqse.git
cd bveqse

# Create a Python 3.11 virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Testing

The repository maintains strict testing isolation:
* **Historical Engineering Tests**: Passed (includes execution logic, parameter selection, and boundary purges).
* **Statistical Audit**: Passed (validates significance testing, plateau structures, and cost multipliers).
* **Forward-Framework Tests**: Passed (verifies idempotency, state persistence, and config-drift barriers).

To run the unit and integrity tests:
```bash
python -m unittest discover tests/
```

---

## Forward Operation

To invoke the forward engine for a specific market session:

```bash
python -m bveqse.forward.engine 2026-10-01
python -m bveqse.forward.reporting
```

> **CRITICAL**: Do NOT backfill fake observations into the forward database. The engine relies on genuine point-in-time sequential processing. Re-running the engine for the same session is fully idempotent and will not corrupt state.

---

## Research Roadmap

* Continue genuine forward observation.
* Accumulate completed OOS trades.
* Monitor failure conditions.
* Reach 25 / 50 / 100 / 150 / 200 milestones.
* Re-evaluate the frozen acceptance criteria when sufficient observations exist.
* Resolve survivorship/data-quality limitations where possible.
* Evaluate 2026 temporal holdout when the required data becomes available.
* Future ML work requires a separate PRD and proper time-series validation.

---

## Disclaimer

This repository is an experimental quantitative research project. Historical and forward-observation results are not guarantees of future performance. The system is not connected to live brokerage execution and should not be interpreted as investment advice or a production trading system.
