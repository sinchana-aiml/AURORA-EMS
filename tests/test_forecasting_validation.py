# tests/test_forecasting_validation.py
# ─────────────────────────────────────────────────────────────────────────────
# Tests for Member 3 Forecasting Output Validation & Integration (Phase 4)
# Verifies:
#   - Valid Phase 3 forecast DataFrame passes validation.
#   - Missing required contract column is rejected.
#   - Empty DataFrame is rejected.
#   - Incorrect step_ahead sequence is rejected.
#   - NaN/infinite numeric values are rejected.
#   - Solar P10 <= P50 <= P90 quantile monotonicity.
#   - Wind P10 <= P50 <= P90 quantile monotonicity.
#   - Total load P10 <= P50 <= P90 quantile monotonicity.
#   - Solar power bounds [0, SOLAR_CAPACITY_KW].
#   - Wind power bounds [0, WIND_CAPACITY_KW].
#   - Negative electrical/heating/total load is rejected.
#   - net_load_kw_p50 identity: net_load = total_load - (solar + wind).
#   - Risk flags must be boolean.
#   - Confidence score must be between 0 and 1.
#   - Valid forecast modes are accepted; invalid modes are rejected.
#   - Valid weather input passes validation.
#   - Member 2 raw weather aliases are normalized:
#       timestamp_utc -> timestamp
#       solar_irradiance_wm2 -> irradiance_w_m2
#       wind_speed_mps -> wind_speed_ms
#   - Invalid weather input is rejected.
#   - include_flexible=True/False electrical load behavior.
#   - Timestamp ordering violations are rejected.
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
from src.forecasting.service import ForecastService, get_forecast
from src.forecasting.validation import (
    validate_forecast_output,
    validate_weather_input,
    normalize_weather_columns,
    ForecastValidationError,
    EXPECTED_CONTRACT_COLUMNS,
    CANONICAL_WEATHER_FIELDS,
    VALID_FORECAST_MODES,
)


@pytest.fixture(scope="module")
def service():
    """Initializes ForecastService once for testing."""
    return ForecastService(auto_initialize=True)


@pytest.fixture
def valid_forecast(service):
    """Provides a fresh, valid 24h forecast DataFrame."""
    return service.get_24h_forecast("2024-07-01T00:00:00+00:00")


# ── Valid Forecast Acceptance ────────────────────────────────────────────────

def test_valid_phase3_forecast_passes_validation(valid_forecast):
    """Verifies that a normal Phase 3 forecast passes validation completely."""
    validated = validate_forecast_output(valid_forecast)
    assert validated is not None
    assert len(validated) == 24
    assert list(validated.columns) == list(valid_forecast.columns)


def test_empty_dataframe_rejected():
    """Verifies that an empty DataFrame is rejected with ForecastValidationError."""
    empty_df = pd.DataFrame()
    with pytest.raises(ForecastValidationError, match="Forecast output must contain at least one row|empty"):
        validate_forecast_output(empty_df)


# ── Schema & Column Requirements ─────────────────────────────────────────────

def test_missing_required_column_rejected(valid_forecast):
    """Verifies that dropping any required contract column raises ForecastValidationError."""
    for col in ["solar_power_kw_p50", "net_load_kw_p50", "storm_risk_flag", "confidence_score"]:
        corrupted = valid_forecast.drop(columns=[col])
        with pytest.raises(ForecastValidationError, match="missing required contract column"):
            validate_forecast_output(corrupted)


# ── Step Ahead Sequence ──────────────────────────────────────────────────────

def test_incorrect_step_ahead_sequence_rejected(valid_forecast):
    """Verifies that non-consecutive or non-1-based step_ahead values are rejected."""
    corrupted = valid_forecast.copy()
    corrupted.loc[2, "step_ahead"] = 99
    with pytest.raises(ForecastValidationError, match="step_ahead"):
        validate_forecast_output(corrupted)


# ── Timestamp Ordering & Validity ───────────────────────────────────────────

def test_timestamp_ordering_violation_rejected(valid_forecast):
    """Verifies that non-increasing timestamps raise ForecastValidationError."""
    corrupted = valid_forecast.copy()
    # Reverse timestamps
    corrupted["timestamp"] = valid_forecast["timestamp"].iloc[::-1].values
    with pytest.raises(ForecastValidationError, match="monotonically increasing"):
        validate_forecast_output(corrupted)


def test_invalid_timestamp_string_rejected(valid_forecast):
    """Verifies that unparseable timestamps raise ForecastValidationError."""
    corrupted = valid_forecast.copy()
    corrupted.loc[0, "timestamp"] = "not-a-date"
    with pytest.raises(ForecastValidationError, match="timestamp"):
        validate_forecast_output(corrupted)


# ── Numeric NaN and Inf Rejection ────────────────────────────────────────────

def test_nan_numeric_value_rejected(valid_forecast):
    """Verifies that NaN in any numerical forecast column is rejected."""
    for col in ["wind_power_kw_p50", "total_load_kw_p10", "temperature_c_pred"]:
        corrupted = valid_forecast.copy()
        corrupted.loc[1, col] = np.nan
        with pytest.raises(ForecastValidationError, match="non-numeric or NaN values|NaN"):
            validate_forecast_output(corrupted)


def test_inf_numeric_value_rejected(valid_forecast):
    """Verifies that infinite values in any numerical forecast column are rejected."""
    for col in ["solar_power_kw_p90", "net_load_kw_p50", "irradiance_w_m2_pred"]:
        corrupted = valid_forecast.copy()
        corrupted.loc[3, col] = np.inf
        with pytest.raises(ForecastValidationError, match="non-finite values|infinite"):
            validate_forecast_output(corrupted)


# ── Quantile Monotonicity (P10 <= P50 <= P90) ────────────────────────────────

def test_solar_quantile_monotonicity_rejected(valid_forecast):
    """Verifies rejection when solar P10 > P50 or P50 > P90."""
    corrupted1 = valid_forecast.copy()
    corrupted1.loc[0, "solar_power_kw_p10"] = corrupted1.loc[0, "solar_power_kw_p50"] + 10.0
    with pytest.raises(ForecastValidationError, match="P10 <= P50 <= P90"):
        validate_forecast_output(corrupted1)

    corrupted2 = valid_forecast.copy()
    corrupted2.loc[0, "solar_power_kw_p50"] = corrupted2.loc[0, "solar_power_kw_p90"] + 5.0
    with pytest.raises(ForecastValidationError, match="P10 <= P50 <= P90"):
        validate_forecast_output(corrupted2)


def test_wind_quantile_monotonicity_rejected(valid_forecast):
    """Verifies rejection when wind P10 > P50 or P50 > P90."""
    corrupted = valid_forecast.copy()
    corrupted.loc[2, "wind_power_kw_p10"] = corrupted.loc[2, "wind_power_kw_p50"] + 5.0
    with pytest.raises(ForecastValidationError, match="P10 <= P50 <= P90"):
        validate_forecast_output(corrupted)


def test_total_load_quantile_monotonicity_rejected(valid_forecast):
    """Verifies rejection when total load P10 > P50 or P50 > P90."""
    corrupted = valid_forecast.copy()
    corrupted.loc[4, "total_load_kw_p50"] = corrupted.loc[4, "total_load_kw_p90"] + 10.0
    with pytest.raises(ForecastValidationError, match="P10 <= P50 <= P90"):
        validate_forecast_output(corrupted)


# ── Physical Generation Limits ───────────────────────────────────────────────

def test_solar_capacity_exceeded_rejected(valid_forecast):
    """Verifies that solar power exceeding SOLAR_CAPACITY_KW is rejected."""
    corrupted = valid_forecast.copy()
    corrupted.loc[0, "solar_power_kw_p90"] = config.SOLAR_CAPACITY_KW + 10.0
    with pytest.raises(ForecastValidationError, match="Solar power forecast exceeds configured solar capacity|exceeds rated capacity"):
        validate_forecast_output(corrupted)


def test_solar_negative_power_rejected(valid_forecast):
    """Verifies that negative solar power is rejected."""
    corrupted = valid_forecast.copy()
    corrupted.loc[0, "solar_power_kw_p10"] = -1.0
    with pytest.raises(ForecastValidationError, match="Solar power forecast contains negative values|cannot be negative"):
        validate_forecast_output(corrupted)


def test_wind_capacity_exceeded_rejected(valid_forecast):
    """Verifies that wind power exceeding WIND_CAPACITY_KW is rejected."""
    corrupted = valid_forecast.copy()
    corrupted.loc[0, "wind_power_kw_p90"] = config.WIND_CAPACITY_KW + 15.0
    with pytest.raises(ForecastValidationError, match="Wind power forecast exceeds configured wind capacity|exceeds rated capacity"):
        validate_forecast_output(corrupted)


def test_wind_negative_power_rejected(valid_forecast):
    """Verifies that negative wind power is rejected."""
    corrupted = valid_forecast.copy()
    corrupted.loc[0, "wind_power_kw_p10"] = -0.5
    with pytest.raises(ForecastValidationError, match="Wind power forecast contains negative values|cannot be negative"):
        validate_forecast_output(corrupted)


# ── Non-negative Station Loads ───────────────────────────────────────────────

def test_negative_load_rejected(valid_forecast):
    """Verifies that negative electrical, heating, or total load is rejected."""
    for col in ["electrical_load_kw", "heating_load_kw_p50", "total_load_kw_p10"]:
        corrupted = valid_forecast.copy()
        corrupted.loc[0, col] = -5.0
        with pytest.raises(ForecastValidationError, match="Load forecast.*contains negative values|cannot be negative"):
            validate_forecast_output(corrupted)


# ── Net Load Identity ────────────────────────────────────────────────────────

def test_net_load_identity_violation_rejected(valid_forecast):
    """
    Verifies that net_load_kw_p50 != total_load_kw_p50 - (solar_p50 + wind_p50)
    raises ForecastValidationError.
    """
    corrupted = valid_forecast.copy()
    corrupted.loc[0, "net_load_kw_p50"] = 999.0
    with pytest.raises(ForecastValidationError, match="net-load identity|Net load identity violated"):
        validate_forecast_output(corrupted)


# ── Risk Flags & Confidence Validation ───────────────────────────────────────

def test_risk_flags_must_be_boolean(valid_forecast):
    """Verifies that string or float values in risk flags raise ForecastValidationError."""
    corrupted1 = valid_forecast.copy()
    corrupted1.loc[0, "storm_risk_flag"] = "TRUE"
    with pytest.raises(ForecastValidationError, match="must contain boolean values|contains non-boolean"):
        validate_forecast_output(corrupted1)

    corrupted2 = valid_forecast.copy()
    corrupted2.loc[0, "turbine_cutout_risk"] = 1.0
    with pytest.raises(ForecastValidationError, match="must contain boolean values|contains non-boolean"):
        validate_forecast_output(corrupted2)


def test_confidence_score_range(valid_forecast):
    """Verifies that confidence scores outside [0, 1] raise ForecastValidationError."""
    corrupted_high = valid_forecast.copy()
    corrupted_high.loc[0, "confidence_score"] = 1.5
    with pytest.raises(ForecastValidationError, match="confidence_score must be between 0 and 1|outside \\[0.0, 1.0\\]"):
        validate_forecast_output(corrupted_high)

    corrupted_low = valid_forecast.copy()
    corrupted_low.loc[0, "confidence_score"] = -0.1
    with pytest.raises(ForecastValidationError, match="confidence_score must be between 0 and 1|outside \\[0.0, 1.0\\]"):
        validate_forecast_output(corrupted_low)


# ── Forecast Modes ───────────────────────────────────────────────────────────

def test_valid_forecast_modes_accepted(valid_forecast):
    """Verifies all standard ForecastService modes are recognized as valid."""
    for mode in ["online_ml", "ml_ensemble", "offline_climatology", "offline_climatology_comms_outage"]:
        df = valid_forecast.copy()
        df["forecast_mode"] = mode
        assert validate_forecast_output(df) is not None


def test_invalid_forecast_mode_rejected(valid_forecast):
    """Verifies that unknown or unsupported forecast modes raise ForecastValidationError."""
    corrupted = valid_forecast.copy()
    corrupted.loc[0, "forecast_mode"] = "unsupported_magic_mode"
    with pytest.raises(ForecastValidationError, match="unsupported forecast_mode"):
        validate_forecast_output(corrupted)


# ── Weather Input Compatibility & Aliasing ───────────────────────────────────

def test_valid_weather_input_passes():
    """Verifies that a valid canonical weather feed passes validate_weather_input."""
    weather_df = pd.DataFrame(
        {
            "timestamp": ["2024-07-01T00:00:00+00:00", "2024-07-01T01:00:00+00:00"],
            "temperature_c": [-20.0, -18.5],
            "irradiance_w_m2": [0.0, 50.0],
            "wind_speed_ms": [6.5, 8.0],
        }
    )
    result = validate_weather_input(weather_df)
    assert result is not None
    assert len(result) == 2


def test_member2_weather_aliases_normalization():
    """
    Verifies that Member 2 raw names:
      - timestamp_utc -> timestamp
      - solar_irradiance_wm2 -> irradiance_w_m2
      - wind_speed_mps -> wind_speed_ms
    are automatically normalized and validated.
    """
    raw_df = pd.DataFrame(
        {
            "timestamp_utc": ["2024-07-01T00:00:00+00:00", "2024-07-01T01:00:00+00:00"],
            "temperature_c": [-15.0, -14.0],
            "solar_irradiance_wm2": [100.0, 200.0],
            "wind_speed_mps": [7.0, 9.0],
        }
    )
    normalized = normalize_weather_columns(raw_df)
    for col in CANONICAL_WEATHER_FIELDS:
        assert col in normalized.columns

    validated = validate_weather_input(raw_df)
    assert validated is not None


def test_invalid_weather_input_rejected():
    """Verifies that invalid weather inputs (negative irradiance/wind, extreme temp) are rejected."""
    # Negative irradiance
    with pytest.raises(ValueError, match="irradiance cannot be negative|negative irradiance"):
        validate_weather_input(
            pd.DataFrame(
                {
                    "timestamp": ["2024-07-01T00:00:00+00:00"],
                    "temperature_c": [-20.0],
                    "irradiance_w_m2": [-10.0],
                    "wind_speed_ms": [5.0],
                }
            )
        )

    # Negative wind speed
    with pytest.raises(ValueError, match="wind speed cannot be negative|negative wind_speed"):
        validate_weather_input(
            pd.DataFrame(
                {
                    "timestamp": ["2024-07-01T00:00:00+00:00"],
                    "temperature_c": [-20.0],
                    "irradiance_w_m2": [0.0],
                    "wind_speed_ms": [-2.0],
                }
            )
        )

    # Out-of-bounds temperature (< -90 C)
    with pytest.raises(ValueError, match="temperature must remain within|realistic Earth range"):
        validate_weather_input(
            pd.DataFrame(
                {
                    "timestamp": ["2024-07-01T00:00:00+00:00"],
                    "temperature_c": [-105.0],
                    "irradiance_w_m2": [0.0],
                    "wind_speed_ms": [5.0],
                }
            )
        )


# ── Load Semantics: Critical vs Flexible ─────────────────────────────────────

def test_include_flexible_load_behavior(service):
    """
    Verifies that include_flexible=True yields 30 kW electrical load
    (20 kW base + 10 kW flexible), while include_flexible=False yields
    20 kW electrical load (critical base only).
    """
    ts = "2024-07-01T00:00:00+00:00"
    df_flex = service.generate_forecast(ts, horizon_hours=12, include_flexible=True)
    df_crit = service.generate_forecast(ts, horizon_hours=12, include_flexible=False)

    assert (df_flex["electrical_load_kw"] == 30.0).all()
    assert (df_crit["electrical_load_kw"] == 20.0).all()

    # Total load with flexible load should be exactly 10 kW higher than critical only
    load_diff = df_flex["total_load_kw_p50"] - df_crit["total_load_kw_p50"]
    np.testing.assert_allclose(load_diff.to_numpy(), 10.0, atol=1e-4)

    # Both outputs must pass validation
    assert validate_forecast_output(df_flex) is not None
    assert validate_forecast_output(df_crit) is not None
