"""
run_real_weather_digital_twin.py
---------------------------------
Integration runner: loads the Member 2 NASA POWER-derived 24-hour weather
sample and drives the Member 1 Digital Twin simulation.

- Does NOT use pv_available_kw or wind_available_kw.
- Solar and wind output are calculated by the Digital Twin's own models.
- Does NOT modify any input file.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.digital_twin.weather_loader import load_weather_csv, validate_weather_records
from src.digital_twin.simulation import run_simulation
import config

SAMPLE_CSV = os.path.join(
    os.path.dirname(__file__), "..", "data", "sample", "digital_twin_weather_24h.csv"
)

INITIAL_SOC_KWH     = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION
INITIAL_FUEL_LITRES = config.FUEL_TANK_LITRES


def run_real_weather():
    path = os.path.normpath(SAMPLE_CSV)

    records = load_weather_csv(path)
    validate_weather_records(records)

    print(f"Input row count      : {len(records)}")
    print(f"First timestamp      : {records[0]['timestamp']}")
    print(f"Last timestamp       : {records[-1]['timestamp']}")
    print("\nFirst 5 input weather records:")
    print(f"  {'timestamp':<35} {'temp_c':>8} {'irr_w_m2':>10} {'wind_ms':>9}")
    print(f"  {'-'*35} {'-'*8} {'-'*10} {'-'*9}")
    for r in records[:5]:
        print(f"  {r['timestamp']:<35} {r['temperature_c']:>8.2f} "
              f"{r['irradiance_w_m2']:>10.2f} {r['wind_speed_ms']:>9.2f}")

    results = run_simulation(
        weather_records     = records,
        initial_soc_kwh     = INITIAL_SOC_KWH,
        initial_fuel_litres = INITIAL_FUEL_LITRES,
    )

    final_soc      = results[-1]["battery_soc_kwh"]
    final_fuel     = results[-1]["fuel_remaining_litres"]
    total_fuel     = INITIAL_FUEL_LITRES - final_fuel
    max_unmet      = max(r["unmet_load_kw"] for r in results)
    hours_renewable = sum(
        1 for r in results
        if r["solar_power_kw"] + r["wind_power_kw"] > 0
    )
    hours_unmet    = sum(1 for r in results if r["unmet_load_kw"] > 0)

    print(f"\nSimulation results (NASA POWER weather, 2015-01-01 UTC):")
    print(f"  Final battery SOC    : {final_soc:.4f} kWh")
    print(f"  Final fuel remaining : {final_fuel:.4f} L")
    print(f"  Total fuel used      : {total_fuel:.4f} L")
    print(f"  Maximum unmet load   : {max_unmet:.4f} kW")
    print(f"  Hours with renewable : {hours_renewable} / {len(results)}")
    print(f"  Hours with unmet load: {hours_unmet} / {len(results)}")

    return records, results


if __name__ == "__main__":
    run_real_weather()
