"""
Washing machine cycle detection, extraction, and sensitivity analysis.
"""
from typing import List, Dict, Tuple, Any
import numpy as np
import pandas as pd


def detect_cycles(
    series: pd.Series,
    on_threshold: float = 15.0,
    min_peak: float = 500.0,
    min_duration: int = 15,
    max_pause_minutes: int = 10
) -> List[Dict[str, Any]]:
    """
    Identifies discrete washing machine cycles from a 1-minute power series.
    
    Rule definition:
    1. A sample is active if Power > on_threshold (15 W, above standby/parasitic drain).
    2. Consecutive active samples form active segments.
    3. Active segments separated by an inactive gap <= max_pause_minutes (wash-to-rinse pauses)
       are merged into a single candidate cycle.
    4. Candidate cycles are retained only if:
       - Total duration >= min_duration (minutes)
       - Maximum instantaneous power >= min_peak (W), confirming heating element or spin motor.
    """
    # Fill NaN with 0 for cycle detection
    s = series.fillna(0.0)
    is_active = (s > on_threshold).astype(int)
    
    if is_active.sum() == 0:
        return []
        
    # Group contiguous blocks of same state
    block_id = (is_active != is_active.shift(1)).cumsum()
    blocks = s.groupby(block_id)
    
    # Collect raw active intervals: (start_idx, end_idx)
    raw_active = []
    for bid, group in blocks:
        if is_active.loc[group.index[0]] == 1:
            raw_active.append((group.index[0], group.index[-1]))
            
    if not raw_active:
        return []
        
    # Merge pauses <= max_pause_minutes
    merged_intervals = []
    cur_start, cur_end = raw_active[0]
    
    for next_start, next_end in raw_active[1:]:
        pause_mins = (next_start - cur_end).total_seconds() / 60.0 - 1.0
        if pause_mins <= max_pause_minutes:
            cur_end = next_end
        else:
            merged_intervals.append((cur_start, cur_end))
            cur_start, cur_end = next_start, next_end
    merged_intervals.append((cur_start, cur_end))
    
    # Filter by min_duration and min_peak
    cycles = []
    for c_id, (start, end) in enumerate(merged_intervals, 1):
        c_series = s.loc[start:end]
        duration = len(c_series)  # 1-minute samples
        peak = float(c_series.max())
        
        if duration >= min_duration and peak >= min_peak:
            # Energy in kWh: sum(P_W * 1 min) / (60 min/h * 1000 W/kW)
            energy_kwh = float(c_series.sum() / 60000.0)
            mean_p = float(c_series.mean())
            
            cycles.append({
                "cycle_id": c_id,
                "start_time": start,
                "end_time": end,
                "duration_min": duration,
                "peak_watts": round(peak, 1),
                "mean_watts": round(mean_p, 1),
                "energy_kwh": round(energy_kwh, 4),
                "start_hour": start.hour,
                "start_dayofweek": start.dayofweek, # 0=Mon, 6=Sun
                "start_day_name": start.day_name()
            })
            
    return cycles


def run_cycle_sensitivity_analysis(
    series: pd.Series,
    peak_thresholds: List[float] = [200.0, 300.0, 500.0],
    merge_gaps: List[int] = [5, 10, 15],
    min_durations: List[int] = [10, 15, 20],
    on_threshold: float = 15.0
) -> pd.DataFrame:
    """
    Evaluates sensitivity of detected cycle counts and properties
    across parameter permutations.
    """
    results = []
    for p in peak_thresholds:
        for g in merge_gaps:
            for d in min_durations:
                cycles = detect_cycles(
                    series,
                    on_threshold=on_threshold,
                    min_peak=p,
                    min_duration=d,
                    max_pause_minutes=g
                )
                c_count = len(cycles)
                if c_count > 0:
                    durations = [c['duration_min'] for c in cycles]
                    energies = [c['energy_kwh'] for c in cycles]
                    peaks = [c['peak_watts'] for c in cycles]
                    mean_dur = round(float(np.mean(durations)), 1)
                    median_dur = round(float(np.median(durations)), 1)
                    mean_kwh = round(float(np.mean(energies)), 3)
                    mean_peak = round(float(np.mean(peaks)), 1)
                else:
                    mean_dur, median_dur, mean_kwh, mean_peak = 0, 0, 0, 0
                    
                results.append({
                    "min_peak_watts": p,
                    "merge_gap_min": g,
                    "min_duration_min": d,
                    "cycle_count": c_count,
                    "mean_duration_min": mean_dur,
                    "median_duration_min": median_dur,
                    "mean_energy_kwh": mean_kwh,
                    "mean_peak_watts": mean_peak
                })
    return pd.DataFrame(results)
