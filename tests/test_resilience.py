# tests/test_resilience.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Resilience & Offline Integration tests
#
# Verifies the station keeps producing safe, explainable dispatch decisions
# when the uplink drops, a generator fails, fuel runs low, or the optimizer
# raises — individually and all at once.
# ─────────────────────────────────────────────────────────────────────────────

import pytest

import config
from src.digital_twin import make_test_weather
from src.resilience import (
    ONLINE, OFFLINE, OFFLINE_AUTONOMOUS,
    get_connectivity_status, safe_dispatch, fallback_dispatch,
    run_resilience_scenario, clear_cache,
    MODE_FALLBACK,
)


@pytest.fixture(autouse=True)
def _clean_cache():
    """Each test starts from a known cache state."""
    clear_cache()
    yield
    clear_cache()


WEATHER_24H = make_test_weather(24)
CALM_DARK_COLD = {
    "timestamp": "2024-07-01T00:00",
    "temperature_c": -40.0,
    "irradiance_w_m2": 0.0,
    "wind_speed_ms": 1.0,
}


# ── Connectivity indicator ────────────────────────────────────────────────────

def test_connectivity_status_online():
    assert get_connectivity_status(offline=False) == ONLINE


def test_connectivity_status_offline_then_autonomous():
    assert get_connectivity_status(offline=True, consecutive_offline_hours=1) == OFFLINE
    assert get_connectivity_status(offline=True, consecutive_offline_hours=3) == OFFLINE_AUTONOMOUS


# ── Fallback policy ───────────────────────────────────────────────────────────

def test_fallback_triggers_when_no_optimizer():
    result = safe_dispatch(CALM_DARK_COLD,
                           battery_soc_kwh=config.BATTERY_CAPACITY_KWH * 0.7,
                           fuel_remaining_litres=config.FUEL_TANK_LITRES)
    assert result["fallback_triggered"] is True
    assert result["dispatch_mode"] == MODE_FALLBACK
    assert result["reasoning"]


def test_fallback_triggers_when_optimizer_raises():
    def broken_optimizer(*args, **kwargs):
        raise RuntimeError("forecast model unavailable")

    result = safe_dispatch(CALM_DARK_COLD,
                           battery_soc_kwh=config.BATTERY_CAPACITY_KWH * 0.7,
                           fuel_remaining_litres=config.FUEL_TANK_LITRES,
                           optimizer=broken_optimizer)
    assert result["fallback_triggered"] is True
    assert "forecast model unavailable" in result["fallback_reason"]
    # The station still has a complete, usable dispatch decision.
    assert result["critical_load_served"] is True


def test_working_optimizer_is_used_and_not_overridden():
    def good_optimizer(weather, soc, fuel, g1, g2, ts):
        base = fallback_dispatch(weather, soc, fuel, g1, g2, ts)
        base["dispatch_mode"] = "OPTIMIZED"
        return base

    result = safe_dispatch(CALM_DARK_COLD,
                           battery_soc_kwh=config.BATTERY_CAPACITY_KWH * 0.7,
                           fuel_remaining_litres=config.FUEL_TANK_LITRES,
                           optimizer=good_optimizer)
    assert result["fallback_triggered"] is False
    assert result["dispatch_mode"] == "OPTIMIZED"


def test_fallback_never_raises_on_empty_fuel_and_failed_generators():
    result = safe_dispatch(CALM_DARK_COLD,
                           battery_soc_kwh=config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION,
                           fuel_remaining_litres=0.0,
                           generator_1_available=False,
                           generator_2_available=False)
    # Worst case: no sun, no wind, no fuel, no generators, battery at reserve.
    # The system must still return an explainable decision rather than crash.
    assert result is not None
    assert result["reasoning"]
    assert result["flexible_load_shed"] is True


# ── Battery reserve is respected ──────────────────────────────────────────────

def test_battery_never_discharges_below_reserve():
    results = run_resilience_scenario(WEATHER_24H)
    floor_kwh = config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION
    assert all(r["battery_soc_kwh"] >= floor_kwh - 1e-6 for r in results)


# ── Offline mode ──────────────────────────────────────────────────────────────

def test_offline_hours_report_offline_status_and_use_cache():
    results = run_resilience_scenario(WEATHER_24H, comms_outage_hours=range(6, 12))
    offline_results = results[6:12]
    assert all(r["connectivity_status"].startswith("OFFLINE") for r in offline_results)
    assert all(r["used_cached_weather"] for r in offline_results)
    # Hours outside the outage stay online.
    assert results[0]["connectivity_status"] == ONLINE
    assert results[20]["connectivity_status"] == ONLINE


def test_extended_outage_escalates_to_autonomous():
    results = run_resilience_scenario(WEATHER_24H, comms_outage_hours=range(0, 8))
    statuses = [r["connectivity_status"] for r in results[:8]]
    assert OFFLINE in statuses
    assert OFFLINE_AUTONOMOUS in statuses


def test_offline_never_calls_the_optimizer():
    calls = []

    def counting_optimizer(weather, soc, fuel, g1, g2, ts):
        calls.append(weather)
        return fallback_dispatch(weather, soc, fuel, g1, g2, ts)

    run_resilience_scenario(WEATHER_24H, comms_outage_hours=range(0, 24),
                            optimizer=counting_optimizer)
    assert calls == []


def test_reconnection_restores_online_status():
    results = run_resilience_scenario(WEATHER_24H, comms_outage_hours=range(0, 6))
    assert results[5]["connectivity_status"].startswith("OFFLINE")
    assert results[6]["connectivity_status"] == ONLINE


# ── Combined failure scenario ─────────────────────────────────────────────────

def test_combined_storm_generator_failure_lowfuel_offline():
    results = run_resilience_scenario(
        WEATHER_24H,
        storm=True,
        failed_generator="G1",
        comms_outage_hours=range(0, 24),
        initial_fuel_litres=config.LOW_FUEL_THRESHOLD_L,
    )
    assert len(results) == 24
    # Every hour still produces an explainable decision while offline.
    assert all(r["reasoning"] for r in results)
    assert all(r["connectivity_status"].startswith("OFFLINE") for r in results)
    assert all(r["dispatch_mode"] == MODE_FALLBACK for r in results)
    # The failed generator never produces power.
    assert all(r["generator_1_power_kw"] == 0.0 for r in results)


def test_low_fuel_warning_is_raised():
    results = run_resilience_scenario(
        WEATHER_24H, initial_fuel_litres=config.LOW_FUEL_THRESHOLD_L)
    assert any(r["low_fuel_warning"] for r in results)


def test_scenario_runner_does_not_mutate_input_records():
    before = [dict(r) for r in WEATHER_24H]
    run_resilience_scenario(WEATHER_24H, storm=True, comms_outage_hours=[0, 1])
    assert WEATHER_24H == before
