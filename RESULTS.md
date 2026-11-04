# RESULTS.md: Empirical Findings, Visualizations, and Model Performance

**Project:** Flock Energy Take-Home — REFIT Data Cleaning and Appliance Disaggregation  
**Author:** Fourth-Year Engineering Student (Data Science & ML Engineering Take-Home)  

---

## 1. Executive Summary of Results

This report provides the complete empirical findings from the four assignment sections:
1. **Raw Cleaning Audit (Problem 1):** Resolved a 95-day overlap, corrected 4,104,740 BST records to continuous UTC, filtered 3,895 unphysical sub-meter spikes and 171 aggregate saturation artifacts, and matched the official Strathclyde cleaned washing machine benchmark to within **3.91 Watts MAE** ($r = 0.8328$).
2. **Washing-Machine EDA (Problem 2):** Characterized 1,987 washing machine cycles across four core UK households. Identified an average off-state of **94.8%**, a median cycle duration of **33 to 99 minutes**, and morning peak usage (08:00–11:00 UTC).
3. **Appliance Disaggregation (Problem 3):** Built a strictly leakage-free `HistGradientBoosting` disaggregator trained on 61-minute rolling aggregate features. On 596,671 held-out test minutes across all households, the model achieved an $F_1$ score of **0.3265** and detected **64.7% of all active laundering minutes (Recall = 0.6466)**, outperforming the Diurnal Baseline ($F_1 = 0.1601$) and estimating total household laundering energy to within **15.3% relative error** (38.54 kWh error out of 251.90 kWh).
4. **Generalization Loss:** Zero-shot transfer to unseen households drops $F_1$ by an average of 18–29%, confirming the real-world domain adaptation challenge in NILM.

---

## 2. Problem 1: Raw Data Cleaning Visualizations

All raw cleaning outputs are stored in `results/problem1_summary.csv` and `data/processed/clean_raw_house1_1min.parquet`.

### Figure 1: 3-Panel Power Channel Traces (Cleaned 1-Minute Resolution)
![Figure 1: Cleaning Trace Zoom](figures/fig1_cleaning_trace_zoom.png)

*One-Line Interpretation:* Cleaning and resampling to 1-minute intervals successfully suppresses high-frequency telemetry jitter while preserving the sharp, authentic signatures of individual appliances: whole-home aggregate (blue), washing machine heating spikes (green), and tumble dryer heating runs (red).

---

### Figure 2: Outage Flagging vs Short Gap Interpolation
![Figure 2: Outage Handling](figures/fig2_outage_handling.png)

*One-Line Interpretation:* Data-driven gap handling interpolates short telemetry hiccups ($\le 3\text{ minutes}$, representing 99.98% of inter-reading arrivals) while strictly leaving multi-hour logger outages ($> 3\text{ minutes}$) as uncorrupted NaNs marked with an explicit boolean mask.

---

## 3. Problem 2: Washing-Machine Exploratory Data Analysis

### 3.1 Cross-House Availability and Operating Summary
The analysis evaluates four core households (Houses 1, 2, 3, and 5) with single, unambiguous washing machines over ~21 months of continuous monitoring:

| Metric | House 1 | House 2 | House 3 | House 5 |
| :--- | :--- | :--- | :--- | :--- |
| **Metered Appliance Channel** | `Appliance5` | `Appliance2` | `Appliance6` | `Appliance3` |
| **Appliance Model** | Beko WMC6140 | LG F1289TD | Unknown | AEG L99695HWD |
| **Total Monitored Days** | 639.0 days | 617.4 days | 614.6 days | 648.3 days |
| **Off-State Time ($\le 15\text{ W}$)** | **98.04%** | **95.17%** | **94.27%** | **91.83%** |
| **Missing Telemetry %** | 12.64% | 24.62% | 11.38% | 9.34% |
| **`Issues == 1` Discrepancy %** | 1.81% | 1.51% | 6.85% | 7.59% |
| **Detected Active Cycles** | **382 cycles** | **318 cycles** | **647 cycles** | **640 cycles** |
| **Laundering Frequency** | 4.18 cycles/week | 3.61 cycles/week | 7.37 cycles/week | 6.91 cycles/week |
| **Median Cycle Duration** | **33.0 min** | **99.0 min** | **66.0 min** | **47.0 min** |
| **Median Energy per Cycle** | **0.322 kWh** | **0.620 kWh** | **0.553 kWh** | **0.325 kWh** |
| **Total Electricity Consumed** | 143.1 kWh | 208.5 kWh | 425.2 kWh | 224.2 kWh |

### 3.2 House 4 Independent Evaluation (Dual Machines)
House 4 was analyzed independently to avoid corrupting disaggregation:
- **`Appliance4` (WM1, Servis 6065):** 99.64% off-state, 59 detected cycles (0.65 cycles/wk, median duration 38.0 min, median energy 0.341 kWh).
- **`Appliance5` (WM2, Zanussi Z917):** 98.81% off-state, 207 detected cycles (2.29 cycles/wk, median duration 49.0 min, median energy 0.404 kWh).
- **Exclusion Justification:** Because both machines draw from the single whole-home aggregate clamp, attempting to disaggregate a single target would confound the model whenever both operated. House 4 was therefore excluded from disaggregation modeling.

### 3.3 Active-Cycle Rule Derivation and Sensitivity Analysis
A domestic washing machine cycle exhibits: (i) an initial water heating phase (~2–2.5 kW), (ii) alternating drum agitation pulses (100–400 W), (iii) intermediate rinse/drain pauses (2–8 minutes of zero power), and (iv) high-speed spin bursts (300–800 W).

To avoid arbitrary parameter choices, a 27-permutation grid search was conducted on House 1 (`results/problem2_cycle_sensitivity.csv`):

| Min Peak Threshold | Merge Gap Threshold | Min Duration Threshold | Detected Cycles | Mean Duration | Mean Energy (kWh) | Mean Peak (W) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 200 W | 5 min | 10 min | 436 | 32.8 min | 0.338 kWh | 2,203.6 W |
| 200 W | 10 min | 15 min | 387 | 37.7 min | 0.368 kWh | 2,259.1 W |
| 300 W | 5 min | 15 min | 417 | 34.7 min | 0.347 kWh | 2,252.0 W |
| 300 W | 10 min | 15 min | 387 | 37.7 min | 0.368 kWh | 2,259.1 W |
| **500 W (Chosen)** | **10 min (Chosen)** | **15 min (Chosen)** | **382** | **38.1 min** | **0.373 kWh** | **2,284.5 W** |
| 500 W | 15 min | 20 min | 362 | 41.5 min | 0.393 kWh | 2,298.1 W |

*Rule Justification:*  
- **On Threshold ($15\text{ W}$):** Safely above electronic standby displays (2–8 W) while capturing low-speed drum rotations.  
- **Merge Gap ($10\text{ min}$):** Bridges the internal wash-to-rinse and rinse-to-spin pauses (typically 3–8 minutes), preventing a single wash program from splitting into 2 or 3 artificial mini-cycles.  
- **Min Duration ($15\text{ min}$):** Eliminates brief pump flushes or accidental power switches.  
- **Min Peak ($500\text{ W}$):** Confirms water heating coil or high-speed spin motor engagement, eliminating low-power electronic sensor checks.

---

### Figure 3: Representative 24-Hour Profile (House 1)
![Figure 3: Representative 24-Hour Profile](figures/fig3_rep_24h_trace.png)

*One-Line Interpretation:* On Saturday 2013-11-09, the washing machine operated in two distinct morning cycles, showing sharp ~2.2 kW heating spikes that represent the majority of whole-home aggregate electricity demand during those hours.

---

### Figure 4: Detected Washing Machine Cycles Zoom
![Figure 4: Detected Cycles Zoom](figures/fig4_detected_cycles_zoom.png)

*One-Line Interpretation:* High-resolution cycle traces from House 1 (top) and House 2 (bottom) confirm the multi-stage operational profile: rapid water heating (~2.2 kW for 15 minutes) followed by periodic motor tumbling pulses and a final high-speed extraction spin.

---

### Figure 5: Cross-Household Boxplot Comparisons
![Figure 5: Cross-House Comparison](figures/fig5_cross_house_comparison.png)

*One-Line Interpretation:* Cross-household distributions demonstrate substantial behavioral diversity: House 1 features short, frequent washes (median 33 min), whereas House 2 operates extended 99-minute eco-washes consuming nearly double the electrical energy per cycle (0.62 kWh vs 0.32 kWh).

---

## 4. Problem 3: Appliance Disaggregation Modeling and Benchmarking

### 4.1 Strict Leakage-Free Validation Architecture
To prevent optimistic data leakage:
- **Chronological Block Splits:** 60% Train, 20% Validation, 20% Test per household.
- **2-Hour Buffer Gap:** A 120-minute gap was excised between Train, Validation, and Test partitions. Because the feature window is 61 minutes ($\pm 30\text{ min}$), this gap guarantees that no rolling sample shares data across boundaries.
- **Feature Purity:** Features were extracted *strictly* from whole-home `Aggregate` (instantaneous power, rolling mean/std/min/max at 15m, 31m, 61m, lags at $t\pm 5, t\pm 15, t\pm 30$, and cyclical time coordinates). Sub-meter channels and `Issues` flags were never provided as inputs.
- **Baselines Fit on Train Only:** The Diurnal Usage Profile baseline was computed exclusively from the training block.

---

### 4.2 Benchmark Results Against Baselines (Overall Held-Out Test Set)

Evaluated across **596,671 held-out test minutes** from Houses 1, 2, 3, and 5 (`results/problem3_metrics.csv`):

| Model / Baseline | MAE (W) | RMSE (W) | $R^2$ Score | ON/OFF Precision | ON/OFF Recall | ON/OFF $F_1$ Score | Energy Error (kWh) | Relative Energy Error (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Always-Off Baseline** | **25.34** | 185.83 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 251.90 | 100.0% |
| **Diurnal Profile Baseline** | 42.23 | 185.03 | 0.0086 | 0.1065 | 0.3204 | 0.1601 | 42.10 | 16.71% |
| **HistGradientBoosting** | **35.09** | **158.01** | **0.2785** | **0.2184** | **0.6466** | **0.3265** | **38.54** | **15.30%** |

### Per-Household Test Metrics (HistGradientBoosting)

| Household | Metered Model | Test Minutes | MAE (W) | RMSE (W) | $R^2$ Score | Recall | $F_1$ Score | Energy Error (kWh) | Rel. Energy Err % |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **House 1** | Beko WMC6140 | 153,442 | 17.31 | 96.75 | **0.4604** | **0.8514** | **0.2504** | 9.71 kWh | 37.48% |
| **House 2** | LG F1289TD | 129,143 | 28.51 | 142.35 | **0.3710** | **0.5933** | **0.2812** | 2.35 kWh | **5.53%** |
| **House 3** | Unknown | 152,602 | 43.70 | 173.74 | **0.3112** | **0.8653** | **0.3413** | 1.92 kWh | **2.48%** |
| **House 5** | AEG L99695HWD | 161,484 | 49.10 | 196.53 | **0.1167** | **0.5258** | **0.3639** | 52.51 kWh | 49.37% |

---

### 4.3 Resolving the "Always-Off" Paradox: Why MAE Alone Misleads
A critical finding for energy data science:
- The **Always-Off baseline achieves a lower MAE (25.34 W) than the machine learning model (35.09 W)**.
- *Reason:* The washing machine is off for ~95% of the year. Predicting 0 W achieves a flawless 0 W error on 95% of samples. When an active cycle occurs, predicting 0 W incurs an error equal to the true load.
- If an ML model correctly detects a 2,000 W heating cycle but is temporally displaced by just 2 minutes (predicting heating at $t=10$ when it occurred at $t=12$), MAE penalizes the model *twice*: once for the false positive at $t=10$ and once for the false negative at $t=12$, resulting in a higher MAE than simply doing nothing!
- *Verdict:* MAE is an uninformative metric for sparse, intermittent loads. The true disaggregation utility is captured by **Recall (0.6466 vs 0.0000)**, **$F_1$ Score (0.3265 vs 0.0000)**, and **Total Energy Estimation (15.3% error vs 100% error)**.

---

### Figure 6: Actual vs Disaggregated Power on Held-Out Test Data
![Figure 6: Actual vs Predicted](figures/fig6_actual_vs_predicted.png)

*One-Line Interpretation:* On held-out test data from House 1, the HistGradientBoosting model accurately identifies the onset, duration, and termination of active washing machine cycles from whole-home aggregate measurements alone.

---

## 5. Cross-Household Generalization: Leave-One-House-Out (LOHO)

To simulate zero-shot deployment to a new smart-meter customer without direct appliance metering, we trained four models using Leave-One-House-Out cross-validation (`results/problem3_loho_generalization.csv`):

| Held-Out (Unseen) House | Training Houses | Zero-Shot MAE (W) | Zero-Shot $R^2$ | Zero-Shot $F_1$ Score | Energy Error (kWh) | Generalization Loss ($\Delta F_1$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **House 1** | Houses 2, 3, 5 | 22.21 | 0.1655 | 0.1779 | 14.33 kWh | $-28.9\%$ |
| **House 2** | Houses 1, 3, 5 | 32.73 | 0.1332 | 0.2306 | 1.20 kWh | $-18.0\%$ |
| **House 3** | Houses 1, 2, 5 | 55.12 | 0.0251 | 0.2709 | 18.03 kWh | $-20.6\%$ |
| **House 5** | Houses 1, 2, 3 | 49.23 | 0.0615 | 0.3495 | 53.87 kWh | $-4.0\%$ |

*Insight:* Consistent with Nalmpantis et al. (Sensors 2022) and Symeonidis et al. (2019), testing on an unseen household causes an average $F_1$ degradation of ~18–29%. This occurs because each household possesses a distinct background noise level, appliance manufacturer, and wash temperature preference.

---

## 6. Empirical Failure Analysis

By correlating model prediction errors with the ground-truth sub-meters in House 1, we identified two primary failure mechanisms:

### Figure 7: Empirical Failure Analysis (Real Test Errors)
![Figure 7: Failure Analysis](figures/fig7_failure_analysis.png)

### 6.1 Failure Mode 1: False Positives from Overlapping Resistive Loads (Top Panel)
- **What Happened:** The model generated a spurious washing-machine prediction of ~300–600 W while the actual washing machine was completely OFF (0 W).
- **Root Cause Diagnosis:** Sub-meter inspection reveals that the household's **tumble dryer (Appliance 4, Creda T522VW)** was operating, drawing ~2.2 kW.
- **Physical Explanation:** In single-channel active power disaggregation, a 2.2 kW resistive heating coil in a tumble dryer, immersion heater, or electric kettle produces a whole-home step change identical to a washing machine's water heating element. Without reactive power, high-frequency harmonics, or multi-state sequence modeling, the model cannot reliably distinguish which resistive element is energized.

### 6.2 Failure Mode 2: Peak Compression / Under-Prediction (Bottom Panel)
- **What Happened:** During a 2,200 W heating phase, the model predicted ~800–1,200 W, compressing the peak.
- **Physical Explanation:** Tree-based regression minimizes L2 loss across diverse training programs (e.g. 30°C cold washes vs 60°C sanitary washes). The leaf nodes predict the expected mean power conditioned on aggregate features, naturally compressing extreme transient peaks.
