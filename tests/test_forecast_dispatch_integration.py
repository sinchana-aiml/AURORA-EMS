# tests/test_forecast_dispatch_integration.py
# Member 4 — Member 3 Forecasting → Member 4 Dispatch Integration Tests
#
# Verifies that the real Member 3 ForecastService output can be consumed
# directly by the Member 4 optimized_dispatch_lookahead() without any
# manual column fabrication.
#
# Scenarios tested:
#   1. Normal operation
#   2. Flexible load enabled (include_flexible=True)
#   3. Flexible load disabled (include_flexible=False)
#   4. Low renewable generation (offline climatology, winter night)
#   5. Storm / high-wind condition (storm_mode=True in dispatch)
#   6. Generator failure (G1 unavailable)
#   7. Low-fuel scenario
#   8. Communication-loss / offline forecast

import pytest
import config

from src.forecasting.service import ForecastService, get_forecast
from src.forecasting.validation import validate_forecast_output
from src.dispatch.optimizer import optimized_dispatch_lookahead

TIMESTAMP = "2024-07-01T00:00:00+00:00"  # Antarctic winter — low solar, high wind


def _forecast_to_dispatch_records(forecast_df):
    """
    Convert Member 3 DataFrame to the list-of-dicts format that
    optimized_dispatch_lookahead() expects.

    Member 4's optimizer needs per-hour dicts with:
        load_total_kw          <- total_load_kw_p50
        renewable_available_kw <- solar_power_kw_p50 + wind_power_kw_p50
        timestamp_utc          <- timestamp
    """
    records = []
    for _, row in forecast_df.iterrows():
        records.append({
            "timestamp_utc":          row["timestamp"],
            "load_total_kw":          float(row["total_load_kw_p50"]),
            "renewable_available_kw": float(row["solar_power_kw_p50"]
                                            + row["wind_power_kw_p50"]),
        })
    return records


def _run_dispatch(forecast_df, **kwargs):
    """Validate forecast, convert, run DP optimizer, return results list."""
    validate_forecast_output(forecast_df)
    records = _forecast_to_dispatch_records(forecast_df)
    initial_soc = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION
    return optimized_dispatch_lookahead(
        records=records,
        initial_soc_kwh=initial_soc,
        initial_fuel_litres=config.FUEL_TANK_LITRES,
        **kwargs,
    )


def _assert_dispatch_safety(results, allow_unmet=False):
    """Common safety assertions for every dispatch result."""
    assert results, "Dispatch returned empty results"
    min_soc = config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION

    for i, r in enumerate(results):
        assert r["battery_soc_kwh"] >= min_soc - 1e-3, \
            f"Hour {i}: SOC {r['battery_soc_kwh']:.2f} below floor {min_soc}"
        assert r["fuel_remaining_litres"] >= -1e-6, \
            f"Hour {i}: negative fuel {r['fuel_remaining_litres']:.4f}"
        assert r["generator_1_kw"] <= config.GENERATOR_1_RATED_KW + 1e-6, \
            f"Hour {i}: G1 {r['generator_1_kw']} exceeds rated {config.GENERATOR_1_RATED_KW}"
        assert r["generator_2_kw"] <= config.GENERATOR_2_RATED_KW + 1e-6, \
            f"Hour {i}: G2 {r['generator_2_kw']} exceeds rated {config.GENERATOR_2_RATED_KW}"
        if not allow_unmet:
            assert r["critical_load_served"], \
                f"Hour {i}: critical load not served"
            assert r["unmet_load_kw"] < 1e-3, \
                f"Hour {i}: unmet load {r['unmet_load_kw']:.4f} kW"


# ── Scenario 1: Normal operation ─────────────────────────────────────────────

def test_normal_operation():
    df = get_forecast(TIMESTAMP, horizon_hours=24, include_flexible=True)
    results = _run_dispatch(df)
    _assert_dispatch_safety(results)
    assert len(results) == 24


# ── Scenario 2: Flexible load enabled ────────────────────────────────────────

def test_flexible_load_enabled():
    df = get_forecast(TIMESTAMP, horizon_hours=24, include_flexible=True)
    assert df["electrical_load_kw"].iloc[0] == pytest.approx(
        config.BASE_LOAD_KW + config.FLEXIBLE_LOAD_KW
    )
    results = _run_dispatch(df)
    _assert_dispatch_safety(results)


# ── Scenario 3: Flexible load disabled ───────────────────────────────────────

def test_flexible_load_disabled():
    df = get_forecast(TIMESTAMP, horizon_hours=24, include_flexible=False)
    assert df["electrical_load_kw"].iloc[0] == pytest.approx(config.BASE_LOAD_KW)
    results = _run_dispatch(df)
    _assert_dispatch_safety(results)
    # Critical-only load is lower — fuel use should be <= flexible case
    df_flex = get_forecast(TIMESTAMP, horizon_hours=24, include_flexible=True)
    results_flex = _run_dispatch(df_flex)
    fuel_noflex = sum(r["fuel_used_litres"] for r in results)
    fuel_flex   = sum(r["fuel_used_litres"] for r in results_flex)
    assert fuel_noflex <= fuel_flex + 1e-3


# ── Scenario 4: Low renewable (offline climatology, winter night) ─────────────

def test_low_renewable_generation():
    # Antarctic winter midnight — solar is zero, wind may be low
    df = get_forecast("2024-06-21T12:00:00+00:00", horizon_hours=24,
                      include_flexible=True)
    total_renewable = (df["solar_power_kw_p50"] + df["wind_power_kw_p50"]).sum()
    # Just confirm we can dispatch even when renewables are low
    results = _run_dispatch(df)
    _assert_dispatch_safety(results)
    assert len(results) == 24


# ── Scenario 5: Storm / high-wind (storm_mode in dispatch) ───────────────────

def test_storm_mode_dispatch():
    df = get_forecast(TIMESTAMP, horizon_hours=24, include_flexible=True)
    results = _run_dispatch(df, storm_mode=True)
    _assert_dispatch_safety(results)
    # storm_mode cuts renewables to 60% — generators should run more
    results_normal = _run_dispatch(df, storm_mode=False)
    fuel_storm  = sum(r["fuel_used_litres"] for r in results)
    fuel_normal = sum(r["fuel_used_litres"] for r in results_normal)
    assert fuel_storm >= fuel_normal - 1e-3


# ── Scenario 6: Generator 1 failure ──────────────────────────────────────────

def test_g1_failure():
    df = get_forecast(TIMESTAMP, horizon_hours=24, include_flexible=True)
    results = _run_dispatch(df, generator_1_available=False)
    _assert_dispatch_safety(results)
    for i, r in enumerate(results):
        assert r["generator_1_kw"] == pytest.approx(0.0), \
            f"Hour {i}: G1 should be 0 when unavailable"


# ── Scenario 7: Low-fuel scenario ────────────────────────────────────────────

def test_low_fuel_scenario():
    df = get_forecast(TIMESTAMP, horizon_hours=24, include_flexible=True)
    validate_forecast_output(df)
    records = _forecast_to_dispatch_records(df)
    initial_soc = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION
    results = optimized_dispatch_lookahead(
        records=records,
        initial_soc_kwh=initial_soc,
        initial_fuel_litres=config.LOW_FUEL_THRESHOLD_L,
    )
    for r in results:
        assert r["fuel_remaining_litres"] >= -1e-6
        assert r["battery_soc_kwh"] >= (
            config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION - 1e-3
        )
    # At least some hours should activate low_fuel_mode
    assert any(r["low_fuel_mode"] for r in results)


# ── Scenario 8: Communication loss (offline forecast + dispatch flag) ─────────

def test_communication_loss():
    svc = ForecastService()
    df = svc.generate_forecast(TIMESTAMP, horizon_hours=24, is_offline=True,
                               include_flexible=True)
    assert df["forecast_mode"].iloc[0] == "offline_climatology_comms_outage"
    # Confidence should be lower than normal offline
    df_normal = get_forecast(TIMESTAMP, horizon_hours=24, include_flexible=True)
    assert df["confidence_score"].mean() < df_normal["confidence_score"].mean()

    results = _run_dispatch(df, communication_loss=True)
    _assert_dispatch_safety(results)
    # G2 must be zero throughout (communication_loss disables G2)
    for i, r in enumerate(results):
        assert r["generator_2_kw"] == pytest.approx(0.0), \
            f"Hour {i}: G2 should be 0 during comms loss"


# ── Schema / contract integrity ───────────────────────────────────────────────

def test_forecast_output_passes_member3_validation():
    """Member 3's own validator must accept the output before dispatch uses it."""
    df = get_forecast(TIMESTAMP, horizon_hours=24, include_flexible=True)
    # validate_forecast_output raises ForecastValidationError on failure
    validate_forecast_output(df)


def test_dispatch_output_schema_complete():
    """Every dispatch result dict must contain all required output fields."""
    required = {
        "renewable_used_kw", "renewable_curtailed_kw",
        "battery_discharge_kw", "battery_charge_kw", "battery_soc_kwh",
        "generator_1_kw", "generator_2_kw", "generator_total_kw",
        "fuel_used_litres", "fuel_remaining_litres",
        "unmet_load_kw", "critical_load_served",
        "battery_reserve_kwh", "low_fuel_mode", "flexible_load_shed_kw",
    }
    df = get_forecast(TIMESTAMP, horizon_hours=24, include_flexible=True)
    results = _run_dispatch(df)
    for i, r in enumerate(results):
        missing = required - set(r.keys())
        assert not missing, f"Hour {i} missing fields: {missing}"


def test_confidence_score_maps_to_forecast_confidence():
    """
    When Member 3 reports low confidence, the dispatch reserve should be
    higher than when confidence is high.
    """
    from src.dispatch.optimizer import optimized_dispatch

    result_high = optimized_dispatch(60.0, 20.0, 210.0, forecast_confidence="high")
    result_low  = optimized_dispatch(60.0, 20.0, 210.0, forecast_confidence="low")
    assert result_low["battery_reserve_kwh"] > result_high["battery_reserve_kwh"]
