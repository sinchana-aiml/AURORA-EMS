"""Adapt validated Digital Twin output for the Streamlit dashboard.

This module intentionally performs no energy, generator, weather, forecasting,
or optimization calculations. It loads the repository's validated weather
sample and maps fields already returned by the Digital Twin.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_WEATHER_CSV = PROJECT_ROOT / "data" / "sample" / "digital_twin_weather_24h.csv"

# `streamlit run dashboard/app.py` places dashboard/ on sys.path, so make the
# repository root importable before accessing the existing public Twin API.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config
from src.digital_twin import load_weather_csv, run_simulation, validate_weather_records


DASHBOARD_COLUMNS = [
    "timestamp",
    "load_kw",
    "solar_kw",
    "wind_kw",
    "generator_kw",
    "battery_soc_kwh",
    "fuel_litres",
    "unmet_load_kw",
]


def load_digital_twin_sample() -> pd.DataFrame:
    """Run the Twin against its validated NASA POWER 24-hour weather sample.

    Exceptions from loading, validation, or simulation deliberately reach the
    caller. The dashboard presents a clear error instead of fake replacement
    data when this explicit mode cannot be loaded.
    """
    weather_records = load_weather_csv(SAMPLE_WEATHER_CSV)
    validate_weather_records(weather_records)

    results = run_simulation(
        weather_records=weather_records,
        initial_soc_kwh=config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION,
        initial_fuel_litres=config.FUEL_TANK_LITRES,
    )
    if not results:
        raise ValueError("Digital Twin returned no simulation results.")

    data = pd.DataFrame(
        {
            "timestamp": [result["timestamp"] for result in results],
            "load_kw": [result["total_load_kw"] for result in results],
            "solar_kw": [result["solar_power_kw"] for result in results],
            "wind_kw": [result["wind_power_kw"] for result in results],
            "generator_kw": [result["generator_total_kw"] for result in results],
            "battery_soc_kwh": [result["battery_soc_kwh"] for result in results],
            "fuel_litres": [result["fuel_remaining_litres"] for result in results],
            "unmet_load_kw": [result["unmet_load_kw"] for result in results],
        },
        columns=DASHBOARD_COLUMNS,
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
    data.attrs["battery_capacity_kwh"] = config.BATTERY_CAPACITY_KWH
    return data
