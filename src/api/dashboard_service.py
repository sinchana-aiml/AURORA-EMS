"""Compose existing AURORA-EMS module outputs into dashboard JSON data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import config
from src.digital_twin import load_weather_csv, run_simulation, validate_weather_records
from src.digital_twin.scenarios import apply_storm_scenario
from src.dispatch.adapter import adapt_digital_twin_results
from src.dispatch.optimizer import optimized_dispatch_lookahead
from src.forecasting import ForecastService
from src.resilience.scenario_runner import run_resilience_scenario


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_WEATHER_CSV = PROJECT_ROOT / "data" / "sample" / "digital_twin_weather_24h.csv"
SUPPORTED_SCENARIOS = {
    "normal",
    "storm",
    "g1_failure",
    "g2_failure",
    "low_fuel",
    "communication_loss",
    "both_generators_unavailable",
}


def _json_value(value: Any) -> Any:
    """Convert pandas/numpy scalar values without changing their meaning."""
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _scenario_options(scenario: str) -> dict[str, Any]:
    if scenario not in SUPPORTED_SCENARIOS:
        raise ValueError(f"Unsupported scenario '{scenario}'.")

    return {
        "storm": scenario == "storm",
        "failed_generator": "G1" if scenario == "g1_failure" else "G2" if scenario == "g2_failure" else None,
        "generator_1_available": scenario not in {"g1_failure", "both_generators_unavailable"},
        "generator_2_available": scenario not in {"g2_failure", "both_generators_unavailable"},
        "communication_loss": scenario == "communication_loss",
        "initial_fuel_litres": config.LOW_FUEL_THRESHOLD_L if scenario == "low_fuel" else config.FUEL_TANK_LITRES,
    }


def build_dashboard_payload(scenario: str = "normal", horizon_hours: int = 24) -> dict[str, Any]:
    """Return serialized dashboard data from the project's established modules."""
    if not 1 <= horizon_hours <= 48:
        raise ValueError("horizon_hours must be between 1 and 48.")

    options = _scenario_options(scenario)
    weather_records = load_weather_csv(SAMPLE_WEATHER_CSV)
    validate_weather_records(weather_records)
    scenario_weather = apply_storm_scenario(weather_records) if options["storm"] else weather_records
    initial_soc_kwh = config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION

    telemetry_history = run_simulation(
        weather_records=scenario_weather,
        initial_soc_kwh=initial_soc_kwh,
        initial_fuel_litres=options["initial_fuel_litres"],
        generator_1_available=options["generator_1_available"],
        generator_2_available=options["generator_2_available"],
    )
    if not telemetry_history:
        raise RuntimeError("Digital Twin returned no telemetry records.")

    forecast: dict[str, Any]
    try:
        forecast_rows = ForecastService().generate_forecast(
            current_timestamp=telemetry_history[-1]["timestamp"],
            horizon_hours=horizon_hours,
            is_offline=options["communication_loss"],
        ).to_dict(orient="records")
        forecast = {"available": True, "horizon_hours": horizon_hours, "rows": forecast_rows}
    except Exception as error:  # Forecast availability must be explicit to the UI.
        forecast = {"available": False, "horizon_hours": horizon_hours, "rows": [], "error": str(error)}

    dispatch: dict[str, Any]
    try:
        dispatch_inputs = adapt_digital_twin_results(telemetry_history)
        dispatch_history = optimized_dispatch_lookahead(
            records=dispatch_inputs,
            initial_soc_kwh=initial_soc_kwh,
            initial_fuel_litres=options["initial_fuel_litres"],
            generator_1_available=options["generator_1_available"],
            generator_2_available=options["generator_2_available"],
            storm_mode=options["storm"],
            communication_loss=options["communication_loss"],
        )
        dispatch = {
            "available": True,
            "strategy": "optimized_lookahead",
            "history": dispatch_history,
            "summary": {
                "optimized_fuel_used_litres": options["initial_fuel_litres"] - dispatch_history[-1]["fuel_remaining_litres"],
                "optimized_final_soc_kwh": dispatch_history[-1]["battery_soc_kwh"],
            },
        }
    except Exception as error:
        dispatch = {"available": False, "strategy": "optimized_lookahead", "history": [], "summary": {}, "error": str(error)}

    resilience: dict[str, Any]
    try:
        resilience_history = run_resilience_scenario(
            weather_records,
            storm=options["storm"],
            failed_generator=options["failed_generator"],
            comms_outage_hours=range(len(weather_records)) if options["communication_loss"] else None,
            initial_fuel_litres=options["initial_fuel_litres"],
            initial_soc_kwh=initial_soc_kwh,
        )
        resilience = {
            "available": True,
            "connectivity_status": resilience_history[-1]["connectivity_status"],
            "scenario": scenario,
            "latest": resilience_history[-1],
        }
    except Exception as error:
        resilience = {"available": False, "connectivity_status": "UNAVAILABLE", "scenario": scenario, "latest": None, "error": str(error)}

    return _json_value({
        "station": {"id": "bharati", "name": "Bharati", "latitude": -69.4069, "longitude": 76.1956},
        "provenance": {
            "data_mode": "simulated",
            "weather_source": "NASA_POWER",
            "weather_sample": SAMPLE_WEATHER_CSV.name,
        },
        "telemetry": {"latest": telemetry_history[-1], "history": telemetry_history},
        "forecast": forecast,
        "dispatch": dispatch,
        "resilience": resilience,
    })
