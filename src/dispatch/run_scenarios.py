# AURORA-EMS
# Member 4 — Dispatch Scenario Runner
#
# Scenario-level validation for the prototype EMS.
# All values are simulated for research/demo purposes.

import config

from src.digital_twin.simulation import run_simulation
from src.digital_twin.weather_loader import load_weather_csv
from src.dispatch.adapter import adapt_digital_twin_results
from src.dispatch.optimizer import (
    optimized_dispatch,
    optimized_dispatch_lookahead,
)


WEATHER_PATH = "data/sample/digital_twin_weather_24h.csv"


def run_scenario(
    scenario_name,
    generator_1_available=True,
    generator_2_available=True,
    initial_fuel_litres=None,
    storm_mode=False,
    communication_loss=False,
):
    """Run one 24-hour dispatch scenario."""

    if initial_fuel_litres is None:
        initial_fuel_litres = config.FUEL_TANK_LITRES

    weather = load_weather_csv(WEATHER_PATH)

    initial_soc_kwh = (
        config.BATTERY_CAPACITY_KWH * config.BATTERY_INITIAL_SOC_FRACTION
    )

    digital_twin_results = run_simulation(
        weather,
        initial_soc_kwh=initial_soc_kwh,
        initial_fuel_litres=initial_fuel_litres,
    )

    records = adapt_digital_twin_results(
        digital_twin_results
    )

    # Use 24-hour look-ahead optimizer for genuine fuel minimisation
    hourly = optimized_dispatch_lookahead(
        records=records,
        initial_soc_kwh=initial_soc_kwh,
        initial_fuel_litres=initial_fuel_litres,
        generator_1_available=generator_1_available,
        generator_2_available=generator_2_available,
        storm_mode=storm_mode,
        communication_loss=communication_loss,
    )

    results = [
        {
            "timestamp_utc": records[i]["timestamp_utc"],
            "load_total_kw": records[i]["load_total_kw"],
            "renewable_available_kw": (
                records[i]["renewable_available_kw"] * 0.60
                if storm_mode
                else records[i]["renewable_available_kw"]
            ),
            **hourly[i],
        }
        for i in range(len(records))
    ]

    return results


def summarize_scenario(
    scenario_name,
    results,
    initial_fuel_litres,
):
    """Create a safety summary for a scenario."""

    fuel_used = (
        initial_fuel_litres
        - results[-1]["fuel_remaining_litres"]
    )

    minimum_soc = min(
        result["battery_soc_kwh"]
        for result in results
    )

    maximum_unmet = max(
        result["unmet_load_kw"]
        for result in results
    )

    critical_failures = sum(
        not result["critical_load_served"]
        for result in results
    )

    negative_fuel = any(
        result["fuel_remaining_litres"] < 0.0
        for result in results
    )

    generator_capacity_violation = any(
        result["generator_1_kw"]
        > config.GENERATOR_1_RATED_KW
        or result["generator_2_kw"]
        > config.GENERATOR_2_RATED_KW
        for result in results
    )

    minimum_allowed_soc = (
        config.BATTERY_CAPACITY_KWH
        * config.BATTERY_MIN_SOC_FRACTION
    )

    soc_reserve_violation = any(
        result["battery_soc_kwh"]
        < minimum_allowed_soc
        for result in results
    )

    return {
        "scenario": scenario_name,
        "fuel_used_litres": fuel_used,
        "final_fuel_litres": results[-1][
            "fuel_remaining_litres"
        ],
        "minimum_soc_kwh": minimum_soc,
        "maximum_unmet_kw": maximum_unmet,
        "critical_failures": critical_failures,
        "negative_fuel": negative_fuel,
        "generator_capacity_violation": (
            generator_capacity_violation
        ),
        "soc_reserve_violation": soc_reserve_violation,
    }


def main():
    scenarios = [
        {
            "name": "Normal",
            "g1": True,
            "g2": True,
            "fuel": config.FUEL_TANK_LITRES,
            "storm": False,
            "comms_loss": False,
        },
        {
            "name": "Storm",
            "g1": True,
            "g2": True,
            "fuel": config.FUEL_TANK_LITRES,
            "storm": True,
            "comms_loss": False,
        },
        {
            "name": "G1 Failure",
            "g1": False,
            "g2": True,
            "fuel": config.FUEL_TANK_LITRES,
            "storm": False,
            "comms_loss": False,
        },
        {
            "name": "G2 Failure",
            "g1": True,
            "g2": False,
            "fuel": config.FUEL_TANK_LITRES,
            "storm": False,
            "comms_loss": False,
        },
        {
            "name": "Low Fuel",
            "g1": True,
            "g2": True,
            "fuel": config.LOW_FUEL_THRESHOLD_L,
            "storm": False,
            "comms_loss": False,
        },
        {
            "name": "Communication Loss",
            "g1": True,
            "g2": True,
            "fuel": config.FUEL_TANK_LITRES,
            "storm": False,
            "comms_loss": True,
        },
        {
            "name": "Both Generators Unavailable",
            "g1": False,
            "g2": False,
            "fuel": config.FUEL_TANK_LITRES,
            "storm": False,
            "comms_loss": False,
        },
    ]

    print()
    print("AURORA-EMS Dispatch Scenario Tests")
    print("=" * 90)

    for scenario in scenarios:
        results = run_scenario(
            scenario_name=scenario["name"],
            generator_1_available=scenario["g1"],
            generator_2_available=scenario["g2"],
            initial_fuel_litres=scenario["fuel"],
            storm_mode=scenario["storm"],
            communication_loss=scenario["comms_loss"],
        )

        summary = summarize_scenario(
            scenario["name"],
            results,
            scenario["fuel"],
        )

        print()
        print(f"Scenario: {summary['scenario']}")
        print("-" * 90)

        print(
            f"Fuel used                    : "
            f"{summary['fuel_used_litres']:.4f} L"
        )

        print(
            f"Final fuel                   : "
            f"{summary['final_fuel_litres']:.4f} L"
        )

        print(
            f"Minimum battery SOC          : "
            f"{summary['minimum_soc_kwh']:.4f} kWh"
        )

        print(
            f"Maximum unmet load           : "
            f"{summary['maximum_unmet_kw']:.4f} kW"
        )

        print(
            f"Critical-load failures       : "
            f"{summary['critical_failures']}"
        )

        print(
            f"Negative fuel                : "
            f"{summary['negative_fuel']}"
        )

        print(
            f"Generator capacity violation : "
            f"{summary['generator_capacity_violation']}"
        )

        print(
            f"SOC reserve violation        : "
            f"{summary['soc_reserve_violation']}"
        )

    print()
    print("=" * 90)
    print("Scenario testing complete.")


if __name__ == "__main__":
    main()