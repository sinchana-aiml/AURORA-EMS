# tests/test_simulation.py
import pytest
import config
from src.digital_twin.simulation import make_test_weather, run_simulation

INIT_SOC  = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION  # 210 kWh
INIT_FUEL = config.FUEL_TANK_LITRES                                              # 5000 L


@pytest.fixture(scope="module")
def sim_normal():
    return run_simulation(make_test_weather(24), INIT_SOC, INIT_FUEL)


@pytest.fixture(scope="module")
def sim_g1fail():
    return run_simulation(make_test_weather(24), INIT_SOC, INIT_FUEL,
                          generator_1_available=False)


class TestSimulationRowCount:
    def test_24_rows_returned(self, sim_normal):
        assert len(sim_normal) == 24

    def test_row_count_matches_input(self):
        weather = make_test_weather(12)
        results = run_simulation(weather, INIT_SOC, INIT_FUEL)
        assert len(results) == 12


class TestSimulationTimestamps:
    def test_timestamps_in_order(self, sim_normal):
        ts = [r["timestamp"] for r in sim_normal]
        assert ts == sorted(ts)

    def test_first_timestamp_matches_weather(self, sim_normal):
        weather = make_test_weather(24)
        assert sim_normal[0]["timestamp"] == weather[0]["timestamp"]

    def test_last_timestamp_matches_weather(self, sim_normal):
        weather = make_test_weather(24)
        assert sim_normal[-1]["timestamp"] == weather[-1]["timestamp"]


class TestSimulationSOCContinuity:
    def test_soc_continuity_between_hours(self, sim_normal):
        eff_c = config.BATTERY_CHARGE_EFFICIENCY
        eff_d = config.BATTERY_DISCHARGE_EFFICIENCY
        for i in range(1, len(sim_normal)):
            prev     = sim_normal[i - 1]["battery_soc_kwh"]
            r        = sim_normal[i]
            expected = round(prev
                             + r["battery_charge_kw"]    * eff_c
                             - r["battery_discharge_kw"] / eff_d, 2)
            actual   = round(r["battery_soc_kwh"], 2)
            assert abs(actual - expected) <= 0.05, (
                f"SOC discontinuity at hour {i}: expected {expected}, got {actual}"
            )


class TestSimulationFuelMonotonicity:
    def test_fuel_never_increases(self, sim_normal):
        for i in range(1, len(sim_normal)):
            assert sim_normal[i]["fuel_remaining_litres"] <= sim_normal[i - 1]["fuel_remaining_litres"]


class TestSimulationNormalScenario:
    def test_no_unmet_load(self, sim_normal):
        assert all(r["unmet_load_kw"] == 0.0 for r in sim_normal)

    def test_final_soc_approx(self, sim_normal):
        assert sim_normal[-1]["battery_soc_kwh"] == pytest.approx(103.5, abs=0.1)

    def test_final_fuel_approx(self, sim_normal):
        assert sim_normal[-1]["fuel_remaining_litres"] == pytest.approx(4806.2881, abs=0.01)

    def test_fuel_was_consumed(self, sim_normal):
        assert sim_normal[-1]["fuel_remaining_litres"] < INIT_FUEL


class TestSimulationG1Failure:
    def test_g1_always_zero(self, sim_g1fail):
        assert all(r["generator_1_power_kw"] == 0.0 for r in sim_g1fail)

    def test_g2_runs_during_night(self, sim_g1fail):
        # Night hours (0-5) have no renewables — G2 must supply load
        night_hours = sim_g1fail[:6]
        assert all(r["generator_2_power_kw"] > 0.0 for r in night_hours)

    def test_no_unmet_load_g1_fail(self, sim_g1fail):
        assert all(r["unmet_load_kw"] == 0.0 for r in sim_g1fail)

    def test_row_count_unchanged(self, sim_g1fail):
        assert len(sim_g1fail) == 24
