# weather_loader.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS Weather Data Loader
# Loads a local CSV file and converts it into the list-of-dicts format
# expected by run_simulation() in simulator.py.
#
# NOTE: Sample data produced here is SYNTHETIC / PROTOTYPE only.
#       It is NOT real Antarctic or NCPOR measurement data.
# ─────────────────────────────────────────────────────────────────────────────

import csv
import os

# ── Required columns and their target Python types ───────────────────────────
REQUIRED_COLUMNS = ["timestamp", "temperature_c", "irradiance_w_m2", "wind_speed_ms"]
NUMERIC_COLUMNS  = ["temperature_c", "irradiance_w_m2", "wind_speed_ms"]

# ── Prototype validation bounds ───────────────────────────────────────────────
TEMP_MIN_C   = -90.0   # coldest recorded on Earth (Vostok, Antarctica)
TEMP_MAX_C   =  60.0   # upper bound for prototype range
IRR_MIN      =   0.0   # irradiance cannot be negative
WIND_MIN     =   0.0   # wind speed cannot be negative


# ── 1. CSV LOADER ─────────────────────────────────────────────────────────────

def load_weather_csv(path):
    """
    Reads a CSV file and returns a list of hourly weather dicts.

    Each dict contains:
      timestamp       : str  (preserved as-is from the CSV)
      temperature_c   : float
      irradiance_w_m2 : float
      wind_speed_ms   : float

    Raises ValueError if:
      - a required column is missing from the header
      - any numeric cell cannot be converted to float
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Weather CSV not found: {path}")

    records = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Check all required columns are present in the header
        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"CSV is missing required column(s): {missing}\n"
                f"Found columns: {list(reader.fieldnames)}"
            )

        for row_num, row in enumerate(reader, start=2):  # row 1 = header
            record = {"timestamp": row["timestamp"].strip()}

            for col in NUMERIC_COLUMNS:
                raw = row[col].strip()
                try:
                    record[col] = float(raw)
                except ValueError:
                    raise ValueError(
                        f"Row {row_num}, column '{col}': "
                        f"cannot convert '{raw}' to a number."
                    )

            records.append(record)

    return records


# ── 2. VALIDATOR ──────────────────────────────────────────────────────────────

def validate_weather_records(records):
    """
    Checks a list of weather dicts for physical and ordering constraints.

    Raises ValueError with a descriptive message on the first violation found.
    Returns True if all checks pass.

    Checks:
      - records list is not empty
      - timestamps are in non-decreasing (chronological) order
      - irradiance_w_m2 >= 0 for every row
      - wind_speed_ms   >= 0 for every row
      - temperature_c is within [TEMP_MIN_C, TEMP_MAX_C] for every row
    """
    if not records:
        raise ValueError("Weather records list is empty.")

    for i, r in enumerate(records):
        row_label = f"Record {i} (timestamp={r['timestamp']})"

        # Temperature bounds
        if not (TEMP_MIN_C <= r["temperature_c"] <= TEMP_MAX_C):
            raise ValueError(
                f"{row_label}: temperature_c={r['temperature_c']} is outside "
                f"prototype range [{TEMP_MIN_C}, {TEMP_MAX_C}] °C."
            )

        # Irradiance non-negative
        if r["irradiance_w_m2"] < IRR_MIN:
            raise ValueError(
                f"{row_label}: irradiance_w_m2={r['irradiance_w_m2']} is negative."
            )

        # Wind speed non-negative
        if r["wind_speed_ms"] < WIND_MIN:
            raise ValueError(
                f"{row_label}: wind_speed_ms={r['wind_speed_ms']} is negative."
            )

    # Timestamp order — compare adjacent string timestamps lexicographically.
    # ISO-8601 strings (YYYY-MM-DDTHH:MM) sort correctly as strings.
    for i in range(1, len(records)):
        if records[i]["timestamp"] < records[i - 1]["timestamp"]:
            raise ValueError(
                f"Timestamps are not in order at record {i}: "
                f"'{records[i]['timestamp']}' comes after "
                f"'{records[i-1]['timestamp']}'."
            )

    return True


# ── 3. SAMPLE CSV GENERATOR ───────────────────────────────────────────────────

def make_sample_weather_csv(path):
    """
    Writes a 24-hour synthetic weather CSV to the given path.

    PROTOTYPE / SYNTHETIC DATA — not real Antarctic measurements.
    Pattern mirrors make_test_weather() in simulator.py so the two
    can be cross-checked easily.

      Hours  0-5  : polar night, calm
      Hours  6-11 : morning sun, moderate wind
      Hours 12-17 : peak irradiance, strong wind
      Hours 18-23 : evening, low irradiance, light wind
    """
    rows = []
    for h in range(24):
        if h < 6:
            irr, wind, temp = 0.0,   2.0, -25.0
        elif h < 12:
            irr, wind, temp = 400.0, 8.0, -20.0
        elif h < 18:
            irr, wind, temp = 900.0, 14.0, -15.0
        else:
            irr, wind, temp = 50.0,  5.0, -18.0

        rows.append({
            "timestamp":       f"2024-07-01T{h:02d}:00",
            "temperature_c":   temp,
            "irradiance_w_m2": irr,
            "wind_speed_ms":   wind,
        })

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Sample CSV written to: {path}  ({len(rows)} rows, SYNTHETIC data)")


# ── Self-tests ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
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

    # ── Use a temp directory so tests leave no permanent files ────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_path = os.path.join(tmpdir, "sample_weather.csv")

        # Test 1: make_sample_weather_csv creates a file
        print()
        print("-- Sample CSV generation --")
        make_sample_weather_csv(sample_path)
        check("Sample file exists on disk", os.path.exists(sample_path))

        # Test 2: load_weather_csv returns exactly 24 rows
        print()
        print("-- load_weather_csv --")
        records = load_weather_csv(sample_path)
        check("Loads exactly 24 rows", len(records) == 24)

        # Test 3: numeric conversion — all three numeric fields are floats
        all_float = all(
            isinstance(r["temperature_c"],   float) and
            isinstance(r["irradiance_w_m2"], float) and
            isinstance(r["wind_speed_ms"],   float)
            for r in records
        )
        check("All numeric fields converted to float", all_float)

        # Test 4: timestamps preserved in order
        ts = [r["timestamp"] for r in records]
        check("Timestamps are in chronological order", ts == sorted(ts))

        # Test 5: first and last timestamp spot-check
        check("First timestamp is 2024-07-01T00:00", records[0]["timestamp"]  == "2024-07-01T00:00")
        check("Last  timestamp is 2024-07-01T23:00", records[-1]["timestamp"] == "2024-07-01T23:00")

        # ── validate_weather_records ──────────────────────────────────────────
        print()
        print("-- validate_weather_records --")
        check("Valid records pass validation", validate_weather_records(records) is True)

        # Test 6: reject negative irradiance
        bad_irr = [dict(r) for r in records]
        bad_irr[3]["irradiance_w_m2"] = -10.0
        expect_error("Rejects negative irradiance", lambda: validate_weather_records(bad_irr))

        # Test 7: reject negative wind speed
        bad_wind = [dict(r) for r in records]
        bad_wind[5]["wind_speed_ms"] = -1.0
        expect_error("Rejects negative wind speed", lambda: validate_weather_records(bad_wind))

        # Test 8: reject out-of-range temperature
        bad_temp = [dict(r) for r in records]
        bad_temp[0]["temperature_c"] = -95.0
        expect_error("Rejects temperature below -90 C", lambda: validate_weather_records(bad_temp))

        # Test 9: reject out-of-order timestamps
        bad_order = list(records)          # shallow copy of list
        bad_order[1], bad_order[2] = bad_order[2], bad_order[1]  # swap two rows
        expect_error("Rejects out-of-order timestamps", lambda: validate_weather_records(bad_order))

        # Test 10: reject empty records
        expect_error("Rejects empty records list", lambda: validate_weather_records([]))

        # ── Missing column detection ──────────────────────────────────────────
        print()
        print("-- Missing column detection --")
        bad_csv_path = os.path.join(tmpdir, "bad_weather.csv")
        with open(bad_csv_path, "w", newline="", encoding="utf-8") as f:
            # Write CSV without the wind_speed_ms column
            writer = csv.DictWriter(f, fieldnames=["timestamp", "temperature_c", "irradiance_w_m2"])
            writer.writeheader()
            writer.writerow({"timestamp": "2024-07-01T00:00", "temperature_c": -20.0, "irradiance_w_m2": 0.0})
        expect_error("Rejects CSV missing wind_speed_ms column",
                     lambda: load_weather_csv(bad_csv_path))

        # Test 11: reject non-numeric value in a numeric column
        print()
        print("-- Non-numeric value detection --")
        bad_num_path = os.path.join(tmpdir, "bad_numeric.csv")
        with open(bad_num_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
            writer.writeheader()
            writer.writerow({
                "timestamp": "2024-07-01T00:00",
                "temperature_c": "N/A",          # bad value
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
