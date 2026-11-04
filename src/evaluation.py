"""
Evaluation metrics for NILM disaggregation:
Computes continuous regression metrics (MAE, RMSE, R2), minute-level ON/OFF
classification metrics (Precision, Recall, F1), and total energy error (kWh).
"""
from typing import Dict, Any
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def evaluate_disaggregation(
    y_true: np.ndarray, 
    y_pred: np.ndarray, 
    on_threshold: float = 15.0
) -> Dict[str, float]:
    """
    Evaluates disaggregation performance.
    
    Parameters:
    - y_true: Ground truth power in Watts
    - y_pred: Predicted power in Watts (clipped at 0 W)
    - on_threshold: Power threshold (Watts) defining the active ON state
    """
    # Guarantee non-negative predictions
    y_pred = np.clip(y_pred, 0.0, None)
    y_true = np.asarray(y_true)
    
    # Continuous error metrics
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    
    # Minute-level ON/OFF state metrics
    true_on = y_true > on_threshold
    pred_on = y_pred > on_threshold
    
    tp = int(np.sum(true_on & pred_on))
    fp = int(np.sum((~true_on) & pred_on))
    fn = int(np.sum(true_on & (~pred_on)))
    tn = int(np.sum((~true_on) & (~pred_on)))
    
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    
    # Energy metrics (kWh)
    actual_kwh = float(np.sum(y_true) / 60000.0)
    pred_kwh = float(np.sum(y_pred) / 60000.0)
    energy_error_kwh = float(abs(pred_kwh - actual_kwh))
    rel_energy_error_pct = float(energy_error_kwh / actual_kwh * 100.0) if actual_kwh > 0 else 0.0
    
    return {
        "mae_watts": round(mae, 2),
        "rmse_watts": round(rmse, 2),
        "r2_score": round(r2, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "actual_energy_kwh": round(actual_kwh, 2),
        "pred_energy_kwh": round(pred_kwh, 2),
        "energy_error_kwh": round(energy_error_kwh, 2),
        "relative_energy_error_pct": round(rel_energy_error_pct, 2),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn
    }
