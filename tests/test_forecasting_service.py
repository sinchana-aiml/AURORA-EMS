# tests/test_forecasting_service.py
# ─────────────────────────────────────────────────────────────────────────────
# Tests for Member 3 Forecasting Service & Member 4 Interface (Phase 3)
# Verifies:
#   - ForecastService initialization and mode readiness
#   - 24-hour and 48-hour horizon generation conforming to Member 4 schema
#   - All 21 contract columns, types, step indices, and monotonic timestamps
#   - Physical limits: solar in [0, 40 kW], wind in [0, 50 kW], total >= 45 kW
#   - Monotonicity: P10 <= P50 <= P90 for all targets
#   - Net load identity: net_load_p50 == total_p50 - (solar_p50 + wind_p50)
#   - Offline comms-outage mode switching and adaptive uncertainty widening
#   - Severe storm (>= 20 m/s) and turbine cutout (>= 25 m/s) risk flagging
#   - Standalone get_forecast() convenience function
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

# Complete 21-column schema required by Member 4
EXPECTED_CONTRACT_COLUMNS = [
    "timestamp",
    "step_ahead",
    "solar_power_kw_p10",
    "solar_power_kw_p50",
    "solar_power_kw_p90",
    "wind_power_kw_p10",
    "wind_power_kw_p50",
    "wind_power_kw_p90",
    "electrical_load_kw",
    "heating_load_kw_p50",
    "total_load_kw_p10",
    "total_load_kw_p50",
    "total_load_kw_p90",
    "net_load_kw_p50",
    "temperature_c_pred",
    "wind_speed_ms_pred",
    "irradiance_w_m2_pred",
    "storm_risk_flag",
    "turbine_cutout_risk",
    "confidence_score",
    "forecast_mode",
]


@pytest.fixture(scope="module")
def service():
    """Initializes ForecastService once for test module."""
    return ForecastService(auto_initialize=True)


# ── Core Interface Tests ──────────────────────────────────────────────────────

def test_service_initialization(service):
    """Verifies that ForecastService initializes cleanly with climatology available."""
    assert service is not None
    assert service.climatology is not None
    assert service.climatology.is_fitted is True


def test_24h_forecast_contract_schema(service):
    """Verifies that a 24-hour forecast produces all 21 contract columns with exact row count."""
    start_ts = "2024-07-01T00:00:00+00:00"
    df = service.get_24h_forecast(current_timestamp=start_ts)

    assert len(df) == 24
    assert list(df["step_ahead"]) == list(range(1, 25))

    for col in EXPECTED_CONTRACT_COLUMNS:
        assert col in df.columns, f"Missing required contract column: {col}"

    # Confirm timestamps are strictly increasing
    ts = pd.to_datetime(df["timestamp"])
    assert ts.is_monotonic_increasing


def test_48h_horizon_forecast(service):
    """Verifies arbitrary horizon generation up to 48 hours."""
    start_ts = "2024-01-01T12:00:00+00:00"
    df = service.generate_forecast(current_timestamp=start_ts, horizon_hours=48)

    assert len(df) == 48
    assert df["step_ahead"].iloc[0] == 1
    assert df["step_ahead"].iloc[-1] == 48


def test_invalid_horizon_raises_error(service):
    """Verifies that horizon outside [1, 48] raises ValueError."""
    with pytest.raises(ValueError):
        service.generate_forecast("2024-07-01T00:00:00+00:00", horizon_hours=0)

    with pytest.raises(ValueError):
        service.generate_forecast("2024-07-01T00:00:00+00:00", horizon_hours=49)


# ── Physical Realism & Monotonicity Tests ─────────────────────────────────────

def test_physical_limits_conformance(service):
    """Verifies that all predicted powers and loads respect physical station ratings."""
    df = service.get_24h_forecast("2024-01-15T00:00:00+00:00")

    # Solar in [0, 40 kW]
    assert (df["solar_power_kw_p10"] >= 0.0).all()
    assert (df["solar_power_kw_p50"] >= 0.0).all()
    assert (df["solar_power_kw_p90"] <= config.SOLAR_CAPACITY_KW + 1e-4).all()

    # Wind in [0, 50 kW]
    assert (df["wind_power_kw_p10"] >= 0.0).all()
    assert (df["wind_power_kw_p50"] >= 0.0).all()
    assert (df["wind_power_kw_p90"] <= config.WIND_CAPACITY_KW + 1e-4).all()

    # Electrical load is fixed at 30 kW (20 kW critical + 10 kW flexible)
    assert (df["electrical_load_kw"] == 30.0).all()

    # Heating load >= 15 kW
    assert (df["heating_load_kw_p50"] >= config.HEATING_BASE_KW - 1e-4).all()

    # Total load >= 45 kW
    assert (df["total_load_kw_p50"] >= 45.0 - 1e-4).all()


def test_probabilistic_quantile_monotonicity(service):
    """Verifies P10 <= P50 <= P90 holds unconditionally across all prediction rows."""
    df = service.get_24h_forecast("2024-06-21T00:00:00+00:00")  # Polar night solstice

    assert (df["solar_power_kw_p10"] <= df["solar_power_kw_p50"] + 1e-6).all()
    assert (df["solar_power_kw_p50"] <= df["solar_power_kw_p90"] + 1e-6).all()

    assert (df["wind_power_kw_p10"] <= df["wind_power_kw_p50"] + 1e-6).all()
    assert (df["wind_power_kw_p50"] <= df["wind_power_kw_p90"] + 1e-6).all()

    assert (df["total_load_kw_p10"] <= df["total_load_kw_p50"] + 1e-6).all()
    assert (df["total_load_kw_p50"] <= df["total_load_kw_p90"] + 1e-6).all()


def test_net_load_identity(service):
    """Verifies net_load_kw_p50 == total_load_kw_p50 - (solar_p50 + wind_p50)."""
    df = service.get_24h_forecast("2024-12-21T00:00:00+00:00")  # Polar summer solstice

    expected_net = df["total_load_kw_p50"] - (df["solar_power_kw_p50"] + df["wind_power_kw_p50"])
    np.testing.assert_allclose(df["net_load_kw_p50"].to_numpy(), expected_net.to_numpy(), atol=1e-4)


# ── Offline Mode & Comms Outage Handling ─────────────────────────────────────

def test_comms_outage_uncertainty_widening(service):
    """
    Verifies that setting is_offline=True:
      - Expands the uncertainty margin (lower P10, higher P90).
      - Reflects offline_climatology_comms_outage in forecast_mode.
      - Lowers confidence_score compared to normal operation.
    """
    ts = "2024-03-21T00:00:00+00:00"
    df_normal = service.generate_forecast(ts, horizon_hours=12, is_offline=False)
    df_offline = service.generate_forecast(ts, horizon_hours=12, is_offline=True)

    # Uncertainty interval for offline must be wider
    width_normal = df_normal["wind_power_kw_p90"] - df_normal["wind_power_kw_p10"]
    width_offline = df_offline["wind_power_kw_p90"] - df_offline["wind_power_kw_p10"]
    assert (width_offline >= width_normal - 1e-6).all()

    assert (df_offline["forecast_mode"] == "offline_climatology_comms_outage").all()
    assert (df_offline["confidence_score"] < df_normal["confidence_score"]).all()


# ── Severe Weather & Risk Flagging Tests ─────────────────────────────────────

def test_storm_and_cutout_risk_flags(service):
    """Verifies storm and cutout risk boolean flags under extreme wind conditions."""
    # Test through simulated weather feed
    extreme_weather = [
        {"timestamp": "2024-07-01T01:00:00+00:00", "wind_speed_ms": 15.0, "temperature_c": -20.0, "irradiance_w_m2": 0.0},
        {"timestamp": "2024-07-01T02:00:00+00:00", "wind_speed_ms": 21.0, "temperature_c": -20.0, "irradiance_w_m2": 0.0},  # storm >= 20
        {"timestamp": "2024-07-01T03:00:00+00:00", "wind_speed_ms": 26.0, "temperature_c": -20.0, "irradiance_w_m2": 0.0},  # cutout >= 25
    ]
    df = service._predict_ml(
        future_timestamps=[pd.Timestamp(w["timestamp"]) for w in extreme_weather],
        weather_forecast_feed=extreme_weather,
        recent_history=None,
    )

    # Row 0 (15 m/s): neither storm nor cutout
    assert df.loc[0, "storm_risk_flag"] is False
    assert df.loc[0, "turbine_cutout_risk"] is False

    # Row 1 (21 m/s): storm risk True, cutout risk False
    assert df.loc[1, "storm_risk_flag"] is True
    assert df.loc[1, "turbine_cutout_risk"] is False

    # Row 2 (26 m/s): both storm and cutout True
    assert df.loc[2, "storm_risk_flag"] is True
    assert df.loc[2, "turbine_cutout_risk"] is True


# ── Functional get_forecast API Test ─────────────────────────────────────────

def test_get_forecast_function():
    """Verifies standalone get_forecast() direct entry point."""
    df = get_forecast("2024-08-01T00:00:00+00:00", horizon_hours=6)
    assert len(df) == 6
    assert "net_load_kw_p50" in df.columns
    assert "confidence_score" in df.columns
