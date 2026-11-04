"""
Machine Learning models and baselines for Appliance Disaggregation (NILM).
Includes:
- AlwaysOffBaseline: Predicts 0 Watts unconditionally.
- HourOfDayMeanBaseline: Predicts mean training power for each hour (0-23).
- WashingMachineDisaggregator: Native HistGradientBoostingRegressor tree ensemble
  predicting appliance power from 11 compact aggregate features.
"""
from typing import Dict, Tuple, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from config import PROCESSED_DATA_DIR, RESULTS_DIR, WM_COLUMNS
from src.features import compute_aggregate_features
from src.evaluation import evaluate_disaggregation


class AlwaysOffBaseline:
    """
    Mandatory baseline that unconditionally predicts 0 Watts for all time steps.
    Represents the naive zero-intelligence baseline in sparse load NILM.
    """
    def __init__(self):
        self.is_fitted = False

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "AlwaysOffBaseline":
        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.zeros(len(X), dtype=np.float32)


class HourOfDayMeanBaseline:
    """
    Diurnal usage profile baseline that predicts the average training-set power
    for each hour of the day (0 to 23).
    Fit strictly on training blocks only (zero future leakage).
    """
    def __init__(self):
        self.hour_means: Dict[int, float] = {}

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "HourOfDayMeanBaseline":
        hours = X.index.hour
        df_tmp = pd.DataFrame({"hour": hours, "power": y})
        self.hour_means = df_tmp.groupby("hour")["power"].mean().to_dict()
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        hours = X.index.hour
        preds = np.array([self.hour_means.get(h, 0.0) for h in hours], dtype=np.float32)
        return preds


class WashingMachineDisaggregator:
    """
    Native non-linear tree ensemble for washing machine energy disaggregation.
    Uses HistGradientBoostingRegressor with default settings (max_iter=100, max_depth=6).
    
    In plain English: A sequence of small decision trees built one after another,
    where each subsequent tree corrects the residual mistakes of earlier trees.
    Predictions are clipped at 0 Watts (appliances cannot produce negative energy).
    """
    def __init__(self, max_iter: int = 100, max_depth: int = 6, random_state: int = 42):
        self.model = HistGradientBoostingRegressor(
            max_iter=max_iter,
            max_depth=max_depth,
            random_state=random_state
        )
        self.feature_names: List[str] = []

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "WashingMachineDisaggregator":
        self.feature_names = list(X.columns)
        # Ensure float32 to prevent unnecessary memory overhead
        X_arr = np.asarray(X, dtype=np.float32)
        y_arr = np.asarray(y, dtype=np.float32)
        self.model.fit(X_arr, y_arr)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        X_arr = np.asarray(X, dtype=np.float32)
        preds = self.model.predict(X_arr)
        # Physical constraint: power cannot be negative
        return np.clip(preds, 0.0, None).astype(np.float32)


def get_chronological_splits(
    df: pd.DataFrame,
    agg_col: str,
    target_col: str,
    train_frac: float = 0.60,
    val_frac: float = 0.20,
    buffer_minutes: int = 180,
    subsample_train: int = 2
) -> Tuple[pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray]:
    """
    Extracts 11 aggregate features and splits into chronological blocks
    (60% Train, 20% Val, 20% Test) separated by an excised 3-hour (180 min) buffer gap.
    """
    X, y, _ = compute_aggregate_features(df, agg_col=agg_col, target_col=target_col)
    n = len(X)
    
    train_end = int(n * train_frac)
    val_start = train_end + buffer_minutes
    val_end = int(n * (train_frac + val_frac))
    test_start = val_end + buffer_minutes
    
    # Subsample training data to maintain low RAM footprint (< 150 MB)
    X_train = X.iloc[:train_end:subsample_train].copy()
    y_train = y.iloc[:train_end:subsample_train].copy().values
    
    X_val = X.iloc[val_start:val_end:subsample_train].copy()
    y_val = y.iloc[val_start:val_end:subsample_train].copy().values
    
    # Test set is kept at full 1-minute resolution (no subsampling)
    X_test = X.iloc[test_start:].copy()
    y_test = y.iloc[test_start:].copy().values
    
    return X_train, y_train, X_val, y_val, X_test, y_test
