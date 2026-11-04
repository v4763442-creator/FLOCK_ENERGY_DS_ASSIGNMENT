"""
End-to-end execution script for Problem 3: Appliance Disaggregation
- Builds rolling features strictly from Aggregate power (61-minute centered window, float32)
- Implements strictly leakage-free chronological block splits with 2-hour buffer gaps
- Fits Always-Off and Diurnal Usage Profile baselines on training data only
- Trains HistGradientBoostingRegressor disaggregation model
- Evaluates continuous (MAE, RMSE, R2), event classification (Precision, Recall, F1), and energy metrics
- Executes Leave-One-House-Out cross-household generalization test
- Conducts empirical failure analysis using actual test predictions
- Generates Figures 6 and 7, saving all tables to results/
"""
import json
import gc
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from config import PROCESSED_DATA_DIR, FIGURES_DIR, RESULTS_DIR, WM_COLUMNS
from src.features import compute_aggregate_features
from src.evaluation import evaluate_disaggregation


def run_disaggregation():
    print("=" * 60)
    print("FLOCK ENERGY TAKE-HOME: PROBLEM 3 APPLIANCE DISAGGREGATION")
    print("=" * 60)
    
    houses = [1, 2, 3, 5]
    house_splits = {}
    
    # 1. Feature Engineering and Chronological Block Splitting
    print("\n--- 1. Generating Features and Chronological Block Splits ---")
    for h in houses:
        p_path = PROCESSED_DATA_DIR / f"clean_house{h}_1min.parquet"
        df = pd.read_parquet(p_path)
        wm_col = WM_COLUMNS[h]
        
        # Compute features
        X_h, y_h, valid_idx = compute_aggregate_features(df, agg_col='Aggregate', target_col=wm_col)
        
        # Chronological block split: 60% Train, 20% Val, 20% Test
        n_samples = len(X_h)
        train_end_idx = int(n_samples * 0.60)
        val_start_idx = train_end_idx + 120  # 2-hour buffer gap (120 min > 61 min window)
        val_end_idx = int(n_samples * 0.80)
        test_start_idx = val_end_idx + 120   # 2-hour buffer gap
        
        # Subsample training data by step=2 to maintain strict <150MB RAM footprint
        X_train = X_h.iloc[:train_end_idx:2].copy()
        y_train = y_h.iloc[:train_end_idx:2].copy()
        
        X_val = X_h.iloc[val_start_idx:val_end_idx:2].copy()
        y_val = y_h.iloc[val_start_idx:val_end_idx:2].copy()
        
        # Test set is kept at full 1-minute resolution (no subsampling!)
        X_test = X_h.iloc[test_start_idx:].copy()
        y_test = y_h.iloc[test_start_idx:].copy()
        
        # Store failure diagnosis slice for House 1
        df_diag = df.loc[X_test.index, ['Aggregate', 'Appliance4', 'Appliance5']].copy() if h == 1 else None
        
        house_splits[h] = {
            "X_train": X_train, "y_train": y_train,
            "X_val": X_val, "y_val": y_val,
            "X_test": X_test, "y_test": y_test,
            "df_diag": df_diag
        }
        
        del df, X_h, y_h, valid_idx
        gc.collect()
        print(f"House {h}: Train={len(X_train):,}, Val={len(X_val):,}, Test={len(X_test):,} (Buffer=120m)")

    # 2. Fit Diurnal Profile Baseline (on Training blocks only!)
    print("\n--- 2. Fitting Baselines on Training Blocks ---")
    X_train_pooled = pd.concat([house_splits[h]["X_train"] for h in houses])
    y_train_pooled = pd.concat([house_splits[h]["y_train"] for h in houses])
    
    train_time_df = pd.DataFrame({
        'hour': X_train_pooled.index.hour,
        'is_weekend': (X_train_pooled.index.dayofweek >= 5).astype(int),
        'wm_power': y_train_pooled.values
    })
    diurnal_lookup = train_time_df.groupby(['hour', 'is_weekend'])['wm_power'].mean().to_dict()
    del train_time_df
    gc.collect()
    
    def predict_diurnal_baseline(index_series):
        hrs = index_series.hour
        wknds = (index_series.dayofweek >= 5).astype(int)
        preds = [diurnal_lookup.get((h, w), 0.0) for h, w in zip(hrs, wknds)]
        return np.array(preds, dtype=np.float32)

    # 3. Train HistGradientBoostingRegressor
    print("\n--- 3. Training HistGradientBoostingRegressor ---")
    model = HistGradientBoostingRegressor(
        max_iter=100,
        learning_rate=0.08,
        max_leaf_nodes=31,
        min_samples_leaf=20,
        random_state=42
    )
    print(f"Training on {len(X_train_pooled):,} pooled samples across 4 households...")
    model.fit(X_train_pooled, y_train_pooled)
    print("Model training complete!")
    
    del X_train_pooled, y_train_pooled
    gc.collect()

    # 4. Evaluation against Baselines
    print("\n--- 4. Evaluating Test Performance ---")
    metrics_records = []
    test_preds_by_house = {}
    
    for h in houses:
        X_te = house_splits[h]["X_test"]
        y_te = house_splits[h]["y_test"].values
        
        # 1. Always-Off Baseline
        y_pred_off = np.zeros_like(y_te)
        eval_off = evaluate_disaggregation(y_te, y_pred_off, on_threshold=15.0)
        eval_off.update({"household": f"House {h}", "model": "Always-Off Baseline"})
        metrics_records.append(eval_off)
        
        # 2. Diurnal Profile Baseline
        y_pred_diurnal = predict_diurnal_baseline(X_te.index)
        eval_diurnal = evaluate_disaggregation(y_te, y_pred_diurnal, on_threshold=15.0)
        eval_diurnal.update({"household": f"House {h}", "model": "Diurnal Profile Baseline"})
        metrics_records.append(eval_diurnal)
        
        # 3. HistGradientBoosting Model
        y_pred_model = np.clip(model.predict(X_te), 0.0, None).astype(np.float32)
        test_preds_by_house[h] = y_pred_model
        eval_model = evaluate_disaggregation(y_te, y_pred_model, on_threshold=15.0)
        eval_model.update({"household": f"House {h}", "model": "HistGradientBoosting"})
        metrics_records.append(eval_model)
        
        print(f"\nHouse {h} Test Performance:")
        print(f"  Always-Off:  MAE={eval_off['mae_watts']} W, F1={eval_off['f1_score']}")
        print(f"  Diurnal:     MAE={eval_diurnal['mae_watts']} W, F1={eval_diurnal['f1_score']}")
        print(f"  Model (HGB): MAE={eval_model['mae_watts']} W, RMSE={eval_model['rmse_watts']} W, R2={eval_model['r2_score']}, Precision={eval_model['precision']}, Recall={eval_model['recall']}, F1={eval_model['f1_score']}, EnergyErr={eval_model['energy_error_kwh']} kWh ({eval_model['relative_energy_error_pct']}%)")

    # Overall Pooled Evaluation
    y_test_all = np.concatenate([house_splits[h]["y_test"].values for h in houses])
    y_pred_all = np.concatenate([test_preds_by_house[h] for h in houses])
    y_off_all = np.zeros_like(y_test_all)
    y_diurnal_all = np.concatenate([predict_diurnal_baseline(house_splits[h]["X_test"].index) for h in houses])
    
    eval_pooled_off = evaluate_disaggregation(y_test_all, y_off_all, on_threshold=15.0)
    eval_pooled_off.update({"household": "Overall Pooled", "model": "Always-Off Baseline"})
    metrics_records.append(eval_pooled_off)
    
    eval_pooled_diurnal = evaluate_disaggregation(y_test_all, y_diurnal_all, on_threshold=15.0)
    eval_pooled_diurnal.update({"household": "Overall Pooled", "model": "Diurnal Profile Baseline"})
    metrics_records.append(eval_pooled_diurnal)
    
    eval_pooled_model = evaluate_disaggregation(y_test_all, y_pred_all, on_threshold=15.0)
    eval_pooled_model.update({"household": "Overall Pooled", "model": "HistGradientBoosting"})
    metrics_records.append(eval_pooled_model)
    
    print("\n" + "=" * 40)
    print("OVERALL POOLED TEST PERFORMANCE:")
    print(f"  Always-Off Baseline:  MAE={eval_pooled_off['mae_watts']} W, F1={eval_pooled_off['f1_score']}")
    print(f"  Diurnal Baseline:     MAE={eval_pooled_diurnal['mae_watts']} W, F1={eval_pooled_diurnal['f1_score']}")
    print(f"  HistGradientBoosting: MAE={eval_pooled_model['mae_watts']} W, RMSE={eval_pooled_model['rmse_watts']} W, R2={eval_pooled_model['r2_score']}, Precision={eval_pooled_model['precision']}, Recall={eval_pooled_model['recall']}, F1={eval_pooled_model['f1_score']}, EnergyErr={eval_pooled_model['energy_error_kwh']} kWh ({eval_pooled_model['relative_energy_error_pct']}%)")
    print("=" * 40)

    metrics_df = pd.DataFrame(metrics_records)
    metrics_csv = RESULTS_DIR / "problem3_metrics.csv"
    metrics_df.to_csv(metrics_csv, index=False)
    print(f"Saved benchmark metrics to {metrics_csv.name}")
    
    with open(RESULTS_DIR / "problem3_metrics.json", "w") as f:
        json.dump(metrics_records, f, indent=2)

    # 5. Leave-One-House-Out (LOHO) Generalization
    print("\n--- 5. Leave-One-House-Out (LOHO) Generalization Benchmark ---")
    loho_records = []
    for test_h in houses:
        train_h_list = [h for h in houses if h != test_h]
        X_tr_loho = pd.concat([house_splits[h]["X_train"] for h in train_h_list])
        y_tr_loho = pd.concat([house_splits[h]["y_train"] for h in train_h_list])
        
        m_loho = HistGradientBoostingRegressor(
            max_iter=100, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=20, random_state=42
        )
        m_loho.fit(X_tr_loho, y_tr_loho)
        
        y_te = house_splits[test_h]["y_test"].values
        y_pred_loho = np.clip(m_loho.predict(house_splits[test_h]["X_test"]), 0.0, None)
        
        res = evaluate_disaggregation(y_te, y_pred_loho, on_threshold=15.0)
        res.update({
            "test_house": f"House {test_h}",
            "train_houses": str(train_h_list),
            "generalization": "Zero-Shot Unseen Household"
        })
        loho_records.append(res)
        print(f"Zero-Shot Test on House {test_h}: MAE={res['mae_watts']} W, F1={res['f1_score']}, R2={res['r2_score']}, EnergyErr={res['energy_error_kwh']} kWh")
        del X_tr_loho, y_tr_loho, m_loho
        gc.collect()

    loho_df = pd.DataFrame(loho_records)
    loho_csv = RESULTS_DIR / "problem3_loho_generalization.csv"
    loho_df.to_csv(loho_csv, index=False)
    print(f"Saved LOHO generalization metrics to {loho_csv.name}")

    # 6. Figures: Actual vs Predicted and Failure Analysis
    print("\n--- 6. Generating Visualizations ---")
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # FIGURE 6: Actual vs Predicted Trace on Held-out Test Data (House 1)
    h1_test_idx = house_splits[1]["X_test"].index
    h1_y_true = house_splits[1]["y_test"]
    h1_y_pred = pd.Series(test_preds_by_house[1], index=h1_test_idx)
    
    # Find active test window
    active_test_days = h1_y_true[h1_y_true > 1500].index
    if len(active_test_days) > 0:
        sample_time = active_test_days[min(10, len(active_test_days)-1)]
        plot_start = sample_time - pd.Timedelta(hours=6)
        plot_end = sample_time + pd.Timedelta(hours=18)
    else:
        plot_start = h1_test_idx[1000]
        plot_end = plot_start + pd.Timedelta(hours=24)
        
    s_true = h1_y_true.loc[plot_start:plot_end]
    s_pred = h1_y_pred.loc[plot_start:plot_end]
    s_agg = house_splits[1]["X_test"]['agg_t'].loc[plot_start:plot_end]
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    
    # Top: Aggregate Input
    axes[0].plot(s_agg.index, s_agg.values, color='#7f8c8d', lw=1.2, label='Whole-Home Aggregate Power (Input X)')
    axes[0].set_ylabel('Power (Watts)', fontsize=11)
    axes[0].set_title('Appliance Disaggregation on Held-Out Test Data: House 1', fontsize=13, fontweight='bold')
    axes[0].legend(loc='upper right')
    axes[0].grid(True, alpha=0.3)
    
    # Bottom: Actual vs Predicted
    axes[1].plot(s_true.index, s_true.values, color='#27ae60', lw=2.0, label='Actual Washing Machine (Ground Truth y)')
    axes[1].plot(s_pred.index, s_pred.values, color='#e74c3c', lw=1.8, ls='--', label='Disaggregated Prediction (HistGradientBoosting)')
    axes[1].set_ylabel('Power (Watts)', fontsize=11)
    axes[1].set_xlabel('UTC Timestamp', fontsize=11)
    axes[1].legend(loc='upper right')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig6_path = FIGURES_DIR / "fig6_actual_vs_predicted.png"
    plt.savefig(fig6_path, dpi=200)
    plt.close()
    print(f"Saved {fig6_path.name}")
    
    # FIGURE 7: Empirical Failure Analysis (Real Test Errors)
    df_diag = house_splits[1]["df_diag"]
    h1_err = h1_y_pred - h1_y_true
    
    # Find a real False Positive where Model > 250W but Actual WM < 15W
    fp_candidates = h1_err[(h1_y_pred > 250) & (h1_y_true < 15)].index
    # Find a real False Negative where Actual WM > 1000W but Model < 150W
    fn_candidates = h1_err[(h1_y_true > 1000) & (h1_y_pred < 150)].index
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    
    if len(fp_candidates) > 0:
        fp_time = fp_candidates[min(5, len(fp_candidates)-1)]
        fp_start = fp_time - pd.Timedelta(hours=2)
        fp_end = fp_time + pd.Timedelta(hours=2)
        
        axes[0].plot(df_diag['Aggregate'].loc[fp_start:fp_end].index, df_diag['Aggregate'].loc[fp_start:fp_end].values, color='#7f8c8d', lw=1.2, label='Aggregate Power')
        if 'Appliance4' in df_diag.columns:
            axes[0].plot(df_diag['Appliance4'].loc[fp_start:fp_end].index, df_diag['Appliance4'].loc[fp_start:fp_end].values, color='#d62728', lw=1.5, ls='-.', label='Appliance 4: Tumble Dryer (True Confounder)')
        axes[0].plot(h1_y_true.loc[fp_start:fp_end].index, h1_y_true.loc[fp_start:fp_end].values, color='#27ae60', lw=2.0, label='Actual Washing Machine (0 W - OFF)')
        axes[0].plot(h1_y_pred.loc[fp_start:fp_end].index, h1_y_pred.loc[fp_start:fp_end].values, color='#e74c3c', lw=2.0, ls='--', label='Model Spurious Prediction (False Positive)')
        axes[0].set_title('Failure Case 1: False Positive Induced by Overlapping Resistive Load (Tumble Dryer / Immersion Heater)', fontsize=11, fontweight='bold')
        axes[0].set_ylabel('Power (Watts)', fontsize=10)
        axes[0].legend(loc='upper right')
        axes[0].grid(True, alpha=0.3)
    else:
        axes[0].text(0.5, 0.5, "No False Positive Exceeded 250W", ha='center', va='center')

    if len(fn_candidates) > 0:
        fn_time = fn_candidates[min(5, len(fn_candidates)-1)]
        fn_start = fn_time - pd.Timedelta(hours=2)
        fn_end = fn_time + pd.Timedelta(hours=2)
        
        axes[1].plot(df_diag['Aggregate'].loc[fn_start:fn_end].index, df_diag['Aggregate'].loc[fn_start:fn_end].values, color='#7f8c8d', lw=1.2, label='Aggregate Power')
        axes[1].plot(h1_y_true.loc[fn_start:fn_end].index, h1_y_true.loc[fn_start:fn_end].values, color='#27ae60', lw=2.0, label='Actual Washing Machine (Sharp 2 kW Heating Spike)')
        axes[1].plot(h1_y_pred.loc[fn_start:fn_end].index, h1_y_pred.loc[fn_start:fn_end].values, color='#e74c3c', lw=2.0, ls='--', label='Model Under-Prediction (Clipped Peak)')
        axes[1].set_title('Failure Case 2: Magnitude Compression / Transient Peak Clipping', fontsize=11, fontweight='bold')
        axes[1].set_ylabel('Power (Watts)', fontsize=10)
        axes[1].set_xlabel('UTC Timestamp', fontsize=10)
        axes[1].legend(loc='upper right')
        axes[1].grid(True, alpha=0.3)
    else:
        axes[1].text(0.5, 0.5, "No Severe False Negative Exceeded 1000W", ha='center', va='center')

    plt.tight_layout()
    fig7_path = FIGURES_DIR / "fig7_failure_analysis.png"
    plt.savefig(fig7_path, dpi=200)
    plt.close()
    print(f"Saved {fig7_path.name}")
    
    print("\nProblem 3 execution completed successfully!")

if __name__ == "__main__":
    run_disaggregation()
