# DATA.md: Data Coverage, Raw Quality Findings, and Cleaning Decisions

---

## 1. Household Data Coverage and Units

All measurements are from the University of Strathclyde REFIT dataset covering UK domestic residences. Active power is recorded in **Watts (W)** at an event-driven nominal sampling rate of 6–8 seconds.

| File / House | Channel Used | Monitored Days | Cleaned 1-Min Bins | Usable Coverage % | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **House 1 (Raw & Clean)** | `Appliance5` | 639.0 days | 920,031 | 86.94% | Beko WMC6140. App4 is Creda T522VW tumble dryer. |
| **House 2 (Clean)** | `Appliance2` | 617.4 days | 889,078 | 75.38% | LG F1289TD. 24.6% missing (Feb 2014 outage). |
| **House 3 (Clean)** | `Appliance6` | 614.6 days | 885,095 | 88.62% | Unknown washing machine. |
| **House 4 (Clean)** | `Appliance4` & `5` | 633.9 days | 912,939 | 94.61% | WM1 (Servis 6065) and WM2 (Zanussi Z917). |
| **House 5 (Clean)** | `Appliance3` | 648.3 days | 933,593 | 90.66% | AEG L99695HWD washer-dryer. |

---

## 2. Raw House 1 Findings and Diagnostic Counts

All counts below were computed directly by our cleaning pipeline on House 1 (combining `RAW_House1_Part1.csv` and `Part2.csv`, totaling **7,573,360 raw rows**):

### 2.1 The Part 1 / Part 2 Boundary Overlap
- **The Overlap Window:** Part 1 ends on `2014-10-01 01:27:07`. Part 2 begins on `2014-06-27 21:57:50`. The two parts overlap for **95.1 days** (sharing 191,889 distinct timestamps).
- **Offset Verification:** Resampling both parts to 1-minute in the overlap yields a Pearson correlation of **$r = 0.7887$ (MAE = 57.80 W) at 0 seconds offset**. At $\pm 3600\text{ s}$ offset, correlation drops to $r \approx 0.03$. This confirms that both parts share the exact same clock reference.
- **Sensor Ambiguity in Part 1:** As documented in the Strathclyde readme, Part 1 substituted unpolled or unavailable sensors with `0`, whereas Part 2 substituted them with `NaN`. Consequently, in the Part-1-only period (Oct 2013 to Jun 2014), a reading of `0 W` is ambiguous—it cannot distinguish a true powered-off state from a temporary sensor dropout.
- **Merge Decision:** We transition from Part 1 to Part 2 exactly at `2014-10-01 01:27:07` where Part 1 ended, matching the official Strathclyde dataset demarcation.

### 2.2 Daylight Savings Time (DST) Transitions Handled
The raw logger recorded local UK wall-clock time as naive Unix timestamps without timezone awareness. We handled four clock transitions across the monitoring period:
1. **Autumn 2013 (2013-10-27):** Clocks fell back from 02:00 BST to 01:00 GMT. Raw Unix timestamps jumped backward by **$-3,597\text{ seconds}$** (row 249,600: `01:59:59`, Unix 1382839198 $\to$ row 249,601: `01:00:01`, Unix 1382835601).
2. **Spring 2014 (2014-03-30):** Clocks sprang forward from 01:00 GMT to 02:00 BST, creating an artificial **$+3,605\text{ second}$ gap** in raw timestamps.
3. **Autumn 2014 (2014-10-26):** Local clock transitioned from BST to GMT.
4. **Spring 2015 (2015-03-29):** Clocks sprang forward from 01:00 GMT to 02:00 BST, creating a **$+3,607\text{ second}$ gap**.

**Resolution:** We shifted all **4,104,740 rows (54.20%)** logged during British Summer Time (BST) by **-3,600 seconds** (`Unix - 3600`). This completely eliminated backward time travel and fake spring outages, producing a strictly monotonic UTC time series.

### 2.3 Spike Filtering Justified by Data Distribution
- **Single-Appliance Sockets (> 4,000 W):** UK domestic plug monitors (IAMs) operate on BS 1363 sockets with 13A fuses ($13\text{A} \times 230\text{V} \approx 3,000\text{W}$). Any reading $> 4,000\text{W}$ is an unphysical telemetry error. In raw data, **3,895 spikes $> 4,000\text{W}$** were detected (including glitch values reaching 76,677 W on the fridge and 98,301 W on the freezer). These were set to `NaN`.
- **Whole-Home Aggregate (> 15,000 W):** Over **99.99% of valid aggregate readings are below 12,000 W**. Readings between 12,000 W and 15,000 W are rare but legitimate multi-appliance combinations (e.g. an electric shower at 9.5–10.5 kW plus an electric kettle or toaster at 2–3 kW). Above 15,000 W, readings drop to fewer than 100 isolated points that hit flat-top current transformer (CT) saturation limits (24,000 W in Part 1 and 29,159 W in Part 2). Capping aggregate power at **15,000 W** eliminated **171 saturation spikes** while preserving real domestic load surges.

### 2.4 Duplicate Timestamps
- Identified **1,016,085 duplicate rows** in raw House 1.
- Grouping duplicate timestamps revealed that **914,781 groups (90.03%) were exact repeats** across all channels (caused by sensor re-transmissions). Only **101,304 groups (9.97%)** contained conflicting values (caused by separate asynchronous sub-meter packets arriving within the same integer second). The first valid reading per second was retained.

---

## 3. Cleaning Decisions and Gap Policy

- **Order of Operations:** Unphysical spikes were set to `NaN` FIRST, then timestamps were de-duplicated, then resampled. If spikes are not removed first, they corrupt duplicate averages and spread into adjacent bins during interpolation.
- **Resampling Method:** 1-minute arithmetic mean. Because sensors polled every 6–8 seconds (mean $\Delta t \approx 7.0\text{ s}$), sampling within each minute is nearly uniform; arithmetic mean differed from continuous time-weighted integration by a mean of only 3.04 W ($r = 0.9985$).
- **Gap Interpolation Threshold:** Analysis of 3.37 million raw intervals showed that 99.98% of valid sensor arrivals were $\le 120\text{ s}$ (2 minutes). Therefore:
  - Gaps $\le 3\text{ minutes}$ were linearly interpolated (**1,989 minutes filled**).
  - Outages $> 3\text{ minutes}$ were flagged as unfillable NaNs (**121,530 minutes flagged**).

---

## 4. Comparison with Official Strathclyde Cleaned Benchmark

Across **791,810 common valid minutes** between our cleaned 1-minute series and the official `CLEAN_House1.csv` resampled to 1 minute:
- **Washing Machine (`Appliance5`):** **MAE = 3.91 Watts** (39.5% of the channel's 9.9 W mean power), Pearson $r = \mathbf{0.83282}$.
- **Whole-Home `Aggregate`:** **MAE = 56.38 Watts** (11.7% of the channel's 481 W mean power), Pearson $r = \mathbf{0.86916}$.

*Why they differ:* The official Strathclyde cleaning pipeline forward-filled through multi-day outages and did not cap CT saturation spikes above 15 kW, whereas our pipeline left outages $> 3\text{ min}$ as uncorrupted NaNs.

---

## 5. Remaining Data Concerns

1. **Part-1 Zero Ambiguity:** Prior to October 2014, true sensor dropouts in House 1 cannot be distinguished from genuine 0 W idle states.
2. **Current Transformer Satiation:** When an electric shower and kettle operate simultaneously, the raw CT clamp saturates at 24 kW; peak transient demand during those rare moments is physically lost.
