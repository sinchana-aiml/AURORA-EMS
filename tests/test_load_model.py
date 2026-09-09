# tests/test_load_model.py
import config
from src.digital_twin.load_model import electrical_load, heating_load, total_load


class TestElectricalLoad:
    def test_with_flexible(self):
        assert electrical_load(include_flexible=True) == config.BASE_LOAD_KW + config.FLEXIBLE_LOAD_KW

    def test_without_flexible(self):
        assert electrical_load(include_flexible=False) == config.BASE_LOAD_KW

    def test_default_includes_flexible(self):
        assert electrical_load() == config.BASE_LOAD_KW + config.FLEXIBLE_LOAD_KW


class TestHeatingLoad:
    def test_at_zero_celsius(self):
        # No extra heating at 0 C
        assert heating_load(0) == config.HEATING_BASE_KW

    def test_above_zero_celsius(self):
        # No extra heating above 0 C
        assert heating_load(10) == config.HEATING_BASE_KW

    def test_below_zero_celsius(self):
        # Extra heating = 10 * 0.8 = 8 kW above base
        assert heating_load(-10) == pytest.approx(config.HEATING_BASE_KW + 10 * config.HEATING_TEMP_COEFF)

    def test_deep_cold(self):
        assert heating_load(-30) == pytest.approx(config.HEATING_BASE_KW + 30 * config.HEATING_TEMP_COEFF)

    def test_known_value_minus20(self):
        # 15 + 20*0.8 = 31 kW
        assert heating_load(-20) == pytest.approx(31.0)


class TestTotalLoad:
    def test_equals_sum_of_components(self):
        for temp in [0, -10, -20, -30]:
            assert total_load(temp) == pytest.approx(
                electrical_load() + heating_load(temp)
            )

    def test_known_value_minus20(self):
        # electrical=30, heating=31 → total=61
        assert total_load(-20) == pytest.approx(61.0)

    def test_without_flexible_minus20(self):
        # electrical=20, heating=31 → total=51
        assert total_load(-20, include_flexible=False) == pytest.approx(51.0)


import pytest
