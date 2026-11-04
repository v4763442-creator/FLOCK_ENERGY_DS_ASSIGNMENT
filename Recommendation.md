# Recommendation: Utility Disaggregation Viability and Operational Limits

**Executive Briefing for Flock Energy & Utility Partners** | *Target Length: ~500 Words*

---

### 1. Suitable Uses and Operating Boundaries of the Model
Our analysis shows that 1-minute Non-Intrusive Load Monitoring (NILM) using `HistGradientBoosting` can estimate total household washing-machine electricity consumption to within **12.67% error** (30.78 kWh error on 243.0 kWh total) and detect **71.4% of active laundering minutes** on households seen during training (*supported by our results*).

**Recommended Uses:**
- **Targeted Demand-Side Management (DSM):** Identifying customers who frequently run laundry during high-cost peak windows (08:00–11:00 AM) to deliver targeted delay-start incentives (*supported by our results*).
- **Customer Energy Audits & Disaggregated Feedback:** Providing monthly billing breakdowns and recommending lower wash temperatures (*supported by our results*).

**Unsuitable Uses (Boundaries):**
- **Sub-Metered Revenue Billing:** With an event-level precision of 21.4% (elevated false positives during concurrent heating loads), the model cannot replace physical sub-meters for certified billing (*supported by our results*).
- **Uncalibrated Zero-Shot Deployment:** When evaluated on completely unseen homes (Leave-One-House-Out), $F_1$ scores degraded by 18% to 29% (*supported by our results*). Models must not be used for real-time grid automation without local calibration (*reasoned judgement*).

---

### 2. Energy-Saving Opportunity and Measurement & Verification (M&V)
- **Opportunity:** Laundering activity exhibits a sharp morning peak between **08:00 and 11:00 UTC** (over 45% of weekday cycle starts), while washing programs range from **0.32 kWh** (House 1) to **0.62 kWh** (House 2) (*supported by our results*). Shifting laundry to off-peak solar hours via delay-start nudges and encouraging lower wash temperatures can reduce peak load and consumption (*reasoned expectation*).
- **Measurement Plan:** We recommend a **Randomized Controlled Trial (RCT)** evaluated via **Difference-in-Differences (DiD)** regression comparing an intervention group (receiving disaggregated insights and TOU prompts) against a randomized control group (*reasoned judgement*). The primary metrics are the proportion of cycles started in the peak window and total laundering kWh, controlling for ambient temperature, seasonal weather, and holiday schedules (*reasoned judgement*).

---

### 3. Key Limitations and Transferability to India
- **Overlapping Loads:** Resistive heating coils in tumble dryers (~2.2 kW) and kettles produce aggregate step changes identical to washing machine heaters, triggering model false positives (*supported by our results*).
- **Missing Telemetry:** Unrecorded gateway dropouts create gaps that must be masked rather than filled (*supported by our results*).
- **Applying UK Results to India:**
  1. *Appliance Design:* Many Indian washing machines are top-loading models that wash with ambient cold water, drawing only 150–400 W for the motor (*reasoned expectation*). Without the 2 kW heating pulse present in UK machines, the signature is easily masked by ceiling fans and baseline appliances (*reasoned judgement*).
  2. *Power Quality & Backup Systems:* Periodic voltage fluctuations and unmetered battery inverters (UPS) decouple smart meters from actual instantaneous consumption during outages (*reasoned expectation*).
  3. *Climate & Drying Habits:* Abundant solar heat enables outdoor air-drying, eliminating tumble dryers but altering laundry timing to early mornings (*reasoned expectation*).

---

### 4. Impact of 15-Minute or 30-Minute Smart-Meter Data
When data is recorded at 15- or 30-minute intervals:
- A 15-minute heating spike of 2,200 W is mathematically averaged over 30 minutes into a modest ~360 W increase (*supported by math*).
- Rapid motor reversals and turn-on edges vanish into flat interval blocks (*supported by math*).
- Disaggregating simultaneous appliances becomes mathematically ill-posed, dropping discrete event detection to negligible levels (*reasoned judgement*).
