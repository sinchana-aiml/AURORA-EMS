# scripts/train_forecast_models.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Forecasting Model Training & Evaluation Pipeline
# Member 3: Renewable Energy & Station Load Forecasting
#
# Trains Quantile Gradient Boosting Regressors on historical polar data:
#   - Train: 2015–2022 (70,128 hours)
#   - Validation: 2023 (8,760 hours)
#   - Test: 2024 (8,784 hours)
#
# Computes evaluation metrics (MAE, RMSE, nRMSE, R², Quantile Loss, PICP)
# and serializes model weights to models/ directory.
#
# Run:
#   python scripts/train_forecast_models.py
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import time
import pandas as pd
import numpy as np

# Ensure project root is available
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import config
from src.forecasting.preprocessor import (
    load_and_prepare_dataset,
    create_chronological_splits,
    TARGET_COLUMNS,
)
from src.forecasting.features import (
    build_features,
    get_feature_column_names,
)
from src.forecasting.models import (
    AuroraForecastingSystem,
    HAS_SKLEARN,
)
from src.forecasting.evaluation import (
    evaluate_forecast,
    mean_absolute_error,
    root_mean_squared_error,
    normalized_rmse,
    r2_score,
)


def run_training_pipeline(model_dir: str = "models", max_iter: int = 100):
    print("=" * 70)
    print("  AURORA-EMS: Member 3 Forecasting Model Training Pipeline")
    print(f"  Scikit-Learn Available: {HAS_SKLEARN}")
    print("=" * 70)

    t0 = time.time()

    # Step 1: Load and prepare dataset with Member 1 physics targets
    print("\n[1/5] Loading 10-year clean polar weather dataset & generating targets...")
    df = load_and_prepare_dataset()
    print(f"      Total records loaded: {len(df):,} hours")

    # Step 2: Build deterministic feature pipeline
    print("\n[2/5] Constructing feature pipeline (calendar, solar angles, lags, rolling)...")
    df_feat = build_features(df)
    feature_cols = [c for c in get_feature_column_names() if c in df_feat.columns]
    print(f"      Total features engineered: {len(feature_cols)}")

    # Step 3: Chronological Train / Val / Test splitting
    print("\n[3/5] Partitioning chronological splits...")
    train_df, val_df, test_df = create_chronological_splits(df_feat)
    print(f"      Train set (2015-2022) : {len(train_df):,} rows")
    print(f"      Val set   (2023)      : {len(val_df):,} rows")
    print(f"      Test set  (2024)      : {len(test_df):,} rows")

    # Step 4: Train Quantile Gradient Boosting Forecasting System
    print(f"\n[4/5] Training Quantile GBDT Models (P10, P50, P90) (max_iter={max_iter})...")
    forecasting_system = AuroraForecastingSystem(max_iter=max_iter, random_state=42)
    forecasting_system.fit(train_df, feature_names=feature_cols)
    print("      Training completed successfully.")

    # Step 5: Evaluate on Validation Set (2023)
    print("\n[5/5] Evaluating on Validation Set (2023 - 8,760 hours)...")
    val_clean = val_df.dropna().reset_index(drop=True)
    val_preds = forecasting_system.predict(val_clean)

    # Evaluate Solar PV
    solar_eval = evaluate_forecast(
        y_true=val_clean["solar_power_kw"].to_numpy(),
        y_pred=val_preds["solar_power_kw_p50"].to_numpy(),
        y_lower=val_preds["solar_power_kw_p10"].to_numpy(),
        y_upper=val_preds["solar_power_kw_p90"].to_numpy(),
        capacity=config.SOLAR_CAPACITY_KW,
    )

    # Evaluate Wind Power
    wind_eval = evaluate_forecast(
        y_true=val_clean["wind_power_kw"].to_numpy(),
        y_pred=val_preds["wind_power_kw_p50"].to_numpy(),
        y_lower=val_preds["wind_power_kw_p10"].to_numpy(),
        y_upper=val_preds["wind_power_kw_p90"].to_numpy(),
        capacity=config.WIND_CAPACITY_KW,
    )

    # Evaluate Heating Load
    heat_eval = evaluate_forecast(
        y_true=val_clean["heating_load_kw"].to_numpy(),
        y_pred=val_preds["heating_load_kw_p50"].to_numpy(),
        y_lower=val_preds["heating_load_kw_p10"].to_numpy(),
        y_upper=val_preds["heating_load_kw_p90"].to_numpy(),
        capacity=50.0,
    )

    # Evaluate Total Load
    total_eval = evaluate_forecast(
        y_true=val_clean["total_load_kw"].to_numpy(),
        y_pred=val_preds["total_load_kw_p50"].to_numpy(),
        y_lower=val_preds["total_load_kw_p10"].to_numpy(),
        y_upper=val_preds["total_load_kw_p90"].to_numpy(),
        capacity=100.0,
    )

    print("\n" + "=" * 70)
    print("  VALIDATION SET BENCHMARK RESULTS (Year 2023)")
    print("=" * 70)
    print(f"{'Target':<18} {'MAE (kW)':<10} {'RMSE (kW)':<10} {'nRMSE (%)':<12} {'R²':<8} {'PICP (%)':<10}")
    print("-" * 70)
    print(f"{'Solar Power':<18} {solar_eval['mae']:<10.3f} {solar_eval['rmse']:<10.3f} {solar_eval.get('nrmse_pct', 0.0):<12.2f} {solar_eval['r2']:<8.3f} {solar_eval.get('picp_pct', 0.0):<10.1f}")
    print(f"{'Wind Power':<18} {wind_eval['mae']:<10.3f} {wind_eval['rmse']:<10.3f} {wind_eval.get('nrmse_pct', 0.0):<12.2f} {wind_eval['r2']:<8.3f} {wind_eval.get('picp_pct', 0.0):<10.1f}")
    print(f"{'Heating Load':<18} {heat_eval['mae']:<10.3f} {heat_eval['rmse']:<10.3f} {heat_eval.get('nrmse_pct', 0.0):<12.2f} {heat_eval['r2']:<8.3f} {heat_eval.get('picp_pct', 0.0):<10.1f}")
    print(f"{'Total Load':<18} {total_eval['mae']:<10.3f} {total_eval['rmse']:<10.3f} {total_eval.get('nrmse_pct', 0.0):<12.2f} {total_eval['r2']:<8.3f} {total_eval.get('picp_pct', 0.0):<10.1f}")

    # Save model artifacts
    save_path = os.path.join(_ROOT, model_dir)
    print(f"\nSerializing trained models to: {save_path}...")
    forecasting_system.save_system(save_path)
    print("      Model artifacts saved successfully.")

    elapsed = time.time() - t0
    print(f"\nPipeline finished in {elapsed:.2f} seconds.")
    print("=" * 70)

    return {
        "solar": solar_eval,
        "wind": wind_eval,
        "heating": heat_eval,
        "total_load": total_eval,
    }


if __name__ == "__main__":
    run_training_pipeline()
