# tests/test_energy_balance.py
import pytest
import config
from src.digital_twin.energy_balance import energy_balance_step

FUEL    = 5000.0
SOC     = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION  # 210 kWh
MIN_SOC = config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION       # 75 kWh

TOLERANCE = 1e-4  # kW tolerance for power-balance identity


def power_balance_ok(r):
    """LHS = all generation; RHS = all consumption. Must be equal."""
    lhs = r["solar_power_kw"] + r["wind_power_kw"] + r["generator_total_kw"] + r["battery_discharge_kw"]
    rhs = r["supplied_load_kw"] + r["battery_charge_kw"] + r["curtailed_power_kw"]
    return abs(lhs - rhs) < TOLERANCE


class TestEnergyBalanceSunnyWindy:
    """Renewables surplus — no generators needed."""

    def setup_method(self):
        self.r = energy_balance_step(-10, 800, 12.0, SOC, FUEL)

    def test_no_generator_output(self):
        assert self.r["generator_total_kw"] == 0.0

    def test_battery_charges(self):
        assert self.r["battery_charge_kw"] > 0.0

    def test_no_unmet_load(self):
        assert self.r["unmet_load_kw"] == 0.0

    def test_no_fuel_used(self):
        assert self.r["fuel_used_litres"] == 0.0

    def test_power_balance(self):
        assert power_balance_ok(self.r)


class TestEnergyBalanceDarkCalm:
    """No renewables — battery discharges then G1 minimum kicks in."""

    def setup_method(self):
        self.r = energy_balance_step(-20, 0, 2.0, SOC, FUEL)

    def test_no_renewable_output(self):
        assert self.r["solar_power_kw"] == 0.0
        assert self.r["wind_power_kw"]  == 0.0

    def test_battery_discharges(self):
        assert self.r["battery_discharge_kw"] > 0.0

    def test_g1_runs_at_minimum(self):
        assert self.r["generator_1_power_kw"] == pytest.approx(config.GENERATOR_1_MINIMUM_KW)

    def test_no_unmet_load(self):
        assert self.r["unmet_load_kw"] == 0.0

    def test_power_balance(self):
        assert power_balance_ok(self.r)


class TestEnergyBalanceG1Unavailable:
    """G1 offline — G2 takes over."""

    def setup_method(self):
        self.r = energy_balance_step(-20, 0, 2.0, SOC, FUEL,
                                     generator_1_available=False)

    def test_g1_produces_nothing(self):
        assert self.r["generator_1_power_kw"] == 0.0

    def test_g2_runs(self):
        assert self.r["generator_2_power_kw"] > 0.0

    def test_no_unmet_load(self):
        assert self.r["unmet_load_kw"] == 0.0

    def test_power_balance(self):
        assert power_balance_ok(self.r)


class TestEnergyBalanceBatteryAtMinSOC:
    """Battery at floor — cannot discharge, G1 covers full load."""

    def setup_method(self):
        self.r = energy_balance_step(-20, 0, 2.0, MIN_SOC, FUEL)

    def test_battery_does_not_discharge(self):
        assert self.r["battery_discharge_kw"] == 0.0

    def test_g1_covers_load(self):
        assert self.r["generator_1_power_kw"] > 0.0

    def test_no_unmet_load(self):
        assert self.r["unmet_load_kw"] == 0.0

    def test_power_balance(self):
        assert power_balance_ok(self.r)


class TestEnergyBalanceBothGensDown:
    """Both generators offline and battery at floor — unmet load reported."""

    def setup_method(self):
        self.r = energy_balance_step(-20, 0, 2.0, MIN_SOC, FUEL,
                                     generator_1_available=False,
                                     generator_2_available=False)

    def test_unmet_load_positive(self):
        assert self.r["unmet_load_kw"] > 0.0

    def test_critical_load_not_served(self):
        assert self.r["critical_load_served"] is False

    def test_no_fuel_used(self):
        assert self.r["fuel_used_litres"] == 0.0

    def test_power_balance(self):
        assert power_balance_ok(self.r)


class TestOutputFieldNames:
    """All 23 expected keys must be present in every result."""

    EXPECTED_KEYS = {
        "temperature_c", "irradiance_w_m2", "wind_speed_ms",
        "electrical_load_kw", "heating_load_kw", "total_load_kw",
        "solar_power_kw", "wind_power_kw", "renewable_used_kw",
        "battery_charge_kw", "battery_discharge_kw", "battery_soc_kwh",
        "generator_1_power_kw", "generator_2_power_kw", "generator_total_kw",
        "generator_to_battery_charge_kw", "excess_generation_kw",
        "curtailed_power_kw", "fuel_used_litres", "fuel_remaining_litres",
        "unmet_load_kw", "supplied_load_kw", "critical_load_served",
    }

    def test_all_keys_present(self):
        r = energy_balance_step(-10, 800, 12.0, SOC, FUEL)
        assert self.EXPECTED_KEYS.issubset(r.keys())
