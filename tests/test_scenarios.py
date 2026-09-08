# tests/test_scenarios.py
import pytest
import config
from src.digital_twin.scenarios import (
    apply_storm_scenario,
    apply_generator_failure_scenario,
    apply_low_fuel_scenario,
    apply_communication_outage_scenario,
    apply_sensor_fault_scenario,
)

# Three synthetic records: calm / threshold / storm-force
RECORDS = [
    {"timestamp": "2024-07-01T00:00", "temperature_c": -25.0,
     "irradiance_w_m2": 0.0,   "wind_speed_ms": 5.0},
    {"timestamp": "2024-07-01T01:00", "temperature_c": -20.0,
     "irradiance_w_m2": 400.0, "wind_speed_ms": 20.0},
    {"timestamp": "2024-07-01T02:00", "temperature_c": -15.0,
     "irradiance_w_m2": 900.0, "wind_speed_ms": 28.0},
]


class TestStormScenario:
    def setup_method(self):
        self.result = apply_storm_scenario(RECORDS)

    def test_returns_new_list(self):
        assert self.result is not RECORDS

    def test_input_not_mutated(self):
        assert "scenario_name" not in RECORDS[0]
        assert "scenario_name" not in RECORDS[1]
        assert "scenario_name" not in RECORDS[2]

    def test_calm_record_has_no_label(self):
        assert "scenario_name" not in self.result[0]

    def test_threshold_record_labeled_storm(self):
        # 20.0 m/s == STORM_WIND_THRESHOLD_MS → labeled
        assert self.result[1].get("scenario_name") == "storm"

    def test_storm_force_record_labeled_storm(self):
        assert self.result[2].get("scenario_name") == "storm"

    def test_timestamps_preserved(self):
        assert [r["timestamp"] for r in self.result] == [r["timestamp"] for r in RECORDS]

    def test_weather_values_preserved(self):
        for i, rec in enumerate(RECORDS):
            assert self.result[i]["wind_speed_ms"]   == rec["wind_speed_ms"]
            assert self.result[i]["temperature_c"]   == rec["temperature_c"]
            assert self.result[i]["irradiance_w_m2"] == rec["irradiance_w_m2"]


class TestGeneratorFailureScenario:
    def test_g1_failure_config(self):
        cfg = apply_generator_failure_scenario(RECORDS, "G1")
        assert cfg["generator_1_available"] is False
        assert cfg["generator_2_available"] is True
        assert cfg["failed_generator"]      == "G1"
        assert cfg["scenario_name"]         == "generator_failure"

    def test_g2_failure_config(self):
        cfg = apply_generator_failure_scenario(RECORDS, "G2")
        assert cfg["generator_1_available"] is True
        assert cfg["generator_2_available"] is False
        assert cfg["failed_generator"]      == "G2"

    def test_default_fails_g1(self):
        cfg = apply_generator_failure_scenario(RECORDS)
        assert cfg["generator_1_available"] is False

    def test_invalid_generator_raises(self):
        with pytest.raises(ValueError, match="G1.*G2"):
            apply_generator_failure_scenario(RECORDS, "G3")


class TestLowFuelScenario:
    def test_below_threshold_warns(self):
        r = apply_low_fuel_scenario(300.0)
        assert r["low_fuel_warning"]    is True
        assert r["initial_fuel_litres"] == 300.0
        assert r["scenario_name"]       == "low_fuel"

    def test_exactly_at_threshold_warns(self):
        r = apply_low_fuel_scenario(config.LOW_FUEL_THRESHOLD_L)
        assert r["low_fuel_warning"] is True

    def test_above_threshold_no_warning(self):
        r = apply_low_fuel_scenario(config.LOW_FUEL_THRESHOLD_L + 1.0)
        assert r["low_fuel_warning"] is False

    def test_zero_fuel_warns(self):
        r = apply_low_fuel_scenario(0.0)
        assert r["low_fuel_warning"] is True

    def test_negative_fuel_raises(self):
        with pytest.raises(ValueError, match="negative"):
            apply_low_fuel_scenario(-1.0)


class TestCommunicationOutageScenario:
    def setup_method(self):
        self.result = apply_communication_outage_scenario(RECORDS)

    def test_returns_new_list(self):
        assert self.result is not RECORDS

    def test_input_not_mutated(self):
        assert "communication_status" not in RECORDS[0]

    def test_all_records_offline(self):
        assert all(r["communication_status"] == "offline" for r in self.result)

    def test_timestamps_preserved(self):
        assert [r["timestamp"] for r in self.result] == [r["timestamp"] for r in RECORDS]

    def test_weather_values_preserved(self):
        for i, rec in enumerate(RECORDS):
            assert self.result[i]["wind_speed_ms"] == rec["wind_speed_ms"]


class TestSensorFaultScenario:
    @pytest.mark.parametrize("sensor", ["wind_speed_ms", "temperature_c", "irradiance_w_m2"])
    def test_sensor_set_to_none(self, sensor):
        result = apply_sensor_fault_scenario(RECORDS, sensor)
        assert all(r[sensor] is None for r in result)

    @pytest.mark.parametrize("sensor", ["wind_speed_ms", "temperature_c", "irradiance_w_m2"])
    def test_quality_flag_set(self, sensor):
        result = apply_sensor_fault_scenario(RECORDS, sensor)
        assert all(r["sensor_quality_flag"] == "fault" for r in result)

    @pytest.mark.parametrize("sensor", ["wind_speed_ms", "temperature_c", "irradiance_w_m2"])
    def test_returns_new_list(self, sensor):
        result = apply_sensor_fault_scenario(RECORDS, sensor)
        assert result is not RECORDS

    @pytest.mark.parametrize("sensor", ["wind_speed_ms", "temperature_c", "irradiance_w_m2"])
    def test_input_not_mutated(self, sensor):
        apply_sensor_fault_scenario(RECORDS, sensor)
        assert RECORDS[0][sensor] is not None

    @pytest.mark.parametrize("sensor", ["wind_speed_ms", "temperature_c", "irradiance_w_m2"])
    def test_timestamps_preserved(self, sensor):
        result = apply_sensor_fault_scenario(RECORDS, sensor)
        assert [r["timestamp"] for r in result] == [r["timestamp"] for r in RECORDS]

    @pytest.mark.parametrize("sensor", ["wind_speed_ms", "temperature_c", "irradiance_w_m2"])
    def test_other_sensors_unchanged(self, sensor):
        other = {"wind_speed_ms", "temperature_c", "irradiance_w_m2"} - {sensor}
        result = apply_sensor_fault_scenario(RECORDS, sensor)
        for i, rec in enumerate(RECORDS):
            for s in other:
                assert result[i][s] == rec[s]

    def test_unsupported_sensor_raises(self):
        with pytest.raises(ValueError, match="Unsupported sensor"):
            apply_sensor_fault_scenario(RECORDS, "pressure_hpa")
