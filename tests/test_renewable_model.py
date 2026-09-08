# tests/test_renewable_model.py
import pytest
import config
from src.digital_twin.renewable_model import solar_pv_output, wind_power_output


class TestSolarPvOutput:
    def test_zero_irradiance_gives_zero(self):
        assert solar_pv_output(0, 25.0) == 0.0

    def test_negative_irradiance_clamped_to_zero(self):
        assert solar_pv_output(-100, 25.0) == 0.0

    def test_full_sun_at_reference_temp(self):
        # 40 * 1.0 * 1.0 * 0.82 = 32.8 kW
        assert solar_pv_output(1000, 25.0) == pytest.approx(32.8)

    def test_half_sun_at_reference_temp(self):
        assert solar_pv_output(500, 25.0) == pytest.approx(16.4)

    def test_cold_temperature_increases_output(self):
        # temp_factor > 1 when temp < 25 C
        output_cold = solar_pv_output(1000, -20.0)
        output_ref  = solar_pv_output(1000,  25.0)
        assert output_cold > output_ref

    def test_hot_temperature_decreases_output(self):
        output_hot = solar_pv_output(1000, 50.0)
        output_ref = solar_pv_output(1000, 25.0)
        assert output_hot < output_ref

    def test_output_never_exceeds_capacity(self):
        # Very cold + full sun should not exceed rated capacity
        assert solar_pv_output(1000, -50.0) <= config.SOLAR_CAPACITY_KW

    def test_output_never_negative(self):
        assert solar_pv_output(0, 100.0) >= 0.0


class TestWindPowerOutput:
    def test_below_cut_in_zero(self):
        assert wind_power_output(0.0) == 0.0
        assert wind_power_output(2.9) == 0.0

    def test_exactly_at_cut_in_zero(self):
        # fraction = (3.0 - 3.0) / (12.0 - 3.0) = 0
        assert wind_power_output(config.WIND_CUT_IN_MS) == 0.0

    def test_midpoint_of_ramp(self):
        # midpoint between cut-in(3) and rated(12) = 7.5 m/s → 25 kW
        assert wind_power_output(7.5) == pytest.approx(25.0)

    def test_at_rated_speed_full_output(self):
        assert wind_power_output(config.WIND_RATED_MS) == pytest.approx(config.WIND_CAPACITY_KW)

    def test_inside_rated_zone_full_output(self):
        assert wind_power_output(20.0) == pytest.approx(config.WIND_CAPACITY_KW)

    def test_exactly_at_cut_out_zero(self):
        assert wind_power_output(config.WIND_CUT_OUT_MS) == 0.0

    def test_above_cut_out_zero(self):
        assert wind_power_output(30.0) == 0.0

    def test_output_never_negative(self):
        for speed in [0, 1, 3, 7.5, 12, 20, 25, 30]:
            assert wind_power_output(speed) >= 0.0
