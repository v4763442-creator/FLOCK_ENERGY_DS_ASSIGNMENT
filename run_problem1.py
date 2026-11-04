"""
End-to-end execution script for Problem 1:
- Streams RAW House 1 (Part 1 and Part 2) with zero memory overhead
- Executes physical spike filtering, UTC alignment, deduplication, 1-min resampling, and gap/outage handling
- Saves cleaned dataset to data/processed/clean_raw_house1_1min.parquet
- Runs sanity check against official Clean House 1
- Generates required figures in figures/
- Saves summary metrics to results/
"""
import json
import gc
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from config import DATA_DIR, PROCESSED_DATA_DIR, FIGURES_DIR, RESULTS_DIR
from src.cleaning import (
    clean_raw_house1_stream,
    resample_official_clean_house1,
    compare_with_official
)


def run_pipeline():
    print("=" * 60)
    print("FLOCK ENERGY TAKE-HOME: PROBLEM 1 PIPELINE")
    print("=" * 60)
    
    # 1. Clean RAW House 1 via stream
    clean_1min, audit_stats = clean_raw_house1_stream(data_dir=DATA_DIR)
    
    print("\n--- Cleaning Audit Summary ---")
    for k, v in audit_stats.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v:,}")
            
    # Save cleaned 1-min dataset
    processed_path = PROCESSED_DATA_DIR / "clean_raw_house1_1min.parquet"
    print(f"\nSaving cleaned 1-minute data to {processed_path}...")
    clean_1min.to_parquet(processed_path)
    print(f"Successfully saved {len(clean_1min):,} 1-minute rows.")
    
    # Save JSON and CSV summaries
    json_path = RESULTS_DIR / "problem1_summary.json"
    with open(json_path, "w") as f:
        json.dump(audit_stats, f, indent=2)
    print(f"Saved audit metrics to {json_path}")
    
    summary_df = pd.DataFrame([audit_stats]).T.reset_index()
    summary_df.columns = ["Metric", "Value"]
    csv_path = RESULTS_DIR / "problem1_summary.csv"
    summary_df.to_csv(csv_path, index=False)
    print(f"Saved audit table to {csv_path}")
    
    # 2. Sanity check: Stream official clean House 1 and compare
    print("\n--- Sanity Check: Comparing with Official CLEAN House 1 ---")
    official_1min = resample_official_clean_house1(data_dir=DATA_DIR)
    comp_results = compare_with_official(clean_1min, official_1min)
    
    comp_json_path = RESULTS_DIR / "problem1_official_comparison.json"
    with open(comp_json_path, "w") as f:
        json.dump(comp_results, f, indent=2)
    print("Comparison results against official Strathclyde cleaning:")
    print(json.dumps(comp_results, indent=2))
    
    # 3. Generate Visualizations
    print("\n--- Generating Visualizations ---")
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # Figure 1: 3-panel zoom trace around active cycles and gap
    # 2013-11-09: active Saturday morning wash cycles and tumble dryer runs
    z_start = '2013-11-09 06:00:00'
    z_end = '2013-11-09 18:00:00'
    slice_clean = clean_1min.loc[z_start:z_end]
    
    fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
    
    # (a) Aggregate
    axes[0].plot(slice_clean.index, slice_clean['Aggregate'], color='#1f77b4', lw=1.5, label='Cleaned Aggregate (1-min)')
    axes[0].set_ylabel('Power (W)', fontsize=11)
    axes[0].set_title('House 1 Power Traces on 2013-11-09: Cleaned 1-Minute Resolution', fontsize=13, fontweight='bold')
    axes[0].legend(loc='upper right')
    axes[0].grid(True, alpha=0.3)
    
    # (b) Appliance 5: Washing Machine
    axes[1].plot(slice_clean.index, slice_clean['Appliance5'], color='#2ca02c', lw=1.5, label='Appliance 5: Washing Machine (Beko WMC6140)')
    axes[1].set_ylabel('Power (W)', fontsize=11)
    axes[1].legend(loc='upper right')
    axes[1].grid(True, alpha=0.3)
    
    # (c) Appliance 4: Tumble Dryer (Creda T522VW)
    axes[2].plot(slice_clean.index, slice_clean['Appliance4'], color='#d62728', lw=1.5, label='Appliance 4: Tumble Dryer (Creda T522VW)')
    axes[2].set_ylabel('Power (W)', fontsize=11)
    axes[2].set_xlabel('UTC Timestamp', fontsize=11)
    axes[2].legend(loc='upper right')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig1_path = FIGURES_DIR / "fig1_cleaning_trace_zoom.png"
    plt.savefig(fig1_path, dpi=200)
    plt.close()
    print(f"Saved {fig1_path.name}")
    
    # Figure 2: Outage & Gap Handling Demonstration
    # Pick a real outage event in the dataset
    outage_pts = clean_1min.index[clean_1min['outage_flag']]
    if len(outage_pts) > 0:
        sample_pt = outage_pts[200]
        o_start = sample_pt - pd.Timedelta(hours=4)
        o_end = sample_pt + pd.Timedelta(hours=8)
        o_slice = clean_1min.loc[o_start:o_end]
        
        fig, ax = plt.subplots(figsize=(13, 5))
        # Plot valid signal
        ax.plot(o_slice.index, o_slice['Aggregate'], label='Aggregate Power (Short gaps <=3m filled)', color='#1f77b4', lw=1.5)
        
        # Highlight outage region
        flagged_points = o_slice[o_slice['outage_flag']]
        if len(flagged_points) > 0:
            ax.axvspan(flagged_points.index[0], flagged_points.index[-1], color='#e74c3c', alpha=0.25, label='Flagged Outage (>3 min unfillable outage)')
            
        ax.set_title('Demonstration of Gap Handling: Short Gaps Interpolated vs Long Outages Flagged', fontsize=12, fontweight='bold')
        ax.set_ylabel('Aggregate Power (W)', fontsize=11)
        ax.set_xlabel('UTC Timestamp', fontsize=11)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        fig2_path = FIGURES_DIR / "fig2_outage_handling.png"
        plt.savefig(fig2_path, dpi=200)
        plt.close()
        print(f"Saved {fig2_path.name}")
        
    print("\nProblem 1 pipeline execution completed successfully!")

if __name__ == "__main__":
    run_pipeline()
