# tests/test_weather_loader.py
import csv
import os
import tempfile
import pytest
from src.digital_twin.weather_loader import (
    load_weather_csv,
    validate_weather_records,
    make_sample_weather_csv,
    REQUIRED_COLUMNS,
)


@pytest.fixture
def sample_csv(tmp_path):
    """Write a valid 24-row synthetic CSV and return its path."""
    path = str(tmp_path / "weather.csv")
    make_sample_weather_csv(path)
    return path


@pytest.fixture
def sample_records(sample_csv):
    return load_weather_csv(sample_csv)


class TestLoadWeatherCsv:
    def test_loads_24_rows(self, sample_records):
        assert len(sample_records) == 24

    def test_numeric_fields_are_floats(self, sample_records):
        for r in sample_records:
            assert isinstance(r["temperature_c"],   float)
            assert isinstance(r["irradiance_w_m2"], float)
            assert isinstance(r["wind_speed_ms"],   float)

    def test_timestamps_are_strings(self, sample_records):
        assert all(isinstance(r["timestamp"], str) for r in sample_records)

    def test_first_timestamp(self, sample_records):
        assert sample_records[0]["timestamp"] == "2024-07-01T00:00"

    def test_last_timestamp(self, sample_records):
        assert sample_records[-1]["timestamp"] == "2024-07-01T23:00"

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_weather_csv("/nonexistent/path/weather.csv")

    def test_missing_column_raises(self, tmp_path):
        bad = str(tmp_path / "bad.csv")
        with open(bad, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "temperature_c", "irradiance_w_m2"])
            writer.writeheader()
            writer.writerow({"timestamp": "2024-07-01T00:00",
                             "temperature_c": "-20.0", "irradiance_w_m2": "0.0"})
        with pytest.raises(ValueError, match="wind_speed_ms"):
            load_weather_csv(bad)

    def test_non_numeric_value_raises(self, tmp_path):
        bad = str(tmp_path / "bad_num.csv")
        with open(bad, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
            writer.writeheader()
            writer.writerow({"timestamp": "2024-07-01T00:00",
                             "temperature_c": "N/A",
                             "irradiance_w_m2": "0.0",
                             "wind_speed_ms": "2.0"})
        with pytest.raises(ValueError, match="temperature_c"):
            load_weather_csv(bad)


class TestValidateWeatherRecords:
    def test_valid_records_return_true(self, sample_records):
        assert validate_weather_records(sample_records) is True

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="empty"):
            validate_weather_records([])

    def test_negative_irradiance_raises(self, sample_records):
        bad = [dict(r) for r in sample_records]
        bad[3]["irradiance_w_m2"] = -1.0
        with pytest.raises(ValueError, match="irradiance"):
            validate_weather_records(bad)

    def test_negative_wind_raises(self, sample_records):
        bad = [dict(r) for r in sample_records]
        bad[0]["wind_speed_ms"] = -0.1
        with pytest.raises(ValueError, match="wind_speed_ms"):
            validate_weather_records(bad)

    def test_temperature_too_low_raises(self, sample_records):
        bad = [dict(r) for r in sample_records]
        bad[0]["temperature_c"] = -95.0
        with pytest.raises(ValueError, match="temperature_c"):
            validate_weather_records(bad)

    def test_temperature_too_high_raises(self, sample_records):
        bad = [dict(r) for r in sample_records]
        bad[0]["temperature_c"] = 61.0
        with pytest.raises(ValueError, match="temperature_c"):
            validate_weather_records(bad)

    def test_out_of_order_timestamps_raises(self, sample_records):
        bad = list(sample_records)
        bad[1], bad[2] = bad[2], bad[1]
        with pytest.raises(ValueError, match="order"):
            validate_weather_records(bad)


class TestMakeSampleWeatherCsv:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "out.csv")
        make_sample_weather_csv(path)
        assert os.path.exists(path)

    def test_file_has_24_data_rows(self, tmp_path):
        path = str(tmp_path / "out.csv")
        make_sample_weather_csv(path)
        records = load_weather_csv(path)
        assert len(records) == 24
