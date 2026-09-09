"""
tests/test_digital_twin_export.py
──────────────────────────────────
Verifies the Digital-Twin export produced by scripts/export_for_digital_twin.py.

Run with:
    python -m pytest tests/test_digital_twin_export.py -v
"""

import os
import sys
import pandas as pd
import pytest

# Allow importing from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.export_for_digital_twin import (
    load_cleaned_weather,
    build_dt_export,
    export_sample_24h,
    SOURCE_CSV,
    SAMPLE_CSV,
    DT_REQUIRED,
    DT_OPTIONAL,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def raw_df():
    return load_cleaned_weather()

@pytest.fixture(scope="module")
def dt_df(raw_df):
    return build_dt_export(raw_df)

@pytest.fixture(scope="module")
def sample_df(dt_df, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("sample")
    path = str(tmp / "digital_twin_weather_24h.csv")
    return export_sample_24h(dt_df, path=path)


# ── Required-column tests ─────────────────────────────────────────────────────

def test_required_columns_exist(dt_df):
    for col in DT_REQUIRED:
        assert col in dt_df.columns, f"Missing required column: {col}"

def test_sample_has_exactly_24_rows(sample_df):
    assert len(sample_df) == 24, f"Expected 24 rows, got {len(sample_df)}"

def test_timestamps_are_ordered(dt_df):
    ts = pd.to_datetime(dt_df["timestamp"])
    assert ts.is_monotonic_increasing, "Timestamps are not in chronological order"

def test_timestamps_are_utc(dt_df):
    ts = pd.to_datetime(dt_df["timestamp"], utc=True)
    assert str(ts.dt.tz) == "UTC", f"Expected UTC timezone, got {ts.dt.tz}"

def test_numeric_fields(dt_df):
    for col in ["temperature_c", "irradiance_w_m2", "wind_speed_ms"]:
        assert pd.api.types.is_numeric_dtype(dt_df[col]), f"{col} is not numeric"

def test_no_missing_required_values(dt_df):
    missing = dt_df[DT_REQUIRED].isna().sum()
    assert missing.sum() == 0, f"Missing values in required columns:\n{missing}"

def test_irradiance_nonnegative(dt_df):
    assert (dt_df["irradiance_w_m2"] >= 0).all(), "Negative irradiance values found"

def test_wind_speed_nonnegative(dt_df):
    assert (dt_df["wind_speed_ms"] >= 0).all(), "Negative wind speed values found"


# ── Source-integrity tests ────────────────────────────────────────────────────

def test_original_dataset_not_modified(raw_df):
    """Reload the source CSV and confirm its columns are unchanged."""
    fresh = pd.read_csv(SOURCE_CSV, nrows=1)
    original_cols = [
        "timestamp_utc", "latitude", "longitude", "temperature_c",
        "wind_speed_mps", "solar_irradiance_wm2", "precipitation_mm",
        "surface_pressure_kpa", "pv_available_kw", "wind_available_kw",
        "weather_quality_flag", "weather_source", "scenario_name",
    ]
    for col in original_cols:
        assert col in fresh.columns, f"Original column missing from source CSV: {col}"

def test_derived_columns_not_in_dt_export(dt_df):
    """pv_available_kw and wind_available_kw must NOT appear in the DT export."""
    assert "pv_available_kw"   not in dt_df.columns
    assert "wind_available_kw" not in dt_df.columns


# ── Optional-column tests ─────────────────────────────────────────────────────

def test_optional_columns_do_not_break_required_interface(dt_df):
    """Extra columns must not interfere with the four required columns."""
    subset = dt_df[DT_REQUIRED]
    assert list(subset.columns) == DT_REQUIRED
    assert subset.isna().sum().sum() == 0

def test_quality_flag_column_present(dt_df):
    assert "weather_quality_flag" in dt_df.columns

def test_scenario_name_column_present(dt_df):
    assert "scenario_name" in dt_df.columns
