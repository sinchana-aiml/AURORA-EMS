# tests/test_battery_model.py
import pytest
import config
from src.digital_twin.battery_model import battery_step

INIT_SOC = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION  # 210 kWh
MIN_SOC  = config.BATTERY_CAPACITY_KWH * config.BATTERY_MIN_SOC_FRACTION       # 75 kWh
MAX_SOC  = config.BATTERY_CAPACITY_KWH                                          # 300 kWh


class TestBatteryIdle:
    def test_zero_request_no_change(self):
        r = battery_step(INIT_SOC, 0.0)
        assert r["new_soc_kwh"]         == pytest.approx(INIT_SOC)
        assert r["actual_charge_kw"]    == 0.0
        assert r["actual_discharge_kw"] == 0.0


class TestBatteryCharging:
    def test_normal_charge_efficiency(self):
        # 40 kW * 1 h * 0.95 = 38 kWh added → SOC = 248
        r = battery_step(INIT_SOC, 40.0)
        assert r["new_soc_kwh"]      == pytest.approx(248.0)
        assert r["actual_charge_kw"] == pytest.approx(40.0)

    def test_charge_power_capped_at_max(self):
        # Request 100 kW, capped at 60 kW → 60*0.95 = 57 kWh → SOC = 267
        r = battery_step(INIT_SOC, 100.0)
        assert r["new_soc_kwh"]      == pytest.approx(267.0)
        assert r["actual_charge_kw"] == pytest.approx(60.0)

    def test_soc_ceiling_not_exceeded(self):
        # Start at 295, request 40 kW — can only add 5 kWh
        r = battery_step(295.0, 40.0)
        assert r["new_soc_kwh"] == pytest.approx(MAX_SOC)

    def test_charge_returns_zero_discharge(self):
        r = battery_step(INIT_SOC, 40.0)
        assert r["actual_discharge_kw"] == 0.0


class TestBatteryDischarging:
    def test_normal_discharge_efficiency(self):
        # 40 kW delivered → 40/0.95 kWh leaves battery → SOC = 210 - 42.105... = 167.895
        r = battery_step(INIT_SOC, -40.0)
        assert r["new_soc_kwh"]         == pytest.approx(167.8947, abs=1e-3)
        assert r["actual_discharge_kw"] == pytest.approx(40.0)

    def test_discharge_power_capped_at_max(self):
        # Request -100 kW, capped at 60 kW → 60/0.95 kWh leaves → SOC = 210 - 63.158 = 146.842
        r = battery_step(INIT_SOC, -100.0)
        assert r["new_soc_kwh"]         == pytest.approx(146.8421, abs=1e-3)
        assert r["actual_discharge_kw"] == pytest.approx(60.0)

    def test_soc_floor_not_breached(self):
        # Start at 80, request -40 kW — can only drain to 75 kWh floor
        r = battery_step(80.0, -40.0)
        assert r["new_soc_kwh"] == pytest.approx(MIN_SOC)

    def test_discharge_returns_zero_charge(self):
        r = battery_step(INIT_SOC, -40.0)
        assert r["actual_charge_kw"] == 0.0

    def test_at_min_soc_cannot_discharge(self):
        r = battery_step(MIN_SOC, -40.0)
        assert r["new_soc_kwh"]         == pytest.approx(MIN_SOC)
        assert r["actual_discharge_kw"] == 0.0
