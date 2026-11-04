"""
End-to-end execution script for Problem 2: Washing-Machine EDA
- Evaluates data quality, forward-fill runs, and Issues=1 rows across Houses 1, 2, 3, 5 (and House 4)
- Conducts cycle-detection parameter sensitivity analysis
- Extracts cycles and computes duration, peak, and kWh distributions
- Generates usage patterns (diurnal and day-of-week)
- Generates mandatory figures 3, 4, and 5
- Saves results to results/
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from config import PROCESSED_DATA_DIR, FIGURES_DIR, RESULTS_DIR, WM_COLUMNS
from src.cycles import detect_cycles, run_cycle_sensitivity_analysis


def run_eda():
    print("=" * 60)
    print("FLOCK ENERGY TAKE-HOME: PROBLEM 2 WASHING MACHINE EDA")
    print("=" * 60)
    
    houses = [1, 2, 3, 5]
    eda_summary = {}
    house_comparison_rows = []
    all_cycles_dict = {}
    
    # 1. Quality & Availability analysis per house
    print("\n--- 1. Data Availability, Off-Time, Forward-Fill, and Issues ---")
    for h in houses:
        p_path = PROCESSED_DATA_DIR / f"clean_house{h}_1min.parquet"
        df = pd.read_parquet(p_path)
        wm_col = WM_COLUMNS[h]
        
        total_mins = len(df)
        start_date = str(df.index.min().date())
        end_date = str(df.index.max().date())
        total_days = round((df.index.max() - df.index.min()).total_seconds() / 86400.0, 1)
        
        # Missing values in WM
        missing_mins = int(df[wm_col].isna().sum())
        missing_pct = round(missing_mins / total_mins * 100, 2)
        
        # Off-state (<= 15 W)
        valid_wm = df[wm_col].dropna()
        off_mins = int((valid_wm <= 15.0).sum())
        off_pct = round(off_mins / len(valid_wm) * 100, 2)
        
        # Issues == 1
        issues_mins = int((df['Issues'] > 0).sum()) if 'Issues' in df.columns else 0
        issues_pct = round(issues_mins / total_mins * 100, 2)
        
        # Forward-fill artifacts: consecutive constant non-zero runs > 30 minutes
        is_const = (valid_wm == valid_wm.shift(1)) & (valid_wm > 15.0)
        const_blocks = (~is_const).cumsum()
        const_run_lengths = is_const.groupby(const_blocks).transform('sum')
        long_runs_count = int((const_run_lengths > 30).sum())
        
        eda_summary[f"House_{h}"] = {
            "channel": wm_col,
            "start_date": start_date,
            "end_date": end_date,
            "total_days": total_days,
            "total_minutes": total_mins,
            "missing_minutes": missing_mins,
            "missing_percent": missing_pct,
            "off_minutes_le_15w": off_mins,
            "off_percent": off_pct,
            "issues_count": issues_mins,
            "issues_percent": issues_pct,
            "forward_fill_long_run_minutes": long_runs_count
        }
        print(f"House {h} ({wm_col}): {start_date} to {end_date} ({total_days} days) | Off: {off_pct}% | Issues=1: {issues_pct}% | Missing: {missing_pct}%")
        
    # Also evaluate House 4 WM1 and WM2 separately
    print("\n--- Evaluating House 4 (Separate WM1 and WM2) ---")
    df4 = pd.read_parquet(PROCESSED_DATA_DIR / "clean_house4_1min.parquet")
    for wm_col, name in [('Appliance4', 'House 4 WM1 (Servis 6065)'), ('Appliance5', 'House 4 WM2 (Zanussi Z917)')]:
        valid_wm = df4[wm_col].dropna()
        off_pct = round((valid_wm <= 15.0).sum() / len(valid_wm) * 100, 2)
        c_list = detect_cycles(valid_wm, on_threshold=15.0, min_peak=500.0, min_duration=15, max_pause_minutes=10)
        print(f"  {name}: Off={off_pct}% | Detected Cycles={len(c_list)}")
        eda_summary[name] = {
            "channel": wm_col,
            "off_percent": off_pct,
            "cycles_detected": len(c_list),
            "reason_excluded_from_model": "House 4 contains two washing machines in the same aggregate load, making the single-appliance NILM target ambiguous."
        }

    # 2. Cycle-Rule Parameter Sensitivity Analysis (House 1)
    print("\n--- 2. Parameter Sensitivity Analysis on House 1 ---")
    df1 = pd.read_parquet(PROCESSED_DATA_DIR / "clean_house1_1min.parquet")
    sens_df = run_cycle_sensitivity_analysis(
        df1['Appliance5'],
        peak_thresholds=[200.0, 300.0, 500.0],
        merge_gaps=[5, 10, 15],
        min_durations=[10, 15, 20],
        on_threshold=15.0
    )
    sens_path = RESULTS_DIR / "problem2_cycle_sensitivity.csv"
    sens_df.to_csv(sens_path, index=False)
    print(f"Saved sensitivity analysis table to {sens_path.name}")
    print("Sample sensitivity rows:")
    print(sens_df.head(6))

    # 3. Detect Cycles with Justified Parameters (min_peak=500W, merge_gap=10min, min_dur=15min)
    print("\n--- 3. Cycle Extraction Across Selected Households ---")
    for h in houses:
        df = pd.read_parquet(PROCESSED_DATA_DIR / f"clean_house{h}_1min.parquet")
        wm_col = WM_COLUMNS[h]
        cycles = detect_cycles(
            df[wm_col],
            on_threshold=15.0,
            min_peak=500.0,
            min_duration=15,
            max_pause_minutes=10
        )
        all_cycles_dict[h] = cycles
        c_count = len(cycles)
        
        durations = [c['duration_min'] for c in cycles]
        peaks = [c['peak_watts'] for c in cycles]
        energies = [c['energy_kwh'] for c in cycles]
        total_kwh = round(float(np.sum(energies)), 2)
        
        weeks = eda_summary[f"House_{h}"]["total_days"] / 7.0
        cycles_per_week = round(c_count / weeks, 2)
        
        row_stat = {
            "house": h,
            "appliance_channel": wm_col,
            "cycle_count": c_count,
            "cycles_per_week": cycles_per_week,
            "duration_mean_min": round(float(np.mean(durations)), 1),
            "duration_median_min": round(float(np.median(durations)), 1),
            "duration_iqr_min": round(float(np.percentile(durations, 75) - np.percentile(durations, 25)), 1),
            "peak_mean_watts": round(float(np.mean(peaks)), 1),
            "peak_max_watts": round(float(np.max(peaks)), 1),
            "energy_per_cycle_mean_kwh": round(float(np.mean(energies)), 3),
            "energy_per_cycle_median_kwh": round(float(np.median(energies)), 3),
            "total_consumption_kwh": total_kwh
        }
        house_comparison_rows.append(row_stat)
        eda_summary[f"House_{h}"]["cycle_stats"] = row_stat
        print(f"House {h}: {c_count} cycles ({cycles_per_week} cycles/wk) | Median Duration: {row_stat['duration_median_min']} min | Median Energy: {row_stat['energy_per_cycle_median_kwh']} kWh")

    comp_df = pd.DataFrame(house_comparison_rows)
    comp_path = RESULTS_DIR / "problem2_house_comparison.csv"
    comp_df.to_csv(comp_path, index=False)
    print(f"Saved cross-house comparison table to {comp_path.name}")
    
    with open(RESULTS_DIR / "problem2_eda.json", "w") as f:
        json.dump(eda_summary, f, indent=2)

    # 4. Usage Patterns by Hour of Day and Day of Week
    print("\n--- 4. Computing Diurnal and Weekly Usage Patterns ---")
    diurnal_stats = {}
    weekly_stats = {}
    for h in houses:
        c_list = all_cycles_dict[h]
        total_days = eda_summary[f"House_{h}"]["total_days"]
        
        # Hourly counts normalized by total days
        hr_counts = pd.Series([c['start_hour'] for c in c_list]).value_counts().reindex(range(24), fill_value=0)
        hr_norm = (hr_counts / total_days * 100.0).round(3) # cycles per 100 days
        diurnal_stats[f"House_{h}"] = hr_norm.to_dict()
        
        # Day of week counts normalized by total weeks
        dow_counts = pd.Series([c['start_dayofweek'] for c in c_list]).value_counts().reindex(range(7), fill_value=0)
        dow_norm = (dow_counts / (total_days / 7.0)).round(2) # cycles per week
        weekly_stats[f"House_{h}"] = dow_norm.to_dict()

    with open(RESULTS_DIR / "problem2_usage_patterns.json", "w") as f:
        json.dump({"diurnal_per_100_days": diurnal_stats, "weekly_cycles_per_day": weekly_stats}, f, indent=2)

    # 5. Mandatory Figures
    print("\n--- 5. Generating Mandatory Figures ---")
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # FIGURE 3: Representative 24-hour trace (Aggregate + Washing Machine)
    # Pick 2013-11-09 for House 1: a clear Saturday with morning wash cycles
    df1 = pd.read_parquet(PROCESSED_DATA_DIR / "clean_house1_1min.parquet")
    t24_start = '2013-11-09 00:00:00'
    t24_end = '2013-11-09 23:59:00'
    s24 = df1.loc[t24_start:t24_end]
    
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(s24.index, s24['Aggregate'], color='#7f8c8d', lw=1.2, alpha=0.7, label='Whole-Home Aggregate')
    ax.plot(s24.index, s24['Appliance5'], color='#27ae60', lw=2.0, label='Washing Machine (Appliance 5)')
    ax.fill_between(s24.index, 0, s24['Appliance5'], color='#2ecc71', alpha=0.3)
    ax.set_title('Representative 24-Hour Electricity Profile: House 1 (Saturday 2013-11-09)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Active Power (Watts)', fontsize=11)
    ax.set_xlabel('UTC Time', fontsize=11)
    ax.legend(loc='upper right', frameon=True)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig3_path = FIGURES_DIR / "fig3_rep_24h_trace.png"
    plt.savefig(fig3_path, dpi=200)
    plt.close()
    print(f"Saved {fig3_path.name}")
    
    # FIGURE 4: Detected Washing Machine Cycles Zoom
    # Zoom into House 1 and House 2 cycles showing water heating and agitation phases
    fig, axes = plt.subplots(2, 1, figsize=(13, 8), sharey=True)
    
    # House 1 cycle
    c1 = all_cycles_dict[1][10] # 11th cycle
    s_h1 = df1['Appliance5'].loc[c1['start_time'] - pd.Timedelta(minutes=15) : c1['end_time'] + pd.Timedelta(minutes=15)]
    axes[0].plot(s_h1.index, s_h1.values, color='#2980b9', lw=2.0, label=f'House 1 Cycle (Dur: {c1["duration_min"]}m, Peak: {c1["peak_watts"]}W, Energy: {c1["energy_kwh"]}kWh)')
    axes[0].axvspan(c1['start_time'], c1['end_time'], color='#3498db', alpha=0.15, label='Detected Active Cycle Window')
    axes[0].axhline(15, color='orange', ls='--', lw=1.0, label='Standby Threshold (15 W)')
    axes[0].axhline(500, color='red', ls=':', lw=1.0, label='Min Peak Threshold (500 W)')
    axes[0].set_title(f'Detected Wash Cycle 1: House 1 (Heating Element ~2.2 kW + Agitation & Spin Pulses)', fontsize=11, fontweight='bold')
    axes[0].set_ylabel('Power (Watts)', fontsize=10)
    axes[0].legend(loc='upper right')
    axes[0].grid(True, alpha=0.3)
    
    # House 2 cycle
    df2 = pd.read_parquet(PROCESSED_DATA_DIR / "clean_house2_1min.parquet")
    c2 = all_cycles_dict[2][15]
    s_h2 = df2['Appliance2'].loc[c2['start_time'] - pd.Timedelta(minutes=15) : c2['end_time'] + pd.Timedelta(minutes=15)]
    axes[1].plot(s_h2.index, s_h2.values, color='#8e44ad', lw=2.0, label=f'House 2 Cycle (Dur: {c2["duration_min"]}m, Peak: {c2["peak_watts"]}W, Energy: {c2["energy_kwh"]}kWh)')
    axes[1].axvspan(c2['start_time'], c2['end_time'], color='#9b59b6', alpha=0.15, label='Detected Active Cycle Window')
    axes[1].axhline(15, color='orange', ls='--', lw=1.0)
    axes[1].axhline(500, color='red', ls=':', lw=1.0)
    axes[1].set_title(f'Detected Wash Cycle 2: House 2 (Initial Heating Burst ~2.0 kW + Periodic Drum Rotation)', fontsize=11, fontweight='bold')
    axes[1].set_ylabel('Power (Watts)', fontsize=10)
    axes[1].set_xlabel('UTC Time', fontsize=10)
    axes[1].legend(loc='upper right')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig4_path = FIGURES_DIR / "fig4_detected_cycles_zoom.png"
    plt.savefig(fig4_path, dpi=200)
    plt.close()
    print(f"Saved {fig4_path.name}")
    
    # FIGURE 5: Cross-House Comparison Boxplots
    # Duration, Peak Power, Energy per Cycle across Houses 1, 2, 3, 5
    cycle_records_for_df = []
    for h in houses:
        for c in all_cycles_dict[h]:
            cycle_records_for_df.append({
                "House": f"House {h}",
                "Duration (min)": c['duration_min'],
                "Peak Power (W)": c['peak_watts'],
                "Energy (kWh)": c['energy_kwh']
            })
    cdf = pd.DataFrame(cycle_records_for_df)
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # (a) Duration
    box1 = [cdf[cdf['House'] == f"House {h}"]['Duration (min)'].values for h in houses]
    axes[0].boxplot(box1, tick_labels=[f"House {h}" for h in houses], patch_artist=True, boxprops=dict(facecolor='#3498db', alpha=0.6))
    axes[0].set_title('Cycle Duration Distribution', fontsize=11, fontweight='bold')
    axes[0].set_ylabel('Minutes', fontsize=10)
    axes[0].grid(True, alpha=0.3)
    
    # (b) Peak Power
    box2 = [cdf[cdf['House'] == f"House {h}"]['Peak Power (W)'].values for h in houses]
    axes[1].boxplot(box2, tick_labels=[f"House {h}" for h in houses], patch_artist=True, boxprops=dict(facecolor='#e67e22', alpha=0.6))
    axes[1].set_title('Cycle Peak Power Distribution', fontsize=11, fontweight='bold')
    axes[1].set_ylabel('Watts', fontsize=10)
    axes[1].grid(True, alpha=0.3)
    
    # (c) Energy per cycle
    box3 = [cdf[cdf['House'] == f"House {h}"]['Energy (kWh)'].values for h in houses]
    axes[2].boxplot(box3, tick_labels=[f"House {h}" for h in houses], patch_artist=True, boxprops=dict(facecolor='#2ecc71', alpha=0.6))
    axes[2].set_title('Energy per Cycle Distribution', fontsize=11, fontweight='bold')
    axes[2].set_ylabel('kWh per cycle', fontsize=10)
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig5_path = FIGURES_DIR / "fig5_cross_house_comparison.png"
    plt.savefig(fig5_path, dpi=200)
    plt.close()
    print(f"Saved {fig5_path.name}")
    
    print("\nProblem 2 execution completed successfully!")

if __name__ == "__main__":
    run_eda()
