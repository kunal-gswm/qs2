# Final Consistency Audit

## Final Verdict
* **Engineering**: REPRODUCIBLE
* **Historical evidence**: POSITIVE DESCRIPTIVE EVIDENCE, BUT INSUFFICIENT OOS SAMPLE
* **Protocol**: INCONCLUSIVE
* **Reason**: 91 stitched OOS trades < 200 required.

## 1. Resolve the 2× Cost Contradiction
* **Authoritative Result**: `0.842R` (Expectancy) across 92 closed trades.
* **Resolution**: The earlier 0.902R value was a residual artifact from the invalid post-hoc deduction approximation. The `0.842R` value is the authoritative result generated natively by passing the signals through `BacktestEngine.process_day()` using a versioned 2× cost configuration.
* **Exact Multiplier/Config**: 2× applied to `stt_rate`, `exchange_transaction_charge_rate`, `sebi_turnover_fee_rate`, `stamp_duty_rate`, `slippage_rate`, and `dp_charge_per_sell_inr`.
* **Execution Path**: Canonical canonical execution verified. All artifacts updated to reflect 0.842R.

## 2. Verify Random-Control Test
* **Null Hypothesis / Implementation**: Sign-flipping permutation where $R'_i = s_i \times R_i$ ($s_i \in \{-1,+1\}$).
* **Parameters**: Seed = 42, Simulations = 10,000, Statistic = Mean R.
* **Calculation**: One-sided upper-tail p-value correctly includes the observed statistic. The original mean is properly destroyed in the null permutations.
* **Result**: Observed 1.042R yields p-value < 0.0001. (N1/N2 PASS).

## 3. Verify Neighbor Plateau
* **Construction**: Exactly 50 unique fold-neighbor pairings. Evaluated strictly on the respective fold's training data. Exactly one parameter dimension shifted by ±1 grid index. Selected cell excluded.
* **Result**: 46 positive out of 50 total eligible.
* **Plateau Ratio**: 92.0% (PASS).

## 4. Verify Monte Carlo
* **Methodology**: 10,000 simulations, Seed = 42, Sampling *with replacement* of the observed OOS returns.
* **Metrics**: 95th percentile max absolute drawdown (relative to R), terminal loss probability.
* **Result**: 95th pct DD < 35%, Terminal loss prob = 0.0%. (PASS).

## 5. Verify Regime Analysis
* **2021**: 18 trades -> `NOT_EVALUABLE`
* **2022**: 2 trades -> `NOT_EVALUABLE`
* **2023**: 15 trades -> `NOT_EVALUABLE`
* **2024**: 21 trades -> `NOT_EVALUABLE`
* **2025**: 35 trades -> Evaluated (0.904R) -> `PASS`

## 6. Cross-Artifact Consistency
* Scanned repository for contradictions.
* Purged all instances of `0.902` (obsolete 2x proxy).
* Purged all instances of `90.0%` and `96.6%` (obsolete plateau aggregates).
* Synced all artifacts to `0.842` and `92.0%`.
