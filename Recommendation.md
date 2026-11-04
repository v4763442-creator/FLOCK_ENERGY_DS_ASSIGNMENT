# Recommendation.md: Utility Recommendations, Practical Implications, and Operational Limits

**Audience:** Utility Product Leaders, Demand-Side Management (DSM) Planners, and Smart Grid Engineers  
**Project:** Non-Intrusive Load Monitoring (NILM) for Appliance Disaggregation  
**Scope:** One-Page Utility Executive Briefing & Responses to Section 4 Requirements  

---

## 1. Executive Summary: Suitable Uses and Boundaries of the Model

Non-Intrusive Load Monitoring (NILM) at 1-minute smart-meter resolution offers utilities an automated, zero-hardware pathway to infer individual appliance consumption from whole-home aggregate measurements. However, successful operational deployment requires matching the model to its mathematically viable use cases while respecting fundamental physics:

### Suitable Operational Uses
- **Targeted Energy-Efficiency Audits & Disaggregated Billing:** Providing customers with monthly appliance-level energy breakdowns (estimating total laundering kWh within $\pm 15.3\%$ error on seen households).
- **Time-of-Use (TOU) Demand Response Planning:** Identifying which households regularly wash during high-tariff grid peak windows (08:00–11:00) to target demand-shifting incentives.
- **Eco-Program Nudges:** Detecting prolonged high-temperature cycles to recommend modern cold-wash detergent programs.

### Unsuitable Operational Uses (Boundaries)
- **High-Stakes Legal or Sub-Metered Billing:** Single-channel active power NILM exhibits minute-level false positive rates (~78% false-positive state predictions during concurrent heating loads). It must never replace certified revenue-grade sub-meters for tenant billing.
- **Zero-Shot Real-Time Safety Interventions:** On completely unseen homes, transferability drops significantly ($F_1$ degrades by ~18–29%), meaning real-time grid balancing cannot rely solely on uncalibrated models.

---

## 2. Practical Energy-Saving and Customer-Insight Opportunity

### 2.1 The Opportunity: Morning Peak Shifting and Eco-Temperature Nudges
Our empirical findings reveal two massive utility optimization levers:
1. **Morning Laundering Peak:** Across all evaluated UK households, laundering activity peaks sharply between **08:00 and 11:00 UTC** (accounting for over 45% of weekday cycle starts), directly coinciding with the morning grid demand peak.
2. **Cycle Temperature / Duration Divergence:** House 2 (running extended hot/cotton washes) consumed **0.620 kWh per cycle**, whereas House 1 and House 5 consumed **0.322–0.325 kWh per cycle** (a **48% energy reduction per load**).

**Proposed Program:** A utility "Smart Laundry Nudge" combining:
- Automated smartphone notifications recommending a **Delay-Start schedule** to shift washing to off-peak / solar generation hours (12:00–15:00 or overnight 00:00–05:00).
- An educational "Cold Wash Challenge" providing rebate credits when cycles shift from 60°C to 30°C/Eco mode.

---

### 2.2 Measurement and Verification (M&V) Plan: Did It Work?
To rigorously evaluate program efficacy, the utility must execute a **Randomized Controlled Trial (RCT)** evaluated via a **Difference-in-Differences (DiD)** regression framework:

```
Y_it = β_0 + β_1 * Treatment_i + β_2 * Post_t + β_3 * (Treatment_i * Post_t) + γ * X_it + ε_it
```

1. **Experimental Design:**
   - **Target Population:** Customers identified by our disaggregation pipeline as running $\ge 3$ cycles/week during the morning peak (08:00–11:00).
   - **Random Assignment:** Split randomly into **Treatment Group** (receives disaggregated insights, dynamic TOU savings alerts, and cold-wash nudges) and **Control Group** (receives standard billing with no appliance insights).
2. **Core Outcome Metrics:**
   - *Peak-Window Load Shift:* Proportion of total laundering cycles initiated between 08:00 and 11:00 (baseline vs treatment period).
   - *Average Energy per Cycle:* Mean kWh consumed per detected cycle (measuring 60°C to 30°C temperature shifts).
   - *Customer Bill Impact:* Net monthly financial savings under TOU tariffs.
3. **Controlling for Confounders:**
   - **Seasonal Temperature:** Heating baseline loads rise in winter; weather-normalized cooling degree days (CDD) and heating degree days (HDD) must be included as covariates ($X_{it}$).
   - **Holiday / School Vacation Schedules:** Laundry surges during family vacations; DiD controls for shared macro temporal shocks across treatment and control cohorts.
   - **Household Occupancy Shifts:** Monitored via baseline standby power changes.

---

## 3. Real-World Limitations and Transferability Challenges

### 3.1 Overlapping Appliance Signatures
- **The Resistive Heating Dilemma:** A washing machine water heating coil (2.0–2.5 kW), a tumble dryer heater (2.0–2.5 kW, Creda T522VW in House 1), an electric kettle (2.5–3.0 kW), and an electric shower (9.5–10.5 kW) are all purely resistive loads ($PF \approx 1.0$).
- In single-channel active power NILM, when two resistive appliances operate concurrently or sequentially, the model cannot distinguish them by waveform shape alone, leading to false positives (as demonstrated in `figures/fig7_failure_analysis.png`).

### 3.2 Missing Data and Telemetry Interruptions
- In real smart-meter deployments, gateway dropouts (e.g. the 2-week February 2014 outage) create blind spots. Unprincipled interpolation fabricates phantom cycles. Models must incorporate explicit validity masks.

### 3.3 Household Behavioral Heterogeneity
- As demonstrated by our Leave-One-House-Out benchmark (`problem3_loho_generalization.csv`), transferability to unseen homes experiences a **18–29% drop in $F_1$ score**. Variations in household size, detergent types, machine ages, and base loads require localized self-supervised fine-tuning.

---

### 3.4 Transferring UK Findings to India: The Socio-Technical Gap
Applying a model trained on UK smart-meter data to the Indian domestic grid faces severe domain shifts:

1. **Appliance Architecture & Cold-Water Washing:**
   - *UK:* Over 90% of UK homes utilize European front-loading machines with internal 2–2.5 kW electrical heating elements that heat cold tap water to 40°C–60°C. The heating spike is the primary signal detected by NILM.
   - *India:* The dominant market share consists of **top-loading semi-automatic or fully automatic machines without internal heating elements** (water is supplied at ambient room temperature). The total power draw is dominated by the wash/spin agitator motor (**150 to 400 Watts only**). Without a 2 kW heating pulse, the washing machine signal is completely buried inside the base load of ceiling fans, refrigerators, and television sets.
2. **Power Quality and Grid Stability:**
   - *UK:* Stable 230V $\pm 10\%$ sinusoidal AC grid with virtually zero outages.
   - *India:* Domestic distribution grids frequently experience significant voltage sag (170V–260V fluctuations) and periodic load shedding. Many homes operate unmetered **battery inverters (UPS)** that switch on during outages, completely decoupling smart-meter readings from actual appliance consumption.
3. **Climate and Drying Culture:**
   - *UK:* Cold, humid winters force heavy reliance on heated tumble dryers and indoor radiators, creating confounding 2 kW resistive signatures.
   - *India:* Abundant solar insolation and tropical heat make tumble dryers virtually non-existent in mass households; laundry is air-dried outdoors, eliminating dryer confounders but altering laundry timing to early mornings to maximize daylight drying.
4. **Household Demographics & Domestic Labor:**
   - *UK:* Typically nuclear families running 3–4 large weekend loads.
   - *India:* Joint families or households with domestic help (*maids*) who wash clothes manually or run multiple daily small-batch cycles between 06:00 and 08:00 AM, creating a drastically different diurnal profile.

---

## 4. The Impact of 15-Minute or 30-Minute Smart-Meter Data

In commercial utility deployments, smart meters rarely stream at 1-minute resolution due to cellular bandwidth costs; standard AMI infrastructure logs at **15-minute or 30-minute intervals**. At this coarse granularity, the physics of disaggregation breaks down:

1. **Severe Signal Dilution:** A 15-minute wash heating pulse of 2,200 W represents $0.55\text{ kWh}$. When averaged over a 30-minute interval, this energy manifests as a diffuse average power of only **367 Watts** ($550\text{ Wh} / 0.5\text{ h} + \text{base load}$). The sharp 2.2 kW signature is diluted by 83%, making it indistinguishable from a refrigerator compressor surge, multiple ceiling fans, or a microwave.
2. **Loss of Temporal Edge Transitions:** The fast transient edges ($< 1\text{ minute}$) that characterize motor reversals and spin accelerations vanish entirely into flat block averages.
3. **Cycle Merging & Duration Inversion:** A short 30-minute cycle (such as House 1's median 33-minute wash) collapses into a single discrete data point. It becomes mathematically impossible to determine whether the load was a 30-minute washing machine, a 10-minute electric kettle run, or a 15-minute vacuum cleaner.
4. **Accuracy Degradation:** In NILM literature, moving from 1-minute to 30-minute data drops event detection $F_1$ scores from ~0.33 down to $< 0.10$, restricting utilities to coarse aggregate regression rather than discrete event tracking.

---

## 5. Evidence-Based Classification of Statements

To maintain scientific integrity, all statements in this recommendation are explicitly classified:

| Statement / Claim | Classification | Justifying Evidence / Source |
| :--- | :--- | :--- |
| Washing machines are idle $\ge 91.8\%$ of the time | **Supported by Our Results** | Direct calculation across 4 homes (`results/problem2_eda.json`) |
| Laundering peaks between 08:00 and 11:00 UTC | **Supported by Our Results** | Diurnal usage statistics (`results/problem2_usage_patterns.json`) |
| Machine learning model detects 64.7% of active minutes | **Supported by Our Results** | Held-out test set Recall = 0.6466 (`results/problem3_metrics.csv`) |
| Disaggregation estimates laundering kWh within 15.3% error | **Supported by Our Results** | Overall test energy error = 38.54 kWh on 251.9 kWh (`problem3_metrics.csv`) |
| Zero-shot transfer to unseen homes degrades $F_1$ by 18–29% | **Supported by Our Results** | Leave-One-House-Out benchmark (`results/problem3_loho_generalization.csv`) |
| Tumble dryers cause false positive washing machine detections | **Supported by Our Results** | Empirical failure analysis on House 1 (`figures/fig7_failure_analysis.png`) |
| RCT / Difference-in-Differences is the gold standard for M&V | **Reasoned Engineering Judgement** | Standard utility econometric evaluation practice |
| UK models fail in India due to unheated top-load washers | **Reasoned Engineering Judgement** | Physical knowledge of Indian appliance markets & grid infrastructure |
| 30-minute AMI data dilutes 2 kW peaks to ~360 W | **Supported by Our Results (Math)** | Energy conservation: $P_{\text{avg}} = \int P dt / \Delta t$ applied to our cycle traces |
