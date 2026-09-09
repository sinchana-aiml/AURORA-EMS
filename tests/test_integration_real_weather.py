# tests/test_integration_real_weather.py
# ─────────────────────────────────────────────────────────────────────────────
# Integration test: Member 2 NASA POWER weather sample -> Member 1 Digital Twin
# Does NOT modify any production physics, config values, or Member 2 source data.
# ─────────────────────────────────────────────────────────────────────────────

import os
import pytest

SAMPLE_CSV = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "sample", "digital_twin_weather_24h.csv")
)

from src.digital_twin.weather_loader import load_weather_csv, validate_weather_records
from src.digital_twin.simulation import run_simulation
import config

INITIAL_SOC_KWH     = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION
INITIAL_FUEL_LITRES = config.FUEL_TANK_LITRES
MIN_SOC_KWH         = config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION
MAX_SOC_KWH         = config.BATTERY_CAPACITY_KWH


@pytest.fixture(scope="module")
def loaded_records():
    return load_weather_csv(SAMPLE_CSV)


@pytest.fixture(scope="module")
def simulation_results(loaded_records):
    return run_simulation(
        weather_records     = loaded_records,
        initial_soc_kwh     = INITIAL_SOC_KWH,
        initial_fuel_litres = INITIAL_FUEL_LITRES,
    )


# ── Loading checks ────────────────────────────────────────────────────────────

def test_exactly_24_rows_loaded(loaded_records):
    assert len(loaded_records) == 24


def test_required_fields_present(loaded_records):
    for r in loaded_records:
        assert "timestamp" in r
        assert "temperature_c" in r
        assert "irradiance_w_m2" in r
        assert "wind_speed_ms" in r


def test_timestamps_are_utc(loaded_records):
    for r in loaded_records:
        assert "+00:00" in r["timestamp"], (
            f"Expected UTC offset in timestamp, got: {r['timestamp']}"
        )


def test_timestamps_are_ordered(loaded_records):
    timestamps = [r["timestamp"] for r in loaded_records]
    assert timestamps == sorted(timestamps)


def test_validation_passes(loaded_records):
    assert validate_weather_records(loaded_records) is True


# ── Simulation output checks ──────────────────────────────────────────────────

def test_simulation_returns_24_rows(simulation_results):
    assert len(simulation_results) == 24


def test_soc_stays_within_bounds(simulation_results):
    for r in simulation_results:
        assert MIN_SOC_KWH <= r["battery_soc_kwh"] <= MAX_SOC_KWH, (
            f"SOC out of bounds at {r['timestamp']}: {r['battery_soc_kwh']:.2f} kWh"
        )


def test_fuel_never_increases(simulation_results):
    for i in range(1, len(simulation_results)):
        assert simulation_results[i]["fuel_remaining_litres"] <= (
            simulation_results[i - 1]["fuel_remaining_litres"] + 1e-6
        ), f"Fuel increased at hour {i}"


def test_solar_wind_recalculated_by_digital_twin(loaded_records, simulation_results):
    """Solar and wind outputs must be calculated by the DT, not copied from input."""
    for rec, res in zip(loaded_records, simulation_results):
        assert "pv_available_kw" not in rec
        assert "wind_available_kw" not in rec
        assert "solar_power_kw" in res
        assert "wind_power_kw" in res
        assert res["solar_power_kw"] >= 0.0
        assert res["wind_power_kw"] >= 0.0


def test_input_file_not_modified():
    """Confirm the sample CSV mtime is not changed by the simulation."""
    mtime_before = os.path.getmtime(SAMPLE_CSV)
    load_weather_csv(SAMPLE_CSV)
    run_simulation(
        weather_records     = load_weather_csv(SAMPLE_CSV),
        initial_soc_kwh     = INITIAL_SOC_KWH,
        initial_fuel_litres = INITIAL_FUEL_LITRES,
    )
    mtime_after = os.path.getmtime(SAMPLE_CSV)
    assert mtime_before == mtime_after
