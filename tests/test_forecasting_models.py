# tests/test_forecasting_models.py
# ─────────────────────────────────────────────────────────────────────────────
# Tests for Member 3 Forecasting Models, Fallbacks & Evaluation (Phase 2)
# Verifies:
#   - Quantile Gradient Boosting regressor training and multi-quantile outputs
#   - Strict quantile monotonicity: P10 <= P50 <= P90
#   - Clamping to physical equipment limits (solar <= 40 kW, wind <= 50 kW)
#   - Total load and net load calculation integrity
#   - Model serialization and deserialization (save / load roundtrip)
#   - Offline Polar Climatology and Persistence forecasters
#   - Metric calculators in evaluation.py (MAE, RMSE, R², Pinball loss, PICP)
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import tempfile
import numpy as np
import pandas as pd
import pytest

# Ensure project root is on path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import config
from src.forecasting.preprocessor import load_and_prepare_dataset, DEFAULT_DATA_PATH
from src.forecasting.features import build_features, get_feature_column_names
from src.forecasting.models import (
    QuantileGradientBoostingForecaster,
    AuroraForecastingSystem,
    HAS_SKLEARN,
)
from src.forecasting.fallback import (
    PolarClimatologyForecaster,
    PersistenceForecaster,
)
from src.forecasting.evaluation import (
    mean_absolute_error,
    root_mean_squared_error,
    normalized_rmse,
    r2_score,
    pinball_loss,
    prediction_interval_coverage,
    mean_prediction_interval_width,
    evaluate_forecast,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def small_training_data():
    """Provides a 200-hour slice of prepared data with features for fast model tests."""
    df = load_and_prepare_dataset(DEFAULT_DATA_PATH)
    slice_df = df.iloc[:200].copy()
    feat_df = build_features(slice_df)
    clean_df = feat_df.dropna().reset_index(drop=True)
    return clean_df


# ── Model & Quantile Tests ───────────────────────────────────────────────────

def test_quantile_forecaster_fit_and_predict(small_training_data):
    """Verifies that QuantileGradientBoostingForecaster fits and predicts P10, P50, P90."""
    feat_cols = [c for c in get_feature_column_names() if c in small_training_data.columns]
    X = small_training_data[feat_cols]
    y = small_training_data["solar_power_kw"]

    forecaster = QuantileGradientBoostingForecaster(
        target_name="solar_power_kw",
        capacity_min=0.0,
        capacity_max=config.SOLAR_CAPACITY_KW,
        max_iter=20,
    )
    forecaster.fit(X, y, feat_cols)

    preds = forecaster.predict(X)

    assert "solar_power_kw_p10" in preds
    assert "solar_power_kw_p50" in preds
    assert "solar_power_kw_p90" in preds
    assert len(preds["solar_power_kw_p50"]) == len(small_training_data)


def test_quantile_monotonicity(small_training_data):
    """CRITICAL: Verifies strict quantile ordering: P10 <= P50 <= P90 for all rows."""
    feat_cols = [c for c in get_feature_column_names() if c in small_training_data.columns]
    X = small_training_data[feat_cols]
    y = small_training_data["wind_power_kw"]

    forecaster = QuantileGradientBoostingForecaster(
        target_name="wind_power_kw",
        capacity_min=0.0,
        capacity_max=config.WIND_CAPACITY_KW,
        max_iter=20,
    )
    forecaster.fit(X, y, feat_cols)
    preds = forecaster.predict(X)

    p10 = preds["wind_power_kw_p10"]
    p50 = preds["wind_power_kw_p50"]
    p90 = preds["wind_power_kw_p90"]

    assert np.all(p10 <= p50 + 1e-6), "Monotonicity violated: P10 > P50 found"
    assert np.all(p50 <= p90 + 1e-6), "Monotonicity violated: P50 > P90 found"


def test_predictions_respect_physical_limits(small_training_data):
    """Verifies that predictions are clamped to hardware limits."""
    feat_cols = [c for c in get_feature_column_names() if c in small_training_data.columns]
    X = small_training_data[feat_cols]
    y = small_training_data["solar_power_kw"]

    forecaster = QuantileGradientBoostingForecaster(
        target_name="solar_power_kw",
        capacity_min=0.0,
        capacity_max=config.SOLAR_CAPACITY_KW,
        max_iter=20,
    )
    forecaster.fit(X, y, feat_cols)
    preds = forecaster.predict(X)

    for q_col in ["solar_power_kw_p10", "solar_power_kw_p50", "solar_power_kw_p90"]:
        assert (preds[q_col] >= 0.0).all(), f"{q_col} contains negative values"
        assert (preds[q_col] <= config.SOLAR_CAPACITY_KW + 1e-4).all(), (
            f"{q_col} exceeded SOLAR_CAPACITY_KW"
        )


def test_aurora_forecasting_system_integration(small_training_data):
    """
    Verifies AuroraForecastingSystem coordinates all equipment models,
    maintains total load identity, and calculates net load.
    """
    system = AuroraForecastingSystem(max_iter=20, random_state=42)
    system.fit(small_training_data)

    preds_df = system.predict(small_training_data)

    # Check presence of all predicted columns
    expected_pred_cols = [
        "solar_power_kw_p10", "solar_power_kw_p50", "solar_power_kw_p90",
        "wind_power_kw_p10", "wind_power_kw_p50", "wind_power_kw_p90",
        "heating_load_kw_p10", "heating_load_kw_p50", "heating_load_kw_p90",
        "total_load_kw_p10", "total_load_kw_p50", "total_load_kw_p90",
        "electrical_load_kw", "net_load_kw_p50",
    ]
    for col in expected_pred_cols:
        assert col in preds_df.columns, f"Missing prediction column: {col}"

    # Verify total load identity: total_load = electrical (30 kW) + heating
    elec_kw = preds_df["electrical_load_kw"].iloc[0]
    assert elec_kw == 30.0

    expected_total_p50 = np.round(elec_kw + preds_df["heating_load_kw_p50"], 4)
    np.testing.assert_allclose(preds_df["total_load_kw_p50"].to_numpy(), expected_total_p50.to_numpy())

    # Verify net load calculation: net_load = total_load - (solar + wind)
    expected_net = np.round(
        preds_df["total_load_kw_p50"] - (preds_df["solar_power_kw_p50"] + preds_df["wind_power_kw_p50"]),
        4,
    )
    np.testing.assert_allclose(preds_df["net_load_kw_p50"].to_numpy(), expected_net.to_numpy())


def test_model_serialization_roundtrip(small_training_data):
    """Verifies that AuroraForecastingSystem can be saved and loaded from disk."""
    system = AuroraForecastingSystem(max_iter=20, random_state=42)
    system.fit(small_training_data)

    preds_before = system.predict(small_training_data)

    with tempfile.TemporaryDirectory() as tmpdir:
        system.save_system(tmpdir)
        loaded_system = AuroraForecastingSystem.load_system(tmpdir)

        preds_after = loaded_system.predict(small_training_data)

        # Confirm exact identical predictions
        pd.testing.assert_frame_equal(preds_before, preds_after)


# ── Offline Fallback Forecaster Tests ────────────────────────────────────────

def test_polar_climatology_forecaster(small_training_data):
    """Verifies PolarClimatologyForecaster produces physical multi-step horizons."""
    climatology = PolarClimatologyForecaster()
    climatology.fit(small_training_data)

    start_ts = pd.Timestamp("2024-01-01 00:00:00+00:00")
    horizon_df = climatology.predict_horizon(start_ts, horizon_hours=24)

    assert len(horizon_df) == 24
    assert "solar_power_kw_p50" in horizon_df.columns
    assert "wind_power_kw_p50" in horizon_df.columns
    assert "forecast_mode" in horizon_df.columns
    assert (horizon_df["forecast_mode"] == "offline_climatology").all()

    # All outputs must respect non-negativity and rated limits
    assert (horizon_df["solar_power_kw_p50"] >= 0.0).all()
    assert (horizon_df["solar_power_kw_p50"] <= config.SOLAR_CAPACITY_KW).all()
    assert (horizon_df["wind_power_kw_p50"] >= 0.0).all()
    assert (horizon_df["wind_power_kw_p50"] <= config.WIND_CAPACITY_KW).all()


def test_persistence_forecaster(small_training_data):
    """Verifies PersistenceForecaster diurnal and last-value multi-hour predictions."""
    history_24h = small_training_data.iloc[:24].copy()
    forecaster = PersistenceForecaster(mode="diurnal")

    preds = forecaster.predict_horizon(history_24h, horizon_hours=24)
    assert len(preds) == 24
    assert (preds["solar_power_kw_p50"] >= 0.0).all()


# ── Evaluation Metrics Tests ─────────────────────────────────────────────────

def test_evaluation_metrics_exact_values():
    """Verifies accuracy of evaluation metrics on known numerical vectors."""
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    y_pred = np.array([12.0, 18.0, 33.0, 39.0])  # errors: +2, -2, +3, -1 -> abs: 2, 2, 3, 1 -> mean: 2.0

    assert mean_absolute_error(y_true, y_pred) == 2.0
    assert round(root_mean_squared_error(y_true, y_pred), 4) == round(np.sqrt(18.0 / 4.0), 4)
    assert normalized_rmse(y_true, y_pred, capacity=40.0) == round((root_mean_squared_error(y_true, y_pred) / 40.0) * 100.0, 4)

    # Perfect predictions yield MAE = 0, RMSE = 0, R2 = 1.0
    assert mean_absolute_error(y_true, y_true) == 0.0
    assert root_mean_squared_error(y_true, y_true) == 0.0
    assert r2_score(y_true, y_true) == 1.0


def test_pinball_loss_and_interval_coverage():
    """Verifies quantile pinball loss and PICP calculation."""
    y_true = np.array([10.0, 20.0, 30.0])
    y_lower = np.array([8.0, 18.0, 28.0])   # all true values are above lower bound
    y_upper = np.array([12.0, 22.0, 32.0])  # all true values are below upper bound

    # 100% coverage
    assert prediction_interval_coverage(y_true, y_lower, y_upper) == 100.0
    assert mean_prediction_interval_width(y_lower, y_upper) == 4.0

    # Pinball loss is non-negative
    loss_p10 = pinball_loss(y_true, y_lower, 0.10)
    loss_p50 = pinball_loss(y_true, y_true, 0.50)
    assert loss_p10 >= 0.0
    assert loss_p50 == 0.0


def test_evaluate_forecast_summary():
    """Verifies evaluate_forecast produces all expected summary keys."""
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred = np.array([11.0, 19.0, 31.0])
    y_lower = np.array([9.0, 17.0, 29.0])
    y_upper = np.array([13.0, 23.0, 33.0])

    summary = evaluate_forecast(y_true, y_pred, y_lower, y_upper, capacity=50.0)

    for key in ["mae", "rmse", "r2", "mape", "nrmse_pct", "pinball_p10", "pinball_p50", "pinball_p90", "picp_pct", "mpiw_kw"]:
        assert key in summary
