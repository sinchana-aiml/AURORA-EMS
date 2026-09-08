# weather_loader.py  (project root)
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Weather Loader -- compatibility wrapper
#
# The real implementation lives in src/digital_twin/weather_loader.py.
# This file re-exports the public API so that any code that previously
# imported from the root weather_loader continues to work unchanged.
#
#   from weather_loader import load_weather_csv          # still works
#   from weather_loader import validate_weather_records  # still works
#   from weather_loader import make_sample_weather_csv   # still works
#   python weather_loader.py                             # still works
# ─────────────────────────────────────────────────────────────────────────────

from src.digital_twin.weather_loader import (
    REQUIRED_COLUMNS,
    NUMERIC_COLUMNS,
    TEMP_MIN_C,
    TEMP_MAX_C,
    IRR_MIN,
    WIND_MIN,
    load_weather_csv,
    validate_weather_records,
    make_sample_weather_csv,
)

# ── Self-tests ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    import tempfile

    PASS = "PASS"
    FAIL = "FAIL"

    def check(label, condition):
        print(f"  [{PASS if condition else FAIL}] {label}")
        return condition

    def expect_error(label, fn):
        """Calls fn(); passes if fn raises ValueError, fails if it does not."""
        try:
            fn()
            print(f"  [{FAIL}] {label}  <-- expected ValueError but none raised>")
            return False
        except ValueError as e:
            print(f"  [{PASS}] {label}  (error: {e})")
            return True

    print("=" * 60)
    print("  weather_loader.py  self-tests")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        sample_path = os.path.join(tmpdir, "sample_weather.csv")

        print()
        print("-- Sample CSV generation --")
        make_sample_weather_csv(sample_path)
        check("Sample file exists on disk", os.path.exists(sample_path))

        print()
        print("-- load_weather_csv --")
        records = load_weather_csv(sample_path)
        check("Loads exactly 24 rows", len(records) == 24)

        all_float = all(
            isinstance(r["temperature_c"],   float) and
            isinstance(r["irradiance_w_m2"], float) and
            isinstance(r["wind_speed_ms"],   float)
            for r in records
        )
        check("All numeric fields converted to float", all_float)

        ts = [r["timestamp"] for r in records]
        check("Timestamps are in chronological order", ts == sorted(ts))
        check("First timestamp is 2024-07-01T00:00", records[0]["timestamp"]  == "2024-07-01T00:00")
        check("Last  timestamp is 2024-07-01T23:00", records[-1]["timestamp"] == "2024-07-01T23:00")

        print()
        print("-- validate_weather_records --")
        check("Valid records pass validation", validate_weather_records(records) is True)

        bad_irr = [dict(r) for r in records]
        bad_irr[3]["irradiance_w_m2"] = -10.0
        expect_error("Rejects negative irradiance", lambda: validate_weather_records(bad_irr))

        bad_wind = [dict(r) for r in records]
        bad_wind[5]["wind_speed_ms"] = -1.0
        expect_error("Rejects negative wind speed", lambda: validate_weather_records(bad_wind))

        bad_temp = [dict(r) for r in records]
        bad_temp[0]["temperature_c"] = -95.0
        expect_error("Rejects temperature below -90 C", lambda: validate_weather_records(bad_temp))

        bad_order = list(records)
        bad_order[1], bad_order[2] = bad_order[2], bad_order[1]
        expect_error("Rejects out-of-order timestamps", lambda: validate_weather_records(bad_order))

        expect_error("Rejects empty records list", lambda: validate_weather_records([]))

        print()
        print("-- Missing column detection --")
        import csv as _csv
        bad_csv_path = os.path.join(tmpdir, "bad_weather.csv")
        with open(bad_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = _csv.DictWriter(f, fieldnames=["timestamp", "temperature_c", "irradiance_w_m2"])
            writer.writeheader()
            writer.writerow({"timestamp": "2024-07-01T00:00", "temperature_c": -20.0, "irradiance_w_m2": 0.0})
        expect_error("Rejects CSV missing wind_speed_ms column",
                     lambda: load_weather_csv(bad_csv_path))

        print()
        print("-- Non-numeric value detection --")
        bad_num_path = os.path.join(tmpdir, "bad_numeric.csv")
        with open(bad_num_path, "w", newline="", encoding="utf-8") as f:
            writer = _csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "timestamp": "2024-07-01T00:00",
                "temperature_c": "N/A",
                "irradiance_w_m2": "0.0",
                "wind_speed_ms": "2.0",
            })
        expect_error("Rejects non-numeric temperature value",
                     lambda: load_weather_csv(bad_num_path))

    print()
    print("All weather_loader tests complete.")
    print()
    print("How to use with run_simulation:")
    print("  from weather_loader import load_weather_csv, validate_weather_records")
    print("  from simulator import run_simulation")
    print("  records = load_weather_csv('data/my_weather.csv')")
    print("  validate_weather_records(records)")
    print("  results = run_simulation(records, initial_soc_kwh=210, initial_fuel_litres=5000)")
