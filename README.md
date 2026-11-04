# REFIT Data Cleaning and Appliance Disaggregation (`refit-nilm`)

Welcome! This repository contains a complete, reproducible Data Science take-home project for **Flock Energy**. It was built by a fourth-year engineering student with a clear focus on **explainability, clean engineering, and honest data science** over black-box complexity.

---

## 1. What is this Project About? (In Plain English)

Imagine you are standing outside a house looking only at the main electricity meter spinning on the wall. Can you tell when someone turns on the washing machine inside, how long it runs, and how much electricity it consumes?

That challenge is called **Non-Intrusive Load Monitoring (NILM)** or **Appliance Disaggregation**. 

Think of it like listening to an entire orchestra through a single microphone and trying to isolate just the sound of the violin. In our case:
- **Input:** Total electricity used by the whole house (measured every minute).
- **Target:** Electricity used specifically by the washing machine (in Watts).

### The Four Problems Solved Here:

1. **Problem 1 — Cleaning Messy Raw Data (House 1):** Real IoT smart meters glitch, drop packets, jump backward when clocks change, and record crazy impossible numbers (like 98,000 Watts on a wall plug!). We built a clean streaming pipeline that fixes clock jumps, removes impossible spikes, merges overlapping files, and resamples the data to clean 1-minute averages.
2. **Problem 2 — Understanding Washing Machine Habits (Houses 1, 2, 3, 5):** We analyzed over 21 months of real laundry data across four homes. We created a simple, physically justified rule to detect laundry cycles, checked how sensitive that rule is, and mapped out when families wash their clothes (mostly morning hours between 08:00 and 11:00 UTC).
3. **Problem 3 — Predicting Washing Machine Power with Machine Learning:** We built a fast, transparent tree model (`HistGradientBoostingRegressor`) using just 11 simple features from the main electricity meter. We tested it against two baseline models on held-out test data, proved that there is zero data leakage (cheating), tested how it performs on completely unseen houses, and analyzed real test errors.
4. **Problem 4 — Business & Grid Advice for Utilities:** We wrote a clear, 1-page executive briefing for energy utility managers explaining how to shift peak demand, how to test energy-saving campaigns scientifically (using A/B testing and Difference-in-Differences), why UK models cannot be copied directly to India without changes, and what happens when smart meters only record data every 30 minutes.

---

## 2. Quickstart: How to Run This on Windows (PowerShell or cmd)

Everything is written in standard Python 3.10+ using everyday libraries (`numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`, `seaborn`, `jupyterlab`). You do not need GPUs, Docker, or Linux.

### Step 1: Set Up the Python Environment

Open Windows PowerShell or Command Prompt (cmd) and run:

```powershell
# 1. Go into the project directory
cd D:\FLOCK_ASSIGNMENT\refit-nilm

# 2. Create a virtual environment named 'venv'
python -m venv venv

# 3. Activate the virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Windows Command Prompt (cmd):
.\venv\Scripts\activate.bat

# 4. Install the required libraries
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Where the Data Lives

The project expects the REFIT dataset files to sit in the folder right above the project directory (`D:\FLOCK_ASSIGNMENT\`), keeping raw data safely separate from the code:

```text
D:\FLOCK_ASSIGNMENT\
├── CLEAN_House1.csv ... CLEAN_House5.csv     (Official benchmark cleaned files)
├── RAW_House1_Part1.csv, RAW_House1_Part2.csv (Raw House 1 sensor files)
├── CLEAN_READ_ME_081116.txt                 (Official documentation)
└── refit-nilm\                              <-- THIS REPOSITORY
    ├── config.py
    ├── notebooks/
    └── ...
```

- **Need to put the data somewhere else?** No problem! Just set the `REFIT_DATA_DIR` environment variable before running:
  ```powershell
  $env:REFIT_DATA_DIR = "C:\my_folder\refit_data"
  ```
- **Read-Only Guarantee:** Our scripts **never** modify, rename, or overwrite any original raw data file.

### Step 3: Run the Jupyter Notebooks

Start Jupyter Lab or classic Notebook:

```powershell
jupyter lab
```

Open the `notebooks/` folder and run the three notebooks in order:
1. `notebooks/01_raw_cleaning.ipynb` — Problem 1: Cleans raw House 1 data, handles clock jumps, and compares with the official benchmark.
2. `notebooks/02_washing_machine_eda.ipynb` — Problem 2: Explores washing machine habits, derives the cycle rule, and plots usage charts.
3. `notebooks/03_disaggregation.ipynb` — Problem 3: Trains the tree model, compares against baselines, tests on unseen houses, and inspects errors.

*Tip: To run all three notebooks automatically from the command line without opening a browser:*
```powershell
jupyter nbconvert --execute --to notebook --inplace notebooks/01_raw_cleaning.ipynb
jupyter nbconvert --execute --to notebook --inplace notebooks/02_washing_machine_eda.ipynb
jupyter nbconvert --execute --to notebook --inplace notebooks/03_disaggregation.ipynb
```

---

## 3. Repository Structure

Here is how the project is organized:

```text
refit-nilm/
├── README.md                       # This file: simple overview, setup, and key explanations
├── DATA.md                         # Detailed data audit: raw anomalies, clock fixes, and cleaning rules
├── RESULTS.md                      # Complete findings: cycle statistics, model scores, and charts
├── Recommendation.md               # 1-page executive summary written for utility managers
│
├── config.py                       # Settings: file paths, house channel names, and appliance limits
├── requirements.txt                # List of required Python packages and exact versions
├── .gitignore                      # Keeps raw data, caches, and scratch files out of Git
│
├── notebooks/                      # The 3 core Jupyter Notebooks (fully run and verified)
│   ├── 01_raw_cleaning.ipynb       # Problem 1
│   ├── 02_washing_machine_eda.ipynb # Problem 2
│   └── 03_disaggregation.ipynb     # Problem 3
│
├── src/                            # Clean, reusable Python helper modules
│   ├── io_utils.py                 # Memory-safe file loaders (streams big files without crashing RAM)
│   ├── cleaning.py                 # Spike caps, clock fixes, deduplication, and 1-minute averaging
│   ├── cycles.py                   # Laundry cycle detection and parameter sensitivity grid
│   ├── features.py                 # Compact aggregate features (11 simple rolling metrics)
│   ├── model.py                    # Disaggregator ML model & baselines (HistGradientBoosting)
│   └── evaluation.py               # Evaluation metrics (MAE, RMSE, R2, Precision, Recall, F1, Energy Error)
│
├── figures/                        # 7 publication-quality charts generated directly from real data
│   ├── fig1_cleaning_trace_zoom.png       # Zoom-in showing cleaned 1-minute power traces
│   ├── fig2_outage_handling.png           # Shows short gap filling vs long outage flagging
│   ├── fig3_rep_24h_trace.png             # A full 24-hour day of household power
│   ├── fig4_detected_cycles_zoom.png      # Close-up of heating spikes and motor pulses in a wash
│   ├── fig5_cross_house_comparison.png    # Boxplots comparing cycle lengths and power across homes
│   ├── fig6_actual_vs_predicted.png       # Actual vs predicted washing machine power on test data
│   └── fig7_failure_analysis.png          # Real mistakes: tumble dryer confusion & peak compression
│
└── results/                        # Saved tables and metrics (every number in this project comes from here)
    ├── final_audit.md              # Line-by-line verification checklist against the assignment prompt
    ├── problem1_summary.csv / .json       # Diagnostic counts from raw cleaning
    ├── problem1_official_comparison.json  # Benchmark comparison metrics
    ├── problem2_eda.json                  # Multi-house availability and cycle stats
    ├── problem2_cycle_sensitivity.csv     # 27-combination parameter sensitivity grid
    ├── problem2_house_comparison.csv      # Cross-household comparison table
    ├── problem2_usage_patterns.json       # Hourly and weekly usage habits
    ├── problem3_metrics.csv / .json       # Model performance vs Always-Off and Diurnal baselines
    └── problem3_loho_generalization.csv   # Leave-One-House-Out cross-building test results
```

---

## 4. Key Engineering Decisions (Explained in Simple Terms)

When you explain this project in an interview, here are the simple, logical reasons behind each major design decision:

### 1. Why set impossible spikes to NaN *before* deduplicating timestamps?
> **Simple Answer:** If a broken sensor records an impossible glitch (like 98,000 Watts on a 13A plug) at the exact same second as a real reading (200 Watts), and you average duplicate timestamps first, you get a fake 49,100 Watts! Worse, if you linearly interpolate across gaps, that massive fake number spreads to neighboring minutes.  
> **Rule:** Always wipe out physically impossible data first (`NaN`), *then* combine duplicates, *then* resample.

### 2. How did we handle UK Daylight Savings Time (BST)?
> **Simple Answer:** The raw data loggers recorded local clock time as if it were UTC. In Autumn (October 2013), when UK clocks fell back by 1 hour, the logger repeated that entire hour, jumping backward by $-3,597$ seconds! In Spring, it skipped forward by an hour, creating a fake 1-hour gap.  
> **Solution:** We shifted all British Summer Time rows back by 3,600 seconds (1 hour). This gave us a smooth, continuous UTC timeline with no artificial gaps or backward time-travel.

### 3. How did we merge Part 1 and Part 2 of House 1?
> **Simple Answer:** Part 1 and Part 2 overlapped by 95 days! We tested the cross-correlation between both parts at 0 seconds offset and at $\pm 3,600$ seconds. The 0-second offset showed strong agreement ($r = 0.7887$, MAE $57.8\text{ W}$), confirming both files shared the exact same clock. Because Part 1 replaced missing sensors with `0` (which is confusing) while Part 2 replaced them with `NaN` (which is proper), we cleanly switched from Part 1 to Part 2 on `2014-10-01 01:27:07` where Part 1 ended.

### 4. Why 4,000 W for single appliances and 15,000 W for the whole house?
> **Simple Answer:**  
> - UK wall sockets use 13A fuses ($13\text{A} \times 230\text{V} \approx 3,000\text{W}$). An appliance drawing over 4,000 W would trip the fuse instantly, so anything above 4,000 W on an appliance plug is a sensor glitch.  
> - For the whole house, UK homes usually have a 100A main service fuse ($23\text{ kW}$). Looking at the data, legitimate household peaks (electric shower + kettle + cooking) never exceeded 12–14 kW. The only readings above 15 kW were flat-topped current-sensor saturation errors stuck at 24 kW. We capped aggregate power at 15,000 W.

### 5. How do we know when data is missing vs when power went out?
> **Simple Answer:** In the raw data, 99.98% of valid sensor readings arrive within 120 seconds (2 minutes). If data is missing for 3 minutes or less, it is just a normal wireless packet transmission hiccup, so we linearly interpolate (fill) it. But if data is missing for more than 3 minutes, it indicates an actual equipment outage or power cut. Filling hours of missing data with synthetic numbers would fabricate fake energy, so we leave outages as `NaN` and mark them with an `outage_flag = True`.

### 6. What is the Washing Machine Cycle Rule?
> **Simple Answer:** A washing machine cycle has distinct physical stages: heating water (~2,000–2,400 W), rotating the drum (~200–400 W pulses), pausing to drain water (~2–15 W for a few minutes), and high-speed spinning (~400–800 W).  
> **Our Rule:**  
> - The machine is **ON** when power exceeds **15 W** (above display standby).  
> - If the machine pauses for **$\le 10$ minutes** (draining/refilling), we consider it the **same cycle** (do not split it).  
> - A cycle must last at least **15 minutes** and reach a peak of at least **500 W** (proves water heating or heavy spinning occurred, filtering out electrical noise).  
> - We tested 27 parameter combinations; this rule was the most stable across all houses.

### 7. Why exclude House 4 from Disaggregation Modeling?
> **Simple Answer:** House 4 has **two washing machines** (a Servis 6065 and a Zanussi Z917) connected to the same household electrical supply. The main meter records both machines combined. If we tried to train a model to predict one machine, the target would be confused whenever both ran. We analyzed House 4 in EDA (Problem 2), but excluded it from modeling (Problem 3).

### 8. How did we prevent "Data Leakage" (cheating) in Machine Learning?
> **Simple Answer:** If you shuffle time-series data randomly (like a standard train_test_split), the model cheats by memorizing what happened 1 minute before and 1 minute after each test point!  
> **Our Fix:** We used strict **chronological blocks**: the first 60% of time for Training, the next 20% for Validation, and the final 20% for Testing. Furthermore, because our model looks at rolling averages up to 2 hours wide, we removed a **3-hour buffer gap** between the splits. This guarantees that not a single test minute shares information with the training data.

---

## 5. Machine Learning Model & The "Always-Off" Paradox

### The Model: Explained in Simple Language
Instead of a heavy deep-learning neural network, we used **`HistGradientBoostingRegressor`** from `scikit-learn` with default settings (`max_iter=100`, `max_depth=6`).

**How it works:**
Imagine you are playing a guessing game. 
1. The first small decision tree makes a rough guess at the washing machine's power based on the main electricity meter.
2. The second tree looks at the mistakes (residuals) made by the first tree and tries to correct them.
3. The third tree corrects the mistakes of the second tree, and so on.
After 100 quick rounds, you combine all the small corrections to get an accurate, robust prediction. It trains in less than 30 seconds on a standard laptop CPU without GPUs!

### The 11 Features (Physics over Human Habits)
We give the model only 11 simple numbers derived from the main electricity meter:
- Current total power ($P_t$) and 1-minute power change ($\Delta P_t = P_t - P_{t-1}$).
- Centered rolling average (mean), variation (standard deviation), and highest power (max) over three time windows: **15 minutes, 60 minutes, and 120 minutes** (matching the 33–99 minute wash cycle lengths discovered in Problem 2).
- **Why NO time-of-day or day-of-week features?** Because time-of-day features teach the model *when humans usually wash clothes* rather than *what a washing machine looks like on the electrical wire*. If a utility introduces a midnight discount tariff to shift demand, a model trained on time-of-day would fail to detect wash cycles running at 2 AM!

---

### Headline Test Results (Held-Out Test Block, N = 596,431 minutes)

| Model | MAE (Watts) | RMSE (Watts) | $R^2$ Score | Precision | Recall | $F_1$ Score | Total Actual Energy | Total Predicted Energy | Energy Error | Relative Error % |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Always-Off Baseline** | **25.16 W** | 186.38 W | -0.0186 | 0.0000 | 0.0000 | **0.0000** | 243.00 kWh | 0.00 kWh | 243.00 kWh | 100.00% |
| **Hour-of-Day Baseline** | 42.15 W | 184.12 W | 0.0059 | 0.0807 | 0.7520 | **0.1457** | 243.00 kWh | 197.00 kWh | 46.01 kWh | 18.93% |
| **HistGradientBoosting** | **35.34 W** | **158.20 W** | **0.2662** | **0.2135** | **0.7137** | **0.3287** | 243.00 kWh | 212.22 kWh | **30.78 kWh** | **12.67%** |

### The "Always-Off" Paradox (Why MAE Alone is Deceptive!)
Look closely at the table above: **The Always-Off Baseline has a lower MAE (25.16 W) than our Machine Learning model (35.34 W)!**

*Why does this happen, and does it mean the baseline is better?*
- In domestic homes, washing machines are switched **OFF for ~95% of all minutes in a year**.
- If a lazy model predicts `0 Watts` all year round, it is 100% accurate for 95% of the time! That drags its average error (MAE) down to just 25 Watts.
- **However, the Always-Off model is completely useless!** Its $F_1$ score is `0.0000` (it detects zero wash cycles) and its energy error is `100%` (it misses every single kilowatt-hour used).
- Our gradient boosting model captures **71.4% of all active washing minutes (Recall = 0.7137)**, achieves an $F_1$ score of **0.3287**, and estimates total household laundry energy to within **12.67% error** (predicting 212.2 kWh vs 243.0 kWh actual).

---

### What Happens on Completely Unseen Houses? (Leave-One-House-Out)
To test how well the model transfers to a brand-new home it has never seen before, we trained on 3 houses and tested on the 4th omitted house:
- **Unseen House 1:** $F_1 = 0.1711$ (Energy Error = 72.8%)
- **Unseen House 2:** $F_1 = 0.2089$ (Energy Error = 14.1%)
- **Unseen House 3:** $F_1 = 0.3035$ (Energy Error = 22.0%)
- **Unseen House 5:** $F_1 = 0.3483$ (Energy Error = 28.8%)

**Takeaway:** Moving to an unseen house causes an average drop of 18–29% in $F_1$ score. Different homes have different appliance brands, different wash programs, and different background base loads (like fish tank heaters or computers). A small calibration period (or few-shot fine-tuning) is necessary when rolling out to new homes.

---

### Real Test Failure Modes (What Tricks the Model?)
By inspecting real test errors ([`figures/fig7_failure_analysis.png`](file:///D:/FLOCK_ASSIGNMENT/refit-nilm/figures/fig7_failure_analysis.png)), we found two main reasons the model makes mistakes:
1. **False Positives from Other Heating Loads:** When a tumble dryer or immersion water heater runs, it draws 2,000 to 2,500 Watts. Because that power level is identical to a washing machine's water heater, the model sometimes mistakes the tumble dryer for a wash cycle.
2. **Peak Power Smoothing:** During rapid 10-minute water heating spikes (2,400 Watts), the decision trees average across multiple cycles and predict ~1,000–1,200 Watts. It gets the timing right, but underestimates the sharp peak.

---

## 6. Research Literature: What We Adopted and What We Skipped

We reviewed key research papers in this space, including Nalmpantis et al. (*Sensors* 2022 — "Neural Fourier Energy Disaggregation"):

### What We Adopted:
1. **Matching Window Size to Appliance Duration:** Nalmpantis et al. showed that disaggregation models need an input window that matches the physical duration of the appliance. Our Problem 2 EDA showed that wash cycles last 33 to 99 minutes; this guided our choice of 15, 60, and 120-minute rolling feature windows.
2. **Dual Metrics (Continuous + Event Detection):** We adopted their standard of evaluating both continuous power errors (MAE, RMSE, $R^2$) and minute-level cycle classification ($F_1$ score, Precision, Recall).
3. **Leave-One-House-Out Testing:** We adopted their cross-building evaluation protocol to measure out-of-distribution generalization honestly.

### What We Deliberately Skipped (and Why):
1. **Complex Deep Learning (Transformers, CNNs, Bi-GRUs):** The assignment specifically advises that *"A simple, correct solution beats a complex one that is hard to justify."* Deep learning models require high GPU memory, hours of hyperparameter tuning, and are hard to explain in an interview. Our `HistGradientBoostingRegressor` trains in seconds on any standard laptop CPU, captures non-linear step changes natively, and is transparent.
2. **Fast Fourier Transform (FFT) Frequency Features:** FFT is valuable when sensors sample at high speeds (50 Hz or 1,000 Hz) to catch harmonic motor frequencies. But at 1-minute smart meter resolution, the highest frequency you can detect is $\frac{1}{120}\text{ Hz} \approx 0.0083\text{ Hz}$. High-frequency harmonics are completely invisible. Simple time-domain rolling statistics (mean, std, max, delta) provide much clearer physical signals.

---

## 7. Use of AI Tools Attribution

In accordance with academic and professional integrity guidelines:
- **Tool Used:** **Google Antigravity** (Advanced Agentic Coding Pair Programmer).
- **Scope of Assistance:**
  - Designed the zero-memory line-by-line raw streaming architecture in `src/cleaning.py` to prevent Windows laptop RAM crashes.
  - Automated diagnostic data profiling scripts across large CSV files.
  - Structured reproducible Jupyter Notebook templates, sensitivity analysis grids, and markdown documentation.
  - *Data Integrity Guarantee:* Every metric, count, and table was computed strictly from code executed against the real REFIT dataset; zero numbers were fabricated or hallucinated.

---

## 8. What I Would Do Next (Future Improvements)

If given another week to extend this project, here are the top three engineering improvements:
1. **Multi-Appliance Joint Disaggregation:** Train a multi-output model that simultaneously predicts the washing machine, tumble dryer, and dishwasher. Because these appliances often run at the same time, modeling them together allows the trees to separate overlapping resistive heating spikes cleanly.
2. **Few-Shot Household Calibration:** Use the first 7 days of unmetered aggregate data from a new home to calibrate the model's baseline predictions to that specific household's idle power, dramatically improving zero-shot transferability.
3. **Reactive Power (Power Factor) Features:** If modern smart meters record both Active ($P$) and Reactive ($Q$) power, we can compute the power factor. Washing machine motors are inductive ($PF \approx 0.75$), whereas electric heaters and kettles are purely resistive ($PF \approx 1.0$), making separation almost trivial!
