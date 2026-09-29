# BVEQSE v1.0 - Specification Freeze and Mandatory Fixes

This document serves as the frozen specification supplement to `BVEQSE_v1.0_PRD.pdf`. It codifies the mandatory specification fixes and clarifications enacted after the independent audit.

## 1. Mandatory Specification Fixes

### A. Historical OOS trade threshold
* **Threshold**: 200 stitched OOS trades.
* **Interpretation**:
  * `< 200 OOS trades` = `INCONCLUSIVE`
  * It MUST NOT be classified as `FAILED`.
  * The threshold is strictly frozen and MUST NOT be relaxed after seeing the results.

### B. 2026 Final Temporal Holdout Test
* **Definition**: The 2026 test period is designated as `FINAL_TEMPORAL_HOLDOUT`. (It is computationally held out, though not psychologically pristine as of Sept 2026).
* **Criterion**: 
  * Calculate net trade-level R.
  * Construct a **one-sided 95% cluster bootstrap confidence interval** for mean R.
  * Clustering must group by symbol to prevent trades from the same symbol from being treated as fully independent.
  * **Failure Condition**: The holdout fails if the **upper bound of the 95% confidence interval is below 0**.
* **Restriction**: The 2026 holdout MUST NOT be used for parameter selection.

### C. Versioned India Equity Cost Configuration
* **Identifier**: `INDIA_EQUITY_DELIVERY_2026_09`
* **Contents**: Must include effective date, verification date, STT, stamp duty, GST, SEBI charges, exchange transaction charges, and brokerage assumption.
* **Implementation**: The cost model is loaded from a frozen configuration module and hashed. Hard-coding of cost parameters in the logic is strictly prohibited.

### D. Signal-level vs Capacity-constrained Results
* The research engine produces two strictly separated layers:
  1. `SIGNAL_LEVEL`: Evaluates raw strategy hypothesis without portfolio capacity constraints.
  2. `PORTFOLIO_CAPACITY_CONSTRAINED`: Applies all PRD constraints (max 10 positions, max 20% weight, 2% ADV, etc.).
* These result layers must never be mixed.

### E. Identical Signal-generation Path
* A single, canonical signal generation architecture is mandated.
* The historical backtest, walk-forward testing, final temporal holdout, and forward observation engine MUST call the exact same logic. Duplicate strategy logic is prohibited.

### F. Slippage Monitoring States
* Slippage statuses are strictly enumerated:
  * `EVALUABLE`
  * `NOT_EVALUABLE`
  * `TRIGGERED`
* `NOT_EVALUABLE` indicates an absence of independent execution reference and MUST NOT be interpreted as a pass.

## 2. Additional Constraints
* No Machine Learning in v1.0.
* No shorting, leverage, intraday trading, derivatives, or pyramiding.
* No automatic parameter adaptation.
* No modification or importing of TPQSE code/artifacts. BVEQSE remains entirely independent.

## 3. Reporting Distinctions
* Reports MUST distinguish the following runs explicitly:
  * `BASELINE`
  * `WALK_FORWARD_SELECTED`
  * `ABLATION`
  * `SENSITIVITY`
* The optimized walk-forward results must NEVER obscure the frozen `BASELINE` results.
