# tests/test_generator_model.py
import pytest
import config
from src.digital_twin.generator_model import generator_output_and_fuel


class TestGeneratorOff:
    def test_g1_zero_request_is_off(self):
        r = generator_output_and_fuel(1, 0)
        assert r["actual_output_kw"] == 0.0
        assert r["fuel_used_litres"] == 0.0
        assert r["status"] == "off"

    def test_g2_zero_request_is_off(self):
        r = generator_output_and_fuel(2, 0)
        assert r["status"] == "off"


class TestGeneratorUnavailable:
    def test_g1_unavailable_produces_nothing(self):
        r = generator_output_and_fuel(1, 50, available=False)
        assert r["actual_output_kw"] == 0.0
        assert r["fuel_used_litres"] == 0.0
        assert r["status"] == "unavailable"

    def test_g2_unavailable_produces_nothing(self):
        r = generator_output_and_fuel(2, 80, available=False)
        assert r["actual_output_kw"] == 0.0
        assert r["status"] == "unavailable"


class TestGeneratorMinimumLoad:
    def test_g1_below_minimum_bumped_up(self):
        # Request 10 kW < minimum 20 kW → output = 20 kW
        r = generator_output_and_fuel(1, 10)
        assert r["actual_output_kw"] == pytest.approx(config.GENERATOR_1_MINIMUM_KW)
        assert r["status"] == "running"

    def test_g2_below_minimum_bumped_up(self):
        r = generator_output_and_fuel(2, 20)
        assert r["actual_output_kw"] == pytest.approx(config.GENERATOR_2_MINIMUM_KW)


class TestGeneratorRatedLimit:
    def test_g1_normal_request(self):
        r = generator_output_and_fuel(1, 50)
        assert r["actual_output_kw"] == pytest.approx(50.0)

    def test_g1_capped_at_rated(self):
        r = generator_output_and_fuel(1, 200)
        assert r["actual_output_kw"] == pytest.approx(config.GENERATOR_1_RATED_KW)

    def test_g2_capped_at_rated(self):
        r = generator_output_and_fuel(2, 500)
        assert r["actual_output_kw"] == pytest.approx(config.GENERATOR_2_RATED_KW)


class TestGeneratorFuel:
    def test_g1_fuel_formula_at_50kw(self):
        # idle=3 L/h + 0.25 L/kWh * 50 kW * 1 h = 15.5 L
        r = generator_output_and_fuel(1, 50)
        assert r["fuel_used_litres"] == pytest.approx(15.5)

    def test_g1_fuel_at_minimum_load(self):
        # idle=3 + 0.25*20*1 = 8.0 L
        r = generator_output_and_fuel(1, 10)   # bumped to minimum 20 kW
        assert r["fuel_used_litres"] == pytest.approx(8.0)

    def test_g2_fuel_formula_at_60kw(self):
        # idle=4 + 0.23*60*1 = 17.8 L
        r = generator_output_and_fuel(2, 60)
        assert r["fuel_used_litres"] == pytest.approx(17.8)

    def test_no_fuel_when_off(self):
        r = generator_output_and_fuel(1, 0)
        assert r["fuel_used_litres"] == 0.0

    def test_no_fuel_when_unavailable(self):
        r = generator_output_and_fuel(1, 50, available=False)
        assert r["fuel_used_litres"] == 0.0
