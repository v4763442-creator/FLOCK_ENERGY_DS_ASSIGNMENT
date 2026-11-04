# Final Assignment Audit Checklist

**Project:** Flock Energy Take-Home Assignment — REFIT Data Cleaning and Appliance Disaggregation  
**Date:** November 2026  
**Auditor:** Senior Data Scientist & ML Engineering Lead  

---

## 1. Line-by-Line Requirement Audit Table

| # | Assignment Requirement (from PDF & Amendments) | Location Satisfied | Status | Notes / Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **1.1** | **Raw Data Selection & Resampling:** Select House 1 raw data, resample readings to 1-minute intervals. | `src/cleaning.py`, `notebooks/01_raw_cleaning.ipynb` | **Fully Met** | Processed 7,573,360 raw rows into 920,031 continuous 1-minute intervals. |
| **1.2** | **Timestamp Checks & Ordering:** Check timestamp parsing, ordering, duplicates, missing readings, irregular intervals. | `DATA.md` (Sec 3), `results/problem1_summary.json` | **Fully Met** | Quantified 1,016,085 duplicate rows; 4,104,740 BST rows; 121,530 outage minutes. |
| **1.3** | **DST & Timezone Investigation:** Test clock changes for $\pm 1\text{h}$ jumps, duplicates, fake gaps; keep consistent with UTC. | `DATA.md` (Sec 3.2), `results/checkpoint_problem1.md` | **Fully Met** | Identified $-3,597\text{s}$ autumn jump on 2013-10-27; shifted BST by $-3600\text{s}$ to UTC. |
| **1.4** | **Part 1 / Part 2 Overlap Merge:** Compare aggregates in overlap at 0 and $\pm 3600\text{s}$ offset; document merge rule. | `DATA.md` (Sec 2), `README.md` (Sec 3) | **Fully Met** | 0s offset correlation = 0.7887 (MAE 57.8W); enforced clean boundary at `2014-10-01 01:27:07`. |
| **1.5** | **Order of Operations:** Impossible values to NaN FIRST, then de-duplicate, then resample; report exact repeats vs conflicting. | `src/cleaning.py`, `results/problem1_summary.json` | **Fully Met** | NaNs applied first; 914,781 exact repeat groups (90.03%) vs 101,304 conflicting (9.97%). |
| **1.6** | **Spike Threshold Justification:** Data-driven aggregate threshold; IAM capped at 4,000 W based on evidence. | `DATA.md` (Sec 3.1, 4.1), `results/problem1_summary.json` | **Fully Met** | Aggregate capped at 15 kW (171 saturation spikes); IAM capped at 4 kW (3,895 13A socket spikes). |
| **1.7** | **Gap Handling:** Plain vs time-weighted mean justified; short-gap cutoff derived from $\Delta t$ distribution; flag outages. | `src/cleaning.py`, `DATA.md` (Sec 4.1) | **Fully Met** | 99.98% $\Delta t \le 120\text{s}$; gaps $\le 3\text{m}$ interpolated (1,989 mins); outages $> 3\text{m}$ flagged (121,530 mins). |
| **1.8** | **Sanity Check vs Official Clean:** Compare 1-min cleaned House 1 with official cleaned House 1 (MAE/corr). | `results/problem1_official_comparison.json`, `DATA.md` | **Fully Met** | WM MAE = **3.91 W** ($r = 0.8328$); Aggregate MAE = **56.38 W** ($r = 0.8692$). |
| **1.9** | **Problem 1 Figures:** Plot Aggregate + at least 2 appliances before/after cleaning with one-line interpretations. | `figures/fig1_cleaning_trace_zoom.png`, `fig2_outage_handling.png` | **Fully Met** | Generated, embedded in `RESULTS.md`, and captioned with one-line interpretations. |
| **2.1** | **Multi-House Washing Machine EDA:** Analyze $\ge 4$ households at 1-minute resolution; state periods and rationale. | `src/cycles.py`, `notebooks/02_washing_machine_eda.ipynb` | **Fully Met** | Evaluated Houses 1, 2, 3, 5 (~21 months each) plus House 4 independently. |
| **2.2** | **House 4 Independent Evaluation:** Treat WM1 and WM2 separately; explain exclusion from disaggregation. | `RESULTS.md` (Sec 3.2), `results/problem2_eda.json` | **Fully Met** | WM1 (59 cycles), WM2 (207 cycles); excluded because aggregate meters both simultaneously. |
| **2.3** | **Data Availability & Quality:** Date range, missing intervals, zero/off time, forward-fill runs, `Issues = 1` rows. | `results/problem2_eda.json`, `RESULTS.md` (Sec 3.1) | **Fully Met** | Off-state 91.8%–98.0%; Issues 1.5%–7.6%; forward-fill runs quantified per house. |
| **2.4** | **Cycle Rule Derivation & Sensitivity:** Test peak 200–500W, gap 5/10/15m, dur 10–20m; explain rule in plain language. | `src/cycles.py`, `results/problem2_cycle_sensitivity.csv` | **Fully Met** | 27-grid tested; chosen: `on=15W, peak=500W, gap=10m, dur=15m`. Full plain language explanation given. |
| **2.5** | **Channel Label Verification:** Verify House 1 labels (Appliance 4 Creda T522VW tumble dryer vs washer dryer). | `RESULTS.md` (Sec 3.1), `config.py` | **Fully Met** | Verified Creda T522VW is a vented tumble dryer; Appliance 5 is the sole washing machine. |
| **2.6** | **Usage Patterns & Comparison:** Hour of day, day of week normalized; cross-house duration/peak/energy comparison. | `results/problem2_usage_patterns.json`, `RESULTS.md` | **Fully Met** | Normalized diurnal & weekly patterns; 1,987 cycles analyzed across homes. |
| **2.7** | **Problem 2 Figures:** Representative 24-hr trace, detected cycles zoom, cross-house comparison boxplots. | `figures/fig3_rep_24h_trace.png`, `fig4_detected_cycles_zoom.png`, `fig5_cross_house_comparison.png` | **Fully Met** | Generated, saved to `figures/`, embedded and interpreted in `RESULTS.md`. |
| **3.1** | **Model & Target:** Disaggregate washing machine from Aggregate at 1-min resolution; explain homes/periods. | `src/features.py`, `notebooks/03_disaggregation.ipynb` | **Fully Met** | Target: WM power (W); Input: Aggregate features; Houses 1, 2, 3, 5 held-out blocks. |
| **3.2** | **Window Length & Feature Design:** Derived from Problem 2 cycle duration; compact feature set; no leakages. | `src/features.py`, `README.md` (Sec 3) | **Fully Met** | 11 compact rolling aggregate features (agg, 1m delta, rolling mean/std/max over 15, 60, 120 min) derived from 33–99 min wash duration. |
| **3.3** | **Baselines:** Always-off baseline (mandatory) + Diurnal usage profile baseline fit on training only. | `src/evaluation.py`, `results/problem3_metrics.csv` | **Fully Met** | Always-off (MAE 25.16W, F1 0.0); Hour-of-Day (MAE 42.15W, F1 0.1457); HGB (MAE 35.34W, R2 0.2662, F1 0.3287, Rel Energy Error 12.67%). |
| **3.4** | **Model Choice:** Fast tree model on CPU (HistGradientBoostingRegressor); no arbitrary scaling. | `src/features.py`, `notebooks/03_disaggregation.ipynb` | **Fully Met** | HistGradientBoosting trained in seconds on CPU without GPU overhead or scaling. |
| **3.5** | **Leakage-Free Split:** Chronological blocks (60/20/20) with buffer gap $\ge$ window length; explain in plain language. | `src/features.py`, `README.md` (Sec 3) | **Fully Met** | 3-hour (180 min) excised buffer gap between train/val/test; zero window spillover. |
| **3.6** | **Metrics:** MAE, RMSE, R2, minute-level ON/OFF Precision/Recall/F1, Total Energy Error (kWh) & % error. | `results/problem3_metrics.csv`, `RESULTS.md` | **Fully Met** | All continuous, classification, and energy metrics reported across all homes and overall pooled set. |
| **3.7** | **Visualizations:** Clear actual vs predicted plot on test data; failure analysis of real test errors. | `figures/fig6_actual_vs_predicted.png`, `fig7_failure_analysis.png` | **Fully Met** | Generated, saved to `figures/`, embedded and interpreted in `RESULTS.md`. |
| **3.8** | **Leave-One-House-Out (LOHO):** Secondary zero-shot cross-household generalization benchmark. | `results/problem3_loho_generalization.csv` | **Fully Met** | Trained 4 independent leave-one-out models; quantified 18–29% generalization loss. |
| **4.1** | **Energy-Saving Opportunity:** Realistic DSM opportunity and measurement methodology (A/B testing, DiD). | `Recommendation.md` (Sec 2) | **Fully Met** | Morning peak shifting (08:00–11:00) and eco-wash nudges; RCT DiD econometric regression plan. |
| **4.2** | **Limitations:** Resistive load overlaps, telemetry gaps, household differences, UK-to-India transferability. | `Recommendation.md` (Sec 3) | **Fully Met** | Detailed analysis of cold-water top-load washers, voltage sags, inverters, and climate in India. |
| **4.3** | **15/30-Minute Degradation:** Clear explanation of signal dilution, loss of transient edges, and accuracy drop. | `Recommendation.md` (Sec 4) | **Fully Met** | Mathematical proof of 83% peak power dilution and collapse of edge detection. |
| **4.4** | **Statement Labeling:** Explicitly label supported by results vs reasoned engineering judgement. | `Recommendation.md` (Sec 5) | **Fully Met** | Complete classification matrix provided in Section 5 of `Recommendation.md`. |
| **5.1** | **Five Deliverables:** Source code, README.md, DATA.md, RESULTS.md, Recommendation.md. | Root directory of repository | **Fully Met** | All 5 deliverables written, validated, and numerically cross-referenced. |
| **5.2** | **End-to-End Notebook Execution:** Headless execution with no errors. | `notebooks/01_raw_cleaning.ipynb` ... `03_disaggregation.ipynb` | **Fully Met** | All 3 notebooks executed top-to-bottom via `nbconvert --execute` with 0 errors. |
| **5.3** | **Data Isolation & Reproducibility:** Data outside repo; git-ignored; configurable path via `REFIT_DATA_DIR`. | `.gitignore`, `config.py` | **Fully Met** | No data or `.7z` tracked; paths relative to parent with env override. |

---

## 2. Unmet or Partial Requirements

**None.** Every requirement from the assignment specification and the user's fifteen amendments has been fully implemented, executed on real data, verified, and documented.
