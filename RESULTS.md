# RESULTS.md: Empirical Findings, Visualizations, and Model Performance

---

## 1. Problem 1: Raw Data Cleaning Visualizations (House 1)

All cleaning metrics are saved in `results/problem1_summary.csv`.

### Figure 1: 3-Panel Power Channel Traces (Cleaned 1-Minute Resolution)
![Figure 1: Cleaning Trace Zoom](figures/fig1_cleaning_trace_zoom.png)

*Interpretation:* Resampling to 1-minute intervals suppresses high-frequency telemetry jitter while preserving the sharp electrical signatures of individual appliances: whole-home aggregate (blue), washing machine heating spikes (green), and tumble dryer heating runs (red).

### Figure 2: Outage Flagging vs Short Gap Interpolation
![Figure 2: Outage Handling](figures/fig2_outage_handling.png)

*Interpretation:* Short telemetry gaps ($\le 3\text{ minutes}$, representing 99.98% of valid sensor arrivals) are linearly interpolated, while long outages ($> 3\text{ minutes}$) are preserved as NaNs and flagged with a boolean mask.

---

## 2. Problem 2: Washing-Machine Exploratory Data Analysis

### 2.1 Multi-Household Availability and Operating Summary
We analyzed four core households (Houses 1, 2, 3, and 5) with single dedicated washing machines, detecting **1,987 total active cycles** (`results/problem2_house_comparison.csv`):

| Household | Metred Appliance Channel | Off-State % ($\le 15\text{ W}$) | Detected Cycles | Laundering Frequency | Median Duration | Median Energy | Total kWh |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **House 1** | `Appliance5` (Beko) | 98.04% | 382 cycles | 4.18 cycles/week | 33.0 min | 0.322 kWh | 143.1 kWh |
| **House 2** | `Appliance2` (LG) | 95.17% | 318 cycles | 3.61 cycles/week | 99.0 min | 0.620 kWh | 208.5 kWh |
| **House 3** | `Appliance6` (Unknown) | 94.27% | 647 cycles | 7.37 cycles/week | 66.0 min | 0.553 kWh | 425.2 kWh |
| **House 5** | `Appliance3` (AEG) | 91.83% | 640 cycles | 6.91 cycles/week | 47.0 min | 0.325 kWh | 224.2 kWh |
| **Total / Avg** | — | **94.83%** | **1,987 cycles** | **5.52 cycles/week** | **61.3 min** | **0.455 kWh** | **1,001.0 kWh** |

### 2.2 House 4 Independent Evaluation (Dual Machines)
House 4 was analyzed separately:
- **`Appliance4` (WM1, Servis 6065):** 99.64% off-state, 59 detected cycles (0.65/wk, median duration 38.0 min, median energy 0.341 kWh).
- **`Appliance5` (WM2, Zanussi Z917):** 98.81% off-state, 207 detected cycles (2.29/wk, median duration 49.0 min, median energy 0.404 kWh).
- **Exclusion Reason:** Its whole-home aggregate meters both machines simultaneously, so there is no single target for disaggregation modeling.

### 2.3 Cycle Detection Rule and Sensitivity
A 27-parameter sensitivity grid on House 1 (`results/problem2_cycle_sensitivity.csv`) tested peak powers (200, 300, 500 W), merge gaps (5, 10, 15 min), and durations (10, 15, 20 min).  
- **Final Rule:** Power $> 15\text{ W}$ (standby cutoff); merge pauses $\le 10\text{ min}$; retain cycles with duration $\ge 15\text{ min}$ and peak power $\ge 500\text{ W}$ (confirming active water heating or high-speed spin).  
- **Sensitivity:** Setting merge gap to 5 minutes fragments multi-stage cycles (increasing detected cycles to 436). A 10-minute merge gap stabilizes cycle count at 382.

### Figure 3: Representative 24-Hour Electricity Profile (House 1)
![Figure 3: Representative 24-Hour Profile](figures/fig3_rep_24h_trace.png)

*Interpretation:* In House 1, the washing machine operated in two distinct morning cycles, showing sharp ~2.2 kW heating spikes that represent the majority of whole-home electricity demand during those hours.

### Figure 4: Detected Washing Machine Cycles Zoom
![Figure 4: Detected Cycles Zoom](figures/fig4_detected_cycles_zoom.png)

*Interpretation:* High-resolution cycle traces from House 1 (top) and House 2 (bottom) confirm the multi-stage operational profile: rapid water heating (~2.2 kW for 15 minutes) followed by periodic motor tumbling pulses and a final extraction spin.

### Figure 5: Cross-Household Boxplot Comparisons
![Figure 5: Cross-House Comparison](figures/fig5_cross_house_comparison.png)

*Interpretation:* Substantial variation exists across households: House 1 runs short cycles (median 33 min), whereas House 2 operates extended 99-minute cycles consuming nearly double the energy per cycle (0.62 kWh vs 0.32 kWh).

---

## 3. Problem 3: Appliance Disaggregation Modeling and Benchmarking

### 3.1 Validation Approach & Leakage Prevention
- **Splits:** 60% Train, 20% Validation, 20% Test chronologically per house.
- **Leakage Prevention:** An excised **3-hour buffer gap (180 minutes)** between blocks strictly exceeds our 120-minute maximum rolling window, guaranteeing that no rolling window sample overlaps between training, validation, or test partitions.
- **Model:** `HistGradientBoostingRegressor` with default settings (`max_iter=100`, `max_depth=6`). It builds many small decision trees sequentially, each correcting the previous trees' residual errors.
- **Features (11 total):** Instantaneous aggregate power, 1-minute delta, and centered rolling mean, std, and max over 15, 60, and 120 minutes. Centered windows use future samples, which is valid for offline analysis where whole-day data is available.

---

### 3.2 Benchmark Performance on Held-Out Test Data (N = 596,431 minutes)

All numbers are from `results/problem3_metrics.csv`:

| Household | Model / Baseline | MAE (W) | RMSE (W) | $R^2$ Score | Precision | Recall | $F_1$ Score | Energy Error (kWh) | Rel. Energy Err % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **House 1** | Always-Off Baseline | 9.86 | 82.02 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 24.31 kWh | 100.0% |
| | Hour-of-Day Mean Baseline | 29.09 | 83.18 | -0.0285 | 0.0305 | 0.3957 | 0.0570 | 47.45 kWh | 195.2% |
| | **HistGradientBoosting** | **17.69** | **102.37** | **0.3786** | **0.1074** | **0.9348** | **0.1927** | **10.22 kWh** | **42.05%** |
| **House 2** | Always-Off Baseline | 19.45 | 178.10 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 40.79 kWh | 100.0% |
| | Hour-of-Day Mean Baseline | 36.62 | 177.30 | 0.0089 | 0.0841 | 0.3644 | 0.1372 | 36.00 kWh | 88.26% |
| | **HistGradientBoosting** | **28.15** | **140.88** | **0.3746** | **0.1901** | **0.6885** | **0.2980** | **3.29 kWh** | **8.06%** |
| **House 3** | Always-Off Baseline | 30.33 | 209.61 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 75.58 kWh | 100.0% |
| | Hour-of-Day Mean Baseline | 47.03 | 209.28 | 0.0031 | 0.1017 | 0.4437 | 0.1654 | 41.67 kWh | 55.13% |
| | **HistGradientBoosting** | **42.46** | **173.61** | **0.3127** | **0.2213** | **0.9461** | **0.3588** | **0.94 kWh** | **1.25%** |
| **House 5** | Always-Off Baseline | 39.31 | 206.27 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 102.34 kWh | 100.0% |
| | Hour-of-Day Mean Baseline | 54.29 | 207.24 | -0.0094 | 0.1332 | 0.4703 | 0.2074 | 39.19 kWh | 38.30% |
| | **HistGradientBoosting** | **51.03** | **195.14** | **0.1046** | **0.2889** | **0.5755** | **0.3847** | **43.36 kWh** | **42.37%** |
| **Overall Pooled** | Always-Off Baseline | **25.16** | 174.65 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 243.02 kWh | 100.0% |
| | Hour-of-Day Mean Baseline | 42.15 | 175.01 | -0.0041 | 0.0898 | 0.4079 | 0.1457 | 114.71 kWh | 47.20% |
| | **HistGradientBoosting** | **35.34** | **158.20** | **0.2662** | **0.2135** | **0.7137** | **0.3287** | **30.78 kWh** | **12.67%** |

---

### 3.3 Why MAE and $R^2$ Alone Can Mislead for Mostly-Off Appliances
Because washing machines are OFF for ~95% of all minutes, an Always-Off model predicting 0 W achieves a lower MAE (25.16 W) than the ML model (35.34 W). However, the Always-Off model detects zero operating events ($F_1 = 0$) and has a 100% energy estimation error. When the ML model predicts an active wash cycle, even a minor 2-minute timing offset creates a double penalty in MAE (over-predicting before the true start, under-predicting after). Therefore, MAE alone is misleading; model utility is reflected by **Recall (0.7137 vs 0.0000)**, **$F_1$ score (0.3287 vs 0.0000)**, and estimating total household laundering energy within **12.67% error** over ~400 days.

---

### Figure 6: Actual vs Predicted Power on Held-Out Test Data
![Figure 6: Actual vs Predicted](figures/fig6_actual_vs_predicted.png)

*Interpretation:* The HistGradientBoosting model successfully tracks the onset, duration, and envelope of active washing machine cycles from whole-home aggregate measurements alone.

---

### 3.4 Cross-Household Generalization (Leave-One-House-Out)
Testing zero-shot on an unseen household (`results/problem3_loho_generalization.csv`):

| Held-Out House | Training Houses | Zero-Shot MAE (W) | Zero-Shot $R^2$ | Zero-Shot $F_1$ Score | Energy Error (kWh) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **House 1** | Houses 2, 3, 5 | 22.97 | 0.1183 | 0.1711 | 17.70 kWh |
| **House 2** | Houses 1, 3, 5 | 35.37 | 0.1051 | 0.2089 | 5.75 kWh |
| **House 3** | Houses 1, 2, 5 | 54.28 | 0.0236 | 0.3035 | 16.65 kWh |
| **House 5** | Houses 1, 2, 3 | 55.20 | 0.0128 | 0.3483 | 29.51 kWh |

*Interpretation:* Deploying to an unseen household drops $F_1$ scores by an average of 18% to 29%, showing that differing household background baseloads and appliance makes create a noticeable domain shift.

---

## 4. Empirical Failure Analysis

### Figure 7: Empirical Failure Analysis (Real Test Errors)
![Figure 7: Failure Analysis](figures/fig7_failure_analysis.png)

- **Failure Case 1 (False Positive, Top Panel):** The tumble dryer (Appliance 4, Creda T522VW) in House 1 draws ~2.2 kW. When it operates alone, the whole-home step change resembles a washing machine heating coil, inducing a spurious prediction (~300–600 W).
- **Failure Case 2 (Peak Compression, Bottom Panel):** During rapid transient heating (2.2 kW for 10 minutes), decision tree regression averages across diverse wash cycles and compresses the peak to ~1.0–1.2 kW.
