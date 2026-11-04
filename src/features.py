"""
Feature engineering module for appliance disaggregation.
Computes compact rolling window, lag, difference, and cyclical temporal features
strictly from the whole-home Aggregate signal using float32 for strict memory safety.
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
    Computes a compact, physically motivated feature representation from the Aggregate power series.
    Window length: 61 minutes centered (-30 min to +30 min), derived from the empirical
    wash cycle duration (median 33-99 min).
    All features are strictly float32.
    """
    s = df[agg_col].astype(np.float32)
    
    feats = {}
    feats['agg_t'] = s
    
    # Rolling stats (centered)
    feats['agg_mean_15'] = s.rolling(window=15, center=True, min_periods=15).mean().astype(np.float32)
    feats['agg_std_15'] = s.rolling(window=15, center=True, min_periods=15).std().astype(np.float32)
    
    feats['agg_mean_31'] = s.rolling(window=31, center=True, min_periods=31).mean().astype(np.float32)
    feats['agg_std_31'] = s.rolling(window=31, center=True, min_periods=31).std().astype(np.float32)
    feats['agg_min_31'] = s.rolling(window=31, center=True, min_periods=31).min().astype(np.float32)
    feats['agg_max_31'] = s.rolling(window=31, center=True, min_periods=31).max().astype(np.float32)
    
    feats['agg_mean_61'] = s.rolling(window=61, center=True, min_periods=61).mean().astype(np.float32)
    feats['agg_std_61'] = s.rolling(window=61, center=True, min_periods=61).std().astype(np.float32)
    feats['agg_max_61'] = s.rolling(window=61, center=True, min_periods=61).max().astype(np.float32)
    
    # Lags and leads
    feats['agg_lag_30'] = s.shift(30).astype(np.float32)
    feats['agg_lag_15'] = s.shift(15).astype(np.float32)
    feats['agg_lag_5'] = s.shift(5).astype(np.float32)
    feats['agg_lead_5'] = s.shift(-5).astype(np.float32)
    feats['agg_lead_15'] = s.shift(-15).astype(np.float32)
    feats['agg_lead_30'] = s.shift(-30).astype(np.float32)
    
    # Transient deltas
    feats['agg_diff_past_5'] = (feats['agg_t'] - feats['agg_lag_5']).astype(np.float32)
    feats['agg_diff_lead_5'] = (feats['agg_lead_5'] - feats['agg_t']).astype(np.float32)
    feats['agg_diff_past_15'] = (feats['agg_t'] - feats['agg_lag_15']).astype(np.float32)
    
    # Cyclical calendar
    hour_val = (df.index.hour + df.index.minute / 60.0).astype(np.float32)
    feats['sin_hour'] = np.sin(2 * np.pi * hour_val / 24.0).astype(np.float32)
    feats['cos_hour'] = np.cos(2 * np.pi * hour_val / 24.0).astype(np.float32)
    feats['is_weekend'] = (df.index.dayofweek >= 5).astype(np.float32)
    
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
