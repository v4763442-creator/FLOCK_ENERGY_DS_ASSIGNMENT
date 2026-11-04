"""
Data cleaning and preprocessing pipeline for REFIT raw data (House 1).
Implements streaming, out-of-core data cleaning with exact physical spike filtering,
UK DST to UTC conversion, timestamp de-duplication, 1-minute resampling,
empirical gap interpolation (<= 3 min), and outage flagging (> 3 min).
"""
import csv
import json
from pathlib import Path
from typing import Dict, Tuple, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from config import DATA_DIR, PROCESSED_DATA_DIR, FIGURES_DIR, RESULTS_DIR


def clean_raw_house1_stream(data_dir: Path = DATA_DIR) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Streams RAW House 1 (Part 1 and Part 2) line by line, applying:
    1. Order of operations: Filter unphysical values to NaN FIRST (<0, IAM > 4kW, Agg > 15kW)
    2. Timezone conversion: Adjust British Summer Time (BST) to true continuous UTC
    3. De-duplication: Skip duplicate timestamps (keep first reading per second)
    4. 1-minute aggregation: Streaming arithmetic mean into 1-minute bins
    5. Regular grid reindexing, short gap linear interpolation (<= 3 min), and outage flagging (> 3 min).
    """
    p1_path = data_dir / "RAW_House1_Part1.csv"
    p2_path = data_dir / "RAW_House1_Part2.csv"
    
    channels = ['Aggregate'] + [f'Appliance{i}' for i in range(1, 10)]
    
    # Audit counters
    total_raw_rows = 0
    agg_spikes_gt_15kw = 0
    iam_spikes_gt_4kw = 0
    bst_rows_count = 0
    duplicate_rows = 0
    groups_conflicting = 0
    groups_exact = 0
    
    # Streaming state
    prev_unix = None
    prev_agg = None
    current_minute = None
    cur_sum = [0.0] * 10
    cur_count = [0] * 10
    minute_records = []
    
    boundary_time = "2014-10-01 01:27:07"
    
    # Process Part 1 then Part 2 sequentially
    file_configs = [
        (p1_path, True, 249600),   # Part 1: stop at boundary, row 249600 is Oct 2013 fallback
        (p2_path, False, None)     # Part 2: start after boundary
    ]
    
    for f_path, is_part1, fallback_row in file_configs:
        print(f"Streaming {f_path.name}...")
        with open(f_path, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            row_idx = 0
            for row in reader:
                row_idx += 1
                time_str = row[0]
                
                # Enforce boundary: Part 1 up to boundary, Part 2 after boundary
                if is_part1:
                    if time_str > boundary_time:
                        break
                else:
                    if time_str <= boundary_time:
                        continue
                        
                total_raw_rows += 1
                unix_raw = int(row[1])
                
                # Step 1: Filter unphysical values to NaN FIRST
                vals = []
                for i in range(2, 12):
                    raw_v = row[i]
                    if raw_v == '' or raw_v == 'NaN' or raw_v == 'nan':
                        vals.append(None)
                    else:
                        v = float(raw_v)
                        if i == 2:  # Aggregate
                            if v < 0:
                                vals.append(None)
                            elif v > 15000.0:
                                agg_spikes_gt_15kw += 1
                                vals.append(None)
                            else:
                                vals.append(v)
                        else:  # IAM single-appliance channels
                            if v < 0:
                                vals.append(None)
                            elif v > 4000.0:
                                iam_spikes_gt_4kw += 1
                                vals.append(None)
                            else:
                                vals.append(v)
                                
                # Step 2: Timezone correction to UTC
                if is_part1:
                    is_bst = (
                        (row_idx <= fallback_row) or
                        ('2014-03-30 02:00:00' <= time_str < '2014-10-26 02:00:00')
                    )
                else:
                    is_bst = (
                        ('2014-03-30 02:00:00' <= time_str < '2014-10-26 02:00:00') or
                        (time_str >= '2015-03-29 02:00:00')
                    )
                    
                if is_bst:
                    bst_rows_count += 1
                    unix_utc = unix_raw - 3600
                else:
                    unix_utc = unix_raw
                    
                # Step 3: Deduplication
                if unix_utc == prev_unix:
                    duplicate_rows += 1
                    if vals[0] != prev_agg:
                        groups_conflicting += 1
                    else:
                        groups_exact += 1
                    continue
                else:
                    prev_unix = unix_utc
                    prev_agg = vals[0]
                    
                # Step 4: 1-minute binning
                minute_epoch = (unix_utc // 60) * 60
                if current_minute is None:
                    current_minute = minute_epoch
                    
                if minute_epoch != current_minute:
                    # Emit previous minute
                    row_out = [current_minute]
                    for c_idx in range(10):
                        if cur_count[c_idx] > 0:
                            row_out.append(cur_sum[c_idx] / cur_count[c_idx])
                        else:
                            row_out.append(np.nan)
                    minute_records.append(row_out)
                    
                    # Reset accumulators
                    current_minute = minute_epoch
                    cur_sum = [0.0] * 10
                    cur_count = [0] * 10
                    
                # Accumulate valid readings
                for c_idx in range(10):
                    val = vals[c_idx]
                    if val is not None:
                        cur_sum[c_idx] += val
                        cur_count[c_idx] += 1
                        
    # Emit final minute
    if current_minute is not None:
        row_out = [current_minute]
        for c_idx in range(10):
            if cur_count[c_idx] > 0:
                row_out.append(cur_sum[c_idx] / cur_count[c_idx])
            else:
                row_out.append(np.nan)
        minute_records.append(row_out)
        
    print(f"Converting {len(minute_records):,} 1-minute records to DataFrame...")
    cols = ['minute_utc'] + channels
    df_raw_1min = pd.DataFrame(minute_records, columns=cols)
    del minute_records
    
    # Convert epoch seconds to UTC DatetimeIndex
    df_raw_1min['dt_utc'] = pd.to_datetime(df_raw_1min['minute_utc'], unit='s', utc=True)
    df_raw_1min = df_raw_1min.set_index('dt_utc').drop(columns=['minute_utc'])
    
    # Merge any minute bins that crossed the Part 1 / Part 2 boundary
    df_raw_1min = df_raw_1min.groupby(level=0).mean()
    
    # Step 5: Regular Grid Reindexing & Gap / Outage Handling
    print("Reindexing to continuous 1-minute grid...")
    full_idx = pd.date_range(start=df_raw_1min.index.min(), end=df_raw_1min.index.max(), freq='1min', tz='UTC')
    df_grid = df_raw_1min.reindex(full_idx)
    del df_raw_1min
    
    total_grid_minutes = len(df_grid)
    missing_before = int(df_grid['Aggregate'].isna().sum())
    
    # Identify outage runs: consecutive missing bins > 3 minutes (empirical threshold: 99.98% delta_t <= 2 min)
    is_missing = df_grid['Aggregate'].isna()
    # Group contiguous missing runs
    missing_runs = (~is_missing).cumsum()
    run_lengths = is_missing.groupby(missing_runs).transform('sum')
    outage_mask = is_missing & (run_lengths > 3)
    
    # Interpolate short gaps (limit = 3 minutes)
    df_clean = df_grid.interpolate(method='linear', limit=3)
    df_clean['outage_flag'] = outage_mask
    
    missing_after = int(df_clean['Aggregate'].isna().sum())
    short_gaps_filled = missing_before - missing_after
    coverage_pct = round((total_grid_minutes - missing_after) / total_grid_minutes * 100, 2)
    
    audit_stats = {
        "initial_raw_rows": total_raw_rows,
        "aggregate_spikes_gt_15kw": agg_spikes_gt_15kw,
        "iam_spikes_gt_4kw": iam_spikes_gt_4kw,
        "bst_rows_adjusted_utc": bst_rows_count,
        "duplicate_rows_skipped": duplicate_rows,
        "duplicate_groups_exact_repeats": groups_exact,
        "duplicate_groups_conflicting": groups_conflicting,
        "total_1min_grid_minutes": total_grid_minutes,
        "missing_minutes_before_fill": missing_before,
        "short_gap_minutes_filled": short_gaps_filled,
        "outage_minutes_flagged": int(outage_mask.sum()),
        "missing_minutes_remaining": missing_after,
        "percent_coverage": coverage_pct
    }
    
    return df_clean, audit_stats


def resample_official_clean_house1(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """
    Streams official CLEAN_House1.csv line by line and computes 1-minute mean
    for Aggregate and Appliance5 (Washing Machine) for the sanity check.
    """
    clean_path = data_dir / "CLEAN_House1.csv"
    print(f"Streaming official {clean_path.name} to 1-minute bins...")
    
    current_minute = None
    cur_sum = [0.0, 0.0]  # [Aggregate, Appliance5]
    cur_count = [0, 0]
    records = []
    
    with open(clean_path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        # Find column indices
        agg_idx = header.index('Aggregate')
        app5_idx = header.index('Appliance5')
        unix_idx = header.index('Unix')
        
        for row in reader:
            unix_utc = int(row[unix_idx])
            v_agg = float(row[agg_idx]) if row[agg_idx] != '' else None
            v_app5 = float(row[app5_idx]) if row[app5_idx] != '' else None
            
            minute_epoch = (unix_utc // 60) * 60
            if current_minute is None:
                current_minute = minute_epoch
                
            if minute_epoch != current_minute:
                # Emit
                m_agg = (cur_sum[0] / cur_count[0]) if cur_count[0] > 0 else np.nan
                m_wm = (cur_sum[1] / cur_count[1]) if cur_count[1] > 0 else np.nan
                records.append([current_minute, m_agg, m_wm])
                
                current_minute = minute_epoch
                cur_sum = [0.0, 0.0]
                cur_count = [0, 0]
                
            if v_agg is not None:
                cur_sum[0] += v_agg
                cur_count[0] += 1
            if v_app5 is not None:
                cur_sum[1] += v_app5
                cur_count[1] += 1
                
    if current_minute is not None:
        m_agg = (cur_sum[0] / cur_count[0]) if cur_count[0] > 0 else np.nan
        m_wm = (cur_sum[1] / cur_count[1]) if cur_count[1] > 0 else np.nan
        records.append([current_minute, m_agg, m_wm])
        
    df_off = pd.DataFrame(records, columns=['minute_utc', 'Aggregate_off', 'Appliance5_off'])
    df_off['dt_utc'] = pd.to_datetime(df_off['minute_utc'], unit='s', utc=True)
    df_off = df_off.set_index('dt_utc').drop(columns=['minute_utc'])
    df_off = df_off.groupby(level=0).mean()
    return df_off


def compare_with_official(our_df: pd.DataFrame, official_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes MAE, RMSE, Pearson correlation and energy difference between
    our cleaned 1-minute series and the official cleaned 1-minute series.
    """
    common_idx = our_df.index.intersection(official_df.index)
    
    comp = pd.DataFrame({
        'our_agg': our_df.loc[common_idx, 'Aggregate'],
        'off_agg': official_df.loc[common_idx, 'Aggregate_off'],
        'our_wm': our_df.loc[common_idx, 'Appliance5'],
        'off_wm': official_df.loc[common_idx, 'Appliance5_off']
    }).dropna()
    
    agg_diff = comp['our_agg'] - comp['off_agg']
    wm_diff = comp['our_wm'] - comp['off_wm']
    
    results = {
        "common_valid_minutes": len(comp),
        "aggregate_mae_watts": round(float(agg_diff.abs().mean()), 2),
        "aggregate_rmse_watts": round(float(np.sqrt((agg_diff**2).mean())), 2),
        "aggregate_pearson_corr": round(float(comp['our_agg'].corr(comp['off_agg'])), 5),
        "washing_machine_mae_watts": round(float(wm_diff.abs().mean()), 2),
        "washing_machine_rmse_watts": round(float(np.sqrt((wm_diff**2).mean())), 2),
        "washing_machine_pearson_corr": round(float(comp['our_wm'].corr(comp['off_wm'])), 5)
    }
    return results
