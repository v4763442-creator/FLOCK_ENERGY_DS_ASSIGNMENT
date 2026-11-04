"""
Feature engineering module for appliance disaggregation.
Computes a compact set of ~10 aggregate-only features:
- Instantaneous aggregate power
- 1-minute difference in aggregate
- Centered rolling mean, standard deviation, and maximum over 15, 60, and 120 minutes.
All features use float32 for strict memory safety.
"""
from typing import Tuple
import gc
import numpy as np
import pandas as pd


def compute_aggregate_features(
    df: pd.DataFrame, 
    agg_col: str = 'Aggregate',
    target_col: str = None
) -> Tuple[pd.DataFrame, pd.Series, pd.Index]:
    """
    Computes a simplified, compact feature set from the Aggregate power series.
    
    Features (11 total):
    1. agg_t: instantaneous aggregate power at minute t
    2. agg_diff_1m: 1-minute power delta (t - (t-1))
    3-5. agg_mean_15, agg_std_15, agg_max_15 (15-min centered window)
    6-8. agg_mean_60, agg_std_60, agg_max_60 (60-min centered window, matching typical wash duration)
    9-11. agg_mean_120, agg_std_120, agg_max_120 (120-min centered window, enveloping longest wash cycles)
    
    Note on centered windows:
    Centered windows use samples from t - W/2 to t + W/2. Using future aggregate readings
    is standard and valid in offline NILM (energy feedback, auditing, bill breakdown),
    where the entire day's smart-meter data is already available at analysis time.
    """
    s = df[agg_col].astype(np.float32)
    
    feats = {}
    feats['agg_t'] = s
    feats['agg_diff_1m'] = (s - s.shift(1)).astype(np.float32)
    
    for w in [15, 60, 120]:
        feats[f'agg_mean_{w}'] = s.rolling(window=w, center=True, min_periods=w).mean().astype(np.float32)
        feats[f'agg_std_{w}'] = s.rolling(window=w, center=True, min_periods=w).std().astype(np.float32)
        feats[f'agg_max_{w}'] = s.rolling(window=w, center=True, min_periods=w).max().astype(np.float32)
        
    X = pd.DataFrame(feats, index=df.index)
    del feats
    
    if target_col is not None and target_col in df.columns:
        y = df[target_col].astype(np.float32)
    else:
        y = pd.Series(0.0, index=df.index, dtype=np.float32)
        
    valid_mask = ~X.isna().any(axis=1) & ~y.isna()
    if 'outage_flag' in df.columns:
        valid_mask = valid_mask & (~df['outage_flag'])
        
    X_clean = X.loc[valid_mask]
    y_clean = y.loc[valid_mask]
    del X, y, valid_mask
    gc.collect()
    
    return X_clean, y_clean, X_clean.index
