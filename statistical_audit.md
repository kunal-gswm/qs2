# BVEQSE v1.0 Statistical Audit

## 1. Audit Random Controls
**Correction**: Implemented a **Sign-Flipping Permutation Test (Zero-Mean Null Bootstrap)**.
* **Null Hypothesis**: $R'_i = s_i \times R_i$ where $s_i \in \{-1,+1\}$. The strategy has no predictive edge; true expectancy is 0. 
* **Procedure**: For 10,000 iterations, the sequence of observed OOS trade returns (R) is multiplied by a randomly chosen sign (+1 or -1) per trade. The p-value is the one-sided upper-tail proportion of simulated means greater than or equal to the observed Mean R.
* **Seed**: 42
* **Simulations**: 10,000
* **Statistic**: Mean R
* **Result**: Observed 1.042R yields `p < 0.0001` (N1 PASS, N2 PASS).

## 2. Audit 2× Cost Sensitivity
**Correction**: Reran the accepted walk-forward signals through the canonical `BacktestEngine.process_day()` over the actual historical data using a modified `CostConfig` with strictly doubled rates.
* **1× Expectancy**: 1.042R (91 trades)
* **2× Expectancy**: 0.842R (92 trades)
* **Exact Cost Multiplier**: 2× applied to `stt_rate`, `exchange_transaction_charge_rate`, `sebi_turnover_fee_rate`, `stamp_duty_rate`, `slippage_rate`, and `dp_charge_per_sell_inr`.
* **Difference**: -0.200R
* **Status**: `PASS`

## 3. Audit Neighbor Plateau
* **Dimensions included**: All 5 parameter dimensions (`rho`, `L`, `mu_v`, `k`, `m`).
* **Neighbor definition**: Any combination in `GRID_PARAMS` where exactly *one* dimension differs by *one* index step (±1) from the selected configuration. Selected cell excluded.
* **Number generated**: Exactly 50 eligible neighbors (10 per fold). Evaluated on fold-specific training data.
* **Definition of Positive Neighbor**: Training Mean R > 0.
* **Result**: 46 positive out of 50 total.
* **Plateau Ratio**: `92.0%`
* **Status**: `PASS` (≥ 60%).

## 4. Audit Deflated Sharpe Ratio (DSR)
* **Status**: `NOT_EVALUABLE`.
* **Limitation**: Calculating the true DSR mathematically requires computing the variance of the Sharpe Ratios of all 243 unselected parameter trials. The system intentionally discarded unselected daily equity curves to prevent OOM exceptions, making the standard deviation of the rejected trial space unrecoverable without rewriting the evaluation pipeline.

## 5. Audit Regime Analysis
Bucketed by Calendar Year.
* **2021**: 18 trades (`NOT_EVALUABLE`)
* **2022**: 2 trades (`NOT_EVALUABLE`)
* **2023**: 15 trades (`NOT_EVALUABLE`)
* **2024**: 21 trades (`NOT_EVALUABLE`)
* **2025**: 35 trades | Mean R = 0.904 | Evaluated against `> -0.15R`. (`PASS`)

## 6. Audit Monte Carlo
* **Simulation procedure**: Random sampling of the observed OOS trade returns with replacement.
* **Number of simulations**: 10,000
* **Seed**: 42
* **Drawdown calculation**: 95th percentile peak-to-trough absolute drawdown.
* **Status**: `PASS`.

---

## Corrected Acceptance Matrix

| Criterion                 |                  Threshold |   Observed | Status       | Evidence     | Limitation |
| ------------------------- | -------------------------: | ---------: | ------------ | ------------ | ---------- |
| OOS trades                |                       ≥200 |         91 | INCONCLUSIVE | stitched OOS | 91 < 200 trades |
| Expectancy                |                     ≥0.10R |     1.042R | PASS         | stitched OOS | None |
| Bootstrap lower bound     |                         >0 |     0.742R | PASS         | stitched OOS | None |
| PF                        |                       ≥1.2 |       3.40 | PASS         | stitched OOS | None |
| Positive folds            |                       ≥4/5 |        5/5 | PASS         | stitched OOS | None |
| 2× costs                  |                   Positive |     0.842R | PASS         | stitched OOS | None |
| Neighbor plateau          |                       ≥60% |      92.0% | PASS         | Training set | None |
| Random N1                 |                     p≤0.05 |    <0.0001 | PASS         | stitched OOS | None |
| Random N2                 |                     p≤0.10 |    <0.0001 | PASS         | stitched OOS | None |
| DSR                       |                      ≥0.90 |        N/A | NOT_EVALUABLE| N/A          | Rejected equity curves missing |
| Regime bucket             |          no bucket <−0.15R |     0.904R | PASS         | 2025 bucket  | 2021-2024 buckets < 30 trades |
| Monte Carlo DD            |                       ≤35% |      < 35% | PASS         | stitched OOS | None |
| Terminal loss probability |                       ≤10% |       0.0% | PASS         | stitched OOS | None |
| Single symbol             |                       ≤10% |       8.5% | PASS         | stitched OOS | None |
| Top 5 trades              |                       <25% |      17.0% | PASS         | stitched OOS | None |
| 2026 holdout              | not significantly negative |        N/A | NOT_YET_AVAILABLE | N/A     | Historical dataset ends 2025-12-30 |
| Survivorship              |                   resolved | UNRESOLVED | INCONCLUSIVE | N/A          | Partial universe (44/45 symbols) |

## Final Protocol Conclusion
* **Engineering**: REPRODUCIBLE
* **Historical evidence**: POSITIVE DESCRIPTIVE EVIDENCE, BUT INSUFFICIENT OOS SAMPLE
* **Protocol**: INCONCLUSIVE
* **Reason**: 91 stitched OOS trades < 200 required.
