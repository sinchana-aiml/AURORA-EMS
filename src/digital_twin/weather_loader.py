# src/digital_twin/weather_loader.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  Weather Data Loader
# Loads a local CSV file and converts it into the list-of-dicts format
# expected by run_simulation().
#
# NOTE: Sample data produced here is SYNTHETIC / PROTOTYPE only.
#       It is NOT real Antarctic or NCPOR measurement data.
# ─────────────────────────────────────────────────────────────────────────────

import csv
import os

# ── Required columns ──────────────────────────────────────────────────────────
REQUIRED_COLUMNS = ["timestamp", "temperature_c", "irradiance_w_m2", "wind_speed_ms"]
NUMERIC_COLUMNS  = ["temperature_c", "irradiance_w_m2", "wind_speed_ms"]

# ── Prototype validation bounds ───────────────────────────────────────────────
TEMP_MIN_C = -90.0   # coldest recorded on Earth (Vostok, Antarctica)
TEMP_MAX_C =  60.0   # upper bound for prototype range
IRR_MIN    =   0.0   # irradiance cannot be negative
WIND_MIN   =   0.0   # wind speed cannot be negative


def load_weather_csv(path):
    """
    Reads a CSV file and returns a list of hourly weather dicts.

    Each dict contains:
      timestamp       : str  (preserved as-is from the CSV)
      temperature_c   : float
      irradiance_w_m2 : float
      wind_speed_ms   : float

    Raises ValueError if a required column is missing or any numeric cell
    cannot be converted to float.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Weather CSV not found: {path}")

    records = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

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

        if not (TEMP_MIN_C <= r["temperature_c"] <= TEMP_MAX_C):
            raise ValueError(
                f"{row_label}: temperature_c={r['temperature_c']} is outside "
                f"prototype range [{TEMP_MIN_C}, {TEMP_MAX_C}] C."
            )
        if r["irradiance_w_m2"] < IRR_MIN:
            raise ValueError(
                f"{row_label}: irradiance_w_m2={r['irradiance_w_m2']} is negative."
            )
        if r["wind_speed_ms"] < WIND_MIN:
            raise ValueError(
                f"{row_label}: wind_speed_ms={r['wind_speed_ms']} is negative."
            )

    # ISO-8601 strings (YYYY-MM-DDTHH:MM) sort correctly as plain strings
    for i in range(1, len(records)):
        if records[i]["timestamp"] < records[i - 1]["timestamp"]:
            raise ValueError(
                f"Timestamps are not in order at record {i}: "
                f"'{records[i]['timestamp']}' comes after "
                f"'{records[i-1]['timestamp']}'."
            )

    return True


def make_sample_weather_csv(path):
    """
    Writes a 24-hour synthetic weather CSV to the given path.

    PROTOTYPE / SYNTHETIC DATA -- not real Antarctic measurements.
    Pattern mirrors make_test_weather() in simulation.py:
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
