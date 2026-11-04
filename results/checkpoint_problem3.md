# Checkpoint Problem 3: Appliance Disaggregation

**Execution Date:** November 2026  
**Module:** `src/features.py`, `src/evaluation.py`, `run_problem3.py`  
**Outputs Generated:**
- `results/problem3_metrics.csv` & `results/problem3_metrics.json`
- `results/problem3_loho_generalization.csv`
- `figures/fig6_actual_vs_predicted.png` (Held-out actual vs predicted traces)
- `figures/fig7_failure_analysis.png` (Real test error failure cases)

---

## 1. What Was Done
1. **Physically Derived Feature Engineering:**
   - Guided by Problem 2 cycle durations (median 33–99 minutes, mean $\approx 55$ minutes), a centered 61-minute rolling window was constructed.
   - Compact feature set: instantaneous aggregate power, rolling mean/std/min/max at 15m, 31m, and 61m scales, past lags ($t-30, t-15, t-5$), future leads ($t+5, t+15, t+30$), transient deltas, and cyclical temporal coordinates (`sin_hour`, `cos_hour`, `is_weekend`).
   - Zero-leakage enforcement: only `Aggregate` was used as an input feature. No appliance channel or the `Issues` flag was ever supplied to the model.
2. **Contiguous Chronological Block Splits:**
   - Applied a strict 60% Train / 20% Validation / 20% Test chronological split per household.
   - A **2-hour buffer gap (120 minutes > 61-minute window length)** was excised between splits. This prevents any rolling window sample from overlapping across train, validation, or test partitions.
3. **Baselines Built on Training Data Only:**
   - **Always-Off Baseline:** Predicts $0.0\text{ W}$ unconditionally.
   - **Diurnal Profile Baseline:** Computes the average washing machine consumption for each `(hour_of_day, is_weekend)` combination using the training partition exclusively.
4. **Model Architecture:**
   - `HistGradientBoostingRegressor` (100 iterations, learning rate 0.08, max leaf nodes 31, min samples leaf 20).
   - Fast histogram binning natively captures non-linear step changes (e.g. heating element switching on/off) without requiring arbitrary scaling.
   - Output predictions were strictly non-negative (clipped at $0\text{ W}$).
5. **Cross-Household Generalization (Leave-One-House-Out):**
   - Trained four independent models, each omitting one household, and evaluated zero-shot transferability on the omitted unseen home.

---

## 2. Key Real Numbers

### Benchmark Comparison on Held-Out Test Data (Overall Pooled Test Set, N = 596,671 minutes)

| Model | MAE (W) | RMSE (W) | $R^2$ | ON/OFF Precision | ON/OFF Recall | ON/OFF $F_1$ | Total Energy Error (kWh) | Relative Energy Error (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Always-Off Baseline** | **25.34** | 185.83 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 251.90 | 100.0% |
| **Diurnal Profile Baseline** | 42.23 | 185.03 | 0.0086 | 0.1065 | 0.3204 | 0.1601 | 42.10 | 16.71% |
| **HistGradientBoosting** | **35.09** | **158.01** | **0.2785** | **0.2184** | **0.6466** | **0.3265** | **38.54** | **15.30%** |

### Per-Household Test Metrics (HistGradientBoosting on Held-Out Time Block)

| Household | Metered Model | Test Set MAE (W) | Test Set RMSE (W) | Test Set $R^2$ | Test Set $F_1$ | Total Energy Error (kWh) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **House 1** | Beko WMC6140 | 17.31 W | 96.75 W | **0.4604** | **0.2504** | 9.71 kWh (37.5%) |
| **House 2** | LG F1289TD | 28.51 W | 142.35 W | **0.3710** | **0.2812** | 2.35 kWh (5.5%) |
| **House 3** | Unknown | 43.70 W | 173.74 W | **0.3112** | **0.3413** | 1.92 kWh (2.5%) |
| **House 5** | AEG L99695HWD | 49.10 W | 196.53 W | **0.1167** | **0.3639** | 52.51 kWh (49.4%) |

### Zero-Shot Leave-One-House-Out (LOHO) Generalization Benchmark

| Target Household (Unseen) | Training Houses | LOHO MAE (W) | LOHO $R^2$ | LOHO $F_1$ Score | Energy Error (kWh) | Generalization Loss ($\Delta F_1$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **House 1** | Houses 2, 3, 5 | 22.21 W | 0.1655 | 0.1779 | 14.33 kWh | $-28.9\%$ |
| **House 2** | Houses 1, 3, 5 | 32.73 W | 0.1332 | 0.2306 | 1.20 kWh | $-18.0\%$ |
| **House 3** | Houses 1, 2, 5 | 55.12 W | 0.0251 | 0.2709 | 18.03 kWh | $-20.6\%$ |
| **House 5** | Houses 1, 2, 3 | 49.23 W | 0.0615 | 0.3495 | 53.87 kWh | $-4.0\%$ |

---

## 3. Why MAE and $R^2$ Mislead in NILM (The "Always-Off" Paradox)
Notice that the **Always-Off Baseline achieves a lower MAE (25.34 W) than the trained Machine Learning model (35.09 W)**!
- Because washing machines are idle for 92% to 98% of all minutes, predicting $0\text{ W}$ incurs zero error across 95% of the year.
- When an active cycle occurs, predicting 0 W incurs an error equal to the true load.
- When the ML model attempts to predict a cycle, even minor temporal misalignments (e.g. predicting heating at minute 12 when it actually peaked at minute 14) incur a "double penalty" in MAE (over-predicting at minute 12 and under-predicting at minute 14).
- Therefore, **MAE alone is actively misleading for intermittent appliances**.
- The true value of the model is demonstrated by **event-level Recall (0.6466 vs 0.0000)** and **$F_1$ score (0.3265 vs 0.0000)**, capturing 65% of all active laundering minutes and estimating total household laundering energy to within **15.3% relative error** over hundreds of days.

---

## 4. Empirical Failure Analysis
Examining the actual test error traces (`figures/fig7_failure_analysis.png`):
1. **False Positives (Confounder Confusion):**
   - In House 1, the tumble dryer (Appliance 4, Creda T522VW) draws $\approx 2.0 - 2.5\text{ kW}$ intermittently.
   - When the tumble dryer runs alone without the washing machine, the aggregate signal exhibits a sustained 2 kW step. Because both machines utilize high-power resistive heating elements, the model produces a spurious washing-machine prediction of ~300–600 W.
2. **False Negatives & Peak Compression:**
   - The tree model compresses extreme heating spikes: when the actual heating coil draws 2,400 W for 8 minutes, the model predicts ~800–1,200 W. This magnitude compression occurs because tree leaves average the active state across varying household cycle programs (eco vs 60°C wash).
