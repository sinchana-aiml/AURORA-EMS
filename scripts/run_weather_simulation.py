# scripts/run_weather_simulation.py
# ─────────────────────────────────────────────────────────────────────────────
# AURORA-EMS  CSV Weather Loader -> Digital Twin connector
# Loads a local weather CSV, validates it, and runs the simulation loop.
# NOTE: All simulation values are SYNTHETIC / PROTOTYPE only.
#
# Run from the project root:
#   python scripts/run_weather_simulation.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os

# Ensure the project root is on sys.path so both 'config' and 'src' are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.digital_twin.weather_loader import (load_weather_csv, validate_weather_records,
                                              make_sample_weather_csv)
from src.digital_twin import run_simulation


def run_from_csv(
    path,
    initial_soc_kwh,
    initial_fuel_litres,
    generator_1_available=True,
    generator_2_available=True,
):
    """
    Load a weather CSV, validate it, and run the digital-twin simulation.

    Returns a list of result dicts (one per weather record), each containing
    the input timestamp plus all fields from energy_balance_step.
    """
    records = load_weather_csv(path)
    validate_weather_records(records)
    return run_simulation(
        records,
        initial_soc_kwh,
        initial_fuel_litres,
        generator_1_available=generator_1_available,
        generator_2_available=generator_2_available,
    )


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile
    import config

    INIT_SOC  = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION  # 210 kWh
    INIT_FUEL = config.FUEL_TANK_LITRES                                              # 5000 L

    print("=" * 60)
    print("  scripts/run_weather_simulation.py  self-test")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test_weather.csv")

        # Step 1: generate synthetic 24-hour CSV
        print()
        make_sample_weather_csv(csv_path)

        # Step 2: load and validate
        records = load_weather_csv(csv_path)
        validate_weather_records(records)
        print(f"Loaded and validated {len(records)} weather records.")

        # Step 3: run 24-hour simulation via run_from_csv
        results = run_from_csv(csv_path, INIT_SOC, INIT_FUEL)

        # Step 4: summary output
        first = results[0]
        last  = results[-1]
        total_fuel_used = round(INIT_FUEL - last["fuel_remaining_litres"], 4)
        max_unmet       = max(r["unmet_load_kw"] for r in results)

        print()
        print(f"First timestamp : {first['timestamp']}")
        print(f"Last  timestamp : {last['timestamp']}")
        print(f"Final battery SOC     : {last['battery_soc_kwh']} kWh")
        print(f"Final fuel remaining  : {last['fuel_remaining_litres']} L")
        print(f"Total fuel used       : {total_fuel_used} L")
        print(f"Maximum unmet load    : {max_unmet} kW")

        # Step 5: timestamp alignment checks
        print()
        print("Timestamp alignment checks:")

        first_ts_match = first["timestamp"] == records[0]["timestamp"]
        print(f"  [{'PASS' if first_ts_match else 'FAIL'}] "
              f"First result timestamp matches first weather record  "
              f"({first['timestamp']})")

        last_ts_match = last["timestamp"] == records[-1]["timestamp"]
        print(f"  [{'PASS' if last_ts_match else 'FAIL'}] "
              f"Last result timestamp matches last weather record  "
              f"({last['timestamp']})")

        row_count_match = len(results) == len(records)
        print(f"  [{'PASS' if row_count_match else 'FAIL'}] "
              f"Result row count equals record count  ({len(results)})")

    print()
    print("Self-test complete.")
