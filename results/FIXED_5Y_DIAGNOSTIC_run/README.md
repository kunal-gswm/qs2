# FIXED 5-YEAR DIAGNOSTIC: BVEQSE v1.0

## 1. Experiment Definition
This is a `FIXED_5Y_DIAGNOSTIC` experiment. It executes the frozen BVEQSE v1.0 forward configuration continuously over the 2021-01-01 to 2025-12-31 period using a single, static parameter set. 
**Objective**: To diagnose theoretical trade frequency and baseline performance characteristics of the frozen parameter set across a continuous 5-year block.

> **CRITICAL PROTOCOL STATEMENT**: This is NOT a replacement for the expanding-window walk-forward experiment. It does not alter the official BVEQSE protocol status, which remains strictly `INCONCLUSIVE` (due to the 91 stitched OOS trades vs. 200 required). 

## 2. Exact Frozen Configuration
* `rho` (Range Threshold) = 0.075
* `L` (Consolidation Lookback) = 15
* `mu_v` (Volume Multiple) = 2.0
* `k` (Stop ATR Multiple) = 1.25
* `m` (Target R Multiple) = 3.0
* Initial Capital: ₹20,000
* `f` (Fractional Risk) = 0.5% (0.005)

## 3. Data & Universe
* **Source**: Frozen historical dataset (2017-01-01 to 2025-12-31).
* **Universe**: The exact same 44 resolved symbols of the configured 45-symbol partial NIFTY 100 universe. `TATAMOTORS.NS` correctly remains unresolved.
* Data quality, missing bar logic, and corporate-action adjustments identically match the canonical research environment.

## 4. Overall Results (1× Costs)
| Metric | Value |
| :--- | :--- |
| Completed Trades | 165 |
| Win Rate | 59.39% |
| Mean Expectancy (R) | 1.042R |
| Median R | 2.648R |
| Profit Factor | 2.98 |
| Total Gross P&L | ₹24,681.47 |
| Total Costs | ₹4,749.58 |
| Total Net P&L | ₹19,931.89 |
| CAGR | 14.85% |
| Max Drawdown | 6.03% |

## 5. Annual Results
| Year | Trades | Win Rate | Mean R | Profit Factor | Net P&L (₹) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 2021 | 24 | 75.00% | +1.689R | 6.91 | +3,921.27 |
| 2022 | 25 | 36.00% | -0.103R | 1.41 | +772.11 |
| 2023 | 61 | 67.21% | +1.357R | 3.96 | +8,345.37 |
| 2024 | 21 | 61.90% | +1.192R | 3.71 | +3,625.46 |
| 2025 | 34 | 50.00% | +0.770R | 1.98 | +3,267.67 |

## 6. Cost Sensitivity
* **1× Frozen Costs**: 1.042R across 165 trades.
* **2× Frozen Costs**: 0.602R across 159 trades.
*(Evaluated via canonical `BacktestEngine` path. The doubled entry friction causes slightly fewer signals to clear the cash constraints, and heavily throttles the expectancy, but remains strongly positive).*

## 7. Monte Carlo
* **Simulations**: 10,000 (Seed = 42)
* **Method**: Trade sequence sampling with replacement.
* **95th Percentile Max Drawdown**: 14.71 R (Relative to Risk Units)
* **Terminal Loss Probability**: 0.0%

## 8. Concentration
* **Largest single-symbol contribution**: 8.45% of total P&L
* **Top-5 trade contribution**: 12.60% of total P&L
* **Largest single trade**: 2.65% of total P&L

## 9. Comparison With Walk-Forward OOS
| Metric | Fixed 5Y | Existing WF OOS |
| :--- | ---: | ---: |
| Trades | 165 | 91 |
| Mean R | 1.042 | 1.042 |
| PF | 2.98 | 3.40 |
| Win Rate | 59.39% | 60.44% |
| 2× Cost R | 0.602 | 0.842 |
| Symbol concentration | 8.45% | 8.5% |
| Top-5 contribution | 12.60% | 17.0% |

**Interpretation**: 
The Fixed 5Y diagnostic (using the final/tight parameters) generates nearly double the trade frequency (165) over the same chronological window compared to the expanding-window WF (91). This reveals that the walk-forward selection dynamically selected much more restrictive parameters during the earlier chronological folds (2021-2023), severely throttling OOS frequency during those years. Interestingly, the mean expectancy (1.042R) is virtually identical across both methods, suggesting the signal edge is robust, but the WF engine was actively sacrificing trade frequency in an attempt to maximize unobservable metrics during early training folds. 

## 10. Limitations
* **Fixed Parameter Bias**: This diagnostic evaluates a single static parameter set selected using information up to 2025. It inherently suffers from selection bias if used to assert historical performance.
* **Universe**: Uses a configured partial universe with known limitations.

## 11. Reproducibility
* **Experiment**: `FIXED_5Y_DIAGNOSTIC`
* **Run ID**: `62ca2c78-c065-43a1-8159-d30f23e291fc`
* **Config Hash**: `8710891f0eca870be867818a55f434eec06710e4a4337c4b1defe3ae06a5f7b2`
* **Universe Hash**: `bc9570f860cae301a1fdb272abb019be7afe160b6f4034e0fc88188ef34bb951`
* **Seed**: 42

## 12. Official Protocol Status
This experiment is exclusively an additional analytical diagnostic. It strictly **does not modify** the official BVEQSE v1.0 status. Because the formal walk-forward protocol dictates a requirement of ≥200 strictly isolated OOS stitched trades (where it yielded 91), the strategy remains:
**`INCONCLUSIVE`**
