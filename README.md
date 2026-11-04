# REFIT Data Cleaning and Appliance Disaggregation (refit-nilm)

A production-grade, reproducible, and explainable Data Science take-home project for **Flock Energy**, developed by a fourth-year engineering student.

This repository implements an end-to-end Non-Intrusive Load Monitoring (NILM) pipeline for **Washing Machine disaggregation** using the Strathclyde REFIT electrical load dataset:
1. **Raw Sensor Cleaning (House 1):** Resolves multi-part boundary overlaps, fixes naive UK Daylight Savings Time jumps, de-duplicates sensor re-transmissions, applies physical spike caps, and resamples to 1-minute intervals.
2. **Multi-House Washing Machine EDA:** Characterizes consumption across four core households (Houses 1, 2, 3, and 5) plus House 4, derives an empirical cycle detection rule via sensitivity analysis, and maps diurnal/weekly laundering habits.
3. **Appliance Disaggregation Modeling:** Implements a leakage-free `HistGradientBoostingRegressor` using compact rolling aggregate features (61-minute centered window) against mandatory **Always-Off** and **Diurnal Profile** baselines, complete with Leave-One-House-Out cross-household generalization and failure analysis.
4. **Utility Recommendations:** Outlines DSM demand-shifting strategies, an RCT Difference-in-Differences evaluation framework, and critical limitations of transferring UK models to India or 30-minute smart-meter data.

---

## 1. Quickstart & Local Setup (Windows PowerShell / cmd)

The codebase is written in pure Python 3.10+ using standard scientific libraries (`numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`, `seaborn`, `jupyterlab`). No deep learning frameworks, Docker containers, or platform-specific bash scripts are required.

### 1.1 Clone and Environment Setup

```powershell
# Open Windows PowerShell or cmd
cd D:\FLOCK_ASSIGNMENT\refit-nilm

# Create a virtual environment
python -m venv venv

# Activate virtual environment
# In PowerShell:
.\venv\Scripts\Activate.ps1
# In Command Prompt (cmd):
.\venv\Scripts\activate.bat

# Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 1.2 Data Placement and Configuration
By default, the repository expects raw and cleaned REFIT CSV files to reside in the parent directory (`D:\FLOCK_ASSIGNMENT\`), strictly outside the Git repository:

```text
D:\FLOCK_ASSIGNMENT\
├── CLEAN_House1.csv ... CLEAN_House5.csv
├── RAW_House1_Part1.csv, RAW_House1_Part2.csv
├── CLEAN_READ_ME_081116.txt
└── refit-nilm\                <-- Git repository root
    ├── config.py
    ├── notebooks/
    └── ...
```

- **Environment Override:** Other users can point the codebase to any custom data directory by setting the `REFIT_DATA_DIR` environment variable:
  ```powershell
  $env:REFIT_DATA_DIR = "C:\path\to\your\refit_data"
  ```
- **Extracting Archives (7-Zip):** If working from raw `.7z` archives (`CLEAN_REFIT_081116.7z`), extract files using 7-Zip GUI or CLI into the data directory:
  ```powershell
  & "C:\Program Files\7-Zip\7z.exe" x CLEAN_REFIT_081116.7z -o"D:\FLOCK_ASSIGNMENT"
  ```
  *(Note: The repository scripts treat all data files as strictly read-only and never modify or commit them).*

### 1.3 Running the Jupyter Notebooks

```powershell
jupyter lab
# Or classic notebook:
jupyter notebook
```
Navigate to `notebooks/` and execute them in order:
1. `notebooks/01_raw_cleaning.ipynb`
2. `notebooks/02_washing_machine_eda.ipynb`
3. `notebooks/03_disaggregation.ipynb`

To re-run all notebooks headlessly from the command line:
```powershell
jupyter nbconvert --execute --to notebook --inplace notebooks/01_raw_cleaning.ipynb
jupyter nbconvert --execute --to notebook --inplace notebooks/02_washing_machine_eda.ipynb
jupyter nbconvert --execute --to notebook --inplace notebooks/03_disaggregation.ipynb
```

---

## 2. Repository Structure

```text
refit-nilm/
├── .gitignore                      # Strictly ignores data/, *.parquet, *.csv, *.7z, caches
├── requirements.txt                # Pinned dependencies
├── config.py                       # Central paths (relative to root + env override) & metadata
├── src/
│   ├── __init__.py
│   ├── io_utils.py                 # Safe chunked loaders with explicit dtypes
│   ├── cleaning.py                 # Spike filtering, BST->UTC fix, deduplication, 1-min resampler
│   ├── cycles.py                   # Event detection, parameter sensitivity grid, metrics
│   ├── features.py                 # 61-minute centered rolling features (float32 memory-safe)
│   └── evaluation.py               # Continuous (MAE, RMSE, R2) & event metrics (Precision, Recall, F1)
├── notebooks/
│   ├── 01_raw_cleaning.ipynb       # Problem 1: Raw House 1 cleaning & sanity check
│   ├── 02_washing_machine_eda.ipynb # Problem 2: Multi-house EDA, cycle rule & usage habits
│   └── 03_disaggregation.ipynb     # Problem 3: Disaggregation, baselines & failure analysis
├── figures/                        # Generated publication-quality PNG figures (Figures 1 to 7)
├── results/                        # Generated audit CSVs, JSON metrics, and checkpoints
│   ├── problem1_summary.json / .csv
│   ├── problem1_official_comparison.json
│   ├── problem2_eda.json / problem2_cycle_sensitivity.csv / problem2_house_comparison.csv
│   ├── problem3_metrics.json / .csv / problem3_loho_generalization.csv
│   ├── checkpoint_problem1.md / checkpoint_problem2.md / checkpoint_problem3.md
│   └── final_audit.md              # Line-by-line verification against assignment PDF
├── DATA.md                         # Detailed dataset documentation, quality findings & cleaning
├── RESULTS.md                      # Comprehensive findings, embedded figures & failure analysis
├── Recommendation.md               # 1-page utility executive summary & Section 4 questions
└── README.md                       # Main architecture guide & setup manual
```

---

## 3. Assumptions and Key Engineering Decisions

1. **Part 1 / Part 2 Boundary Overlap:**  
   `RAW_House1_Part1` and `Part2` overlap between `2014-06-27` and `2014-10-01` (95 days). Cross-correlation at 0s offset is $r = 0.7887$, confirming identical clock references. We enforced the transition at `2014-10-01 01:27:07` where Part 1 ended, seamlessly matching the official Strathclyde cleaned dataset.
2. **Order of Operations (NaNs First):**  
   Impossible spikes must be set to `NaN` *before* de-duplicating or resampling. Otherwise, a 98 kW glitch would corrupt the duplicate average or leak into neighboring bins during linear interpolation.
3. **Physical Spike Thresholds:**  
   - Sub-meter plug monitors (IAMs): Capped at **4,000 W** based on UK BS 1363 13A socket limits ($13\text{A} \times 230\text{V} \approx 3\text{ kW}$).
   - Whole-home Aggregate clamp: Capped at **15,000 W** based on domestic load distributions (allowing 10 kW electric showers + simultaneous cooking) while eliminating unphysical 24 kW CT saturation flat-tops.
4. **Timezone Standardization:**  
   Raw logger naive Unix timestamps jumped backward by $-3,597\text{ s}$ during the October 2013 clock change. Shifting all British Summer Time (BST) rows by -3600 seconds established a continuous, strictly monotonic UTC time base.
5. **Data-Driven Gap Threshold:**  
   Analysis of 3.37 million raw time intervals showed that 99.98% of valid sensor arrivals occur within $\le 120\text{ s}$ (2 minutes). Therefore, gaps $\le 3\text{ minutes}$ are linearly interpolated, while outages $> 3\text{ minutes}$ are strictly left as `NaN` and marked with `outage_flag = True`.
6. **Cycle Detection Rule:**  
   Derived via a 27-parameter sensitivity grid: `on_threshold = 15.0 W`, `min_peak = 500.0 W`, `merge_gap = 10 min`, `min_duration = 15 min`.
7. **Leakage-Free Disaggregation Validation:**  
   Contiguous chronological block splits (60% Train, 20% Val, 20% Test) with an excised **2-hour buffer gap** (120 min > 61 min window). Scalers and diurnal profile baselines were fit exclusively on the training block.
8. **Memory Management on Laptops:**  
   To prevent out-of-memory errors on Windows laptops with constrained RAM, all raw streaming is handled line-by-line in pure Python, 1-minute cleaned series are cached to Parquet in `data/processed/`, and feature matrices use `float32`.

---

## 4. Research Ideas Adopted and Rejected

### Research Ideas Adopted
1. **Nalmpantis et al. (Sensors 2022 — "Neural Fourier Energy Disaggregation"):**
   - *Input Window Length:* Adopted the principle of matching window size to target appliance operating duration. In Problem 2, observed wash cycles had a median duration of 33–99 minutes; this directly guided our selection of a 61-minute centered window ($\pm 30$ min).
   - *Evaluation Methodology & Generalization Loss:* Adopted their dual-metric benchmark structure (combining continuous MAE/RMSE with event-level $F_1$) and their Leave-One-House-Out cross-building evaluation protocol to quantify generalization loss on unseen homes.
2. **Murray et al. (2015 — "A data management platform for personalised real-time energy feedback"):**
   - Adopted the documented REFIT sub-meter cap ($4,000\text{ W}$) and daylight savings alignment.
3. **Zhang et al. (AAAI 2018 — Sequence-to-Point):**
   - Adopted the sequence-to-point paradigm where a centered time window of aggregate power ($t-W$ to $t+W$) predicts the midpoint appliance state $y_t$.

### Research Ideas Deliberately NOT Adopted (and Why)
1. **Deep Neural Network Architectures (FNet, CNNs, Bi-GRUs, Transformers):**
   - *Reason:* The assignment instructions state: *"Model complexity is not part of the assessment... A simple, correct solution beats a complex one that is hard to justify."* Deep neural networks require high GPU memory, extensive training time, and heavy hyperparameters. `HistGradientBoostingRegressor` trains in seconds on a standard CPU, natively captures non-linear step changes, requires no arbitrary feature scaling, and is fully explainable to an engineering student.
2. **Frequency-Domain / Fast Fourier Transform (FFT) Features:**
   - *Reason:* At 1-minute smart-meter resolution, the Nyquist frequency is $\frac{1}{120}\text{ Hz} \approx 0.0083\text{ Hz}$. High-frequency harmonic current signatures (which FFT utilizes at 50 Hz or 100 Hz) are completely absent. Rolling time-domain statistics (mean, std, min, max, lags, deltas) provide superior physical discrimination without complex spectral transforms.

---

## 5. Use of AI Tools Attribution

As required by the assignment guidelines:
- **Tool Used:** **Google Antigravity** (Advanced Agentic Coding Pair Programmer).
- **Purpose and Scope:**
  - Automated initial data profiling and streaming inspection of large CSV files.
  - Formulated the line-by-line zero-memory streaming architecture in `src/cleaning.py`.
  - Assisted in structuring reproducible script execution, parameter sensitivity grids, and markdown documentation formatting.
  - *Data Integrity:* All diagnostic counts, metrics, and figures were produced strictly from code executed against the actual data files; no synthetic metrics or hallucinated citations were introduced.

---

## 6. What I Would Do Next (Future Improvements)

If allocated additional engineering time beyond the 4–6 hour scope, the following improvements would yield the highest return:
1. **Multi-Appliance Joint Disaggregation:** Expand the model to jointly disaggregate washing machines, tumble dryers, and dishwashers using multi-output gradient boosting, directly resolving the resistive heater confusion identified in our failure analysis.
2. **Self-Supervised Domain Adaptation:** Implement a few-shot fine-tuning step where a newly connected household's unmetered aggregate data is used to adapt tree leaf weights to local base load levels, reducing zero-shot generalization loss.
3. **Reactive Power and Harmonics Integration:** If deployed on advanced AMI meters logging active and reactive power ($P$ and $Q$), incorporate power factor features. Washing machines have significant inductive motor phases ($PF \approx 0.7 - 0.85$), whereas resistive tumble dryers and kettles operate at $PF \approx 1.0$, enabling near-perfect physical separation.
