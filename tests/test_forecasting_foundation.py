# tests/test_forecasting_foundation.py
# ─────────────────────────────────────────────────────────────────────────────
# Tests for Member 3 Forecasting Foundation (Phase 1)
# Verifies:
#   - Dataset loading and standardization
#   - Generation of supervised targets using Member 1 physics
#   - Non-negativity and physical limit conformance
#   - Correct chronological train / validation / test splits
#   - Calendar, cyclical, and polar solar geometry features
#   - Strict prevention of future target leakage in lags and rolling windows
#   - Deterministic reusability
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import numpy as np
import pandas as pd
import pytest

# Ensure project root is available
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import config
from src.forecasting.preprocessor import (
    load_and_prepare_dataset,
    compute_ground_truth_targets,
    create_chronological_splits,
    validate_preprocessed_data,
    TARGET_COLUMNS,
    TARGET_PHYSICAL_LIMITS,
    DEFAULT_DATA_PATH,
)
from src.forecasting.features import (
    build_features,
    compute_solar_geometry,
    add_calendar_features,
    add_lag_features,
    add_rolling_features,
    add_weather_change_rates,
    get_feature_column_names,
    FEATURE_COLUMNS,
    BHARATI_LATITUDE,
    BHARATI_LONGITUDE,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def prepared_dataset():
    """Loads and prepares the canonical dataset once for the test module."""
    return load_and_prepare_dataset(DEFAULT_DATA_PATH)


@pytest.fixture(scope="module")
def sample_features(prepared_dataset):
    """Generates features for a 100-hour slice to test feature transformations quickly."""
    slice_df = prepared_dataset.head(100).copy()
    return build_features(slice_df)


# ── Dataset Loading & Target Generation Tests ─────────────────────────────────

def test_dataset_loading(prepared_dataset):
    """Verifies that the full 10-year dataset loads with exactly 87,672 rows."""
    assert len(prepared_dataset) == 87672
    assert "timestamp" in prepared_dataset.columns
    assert "temperature_c" in prepared_dataset.columns
    assert "wind_speed_ms" in prepared_dataset.columns
    assert "irradiance_w_m2" in prepared_dataset.columns


def test_no_missing_required_values(prepared_dataset):
    """Verifies zero missing/NaN values across all required weather and target columns."""
    required = [
        "timestamp",
        "temperature_c",
        "wind_speed_ms",
        "irradiance_w_m2",
        "surface_pressure_kpa",
        "precipitation_mm",
    ] + TARGET_COLUMNS
    missing = prepared_dataset[required].isna().sum()
    assert missing.sum() == 0, f"Missing values found:\n{missing[missing > 0]}"


def test_generated_targets_exist(prepared_dataset):
    """Verifies all four supervised targets plus electrical load exist."""
    for col in TARGET_COLUMNS:
        assert col in prepared_dataset.columns, f"Missing target: {col}"
    assert "electrical_load_kw" in prepared_dataset.columns


def test_generated_targets_non_negative(prepared_dataset):
    """Verifies all energy generation and load targets are strictly non-negative."""
    for col in TARGET_COLUMNS:
        min_val = prepared_dataset[col].min()
        assert min_val >= 0.0, f"Target '{col}' has negative minimum value: {min_val}"


def test_targets_respect_digital_twin_physical_limits(prepared_dataset):
    """
    Verifies that solar, wind, and load targets respect the physical ratings
    defined in Member 1's config.py.
    """
    solar_max = config.SOLAR_CAPACITY_KW  # 40.0 kW
    wind_max = config.WIND_CAPACITY_KW    # 50.0 kW

    assert prepared_dataset["solar_power_kw"].max() <= solar_max + 1e-4
    assert prepared_dataset["wind_power_kw"].max() <= wind_max + 1e-4

    # Heating load must never be below HEATING_BASE_KW (15.0 kW at 0°C)
    assert prepared_dataset["heating_load_kw"].min() >= config.HEATING_BASE_KW - 1e-4

    # Total load must equal electrical_load + heating_load
    calculated_total = prepared_dataset["electrical_load_kw"] + prepared_dataset["heating_load_kw"]
    np.testing.assert_allclose(
        prepared_dataset["total_load_kw"].to_numpy(),
        calculated_total.to_numpy(),
        rtol=1e-4,
        err_msg="total_load_kw does not equal electrical_load + heating_load",
    )


def test_wind_turbine_cutout_at_25_ms(prepared_dataset):
    """Verifies wind power output cuts out to 0.0 kW when wind speed >= 25.0 m/s."""
    storm_mask = prepared_dataset["wind_speed_ms"] >= config.WIND_CUT_OUT_MS
    assert storm_mask.sum() > 0, "No storm cutout hours found in dataset to test"
    cutout_outputs = prepared_dataset.loc[storm_mask, "wind_power_kw"]
    assert (cutout_outputs == 0.0).all(), (
        f"Wind turbine produced power during cutout (max: {cutout_outputs.max()} kW)"
    )


# ── Chronological Split Tests ─────────────────────────────────────────────────

def test_chronological_split_boundaries(prepared_dataset):
    """
    Verifies the chronological partitioning:
      - Train: 2015-01-01 to 2022-12-31 (8 years = 70,128 hours)
      - Validation: 2023-01-01 to 2023-12-31 (1 year = 8,760 hours)
      - Test: 2024-01-01 to 2024-12-31 (1 leap year = 8,784 hours)
    """
    train_df, val_df, test_df = create_chronological_splits(prepared_dataset)

    assert len(train_df) == 70128, f"Expected 70,128 train rows, got {len(train_df)}"
    assert len(val_df) == 8760, f"Expected 8,760 val rows, got {len(val_df)}"
    assert len(test_df) == 8784, f"Expected 8,784 test rows, got {len(test_df)}"
    assert len(train_df) + len(val_df) + len(test_df) == len(prepared_dataset)

    # Check timestamp boundaries
    assert train_df["timestamp"].iloc[0] == pd.Timestamp("2015-01-01 00:00:00+00:00")
    assert train_df["timestamp"].iloc[-1] == pd.Timestamp("2022-12-31 23:00:00+00:00")

    assert val_df["timestamp"].iloc[0] == pd.Timestamp("2023-01-01 00:00:00+00:00")
    assert val_df["timestamp"].iloc[-1] == pd.Timestamp("2023-12-31 23:00:00+00:00")

    assert test_df["timestamp"].iloc[0] == pd.Timestamp("2024-01-01 00:00:00+00:00")
    assert test_df["timestamp"].iloc[-1] == pd.Timestamp("2024-12-31 23:00:00+00:00")


def test_chronological_splits_zero_leakage_and_ordering(prepared_dataset):
    """Verifies strict monotonic ordering and no temporal leakage across splits."""
    train_df, val_df, test_df = create_chronological_splits(prepared_dataset)

    assert train_df["timestamp"].is_monotonic_increasing
    assert val_df["timestamp"].is_monotonic_increasing
    assert test_df["timestamp"].is_monotonic_increasing

    assert train_df["timestamp"].max() < val_df["timestamp"].min()
    assert val_df["timestamp"].max() < test_df["timestamp"].min()


# ── Feature Engineering Tests ─────────────────────────────────────────────────

def test_expected_feature_columns_present(sample_features):
    """Verifies that all expected feature columns are produced by build_features."""
    expected_cols = get_feature_column_names()
    for col in expected_cols:
        assert col in sample_features.columns, f"Expected feature column missing: {col}"


def test_cyclical_calendar_features(sample_features):
    """Verifies hour_sin/cos and doy_sin/cos stay strictly within [-1.0, 1.0]."""
    for col in ["hour_sin", "hour_cos", "doy_sin", "doy_cos"]:
        assert sample_features[col].between(-1.0, 1.0).all()

    # Verify cyclical identity: sin^2 + cos^2 ≈ 1
    hour_identity = sample_features["hour_sin"] ** 2 + sample_features["hour_cos"] ** 2
    np.testing.assert_allclose(hour_identity.to_numpy(), 1.0, atol=1e-4)


def test_polar_solar_geometry():
    """Verifies astronomical polar solar calculations for Bharati Station."""
    # Test dates: Winter solstice (June 21 - Polar Night) and Summer solstice (Dec 21 - Polar Day)
    winter_noon = pd.Timestamp("2024-06-21 12:00:00+00:00")
    summer_midnight = pd.Timestamp("2024-12-21 00:00:00+00:00")
    summer_noon = pd.Timestamp("2024-12-21 12:00:00+00:00")

    geo = compute_solar_geometry([winter_noon, summer_midnight, summer_noon])

    # Winter noon at -69.4° S: Sun is below horizon (elevation < 0)
    assert geo.loc[0, "solar_elevation_deg"] < 0.0
    assert geo.loc[0, "sun_above_horizon"] == 0
    assert geo.loc[0, "is_polar_night"] == 1

    # Summer solstice: Polar day (sun remains above horizon even at midnight)
    assert geo.loc[1, "is_polar_day"] == 1
    assert geo.loc[2, "is_polar_day"] == 1
    assert geo.loc[2, "solar_elevation_deg"] > 0.0
    assert geo.loc[2, "sun_above_horizon"] == 1


def test_no_target_leakage_in_lags_and_rolling(prepared_dataset):
    """
    CRITICAL LEAKAGE TEST:
    Modifying future rows (rows after index T) must have ZERO effect on
    the computed features at or before index T.
    """
    # Take a 100-row slice
    original_slice = prepared_dataset.iloc[:100].copy()
    features_original = build_features(original_slice)

    # Create a corrupted copy where rows 60 to 99 are modified with extreme values
    corrupted_slice = prepared_dataset.iloc[:100].copy()
    corrupted_slice.loc[60:, "temperature_c"] += 100.0
    corrupted_slice.loc[60:, "wind_speed_ms"] += 50.0
    corrupted_slice.loc[60:, "irradiance_w_m2"] += 500.0

    features_corrupted = build_features(corrupted_slice)

    # Features for rows 0 to 59 MUST be exactly identical between original and corrupted
    feature_cols = get_feature_column_names()
    for col in feature_cols:
        orig_vals = features_original.loc[:59, col].to_numpy()
        corr_vals = features_corrupted.loc[:59, col].to_numpy()
        np.testing.assert_allclose(
            orig_vals,
            corr_vals,
            equal_nan=True,
            err_msg=f"Feature '{col}' leaked future data from row >= 60 into row <= 59!",
        )


def test_deterministic_feature_pipeline(prepared_dataset):
    """Verifies that running build_features multiple times produces identical results."""
    slice_df = prepared_dataset.head(50).copy()
    feat1 = build_features(slice_df)
    feat2 = build_features(slice_df)

    pd.testing.assert_frame_equal(feat1, feat2)
